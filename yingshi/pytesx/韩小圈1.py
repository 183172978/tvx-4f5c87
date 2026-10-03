#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩小圈 / 韩剧TV
修复：无播放地址；修复毫秒时间戳；强化降级；移除openssl回退；增强容错
依赖: pip install pycryptodome
"""
import base64
import hashlib
import json
import random
import re
import string
import time
import urllib.parse

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    AES = None
    pad = None
    unpad = None

from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://hanxiaoquan.com'
        self.appHostList = [
            'https://hxqapi.hiyun.tv',
            'https://hxqapi.zmdcq.com'
        ]
        self.userAgent = 'HanjuTV/6.8.2 (Redmi Note 12; Android 14; Scale/2.00)'
        self.vn = '6.8.2'
        self.vc = 'a_8280'
        self.ch = 'xiaomi'
        self.uk_key = b'f349wghhe784tqwh'
        self.uk_iv = b'd3w8hf94fidk38lk'
        self.response_secret = '34F9Q53w/HJW8E6Q'
        self.uid = ''
        self.page_size = 16
        self.channels = {
            '1': {'name': '韩剧'},
            '2': {'name': '综艺'},
            '3': {'name': '电影'},
            '4': {'name': '日剧'},
            '5': {'name': '美剧'},
            '6': {'name': '泰剧'},
            '7': {'name': '国产剧'},
        }

    def getName(self):
        return '韩小圈'

    def init(self, extend=""):
        self.uid = self._uid()
        try:
            if extend:
                ext = json.loads(extend) if isinstance(extend, str) else (extend or {})
                if ext.get('uid'):
                    self.uid = str(ext.get('uid'))
        except Exception:
            pass

    def _uid(self, n=20):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(n))

    def _md5(self, s):
        return hashlib.md5(str(s).encode('utf-8')).hexdigest()

    def _aes_cbc(self, data, key, iv, encrypt=True):
        key = key[:16] if isinstance(key, (bytes, bytearray)) else str(key).encode('utf-8')[:16]
        iv = iv[:16] if isinstance(iv, (bytes, bytearray)) else str(iv).encode('utf-8')[:16]
        if not AES:
            return b'' if encrypt else ''
        cipher = AES.new(key, AES.MODE_CBC, iv)
        if encrypt:
            raw = pad(data if isinstance(data, bytes) else str(data).encode('utf-8'), 16)
            return cipher.encrypt(raw)
        raw = data if isinstance(data, bytes) else base64.b64decode(data)
        pt = cipher.decrypt(raw)
        try:
            return unpad(pt, 16).decode('utf-8', 'ignore')
        except Exception:
            return pt.rstrip(b'\x00').decode('utf-8', 'ignore')

    def _headers(self):
        if not self.uid:
            self.uid = self._uid()
        headers = {
            'User-Agent': self.userAgent,
            'app': 'hj',
            'ch': self.ch,
            'vn': self.vn,
            'vc': self.vc,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip',
            'Connection': 'Keep-Alive',
        }
        try:
            uk = base64.b64encode(self._aes_cbc(self.uid, self.uk_key, self.uk_iv, True)).decode('ascii')
            mix = self._md5(self.uid)
            # 【修复】必须毫秒时间戳 int(time.time()*1000)
            payload = json.dumps({
                'uid': self.uid,
                'model': 'Redmi Note 12',
                'maker': 'Xiaomi',
                'osv': '14',
                'ts': int(round(time.time() * 1000)),
            }, separators=(',', ':'), ensure_ascii=False)
            sign = base64.b64encode(
                self._aes_cbc(payload, mix[:16].encode('utf-8'), mix[16:32].encode('utf-8'), True)
            ).decode('ascii')
            headers['uk'] = uk
            headers['sign'] = sign
            headers['said'] = self._md5(self.uid)[:16]
        except Exception as e:
            print(f"build header fail {e}")
        return headers

    def _decode_body(self, obj):
        if obj is None:
            return {}
        if isinstance(obj, dict):
            data = obj.get('data')
            if isinstance(data, str) and len(data) > 20 and not data.startswith('http'):
                try:
                    key = obj.get('key') or self._md5(self.uid + str(obj.get('ts') or ''))
                    mix = self._md5(str(key) + self.response_secret)
                    text = self._aes_cbc(data, mix[:16].encode('utf-8'), mix[16:32].encode('utf-8'), False)
                    if text:
                        return json.loads(text)
                except Exception as e:
                    print(f"decode_body decrypt err {e}")
            return obj
        if isinstance(obj, str):
            try:
                return self._decode_body(json.loads(obj))
            except Exception:
                return {}
        return {}

    def fetch(self, url, headers=None, params=None):
        import requests
        if headers is None:
            headers = self._headers()
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=12)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"fetch err {url}:{e}")
            return None

    async def api_get(self, path, params=None):
        """遍历全部host列表自动降级，任意一个成功直接返回"""
        for host in self.appHostList:
            resp = self.fetch(host + path, headers=self._headers(), params=params)
            if not resp:
                continue
            try:
                raw_json = resp.json()
                dec = self._decode_body(raw_json)
                if dec:
                    return dec
            except Exception:
                text = getattr(resp, 'text', '') or ''
                dec = self._decode_body(text)
                if dec:
                    return dec
        return {}

    def _pick_list(self, payload):
        if not isinstance(payload, dict):
            return payload if isinstance(payload, list) else []
        for k in ('seriesList', 'list', 'items', 'series', 'result', 'records', 'searchList', 'playItems', 'data'):
            v = payload.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for kk in ('list', 'seriesList', 'items'):
                    if isinstance(v.get(kk), list):
                        return v.get(kk)
        d = payload.get('data')
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            return self._pick_list(d)
        return []

    def _pic(self, item):
        if not isinstance(item, dict):
            return ''
        img = item.get('image') or {}
        if isinstance(img, dict):
            u = img.get('thumb') or img.get('poster') or img.get('url') or ''
            if u:
                return u
        for k in ('thumb', 'poster', 'posterThumb', 'cover', 'pic'):
            u = item.get(k)
            if isinstance(u, str) and u.startswith('http'):
                return u
        return ''

    def _map(self, item):
        if not item or not isinstance(item, dict):
            return None
        sid = item.get('sid') or item.get('seriesId') or item.get('id') or item.get('series_id')
        if not sid:
            return None
        name = item.get('name') or item.get('title') or item.get('seriesName') or str(sid)
        remarks = (
            item.get('upInfo')
            or item.get('updateInfo')
            or item.get('corner')
            or item.get('shorthand')
            or item.get('score')
            or ''
        )
        if item.get('isFinished') or item.get('finish') or item.get('isFinish'):
            remarks = (str(remarks) + ' 完结').strip() if remarks else '完结'
        elif item.get('count'):
            remarks = (str(remarks) + f" 共{item.get('count')}集").strip() if remarks else f"共{item.get('count')}集"
        return {
            'vod_id': str(sid),
            'vod_name': name,
            'vod_pic': self._pic(item),
            'vod_remarks': str(remarks),
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            js = await self.api_get('/api/series/index', {
                'type': '1', 'offset': '0', 'size': str(self.page_size),
            })
            for item in self._pick_list(js)[:24]:
                v = self._map(item)
                if v:
                    videos.append(v)
            if not videos:
                js = await self.api_get('/api/search/s5', {
                    'k': '', 'srefer': 'home', 'type': '1', 'page': '1',
                })
                for item in self._pick_list(js)[:24]:
                    v = self._map(item)
                    if v:
                        videos.append(v)
        except Exception as e:
            print(f"homeVideoContent error: {e}")
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        cate = str(tid or '1')
        offset = (pg - 1) * self.page_size
        videos = []
        more = False
        try:
            js = await self.api_get('/api/series/index', {
                'type': cate,
                'category': cate,
                'offset': str(offset),
                'size': str(self.page_size),
            })
            for item in self._pick_list(js):
                v = self._map(item)
                if v:
                    videos.append(v)
            more = bool(js.get('more')) or len(videos) >= self.page_size - 2
            if not videos:
                js = await self.api_get('/api/search/s5', {
                    'k': '', 'srefer': 'cate', 'type': cate, 'page': str(pg),
                })
                for item in self._pick_list(js):
                    v = self._map(item)
                    if v:
                        videos.append(v)
                more = len(videos) >= 10
        except Exception as e:
            print(f"categoryContent error: {e}")
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if more else pg,
            'limit': self.page_size,
            'total': 9999 if more else (offset + len(videos)),
        }

    def searchContent(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            js = await self.api_get('/api/search/s5', {
                'k': key, 'srefer': 'search_input', 'type': '0', 'page': str(pg),
            })
            for item in self._pick_list(js):
                v = self._map(item)
                if v:
                    videos.append(v)
            if not videos and pg == 1:
                js = await self.api_get('/api/series/index', {
                    'keyword': key, 'offset': '0', 'size': str(self.page_size),
                })
                for item in self._pick_list(js):
                    name = (item.get('name') or '') if isinstance(item, dict) else ''
                    if key in name:
                        v = self._map(item)
                        if v:
                            videos.append(v)
        except Exception as e:
            print(f"searchContent error: {e}")
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 20,
            'total': len(videos),
        }

    def _ep_name(self, ep, idx):
        name = str((ep or {}).get('title') or (ep or {}).get('name') or (ep or {}).get('alias') or '')
        if name and not re.match(r'^\d+$', name):
            return name
        no = (ep or {}).get('serialNo') or (ep or {}).get('episode') or (ep or {}).get('num') or idx
        return f'第{no}集'

    def _episodes(self, sid):
        drama, episodes = {}, []
        js = await self.api_get('/api/series/detail', {'sid': sid})
        if isinstance(js, dict):
            drama = js.get('series') or js.get('data') or {}
            if not isinstance(drama, dict):
                drama = {}
            episodes = js.get('playItems') or []
            if not episodes:
                episodes = self._pick_list(js)
        if not episodes:
            js = await self.api_get('/api/series2/episodes', {'sid': sid})
            episodes = self._pick_list(js)
        if not episodes:
            js = await self.api_get('/api/series/programs_v2', {'sid': sid})
            episodes = self._pick_list(js) or js.get('qxkPrograms') or []
        return drama, episodes or []

    def detailContent(self, ids):
        sid = str((ids or [''])[0])
        try:
            drama, episodes = await self._episodes(sid)
            if not drama.get('name') and not drama.get('title'):
                extra = await self.api_get('/api/series/detail', {'sid': sid})
                drama = (extra.get('series') or extra.get('data') or drama) if isinstance(extra, dict) else drama
            parts = []
            for i, ep in enumerate(episodes, 1):
                if not isinstance(ep, dict):
                    continue
                pid = ep.get('pid') or ep.get('playItemId') or ep.get('id') or ep.get('eid')
                src = ep.get('srcUrl') or ''
                if pid:
                    token = f'{sid}|{pid}'
                    if src and str(src).startswith('http'):
                        token = token + '|' + urllib.parse.quote(src, safe='')
                    parts.append(f'{self._ep_name(ep, i)}${token}')
                elif src and str(src).startswith('http'):
                    parts.append(f'{self._ep_name(ep, i)}${src}')
            if not parts:
                parts.append(f'正片${sid}')
            name = drama.get('name') or drama.get('title') or drama.get('seriesName') or sid
            intro = drama.get('intro') or drama.get('description') or drama.get('brief') or ''
            intro = re.sub(r'<[^>]+>', '', str(intro)).strip()
            crew = drama.get('crew') or ''
            actor = drama.get('actor') or drama.get('actors') or ''
            if not actor and '主演' in crew:
                m = re.search(r'主演[:：]\s*([^\n]+)', crew)
                if m:
                    actor = m.group(1).strip()
            return {
                'list': [{
                    'vod_id': sid,
                    'vod_name': name,
                    'vod_pic': self._pic(drama),
                    'vod_year': str(drama.get('year') or ''),
                    'vod_area': drama.get('area') or '韩国',
                    'vod_actor': actor,
                    'vod_director': drama.get('director') or '',
                    'vod_remarks': drama.get('upInfo') or drama.get('updateInfo') or (
                        '完结' if drama.get('isFinished') else ''
                    ),
                    'vod_content': intro,
                    'vod_play_from': '韩小圈',
                    'vod_play_url': '#'.join(parts),
                }]
            }
        except Exception as e:
            print(f"detailContent error: {e}")
            return {
                'list': [{
                    'vod_id': sid,
                    'vod_name': sid,
                    'vod_play_from': '韩小圈',
                    'vod_play_url': f'正片${sid}',
                }]
            }

    def _pick_url(self, obj):
        if not obj:
            return ''
        if isinstance(obj, str) and obj.startswith('http'):
            return obj
        if isinstance(obj, dict):
            for k in ('playUrl', 'playurl', 'url', 'm3u8', 'src', 'path', 'srcUrl'):
                v = obj.get(k)
                if isinstance(v, str) and v.startswith('http'):
                    return v
                if isinstance(v, dict):
                    u = self._pick_url(v)
                    if u:
                        return u
            for nest in ('play', 'media', 'video', 'data', 'result'):
                u = self._pick_url(obj.get(nest))
                if u:
                    return u
        if isinstance(obj, list):
            for it in obj:
                u = self._pick_url(it)
                if u:
                    return u
        return ''

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play_id = str(id or '')
        if play_id.startswith('http') and self.isVideoFormat(play_id):
            return {'parse': 0, 'jx': '0', 'url': play_id, 'header': header}
        if play_id.startswith('http'):
            return {'parse': 1, 'jx': '1', 'url': play_id, 'header': header}
        parts = play_id.split('|')
        sid = parts[0] if parts else play_id
        pid = parts[1] if len(parts) > 1 else ''
        src = ''
        if len(parts) > 2:
            try:
                src = urllib.parse.unquote(parts[2])
            except Exception:
                src = parts[2]
        finalUrl = ''
        try:
            if pid:
                play_path_list = [
                    ('/api/play/playurl', {'pid': pid, 'sid': sid}),
                    ('/api/play/get', {'pid': pid, 'sid': sid}),
                    ('/api/series/play', {'pid': pid, 'sid': sid}),
                    ('/api/play/playurl', {'pid': pid}),
                ]
                for path, params in play_path_list:
                    js = await self.api_get(path, params)
                    url = self._pick_url(js)
                    if url:
                        finalUrl = url
                        break
            if not finalUrl and src and src.startswith('http'):
                finalUrl = src
        except Exception as e:
            print(f"playerContent error: {e}")
        if finalUrl:
            return {
                'parse': 0 if self.isVideoFormat(finalUrl) else 1,
                'jx': '0' if self.isVideoFormat(finalUrl) else '1',
                'url': finalUrl,
                'header': header,
            }
        return {
            'parse': 1,
            'jx': '1',
            'url': self.siteUrl + '/',
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.m3u8', '.mp4', '.mpd', '.flv'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
#（注：内容由AI生成）

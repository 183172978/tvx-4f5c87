#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩小圈 / 韩剧TV
列表: /api/series/index （offset 分页）
详情: /api/series/detail
播放: /api/play/playurl（多清晰度/多主机）；失败回退 srcUrl 解析
"""
import base64
import hashlib
import json
import random
import re
import string
import subprocess
import sys
import time
import urllib.parse

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    AES = None
    pad = None
    unpad = None

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://hanxiaoquan.com'
        self.appHost = 'https://hxqapi.hiyun.tv'
        self.appHost2 = 'https://hxqapi.zmdcq.com'
        self.tvHost = 'https://api.xiawen.tv'
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
                if ext.get('host'):
                    self.appHost = str(ext.get('host')).rstrip('/')
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
        if AES:
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
        try:
            if encrypt:
                raw = data if isinstance(data, bytes) else str(data).encode('utf-8')
                pad_len = 16 - (len(raw) % 16)
                padded = raw + bytes([pad_len] * pad_len)
                r = subprocess.run(
                    ['openssl', 'enc', '-aes-128-cbc', '-K', key.hex(), '-iv', iv.hex()],
                    input=padded, capture_output=True, timeout=5,
                )
                return r.stdout if r.returncode == 0 else b''
            raw = data if isinstance(data, bytes) else base64.b64decode(data)
            r = subprocess.run(
                ['openssl', 'enc', '-d', '-aes-128-cbc', '-K', key.hex(), '-iv', iv.hex()],
                input=raw, capture_output=True, timeout=5,
            )
            pt = r.stdout or b''
            if pt and 1 <= pt[-1] <= 16:
                pt = pt[:-pt[-1]]
            return pt.decode('utf-8', 'ignore')
        except Exception:
            return b'' if encrypt else ''

    def _headers(self):
        uid = self.uid or self._uid()
        self.uid = uid
        headers = {
            'User-Agent': self.userAgent,
            'app': 'hj',
            'ch': self.ch,
            'vn': self.vn,
            'vc': self.vc,
            'Accept': 'application/json, text/plain, */*',
            'Connection': 'Keep-Alive',
        }
        try:
            uk = base64.b64encode(self._aes_cbc(uid, self.uk_key, self.uk_iv, True)).decode('ascii')
            mix = self._md5(uid)
            payload = json.dumps({
                'uid': uid,
                'model': 'Redmi Note 12',
                'maker': 'Xiaomi',
                'osv': '14',
                'ts': int(time.time() * 1000),
            }, separators=(',', ':'), ensure_ascii=False)
            sign = base64.b64encode(
                self._aes_cbc(payload, mix[:16].encode('utf-8'), mix[16:32].encode('utf-8'), True)
            ).decode('ascii')
            headers['uk'] = uk
            headers['sign'] = sign
            headers['said'] = self._md5(uid)[:16]
        except Exception:
            pass
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
                except Exception:
                    pass
            return obj
        if isinstance(obj, str):
            try:
                return self._decode_body(json.loads(obj))
            except Exception:
                return {}
        return {}

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = self._headers()
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15).read()

            class R:
                def __init__(self, raw):
                    self.content = raw
                    self.text = raw.decode('utf-8', 'ignore') if raw else ''

                def json(self):
                    if not self.text:
                        return {}
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def api_get(self, path, params=None, host=None):
        host = host or self.appHost
        resp = self.fetch(host + path, headers=self._headers(), params=params)
        if not resp:
            if host != self.appHost2:
                return self.api_get(path, params, self.appHost2)
            return {}
        try:
            text = getattr(resp, 'text', '') or ''
            if not text.strip():
                if host != self.appHost2:
                    return self.api_get(path, params, self.appHost2)
                return {}
            try:
                return self._decode_body(resp.json())
            except Exception:
                return self._decode_body(text)
        except Exception:
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
            remarks = (str(remarks) + ' 共%s集' % item.get('count')).strip() if remarks else '共%s集' % item.get('count')
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
            js = self.api_get('/api/series/index', {
                'type': '1', 'offset': '0', 'size': str(self.page_size),
            })
            for item in self._pick_list(js)[:24]:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        cate = str(tid or '1')
        offset = (pg - 1) * self.page_size
        videos = []
        more = False
        try:
            js = self.api_get('/api/series/index', {
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
                js = self.api_get('/api/search/s5', {
                    'k': '', 'srefer': 'cate', 'type': cate, 'page': str(pg),
                })
                for item in self._pick_list(js):
                    v = self._map(item)
                    if v:
                        videos.append(v)
                more = len(videos) >= 10
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if more else pg,
            'limit': self.page_size,
            'total': 9999 if more else (offset + len(videos)),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            js = self.api_get('/api/search/s5', {
                'k': key, 'srefer': 'search_input', 'type': '0', 'page': str(pg),
            })
            for item in self._pick_list(js):
                v = self._map(item)
                if v:
                    videos.append(v)
            if not videos and pg == 1:
                js = self.api_get('/api/series/index', {
                    'keyword': key, 'offset': '0', 'size': str(self.page_size),
                })
                for item in self._pick_list(js):
                    name = (item.get('name') or '') if isinstance(item, dict) else ''
                    if key in name:
                        v = self._map(item)
                        if v:
                            videos.append(v)
        except Exception as e:
            print('搜索失败: %s' % e)
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
        return '第%s集' % no

    def _episodes(self, sid):
        drama, episodes = {}, []
        js = self.api_get('/api/series/detail', {'sid': sid})
        if isinstance(js, dict):
            drama = js.get('series') or js.get('data') or {}
            if not isinstance(drama, dict):
                drama = {}
            episodes = js.get('playItems') or []
            if not episodes:
                episodes = self._pick_list(js)
        if not episodes:
            js = self.api_get('/api/series2/episodes', {'sid': sid})
            episodes = self._pick_list(js)
        if not episodes:
            js = self.api_get('/api/series/programs_v2', {'sid': sid})
            episodes = self._pick_list(js) or js.get('qxkPrograms') or []
        return drama, episodes or []

    def detailContent(self, ids):
        sid = str((ids or [''])[0])
        try:
            drama, episodes = self._episodes(sid)
            if not drama.get('name') and not drama.get('title'):
                extra = self.api_get('/api/series/detail', {'sid': sid})
                drama = (extra.get('series') or extra.get('data') or drama) if isinstance(extra, dict) else drama
            parts = []
            for i, ep in enumerate(episodes, 1):
                if not isinstance(ep, dict):
                    continue
                pid = ep.get('pid') or ep.get('playItemId') or ep.get('id') or ep.get('eid')
                src = ep.get('srcUrl') or ''
                site = ep.get('srcSite') or ''
                if pid:
                    token = '%s|%s' % (sid, pid)
                    if src and str(src).startswith('http'):
                        token += '|' + urllib.parse.quote(src, safe='')
                        if site:
                            token += '|' + urllib.parse.quote(str(site), safe='')
                    parts.append('%s$%s' % (self._ep_name(ep, i), token))
                elif src and str(src).startswith('http'):
                    parts.append('%s$%s' % (self._ep_name(ep, i), src))
            if not parts:
                parts.append('正片$%s' % sid)
            name = drama.get('name') or drama.get('title') or drama.get('seriesName') or sid
            intro = drama.get('intro') or drama.get('description') or drama.get('brief') or ''
            intro = re.sub(r'<[^>]+>', '', str(intro)).strip()
            crew = drama.get('crew') or ''
            actor = drama.get('actor') or drama.get('actors') or ''
            if not actor and '主演' in crew:
                m = re.search(r'主演[:：]\\s*([^\\n]+)', crew)
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
            print('获取详情失败: %s' % e)
            return {
                'list': [{
                    'vod_id': sid,
                    'vod_name': sid,
                    'vod_play_from': '韩小圈',
                    'vod_play_url': '正片$%s' % sid,
                }]
            }

    def _pick_url(self, obj, depth=0):
        if not obj or depth > 6:
            return ''
        if isinstance(obj, str):
            s = obj.strip()
            if s.startswith('http'):
                return s
            return ''
        if isinstance(obj, dict):
            for k in (
                'playUrl', 'playurl', 'play_url', 'url', 'm3u8', 'mp4',
                'src', 'path', 'srcUrl', 'videoUrl', 'mediaUrl', 'hls',
                'highUrl', 'lowUrl', 'hdUrl', 'sdUrl', 'fhdUrl',
            ):
                v = obj.get(k)
                if isinstance(v, str) and v.startswith('http'):
                    return v
                if isinstance(v, dict):
                    u = self._pick_url(v, depth + 1)
                    if u:
                        return u
            for nest in ('play', 'media', 'video', 'data', 'result', 'urls', 'list'):
                u = self._pick_url(obj.get(nest), depth + 1)
                if u:
                    return u
        if isinstance(obj, list):
            for it in obj:
                u = self._pick_url(it, depth + 1)
                if u:
                    return u
        return ''

    def _resolve_play(self, sid, pid):
        qualities = ['11', '10', '2', '1', '0', '']
        hosts = [self.appHost, self.appHost2]
        paths = [
            '/api/play/playurl',
            '/api/play/get',
            '/api/play/url',
            '/api/series/play',
            '/api/playItem/playurl',
            '/api/playItem/url',
        ]
        for host in hosts:
            for path in paths:
                for q in qualities:
                    params = {'pid': pid, 'sid': sid}
                    if q != '':
                        params['quality'] = q
                        params['definition'] = q
                    js = self.api_get(path, params, host=host)
                    if not js:
                        continue
                    url = self._pick_url(js)
                    if url:
                        return url
                    if isinstance(js, dict) and isinstance(js.get('data'), str) and len(js['data']) > 30:
                        try:
                            decoded = self._decode_body(js)
                            url = self._pick_url(decoded)
                            if url:
                                return url
                        except Exception:
                            pass
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

        try:
            if pid:
                url = self._resolve_play(sid, pid)
                if url:
                    return {
                        'parse': 0 if self.isVideoFormat(url) else 1,
                        'jx': '0' if self.isVideoFormat(url) else '1',
                        'url': url,
                        'header': header,
                    }
            if src and src.startswith('http'):
                return {'parse': 1, 'jx': '1', 'url': src, 'header': header}
            if sid and not pid:
                _, episodes = self._episodes(sid)
                for ep in episodes:
                    if not isinstance(ep, dict):
                        continue
                    ep_pid = ep.get('pid') or ''
                    if ep_pid:
                        url = self._resolve_play(sid, ep_pid)
                        if url:
                            return {
                                'parse': 0 if self.isVideoFormat(url) else 1,
                                'jx': '0' if self.isVideoFormat(url) else '1',
                                'url': url,
                                'header': header,
                            }
                    ep_src = ep.get('srcUrl') or ''
                    if ep_src.startswith('http'):
                        return {'parse': 1, 'jx': '1', 'url': ep_src, 'header': header}
        except Exception as e:
            print('获取播放内容失败: %s' % e)

        if src and src.startswith('http'):
            return {'parse': 1, 'jx': '1', 'url': src, 'header': header}
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


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))

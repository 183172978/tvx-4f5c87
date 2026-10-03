# -*- coding: utf-8 -*-
"""
冠建影视 (pandaguard.com)
- 模板 mxpro：详情 /jieshao/{id}/  播放 /bofang/{id}-{sid}-{nid}/
- player_aaaa encrypt: 0明文 / 1 URLDecode / 2 Base64+URLDecode
参考 爱看机器人.py 结构
"""
import sys
import re
import json
import base64
from urllib.parse import unquote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


HOST = 'https://www.pandaguard.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
HEADERS = {
    'User-Agent': UA,
    'Referer': HOST + '/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
CLASSES = [
    {'type_id': '1', 'type_name': '电影'},
    {'type_id': '2', 'type_name': '电视剧'},
    {'type_id': '3', 'type_name': '综艺'},
    {'type_id': '4', 'type_name': '动漫'},
    {'type_id': '5', 'type_name': '纪录片'},
]


class Spider(Spider):

    def init(self, extend=''):
        self.headers = dict(HEADERS)
        if extend and str(extend).strip().startswith('http'):
            global HOST
            HOST = str(extend).strip().rstrip('/')
            self.headers['Referer'] = HOST + '/'

    def getName(self):
        return '冠建影视'

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv)(?:[?#]|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _get(self, url):
        if url.startswith('/'):
            url = HOST + url
        r = self.fetch(url, headers=self.headers)
        return r.text if hasattr(r, 'text') else str(r)

    def homeContent(self, filter=False):
        try:
            html = self._get(HOST + '/')
            classes, seen = [], set()
            for m in re.finditer(r'href="/vodshow/(\d+)[^"]*"[^>]*>([\s\S]*?)</a>', html, re.I):
                tid, name = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if not name or len(name) > 12 or tid in seen:
                    continue
                if re.search(r'首页|专题|留言|排行|求片', name):
                    continue
                seen.add(tid)
                classes.append({'type_id': tid, 'type_name': name})
                if len(classes) >= 12:
                    break
            return {'class': classes or CLASSES, 'filters': {}}
        except Exception:
            return {'class': CLASSES, 'filters': {}}

    def homeVideoContent(self):
        try:
            return {'list': self._parse_list(self._get(HOST + '/'))[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        pg = max(int(str(pg) or 1), 1)
        try:
            html = self._get(f'{HOST}/vodshow/{tid}--------{pg}---/')
            items = self._parse_list(html)
            return {
                'list': items, 'page': pg,
                'pagecount': pg + 1 if len(items) >= 20 else pg,
                'limit': 40, 'total': 9999,
            }
        except Exception as e:
            print('category', e)
            return {'list': [], 'page': pg, 'pagecount': 0}

    def searchContent(self, key, quick=False, pg=1):
        pg = max(int(str(pg) or 1), 1)
        try:
            from urllib.parse import quote
            html = self._get(f'{HOST}/vodsearch/{quote(key)}----------{pg}---/')
            items = self._parse_list(html)
            return {'list': items, 'page': pg}
        except Exception:
            return {'list': [], 'page': pg}

    def detailContent(self, ids):
        path = str(ids[0] if ids else '')
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path += '/'
        try:
            html = self._get(HOST + path)
            if not html:
                return {'list': []}
            name = ''
            m = re.search(r'module-info-heading[\s\S]*?<h1[^>]*>([\s\S]*?)</h1>', html, re.I) or \
                re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
            if m:
                name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if not name:
                m = re.search(r'<title>([^<]+)', html, re.I)
                if m:
                    name = m.group(1).split('-')[0].strip()
            pic = ''
            m = re.search(r'module-info-poster[\s\S]{0,400}?data-original="([^"]+)"', html, re.I)
            if m:
                pic = self._abs(m.group(1))
            content = ''
            m = re.search(r'module-info-introduction-content[^>]*>([\s\S]*?)</div>', html, re.I)
            if m:
                content = re.sub(r'<[^>]+>', '', m.group(1)).strip()

            line_names = []
            for m in re.finditer(r'class="module-tab-item tab-item"[^>]*>([\s\S]*?)</div>', html, re.I):
                t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if t and '选择播放源' not in t:
                    line_names.append(t)

            all_eps = []
            for m in re.finditer(r'href="(/bofang/(\d+)-(\d+)-(\d+)/?)"[^>]*>([\s\S]*?)</a>', html, re.I):
                href = m.group(1) if m.group(1).endswith('/') else m.group(1) + '/'
                title = re.sub(r'<[^>]+>', '', m.group(5)).strip() or f'第{m.group(4)}集'
                all_eps.append({'href': href, 'sid': m.group(3), 'title': title})

            play_from, play_url = [], []
            if all_eps:
                by_sid = {}
                for ep in all_eps:
                    by_sid.setdefault(ep['sid'], []).append(ep)
                for idx, sid in enumerate(sorted(by_sid.keys(), key=lambda x: int(x) if x.isdigit() else 0)):
                    seen, arr = set(), []
                    for ep in by_sid[sid]:
                        if ep['href'] in seen:
                            continue
                        seen.add(ep['href'])
                        arr.append(f"{ep['title']}${ep['href']}")
                    if arr:
                        play_from.append(line_names[idx] if idx < len(line_names) else f'线路{sid}')
                        play_url.append('#'.join(arr))

            return {'list': [{
                'vod_id': path,
                'vod_name': name or '冠建影视',
                'vod_pic': pic,
                'vod_content': content,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]}
        except Exception as e:
            print('detail', e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            path = str(id or '')
            hdr = {'User-Agent': UA, 'Referer': HOST + '/'}
            if self.isVideoFormat(path) and path.startswith('http'):
                return {'parse': 0, 'jx': 0, 'url': path, 'header': hdr}
            if not path.startswith('http'):
                if not path.startswith('/'):
                    path = '/' + path
                if not path.endswith('/'):
                    path += '/'
                path = HOST + path
            html = self._get(path)
            url = self._decode_player(html)
            if not url:
                return {'parse': 1, 'jx': 0, 'url': path, 'header': hdr}
            return {
                'parse': 0 if self.isVideoFormat(url) else 1,
                'jx': 0, 'url': url, 'header': hdr,
            }
        except Exception as e:
            print('play', e)
            return {'parse': 1, 'url': str(id), 'header': {'User-Agent': UA}}

    def _decode_player(self, html):
        m = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>', html or '', re.I)
        if not m:
            return ''
        try:
            player = json.loads(m.group(1))
        except Exception:
            try:
                player = json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', m.group(1))))
            except Exception:
                return ''
        value = str(player.get('url') or '')
        encrypt = int(player.get('encrypt') or 0)
        try:
            if encrypt == 1:
                value = unquote(value)
            elif encrypt == 2:
                pad = '=' * ((4 - len(value) % 4) % 4)
                value = unquote(base64.b64decode(value + pad).decode('utf-8', 'ignore'))
        except Exception as e:
            print('decodePlayer', e)
        return value if re.match(r'^https?:', value, re.I) else ''

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(
            r'<a[^>]+href="(/jieshao/\d+/?)"[^>]*title="([^"]*)"[^>]*class="[^"]*module-poster-item[^"]*"[^>]*>([\s\S]*?)</a>',
            html, re.I
        ):
            vid = m.group(1).rstrip('/') + '/'
            if vid in seen:
                continue
            seen.add(vid)
            name = (m.group(2) or '').strip()
            block = m.group(3)
            if not name:
                tm = re.search(r'module-poster-item-title[^>]*>([\s\S]*?)</', block, re.I)
                if tm:
                    name = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            if not name:
                continue
            pic = ''
            pm = re.search(r'data-original="([^"]+)"', block, re.I) or re.search(r'src="(https?://[^"]+)"', block, re.I)
            if pm:
                pic = self._abs(pm.group(1))
            remarks = ''
            rm = re.search(r'module-item-note[^>]*>([\s\S]*?)</', block, re.I)
            if rm:
                remarks = re.sub(r'<[^>]+>', '', rm.group(1)).strip()
            items.append({'vod_id': vid, 'vod_name': name, 'vod_pic': pic, 'vod_remarks': remarks})
        if not items:
            for m in re.finditer(r'href="(/jieshao/\d+/?)"[\s\S]{0,400}?module-poster-item-title[^>]*>([\s\S]*?)</', html, re.I):
                vid = m.group(1).rstrip('/') + '/'
                if vid in seen:
                    continue
                seen.add(vid)
                name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if name:
                    items.append({'vod_id': vid, 'vod_name': name, 'vod_pic': '', 'vod_remarks': ''})
        return items

    def _abs(self, u):
        u = str(u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if re.match(r'^https?:', u, re.I):
            return u
        if u.startswith('/'):
            return HOST + u
        return HOST + '/' + u

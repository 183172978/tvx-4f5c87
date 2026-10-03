# -*- coding: utf-8 -*-
# 大马猴影视 https://dmhyy.com （备用域名见 siteConfig.domain）
# API 与多多影视同构；需 header: x-platform / X-Client
# 部分线路（如 lzm3u8）直出 m3u8，优先使用
import re
import json
import sys
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

try:
    import requests
except ImportError:
    requests = None

HOST = 'https://dmhyy.com'
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)
# 占位 client id（站点打包常量），配合 x-platform 可拉到播放地址
X_CLIENT = 'YOUR_PUBLIC_CLIENT_ID'
CHANNELS = {
    '22': '剧集',
    '23': '电影',
    '24': '动漫',
    '25': '综艺',
}
# 直链 m3u8 优先
PREFER_FROM = ['lzm3u8', 'rose', 'BBA', 'Ace', 'vwnet', 'NBY', 'YYNB']


class Spider(BaseSpider):
    def __init__(self):
        self.host = HOST

    def getName(self):
        return '大马猴影视'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
                if conf.get('x_client'):
                    global X_CLIENT
                    X_CLIENT = conf['x_client']
            except Exception:
                pass

    def _headers(self):
        return {
            'User-Agent': UA,
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
            'x-platform': 'web',
            'X-Client': X_CLIENT,
        }

    def _get(self, path, params=None):
        url = path if str(path).startswith('http') else (self.host + path)
        try:
            if requests is None:
                import urllib.request
                full = url
                if params:
                    q = '&'.join('%s=%s' % (k, quote(str(v))) for k, v in params.items())
                    full += ('&' if '?' in full else '?') + q
                req = urllib.request.Request(full, headers=self._headers())
                with urllib.request.urlopen(req, timeout=18) as resp:
                    return json.loads(resp.read().decode('utf-8', 'ignore'))
            r = requests.get(url, params=params, headers=self._headers(), timeout=18, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print('GET error', url, e)
        return None

    def _parse_list(self, items):
        videos = []
        if not isinstance(items, list):
            return videos
        for it in items:
            if not isinstance(it, dict) or not it.get('vod_id'):
                continue
            videos.append({
                'vod_id': str(it['vod_id']),
                'vod_name': it.get('vod_name') or '',
                'vod_pic': it.get('vod_pic') or '',
                'vod_remarks': it.get('vod_remarks') or it.get('vod_year') or '',
            })
        return videos

    def _build_play(self, item):
        froms = [x for x in str(item.get('vod_play_from') or '').split('$$$') if x]
        groups = str(item.get('vod_play_url') or '').split('$$$')
        ordered = [p for p in PREFER_FROM if p in froms] + [f for f in froms if f not in PREFER_FROM]
        names, urls = [], []
        for f in ordered:
            idx = froms.index(f)
            if idx >= len(groups):
                continue
            eps = [e for e in groups[idx].split('#') if e]
            if not eps:
                continue
            parts = []
            for j, ep in enumerate(eps):
                if '$' in ep:
                    n, enc = ep.split('$', 1)
                else:
                    n, enc = '第%d集' % (j + 1), ep
                n, enc = n.strip(), enc.strip()
                if not enc:
                    continue
                # 直链 http 直接用；加密串标记 FROM|enc 留给 player 再解
                if enc.startswith('http'):
                    parts.append('%s$%s' % (n or ('第%d集' % (j + 1)), enc))
                else:
                    parts.append('%s$%s|%s' % (n or ('第%d集' % (j + 1)), f, enc))
            if parts:
                names.append(f)
                urls.append('#'.join(parts))
        return '$$$'.join(names), '$$$'.join(urls)

    def homeContent(self, filter):
        return {
            'class': [{'type_id': k, 'type_name': v} for k, v in CHANNELS.items()],
            'list': [],
        }

    def homeVideoContent(self):
        j = self._get('/api.php/web/index/home')
        items = []
        if j and isinstance(j.get('data'), dict):
            items = j['data'].get('recommend') or []
            if not items:
                for c in j['data'].get('categories') or []:
                    items.extend(c.get('videos') or [])
        return {'list': self._parse_list(items)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        j = self._get('/api.php/web/filter/vod', {
            'type_id': str(tid or '22'),
            'page': pg,
            'pageSize': 24,
        })
        items = []
        if j and j.get('data') is not None:
            data = j['data']
            items = data if isinstance(data, list) else (data.get('list') or [])
        videos = self._parse_list(items)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        j = self._get('/api.php/web/search/index', {'wd': key, 'page': pg})
        items = []
        if j and j.get('data') is not None:
            data = j['data']
            items = data if isinstance(data, list) else (data.get('list') or [])
        videos = self._parse_list(items)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        vid = re.sub(r'\D', '', str(ids[0]))
        if not vid:
            return result
        j = self._get('/api.php/web/vod/get_detail', {'vod_id': vid})
        item = None
        if j and j.get('data') is not None:
            data = j['data']
            item = data[0] if isinstance(data, list) and data else data
        if not isinstance(item, dict):
            return result
        play_from, play_url = self._build_play(item)
        result['list'] = [{
            'vod_id': str(item.get('vod_id') or vid),
            'vod_name': item.get('vod_name') or '',
            'vod_pic': item.get('vod_pic') or '',
            'vod_year': str(item.get('vod_year') or ''),
            'vod_area': str(item.get('vod_area') or ''),
            'vod_remarks': item.get('vod_remarks') or '',
            'vod_actor': item.get('vod_actor') or '',
            'vod_director': item.get('vod_director') or '',
            'vod_content': (item.get('vod_content') or '')[:800],
            'vod_play_from': play_from or '大马猴',
            'vod_play_url': play_url or '',
        }]
        return result

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': UA,
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        raw = str(id or '').strip()
        # 已是直链
        if raw.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', raw, re.I):
            return {'parse': 0, 'url': raw, 'header': header}
        if raw.startswith('http'):
            return {'parse': 0, 'url': raw, 'header': header}
        # FROM|enc 加密线路：当前站多数直链可用，加密串需 WASM decode（暂 parse）
        if '|' in raw:
            play_from, enc = raw.split('|', 1)
            if enc.startswith('http'):
                return {'parse': 0, 'url': enc, 'header': header}
            return {'parse': 1, 'jx': 0, 'url': enc, 'header': header}
        return {'parse': 1, 'jx': 0, 'url': raw, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

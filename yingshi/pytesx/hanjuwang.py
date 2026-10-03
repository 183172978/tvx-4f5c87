# -*- coding: utf-8 -*-
# 韩剧网 / 电影人生  https://dyvip2.cc  (镜像 viprs4.cc)
# 详情 API: /api/video?id=
# 播放 API: /api/m3u8?url=
import re, json, sys
from urllib.parse import quote
sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""): pass
try:
    import requests
except ImportError:
    requests = None

HOST = 'https://dyvip2.cc'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
CHANNELS = {
    'dianying': ('电影', '/dianying.html'),
    'dianshiju': ('电视剧', '/dianshiju.html'),
    'zongyi': ('综艺', '/zongyi.html'),
    'dongman': ('动漫', '/dongman.html'),
    'duanju': ('短剧', '/duanju.html'),
    'dianying_hot': ('电影热播', '/dianying.html?sort_field=play_hot'),
    'dianshiju_hot': ('剧集热播', '/dianshiju.html?sort_field=play_hot'),
}

class Spider(BaseSpider):
    def __init__(self):
        self.host = HOST

    def getName(self):
        return '韩剧网'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass

    def _headers(self, extra=None):
        h = {
            'User-Agent': UA,
            'Accept': 'text/html,application/json,*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
        }
        if extra:
            h.update(extra)
        return h

    def _get(self, url, extra=None):
        if not url.startswith('http'):
            url = self.host + (url if url.startswith('/') else '/' + url)
        try:
            if requests is None:
                import urllib.request, ssl
                req = urllib.request.Request(url, headers=self._headers(extra))
                ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=18, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self._headers(extra), timeout=18, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print('GET error', url, e)
        return ''

    def _cover(self, vid):
        return 'https://pic2.tupian.click/img/id/%s.jpg' % vid if vid else ''

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'href="(?:https?://[^"]+)?(/(?:tv|movie)/([a-f0-9]+)-\d+\.html)[^"]*"[^>]*(?:title="([^"]*)")?',
            html, re.I
        ):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            name = (m.group(3) or '').strip()
            block = html[max(0, m.start() - 200): m.start() + 600]
            if not name:
                tm = re.search(r'(?:title|alt)=["\']([^"\']{2,80})["\']', block)
                if tm:
                    name = tm.group(1).strip()
            tips = ''
            rm = re.search(r'(更新[^<\n]{0,20}|全\d+集|\d+集|HD|TC|1080[Pp])', block)
            if rm:
                tips = re.sub(r'\s+', '', rm.group(1))
            videos.append({
                'vod_id': vid,
                'vod_name': (name or vid)[:80],
                'vod_pic': self._cover(vid),
                'vod_remarks': tips,
            })
        return videos

    def homeContent(self, filter):
        return {
            'class': [{'type_id': k, 'type_name': v[0]} for k, v in CHANNELS.items()],
            'list': [],
        }

    def homeVideoContent(self):
        html = self._get('/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        info = CHANNELS.get(str(tid)) or CHANNELS['dianying']
        path = info[1]
        url = path + ('&' if '?' in path else '?') + 'page=%d' % pg if pg > 1 else path
        # page=1 不带 page 参数
        if pg <= 1:
            url = path
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            'list': videos, 'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24, 'total': 9999,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        url = '/s.html?wd=%s' % quote(key)
        if pg > 1:
            url += '&page=%d' % pg
        html = self._get(url)
        videos = self._parse_list(html)
        if not videos:
            html = self._get('/s.html?q=%s' % quote(key))
            videos = self._parse_list(html)
        return {
            'list': videos, 'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24, 'total': len(videos),
        }

    def _extract_id(self, vod_id):
        s = str(vod_id or '')
        m = re.search(r'/(?:tv|movie)/([a-f0-9]+)', s, re.I)
        if m:
            return m.group(1)
        m = re.search(r'[?&]id=([a-f0-9]+)', s, re.I)
        if m:
            return m.group(1)
        return re.sub(r'[^a-f0-9]', '', s, flags=re.I)

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        vid = self._extract_id(ids[0])
        if not vid:
            return result
        text = self._get('/api/video?id=' + vid, {'Accept': 'application/json'})
        name, pic, remarks, content = vid, self._cover(vid), '', ''
        plays = []
        if text and text.strip().startswith('{'):
            try:
                data = json.loads(text)
                name = data.get('Title') or data.get('title') or data.get('vod_name') or name
                pic = data.get('Cover') or data.get('cover') or data.get('vod_pic') or pic
                remarks = data.get('Remark') or data.get('remarks') or ''
                content = data.get('Desc') or data.get('desc') or data.get('vod_content') or ''
                covers = data.get('PlayCovers') or data.get('playCovers') or data.get('Sources') or []
                for i, c in enumerate(covers):
                    if not isinstance(c, dict):
                        continue
                    path = c.get('path') or c.get('url') or c.get('Path') or ''
                    if not path and c.get('id'):
                        path = '/api/m3u8?url=' + c['id']
                    if not path:
                        continue
                    label = c.get('origin') or c.get('name') or c.get('Origin') or ('线路%d' % (i + 1))
                    if not path.startswith('http'):
                        path = self.host + path
                    plays.append((str(label), path))
            except Exception as e:
                print('detail json err', e)
        if not plays:
            html = self._get('/live.html?id=' + vid)
            seen = set()
            for i, m in enumerate(re.finditer(r'/api/m3u8\?[^"\'\s<>]+', html or '', re.I)):
                u = m.group(0).replace('&amp;', '&')
                if u in seen:
                    continue
                seen.add(u)
                label = '线路%d' % (i + 1)
                om = re.search(r'origin=([^&]+)', u)
                if om:
                    try:
                        from urllib.parse import unquote
                        label = unquote(om.group(1))
                    except Exception:
                        pass
                plays.append((label, self.host + u if u.startswith('/') else u))
            if name == vid and html:
                tm = re.search(r'<title>([^<]+)</title>', html, re.I)
                if tm:
                    name = re.sub(r'\s*[-|—].*$', '', tm.group(1)).strip()
        if not plays:
            plays.append(('播放', self.host + '/live.html?id=' + vid))
        play_url = '#'.join('%s$%s' % (n, u) for n, u in plays)
        result['list'] = [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': remarks,
            'vod_actor': '',
            'vod_director': '',
            'vod_content': str(content)[:500],
            'vod_play_from': '韩剧网',
            'vod_play_url': play_url,
        }]
        return result

    def playerContent(self, flag, id, vipFlags):
        header = {'User-Agent': UA, 'Referer': self.host + '/', 'Origin': self.host}
        url = str(id or '')
        if not url.startswith('http'):
            url = self.host + (url if url.startswith('/') else '/' + url)
        if re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I):
            return {'parse': 0, 'url': url, 'header': header}
        if '/api/m3u8' in url:
            body = self._get(url, {'Accept': '*/*', 'Referer': self.host + '/live.html'})
            if body:
                t = body.strip()
                if t.startswith('#EXTM3U'):
                    return {'parse': 0, 'url': url, 'header': header}
                if t[:1] in '{[':
                    try:
                        j = json.loads(t)
                        real = j.get('url') or j.get('Url') or j.get('play') or j.get('play_url')
                        if not real and isinstance(j.get('data'), dict):
                            real = j['data'].get('url') or j['data'].get('play')
                        if real and str(real).startswith('http'):
                            return {'parse': 0, 'url': real, 'header': header}
                    except Exception:
                        pass
                mm = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', t, re.I)
                if mm:
                    return {'parse': 0, 'url': mm.group(0).replace('&amp;', '&'), 'header': header}
            return {'parse': 0, 'url': url, 'header': header}
        if 'live.html' in url:
            return {'parse': 1, 'jx': 0, 'url': url, 'header': header}
        return {'parse': 1, 'jx': 0, 'url': url, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I))
    def manualVideoCheck(self):
        return False
    def localProxy(self, param):
        return None

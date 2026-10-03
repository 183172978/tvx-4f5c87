# -*- coding: utf-8 -*-
# 4K-AV https://4k-av.com  Python 版（由 FourKAV1.js v1.1 移植）
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
import re
import sys
import ssl
import urllib.request
import urllib.parse

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass

VERSION = '1.1.0'
HOST = 'https://4k-av.com'
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)
IGNORE = ['首页']
FALLBACK = [
    {'type_id': '/', 'type_name': '最新'},
    {'type_id': '/tv/', 'type_name': '电视剧'},
    {'type_id': '/movie/', 'type_name': '电影'},
    {'type_id': '/av/', 'type_name': 'AV'},
]


class Spider(BaseSpider):
    def __init__(self):
        self.host = HOST
        self.last_page = {}
        self.headers = {
            'User-Agent': UA,
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE

    def getName(self):
        return '4K-AV'

    def init(self, extend=''):
        if extend:
            ext = str(extend).strip()
            if ext.startswith('http'):
                self.host = ext.rstrip('/')
            else:
                try:
                    import json
                    conf = json.loads(ext) if ext.startswith('{') else {}
                    if conf.get('host'):
                        self.host = conf['host'].rstrip('/')
                except Exception:
                    pass
        self.headers['Referer'] = self.host + '/'

    def _get(self, url, timeout=20):
        try:
            if hasattr(self, 'fetch'):
                try:
                    r = self.fetch(url, headers=self.headers)
                    if isinstance(r, str):
                        return r
                    if hasattr(r, 'text'):
                        return r.text or ''
                    if hasattr(r, 'content'):
                        c = r.content
                        return c.decode('utf-8', 'ignore') if isinstance(c, bytes) else str(c or '')
                except Exception:
                    pass
            req = urllib.request.Request(url, headers=self.headers, method='GET')
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception as e:
            print('_get error:', url, e, file=sys.stderr)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip()
        if u.startswith('http'):
            return u
        if u.startswith('//'):
            return 'https:' + u
        return self.host.rstrip('/') + (u if u.startswith('/') else '/' + u)

    def _to_path(self, u):
        if not u:
            return '/'
        s = str(u).strip()
        if re.match(r'^https?://', s, re.I):
            m = re.match(r'^https?://[^/]+(/.*)?$', s, re.I)
            s = m.group(1) if m and m.group(1) else '/'
        if not s.startswith('/'):
            s = '/' + s
        if s != '/' and not re.search(r'\.html?$', s, re.I) and not s.endswith('/'):
            s += '/'
        return s

    def _clean(self, s):
        s = re.sub(r'<[^>]+>', '', str(s or ''))
        s = s.replace('&amp;', '&').replace('&nbsp;', ' ')
        return re.sub(r'\s+', ' ', s).strip()

    def _first(self, html, pattern):
        m = re.search(pattern, html or '', re.I | re.S)
        return m.group(1) if m else ''

    def _parse_items(self, html):
        videos = []
        seen = set()
        if not html:
            return videos
        blocks = re.split(r'class="[^"]*(?:NTMitem|RTMitem)', html, flags=re.I)
        for b in blocks[1:]:
            href = self._first(b, r'class="[^"]*title[^"]*"[\s\S]{0,120}?href="([^"]+)"')
            if not href:
                href = self._first(b, r'href="([^"]+)"')
            if not href or href in seen:
                continue
            if re.search(r'page-\d+|/s\?|cate_list|#', href):
                continue
            seen.add(href)
            name = self._clean(
                self._first(b, r'<h2[^>]*>([\s\S]*?)</h2>')
                or self._first(b, r'title="([^"]+)"')
                or self._first(b, r'title">([\s\S]*?)<')
            )
            if not name:
                continue
            pic = self._first(b, r'class="[^"]*poster[^"]*"[\s\S]{0,300}?<img[^>]+src="([^"]+)"')
            if not pic:
                pic = self._first(b, r'<img[^>]+src="([^"]+)"')
            remarks = ''
            rm = re.search(r'<span>([^<]{1,30})</span>', b)
            if rm:
                remarks = self._clean(rm.group(1))
            videos.append({
                'vod_id': self._abs(href),
                'vod_name': name,
                'vod_pic': self._abs(pic),
                'vod_remarks': remarks,
            })
        return videos

    def _parse_last_page(self, html):
        m = re.search(r'页次\s*(\d+)\s*/\s*(\d+)', html or '')
        if m:
            return max(1, int(m.group(2) or 1))
        m = re.search(r'class="[^"]*page-number[^"]*"[^>]*>([\s\S]*?)<', html or '', re.I)
        if m:
            parts = self._clean(m.group(1)).split('/')
            n = re.sub(r'\D', '', parts[1] if len(parts) > 1 else parts[0])
            if n:
                return max(1, int(n))
        mx = 1
        for n in re.findall(r'page-(\d+)\.html', html or '', re.I):
            mx = max(mx, int(n))
        return mx

    def _page_key(self, path):
        p = self._to_path(path)
        if '/tv/' in p or p == '/tv/':
            return 'tv'
        if '/movie/' in p or p == '/movie/':
            return 'movie'
        if '/av/' in p or p == '/av/':
            return 'av'
        return 'home'

    def _build_list_url(self, base_path, pg, last):
        base = self._to_path(base_path)
        p = int(pg or 1)
        total = max(1, int(last or 1))
        if p <= 1:
            return self._abs(base)
        real = max(1, total - p + 1)
        root = base if base.endswith('/') else base + '/'
        return self._abs(root + 'page-%d.html' % real)

    def homeContent(self, filter):
        classes = []
        seen = set()

        def add(tid, name):
            tid = self._to_path(tid)
            if not tid or tid in seen or not name:
                return
            for ig in IGNORE:
                if ig in name:
                    return
            seen.add(tid)
            classes.append({'type_id': tid, 'type_name': name})

        add('/', '最新')
        try:
            html = self._get(self.host + '/')
            box = self._first(html, r'id="cate_list"([\s\S]*?)</ul>') or html
            for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', box, re.I):
                name = self._clean(m.group(2))
                if name:
                    add(m.group(1), name)
        except Exception as e:
            print('homeContent error:', e, file=sys.stderr)
        if len(classes) < 2:
            for c in FALLBACK:
                add(c['type_id'], c['type_name'])
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        try:
            html = self._get(self.host + '/')
            return {'list': self._parse_items(html)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        base = self._to_path(tid or '/')
        key = self._page_key(base)
        try:
            if pg == 1 or key not in self.last_page:
                root_html = self._get(self._abs(base))
                self.last_page[key] = self._parse_last_page(root_html)
                if pg == 1:
                    videos = self._parse_items(root_html)
                    if videos:
                        last = self.last_page.get(key) or 1
                        return {
                            'list': videos,
                            'page': 1,
                            'pagecount': last,
                            'limit': 24,
                            'total': last * 24,
                        }
            list_url = self._build_list_url(base, pg, self.last_page.get(key) or 1)
            html = self._get(list_url)
            if not self.last_page.get(key) or self.last_page[key] <= 1:
                self.last_page[key] = self._parse_last_page(html) or self.last_page.get(key) or 1
            videos = self._parse_items(html)
            last = self.last_page.get(key) or pg
            return {
                'list': videos,
                'page': pg,
                'pagecount': last,
                'limit': 24,
                'total': last * 24,
            }
        except Exception as e:
            print('categoryContent error:', e, file=sys.stderr)
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 24, 'total': 0}

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        url = self.host + '/s?q=' + urllib.parse.quote(key)
        if pg > 1:
            url += '&page=%d' % pg
        html = self._get(url)
        videos = self._parse_items(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 24,
            'total': 9999,
        }

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        url = self._abs(ids[0])
        html = self._get(url)
        name = self._clean(
            self._first(html, r'id="MainContent_titleh12"[\s\S]{0,200}?<div[^>]*>([\s\S]*?)</div>')
            or self._first(html, r'<h1[^>]*>([\s\S]*?)</h1>')
            or self._first(html, r'<title>([^<]+)</title>')
        )
        name = re.split(r'/', name)[0]
        name = re.sub(r'第.*集.*', '', name)
        name = re.sub(r'\s*[-_|].*$', '', name).strip()

        pic = self._first(html, r'id="MainContent_poster"[\s\S]{0,200}?<img[^>]+src="([^"]+)"')
        if not pic:
            pic = self._first(html, r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']')

        content = self._clean(
            self._first(html, r'class="[^"]*cnline[^"]*"[^>]*>([\s\S]*?)</div>')
            or self._first(html, r'class="cnline"[^>]*>([\s\S]*?)<')
        )

        eps = []
        chunk = self._first(html, r'id="rtlist"([\s\S]*?)</ul>') or html
        for li in re.findall(r'<li[\s\S]*?</li>', chunk, re.I):
            label = self._clean(self._first(li, r'<span[^>]*>([\s\S]*?)</span>')) or ('第%d集' % (len(eps) + 1))
            src = self._first(li, r'<img[^>]+src="([^"]+)"')
            if src:
                src = re.sub(r'screenshot\.jpg.*', '', src, flags=re.I)
                src = re.sub(r'poster[^/]*\.jpg.*', '', src, flags=re.I)
                if src and not re.search(r'poster_nail|screenshot', src, re.I):
                    eps.append('%s$%s' % (label, self._abs(src)))
        if not eps:
            for m in re.finditer(r'<li[\s\S]*?href="([^"]+)"[\s\S]*?<span[^>]*>([\s\S]*?)</span>', chunk, re.I):
                label = self._clean(m.group(2)) or ('第%d集' % (len(eps) + 1))
                eps.append('%s$%s' % (label, self._abs(m.group(1))))
        if not eps:
            # 当前页直链
            src = self._first(html, r'id="MainContent_videowindow"[\s\S]{0,800}?<source[^>]+src="([^"]+)"')
            if not src:
                src = self._first(html, r'<source[^>]+src="([^"]+\.(?:mp4|m3u8|mkv)[^"]*)"')
            if src:
                eps.append('播放$%s' % self._abs(src))
            else:
                eps.append('播放$%s' % url)

        return {
            'list': [{
                'vod_id': url,
                'vod_name': name or url,
                'vod_pic': self._abs(pic),
                'vod_content': content,
                'vod_play_from': '4K-AV',
                'vod_play_url': '#'.join(eps),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        header = {'User-Agent': UA, 'Referer': self.host + '/'}
        url = self._abs(id)
        try:
            if re.search(r'\.(mp4|m3u8|mkv)(\?|$)', url, re.I) and 'screenshot' not in url:
                return {'parse': 0, 'jx': 0, 'url': url, 'header': header}
            html = self._get(url)
            src = self._first(html, r'id="MainContent_videowindow"[\s\S]{0,800}?<source[^>]+src="([^"]+)"')
            if not src:
                src = self._first(html, r'<video[\s\S]{0,800}?<source[^>]+src="([^"]+)"')
            if not src:
                src = self._first(html, r'<source[^>]+src="([^"]+\.(?:mp4|m3u8|mkv)[^"]*)"')
            if src:
                return {'parse': 0, 'jx': 0, 'url': self._abs(src), 'header': header}
            return {'parse': 1, 'jx': 1, 'url': url, 'header': header}
        except Exception as e:
            print('playerContent error:', e, file=sys.stderr)
            return {'parse': 1, 'jx': 1, 'url': id, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|mkv|ts)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('VERSION', VERSION, 'host', sp.host)
    h = sp.homeContent(False)
    print('classes', [(c['type_id'], c['type_name']) for c in h.get('class') or []])
    hv = sp.homeVideoContent()
    print('homeVod', len(hv.get('list') or []), [x['vod_name'][:30] for x in (hv.get('list') or [])[:3]])
    for tid in ['/', '/tv/', '/movie/']:
        c = sp.categoryContent(tid, 1, False, {})
        print('cat', tid, 'n=', len(c.get('list') or []), 'pages', c.get('pagecount'),
              [x['vod_name'][:28] for x in (c.get('list') or [])[:2]])
    if hv.get('list'):
        d = sp.detailContent([hv['list'][0]['vod_id']])
        vod = (d.get('list') or [{}])[0]
        print('detail', (vod.get('vod_name') or '')[:40])
        print('play', (vod.get('vod_play_url') or '')[:150])
        if vod.get('vod_play_url'):
            first = vod['vod_play_url'].split('#')[0].split('$')[-1]
            p = sp.playerContent('4K-AV', first, [])
            print('player', p.get('parse'), str(p.get('url') or '')[:100])
    s = sp.searchContentPage('妈祖', False, 1)
    print('search', len(s.get('list') or []), [x['vod_name'][:30] for x in (s.get('list') or [])[:3]])

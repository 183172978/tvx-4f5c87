#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EffedUpMovies Spider
https://www.effedupmovies.com
结构参考 光厂 PY：分类列表 / 详情 m3u8 直出
"""
import json
import re
import gzip
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


HOST = 'https://www.effedupmovies.com'
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)

# 主要地区 + 题材（可按需增删）
CHANNELS = [
    ('home', '最新', ''),
    ('american-movies', '美国', 'american-movies'),
    ('asian-movies', '亚洲', 'asian-movies'),
    ('japanese-cinema', '日本', 'japanese-cinema'),
    ('korean-cinema', '韩国', 'korean-cinema'),
    ('hong-kong-movies', '香港', 'hong-kong-movies'),
    ('uk-english-cinema', '英国', 'uk-english-cinema'),
    ('french-cinema', '法国', 'french-cinema'),
    ('german-cinema', '德国', 'german-cinema'),
    ('italian-movies', '意大利', 'italian-movies'),
    ('spanish-films', '西班牙', 'spanish-films'),
    ('south-american-cinema', '拉美', 'south-american-cinema'),
    ('horror', '恐怖', 'horror'),
    ('psychological-thrillers', '惊悚', 'psychological-thrillers'),
    ('real-sex', '情色', 'real-sex'),
    ('cult', 'cult', 'cult'),
    ('movies-based-on-a-true-story', '真实故事', 'movies-based-on-a-true-story'),
    ('documentary', '纪录片', 'documentary'),
    ('torture', '酷刑', 'torture'),
    ('gore-gruesome-splatter', '血腥', 'gore-gruesome-splatter'),
    ('serial-killers', '连环杀手', 'serial-killers'),
    ('zombies', '丧尸', 'zombies'),
    ('vampires-witches', '吸血鬼', 'vampires-witches'),
]


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = HOST
        self.userAgent = UA

    def getName(self):
        return 'EffedUpMovies'

    def init(self, extend=""):
        pass

    def _headers(self):
        return {
            'User-Agent': self.userAgent,
            'Referer': HOST + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }

    def _decode(self, raw):
        if not raw:
            return ''
        if isinstance(raw, str):
            return raw
        if raw[:2] == b'\x1f\x8b':
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw.decode('utf-8', 'ignore')

    def fetch_text(self, url):
        try:
            if requests is not None:
                r = requests.get(url, headers=self._headers(), timeout=20, verify=False)
                return r.text or ''
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=20) as resp:
                return self._decode(resp.read())
        except Exception as e:
            print('fetch error', url, e)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return HOST + u
        return u

    def _clean(self, t):
        t = re.sub(r'<[^>]+>', '', str(t or ''))
        t = t.replace('&#8217;', "'").replace('&#038;', '&').replace('&amp;', '&')
        t = t.replace('&#8211;', '-').replace('&nbsp;', ' ').strip()
        return t

    def _parse_list(self, html):
        videos = []
        if not html:
            return videos
        seen = set()

        # h2/h3 标题链接
        for m in re.finditer(
            r'<h[23][^>]*>\s*<a[^>]+href="(https?://www\.effedupmovies\.com/([^"/]+)/?)"[^>]*>([^<]+)</a>',
            html, re.I,
        ):
            href, slug, title = m.group(1), m.group(2), self._clean(m.group(3))
            if slug in seen or slug in ('page', 'category', 'tag', 'author', 'wp-admin'):
                continue
            if re.match(r'^\d{4}$', slug):
                continue
            seen.add(slug)
            # 附近封面
            start = max(0, m.start() - 2000)
            near = html[start:m.end() + 300]
            pic = ''
            pm = re.search(
                r'(?:src|data-src|data-lazy-src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                near, re.I,
            )
            if pm:
                pic = pm.group(1)
            videos.append({
                'vod_id': slug,
                'vod_name': title[:120] or slug,
                'vod_pic': self._abs(pic),
                'vod_remarks': '',
                'style': {'type': 'rect', 'ratio': 0.68},
            })

        # 兜底：rel=bookmark
        if len(videos) < 4:
            for m in re.finditer(
                r'href="(https?://www\.effedupmovies\.com/([^"/]+)/?)"[^>]*rel="bookmark"[^>]*>([^<]+)',
                html, re.I,
            ):
                slug = m.group(2)
                if slug in seen:
                    continue
                seen.add(slug)
                videos.append({
                    'vod_id': slug,
                    'vod_name': self._clean(m.group(3))[:120],
                    'vod_pic': '',
                    'vod_remarks': '',
                    'style': {'type': 'rect', 'ratio': 0.68},
                })
        return videos

    def _list_url(self, tid, pg):
        pg = int(pg or 1)
        tid = str(tid or 'home')
        if tid == 'home' or tid == '':
            if pg <= 1:
                return HOST + '/'
            return HOST + '/page/%d/' % pg
        # category
        if pg <= 1:
            return HOST + '/category/%s/' % tid
        return HOST + '/category/%s/page/%d/' % (tid, pg)

    def homeContent(self, filter=False):
        classes = [{'type_id': c[0], 'type_name': c[1]} for c in CHANNELS]
        result = {'class': classes, 'list': []}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        html = self.fetch_text(HOST + '/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        url = self._list_url(tid, pg)
        html = self.fetch_text(url)
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else max(pg, 1),
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        q = urllib.parse.quote(str(key or '').strip())
        if pg <= 1:
            url = HOST + '/?s=' + q
        else:
            url = HOST + '/page/%d/?s=%s' % (pg, q)
        html = self.fetch_text(url)
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else max(pg, 1),
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def _extract_play(self, html):
        parts = []
        seen = set()
        for m in re.finditer(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html or '', re.I):
            u = m.group(0).replace('\\/', '/').rstrip('\\\'";')
            if u in seen:
                continue
            seen.add(u)
            label = 'HD'
            if '/v2/' in u:
                label = 'HD·线路2'
            elif '/v1/' in u:
                label = 'HD·线路1'
            parts.append('%s$%s' % (label, u))
        for m in re.finditer(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', html or '', re.I):
            u = m.group(0).replace('\\/', '/')
            if u in seen or 'fluidplayer' in u:
                continue
            seen.add(u)
            parts.append('MP4$%s' % u)
        return parts

    def detailContent(self, ids):
        slug = str((ids or [''])[0]).strip().strip('/')
        if not slug:
            return {'list': []}
        if slug.startswith('http'):
            url = slug
            slug = slug.rstrip('/').split('/')[-1]
        else:
            url = HOST + '/' + slug + '/'
        html = self.fetch_text(url)
        name = slug
        pic = ''
        desc = ''
        m = re.search(r'<title>([^<]+)</title>', html or '', re.I)
        if m:
            name = self._clean(re.sub(r'\s*[-|].*$', '', m.group(1)))
        m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html or '', re.I)
        if m:
            name = self._clean(m.group(1))
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html or '', re.I)
        if m:
            pic = self._abs(m.group(1))
        m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)', html or '', re.I)
        if m:
            desc = self._clean(m.group(1))[:500]
        if not desc:
            m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html or '', re.I)
            if m:
                desc = self._clean(m.group(1))[:500]

        play_parts = self._extract_play(html)
        if not play_parts:
            play_parts = ['网页$%s' % url]

        return {'list': [{
            'vod_id': slug,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_content': desc or 'EffedUpMovies 在线观看',
            'vod_play_from': 'EffedUp',
            'vod_play_url': '#'.join(play_parts[:8]),
            'style': {'type': 'rect', 'ratio': 0.68},
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': self.userAgent,
            'Referer': HOST + '/',
            'Origin': HOST,
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {
                'parse': 0, 'jx': 0, 'url': play, 'header': header,
                'format': 'application/x-mpegURL' if '.m3u8' in play.lower() else 'video/mp4',
            }
        if play.startswith('http'):
            html = self.fetch_text(play)
            parts = self._extract_play(html)
            if parts:
                u = parts[0].split('$')[-1]
                return {
                    'parse': 0, 'jx': 0, 'url': u, 'header': header,
                    'format': 'application/x-mpegURL',
                }
            return {'parse': 1, 'jx': 1, 'url': play, 'header': header}
        # slug
        page = HOST + '/' + re.sub(r'[^\w\-]', '', play) + '/'
        html = self.fetch_text(page)
        parts = self._extract_play(html)
        if parts:
            u = parts[0].split('$')[-1]
            return {
                'parse': 0, 'jx': 0, 'url': u, 'header': header,
                'format': 'application/x-mpegURL',
            }
        return {'parse': 1, 'jx': 1, 'url': page, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(mp4|m3u8|webm)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('home', [c['type_name'] for c in sp.homeContent(False)['class'][:6]])
    hv = sp.homeVideoContent()
    print('homeVod', len(hv.get('list') or []))
    if hv.get('list'):
        print(' first', hv['list'][0].get('vod_name'), (hv['list'][0].get('vod_pic') or '')[:50])
    r = sp.categoryContent('japanese-cinema', 1, False, {})
    print('jp', len(r.get('list') or []))
    if r.get('list'):
        d = sp.detailContent([r['list'][0]['vod_id']])
        main = (d.get('list') or [{}])[0]
        print('detail', main.get('vod_name'), (main.get('vod_play_url') or '')[:100])
        pu = (main.get('vod_play_url') or '').split('#')[0]
        if '$' in pu:
            p = sp.playerContent('EffedUp', pu.split('$', 1)[1], [])
            print('play', p.get('parse'), str(p.get('url'))[:90])

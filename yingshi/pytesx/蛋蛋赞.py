# -*- coding: utf-8 -*-
"""
蛋蛋赞影院 (dandanzan.club)
原址 dandantu.cc 已失效，使用可用镜像
风格对齐 大师兄影视.py
MacCMS: /index.php/vod/type|detail|play
播放: player_aaaa encrypt=1 → urldecode → m3u8
"""
import re
import json
import sys
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):
    DEFAULT_HOST = 'https://www.dandanzan.club'
    UA = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    )
    CLASSES = [
        {'type_id': '1', 'type_name': '电影'},
        {'type_id': '2', 'type_name': '电视剧'},
        {'type_id': '3', 'type_name': '综艺'},
        {'type_id': '4', 'type_name': '动漫'},
        {'type_id': '57', 'type_name': '短剧'},
        {'type_id': '34', 'type_name': '伦理片'},
    ]

    def __init__(self):
        self.host = self.DEFAULT_HOST
        self.ua = self.UA
        self.headers = {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
        }

    def init(self, extend=''):
        if extend:
            try:
                conf = json.loads(extend) if str(extend).strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = str(conf['host']).rstrip('/')
                    self.headers['Referer'] = self.host + '/'
            except Exception:
                if str(extend).startswith('http'):
                    self.host = str(extend).rstrip('/')
                    self.headers['Referer'] = self.host + '/'

    def getName(self):
        return '蛋蛋赞影院'

    def _get(self, url):
        try:
            if not url.startswith('http'):
                url = self.host + (url if url.startswith('/') else '/' + url)
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=18, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.headers, timeout=18, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _abs(self, path):
        if not path:
            return ''
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return 'https:' + path
        return self.host + (path if path.startswith('/') else '/' + path)

    def _clean(self, s):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', str(s or ''))).strip()

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(
            r'<a[^>]+class="[^"]*vodlist__thumb[^"]*"[^>]+href="([^"]+)"[^>]*title="([^"]*)"[^>]*(?:data-original="([^"]*)")?',
            html, re.I
        ):
            href, title, pic = m.group(1), m.group(2), m.group(3) or ''
            if href in seen:
                continue
            seen.add(href)
            if not pic:
                # look nearby
                pass
            items.append({
                'vod_id': href,
                'vod_name': title or href,
                'vod_pic': self._abs(pic) if pic and not pic.startswith('http') else pic,
                'vod_remarks': '蛋蛋赞',
            })
        if not items:
            for m in re.finditer(
                r'href="(/index\.php/vod/detail/id/\d+\.html)"[^>]*title="([^"]*)"',
                html
            ):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                items.append({
                    'vod_id': m.group(1),
                    'vod_name': m.group(2),
                    'vod_pic': '',
                    'vod_remarks': '蛋蛋赞',
                })
        # fix pics via data-original on same block
        for i, it in enumerate(items):
            if it['vod_pic']:
                continue
            vid = it['vod_id']
            m = re.search(
                r'href="%s"[^>]*data-original="([^"]+)"' % re.escape(vid),
                html
            )
            if not m:
                m = re.search(
                    r'data-original="([^"]+)"[^>]*href="%s"' % re.escape(vid),
                    html
                )
            if m:
                items[i]['vod_pic'] = m.group(1)
        return items

    def homeContent(self, filter=False):
        return {'class': list(self.CLASSES), 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._parse_list(self._get(self.host + '/'))[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or '1')
        if pg <= 1:
            url = '%s/index.php/vod/type/id/%s.html' % (self.host, tid)
        else:
            url = '%s/index.php/vod/show/id/%s/page/%d.html' % (self.host, tid, pg)
        html = self._get(url)
        videos = self._parse_list(html)
        # pagecount
        pages = [int(x) for x in re.findall(r'/page/(\d+)\.html', html or '')]
        pagecount = max(pages + [pg])
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': len(videos) or 24,
            'total': pagecount * 24,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        path = str(raw or '').strip()
        if not path:
            return {'list': []}
        detail_url = self._abs(path)
        html = self._get(detail_url)
        if not html:
            return {'list': []}

        title = ''
        m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
        if m:
            title = self._clean(m.group(1))
            title = re.sub(r'\(\d{4}\).*$', '', title).strip()
        if not title:
            m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                title = m.group(1).split('-')[0].split('_')[0].strip()

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'data-original="(https?://[^"]+)"', html)
            if m:
                pic = m.group(1)

        # plays: /index.php/vod/play/id/X/sid/Y/nid/Z.html
        groups, order = {}, []
        for m in re.finditer(
            r'<a[^>]+href="(/index\.php/vod/play/id/\d+/sid/(\d+)/nid/(\d+)\.html)"[^>]*>([\s\S]*?)</a>',
            html, re.I
        ):
            href, sid, nid, body = m.group(1), m.group(2), m.group(3), m.group(4)
            name = self._clean(body) or ('第%s集' % nid)
            if sid not in groups:
                groups[sid] = []
                order.append(sid)
            groups[sid].append('%s$%s' % (name, self._abs(href)))

        play_from, play_url = [], []
        for sid in order:
            if groups[sid]:
                play_from.append('线路' + sid)
                play_url.append('#'.join(groups[sid]))

        return {
            'list': [{
                'vod_id': path,
                'vod_name': title or path,
                'vod_pic': pic,
                'vod_remarks': '蛋蛋赞',
                'vod_content': '',
                'vod_play_from': '$$$'.join(play_from) if play_from else '默认',
                'vod_play_url': '$$$'.join(play_url) if play_url else '',
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        kw = quote(str(key or '').strip())
        if not kw:
            return {'list': []}
        url = '%s/index.php/vod/search/page/%d/wd/%s.html' % (self.host, pg, kw)
        # alt
        html = self._get(url)
        if not html or not self._parse_list(html):
            html = self._get('%s/index.php/vod/search.html?wd=%s&page=%d' % (self.host, kw, pg))
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': 9999,
        }

    def playerContent(self, flag, id, vipFlags=None):
        header = {'User-Agent': self.ua, 'Referer': self.host + '/'}
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

        url = self._abs(play)
        html = self._get(url)
        m = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>', html or '', re.I)
        if not m:
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html or '', re.S)
        if m:
            text = m.group(1)
            depth = end = 0
            for i, c in enumerate(text):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                obj = json.loads(text[:end] if end else text)
                raw = str(obj.get('url') or '')
                enc = int(obj.get('encrypt') or 0)
                if enc == 1:
                    raw = unquote(raw)
                elif enc == 2:
                    import base64
                    try:
                        raw = unquote(base64.b64decode(raw).decode('utf-8', 'ignore'))
                    except Exception:
                        pass
                raw = raw.replace('\\/', '/')
                if raw.startswith('http') and re.search(r'\.(m3u8|mp4)|/play/', raw, re.I):
                    return {'parse': 0, 'jx': 0, 'url': raw, 'header': header}
            except Exception as e:
                print('player parse', e)

        m3 = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html or '')
        for u in m3:
            if 'preview' not in u.lower():
                return {'parse': 0, 'jx': 0, 'url': u.replace('&amp;', '&'), 'header': header}

        return {'parse': 1, 'jx': 0, 'url': url, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

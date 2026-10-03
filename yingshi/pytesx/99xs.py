# -*- coding: utf-8 -*-
"""
CA情色小说 / 99xs - https://99xs.sbs/enter
夜读小说风格：book 列表 + novel:// 正文阅读
WordPress: /article/{id}  /article/category/{slug}/page/N
"""
import json
import re
import sys
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://99xs.sbs'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.classes = [
            {'type_id': 'latest', 'type_name': '最新收录'},
            {'type_id': '%e4%ba%82%e5%80%ab%e5%b0%8f%e8%aa%aa', 'type_name': '乱伦小说'},
            {'type_id': '%e4%ba%ba%e5%a6%bb%e7%86%9f%e5%a5%b3', 'type_name': '人妻熟女'},
            {'type_id': '%e5%bc%b7%e6%9a%b4%e8%99%90%e5%be%85', 'type_name': '强暴虐待'},
            {'type_id': '%e6%a0%a1%e5%9c%92%e5%b8%ab%e7%94%9f', 'type_name': '校园师生'},
            {'type_id': '%e5%90%8c%e5%bf%97%e5%b0%8f%e8%aa%aa', 'type_name': '同志小说'},
            {'type_id': '%e5%8f%a4%e5%85%b8%e6%ad%a6%e4%bf%a0', 'type_name': '古典武侠'},
            {'type_id': '%e9%83%bd%e5%b8%82%e5%b0%8f%e5%93%81', 'type_name': '都市小品'},
            {'type_id': '%e5%90%8d%e4%ba%ba%e6%98%8e%e6%98%9f', 'type_name': '名人明星'},
            {'type_id': '%e5%a4%96%e5%9c%8b%e7%bf%bb%e8%ad%af', 'type_name': '外国翻译'},
        ]

    def getName(self):
        return '99xs小说'

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')

    def get_header(self, url=None):
        return {
            'User-Agent': self.ua,
            'Referer': self.host + '/enter',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8',
        }

    def fetch(self, url, timeout=20):
        if requests is None:
            return None
        try:
            if url.startswith('/'):
                url = self.host + url
            r = requests.get(url, headers=self.get_header(url), timeout=timeout)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            print('fetch', url, e)
            return None

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': {}}

    def homeVideoContent(self):
        r = self.fetch(self.host + '/enter')
        videos = self._parse_list(r.text) if r is not None else []
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'latest')
        if tid == 'latest':
            url = self.host + '/enter' + (('/page/%d' % pg) if pg > 1 else '')
        else:
            url = self.host + '/article/category/' + tid
            if pg > 1:
                url += '/page/%d' % pg
        r = self.fetch(url)
        videos = self._parse_list(r.text) if r is not None else []
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 20,
            'total': 9999,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        bid = re.sub(r'\D', '', str(raw)) or str(raw)
        url = self.host + '/article/' + bid
        r = self.fetch(url)
        if r is None:
            return {'list': []}
        html = r.text
        name = bid
        m = (
            re.search(r'class="[^"]*post-title[^"]*"[^>]*>([\s\S]*?)</', html, re.I)
            or re.search(r'class="[^"]*entry-title[^"]*"[^>]*>([\s\S]*?)</', html, re.I)
            or re.search(r'<title>([^<]+)', html, re.I)
        )
        if m:
            name = self._text(m.group(1).split('|')[0].split('-')[0].split('&#')[0]) or bid
        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = self._fix(m.group(1))
        intro = ''
        m = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            intro = self._text(m.group(1))
        play_url = '正文$%s' % url
        return {
            'list': [{
                'vod_id': bid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_content': intro,
                'vod_play_from': '99xs',
                'vod_play_url': play_url,
                'book_id': bid,
                'book_name': name,
                'book_pic': pic,
                'book_content': intro,
                'volumes': '99xs',
                'urls': play_url,
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        q = urllib.parse.quote(str(key or '').strip())
        r = self.fetch(self.host + '/?s=%s%s' % (q, ('&paged=%d' % pg) if pg > 1 else ''))
        videos = self._parse_list(r.text) if r is not None else []
        if not videos:
            r2 = self.fetch(self.host + '/enter')
            if r2 is not None:
                kw = str(key or '')
                videos = [
                    v for v in self._parse_list(r2.text)
                    if kw in (v.get('vod_name') or v.get('book_name') or '')
                ]
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
        }

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        url = str(id or '')
        if re.match(r'^\d+$', url):
            url = self.host + '/article/' + url
        else:
            url = self._fix(url)
        r = self.fetch(url)
        html = r.text if r is not None else ''
        title = '章节'
        m = (
            re.search(r'class="[^"]*post-title[^"]*"[^>]*>([\s\S]*?)</', html, re.I)
            or re.search(r'<title>([^<]+)', html, re.I)
        )
        if m:
            title = self._text(m.group(1).split('|')[0].split('-')[0]) or title
        content = self._extract_content(html) or '未找到正文'
        data = {'title': title, 'content': content}
        return {
            'parse': 0,
            'url': 'novel://' + json.dumps(data, ensure_ascii=False),
            'content': content,
            'header': self.get_header(url),
        }

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        pass

    def _fix(self, u):
        if not u:
            return ''
        u = str(u).strip().replace('&amp;', '&')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u

    def _text(self, s):
        s = re.sub(r'<[^>]+>', '', str(s or ''))
        s = s.replace('&#8211;', '-').replace('&amp;', '&').replace('&nbsp;', ' ')
        return re.sub(r'\s+', ' ', s).strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'href="((?:https?://[^"]*)?/article/(\d+))/?"[^>]*>([\s\S]*?)</a>',
            html,
            re.I,
        ):
            aid = m.group(2)
            if aid in seen:
                continue
            name = self._text(m.group(3))
            if not name or len(name) < 2:
                continue
            if re.match(r'^(首页|上一页|下一页|\d+)$', name):
                continue
            seen.add(aid)
            videos.append({
                'vod_id': aid,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '',
                'book_id': aid,
                'book_name': name,
                'book_pic': '',
                'book_remarks': '',
            })
        return videos

    def _extract_content(self, html):
        if not html:
            return ''
        m = re.search(
            r'class="entry(?:\s|")[^"]*"[^>]*>([\s\S]*?)(?:class="clear"|post-tags|post-navigation|id="comments"|</article>)',
            html,
            re.I,
        ) or re.search(
            r'class="entry-inner"[^>]*>([\s\S]*?)(?:</div>\s*</div>\s*<div class="clear"|post-tags)',
            html,
            re.I,
        )
        scope = m.group(1) if m else ''
        if not scope:
            return ''
        scope = re.sub(r'<script[\s\S]*?</script>', '', scope, flags=re.I)
        scope = re.sub(r'<style[\s\S]*?</style>', '', scope, flags=re.I)
        lines = []
        for p in re.findall(r'<p[^>]*>[\s\S]*?</p>', scope, re.I):
            t = self._text(p)
            if not t or len(t) < 2:
                continue
            if re.search(r'JuicyAds|ADVERTISEMENT|赞助', t, re.I):
                continue
            lines.append(t)
        return '\n\n'.join(lines)


if __name__ == '__main__':
    sp = Spider()
    print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2)[:400])
    r = sp.categoryContent('latest', 1, False, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        print('first', r['list'][0].get('vod_name', '')[:40])
        d = sp.detailContent([r['list'][0]['vod_id']])
        print('detail', (d.get('list') or [{}])[0].get('vod_name'))
        p = sp.playerContent('99xs', r['list'][0]['vod_id'], None)
        print('content_len', len(p.get('content') or ''))

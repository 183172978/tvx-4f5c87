#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看度新闻 / 成都广播电视台 https://www.cditv.cn
播放地址来自详情页脚本变量: fhdUrl / hdUrl / sdUrl / lowUrl
CDN 示例: https://cstvod.candocloud.cn/..._hd.mp4
"""
import json
import re
import sys
import urllib.parse

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
    """看度新闻"""

    def __init__(self):
        self.siteUrl = 'https://www.cditv.cn'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        self.channels = {
            '4822': {'name': '视频栏目'},
            '4829': {'name': '成都新闻'},
            '4831': {'name': '成都全接触'},
            '4838': {'name': '今晚800'},
            '4808': {'name': '看度资讯'},
        }

    def getName(self):
        return '看度新闻'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
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
                    self.text = raw.decode('utf-8', 'ignore')

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_text(self, url, params=None):
        resp = self.fetch(url, params=params)
        return getattr(resp, 'text', '') if resp else ''

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip().strip('"\'')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _clean(self, s):
        return re.sub(r'<[^>]+>', '', str(s or '')).replace('&nbsp;', ' ').strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        # 标准链接 /show/catid-id.html
        for m in re.finditer(
            r'href=["\']((?:https?://(?:www\.)?cditv\.cn)?/show/(\d+)-(\d+)\.html)["\']'
            r'[^>]{0,300}(?:title|alt)=["\']([^"\']*)["\']',
            html or '',
            re.I,
        ):
            vid = '%s-%s' % (m.group(2), m.group(3))
            name = self._clean(m.group(4) or vid)
            if vid in seen or not name:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '看度',
            })
        if not videos:
            for m in re.finditer(
                r'/show/(\d+)-(\d+)\.html["\'][^>]*>\s*([^<]{4,100})',
                html or '',
            ):
                vid = '%s-%s' % (m.group(1), m.group(2))
                name = self._clean(m.group(3))
                if vid in seen or not name:
                    continue
                seen.add(vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': name,
                    'vod_pic': '',
                    'vod_remarks': '看度',
                })
        # 补封面
        for m in re.finditer(
            r'show/(\d+-\d+)\.html[\s\S]{0,400}?(?:src|data-src|data-original)=["\']'
            r'([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            html or '',
            re.I,
        ):
            for v in videos:
                if v['vod_id'] == m.group(1) and not v['vod_pic']:
                    v['vod_pic'] = self._abs(m.group(2))
                    break
        return videos

    def _list_url(self, tid, pg):
        tid, pg = str(tid), str(pg)
        return [
            '%s/category/%s/%s.html' % (self.siteUrl, tid, pg),
            '%s/list/%s/%s.html' % (self.siteUrl, tid, pg),
        ]

    def _extract_play(self, html):
        """从详情页提取真实播放地址（优先高清）"""
        if not html:
            return ''
        # 1) 页面内嵌 fhdUrl / hdUrl / sdUrl / lowUrl
        urls = {}
        for key in ('fhdUrl', 'hdUrl', 'sdUrl', 'lowUrl'):
            m = re.search(
                r'(?:var\s+)?%s\s*=\s*[\'"]([^\'"]*)[\'"]' % key,
                html,
                re.I,
            )
            if m and m.group(1).strip():
                urls[key] = self._abs(m.group(1).strip())
        for key in ('fhdUrl', 'hdUrl', 'sdUrl', 'lowUrl'):
            if urls.get(key) and urls[key].startswith('http'):
                return urls[key]

        # 2) videourl / videoUrl 赋值
        for pat in (
            r'videourl\s*[:=]\s*[\'"](https?://[^\'"]+)[\'"]',
            r'videoUrl\s*[:=]\s*[\'"](https?://[^\'"]+)[\'"]',
            r'["\']video_url["\']\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'["\']playurl["\']\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'["\']play_url["\']\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'file\s*:\s*[\'"](https?://[^\'"]+\.(?:mp4|m3u8)[^\'"]*)[\'"]',
        ):
            m = re.search(pat, html, re.I)
            if m:
                return self._abs(m.group(1).replace('\\/', '/'))

        # 3) candocloud / 其他 CDN 直链
        m = re.search(
            r'https?://[^\s"\'<>]+(?:candocloud|cditv|omtech)[^\s"\'<>]*\.(?:mp4|m3u8)[^\s"\'<>]*',
            html,
            re.I,
        )
        if m:
            return m.group(0).replace('\\/', '/')

        # 4) 通用 m3u8 / mp4
        m3 = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html or '')
        if m3:
            return m3.group(0).replace('\\/', '/')
        mp4 = re.search(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html or '')
        if mp4:
            return mp4.group(0).replace('\\/', '/')

        # 5) <video src> / <source>
        src = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html or '', re.I)
        if src:
            return self._abs(src.group(1))
        src2 = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html or '', re.I)
        if src2:
            return self._abs(src2.group(1))

        return ''

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            for tid in ('4822', '4829', '4831'):
                html = ''
                for url in self._list_url(tid, 1):
                    html = self.fetch_text(url)
                    if html and 'show/' in html:
                        break
                videos.extend(self._parse_list(html)[:8])
                if len(videos) >= 24:
                    break
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            tid = str(tid or '4822')
            for url in self._list_url(tid, pg):
                html = self.fetch_text(url)
                videos = self._parse_list(html)
                if videos:
                    break
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else pg,
            'limit': 24,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            q = urllib.parse.quote(key)
            for url in (
                self.siteUrl + '/search/?keyword=' + q,
                self.siteUrl + '/search/index.html?keyword=' + q,
                self.siteUrl + '/list/4822/%s.html' % pg,
            ):
                html = self.fetch_text(url)
                items = self._parse_list(html)
                if 'search' in url:
                    videos = items
                    if videos:
                        break
                else:
                    videos = [v for v in items if key in v['vod_name']]
                    if videos:
                        break
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        name, pic, desc = vid, '', ''
        page = self.siteUrl + '/show/%s.html' % vid
        play = ''
        try:
            html = self.fetch_text(page)
            tm = re.search(r'<title>([^<]+)</title>', html or '')
            if tm:
                name = re.sub(r'\s*[-_|].*$', '', tm.group(1)).strip() or name
            hm = re.search(r'<h1[^>]*>([\s\S]{2,120})</h1>', html or '')
            if hm:
                name = self._clean(hm.group(1)) or name
            pm = re.search(
                r'(?:og:image["\']\s+content=["\']|poster=["\'])([^"\']+)',
                html or '',
            )
            if pm:
                pic = self._abs(pm.group(1))
            dm = re.search(
                r'og:description["\']\s+content=["\']([^"\']+)',
                html or '',
            )
            if dm:
                desc = dm.group(1)
            if not desc:
                cm = re.search(
                    r'class="[^"]*(?:content|article|intro)[^"]*"[^>]*>([\s\S]{20,400})</div>',
                    html or '',
                )
                if cm:
                    desc = self._clean(cm.group(1))[:400]
            play = self._extract_play(html)
            play_url = '播放$%s' % (play or page)
        except Exception as e:
            print('获取详情失败: %s' % e)
            play_url = '播放$%s' % page
        return {'list': [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '成都广播电视台',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': (desc or '').strip(),
            'vod_play_from': '看度新闻',
            'vod_play_url': play_url,
        }]}

    def playerContent(self, flag, id, vipFlags):
        # CDN 播放需带 Referer，否则可能 403
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '').strip()
        if self.isVideoFormat(play) and play.startswith('http'):
            # candocloud 等 CDN
            if 'candocloud' in play or 'cditv' in play:
                header['Referer'] = self.siteUrl + '/'
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # 详情页 id 或路径
        if not play.startswith('http'):
            if re.match(r'\d+-\d+$', play):
                play = self.siteUrl + '/show/%s.html' % play
            elif play.startswith('/'):
                play = self.siteUrl + play
            else:
                play = self.siteUrl + '/show/%s.html' % play

        html = self.fetch_text(play)
        url = self._extract_play(html)
        if url and self.isVideoFormat(url):
            return {'parse': 0, 'jx': '0', 'url': url, 'header': header}
        if url and url.startswith('http'):
            return {'parse': 1, 'jx': '1', 'url': url, 'header': header}
        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower().split('?')[0]
        return any(u.endswith(x) or ('.' + x.split('.')[-1]) in u for x in ('.mp4', '.m3u8', '.flv', '.mpd'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))

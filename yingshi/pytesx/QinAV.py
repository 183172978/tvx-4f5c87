#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QinAV Spider  — 修复播放地址提取（优先 const url / 纯 m3u8，避免命中解析站包装链）
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
    """QinAV https://www.qinav.com  18+"""

    def __init__(self):
        self.siteUrl = 'https://www.qinav.com'
        self.userAgent = (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        )
        # 分类对应 /site/5/{id}.html ，分页 /site/5/{id}-{page}.html
        self.channels = {
            'latest': {'name': '最新视频', 'path': '/'},
            'new': {'name': '最新', 'path': '/new.html'},
            'hot': {'name': '热门', 'path': '/hot.html'},
            'like': {'name': '推荐', 'path': '/like.html'},
            '1': {'name': '亚洲情色', 'path': '/site/5/1.html'},
            '2': {'name': '国产主播', 'path': '/site/5/2.html'},
            '3': {'name': '国产自拍', 'path': '/site/5/3.html'},
            '4': {'name': '无码专区', 'path': '/site/5/4.html'},
            '5': {'name': '欧美性爱', 'path': '/site/5/5.html'},
            '6': {'name': '熟女人妻', 'path': '/site/5/6.html'},
            '7': {'name': '强奸乱伦', 'path': '/site/5/7.html'},
            '8': {'name': '巨乳美乳', 'path': '/site/5/8.html'},
            '9': {'name': '中文字幕', 'path': '/site/5/9.html'},
            '10': {'name': '制服诱惑', 'path': '/site/5/10.html'},
            '11': {'name': '女同性恋', 'path': '/site/5/11.html'},
            '12': {'name': '卡通动画', 'path': '/site/5/12.html'},
            '13': {'name': '视频伦理', 'path': '/site/5/13.html'},
            '14': {'name': '少女萝莉', 'path': '/site/5/14.html'},
            '15': {'name': '重口色情', 'path': '/site/5/15.html'},
            '33': {'name': '福利姬', 'path': '/site/5/33.html'},
        }

    def getName(self):
        return 'QinAV'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None, method='GET', data=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        try:
            if requests:
                if method.upper() == 'POST':
                    resp = requests.post(url, headers=headers, data=data, timeout=15)
                else:
                    resp = requests.get(url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            req_data = None
            if data and method.upper() == 'POST':
                req_data = urllib.parse.urlencode(data).encode('utf-8')
                headers = dict(headers)
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            raw = urlopen(Request(full, data=req_data, headers=headers), timeout=15).read()

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
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _clean(self, s):
        return re.sub(r'<[^>]+>', '', str(s or '')).replace('&nbsp;', ' ').strip()

    def _parse_list(self, html):
        """解析列表页，匹配 <a href="/video/ID.html"> ... <li class="title">标题</li> 与 img img="封面" """
        videos, seen = [], set()
        if not html:
            return videos

        pattern = re.compile(
            r'<a[^>]*href="(/video/(\d+)\.html)"[^>]*>'
            r'[\s\S]*?'
            r'(?:img=["\']([^"\']+)["\']|src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\'])'
            r'[\s\S]*?'
            r'<li\s+class="title">([^<]*)</li>',
            re.I
        )
        for m in pattern.finditer(html):
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            pic = self._abs(m.group(3) or m.group(4) or '')
            title = self._clean(m.group(5)) or vid
            videos.append({
                'vod_id': path,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': vid,
            })

        if not videos:
            for m in re.finditer(r'href="(/video/(\d+)\.html)"', html or '', re.I):
                path, vid = m.group(1), m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    'vod_id': path,
                    'vod_name': vid,
                    'vod_pic': '',
                    'vod_remarks': vid,
                })
            pics = re.findall(
                r'(?:img|data-src|data-original)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
                html or '', re.I
            )
            pi = 0
            for v in videos:
                if not v['vod_pic'] and pi < len(pics):
                    p = self._abs(pics[pi])
                    if not any(x in p.lower() for x in ('logo', 'icon', 'avatar', 'loading')):
                        v['vod_pic'] = p
                    pi += 1
        return videos

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            html = self.fetch_text(self.siteUrl + '/')
            videos = self._parse_list(html)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            info = self.channels.get(str(tid), {'path': '/'})
            path = info.get('path', '/')
            if str(tid).isdigit() and path.startswith('/site/5/'):
                base_id = str(tid)
                if pg <= 1:
                    url = self.siteUrl + '/site/5/%s.html' % base_id
                else:
                    url = self.siteUrl + '/site/5/%s-%s.html' % (base_id, pg)
            elif path in ('/', '/new.html', '/hot.html', '/like.html'):
                if pg <= 1:
                    url = self.siteUrl + path
                else:
                    if path.endswith('.html'):
                        url = self.siteUrl + path.replace('.html', '-%s.html' % pg)
                    else:
                        url = self.siteUrl + '/?page=' + str(pg)
            else:
                url = self.siteUrl + path
                if pg > 1:
                    if url.endswith('.html'):
                        url = url.replace('.html', '-%s.html' % pg)
                    else:
                        url += ('&' if '?' in url else '?') + 'page=' + str(pg)

            html = self.fetch_text(url)
            videos = self._parse_list(html)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else pg,
            'limit': 24,
            'total': 5000,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            q = urllib.parse.quote(key)
            url = '%s/tags/%s.html' % (self.siteUrl, q)
            if pg > 1:
                url = '%s/tags/%s-%s.html' % (self.siteUrl, q, pg)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
            if not videos:
                resp = self.fetch(
                    self.siteUrl + '/?module=tags&action=keyword',
                    method='POST',
                    data={'keyword': key}
                )
                if resp:
                    videos = self._parse_list(getattr(resp, 'text', ''))
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def _page_url(self, vid):
        s = str(vid or '')
        if s.startswith('http'):
            return s
        if s.startswith('/'):
            return self.siteUrl + s
        if re.match(r'^\d+$', s):
            return self.siteUrl + '/video/%s.html' % s
        return self.siteUrl + '/' + s

    def _is_real_media(self, url):
        """判断是否为可直接播放的媒体地址（排除解析站包装）"""
        if not url or not url.startswith('http'):
            return False
        u = url.lower()
        if any(x in u for x in (
            '155jx.com', 'jx.', 'parse.', '?url=', '&url=', 'redirect', 'jump'
        )):
            return False
        return any(x in u for x in ('.m3u8', '.mp4', '.flv', '.mpd'))

    def _extract_play_url(self, html, vid=None):
        """
        从详情页或 embed 页提取真实 m3u8/mp4。
        优先级：
          1. const/var/let url = '真实地址'
          2. 纯 .m3u8 / .mp4 直链（不含解析站）
          3. iframe/?url= 中的真实地址
        """
        if not html:
            return ''

        # 1. JS 变量（最可靠，embed 页里有 const url = '...'）
        m = re.search(
            r"""(?:const|var|let)\s+(?:url|src|playurl|playUrl|videoUrl|hls)\s*=\s*['"](https?://[^'"]+)['"]""",
            html, re.I
        )
        if m:
            u = m.group(1).replace('\\/', '/').strip()
            um = re.search(r'[?&]url=(https?://[^&"\']+)', u)
            if um:
                return urllib.parse.unquote(um.group(1)).replace('\\/', '/')
            return u

        # 2. 纯 m3u8/mp4（排除带 ?url= 的包装）
        for m in re.finditer(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', html):
            u = m.group(0).replace('\\/', '/')
            if '?url=' in u or '&url=' in u:
                um = re.search(r'[?&]url=(https?://[^&"\']+)', u)
                if um:
                    return urllib.parse.unquote(um.group(1)).replace('\\/', '/')
                continue
            if self._is_real_media(u):
                return u

        for m in re.finditer(r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*', html):
            u = m.group(0).replace('\\/', '/')
            if '?url=' in u or '&url=' in u:
                um = re.search(r'[?&]url=(https?://[^&"\']+)', u)
                if um:
                    return urllib.parse.unquote(um.group(1)).replace('\\/', '/')
                continue
            if self._is_real_media(u):
                return u

        # 3. iframe src
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if m:
            src = m.group(1).replace('\\/', '/')
            um = re.search(r'[?&]url=(https?://[^&"\']+)', src)
            if um:
                return urllib.parse.unquote(um.group(1)).replace('\\/', '/')
            if self.isVideoFormat(src) and self._is_real_media(src):
                return self._abs(src)

        # 4. source 标签
        m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if m:
            u = self._abs(m.group(1).replace('\\/', '/'))
            if self.isVideoFormat(u):
                return u

        return ''

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        name, pic, desc = vid, '', ''
        play = ''
        try:
            page = self._page_url(vid)
            html = self.fetch_text(page)
            # 标题
            tm = re.search(r'<title>([^<]+)</title>', html or '')
            if tm:
                name = re.sub(r'\s*[-_|].*$', '', tm.group(1)).strip() or name
            hm = re.search(r'<h1[^>]*>([\s\S]{2,200})</h1>', html or '')
            if hm:
                name = self._clean(hm.group(1)) or name
            # 封面
            pm = re.search(
                r'(?:og:image["\']\s+content=["\']|poster=["\']|img=["\'])([^"\']+)',
                html or '', re.I
            )
            if pm:
                pic = self._abs(pm.group(1))
            # 简介
            dm = re.search(
                r'(?:og:description["\']\s+content=["\']|简介[:：]\s*)([^<"\']+)',
                html or '', re.I
            )
            if dm:
                desc = self._clean(dm.group(1))

            # 优先从当前页取播放地址
            play = self._extract_play_url(html, vid)

            # 无直链则访问 embed 页（关键路径）
            if not play or not self._is_real_media(play):
                em = re.search(r'(?:src|href)=["\'](/embed/\d+\.html)["\']', html or '')
                embed_path = em.group(1) if em else None
                if not embed_path:
                    idm = re.search(r'/video/(\d+)\.html', page) or re.search(r'(\d+)', str(vid))
                    if idm:
                        embed_path = '/embed/%s.html' % idm.group(1)
                if embed_path:
                    ehtml = self.fetch_text(self.siteUrl + embed_path)
                    play = self._extract_play_url(ehtml, vid) or play

            play_url = '播放$%s' % (play or page)
        except Exception as e:
            print('获取详情失败: %s' % e)
            play_url = '播放$%s' % self._page_url(vid)

        return {'list': [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '18+',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': (desc or '').strip(),
            'vod_play_from': 'QinAV',
            'vod_play_url': play_url,
        }]}

    def playerContent(self, flag, id, vipFlags):
        # 播放时带上合适的 Header，避免 CDN 拒播
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
            'Accept': '*/*',
        }
        play = str(id or '').strip()

        # 已经是纯媒体地址
        if self._is_real_media(play):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # 若是包装链，先拆出真实地址
        um = re.search(r'[?&]url=(https?://[^&"\']+)', play)
        if um:
            real = urllib.parse.unquote(um.group(1)).replace('\\/', '/')
            if self.isVideoFormat(real):
                return {'parse': 0, 'jx': '0', 'url': real, 'header': header}

        # 非直链：详情页 / embed 再解析
        page = self._page_url(play)
        html = self.fetch_text(page)
        real = self._extract_play_url(html)
        if not real or not self._is_real_media(real):
            idm = re.search(r'(\d+)', play)
            if idm:
                ehtml = self.fetch_text(self.siteUrl + '/embed/%s.html' % idm.group(1))
                real = self._extract_play_url(ehtml) or real
        if real and (self._is_real_media(real) or self.isVideoFormat(real)):
            return {'parse': 0, 'jx': '0', 'url': real, 'header': header}

        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))

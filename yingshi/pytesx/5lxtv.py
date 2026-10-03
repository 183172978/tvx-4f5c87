#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5lxtv https://18.5lxtv.com
列表: /latest /ranking /tags/...
详情: /videos/{slug}
播放: /api/play/{slug}?t=&n=  (页面内嵌 t/n)
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
    def __init__(self):
        self.siteUrl = 'https://18.5lxtv.com'
        self.hosts = ['https://18.5lxtv.com', 'https://5lxtv.com']
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # 分类互不混用
        self.channels = {
            'latest': {'name': '最新影片', 'path': '/latest'},
            'rank_all': {'name': '总排行', 'path': '/ranking?period=all'},
            'rank_week': {'name': '周排行', 'path': '/ranking?period=week'},
            'rank_month': {'name': '月排行', 'path': '/ranking?period=month'},
            'tag_cn': {'name': '中文/字幕', 'path': '/tags/' + urllib.parse.quote('中文字幕')},
            'tag_jav': {'name': '无码', 'path': '/tags/' + urllib.parse.quote('無碼')},
            'tag_amateur': {'name': '素人', 'path': '/tags/' + urllib.parse.quote('素人')},
            'tag_wife': {'name': '人妻', 'path': '/tags/' + urllib.parse.quote('人妻')},
        }

    def getName(self):
        return '5lxtv'

    def init(self, extend=""):
        if not extend:
            return
        try:
            if isinstance(extend, str) and extend.startswith('http'):
                self.siteUrl = extend.rstrip('/')
            elif isinstance(extend, str) and extend.strip().startswith('{'):
                ext = json.loads(extend)
                if ext.get('host'):
                    self.siteUrl = str(ext['host']).rstrip('/')
        except Exception:
            pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15).read()

            class R:
                def __init__(self, raw):
                    self.text = raw.decode('utf-8', 'ignore')
                    self.status_code = 200
                    self.content = raw

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_text(self, url, params=None):
        resp = self.fetch(url, params=params)
        if not resp:
            return ''
        if getattr(resp, 'status_code', 200) >= 400:
            return ''
        return getattr(resp, 'text', '') or ''

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
        """解析 /videos/{slug} 卡片：封面 alt 为标题，角标为时长"""
        videos, seen = [], set()
        for m in re.finditer(
            r'href="(/videos/([^"]+))"[\s\S]{0,500}?<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"[\s\S]{0,200}?>\s*([\d:]+)?',
            html or '',
            re.I,
        ):
            path, slug, pic, name, dur = (
                m.group(1), m.group(2), m.group(3), self._clean(m.group(4)), m.group(5) or ''
            )
            if slug in seen:
                continue
            seen.add(slug)
            videos.append({
                'vod_id': path,
                'vod_name': name or slug,
                'vod_pic': self._abs(pic),
                'vod_remarks': dur or '18+',
            })
        if videos:
            return videos
        # 宽松：仅 path + alt
        for m in re.finditer(
            r'href="(/videos/([^"]+))"[\s\S]{0,400}?alt="([^"]*)"',
            html or '',
            re.I,
        ):
            path, slug, name = m.group(1), m.group(2), self._clean(m.group(3))
            if slug in seen:
                continue
            seen.add(slug)
            videos.append({
                'vod_id': path,
                'vod_name': name or slug,
                'vod_pic': '',
                'vod_remarks': '18+',
            })
        return videos

    def _list_url(self, path, pg=1):
        pg = int(pg or 1)
        url = path if path.startswith('http') else self.siteUrl + path
        if pg > 1:
            url += ('&' if '?' in url else '?') + 'page=' + str(pg)
        return url

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            html = self.fetch_text(self.siteUrl + '/latest')
            videos = self._parse_list(html)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            info = self.channels.get(str(tid), {'path': '/latest'})
            url = self._list_url(info.get('path', '/latest'), pg)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
            # 标签页可能较少，回退最新
            if not videos and str(tid).startswith('tag_'):
                html = self.fetch_text(self._list_url('/latest', pg))
                videos = self._parse_list(html)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 30,
            'total': 9999 if len(videos) >= 12 else len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            q = urllib.parse.quote(str(key or ''))
            url = '%s/search?q=%s&page=%s' % (self.siteUrl, q, pg)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
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
        if s.startswith('videos/'):
            return self.siteUrl + '/' + s
        return self.siteUrl + '/videos/' + s

    def _extract_play_api(self, html, slug=''):
        """从详情页提取 /api/play/{slug}?t=&n="""
        m = re.search(
            r'var\s+slug\s*=\s*"([^"]+)"\s*;\s*var\s+t\s*=\s*(\d+)\s*;\s*var\s+n\s*=\s*"([^"]+)"',
            html or '',
        )
        if m:
            return m.group(1), m.group(2), m.group(3)
        m = re.search(
            r"/api/play/'?\+?encodeURIComponent\(([^)]+)\)[^']*'?\?t='\s*\+\s*(\w+)\s*\+\s*'&n='\s*\+\s*encodeURIComponent\((\w+)\)",
            html or '',
        )
        # 直接匹配 base 赋值
        m2 = re.search(
            r"base\s*=\s*'/api/play/'\s*\+\s*encodeURIComponent\(slug\)\s*\+\s*'\?t='\s*\+\s*t\s*\+\s*'&n='\s*\+\s*encodeURIComponent\(n\)",
            html or '',
        )
        m3 = re.search(r'var\s+t\s*=\s*(\d+)\s*;\s*var\s+n\s*=\s*"([^"]+)"', html or '')
        if m3 and slug:
            return slug, m3.group(1), m3.group(2)
        if m:
            return slug, '', ''
        return slug, '', ''

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        name, pic, desc = vid, '', ''
        play_url = ''
        try:
            page = self._page_url(vid)
            html = self.fetch_text(page)
            tm = re.search(r'<title>([^<]+)</title>', html or '')
            if tm:
                name = re.sub(r'\s*[-_|].*5lxtv.*$', '', tm.group(1), flags=re.I).strip() or name
            hm = re.search(r'<h1[^>]*>([\s\S]{2,200})</h1>', html or '')
            if hm:
                name = self._clean(hm.group(1)) or name
            pm = re.search(
                r'(?:og:image["\']\s+content=["\']|poster=["\'])([^"\']+)',
                html or '',
            )
            if pm:
                pic = self._abs(pm.group(1))
            if not pic:
                im = re.search(r'content-cover/([^"\'>\s]+)', html or '')
                if im:
                    pic = self.siteUrl + '/content-cover/' + im.group(1)
            dm = re.search(r'og:description["\']\s+content=["\']([^"\']+)', html or '')
            if dm:
                desc = dm.group(1)

            slug = ''
            if '/videos/' in page:
                slug = page.rstrip('/').split('/videos/')[-1].split('?')[0]
            elif vid.startswith('/videos/'):
                slug = vid.split('/videos/')[-1]
            else:
                slug = re.sub(r'^/+', '', vid)

            s, t, n = self._extract_play_api(html, slug)
            if s and t and n:
                # 播放 token 存进 play id，playerContent 再拼
                play_url = '播放$play:%s|%s|%s' % (s, t, n)
            else:
                # 直接页面上的 m3u8
                m3 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html or '')
                if m3:
                    play_url = '播放$%s' % m3.group(0).replace('\\/', '/')
                else:
                    play_url = '播放$%s' % page
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
            'vod_play_from': '5lxtv',
            'vod_play_url': play_url,
        }]}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '')
        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # play:slug|t|n
        if play.startswith('play:'):
            body = play[5:]
            parts = body.split('|')
            if len(parts) >= 3:
                slug, t, n = parts[0], parts[1], parts[2]
                api = '%s/api/play/%s?t=%s&n=%s&hls=1' % (
                    self.siteUrl,
                    urllib.parse.quote(slug),
                    t,
                    urllib.parse.quote(n),
                )
                # 返回可被播放器拉取的 m3u8 接口（需带 Referer）
                return {'parse': 0, 'jx': '0', 'url': api, 'header': header}

        page = self._page_url(play)
        html = self.fetch_text(page)
        slug = ''
        if '/videos/' in page:
            slug = page.rstrip('/').split('/videos/')[-1].split('?')[0]
        s, t, n = self._extract_play_api(html, slug)
        if s and t and n:
            api = '%s/api/play/%s?t=%s&n=%s&hls=1' % (
                self.siteUrl, urllib.parse.quote(s), t, urllib.parse.quote(n)
            )
            return {'parse': 0, 'jx': '0', 'url': api, 'header': header}

        m = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', html or '')
        if m:
            return {'parse': 0, 'jx': '0', 'url': m.group(0).replace('\\/', '/'), 'header': header}
        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        if any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd')):
            return True
        if '/api/play/' in u:
            return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    r = spider.categoryContent('latest', 1, {}, {})
    print('list', len(r['list']), r['list'][0] if r['list'] else None)
    if r['list']:
        d = spider.detailContent([r['list'][0]['vod_id']])
        print('detail', d['list'][0]['vod_name'][:40], d['list'][0]['vod_play_url'][:80])
        token = d['list'][0]['vod_play_url'].split('$')[-1]
        print(json.dumps(spider.playerContent('5lxtv', token, []), ensure_ascii=False)[:250])

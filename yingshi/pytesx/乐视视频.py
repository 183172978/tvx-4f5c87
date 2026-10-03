#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐视视频 https://www.le.com / https://lefun.le.com
分类：so.le.com 关键词搜索 + 首页推荐
播放：详情页直链 / playJson（若可用）/ 网页解析
"""
import json
import re
import ssl
import sys
import time
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
    """乐视视频"""

    def __init__(self):
        self.siteUrl = 'https://www.le.com'
        self.funUrl = 'https://lefun.le.com'
        self.soUrl = 'https://so.le.com'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # type_id -> 搜索关键词（list API / list.le.com 已不可用）
        self.channels = {
            'movie': {'name': '电影', 'kw': '电影'},
            'tv': {'name': '电视剧', 'kw': '电视剧'},
            'anime': {'name': '动漫', 'kw': '动漫'},
            'variety': {'name': '综艺', 'kw': '综艺'},
            'doc': {'name': '纪录片', 'kw': '纪录片'},
            'sport': {'name': '体育', 'kw': '体育'},
            'hot': {'name': '热播', 'kw': '热播'},
        }
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def getName(self):
        return '乐视视频'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        try:
            if requests:
                resp = requests.get(
                    url, headers=headers, params=params, timeout=15, verify=False
                )
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15, context=self._ssl_ctx).read()

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

    def fetch_json(self, url, params=None):
        resp = self.fetch(url, params=params)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            text = getattr(resp, 'text', '') or ''
            m = re.search(r'(\{[\s\S]+\}|\[[\s\S]+\])', text)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    return {}
            return {}

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip()
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u.replace('http://', 'https://')

    def _clean(self, s):
        return re.sub(r'<[^>]+>', '', str(s or '')).replace('&nbsp;', ' ').strip()

    def _bad_name(self, name):
        if not name or len(name) < 2:
            return True
        bad = ('播放', '立即开通', '会员', '登录', '注册', '更多', '分享', '下载', '收藏')
        return any(b in name for b in bad)

    def _parse_list(self, html):
        """从首页/搜索页解析 /ptv/vplay/{id}.html"""
        videos, seen = [], set()
        # 链接文字
        for m in re.finditer(
            r'/ptv/vplay/(\d+)\.html[^>]*>\s*([^<]{2,60})',
            html or '',
        ):
            vid, name = m.group(1), self._clean(m.group(2))
            if vid in seen or self._bad_name(name):
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '乐视',
            })
        # title/alt
        for m in re.finditer(
            r'href="[^"]*?/ptv/vplay/(\d+)\.html"[^>]{0,280}(?:title|alt)="([^"]{2,80})"',
            html or '',
            re.I,
        ):
            vid, name = m.group(1), self._clean(m.group(2))
            if vid in seen or self._bad_name(name):
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '乐视',
            })
        # 补封面
        for m in re.finditer(
            r'/ptv/vplay/(\d+)\.html[\s\S]{0,400}?(?:src|data-src|data-original)="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
            html or '',
            re.I,
        ):
            for v in videos:
                if v['vod_id'] == m.group(1) and not v['vod_pic']:
                    v['vod_pic'] = self._abs(m.group(2))
                    break
        for m in re.finditer(
            r'(?:src|data-src)="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"[^>]{0,200}/ptv/vplay/(\d+)',
            html or '',
            re.I,
        ):
            for v in videos:
                if v['vod_id'] == m.group(2) and not v['vod_pic']:
                    v['vod_pic'] = self._abs(m.group(1))
                    break
        return videos

    def _search_kw(self, kw, pg=1):
        q = urllib.parse.quote(str(kw or ''))
        urls = [
            '%s/s?wd=%s' % (self.soUrl, q),
            '%s/s?wd=%s&from=pc' % (self.soUrl, q),
            '%s/s?wd=%s&page=%s' % (self.soUrl, q, pg),
        ]
        videos = []
        for url in urls:
            html = self.fetch_text(url)
            videos = self._parse_list(html)
            if videos:
                break
        return videos

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            for base in (self.siteUrl + '/', self.funUrl + '/'):
                html = self.fetch_text(base)
                videos = self._parse_list(html)
                if videos:
                    break
            if not videos:
                videos = self._search_kw('热播', 1)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            info = self.channels.get(str(tid), {'kw': str(tid) or '热播'})
            kw = info.get('kw') or str(tid)
            if str(tid) == 'hot' or kw == '热播':
                html = self.fetch_text(self.siteUrl + '/')
                videos = self._parse_list(html)
            if not videos:
                videos = self._search_kw(kw, pg)
            # 首页补充
            if not videos and pg == 1:
                html = self.fetch_text(self.siteUrl + '/')
                videos = self._parse_list(html)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 8 else pg,
            'limit': 30,
            'total': 9999 if len(videos) >= 8 else len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            videos = self._search_kw(key, pg)
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
        vid = re.sub(r'\D', '', vid) or vid
        name, pic, desc = vid, '', ''
        page = '%s/ptv/vplay/%s.html' % (self.siteUrl, vid)
        try:
            html = self.fetch_text(page)
            tm = re.search(r'<title>([^<]+)</title>', html or '')
            if tm:
                name = re.sub(r'\s*[-_|].*$', '', tm.group(1)).strip() or name
            hm = re.search(r'<h1[^>]*>([\s\S]{2,80})</h1>', html or '')
            if hm:
                name = self._clean(hm.group(1)) or name
            pm = re.search(
                r'(?:og:image["\']\s+content=["\']|poster=["\'])([^"\']+)',
                html or '',
            )
            if pm:
                pic = self._abs(pm.group(1))
            if not pic:
                im = re.search(
                    r'(https?://i\d*\.letvimg\.com/[^"\']+\.(?:jpg|png|webp)[^"\']*)',
                    html or '',
                    re.I,
                )
                if im:
                    pic = self._abs(im.group(1))
            dm = re.search(r'og:description["\']\s+content=["\']([^"\']+)', html or '')
            if dm:
                desc = dm.group(1)
            # 选集
            parts = []
            seen = set()
            for m in re.finditer(r'/ptv/vplay/(\d+)\.html[^>]*>\s*([^<]{1,20})', html or ''):
                eid, en = m.group(1), self._clean(m.group(2))
                if eid in seen or self._bad_name(en):
                    continue
                if re.match(r'^\d+$', en) or '集' in en or eid == vid:
                    seen.add(eid)
                    parts.append('%s$%s' % (en if en else ('第%s集' % len(parts) + 1), eid))
            if not parts:
                parts = ['播放$%s' % vid]
            play_url = '#'.join(parts)
        except Exception as e:
            print('获取详情失败: %s' % e)
            play_url = '播放$%s' % vid
        return {'list': [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '乐视',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': (desc or '').strip(),
            'vod_play_from': '乐视',
            'vod_play_url': play_url,
        }]}

    def _play_json(self, vid):
        """尝试历史 playJson 接口"""
        tkey = str(int(time.time()))
        bases = [
            'https://player-pc.le.com/mms/out/video/playJson.json',
        ]
        variants = [
            {'platid': '1', 'splatid': '101', 'tss': 'ios', 'dvtype': '1000', 'domain': 'm.le.com'},
            {'platid': '3', 'splatid': '304', 'tss': 'no', 'dvtype': '1300', 'domain': 'www.le.com'},
            {'platid': '3', 'splatid': '301', 'tss': 'no', 'dvtype': '1000', 'domain': 'www.le.com'},
        ]
        for base in bases:
            for v in variants:
                params = dict(v)
                params.update({'id': vid, 'detect': '1', 'tkey': tkey})
                js = self.fetch_json(base, params=params)
                if not isinstance(js, dict) or js.get('code') == -1:
                    continue
                playurl = (js.get('msgs') or {}).get('playurl') or js.get('playurl') or {}
                if not isinstance(playurl, dict):
                    continue
                dispatch = playurl.get('dispatch') or {}
                domain = playurl.get('domain') or ['']
                if isinstance(domain, list):
                    domain = domain[0] if domain else ''
                path = ''
                if isinstance(dispatch, dict) and dispatch:
                    path = list(dispatch.values())[0]
                    if isinstance(path, list):
                        path = path[0]
                if domain and path:
                    url = str(domain) + str(path)
                    if not url.startswith('http'):
                        url = 'https:' + url
                    return url
        return ''

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '')
        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        vid = re.search(r'(\d{5,})', play)
        vid = vid.group(1) if vid else play
        if play.isdigit() or (not play.startswith('http')):
            play = '%s/ptv/vplay/%s.html' % (self.siteUrl, vid)

        # playJson
        url = self._play_json(vid)
        if url:
            return {'parse': 0, 'jx': '0', 'url': url, 'header': header}

        html = self.fetch_text(play) if play.startswith('http') else ''
        m = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', html or '')
        if m:
            return {'parse': 0, 'jx': '0', 'url': m.group(0).replace('\\/', '/'), 'header': header}

        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

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
    print('--- category movie ---')
    r = spider.categoryContent('movie', 1, {}, {})
    print(json.dumps(r, ensure_ascii=False)[:800])

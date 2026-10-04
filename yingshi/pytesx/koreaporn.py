# -*- coding: utf-8 -*-
# KoreaPorn https://koreaporn.net/
# 列表 /id/{id}/...  播放经 e.xv-cdn / webproxy → xvideos embedframe 抽 mp4/hls
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


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://koreaporn.net'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        )
        self.proxy_api = 'https://s2.webproxy.click/api/'
        self.channels = {
            'new': {'name': '最新', 'path': '/new/'},
            'best': {'name': '最佳', 'path': '/best/'},
            'hits': {'name': '热门', 'path': '/hits/'},
            'korean': {'name': '韩国', 'path': '/tag/korean/'},
            'korea': {'name': 'Korea', 'path': '/tag/korea/'},
            'korean_sex': {'name': '韩国性爱', 'path': '/tag/korean-sex/'},
            'korean_movie': {'name': '韩国电影', 'path': '/tag/korean-movie/'},
            'hanguk': {'name': '한국', 'path': '/tag/한국/'},
            'japanese': {'name': '日本无码', 'path': '/tag/japanese-日本-無修正-高画質/'},
            'jav': {'name': 'JAV无码', 'path': '/tag/jav-uncensored/'},
            'uncensored': {'name': '无码', 'path': '/tag/uncensored/'},
            'japanese2': {'name': '日本', 'path': '/tag/japanese/'},
            'blonde': {'name': '金发', 'path': '/tag/blonde/'},
            'bigtits': {'name': '大胸', 'path': '/tag/big-tits/'},
            'asian': {'name': '亚洲', 'path': '/tag/asian/'},
            'amateur': {'name': '素人', 'path': '/tag/amateur/'},
            'stockings': {'name': '丝袜', 'path': '/tag/stockings/'},
            'pantyhose': {'name': '连裤袜', 'path': '/tag/pantyhose/'},
        }
        self.name_to_id = {}
        for k, v in self.channels.items():
            self.name_to_id[k] = k
            self.name_to_id[v['name']] = k

    def getName(self):
        return 'KoreaPorn'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass

    def _headers(self, referer=None):
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or (self.host + '/'),
        }

    def _get(self, url, referer=None):
        try:
            headers = self._headers(referer)
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=headers, timeout=25, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('GET error', url, e)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/').replace('&amp;', '&')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        if not u.startswith('http'):
            return self.host + '/' + u
        return u

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'<a[^>]+class="[^"]*item_a[^"]*"[^>]+href="(/id/(\d+)/[^"?\s]+)(?:\?[^"]*)?"[^>]*(?:title="([^"]*)")?',
            html, re.I
        ):
            path, vid, title = m.group(1), m.group(2), (m.group(3) or '').strip()
            full = self._abs(path)
            if full in seen:
                continue
            seen.add(full)
            block = html[max(0, m.start() - 50):m.end() + 600]
            if not title:
                tm = re.search(r'(?:title|alt)="([^"]{3,200})"', block)
                title = tm.group(1).strip() if tm else vid
            pic = ''
            pm = re.search(r'<img[^>]+(?:data-src|src)="(https?://[^"]+)"', block, re.I)
            if pm and not re.search(r'flag|logo|icon|svg', pm.group(1), re.I):
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'<img[^>]+(?:data-src|src)="(/[^"]+)"', block, re.I)
                if pm:
                    pic = self._abs(pm.group(1))
            tips = ''
            dm = re.search(r'(\d+:\d+|\d+\s*min)', block, re.I)
            if dm:
                tips = dm.group(1)
            videos.append({
                'vod_id': full,
                'vod_name': title[:120],
                'vod_pic': pic,
                'vod_remarks': tips,
            })
        if not videos:
            for m in re.finditer(r'href="(/id/(\d+)/[^"?\s]+)(?:\?[^"]*)?"', html):
                path, vid = m.group(1), m.group(2)
                full = self._abs(path)
                if full in seen:
                    continue
                seen.add(full)
                block = html[max(0, m.start() - 100):m.end() + 400]
                title = ''
                tm = re.search(r'(?:title|alt)="([^"]{3,200})"', block)
                if tm:
                    title = tm.group(1).strip()
                pic = ''
                pm = re.search(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I)
                if pm:
                    pic = pm.group(1)
                videos.append({
                    'vod_id': full,
                    'vod_name': title or vid,
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
        return videos

    def _extract_vid(self, url_or_html):
        m = re.search(r'/id/(\d+)', str(url_or_html))
        if m:
            return m.group(1)
        m = re.search(r'/embed/(\d+)', str(url_or_html))
        if m:
            return m.group(1)
        return ''

    def _play_from_xvideos(self, vid):
        """通过 webproxy 拉 xvideos embedframe，解析清晰度"""
        plays = []
        if not vid:
            return plays
        api = self.proxy_api + 'www.xvideos.com/embedframe/' + vid
        html = self._get(api, referer='https://e.xv-cdn.net/?id=' + vid)
        if not html:
            return plays
        seen = set()

        def add(name, u):
            if not u or u in seen or not u.startswith('http'):
                return
            seen.add(u)
            plays.append((name, u))

        for label, pat in (
            ('1080P', r"setVideoUrlHigh\(['\"]([^'\"]+)"),
            ('720P', r"setVideoUrlLow\(['\"]([^'\"]+)"),
            ('HLS', r"setVideoHLS\(['\"]([^'\"]+)"),
            ('MP4-H', r"html5player\.setVideoUrlHigh\(['\"]([^'\"]+)"),
            ('MP4-L', r"html5player\.setVideoUrlLow\(['\"]([^'\"]+)"),
            ('HLS2', r"html5player\.setVideoHLS\(['\"]([^'\"]+)"),
        ):
            for m in re.finditer(pat, html):
                add(label, m.group(1).replace('\\/', '/'))
        if not plays:
            for u in re.findall(r'https?://[^\"\'\s<>]+\.(?:mp4|m3u8)[^\"\'\s<>]*', html):
                if 'preview' not in u.lower():
                    add('直链', u.replace('\\/', '/'))
        # 去重按清晰度名保留一条
        best = {}
        order = {'HLS': 0, 'HLS2': 0, '1080P': 1, 'MP4-H': 1, '720P': 2, 'MP4-L': 2, '直链': 3}
        for name, u in plays:
            key = name
            if key not in best:
                best[key] = u
        result = sorted(best.items(), key=lambda x: order.get(x[0], 9))
        return result

    def _resolve_tid(self, tid):
        s = str(tid or 'new').strip()
        if s in self.channels:
            return s
        if s in self.name_to_id:
            return self.name_to_id[s]
        return 'new'

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        html = self._get(self.host + '/new/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = self._resolve_tid(tid)
        info = self.channels.get(tid) or self.channels['new']
        path = info['path']
        if pg <= 1:
            url = self.host + path
        else:
            # /new/2/  /tag/xxx/2/
            if path.endswith('/'):
                url = self.host + path + str(pg) + '/'
            else:
                url = self.host + path + '/' + str(pg) + '/'
        html = self._get(url)
        videos = self._parse_list(html)
        pagecount = pg + 1 if len(videos) >= 12 else pg
        return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 24, 'total': 9999}

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        page_url = str(ids[0])
        if not page_url.startswith('http'):
            page_url = self._abs(page_url)
        html = self._get(page_url)
        name = ''
        m = re.search(r'<title>([^<]+)</title>', html or '', re.I)
        if m:
            name = re.sub(r'\s*[-|].*KoreaPorn.*$', '', m.group(1), flags=re.I).strip()
        if not name:
            m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html or '', re.I)
            if m:
                name = m.group(1).strip()
        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html or '', re.I)
        if m:
            pic = self._abs(m.group(1))

        vid = self._extract_vid(page_url)
        if not vid and html:
            vid = self._extract_vid(html)
        plays = self._play_from_xvideos(vid)

        if plays:
            # 多线路清晰度
            play_from = '$$$'.join([n for n, _ in plays])
            play_url = '$$$'.join(['正片$%s' % u for _, u in plays])
        else:
            # 兜底：embed / player 页交给 playerContent
            play_from = 'KoreaPorn'
            play_url = '正片$%s' % (self.host + '/embed/' + vid + '/' if vid else page_url)

        result['list'] = [{
            'vod_id': page_url,
            'vod_name': name or 'KoreaPorn',
            'vod_pic': pic,
            'vod_remarks': plays[0][0] if plays else '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': play_from,
            'vod_play_url': play_url,
        }]
        return result

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        # 站内 /find 多为骨架，改走 xvideos 搜索代理，ID 映射到 /id/{id}/
        videos = []
        seen = set()
        api = self.proxy_api + 'www.xvideos.com/?k=' + quote(key)
        if pg > 1:
            api = self.proxy_api + 'www.xvideos.com/?k=' + quote(key) + '&p=' + str(pg - 1)
        html = self._get(api, referer='https://www.xvideos.com/')
        if html:
            for m in re.finditer(
                r'data-id="(\d+)"[\s\S]{0,500}?title="([^"]{3,200})"',
                html, re.I
            ):
                vid, title = m.group(1), m.group(2).replace('&#039;', "'").strip()
                if vid in seen:
                    continue
                seen.add(vid)
                block = html[m.start():m.start() + 500]
                pic = ''
                pm = re.search(r'data-src="(https?://[^"]+)"', block)
                if not pm:
                    pm = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I)
                if pm:
                    pic = pm.group(1)
                videos.append({
                    'vod_id': self.host + '/id/%s/' % vid,
                    'vod_name': title[:120],
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
            if not videos:
                for m in re.finditer(r'data-id="(\d+)"', html):
                    vid = m.group(1)
                    if vid in seen:
                        continue
                    seen.add(vid)
                    videos.append({
                        'vod_id': self.host + '/id/%s/' % vid,
                        'vod_name': vid,
                        'vod_pic': '',
                        'vod_remarks': '',
                    })
        # 兜底：尝试标签页
        if not videos:
            tag_url = self.host + '/tag/' + quote(key) + '/'
            videos = self._parse_list(self._get(tag_url))
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def playerContent(self, flag, id, vipFlags):
        play = str(id or '').strip()
        header = {
            'User-Agent': self.ua,
            'Referer': 'https://www.xvideos.com/',
            'Origin': 'https://www.xvideos.com',
            'Accept': '*/*',
        }
        if play.startswith('//'):
            play = 'https:' + play
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}
        vid = self._extract_vid(play)
        if vid:
            plays = self._play_from_xvideos(vid)
            if plays:
                return {'parse': 0, 'jx': 0, 'url': plays[0][1], 'header': header}
        if '/id/' in play or '/embed/' in play:
            html = self._get(play, referer=self.host + '/')
            vid = self._extract_vid(play) or self._extract_vid(html or '')
            plays = self._play_from_xvideos(vid)
            if plays:
                return {'parse': 0, 'jx': 0, 'url': plays[0][1], 'header': header}
        return {'parse': 0, 'jx': 0, 'url': '', 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    r = sp.categoryContent('new', 1, False, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        print('sample', r['list'][0]['vod_name'][:40], r['list'][0]['vod_id'][:60])
        d = sp.detailContent([r['list'][0]['vod_id']])
        item = d['list'][0] if d.get('list') else {}
        print('from', item.get('vod_play_from'))
        print('url', (item.get('vod_play_url') or '')[:200])
        if item.get('vod_play_url'):
            u = item['vod_play_url'].split('$$$')[0].split('$')[-1]
            p = sp.playerContent('720P', u, [])
            print('player', (p.get('url') or '')[:90], p.get('parse'))

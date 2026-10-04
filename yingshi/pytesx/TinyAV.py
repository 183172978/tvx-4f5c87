# -*- coding: utf-8 -*-
# TinyAV https://tinyavideo.com  v1.1
# 修复：分类加载慢/失败、无播放地址、列表标题封面、清晰度
import re
import json
import sys
import ssl
import http.cookiejar
from urllib.parse import quote, urljoin
from urllib.request import Request, build_opener, HTTPSHandler, HTTPCookieProcessor

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

VERSION = '1.1.0'


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://tinyavideo.com'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        # type_id -> path（均为站点有效路径）
        self.channels = [
            {'type_id': 'jp-new', 'type_name': '日本·最近更新', 'path': '/japanese/new'},
            {'type_id': 'japanese', 'type_name': '日本·最新發行', 'path': '/japanese/release'},
            {'type_id': 'jp-hot', 'type_name': '日本·今日熱門', 'path': '/japanese/today-hot'},
            {'type_id': 'asian', 'type_name': '亞洲·最新發行', 'path': '/asian/release'},
            {'type_id': 'asian-new', 'type_name': '亞洲·最近更新', 'path': '/asian/new'},
            {'type_id': 'uncensored', 'type_name': '無碼流出', 'path': '/uncensored-leak/release'},
            {'type_id': 'uc-hot', 'type_name': '無碼·今日熱門', 'path': '/uncensored-leak/today-hot'},
            {'type_id': 'fc2', 'type_name': 'FC2', 'path': '/fc2/release'},
            {'type_id': 'fc2-hot', 'type_name': 'FC2·今日熱門', 'path': '/fc2/today-hot'},
            {'type_id': 'chinese', 'type_name': '中文字幕', 'path': '/chinese-subtitles'},
            {'type_id': 'hentai', 'type_name': '動畫H', 'path': '/hentai/release'},
            {'type_id': 'western', 'type_name': '歐美', 'path': '/western/release'},
            {'type_id': 'korean', 'type_name': '韓國', 'path': '/korean/release'},
        ]
        self._channel_map = {c['type_id']: c for c in self.channels}
        self._opener = None

    def getName(self):
        return 'TinyAV'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self._opener = build_opener(
            HTTPCookieProcessor(http.cookiejar.CookieJar()),
            HTTPSHandler(context=ctx),
        )

    def _headers(self, referer=None):
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'identity',
            'Referer': referer or (self.host + '/'),
            'Connection': 'close',
        }

    def _get(self, url, referer=None, timeout=12):
        """统一请求：短超时，避免部分壳卡死；失败返回空串"""
        try:
            if self._opener is None:
                self.init()
            req = Request(url, headers=self._headers(referer), method='GET')
            with self._opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    return raw.decode('utf-8')
                except UnicodeDecodeError:
                    return raw.decode('utf-8', 'ignore')
        except Exception as e:
            print('GET error', url, e, file=sys.stderr)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        if not u.startswith('http'):
            return urljoin(self.host + '/', u)
        return u

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        # 优先：卡片结构 videotitle + 封面
        for m in re.finditer(
            r'href="(/video/[^"?#]+)"[^>]*>\s*<img[^>]+(?:src|data-src)="([^"]+)"[^>]*alt="([^"]*)"',
            html, re.I
        ):
            href, pic, alt = m.group(1), m.group(2), m.group(3).strip()
            if href in seen:
                continue
            seen.add(href)
            title = alt or href.rstrip('/').split('/')[-1]
            videos.append({
                'vod_id': href,
                'vod_name': title[:120],
                'vod_pic': self._abs(pic),
                'vod_remarks': '',
            })

        # 补充：任意 /video/ 链接 + 邻近标题封面
        if len(videos) < 6:
            for m in re.finditer(r'href="(/video/[^"?#]+)"', html):
                href = m.group(1)
                if href in seen:
                    continue
                seen.add(href)
                block = html[max(0, m.start() - 200):m.start() + 700]
                title = ''
                tm = re.search(r'class="videotitle"[^>]*>\s*<a[^>]*>([^<]+)', block, re.I)
                if not tm:
                    tm = re.search(r'alt="([^"]{3,150})"', block)
                if not tm:
                    tm = re.search(r'hreflang="[^"]*">([^<]{3,120})<', block)
                if tm:
                    title = tm.group(1).strip()
                if not title:
                    title = href.rstrip('/').split('/')[-1].replace('-', ' ')
                pic = ''
                pm = re.search(
                    r'(?:src|data-src)="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    block, re.I
                )
                if pm:
                    pic = self._abs(pm.group(1))
                videos.append({
                    'vod_id': href,
                    'vod_name': title[:120],
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
        return videos

    def homeContent(self, filter):
        classes = [{'type_id': c['type_id'], 'type_name': c['type_name']} for c in self.channels]
        # 不在 home 里拉列表，加快部分壳的分类展示
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        try:
            html = self._get(self.host + '/japanese/new', timeout=10)
            return {'list': self._parse_list(html)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'japanese')
        info = self._channel_map.get(tid) or self._channel_map.get('japanese')
        path = info.get('path', '/japanese/release')
        if pg <= 1:
            url = self.host + path
        else:
            sep = '&' if '?' in path else '?'
            url = self.host + path + sep + 'page=%d' % pg
        html = self._get(url, timeout=12)
        videos = self._parse_list(html)
        pagecount = pg
        if len(videos) >= 8:
            pagecount = pg + 1
        # Drupal 风格页码
        mx = [int(x) for x in re.findall(r'[?&]page=(\d+)', html) if x.isdigit()]
        if mx:
            try:
                pagecount = max(pagecount, max(x for x in mx if x < 50000) + 1)
            except Exception:
                pass
        if '下一' in html or 'pager__item--next' in html:
            pagecount = max(pagecount, pg + 1)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': pagecount * 12,
        }

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        vid = str(ids[0])
        page_url = vid if vid.startswith('http') else self._abs(vid)
        html = self._get(page_url, referer=self.host + '/', timeout=15)
        if not html:
            return result

        name = ''
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if m:
            name = m.group(1).strip()
        if not name:
            m = re.search(r'<title>([^<]+)</title>', html)
            if m:
                name = re.sub(r'\s*[|｜\-].*$', '', m.group(1)).strip()

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
        if not m:
            m = re.search(r'<video[^>]+poster=["\']([^"\']+)["\']', html, re.I)
        if m:
            pic = self._abs(m.group(1))

        desc = ''
        m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            desc = m.group(1).strip()[:500]

        play_urls = []
        m3u8s = self._extract_plays(html)
        if m3u8s:
            # 主清单再展开清晰度
            labeled = []
            for u in m3u8s:
                variants = self._fetch_m3u8_variants(u)
                if variants:
                    labeled.extend(variants)
                else:
                    lab = '1080P' if '1080' in u else ('720P' if '720' in u else 'HLS')
                    labeled.append((lab, u))
            # 去重保序
            seen = set()
            for lab, u in labeled:
                if u in seen:
                    continue
                seen.add(u)
                play_urls.append('%s$%s' % (lab, u))
        if not play_urls:
            play_urls.append('網頁播放$%s' % page_url)

        vod = {
            'vod_id': vid,
            'vod_name': name or '影片',
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': 'TinyAV',
            'vod_play_url': '#'.join(play_urls),
        }
        result['list'] = [vod]
        return result

    def _extract_plays(self, html):
        urls = []
        seen = set()

        def add(u):
            u = (u or '').strip().replace('\\/', '/').replace('\\u0026', '&')
            if not u or u in seen:
                return
            if not u.startswith('http'):
                return
            seen.add(u)
            urls.append(u)

        # window.m3u8List = ["..."]
        m = re.search(r'window\.m3u8List\s*=\s*(\[[\s\S]*?\]);', html)
        if m:
            for um in re.finditer(r'"(https?://[^"]+)"', m.group(1)):
                add(um.group(1))

        # JSON-LD contentUrl
        for m in re.finditer(r'"contentUrl"\s*:\s*"(https?://[^"]+)"', html):
            add(m.group(1))

        # 裸 m3u8 / mp4
        for m in re.finditer(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', html, re.I):
            add(m.group(1))
        for m in re.finditer(r'(https?://[^\s"\'<>]+?\.mp4[^\s"\'<>]*)', html, re.I):
            u = m.group(1)
            if 'ad' not in u.lower() and 'banner' not in u.lower():
                add(u)
        return urls

    def _fetch_m3u8_variants(self, master_url):
        variants = []
        try:
            text = self._get(master_url, referer=self.host + '/', timeout=8)
            if not text or '#EXTM3U' not in text:
                return variants
            # 已是媒体清单
            if '#EXT-X-STREAM-INF' not in text:
                return variants
            lines = text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXT-X-STREAM-INF:'):
                    res = re.search(r'RESOLUTION=\d+x(\d+)', line, re.I)
                    bw = re.search(r'BANDWIDTH=(\d+)', line, re.I)
                    label = 'HLS'
                    if res:
                        h = int(res.group(1))
                        label = '1080P' if h >= 1080 else ('720P' if h >= 720 else ('480P' if h >= 480 else '%dP' % h))
                    elif bw:
                        b = int(bw.group(1))
                        label = '1080P' if b >= 3000000 else ('720P' if b >= 1500000 else '480P')
                    if i + 1 < len(lines):
                        u = lines[i + 1].strip()
                        if u and not u.startswith('#'):
                            if not u.startswith('http'):
                                u = urljoin(master_url, u)
                            variants.append((label, u))
                i += 1
        except Exception:
            pass
        # 高清优先
        order = {'1080P': 0, '720P': 1, '480P': 2, 'HLS': 3}
        variants.sort(key=lambda x: order.get(x[0], 9))
        return variants

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        url = self.host + '/search?fulltext=' + quote(key)
        if pg > 1:
            url += '&page=%d' % pg
        html = self._get(url, timeout=12)
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            # CDN 可能校验 Referer
            if 'cdn2020' in play or 'cdn202' in play:
                header['Referer'] = self.host + '/'
            return {'parse': 0, 'url': play, 'header': header}
        if play.startswith('http'):
            html = self._get(play, timeout=12)
            plays = self._extract_plays(html)
            if plays:
                return {'parse': 0, 'url': plays[0], 'header': header}
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}
        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('VERSION', VERSION)
    print('classes', [c['type_name'] for c in sp.homeContent(False)['class']])
    hv = sp.homeVideoContent()
    print('homeVod', len(hv.get('list') or []))
    for tid in ['japanese', 'uncensored', 'chinese', 'fc2']:
        c = sp.categoryContent(tid, 1, False, {})
        print(tid, 'n=', len(c.get('list') or []),
              [x['vod_name'][:28] for x in (c.get('list') or [])[:2]])
    c = sp.categoryContent('japanese', 1, False, {})
    if c.get('list'):
        d = sp.detailContent([c['list'][0]['vod_id']])
        print('detail', (d['list'][0]['vod_name'][:40] if d.get('list') else None))
        print('play', (d['list'][0].get('vod_play_url') or '')[:150] if d.get('list') else None)
        if d.get('list') and d['list'][0].get('vod_play_url'):
            first = d['list'][0]['vod_play_url'].split('#')[0].split('$')[-1]
            p = sp.playerContent('TinyAV', first, [])
            print('player parse=', p.get('parse'), 'url=', (p.get('url') or '')[:90])
    s = sp.searchContentPage('FNS', False, 1)
    print('search', len(s.get('list') or []),
          [x['vod_name'][:28] for x in (s.get('list') or [])[:3]])

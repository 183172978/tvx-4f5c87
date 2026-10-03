# coding=utf-8
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

    def getName(self):
        return "MJ视频"

    def init(self, extend=""):
        self.home_url = "https://mjv008.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; M2102J2SC Build/UKQ1.240624.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.home_url + '/zh/',
        })
        # 自动通过年龄确认
        try:
            self.session.get(
                self.home_url + '/zh/chinese_IamOverEighteenYearsOld/19/index.html',
                timeout=10
            )
        except Exception:
            pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '9smv_', '/hc/'))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    classes = [
        {"type_id": "chinese", "type_name": "中文字幕"},
        {"type_id": "censored", "type_name": "有码AV"},
        {"type_id": "uncensored", "type_name": "无码AV"},
        {"type_id": "amateurjav", "type_name": "素人AV"},
        {"type_id": "reducing-mosaic", "type_name": "无码破解"},
        {"type_id": "animation", "type_name": "H动画"},
        {"type_id": "dt", "type_name": "国产自拍"},
        {"type_id": "18H", "type_name": "18H长篇"},
    ]

    cate_map = {
        "chinese": "/zh/chinese_random/all/",
        "censored": "/zh/censored_random/all/",
        "uncensored": "/zh/uncensored_random/all/",
        "amateurjav": "/zh/amateurjav_random/all/",
        "reducing-mosaic": "/zh/reducing-mosaic_random/all/",
        "animation": "/zh/animation_random/all/",
        "dt": "/zh/dt_random/all/",
        "18H": "/zh/18H_random/all/",
    }

    # 播放 CDN（新域名优先）
    PLAY_HOSTS = [
        'gifb.eemmhh02.com',
        'gifb.imgstream3.com',
        'fchost1.eemmhh02.com',
        'fbhost1.eemmhh02.com',
    ]

    def homeContent(self, filter):
        return {"class": self.classes, "filters": {}}

    def _parse_list(self, html):
        videos = []
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.select('a[href*="_content/"]'):
            href = a.get('href', '')
            if not re.search(r'_content/\d+/', href):
                continue
            full = href if href.startswith('http') else urljoin(self.home_url, href)
            if any(v['vod_id'] == full for v in videos):
                continue
            title = a.get('title') or a.get_text(strip=True) or ''
            if not title or len(title) < 2:
                parent = a.find_parent(['div', 'li', 'td', 'figure'])
                if parent:
                    t = parent.select_one('.archive-title, .title, h3, h4, [itemprop="name"]')
                    if t:
                        title = t.get_text(strip=True)
            if not title:
                continue
            pic = ''
            img = a.select_one('img')
            if not img:
                parent = a.find_parent(['div', 'figure', 'li'])
                if parent:
                    img = parent.select_one('img')
            if img:
                pic = img.get('src') or img.get('data-src') or img.get('data-original') or ''
            videos.append({
                "vod_id": full,
                "vod_name": title[:80],
                "vod_pic": urljoin(self.home_url, pic) if pic else '',
                "vod_remarks": '',
            })
        return videos

    def homeVideoContent(self):
        videos = []
        try:
            url = self.home_url + '/zh/chinese_random/all/index.html'
            resp = self.session.get(url, timeout=12)
            resp.encoding = 'utf-8'
            videos = self._parse_list(resp.text)
        except Exception as e:
            print('homeVideoContent error:', e)
        return {'list': videos[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        page = int(pg) if str(pg).isdigit() else 1
        try:
            prefix = self.cate_map.get(str(tid), '/zh/chinese_random/all/')
            if page <= 1:
                url = self.home_url + prefix + 'index.html'
            else:
                url = self.home_url + prefix + str(page) + '.html'
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            videos = self._parse_list(resp.text)
        except Exception as e:
            print('categoryContent error:', e)
        return {
            'list': videos,
            'page': page,
            'pagecount': 999 if len(videos) >= 12 else page,
            'limit': 30,
            'total': 999999,
        }

    def _code_from_url(self, page_url):
        """从详情 URL 取番号，如 CJOD-502"""
        m = re.search(r'_content/\d+/([A-Za-z0-9\-]+)\.html', page_url or '', re.I)
        return m.group(1).upper() if m else ''

    def _extract_play_list(self, html, page_url=''):
        """
        提取播放地址。新 CDN: gifb.eemmhh02.com
        封面: .../b|s/{kind}/{num}_{CODE}.jpg
        正片: https://gifb.eemmhh02.com/hc/9smv_{kind}_{num}_{CODE}.mp4
        """
        plays = []
        seen = set()

        def add(name, url):
            url = (url or '').replace('\\/', '/').strip()
            if not url.startswith('http') or url in seen:
                return
            if re.search(r'\.(jpg|jpeg|png|gif|webp|css|js)(\?|$)', url, re.I):
                return
            seen.add(url)
            plays.append((name, url))

        code = self._code_from_url(page_url)

        # 1) 封面推导（本片，最可靠）
        # 支持任意 *host* 上的 /b/ 或 /s/ 封面
        cover_re = re.compile(
            r'https?://([^/"\'\s]+)/(?:b|s)/([a-zA-Z0-9\-]+)/(\d+)_([A-Za-z0-9\-]+)\.(?:jpg|jpeg|png|webp)',
            re.I
        )
        covers = list(cover_re.finditer(html or ''))
        # 优先匹配与当前番号一致的封面
        ordered = []
        for m in covers:
            if code and m.group(4).upper() == code:
                ordered.insert(0, m)
            else:
                ordered.append(m)
        if ordered:
            m = ordered[0]
            kind = m.group(2).lower()
            num = m.group(3)
            c = m.group(4)
            for i, host in enumerate(self.PLAY_HOSTS):
                u = f'https://{host}/hc/9smv_{kind}_{num}_{c}.mp4'
                label = '正片' if i == 0 else f'线路{i}'
                add(label, u)

        # 2) 页面里已有的 9smv_ 直链（优先本番号）
        for m in re.finditer(r'https?://[^"\'\s<>]*?/hc/9smv_[^"\'\s<>]+\.mp4', html or '', re.I):
            u = m.group(0)
            if code and code.replace('-', '').lower() in u.replace('-', '').lower():
                add('正片', u)
            else:
                add('相关', u)

        # 3) 任意 /hc/ 下的 mp4
        for m in re.finditer(r'https?://[^"\'\s<>]+/hc/[^"\'\s<>]+\.mp4', html or '', re.I):
            add('备用', m.group(0))

        # 4) m3u8
        for m in re.finditer(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html or '', re.I):
            add('HLS', m.group(0))

        # 若同时有「正片」与「相关」，只保留正片+线路（避免播错片）
        main = [p for p in plays if p[0] in ('正片', '线路1', '线路2', '线路3')]
        if main:
            # 去重 URL，正片优先
            out, seen2 = [], set()
            for name, u in main:
                if u in seen2:
                    continue
                seen2.add(u)
                out.append((name, u))
            return out

        return plays

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        try:
            vid = ids[0]
            url = vid if str(vid).startswith('http') else urljoin(self.home_url, vid)
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')

            vod = {
                "vod_id": vid,
                "vod_name": "未知",
                "vod_pic": "",
                "vod_content": "",
                "vod_remarks": "",
            }

            h1 = soup.select_one('h1') or soup.select_one('.archive-title') or soup.select_one('title')
            if h1:
                vod['vod_name'] = h1.get_text(strip=True).replace(' - MJ', '').strip()[:80]

            # 封面优先 JSON-LD thumbnailUrl / 大图
            pic = ''
            tm = re.search(r'"thumbnailUrl"\s*:\s*"(https?://[^"]+)"', html)
            if tm:
                pic = tm.group(1)
            if not pic:
                img = (soup.select_one('#player-wrap img') or
                       soup.select_one('.player-wrap img') or
                       soup.select_one('img[src*="/b/"]') or
                       soup.select_one('img[src*="eemmhh"]') or
                       soup.select_one('img[src*="imgstream"]'))
                if img:
                    pic = img.get('src') or img.get('data-src') or ''
            vod['vod_pic'] = pic

            desc = soup.select_one('.entry-content p') or soup.select_one('.content p')
            if desc:
                vod['vod_content'] = desc.get_text(strip=True)[:500]

            play_list = self._extract_play_list(html, url)
            if play_list:
                url_list = [f'{name}${purl}' for name, purl in play_list]
                vod['vod_play_from'] = 'MJ'
                vod['vod_play_url'] = '#'.join(url_list)
            else:
                # 仍给占位，避免壳子当无片源
                vod['vod_play_from'] = 'MJ'
                vod['vod_play_url'] = f'正片${url}'

            return {'list': [vod]}
        except Exception as e:
            print('detailContent error:', e)
        return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            encoded = quote(key)
            url = f"{self.home_url}/zh/search/{encoded}/1.html"
            if str(pg) != "1":
                url = f"{self.home_url}/zh/search/{encoded}/{pg}.html"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            videos = self._parse_list(resp.text)
            if not videos:
                url2 = self.home_url + '/zh/chinese_random/all/index.html'
                resp2 = self.session.get(url2, timeout=12)
                resp2.encoding = 'utf-8'
                all_v = self._parse_list(resp2.text)
                videos = [v for v in all_v if key.lower() in v['vod_name'].lower()]
            return {'list': videos}
        except Exception as e:
            print('searchContent error:', e)
        return {'list': []}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.session.headers.get('User-Agent', ''),
            'Referer': self.home_url + '/',
            'Origin': self.home_url,
        }
        play = str(id or '').strip()
        if '$' in play:
            play = play.split('$')[-1].strip()

        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        try:
            url = play if play.startswith('http') else urljoin(self.home_url, play)
            resp = self.session.get(url, timeout=12)
            resp.encoding = 'utf-8'
            play_list = self._extract_play_list(resp.text, url)
            if play_list:
                return {'parse': 0, 'jx': '0', 'url': play_list[0][1], 'header': header}
        except Exception:
            pass

        return {
            'parse': 0,
            'jx': '0',
            'url': '',
            'header': header
        }

    def localProxy(self, params):
        return None
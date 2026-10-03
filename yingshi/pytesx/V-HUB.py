# coding: utf-8
"""
V-HUB Spider v2.1
修复：newxvideos.pages.dev/api 已 500「API 请求失败」
改为直连 xvideos.com 解析列表/搜索/详情播放地址
"""
import json
import sys
import re
import urllib.request
import urllib.parse
import ssl

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

VERSION = '2.1.0'

SITE_URL = 'https://www.xvideos.com'

CATEGORIES = [
    {"type_id": "Arab-159", "type_name": "阿拉伯"},
    {"type_id": "Mature-38", "type_name": "成熟"},
    {"type_id": "Cuckold-237", "type_name": "出轨背叛"},
    {"type_id": "Femdom-235", "type_name": "调教"},
    {"type_id": "Anal-12", "type_name": "肛交"},
    {"type_id": "Brunette-25", "type_name": "褐发"},
    {"type_id": "Black_Woman-30", "type_name": "黑人"},
    {"type_id": "Redhead-31", "type_name": "红发"},
    {"type_id": "Fucked_Up_Family-81", "type_name": "家庭乱搞"},
    {"type_id": "Blonde-20", "type_name": "金发"},
    {"type_id": "Big_Cock-34", "type_name": "巨屌"},
    {"type_id": "Big_Tits-23", "type_name": "巨乳"},
    {"type_id": "Big_Ass-24", "type_name": "巨臀"},
    {"type_id": "Blowjob-15", "type_name": "口交"},
    {"type_id": "Latina-16", "type_name": "拉丁裔"},
    {"type_id": "Milf-19", "type_name": "辣妈"},
    {"type_id": "Gapes-167", "type_name": "裂开"},
    {"type_id": "Ass-14", "type_name": "美臀"},
    {"type_id": "Lesbian-26", "type_name": "女同"},
    {"type_id": "bbw-51", "type_name": "胖女"},
    {"type_id": "Squirting-56", "type_name": "喷出"},
    {"type_id": "Fisting-165", "type_name": "拳交"},
    {"type_id": "Gangbang-69", "type_name": "群交"},
    {"type_id": "Teen-13", "type_name": "少女"},
    {"type_id": "Cumshot-18", "type_name": "射颜"},
    {"type_id": "Cam_Porn-58", "type_name": "摄像头"},
    {"type_id": "Bi_Sexual-62", "type_name": "双性恋"},
    {"type_id": "Stockings-28", "type_name": "丝袜"},
    {"type_id": "Oiled-22", "type_name": "涂油"},
    {"type_id": "Lingerie-83", "type_name": "性感内衣"},
    {"type_id": "Asian_Woman-32", "type_name": "亚洲"},
    {"type_id": "Amateur-65", "type_name": "业余"},
    {"type_id": "Interracial-27", "type_name": "异族"},
    {"type_id": "Indian-89", "type_name": "印度"},
    {"type_id": "Creampie-40", "type_name": "中出"},
    {"type_id": "Solo_and_Masturbation-33", "type_name": "自慰"},
    {"type_id": "AI-239", "type_name": "AI"},
    {"type_id": "ASMR-229", "type_name": "ASMR"},
]


class Spider(BaseSpider):
    def getName(self):
        return "V-HUB[成人]"

    def init(self, extend=""):
        self.host = SITE_URL
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else (extend if isinstance(extend, dict) else {})
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': self.host + '/',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE

    def _get(self, url, timeout=18):
        try:
            req = urllib.request.Request(url, headers=self.headers, method='GET')
            resp = urllib.request.urlopen(req, context=self._ssl, timeout=timeout)
            return resp.read().decode('utf-8', 'ignore')
        except Exception as e:
            print('_get error:', url, e, file=sys.stderr)
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
            return urllib.parse.urljoin(self.host + '/', u)
        return u

    def _format_time_cn(self, time_str):
        if not time_str:
            return ''
        m = re.match(r'^(\d+)\s*min\s*$', time_str.strip(), re.I)
        if m:
            return m.group(1) + '分钟'
        m = re.match(r'^(\d+)\s*h(?:our)?s?\s*(\d+)?\s*min\s*$', time_str.strip(), re.I)
        if m:
            if m.group(2):
                return m.group(1) + '小时' + m.group(2) + '分钟'
            return m.group(1) + '小时'
        return time_str

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        re_block = re.compile(
            r'data-id=["\'](\d+)["\'][\s\S]{0,80}?data-eid=["\']([^"\']+)["\']'
            r'[\s\S]{0,1200}?href=["\'](/video\.[^"\']+)["\']'
            r'[\s\S]{0,800}?(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']'
            r'[\s\S]{0,600}?title=["\']([^"\']{3,200})["\']'
            r'[\s\S]{0,200}?class=["\']duration["\'][^>]*>([^<]+)',
            re.I
        )
        for m in re_block.finditer(html):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': m.group(3),
                'vod_name': m.group(5).strip()[:150],
                'vod_pic': self._abs(m.group(4)),
                'vod_remarks': self._format_time_cn(m.group(6).strip()),
            })
        if len(videos) >= 6:
            return videos

        for m in re.finditer(r'href=["\'](/video\.[^"\']+)["\'][^>]*title=["\']([^"\']{3,200})["\']', html, re.I):
            href = m.group(1)
            if href in seen:
                continue
            seen.add(href)
            block = html[max(0, m.start() - 400):m.start() + 500]
            pic = ''
            pm = re.search(r'(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block, re.I)
            if pm:
                pic = self._abs(pm.group(1))
            dur = ''
            dm = re.search(r'class=["\']duration["\'][^>]*>([^<]+)', block, re.I)
            if dm:
                dur = self._format_time_cn(dm.group(1).strip())
            videos.append({
                'vod_id': href,
                'vod_name': m.group(2).strip()[:150],
                'vod_pic': pic,
                'vod_remarks': dur,
            })
        return videos

    def _extract_play(self, html):
        plays = []
        if not html:
            return plays
        m = re.search(r"setVideoHLS\(['\"]([^'\"]+)['\"]\)", html, re.I)
        if m:
            plays.append(('高清HLS', m.group(1).replace('\\/', '/')))
        m = re.search(r"setVideoUrlHigh\(['\"]([^'\"]+)['\"]\)", html, re.I)
        if m:
            plays.append(('高清MP4', m.group(1).replace('\\/', '/')))
        m = re.search(r"setVideoUrlLow\(['\"]([^'\"]+)['\"]\)", html, re.I)
        if m:
            plays.append(('低清MP4', m.group(1).replace('\\/', '/')))
        if not plays:
            m = re.search(r'https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*', html, re.I)
            if m:
                plays.append(('HLS', m.group(0)))
        return plays

    def homeContent(self, filter):
        classes = [{'type_id': c['type_id'], 'type_name': c['type_name']} for c in CATEGORIES]
        html = self._get(self.host + '/new/1')
        videos = self._parse_list(html)[:24]
        return {'class': classes, 'list': videos}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'Teen-13').strip()
        # /c/Teen-13/1  页码从 1 开始
        url = '%s/c/%s/%d' % (self.host, urllib.parse.quote(tid, safe='-_'), pg)
        html = self._get(url)
        videos = self._parse_list(html)
        type_name = tid
        for c in CATEGORIES:
            if c['type_id'] == tid:
                type_name = c['type_name']
                break
        pagecount = pg + 1 if len(videos) >= 20 else pg
        return {
            'page': pg,
            'pagecount': pagecount,
            'limit': 48,
            'total': 9999,
            'type_name': type_name,
            'list': videos,
        }

    def detailContent(self, array):
        result = {'list': []}
        if not array or not array[0]:
            return result
        path = str(array[0]).strip()
        page_url = path if path.startswith('http') else self._abs(path)
        html = self._get(page_url)

        vod = {
            'vod_id': path,
            'vod_name': '视频详情',
            'vod_pic': '',
            'vod_remarks': '',
            'vod_content': '',
            'vod_play_from': 'V-HUB',
            'vod_play_url': '',
        }

        m = re.search(r"setVideoTitle\(['\"]([^'\"]+)['\"]\)", html, re.I)
        if m:
            vod['vod_name'] = m.group(1).strip()
        else:
            m = re.search(r'<title>([^<]+)</title>', html, re.I)
            if m:
                vod['vod_name'] = re.split(r'\s*-\s*XVideos', m.group(1), flags=re.I)[0].strip()

        m = re.search(r"setThumbUrl\(['\"]([^'\"]+)['\"]\)", html, re.I)
        if not m:
            m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            vod['vod_pic'] = self._abs(m.group(1))

        m = re.search(r'class=["\'][^"\']*duration[^"\']*["\'][^>]*>([^<]+)', html, re.I)
        if m:
            vod['vod_remarks'] = self._format_time_cn(m.group(1).strip())

        plays = self._extract_play(html)
        if plays:
            vod['vod_play_url'] = '#'.join(['%s$%s' % (a, b) for a, b in plays])
        else:
            vod['vod_play_url'] = '网页$%s' % page_url

        result['list'] = [vod]
        return result

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 48, 'total': 0}
        # 搜索 p=0 为第 1 页
        p = max(0, pg - 1)
        url = '%s/?k=%s&p=%d' % (self.host, urllib.parse.quote(key), p)
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 48,
            'total': 9999,
            'list': videos,
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': self.host + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}
        if play.startswith('http') or play.startswith('/video.'):
            page_url = self._abs(play)
            html = self._get(page_url)
            plays = self._extract_play(html)
            if plays:
                return {'parse': 0, 'url': plays[0][1], 'header': header}
            return {'parse': 1, 'jx': '1', 'url': page_url, 'header': header}
        return {'parse': 0, 'url': play, 'header': header}

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
    h = sp.homeContent(False)
    print('classes', len(h['class']), 'home_list', len(h.get('list') or []))
    for tid in ['Teen-13', 'Asian_Woman-32', 'Milf-19']:
        r = sp.categoryContent(tid, 1, False, {})
        print(tid, 'n=', len(r.get('list') or []),
              [x.get('vod_name', '')[:40] for x in (r.get('list') or [])[:2]])
    if h.get('list'):
        d = sp.detailContent([h['list'][0]['vod_id']])
        print('detail', (d['list'][0].get('vod_name') or '')[:50] if d.get('list') else None)
        print('play', (d['list'][0].get('vod_play_url') or '')[:120] if d.get('list') else None)
    s = sp.searchContentPage('teen', False, 1)
    print('search', len(s.get('list') or []),
          [x.get('vod_name', '')[:35] for x in (s.get('list') or [])[:2]])

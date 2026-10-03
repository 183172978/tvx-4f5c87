#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光厂 VJshi Spider v1.4
修复：分类列表解析（新版 video-card 结构）/ 播放
- 纯 Python 过 acw_sc__v2
- 识别阿里云滑动验证，支持 extend 注入 Cookie
- 加强列表与 MP4 解析

extend 示例：
  "acw_sc__v2=xxx; acw_tc=yyy; tfstk=zzz"
  或 JSON {"cookie":"..."}
"""
import json
import re
import sys
import time
import gzip
import urllib.parse
import urllib.request

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


_ACW_POS = [
    0x0f, 0x23, 0x1d, 0x18, 0x21, 0x10, 0x01, 0x26, 0x0a, 0x09,
    0x13, 0x1f, 0x28, 0x1b, 0x16, 0x17, 0x19, 0x0d, 0x06, 0x0b,
    0x27, 0x12, 0x14, 0x08, 0x0e, 0x15, 0x20, 0x1a, 0x02, 0x1e,
    0x07, 0x04, 0x11, 0x05, 0x03, 0x1c, 0x22, 0x25, 0x0c, 0x24,
]
_ACW_MASK = '3000176000856006061501533003690027800375'


def solve_acw_sc_v2(arg1):
    if not arg1 or len(arg1) < 40:
        return ''
    out = [''] * len(_ACW_POS)
    for i, ch in enumerate(arg1):
        for j, p in enumerate(_ACW_POS):
            if p == i + 1:
                out[j] = ch
    arg2 = ''.join(out)
    parts = []
    for i in range(0, min(len(arg2), len(_ACW_MASK)), 2):
        s = int(arg2[i:i + 2], 16)
        m = int(_ACW_MASK[i:i + 2], 16)
        x = format(s ^ m, 'x')
        if len(x) == 1:
            x = '0' + x
        parts.append(x)
    return ''.join(parts)


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://www.vjshi.com'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        )
        self._cookie = ''
        self._extra_cookie = ''
        self._cookie_ts = 0
        self.channels = {
            'shipinsucai': {'name': '视频素材', 'path': '/so/shipinsucai.html'},
            'aemuban': {'name': 'AE模板', 'path': '/so/aemuban.html'},
            'prmuban': {'name': 'PR模板', 'path': '/so/prmuban.html'},
            'fcpmuban': {'name': 'FCP模板', 'path': '/so/fcpmuban.html'},
            '3d': {'name': '3D模型', 'path': '/so/3dmaxmoxing.html'},
            'c4d': {'name': 'C4D模型', 'path': '/so/c4dmoxing.html'},
            'nature': {'name': '自然风景', 'query': '自然'},
            'city': {'name': '城市建筑', 'query': '城市'},
            'people': {'name': '人物生活', 'query': '人物'},
            'tech': {'name': '科技数据', 'query': '科技'},
            'business': {'name': '商务企业', 'query': '商务'},
            'medical': {'name': '医疗健康', 'query': '医疗'},
            'food': {'name': '美食餐饮', 'query': '美食'},
            'sport': {'name': '运动健身', 'query': '运动'},
            '4k': {'name': '4K素材', 'query': '4K'},
        }

    def getName(self):
        return '光厂视频'

    def init(self, extend=""):
        self._parse_extend(extend)
        try:
            self._ensure_cookie(force=True)
        except Exception as e:
            print('init cookie:', e)

    def _parse_extend(self, extend):
        if not extend:
            return
        s = extend if isinstance(extend, str) else json.dumps(extend, ensure_ascii=False)
        s = s.strip()
        if not s:
            return
        if s.startswith('{'):
            try:
                j = json.loads(s)
                if j.get('cookie'):
                    self._extra_cookie = str(j['cookie'])
                if j.get('acw_sc__v2'):
                    self._cookie = str(j['acw_sc__v2'])
            except Exception:
                pass
            return
        self._extra_cookie = s
        m = re.search(r'acw_sc__v2=([0-9a-fA-F]+)', s)
        if m:
            self._cookie = m.group(1)

    def _headers(self, with_cookie=True):
        h = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        if with_cookie:
            parts = []
            if self._cookie:
                parts.append('acw_sc__v2=' + self._cookie)
            if self._extra_cookie:
                parts.append(self._extra_cookie)
            if parts:
                h['Cookie'] = '; '.join(parts)
        return h

    def _decode_body(self, raw):
        if not raw:
            return ''
        if isinstance(raw, str):
            return raw
        if raw[:2] == b'\x1f\x8b':
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw.decode('utf-8', 'ignore')

    def _raw_get(self, url, with_cookie=True):
        try:
            if requests is not None:
                r = requests.get(
                    url, headers=self._headers(with_cookie),
                    timeout=20, allow_redirects=True,
                )
                return r.text or ''
            req = urllib.request.Request(url, headers=self._headers(with_cookie))
            resp = urllib.request.urlopen(req, timeout=20)
            return self._decode_body(resp.read())
        except Exception as e:
            print('raw_get error:', url, e)
            return ''

    def _is_acw_challenge(self, html):
        return bool(html and 'var arg1=' in html and len(html) < 25000)

    def _is_slide_challenge(self, html):
        if not html:
            return False
        if re.search(r'/watch/\d+\.html', html):
            return False
        return bool(re.search(
            r'滑动验证|Page Verification|Please slide to verify|nocaptcha|CF_APP_WAF|AWSC\.use',
            html,
        ))

    def _ensure_cookie(self, force=False):
        if not force and self._cookie and (time.time() - self._cookie_ts) < 3000:
            return self._cookie
        html = self._raw_get(self.siteUrl + '/', with_cookie=False)
        m = re.search(r"var arg1=['\"]([A-Fa-f0-9]+)['\"]", html or '')
        if not m:
            self._cookie_ts = time.time()
            return self._cookie
        val = solve_acw_sc_v2(m.group(1))
        if val:
            self._cookie = val
            self._cookie_ts = time.time()
            print('acw_sc__v2 ok', val[:16])
        return self._cookie

    def fetch_text(self, url):
        self._ensure_cookie()
        html = self._raw_get(url, with_cookie=True)
        if self._is_acw_challenge(html):
            self._ensure_cookie(force=True)
            html = self._raw_get(url, with_cookie=True)
        return html or ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _parse_list(self, html):
        videos = []
        if not html or self._is_acw_challenge(html) or self._is_slide_challenge(html):
            if html and self._is_slide_challenge(html):
                print('parse_list: 阿里云滑动验证，请在 extend 注入浏览器 Cookie')
            return videos
        seen = set()

        # 新版 video-card：href="/watch/ID.html?..." 后跟 img src + alt
        re_card = re.compile(
            r'href="(/watch/(\d+)\.html)[^"]*"[\s\S]{0,2500}?'
            r'<img[^>]+(?:src|data-src|data-original)="([^"]+)"[^>]*(?:alt="([^"]*)")?',
            re.I,
        )
        for m in re_card.finditer(html):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            pic = m.group(3) or ''
            if pic.startswith('data:'):
                near = html[m.start():m.start() + 2500]
                pm = re.search(r'(?:src|data-src)="(https?://[^"]+)"', near)
                if pm:
                    pic = pm.group(1)
            title = (m.group(4) or '').strip()
            if not title:
                near = html[m.start():m.start() + 3000]
                tm = re.search(r'alt="([^"]{2,120})"', near)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                near = html[m.start():m.start() + 3500]
                tm = re.search(r'>([^<]{2,80})</(?:h[1-6]|a|span|p)>', near)
                if tm:
                    title = tm.group(1).strip()
            videos.append({
                'vod_id': vid,
                'vod_name': (title or ('素材 #%s' % vid))[:100],
                'vod_pic': self._abs(pic),
                'vod_remarks': '',
            })

        # 反向：img 在前
        if len(videos) < 6:
            re2 = re.compile(
                r'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*(?:alt="([^"]*)")?'
                r'[\s\S]{0,800}?href="/watch/(\d+)\.html',
                re.I,
            )
            for m in re2.finditer(html):
                vid = m.group(3)
                if vid in seen:
                    continue
                seen.add(vid)
                title = (m.group(2) or '').strip() or ('素材 #%s' % vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': title[:100],
                    'vod_pic': self._abs(m.group(1)),
                    'vod_remarks': '',
                })

        # 兜底：仅链接
        if len(videos) < 6:
            for m in re.finditer(r'href="/watch/(\d+)\.html', html):
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                near = html[max(0, m.start() - 50):m.start() + 1200]
                title = ''
                tm = re.search(r'alt="([^"]{2,100})"', near)
                if tm:
                    title = tm.group(1).strip()
                if not title:
                    tm = re.search(r'>([^<]{2,80})</(?:h\d|a|span|div)>', near)
                    if tm:
                        title = tm.group(1).strip()
                videos.append({
                    'vod_id': vid,
                    'vod_name': (title or ('素材 #%s' % vid))[:100],
                    'vod_pic': '',
                    'vod_remarks': '',
                })
        return videos

    def _list_url(self, tid, pg):
        pg = int(pg or 1)
        info = self.channels.get(str(tid), {})
        path = info.get('path')
        q = info.get('query')
        if path:
            if pg <= 1:
                return self.siteUrl + path
            return self.siteUrl + path + '?page=' + str(pg)
        params = {'wd': q or str(tid)}
        if pg > 1:
            params['page'] = pg
        return self.siteUrl + '/so?' + urllib.parse.urlencode(params)

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        result = {'class': classes}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos = []
        try:
            html = self.fetch_text(self.siteUrl + '/')
            videos = self._parse_list(html)
        except Exception as e:
            print('首页失败:', e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            url = self._list_url(tid, pg)
            print('category url:', url)
            html = self.fetch_text(url)
            print('category html len:', len(html or ''), 'slide=', self._is_slide_challenge(html))
            videos = self._parse_list(html)
            print('category items:', len(videos))
        except Exception as e:
            print('分类失败:', e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else max(pg, 1),
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            params = {'wd': key or ''}
            if pg > 1:
                params['page'] = pg
            url = self.siteUrl + '/so?' + urllib.parse.urlencode(params)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
        except Exception as e:
            print('搜索失败:', e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else max(pg, 1),
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def _extract_play(self, html):
        play_parts = []
        seen = set()
        for m in re.finditer(r'https?://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html or '', re.I):
            u = m.group(0).replace('\\/', '/').rstrip('\\\'";')
            if u in seen or 'blob:' in u:
                continue
            seen.add(u)
            label = '预览'
            if 'lmp4' in u:
                label = '低清预览'
            elif 'mp4.vjshi' in u or 'hmp4' in u:
                label = '高清预览'
            play_parts.append('%s$%s' % (label, u))
        # 优先高清
        play_parts.sort(key=lambda x: 0 if '高清' in x else (1 if '低清' in x else 2))
        return play_parts

    def detailContent(self, ids):
        vid = re.sub(r'\D', '', str((ids or [''])[0])) or str((ids or [''])[0])
        try:
            url = '%s/watch/%s.html' % (self.siteUrl, vid)
            html = self.fetch_text(url)
            if self._is_slide_challenge(html):
                return {'list': [{
                    'vod_id': vid,
                    'vod_name': '素材 #%s' % vid,
                    'vod_pic': '',
                    'vod_content': '站点开启滑动验证，请在源配置 extend 中注入浏览器 Cookie 后重试。',
                    'vod_play_from': '光厂',
                    'vod_play_url': '网页$%s' % url,
                }]}
            name = '素材 #%s' % vid
            pic = ''
            desc = ''
            m = re.search(r'<title>([^<]+)</title>', html or '', re.I)
            if m:
                name = re.sub(r'\s*[-|_].*$', '', m.group(1)).strip() or name
            m = re.search(
                r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                html or '', re.I,
            )
            if m:
                name = m.group(1).strip()
            m = re.search(
                r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
                html or '', re.I,
            )
            if m:
                pic = self._abs(m.group(1))
            m = re.search(
                r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
                html or '', re.I,
            )
            if m:
                desc = m.group(1).strip()[:400]

            play_parts = self._extract_play(html)
            if not play_parts:
                play_parts.append('网页$%s' % url)

            return {'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': '',
                'vod_content': desc or '光厂（VJshi）正版素材，完整下载需授权，此处为在线预览。',
                'vod_play_from': '光厂',
                'vod_play_url': '#'.join(play_parts[:6]),
            }]}
        except Exception as e:
            print('详情失败:', e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(mp4|m3u8)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}
        if play.startswith('http'):
            html = self.fetch_text(play)
            parts = self._extract_play(html)
            if parts:
                return {
                    'parse': 0,
                    'url': parts[0].split('$')[-1],
                    'header': header,
                }
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}
        page = '%s/watch/%s.html' % (
            self.siteUrl, re.sub(r'\D', '', play) or play
        )
        html = self.fetch_text(page)
        parts = self._extract_play(html)
        if parts:
            return {
                'parse': 0,
                'url': parts[0].split('$')[-1],
                'header': header,
            }
        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(mp4|m3u8|webm)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print('home', json.dumps(spider.homeContent(False), ensure_ascii=False)[:180])
    r = spider.categoryContent('shipinsucai', 1, False, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        print('first', r['list'][0].get('vod_name'), r['list'][0].get('vod_pic')[:60])
        d = spider.detailContent([r['list'][0]['vod_id']])
        print('detail play', d['list'][0].get('vod_play_url', '')[:120] if d.get('list') else None)

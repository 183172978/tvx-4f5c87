# -*- coding: utf-8 -*-
"""
SexKBJ https://sexkbj.com
风格对齐 AVBeBe.py
列表: loop-video thumb-block
播放: streamtape embed → get_video 直链 mp4
"""
import re
import json
import html as html_mod
import sys
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass
        def fetch(self, url, headers=None):
            class R:
                text = ''
            return R()

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):
    def __init__(self):
        self.name = 'SexKBJ'
        self.host = 'https://sexkbj.com'
        self.ua = (
            'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
        )
        self.headers = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.classes = [
            {'type_id': '/category/korean-bj/', 'type_name': 'Korean BJ'},
            {'type_id': '/category/premium/', 'type_name': 'Premium'},
            {'type_id': '/category/afreecatv/', 'type_name': 'AfreecaTV'},
            {'type_id': '/category/korean-amateur/', 'type_name': 'Korean Amateur'},
        ]

    def getName(self):
        return self.name

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')
            self.headers['Referer'] = self.host + '/'

    def _get(self, url, referer=None):
        try:
            if not url.startswith('http'):
                url = self.host + (url if url.startswith('/') else '/' + url)
            headers = dict(self.headers)
            if referer:
                headers['Referer'] = referer
            # 壳子 fetch 优先；本地无壳子时走 requests/urllib
            if hasattr(self, 'fetch') and 'base.spider' in str(type(self).__mro__):
                try:
                    r = self.fetch(url, headers=headers)
                    text = getattr(r, 'text', '') or ''
                    if text:
                        return text
                except Exception:
                    pass
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=18, context=ctx) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=headers, timeout=18, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('GET err', url, e)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip()
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u

    def parse_list(self, html_str):
        videos = []
        if not html_str:
            return videos
        seen = set()
        # loop-video blocks
        blocks = re.findall(
            r'(?:<article[^>]*)?class="[^"]*loop-video[^"]*"[\s\S]{0,1200}',
            html_str, re.I
        )
        for block in blocks:
            lm = re.search(
                r'<a[^>]+href="(https?://sexkbj\.com/\d{4}/\d{2}/\d{2}/[^"]+)"[^>]*(?:title="([^"]*)")?',
                block, re.I
            )
            if not lm:
                lm = re.search(
                    r'href="(https?://sexkbj\.com/\d{4}/\d{2}/\d{2}/[^"]+)"[^>]*title="([^"]*)"',
                    block, re.I
                )
            if not lm:
                continue
            vod_id = lm.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)
            name = (lm.group(2) or '').strip()
            if not name:
                tm = re.search(r'title="([^"]+)"', block)
                name = tm.group(1) if tm else vod_id.rstrip('/').rsplit('/', 1)[-1]
            pic = ''
            pm = re.search(
                r'(?:data-src|data-lazy-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                block, re.I
            )
            if pm:
                pic = pm.group(1).split('?')[0]
            videos.append({
                'vod_id': vod_id,
                'vod_name': re.sub(r'\s+', ' ', name)[:120],
                'vod_pic': pic,
                'vod_remarks': 'SexKBJ',
            })
        # fallback: date-based links
        if not videos:
            for m in re.finditer(
                r'href="(https?://sexkbj\.com/\d{4}/\d{2}/\d{2}/[^"]+)"[^>]*title="([^"]*)"',
                html_str, re.I
            ):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                videos.append({
                    'vod_id': m.group(1),
                    'vod_name': m.group(2)[:120],
                    'vod_pic': '',
                    'vod_remarks': 'SexKBJ',
                })
        return videos

    def homeContent(self, filter=False):
        return {'class': list(self.classes), 'filters': {}}

    def homeVideoContent(self):
        return {'list': self.parse_list(self._get(self.host + '/'))[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        path = str(tid or '/category/korean-bj/')
        if not path.startswith('http'):
            url = self.host + path
        else:
            url = path
        if pg > 1:
            url = url.rstrip('/') + '/page/%d/' % pg
        html_text = self._get(url)
        videos = self.parse_list(html_text)
        pages = [int(x) for x in re.findall(r'/page/(\d+)/', html_text or '')]
        pagecount = max(pages + [pg])
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': pagecount * 24,
        }

    def _parse_streamtape(self, embed_url):
        """从 streamtape embed 页解出直链 mp4"""
        html_text = self._get(embed_url, referer=self.host + '/')
        if not html_text:
            return ''
        # robotlink / botlink 拼接
        patterns = [
            r"getElementById\('robotlink'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*\('([^']+)'\)\.substring\((\d+)\)(?:\.substring\((\d+)\))?",
            r"getElementById\('botlink'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*\('([^']+)'\)\.substring\((\d+)\)(?:\.substring\((\d+)\))?",
            r"getElementById\('ideoolink'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*['\"][^'\"]*['\"]\s*\+\s*\('([^']+)'\)\.substring\((\d+)\)(?:\.substring\((\d+)\))?",
        ]
        for pat in patterns:
            m = re.search(pat, html_text)
            if not m:
                continue
            prefix = m.group(1)
            body = m.group(2)
            a = int(m.group(3))
            b = int(m.group(4)) if m.lastindex >= 4 and m.group(4) else 0
            part = body[a:]
            if b:
                part = part[b:]
            link = prefix + part
            if link.startswith('//'):
                link = 'https:' + link
            if not link.startswith('http'):
                link = 'https://streamtape.com' + (link if link.startswith('/') else '/' + link)
            if 'get_video' in link:
                if '&stream=' not in link:
                    link += '&stream=1'
                return link
        # 兜底：取最后一个看似完整的 get_video token
        tokens = re.findall(
            r"get_video\?id=[A-Za-z0-9]+&expires=\d+&ip=[A-Za-z0-9]+&token=[A-Za-z0-9]+",
            html_text
        )
        if tokens:
            return 'https://streamtape.com/' + tokens[-1] + '&stream=1'
        return ''

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(raw or '').strip()
        if not url.startswith('http'):
            url = self._abs(url)
        html_text = self._get(url)
        if not html_text:
            return {'list': []}

        name = ''
        m = re.search(r'<title>([^<]+)', html_text, re.I)
        if m:
            name = re.sub(r'\s*[&–|│·\-].*$', '', html_mod.unescape(m.group(1))).strip()
        if not name:
            m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html_text, re.I)
            if m:
                name = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html_text, re.I)
        if m:
            pic = m.group(1)

        plays = []
        # 只收 streamtape embed，播放时再解直链（避免 token/IP 过期）
        embeds = re.findall(
            r'(?:src|data-src)=["\'](https?://(?:streamtape|streamta\.pe)[^"\']+)["\']',
            html_text, re.I
        )
        for emb in embeds:
            plays.append(('Streamtape', emb))

        # 页面直出 mp4/m3u8（非封面）
        for u in re.findall(r'https?://[^"\'\s<>]+\.mp4(?:\?[^"\'\s<>]*)?', html_text, re.I):
            if u.endswith('.jpg') or '.mp4.jpg' in u:
                continue
            plays.append(('MP4', u))
        for u in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html_text, re.I):
            if 'preview' not in u.lower():
                plays.append(('M3U8', u))

        if not plays:
            plays = [('原页', url)]

        # 去重
        seen, uniq = set(), []
        for n, u in plays:
            if u in seen:
                continue
            seen.add(u)
            uniq.append('%s$%s' % (n, u))

        return {
            'list': [{
                'vod_id': url,
                'vod_name': name or 'SexKBJ',
                'vod_pic': pic,
                'vod_remarks': 'SexKBJ',
                'vod_content': '',
                'vod_play_from': 'SexKBJ',
                'vod_play_url': '#'.join(uniq),
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        kw = quote(str(key or '').strip())
        if not kw:
            return {'list': []}
        url = '%s/?s=%s' % (self.host, kw)
        if pg > 1:
            url = '%s/page/%d/?s=%s' % (self.host, pg, kw)
        return {
            'list': self.parse_list(self._get(url)),
            'page': pg,
            'pagecount': pg + 1,
            'limit': 24,
            'total': 9999,
        }

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        play = str(id or '').strip()
        if play.startswith('//'):
            play = 'https:' + play

        # streamtape embed：播放时现解，保证 token/IP 有效
        if re.search(r'streamtape\.com/e/|streamta\.pe/e/', play, re.I):
            direct = self._parse_streamtape(play)
            if direct:
                # 跟随一次拿到最终 CDN（部分播放器不跟 302）
                final = self._follow_streamtape(direct)
                st_header = {
                    'User-Agent': self.ua,
                    'Referer': 'https://streamtape.com/',
                    'Origin': 'https://streamtape.com',
                }
                return {'parse': 0, 'jx': 0, 'url': final or direct, 'header': st_header}
            return {
                'parse': 1, 'jx': 0, 'url': play, 'header': header,
                'sniff': 1, 'sniff_include': ['.mp4', 'get_video', 'tapecontent'],
            }

        # 已是 get_video / 直链
        if re.search(r'get_video\?|tapecontent\.net|\.(m3u8|mp4)(\?|$)', play, re.I):
            if 'streamtape' in play or 'streamta' in play or 'tapecontent' in play:
                header = {
                    'User-Agent': self.ua,
                    'Referer': 'https://streamtape.com/',
                    'Origin': 'https://streamtape.com',
                }
                if 'get_video' in play and 'tapecontent' not in play:
                    final = self._follow_streamtape(play)
                    if final:
                        play = final
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

        return {
            'parse': 1, 'jx': 0, 'url': play, 'header': header,
            'sniff': 1, 'sniff_include': ['.m3u8', '.mp4', '.ts', 'get_video'],
        }

    def _follow_streamtape(self, url):
        """跟随 get_video 302 拿到 tapecontent CDN（可选）"""
        try:
            if requests is not None:
                r = requests.get(
                    url,
                    headers={
                        'User-Agent': self.ua,
                        'Referer': 'https://streamtape.com/',
                    },
                    timeout=12,
                    verify=False,
                    allow_redirects=True,
                    stream=True,
                )
                final = str(r.url or '')
                # 读一点确认是视频
                try:
                    chunk = next(r.iter_content(64), b'')
                except Exception:
                    chunk = b''
                r.close()
                if 'tapecontent' in final or (chunk and chunk[:4] in (b'\x00\x00\x00', b'ftyp', b'\x00\x00\x00\x18', b'\x00\x00\x00\x20')):
                    return final
                if r.headers.get('Content-Type', '').startswith('video'):
                    return final
            else:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers={
                    'User-Agent': self.ua,
                    'Referer': 'https://streamtape.com/',
                })
                with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                    final = resp.geturl()
                    if 'tapecontent' in final or 'video' in (resp.headers.get('Content-Type') or ''):
                        return final
        except Exception as e:
            print('follow err', e)
        return 

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)|get_video\?', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

# -*- coding: utf-8 -*-
"""
KRX18 https://krx18.com
DooPlay 主题: 列表 article.item + doo_player_ajax → embed
详情阶段解成真实 http embed，播放 parse/嗅探
网络层多路重试，风格参考 SupJav
"""
import re
import json
import time
import sys
from urllib.parse import quote, urlencode

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def init(self, extend=''):
            pass

try:
    import requests
except Exception:
    requests = None

import urllib.request
import ssl

UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
PROXY_BASE = 'https://py.fzcrym.link:1314'
STREAM_API = PROXY_BASE + '/stream?u='
FS_PAGE_API = PROXY_BASE + '/fs?u='



class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://krx18.com'
        self.name = 'KRX18'
        self.ua = UA
        self.channels = [
            ('movies', '全部', '/movies/'),
            ('korea', 'Korea', '/genre/korea/'),
            ('eng-sub', 'Eng Sub', '/genre/eng-sub/'),
            ('xxx', 'X Clip', '/genre/xxx/'),
            ('japan', 'Japan', '/genre/japan/'),
            ('china', 'China', '/genre/china/'),
            ('home', '首页', '/'),
        ]
        self._play_cache = {}
        self._play_ttl = 120

    def getName(self):
        return self.name

    def init(self, extend=''):
        global PROXY_BASE, STREAM_API, FS_PAGE_API
        if not extend:
            return
        s = str(extend).strip()
        if s.startswith('{'):
            try:
                conf = json.loads(s)
                if conf.get('host'):
                    self.host = str(conf['host']).rstrip('/')
                if conf.get('proxy'):
                    PROXY_BASE = str(conf['proxy']).rstrip('/')
                    STREAM_API = PROXY_BASE + '/stream?u='
                    FS_PAGE_API = PROXY_BASE + '/fs?u='
            except Exception:
                pass
        elif s.startswith('http'):
            # 带端口的当代理，否则当 host
            if (':' in s.split('//', 1)[-1] and 
                    any(x in s for x in [':1314', 'proxy', 'fzcrym'])):
                PROXY_BASE = s.rstrip('/')
                STREAM_API = PROXY_BASE + '/stream?u='
                FS_PAGE_API = PROXY_BASE + '/fs?u='
            else:
                self.host = s.rstrip('/')

    def destroy(self):
        pass

    def _headers(self, referer=None, ajax=False):
        h = {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
            'Referer': referer or (self.host + '/'),
        }
        if ajax:
            h['X-Requested-With'] = 'XMLHttpRequest'
            h['Content-Type'] = 'application/x-www-form-urlencoded'
            h['Origin'] = self.host
        return h

    def _get(self, url, referer=None, timeout=28, retries=3):
        if not url.startswith('http'):
            url = self.host + (url if url.startswith('/') else '/' + url)
        headers = self._headers(referer)
        last_err = None
        for _ in range(max(1, retries)):
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            except Exception as e:
                last_err = e
                time.sleep(0.6)
            if requests is not None:
                try:
                    r = requests.get(url, headers=headers, timeout=timeout, verify=False)
                    if r.status_code == 200 and len(r.text) > 500:
                        return r.text
                except Exception as e:
                    last_err = e
        print('GET fail', url, last_err)
        return ''

    def _post(self, url, data, referer, timeout=20):
        body = urlencode(data).encode()
        headers = self._headers(referer, ajax=True)
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception as e:
            print('POST fail', e)
        if requests is not None:
            try:
                r = requests.post(url, data=data, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 200:
                    return r.text
            except Exception as e:
                print('POST requests fail', e)
        return ''


    def _proxy_get(self, url, timeout=90):
        """经代理拉页面/流"""
        try:
            from urllib.parse import quote
            api = STREAM_API + quote(url, safe='')
            return self._get(api, referer=None, timeout=timeout, retries=2)
        except Exception as e:
            print('proxy get', e)
            return ''

    def _stream(self, url, referer='', timeout=90):
        from urllib.parse import quote
        api = STREAM_API + quote(url, safe='')
        if referer:
            api += '&r=' + quote(referer, safe='')
        # 直接请求代理，避免再套 self._get 的 host 拼接
        headers = self._headers(referer or self.host + '/')
        try:
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(api, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception as e:
            print('stream', e)
        if requests is not None:
            try:
                r = requests.get(api, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 200:
                    return r.text
            except Exception as e:
                print('stream req', e)
        return ''

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip().replace('\\/', '/').replace('&amp;', '&')
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
        # DooPlay: <article class="item ...">
        blocks = re.findall(
            r'<article[^>]*class="[^"]*item[^"]*"[^>]*>[\s\S]{0,1800}?</article>',
            html, re.I
        )
        if not blocks:
            blocks = re.findall(
                r'<article[^>]*>[\s\S]{0,1800}?</article>',
                html, re.I
            )
        for block in blocks:
            lm = re.search(
                r'href="(https?://[^"]+/(?:movies|video)/[^"]+|/movies/[^"]+)"[^>]*(?:title="([^"]*)")?',
                block, re.I
            )
            if not lm:
                continue
            vod_id = self._abs(lm.group(1).split('?')[0])
            if vod_id in seen:
                continue
            # 过滤分类页本身
            if re.search(r'/(genre|category|tag)/', vod_id):
                continue
            seen.add(vod_id)
            name = (lm.group(2) or '').strip()
            if not name:
                tm = re.search(r'(?:alt|title)="([^"]{3,200})"', block)
                name = tm.group(1).strip() if tm else vod_id.rstrip('/').rsplit('/', 1)[-1]
            name = name.replace('&#8211;', '-').replace('&amp;', '&').replace('&#8217;', "'")
            # 清理替换字符
            name = name.replace('\ufffd', "'").replace('\xef\xbf\xbd', "'")
            pic = ''
            for pm in re.finditer(r'(?:data-src|src)="([^"]+)"', block, re.I):
                p = pm.group(1)
                if 'placeholder' in p or 'data:image' in p:
                    continue
                if re.search(r'\.(jpg|jpeg|png|webp)', p, re.I) or 'upload' in p or 'wp-content' in p:
                    pic = self._abs(p)
                    break
            videos.append({
                'vod_id': vod_id,
                'vod_name': re.sub(r'\s+', ' ', name)[:120],
                'vod_pic': pic,
                'vod_remarks': self.name,
            })
        return videos

    def homeContent(self, filter=False):
        classes = [{'type_id': c[0], 'type_name': c[1]} for c in self.channels]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        if not html:
            html = self._get(self.host + '/movies/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = max(1, int(pg or 1))
        tid = str(tid or 'movies').strip()
        path = '/movies/'
        for c in self.channels:
            if c[0] == tid:
                path = c[2]
                break
        if path.endswith('/'):
            url = self.host + path if pg == 1 else self.host + path + 'page/%d/' % pg
        else:
            url = self.host + path
            if pg > 1:
                url = url + '/page/%d/' % pg
        html = self._get(url)
        if not html:
            html = self._get(url, retries=4)
        # 首页兜底
        if not html and path != '/':
            html = self._get(self.host + '/')
        videos = self._parse_list(html)
        pages = [int(x) for x in re.findall(r'/page/(\d+)/', html or '')]
        pagecount = max(pages + [pg]) if videos else pg
        return {
            'list': videos, 'page': pg, 'pagecount': pagecount,
            'limit': 24, 'total': pagecount * max(len(videos), 1),
        }

    def searchContent(self, key, quick, pg='1'):
        pg = max(1, int(pg or 1))
        kw = quote(str(key or '').strip())
        if not kw:
            return {'list': []}
        url = '%s/?s=%s' % (self.host, kw)
        if pg > 1:
            url = '%s/page/%d/?s=%s' % (self.host, pg, kw)
        return {
            'list': self._parse_list(self._get(url)),
            'page': pg, 'pagecount': pg + 1, 'limit': 24, 'total': 9999,
        }

    def _extract_players(self, html):
        """data-type / data-post / data-nume"""
        plays = []
        # 顺序: type, post, nume
        opts = re.findall(
            r'data-type=["\']([^"\']+)["\'][^>]*data-post=["\'](\d+)["\'][^>]*data-nume=["\']([^"\']+)',
            html or '', re.I
        )
        if not opts:
            opts2 = re.findall(
                r'data-post=["\'](\d+)["\'][^>]*data-nume=["\']([^"\']+)["\'][^>]*data-type=["\']([^"\']+)',
                html or '', re.I
            )
            opts = [(c, a, b) for a, b, c in opts2]
        # 按钮文字
        names = re.findall(
            r'data-nume=["\'][^"\']+["\'][^>]*>\s*([^<]{1,40})\s*<',
            html or '', re.I
        )
        for i, (typ, post, nume) in enumerate(opts):
            label = names[i].strip() if i < len(names) else ('Server %s' % nume)
            label = re.sub(r'\s+', ' ', label)[:30] or ('Server %s' % nume)
            plays.append((label, post, nume, typ))
        return plays

    def _resolve_player(self, post, nume, typ, detail_url):
        """doo_player_ajax → embed_url"""
        key = '%s|%s|%s' % (post, nume, typ)
        cached = self._play_cache.get(key)
        if cached and time.time() - cached[0] < self._play_ttl:
            return cached[1]
        ajax = self.host + '/wp-admin/admin-ajax.php'
        data = {
            'action': 'doo_player_ajax',
            'post': str(post),
            'nume': str(nume),
            'type': str(typ),
        }
        raw = self._post(ajax, data, detail_url)
        emb = ''
        if raw:
            try:
                j = json.loads(raw)
                emb_html = str(j.get('embed_url') or j.get('embed') or '')
            except Exception:
                emb_html = raw
            m = re.search(r'src=["\'](https?://[^"\']+)', emb_html, re.I)
            if m:
                emb = m.group(1).replace('\\/', '/')
            if not emb:
                m = re.search(r'https?://(?:filemoon|streamtape|voe|dood|hexload|luluvdo)[^\s"\'<>]+', emb_html, re.I)
                if m:
                    emb = m.group(0)
        if emb:
            self._play_cache[key] = (time.time(), emb)
        return emb

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(raw or '').strip()
        if not url.startswith('http'):
            url = self._abs(url)
        html = self._get(url)
        if not html:
            html = self._get(url, retries=4)
        if not html:
            return {'list': []}

        name = ''
        m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
        if m:
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not name:
            m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                name = re.sub(r'\s*[|\-–].*$', '', m.group(1)).strip()
        name = name.replace('&#8211;', '-').replace('&amp;', '&').replace('\ufffd', "'")

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = self._abs(m.group(1))

        players = self._extract_players(html)
        plays = []
        for label, post, nume, typ in players:
            emb = self._resolve_player(post, nume, typ, url)
            if emb:
                plays.append((label, emb))
            else:
                # 保留 token，播放时再解
                plays.append((label, '%s|%s|%s' % (post, nume, typ)))

        if not plays:
            plays = [('原页', url)]

        # 多线路：每个 Server 独立 play_from，避免壳子丢 URL
        froms = []
        urls = []
        for n, u in plays:
            froms.append(n)
            urls.append('正片$' + u)
        return {
            'list': [{
                'vod_id': url,
                'vod_name': name or self.name,
                'vod_pic': pic,
                'vod_remarks': '',
                'vod_content': '',
                'vod_play_from': '$$$'.join(froms),
                'vod_play_url': '$$$'.join(urls),
            }]
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
        # 去掉可能的 正片$ 前缀
        if '$' in play and not play.startswith('http'):
            play = play.split('$', 1)[-1].strip()

        # token: post|nume|type
        if re.match(r'^\d+\|[^|]+\|\w+$', play):
            post, nume, typ = play.split('|', 2)
            emb = self._resolve_player(post, nume, typ, self.host + '/')
            if emb:
                play = emb
            else:
                return {'parse': 0, 'jx': 0, 'url': '', 'playUrl': '', 'header': header}

        if not play:
            return {'parse': 0, 'jx': 0, 'url': '', 'playUrl': '', 'header': header}

        if re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {
                'parse': 0, 'jx': 0, 'url': play, 'playUrl': play,
                'header': header,
            }

        # filemoon / hexload / 其他 embed
        if play.startswith('http'):
            header['Referer'] = self.host + '/'
            if 'filemoon' in play or 'hexload' in play or '/e/' in play or 'embed' in play:
                header['Referer'] = play
                # 1) 代理拉 embed 页，尝试抽 m3u8/mp4
                try:
                    page = self._stream(play, referer=self.host + '/')
                    if page and len(page) > 200:
                        import re as _re
                        hits = _re.findall(
                            r'https?://[^\s"\'<>\\]+\.(?:m3u8|mp4)[^\s"\'<>\\]*',
                            page, _re.I
                        )
                        for h in hits:
                            if 'test-videos' in h or 'preview' in h.lower():
                                continue
                            # 分片绑 IP 的走代理转流
                            from urllib.parse import quote
                            if h.lower().endswith('.m3u8') or '.m3u8?' in h.lower():
                                proxied = STREAM_API + quote(h, safe='')
                                return {
                                    'parse': 0, 'jx': 0,
                                    'url': proxied, 'playUrl': proxied,
                                    'header': {'User-Agent': self.ua},
                                }
                            return {
                                'parse': 0, 'jx': 0,
                                'url': h, 'playUrl': h,
                                'header': header,
                            }
                        # packer
                        if 'eval(function(p,a,c,k,e' in page:
                            # 简单再扫一次解包后的明文
                            hits2 = _re.findall(
                                r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*',
                                page
                            )
                            if hits2:
                                from urllib.parse import quote
                                proxied = STREAM_API + quote(hits2[0], safe='')
                                return {
                                    'parse': 0, 'jx': 0,
                                    'url': proxied, 'playUrl': proxied,
                                    'header': {'User-Agent': self.ua},
                                }
                except Exception as e:
                    print('embed resolve', e)
                # 2) 兜底：代理打开 embed（部分壳子可跟 302）
                try:
                    from urllib.parse import quote
                    proxied = STREAM_API + quote(play, safe='')
                    # 仍给 parse=1，同时带上代理地址备选
                    return {
                        'parse': 1, 'jx': 0,
                        'url': play, 'playUrl': play,
                        'header': header,
                    }
                except Exception:
                    pass
            return {
                'parse': 1, 'jx': 0,
                'url': play, 'playUrl': play,
                'header': header,
            }
        return {
            'parse': 1, 'jx': 0, 'url': play, 'playUrl': play,
            'header': header,
        }

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

# -*- coding: utf-8 -*-
# 4K影视 https://www.4kvm.tv/  v1.3
# 适配 OK影视 / 影视仓：纯 Python WASM 签名（需 wasmtime），详情只打包参数，播放时解析 m3u8
# 依赖：pip install wasmtime
# 同目录 4kvm_wasm/nbmovie_wasm_bg.wasm + sign_pure.py
import os
import re
import sys
import json
import ssl
import urllib.request
import urllib.parse
import http.cookiejar

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass

VERSION = '1.3.0'
HOST = 'https://www.4kvm.tv'
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
)


def _wasm_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(here, '4kvm_wasm'),
        os.path.join(here, 'wasm'),
        '/home/workdir/artifacts/4kvm_wasm',
        '/tmp/4kvm_wasm',
    ]


class Spider(BaseSpider):
    def __init__(self):
        self.host = HOST
        self.headers = {
            'User-Agent': UA,
            'Referer': HOST + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE
        self._cj = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cj),
            urllib.request.HTTPSHandler(context=self._ssl),
        )
        self._wasm_dir = None
        self._sign_fn = None

    def getName(self):
        return '4K影视'

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')
            self.headers['Referer'] = self.host + '/'
        self._prepare_sign()

    def _prepare_sign(self):
        for d in _wasm_dirs():
            wasm = os.path.join(d, 'nbmovie_wasm_bg.wasm')
            if os.path.isfile(wasm):
                self._wasm_dir = d
                break
        if not self._wasm_dir:
            # 尝试下载
            d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '4kvm_wasm')
            try:
                os.makedirs(d, exist_ok=True)
                bg = self._download_bytes(self.host + '/static/wasm/nbmovie_wasm_bg.d5d51939.wasm')
                if bg and len(bg) > 1000:
                    open(os.path.join(d, 'nbmovie_wasm_bg.wasm'), 'wb').write(bg)
                    self._wasm_dir = d
            except Exception as e:
                print('download wasm fail', e, file=sys.stderr)

        # 优先纯 Python wasmtime
        if self._wasm_dir:
            sign_py = os.path.join(self._wasm_dir, 'sign_pure.py')
            if not os.path.isfile(sign_py):
                # 同级目录找
                alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), '4kvm_wasm', 'sign_pure.py')
                if os.path.isfile(alt):
                    sign_py = alt
            try:
                import importlib.util
                # 确保 wasm 路径可被 sign_pure 找到：把目录加入 path
                if self._wasm_dir not in sys.path:
                    sys.path.insert(0, self._wasm_dir)
                # 直接 import
                try:
                    import sign_pure
                    self._sign_fn = sign_pure.build_play_url
                    # 冒烟
                    u = self._sign_fn('1', 'a', '1080', '0')
                    if '/video/play' in str(u):
                        print('sign: wasmtime ok', file=sys.stderr)
                        return
                except Exception as e:
                    print('sign_pure fail:', e, file=sys.stderr)
            except Exception as e:
                print('sign import fail:', e, file=sys.stderr)

        # 回退 node
        if self._wasm_dir and self._find_node():
            self._sign_fn = self._sign_node
            print('sign: node fallback', file=sys.stderr)
            return
        print('sign: UNAVAILABLE (pip install wasmtime 或安装 node)', file=sys.stderr)

    def _find_node(self):
        for n in ('node', 'nodejs'):
            for path in os.environ.get('PATH', '').split(os.pathsep):
                p = os.path.join(path, n)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p
        return None

    def _sign_node(self, dataid, secret, quality='1080', play_key='0'):
        import subprocess
        d = self._wasm_dir
        js = os.path.join(d, 'nbmovie_wasm.js')
        bg = os.path.join(d, 'nbmovie_wasm_bg.wasm')
        if not os.path.isfile(js):
            # 下载 glue
            try:
                open(js, 'wb').write(
                    self._download_bytes(self.host + '/static/wasm/nbmovie_wasm.426511b7.js')
                )
            except Exception:
                return ''
        open(os.path.join(d, 'package.json'), 'w').write('{"type":"module"}\n')
        script = (
            'import { readFileSync } from "fs";\n'
            'import * as wasm from "file://%s";\n'
            'await wasm.default({ module_or_path: readFileSync("%s") });\n'
            'console.log(wasm.build_play_url(%s,%s,%s,%s));\n'
        ) % (
            js, bg,
            json.dumps(str(dataid)), json.dumps(str(secret)),
            json.dumps(str(quality)), json.dumps(str(play_key)),
        )
        try:
            out = subprocess.check_output(
                [self._find_node(), '--input-type=module', '-e', script],
                stderr=subprocess.STDOUT, timeout=20, cwd=d,
            )
            for line in reversed(out.decode().strip().splitlines()):
                if '/video/play' in line:
                    return line.strip()
            return out.decode().strip().splitlines()[-1]
        except Exception as e:
            print('node sign err', e, file=sys.stderr)
            return ''

    def _download_bytes(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with self._opener.open(req, timeout=30) as r:
            return r.read()

    def _get(self, url, headers=None, timeout=20):
        h = dict(self.headers)
        if headers:
            h.update(headers)
        try:
            if hasattr(self, 'fetch'):
                try:
                    r = self.fetch(url, headers=h)
                    if isinstance(r, str):
                        return r
                    if hasattr(r, 'text'):
                        return r.text or ''
                except Exception:
                    pass
            req = urllib.request.Request(url, headers=h, method='GET')
            with self._opener.open(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception as e:
            print('_get', url, e, file=sys.stderr)
            return ''

    def _build_path(self, dataid, secret, userlink, quality='1080'):
        if not self._sign_fn:
            self._prepare_sign()
        if not self._sign_fn:
            return ''
        try:
            return self._sign_fn(str(dataid), str(secret), str(quality), str(userlink or '0'))
        except Exception as e:
            print('build_path', e, file=sys.stderr)
            return ''

    def _resolve_m3u8(self, dataid, secret, userlink, quality='1080'):
        path = self._build_path(dataid, secret, userlink, quality)
        if not path:
            return []
        url = path if path.startswith('http') else (self.host + path)
        self._get(self.host + '/play/' + secret)
        body = self._get(url, headers={
            'Accept': 'application/json,*/*',
            'Referer': self.host + '/play/' + secret,
        })
        if not body:
            return []
        try:
            data = json.loads(body)
        except Exception:
            return []
        if data.get('code') != 200 or not data.get('data'):
            return []
        out = []
        for q in data['data'].get('quality_urls') or []:
            u = q.get('url') or ''
            if not u or u == '1' or q.get('locked'):
                continue
            if re.search(r'\.(m3u8|mp4)(\?|$)', u, re.I):
                out.append(u)
        return out

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        pat = (
            r'<a href="(/play/([a-z0-9]+))" class="block">\s*'
            r'<div[^>]*>\s*<img[^>]+data-src="([^"]*)"[^>]*alt="([^"]*)"[\s\S]*?'
            r'<h3[^>]*>\s*([^<]+?)\s*</h3>'
        )
        for m in re.finditer(pat, html, re.I):
            path, pid, pic, alt, name = m.groups()
            if pid in seen:
                continue
            seen.add(pid)
            pic = (pic or '').replace('&amp;', '&')
            if pic.startswith('//'):
                pic = 'https:' + pic
            videos.append({
                'vod_id': path,
                'vod_name': (name or alt or pid).strip(),
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return videos

    def _extract_userlink(self, html):
        m = re.search(r"userlink:'([^']+)'", html or '')
        if m:
            return m.group(1)
        m = re.search(r'userlink:"([^"]+)"', html or '')
        if m:
            return m.group(1)
        return '0'

    def homeContent(self, filter):
        return {
            'class': [
                {'type_name': '电影', 'type_id': 'movie'},
                {'type_name': '剧集', 'type_id': 'tv'},
                {'type_name': '动漫', 'type_id': 'anime'},
            ],
            'filters': {},
        }

    def homeVideoContent(self):
        return {'list': self._parse_list(self._get(self.host + '/'))[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        url = '%s/%s' % (self.host, tid or 'movie')
        if pg > 1:
            url += '?page=%d' % pg
        videos = self._parse_list(self._get(url))
        return {
            'list': videos, 'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 24, 'total': 999999,
        }

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        url = '%s/search?q=%s' % (self.host, urllib.parse.quote(key or ''))
        if pg > 1:
            url += '&page=%d' % pg
        videos = self._parse_list(self._get(url))
        return {
            'list': videos, 'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 24, 'total': 999999,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        path = str(raw)
        if path.startswith('http'):
            path = path.replace(self.host, '')
        if not path.startswith('/play/'):
            path = '/play/' + path.lstrip('/')
        page = self.host + path
        html = self._get(page)
        secret = (re.search(r'/play/([a-z0-9]+)', path, re.I) or [None, ''])[1]
        userlink = self._extract_userlink(html)

        title = ''
        tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or re.search(r'<title>([^<]+)</title>', html)
        if tm:
            title = re.sub(r'\s*-\s*第\d+集\s*$', '', tm.group(1).replace('-4k影视', '')).strip()

        pic = ''
        pm = re.search(r'data-poster="([^"]+)"', html) or re.search(
            r'property="og:image"\s+content="([^"]+)"', html)
        if pm:
            pic = pm.group(1).replace('&amp;', '&')

        lines = re.findall(r"lineName:\s*'([^']+)'\s*,\s*episodeCount:\s*(\d+)", html) or [('默认', '1')]
        ep_map = {}
        for m in re.finditer(r'data-line="(\d+)"[^>]*data-episode="(\d+)"\s+dataid="(\d+)"', html):
            ep_map.setdefault(m.group(1), []).append((int(m.group(2)), m.group(3)))

        play_from, play_urls = [], []
        for idx, (line_name, ep_count) in enumerate(lines, start=1):
            play_from.append(line_name)
            eps = ep_map.get(str(idx), [])
            parts = []
            if eps:
                for ep_i, dataid in sorted(eps, key=lambda x: x[0]):
                    # 参数打包，播放时再解析（快、稳）
                    parts.append('第%d集$%s@@@%s@@@%s' % (ep_i, dataid, secret, userlink))
            else:
                for i in range(1, max(int(ep_count), 1) + 1):
                    parts.append('第%d集$%s?line=%d&ep=%d' % (i, page, idx, i))
            play_urls.append('#'.join(parts) if parts else ('播放$%s' % page))

        return {
            'list': [{
                'vod_id': path,
                'vod_name': title or path,
                'vod_pic': pic,
                'vod_content': title,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': UA,
            'Referer': self.host + '/',
            # CDN 可能校验
            'Origin': self.host,
        }
        play = str(id or '').strip()

        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

        if '@@@' in play:
            segs = play.split('@@@')
            dataid = segs[0]
            secret = segs[1] if len(segs) > 1 else ''
            userlink = segs[2] if len(segs) > 2 else '0'
            urls = self._resolve_m3u8(dataid, secret, userlink, '1080')
            if urls:
                return {
                    'parse': 0,
                    'jx': 0,
                    'url': urls[0],
                    'header': {
                        'User-Agent': UA,
                        'Referer': self.host + '/',
                        'Origin': self.host,
                    },
                }
            # 失败提示
            print('resolve failed dataid=', dataid, 'sign=', bool(self._sign_fn), file=sys.stderr)
            return {
                'parse': 1,
                'jx': '1',
                'url': self.host + '/play/' + secret,
                'header': header,
            }

        if play.startswith('/'):
            play = self.host + play
        if play.startswith('http'):
            return {'parse': 1, 'jx': '1', 'url': play.split('?')[0], 'header': header}
        return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|flv|mkv)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('VERSION', VERSION)
    print('wasm_dir', sp._wasm_dir, 'sign', bool(sp._sign_fn))
    hv = sp.homeVideoContent()
    print('home', len(hv.get('list') or []))
    if hv.get('list'):
        d = sp.detailContent([hv['list'][0]['vod_id']])
        vod = (d.get('list') or [{}])[0]
        print('detail', vod.get('vod_name'), (vod.get('vod_play_url') or '')[:80])
        first = (vod.get('vod_play_url') or '').split('#')[0].split('$')[-1]
        p = sp.playerContent('x', first, [])
        print('player', p.get('parse'), str(p.get('url') or '')[:100])

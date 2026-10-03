# -*- coding: utf-8 -*-
# 18AV https://18av01.cc/zh/
# v1.4 影视仓适配：多线路清晰度 $$$ 分隔，只出 m3u8；增强 AES 兼容
import re
import json
import sys
import base64
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

# AES 双后端
AES_BACKEND = None
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    AES_BACKEND = 'cryptography'
except ImportError:
    try:
        from Crypto.Cipher import AES as PCAES
        AES_BACKEND = 'pycryptodome'
    except ImportError:
        try:
            from Cryptodome.Cipher import AES as PCAES
            AES_BACKEND = 'pycryptodome'
        except ImportError:
            AES_BACKEND = None


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://18av01.cc'
        self.base = '/zh'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        )
        self.aes_key = b'f2de1cc5a09e548a'
        self.aes_iv = b'14799105d5ff0474'
        self.hcdeed = 21
        self.hadeed = 26
        self.channels = {
            'chinese': {'name': '中文字幕', 'path': '/zh/chinese_random/all/index.html'},
            'censored': {'name': '有码AV', 'path': '/zh/censored_random/all/index.html'},
            'uncensored': {'name': '无码AV', 'path': '/zh/uncensored_random/all/index.html'},
            'amateur': {'name': '素人AV', 'path': '/zh/amateurjav_random/all/index.html'},
            'mosaic': {'name': '无码破解', 'path': '/zh/reducing-mosaic_random/all/index.html'},
            'animation': {'name': 'H动画', 'path': '/zh/animation_random/all/index.html'},
            'c_anim': {'name': 'H有码动画', 'path': '/zh/CensoredAnimation_random/all/index.html'},
            'u_anim': {'name': 'H无码动画', 'path': '/zh/UncensoredAnimation_random/all/index.html'},
            'td_anim': {'name': 'H_3D动画', 'path': '/zh/tdAnimation_random/all/index.html'},
            'dt': {'name': '国产自拍', 'path': '/zh/dt_random/all/index.html'},
            'news': {'name': '每日更新', 'path': '/zh/content_news/all/index.html'},
        }
        self.name_to_id = {}
        for _k, _v in self.channels.items():
            self.name_to_id[_k] = _k
            self.name_to_id[_v['name']] = _k

    def getName(self):
        return '18AV'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass
        if AES_BACKEND is None:
            print('WARN: 无 AES 库，请 pip install cryptography 或 pycryptodome')

    def _headers(self, referer=None, accept=None):
        return {
            'User-Agent': self.ua,
            'Accept': accept or 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or (self.host + self.base + '/'),
        }

    def _get(self, url, referer=None, accept=None):
        try:
            headers = self._headers(referer, accept)
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=headers, timeout=20, verify=False)
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

    def _refresh_crypto(self, html):
        m = re.search(r"argdeqweqweqwe\s*=\s*'([0-9a-fA-F]{16})'", html or '')
        if m:
            self.aes_key = m.group(1).encode('utf-8')
        m = re.search(r"hdddedg252\s*=\s*'([0-9a-fA-F]{16})'", html or '')
        if m:
            self.aes_iv = m.group(1).encode('utf-8')
        m = re.search(r'hadeedg252\s*=\s*(\d+)', html or '')
        if m:
            self.hadeed = int(m.group(1))
        m = re.search(r'hcdeedg252\s*=\s*(\d+)', html or '')
        if m:
            self.hcdeed = int(m.group(1))

    def _decrypto(self, g):
        if not g:
            return ''
        radix = self.hcdeed if self.hcdeed >= 2 else 21
        sep = chr((radix if radix <= 25 else (radix % 25)) + 97)
        out = []
        for p in g.split(sep):
            if not p:
                continue
            try:
                k = int(p, radix) ^ self.hadeed
                if 0 <= k <= 0x10FFFF:
                    out.append(chr(k))
            except Exception:
                continue
        return ''.join(out)

    def _aes_decrypt(self, b64text):
        if not b64text or AES_BACKEND is None:
            return ''
        try:
            pad_len = (-len(b64text)) % 4
            raw = base64.b64decode(b64text + ('=' * pad_len))
            if AES_BACKEND == 'cryptography':
                cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv))
                dec = cipher.decryptor()
                pt = dec.update(raw) + dec.finalize()
            else:
                cipher = PCAES.new(self.aes_key, PCAES.MODE_CBC, self.aes_iv)
                pt = cipher.decrypt(raw)
            pad = pt[-1]
            if isinstance(pad, str):
                pad = ord(pad)
            if 1 <= pad <= 16:
                pt = pt[:-pad]
            return pt.decode('utf-8', 'ignore')
        except Exception as e:
            print('AES error', e)
            return ''

    def _decode_play_id(self, enc):
        step1 = self._decrypto(enc)
        if not step1:
            return ''
        return self._aes_decrypt(step1)

    def _parse_mvarr(self, html):
        items = []
        if not html:
            return items
        for m in re.finditer(r"mvarr\['(\d+_\d+)'\]\s*=\s*\[\[", html):
            label = m.group(1)
            chunk = html[m.end():m.end() + 2500]
            end = chunk.find('];')
            if end > 0:
                chunk = chunk[:end]
            parts = re.findall(r"'([^']*)'", chunk)
            enc = ''
            play_base = ''
            for p in parts:
                if not enc and re.match(r'^[0-9a-z]{20,}$', p):
                    enc = p
                if 'play.php' in p and 'id=' in p:
                    play_base = p
            if enc and play_base:
                items.append((label, enc, play_base))
        return items

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'href="((?:https?://(?:www\.)?18av01\.cc)?(/zh/[\w-]+_content/\d+/[^"]+\.html))"',
            html, re.I
        ):
            full = self._abs(m.group(1) if m.group(1).startswith('http') else m.group(2))
            if full in seen:
                continue
            seen.add(full)
            block = html[max(0, m.start() - 300):m.end() + 500]
            title = ''
            tm = re.search(r'(?:title|alt)=["\']([^"\']{2,200})["\']', block)
            if tm:
                title = tm.group(1).strip()
            if not title:
                cm = re.search(r'/([^/]+)\.html', full)
                title = cm.group(1) if cm else '18AV'
            pic = ''
            for pat in (
                r'data-src=["\']([^"\']+)["\']',
                r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            ):
                pm = re.search(pat, block, re.I)
                if pm and not re.search(r'logo|loading|icon', pm.group(1), re.I):
                    pic = self._abs(pm.group(1))
                    break
            tips = ''
            dm = re.search(r'(\d+\s*分)', block)
            if dm:
                tips = dm.group(1)
            videos.append({
                'vod_id': full,
                'vod_name': title[:120],
                'vod_pic': pic,
                'vod_remarks': tips,
            })
        return videos

    def _m3u8_from_play_page(self, play_url, referer=''):
        html = self._get(play_url, referer=referer or (self.host + self.base + '/'))
        if not html:
            return []
        urls, seen = [], set()
        for m in re.finditer(
            r"\{src:\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"][^}]*size:\s*(\d+)",
            html, re.I
        ):
            u = self._abs(m.group(1))
            if u in seen:
                continue
            seen.add(u)
            urls.append((int(m.group(2)), m.group(2) + 'P', u))
        if not urls:
            for m in re.finditer(
                r"size:\s*(\d+)[^}]*src:\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]",
                html, re.I
            ):
                u = self._abs(m.group(2))
                if u in seen:
                    continue
                seen.add(u)
                urls.append((int(m.group(1)), m.group(1) + 'P', u))
        if not urls:
            for u in re.findall(r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html):
                u = self._abs(u)
                if u in seen:
                    continue
                seen.add(u)
                urls.append((0, 'HLS', u))
        urls.sort(key=lambda x: -x[0])
        return [(name, u) for _, name, u in urls]

    def _collect_resolutions(self, html, page_url=''):
        """
        返回有序 dict: {'1080P': m3u8, '720P': m3u8, ...}
        以及 play.php 兜底列表
        """
        res_map = {}
        php_list = []
        if not html:
            return res_map, php_list
        self._refresh_crypto(html)
        for label_key, enc_id, play_base in self._parse_mvarr(html):
            decoded = self._decode_play_id(enc_id)
            if not decoded:
                print('decode fail', enc_id[:40])
                continue
            play_page = self._abs(play_base + decoded)
            req = re.search(r'numresolution=(\d+)', play_base)
            req_name = (req.group(1) + 'P') if req else None
            if play_page not in php_list:
                php_list.append((req_name or ('线路' + label_key.split('_')[0]), play_page))
            for lab, u in self._m3u8_from_play_page(play_page, page_url):
                if not re.search(r'\.m3u8(\?|$)', u, re.I):
                    continue
                key = lab if lab != 'HLS' else (req_name or 'HLS')
                # 同清晰度保留先解析到的
                if key not in res_map:
                    res_map[key] = u
        return res_map, php_list

    def _resolve_tid(self, tid):
        s = str(tid or 'chinese').strip()
        if s in self.channels:
            return s
        if getattr(self, 'name_to_id', None) and s in self.name_to_id:
            return self.name_to_id[s]
        return 'chinese'

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        html = self._get(self.host + '/zh/chinese_random/all/index.html')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = self._resolve_tid(tid)
        info = self.channels.get(tid) or self.channels['chinese']
        path = info['path']
        if pg <= 1:
            url = self.host + path
        else:
            url = self.host + path.replace('index.html', 'index_%d.html' % pg)
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
            page_url = self.host + (page_url if page_url.startswith('/') else self.base + '/' + page_url)
        html = self._get(page_url)
        if not html:
            return result

        name = ''
        m = re.search(r'<h1[^>]*>\s*<b>([^<]+)</b>', html, re.I)
        if m:
            name = m.group(1).strip()
        if not name:
            m = re.search(r'<title>([^<]+)</title>', html, re.I)
            if m:
                name = re.sub(r'\s*18AV.*$', '', m.group(1), flags=re.I).strip()
        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = self._abs(m.group(1))

        res_map, php_list = self._collect_resolutions(html, page_url)

        # 按清晰度从高到低
        def res_key(k):
            m = re.search(r'(\d+)', k)
            return -(int(m.group(1)) if m else 0)

        ordered = sorted(res_map.keys(), key=res_key)

        # 影视仓多线路：每个清晰度一条线路
        # vod_play_from: 1080P$$$720P
        # vod_play_url:  正片$url1080$$$正片$url720
        if ordered:
            play_from = '$$$'.join(ordered)
            play_url = '$$$'.join(['正片$%s' % res_map[k] for k in ordered])
        elif php_list:
            # 解密失败或未抽到 m3u8：把 play.php 交给 playerContent
            play_from = '$$$'.join([n for n, _ in php_list])
            play_url = '$$$'.join(['正片$%s' % u for _, u in php_list])
        else:
            # 最终兜底：详情页，playerContent 再解
            play_from = '18AV'
            play_url = '正片$%s' % page_url

        result['list'] = [{
            'vod_id': page_url,
            'vod_name': name or '18AV',
            'vod_pic': pic,
            'vod_remarks': ordered[0] if ordered else '',
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
        url = self.host + '/zh/search/?kw=' + quote(key)
        if pg > 1:
            url += '&page=%d' % pg
        html = self._get(url)
        videos = self._parse_list(html)
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
            'Referer': self.host + '/js/player/play.php',
            'Origin': self.host,
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        if play.startswith('//'):
            play = 'https:' + play

        # 已是直链
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

        # play.php → m3u8
        if 'play.php' in play:
            m3u8s = self._m3u8_from_play_page(play, self.host + self.base + '/')
            if m3u8s:
                return {'parse': 0, 'jx': 0, 'url': m3u8s[0][1], 'header': header}

        if not play.startswith('http'):
            play = self._abs(play)

        # 详情页重新解码
        if '_content/' in play or re.search(r'\.html(\?|$)', play):
            html = self._get(play, referer=self.host + self.base + '/')
            res_map, php_list = self._collect_resolutions(html or '', play)
            if res_map:
                ordered = sorted(res_map.keys(), key=lambda k: -(int(re.search(r'(\d+)', k).group(1)) if re.search(r'(\d+)', k) else 0))
                return {'parse': 0, 'jx': 0, 'url': res_map[ordered[0]], 'header': header}
            for _, php in php_list:
                m3u8s = self._m3u8_from_play_page(php, play)
                if m3u8s:
                    return {'parse': 0, 'jx': 0, 'url': m3u8s[0][1], 'header': header}

        return {'parse': 0, 'jx': 0, 'url': '', 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    print('AES_BACKEND', AES_BACKEND)
    sp = Spider()
    sp.init()
    r = sp.categoryContent('chinese', 1, False, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        d = sp.detailContent([r['list'][0]['vod_id']])
        item = d['list'][0] if d.get('list') else {}
        print('name', (item.get('vod_name') or '')[:40])
        print('from', item.get('vod_play_from'))
        print('url', (item.get('vod_play_url') or '')[:250])
        # simulate player
        parts = (item.get('vod_play_url') or '').split('$$$')
        if parts:
            u = parts[0].split('$')[-1]
            p = sp.playerContent('1080P', u, [])
            print('player', (p.get('url') or '')[:90], 'parse', p.get('parse'))

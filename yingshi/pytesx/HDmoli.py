# -*- coding: utf-8 -*-
"""
HDmoli https://www.hdmoli.me/
修复：纯 Python AES 解密（不依赖 pycryptodome/node）
encrypt3 = smartplay API + AES-CBC(MD5(timestamp+SALT))
"""
import sys
import re
import json
import base64
import time
import hashlib
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

        def post(self, url, data=None, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.post(url, data=data, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


SMART_API = 'https://hd.ticktockwow.com/smartplay-cache/api/webvideo_ty.php'
AES_SALT = 'RY7e48naFXPsLJC'


# ==================== 纯 Python AES-128-CBC ====================
# 不依赖 pycryptodome，TVBox 精简环境也能跑
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0]*256
for i, v in enumerate(_SBOX):
    _INV_SBOX[v] = i
_RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]


def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r & 0xff


def _key_expansion(key):
    # key: 16 bytes -> 11 round keys (176 bytes)
    w = list(key)
    for i in range(4, 44):
        t = w[(i-1)*4:(i-1)*4+4]
        if i % 4 == 0:
            t = [_SBOX[t[1]] ^ _RCON[i // 4], _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]]
        for j in range(4):
            w.append(w[(i-4)*4+j] ^ t[j])
    return [w[i*16:(i+1)*16] for i in range(11)]


def _add_round_key(state, rk):
    return [state[i] ^ rk[i] for i in range(16)]


def _inv_shift_rows(s):
    return [
        s[0], s[13], s[10], s[7],
        s[4], s[1], s[14], s[11],
        s[8], s[5], s[2], s[15],
        s[12], s[9], s[6], s[3],
    ]


def _inv_sub_bytes(s):
    return [_INV_SBOX[b] for b in s]


def _inv_mix_columns(s):
    out = [0]*16
    for c in range(4):
        i = c*4
        a0,a1,a2,a3 = s[i],s[i+1],s[i+2],s[i+3]
        out[i]   = _mul(a0,0x0e)^_mul(a1,0x0b)^_mul(a2,0x0d)^_mul(a3,0x09)
        out[i+1] = _mul(a0,0x09)^_mul(a1,0x0e)^_mul(a2,0x0b)^_mul(a3,0x0d)
        out[i+2] = _mul(a0,0x0d)^_mul(a1,0x09)^_mul(a2,0x0e)^_mul(a3,0x0b)
        out[i+3] = _mul(a0,0x0b)^_mul(a1,0x0d)^_mul(a2,0x09)^_mul(a3,0x0e)
    return out


def _decrypt_block(block, round_keys):
    state = _add_round_key(list(block), round_keys[10])
    for rnd in range(9, 0, -1):
        state = _inv_shift_rows(state)
        state = _inv_sub_bytes(state)
        state = _add_round_key(state, round_keys[rnd])
        state = _inv_mix_columns(state)
    state = _inv_shift_rows(state)
    state = _inv_sub_bytes(state)
    state = _add_round_key(state, round_keys[0])
    return bytes(state)


def aes128_cbc_decrypt(cipher_bytes, key, iv):
    """AES-128-CBC decrypt + PKCS7 unpad. key/iv: 16 bytes."""
    if len(key) != 16 or len(iv) != 16:
        raise ValueError('key/iv must be 16 bytes')
    if len(cipher_bytes) % 16 != 0 or not cipher_bytes:
        raise ValueError('cipher length')
    rks = _key_expansion(list(key))
    prev = iv
    out = bytearray()
    for i in range(0, len(cipher_bytes), 16):
        block = cipher_bytes[i:i+16]
        dec = _decrypt_block(block, rks)
        out.extend(bytes(dec[j] ^ prev[j] for j in range(16)))
        prev = block
    pad = out[-1]
    if 1 <= pad <= 16 and out[-pad:] == bytes([pad])*pad:
        out = out[:-pad]
    return bytes(out)


def aes_decrypt_smart(cipher_b64, timestamp):
    """MD5(timestamp+SALT) -> iv=前16hex字符utf8, key=后16hex字符utf8"""
    try:
        h = hashlib.md5((str(timestamp) + AES_SALT).encode('utf-8')).hexdigest()
        key = h[16:32].encode('utf-8')
        iv = h[0:16].encode('utf-8')
        raw = base64.b64decode(cipher_b64)
        pt = aes128_cbc_decrypt(raw, key, iv)
        text = pt.decode('utf-8', 'ignore')
        return text if text.startswith('http') else ''
    except Exception as e:
        print('aes_decrypt_smart', e)
        return ''


class Spider(Spider):
    host = 'https://www.hdmoli.me'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Referer': 'https://www.hdmoli.me/',
    }
    classes = [
        {'type_id': '1', 'type_name': '电影'},
        {'type_id': '2', 'type_name': '电视剧'},
        {'type_id': '3', 'type_name': '纪录片'},
        {'type_id': '4', 'type_name': '动漫'},
        {'type_id': '5', 'type_name': '综艺'},
    ]

    def init(self, extend=''):
        if extend and str(extend).strip().startswith('http'):
            self.host = str(extend).strip().rstrip('/')
            self.headers['Referer'] = self.host + '/'

    def getName(self):
        return 'HDmoli'

    def isVideoFormat(self, url):
        u = str(url or '').lower()
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv)(?:[?#]|$)', u)) or any(
            x in u for x in ('samtory', 'pcdn', 'getm3u8', 'nbyjson', 'auth_key=')
        )

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _resp_text(self, r):
        if r is None:
            return ''
        if isinstance(r, str):
            return r
        if hasattr(r, 'text'):
            return r.text or ''
        if hasattr(r, 'content'):
            c = r.content
            if isinstance(c, bytes):
                return c.decode('utf-8', 'ignore')
            return str(c or '')
        return str(r)

    def _get(self, url, headers=None):
        try:
            r = self.fetch(url, headers=headers or self.headers)
            return self._resp_text(r)
        except Exception as e:
            print('get', url, e)
            return ''

    def _get_json(self, url):
        try:
            return json.loads(self._get(url) or '{}')
        except Exception:
            return {}

    def _post_json(self, url, data):
        h = dict(self.headers)
        h['Content-Type'] = 'application/json'
        h['Origin'] = self.host
        try:
            # 兼容不同 base.spider：有的 post 吃 data=str，有的吃 json=
            body = json.dumps(data, ensure_ascii=False)
            try:
                r = self.post(url, data=body, headers=h)
            except TypeError:
                r = self.post(url, body, h)
            text = self._resp_text(r)
            return json.loads(text) if text else {}
        except Exception as e:
            print('post_json', e)
            return {}

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': {}}

    def homeVideoContent(self):
        try:
            return {'list': self._parse_list(self._get(self.host + '/'))[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        pagecount = pg
        total = 9999
        try:
            data = self._get_json(f'{self.host}/index.php/ajax/data?mid=1&tid={tid}&page={pg}&limit=24')
            for i in (data.get('list') or []):
                videos.append({
                    'vod_id': str(i.get('vod_id') or ''),
                    'vod_name': i.get('vod_name') or '',
                    'vod_pic': str(i.get('vod_pic') or '').replace('&amp;', '&'),
                    'vod_remarks': i.get('vod_remarks') or '',
                })
            pagecount = int(data.get('pagecount') or pagecount)
            total = int(data.get('total') or total)
        except Exception as e:
            print('category ajax', e)
        if not videos:
            # 兼容 show / type 列表页
            for path in (
                f'{self.host}/show/{tid}--------{pg}---.html',
                f'{self.host}/type/{tid}-{pg}.html',
                f'{self.host}/vod/show/id/{tid}/page/{pg}.html',
            ):
                videos = self._parse_list(self._get(path))
                if videos:
                    break
            if len(videos) >= 20:
                pagecount = pg + 1
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount if pagecount >= pg else pg,
            'limit': 24,
            'total': total,
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        try:
            return {
                'list': self._parse_list(self._get(f'{self.host}/search/-------------.html?wd={quote(key)}')),
                'page': pg,
            }
        except Exception:
            return {'list': [], 'page': pg}

    def detailContent(self, ids):
        try:
            raw_id = ids[0] if isinstance(ids, (list, tuple)) else ids
            vod_id = str(raw_id).replace('/movie/index', '').replace('.html', '').strip('/')
            html = self._get(f'{self.host}/movie/index{vod_id}.html')
            if not html:
                return {'list': []}
            name = re.sub(r'<[^>]+>', '', self._re1(r'<h1[^>]*>([\s\S]*?)</h1>', html) or '').strip()
            pic = (self._re1(r'data-original="([^"]+)"', html) or '').replace('&amp;', '&')
            content = re.sub(
                r'<[^>]+>', '',
                self._re1(r'剧情简介[：:]*</span>\s*([\s\S]*?)</(?:p|div)>', html) or ''
            ).strip()
            tabs = [t.strip() for t in re.findall(r'href="#playlist\d+"[^>]*>([^<]+)</a>', html)]
            play_from, play_url = [], []
            for idx, body in enumerate(re.split(r'id="playlist\d+"', html)[1:]):
                eps = re.findall(r'href="/play/(\d+)-(\d+)-(\d+)\.html"[^>]*>([\s\S]*?)</a>', body)
                if not eps:
                    continue
                items = []
                for v, s, nid, n in eps:
                    title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', n or '')).strip()
                    if not title or len(title) > 40:
                        title = f'第{nid}集'
                    items.append(f'{title}${v}-{s}-{nid}')
                play_from.append(tabs[idx] if idx < len(tabs) else f'线路{eps[0][1]}')
                play_url.append('#'.join(items))
            if not play_url:
                eps = re.findall(r'href="/play/(\d+)-(\d+)-(\d+)\.html"[^>]*>([\s\S]*?)</a>', html)
                items = []
                for v, s, nid, n in eps:
                    title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', n or '')).strip()
                    if title == '立即播放':
                        continue
                    if not title or len(title) > 40:
                        title = nid
                    items.append(f'{title}${v}-{s}-{nid}')
                if items:
                    play_from, play_url = ['默认'], ['#'.join(items)]
            if not play_url:
                return {'list': []}
            return {'list': [{
                'vod_id': vod_id,
                'vod_name': name or vod_id,
                'vod_pic': pic,
                'vod_content': content,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]}
        except Exception as e:
            print('detail', e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        """对齐可播放 JS：parse/jx/url/header；兼容影视仓与 OK影视"""
        try:
            pid = str(id or '').strip()
            if '$' in pid:
                pid = pid.split('$')[-1].strip()
            parts = pid.split('-')
            if len(parts) >= 3:
                page = f'{self.host}/play/{parts[0]}-{parts[1]}-{parts[2]}.html'
            elif pid.startswith('http'):
                page = pid
            else:
                page = f'{self.host}/play/{pid}.html' if pid else self.host

            html = self._get(page)
            player = self._parse_player(html)
            url = page
            parse = 1
            hdr = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36',
                'Referer': self.host + '/',
                'Origin': self.host,
            }

            if player:
                enc = int(player.get('encrypt') or 0)
                raw = str(player.get('url') or '').replace('\\/', '/')
                try:
                    raw = raw.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
                raw = self._decode(enc, raw)
                if raw.startswith('//'):
                    raw = 'https:' + raw

                if self._is_media(raw) or self._is_pan(raw):
                    url, parse = raw, 0
                    if self._is_pan(raw):
                        hdr = dict(self.headers)
                elif raw.startswith('http') and '/play/' not in raw and 'artplayer' not in raw:
                    url, parse = raw, 0
                elif enc == 3 or re.fullmatch(r'[0-9a-fA-F]{16,}', raw or ''):
                    real = self._smartplay(raw)
                    if real and real.startswith('http'):
                        url, parse = real, 0
                    else:
                        # 与 JS 一致：回退 artplayer 嗅探
                        url = f'{self.host}/static/player/artplayer/?url={quote(raw)}'
                        parse = 1
                elif raw.startswith('http'):
                    url, parse = raw, 0 if self._is_media(raw) else 1

            # OK影视 / 部分壳要求 parse 为字符串 "0"/"1"
            result = {
                'header': hdr,
                'parse': parse,
                'jx': 0,
                'url': url,
                'playUrl': '',
            }
            # 额外兼容字段
            if parse == 0 and url.startswith('http'):
                result['parse'] = 0
            return result
        except Exception as e:
            print('play', e)
            return {
                'header': dict(self.headers),
                'parse': 1,
                'jx': 0,
                'url': str(id or ''),
                'playUrl': '',
            }

    def _resolve(self, html, page):
        player = self._parse_player(html)
        if not player:
            return page
        enc = int(player.get('encrypt') or 0)
        raw = str(player.get('url') or '').replace('\\/', '/')
        try:
            raw = raw.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass
        raw = self._decode(enc, raw)
        if raw.startswith('//'):
            raw = 'https:' + raw

        # 已是直链 / 网盘
        if self._is_media(raw) or self._is_pan(raw):
            return raw
        if raw.startswith('http') and '/play/' not in raw and 'artplayer' not in raw:
            return raw

        # encrypt=3：hex 密文 -> smartplay；失败则 artplayer 页
        if enc == 3 or (raw and re.fullmatch(r'[0-9a-fA-F]{16,}', raw or '')):
            real = self._smartplay(raw)
            if real and real.startswith('http'):
                return real
            # 回退：让播放器打开站点 artplayer（壳可解析）
            return f'{self.host}/static/player/artplayer/?url={quote(raw)}'

        if raw.startswith('http'):
            return raw
        return page

    def _parse_player(self, html):
        if not html:
            return None
        idx = html.find('player_aaaa')
        if idx < 0:
            return None
        start = html.find('{', idx)
        if start < 0:
            return None
        depth = 0
        end = start
        for i in range(start, len(html)):
            ch = html[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        blob = html[start:end]
        try:
            return json.loads(blob)
        except Exception:
            try:
                return json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', blob)))
            except Exception:
                return None

    def _smartplay(self, enc_url):
        """与 JS smartPlay 对齐：artplayer 取 vkey/code/timestamp -> POST -> AES"""
        try:
            art_url = f'{self.host}/static/player/artplayer/?url={quote(enc_url)}'
            art = self._get(art_url)
            if not art:
                return ''
            vkey = self._re1(r'playPageUrl\s*=\s*"([^"]*)"', art)
            code = self._re1(r'secretKeySeed\s*=\s*"([^"]*)"', art)
            timestamp = self._re1(r'timestamp\s*=\s*"([^"]*)"', art)
            # 部分情况下变量在 JS 赋值后为空，再试 qualities
            if vkey and code:
                tnow = int(time.time())
                data = self._post_json(SMART_API, {
                    'vkey': vkey,
                    'code': code,
                    't': tnow,
                    'signature': hashlib.md5(str(tnow).encode()).hexdigest(),
                })
                out = ''
                if isinstance(data, dict):
                    out = str(data.get('url') or data.get('data') or '')
                    if isinstance(data.get('data'), dict):
                        out = str(data['data'].get('url') or out)
                if out.startswith('http'):
                    return out
                if out and timestamp:
                    plain = aes_decrypt_smart(out, timestamp)
                    if plain.startswith('http'):
                        return plain
                # 再试：密文可能是 hex
                if out and re.fullmatch(r'[0-9a-fA-F]+', out):
                    try:
                        import binascii
                        b64 = binascii.unhexlify(out).decode('utf-8', 'ignore')
                        plain = aes_decrypt_smart(b64, timestamp) if timestamp else ''
                        if plain.startswith('http'):
                            return plain
                    except Exception:
                        pass
            # qualities 内嵌密文
            qm = re.search(r'qualities\s*=\s*(\[[^\]]+\])', art)
            if qm and timestamp:
                try:
                    for q in json.loads(qm.group(1)):
                        cu = str(q.get('url') or '')
                        if not cu:
                            continue
                        if cu.startswith('http'):
                            return cu
                        plain = aes_decrypt_smart(cu, timestamp)
                        if plain.startswith('http'):
                            return plain
                except Exception as e:
                    print('qualities', e)
            return ''
        except Exception as e:
            print('smartplay', e)
            return ''

    def _decode(self, enc, raw):
        if not raw:
            return ''
        if raw.startswith('http') or raw.startswith('//'):
            return ('https:' + raw) if raw.startswith('//') else raw
        try:
            if enc == 1:
                return unquote(raw)
            if enc == 2:
                pad = '=' * ((4 - len(raw) % 4) % 4)
                return unquote(base64.b64decode(raw + pad).decode('utf-8', 'ignore'))
        except Exception:
            pass
        return raw

    def _is_media(self, url):
        u = str(url or '').lower()
        if not u.startswith('http'):
            return False
        if re.search(r'\.(m3u8|mp4|flv|mkv)(?:[?#]|$)', u):
            return True
        return any(x in u for x in (
            'samtory', 'pcdn', 'auth_key=', 'getm3u8', 'nbyjson',
            'eos-', 'cmecloud', 'aliyuncs',
        ))

    def _is_pan(self, url):
        u = str(url or '').lower()
        return any(x in u for x in (
            'pan.quark.cn', 'drive.uc.cn', 'pan.baidu.com',
            'aliyundrive', 'alipan.com', 'quark.cn', '115.com',
        ))

    def _parse_list(self, html):
        out, seen = [], set()
        for m in re.finditer(r'href="/movie/index(\d+)\.html"[^>]*title="([^"]*)"', html or ''):
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
            tail = html[max(0, m.start() - 200):m.end() + 300]
            pic = self._re1(r'data-original="([^"]+)"', tail) or ''
            out.append({
                'vod_id': m.group(1),
                'vod_name': m.group(2),
                'vod_pic': pic.replace('&amp;', '&'),
                'vod_remarks': '',
            })
        return out

    def _re1(self, pat, text):
        m = re.search(pat, text or '')
        return m.group(1).strip() if m else ''

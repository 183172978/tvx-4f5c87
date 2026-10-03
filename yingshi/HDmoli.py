# -*- coding: utf-8 -*-
"""
HDmoli https://www.hdmoli.me/
修复线路播放地址：encrypt3 = smartplay + AES-CBC(MD5(timestamp+SALT))
无需 node / execB
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

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

SMART_API = 'https://hd.ticktockwow.com/smartplay-cache/api/webvideo_ty.php'
AES_SALT = 'RY7e48naFXPsLJC'


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
            x in u for x in ('samtory', 'pcdn', 'getm3u8', 'nbyjson')
        )

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _get(self, url, headers=None):
        r = self.fetch(url, headers=headers or self.headers)
        return r.text if hasattr(r, 'text') else str(r)

    def _get_json(self, url):
        try:
            return json.loads(self._get(url))
        except Exception:
            return {}

    def _post_json(self, url, data):
        h = dict(self.headers)
        h['Content-Type'] = 'application/json'
        h['Origin'] = self.host
        try:
            r = self.post(url, data=json.dumps(data), headers=h)
            return json.loads(r.text if hasattr(r, 'text') else str(r))
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
        try:
            data = self._get_json(f'{self.host}/index.php/ajax/data?mid=1&tid={tid}&page={pg}&limit=24')
            videos = [{
                'vod_id': str(i.get('vod_id') or ''),
                'vod_name': i.get('vod_name') or '',
                'vod_pic': str(i.get('vod_pic') or '').replace('&amp;', '&'),
                'vod_remarks': i.get('vod_remarks') or '',
            } for i in (data.get('list') or [])]
            if not videos:
                videos = self._parse_list(self._get(f'{self.host}/show/{tid}--------{pg}---.html'))
            return {
                'list': videos, 'page': pg,
                'pagecount': int(data.get('pagecount') or (pg + 1 if len(videos) >= 20 else pg)),
                'limit': 24, 'total': int(data.get('total') or 9999),
            }
        except Exception as e:
            print('category', e)
            return {'list': [], 'page': pg, 'pagecount': 0}

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        try:
            return {'list': self._parse_list(self._get(f'{self.host}/search/-------------.html?wd={quote(key)}')), 'page': pg}
        except Exception:
            return {'list': [], 'page': pg}

    def detailContent(self, ids):
        vod_id = str(ids[0]).replace('/movie/index', '').replace('.html', '')
        try:
            html = self._get(f'{self.host}/movie/index{vod_id}.html')
            name = re.sub(r'<[^>]+>', '', self._re1(r'<h1[^>]*>([\s\S]*?)</h1>', html) or '').strip()
            pic = (self._re1(r'data-original="([^"]+)"', html) or '').replace('&amp;', '&')
            content = re.sub(r'<[^>]+>', '', self._re1(r'剧情简介[：:]*</span>\s*([\s\S]*?)</(?:p|div)>', html) or '').strip()
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
            return {'list': [{
                'vod_id': vod_id, 'vod_name': name or vod_id, 'vod_pic': pic, 'vod_content': content,
                'vod_play_from': '$$$'.join(play_from), 'vod_play_url': '$$$'.join(play_url),
            }]}
        except Exception as e:
            print('detail', e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id).split('-')
            if len(parts) >= 3:
                page = f'{self.host}/play/{parts[0]}-{parts[1]}-{parts[2]}.html'
            elif str(id).startswith('http'):
                page = str(id)
            else:
                page = f'{self.host}/play/{id}'
            html = self._get(page)
            url = self._resolve(html, page) or page
            # 直链 / 网盘 / 解密出的 http 一律 parse=0；仅站点播放页才嗅探
            is_site_play = ('/play/' in url and 'hdmoli' in url) or '/static/player/artplayer' in url
            parse = 1 if is_site_play else 0
            hdr = dict(self.headers)
            if not self._is_pan(url):
                hdr = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36',
                    'Referer': self.host + '/',
                    'Origin': self.host,
                }
            return {'jx': 0, 'parse': parse, 'url': url, 'header': hdr}
        except Exception as e:
            print('play', e)
            return {'jx': 0, 'parse': 1, 'url': str(id), 'header': self.headers}

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
        if self._is_media(raw) or self._is_pan(raw):
            return raw
        if raw.startswith('http') and '/play/' not in raw:
            return raw
        if enc == 3 or re.fullmatch(r'[0-9a-fA-F]+', raw or ''):
            real = self._smartplay(raw)
            if real:
                return real
            return f'{self.host}/static/player/artplayer/?url={quote(raw)}'
        return page

    def _parse_player(self, html):
        idx = (html or '').find('player_aaaa')
        if idx < 0:
            return None
        start = html.find('{', idx)
        if start < 0:
            return None
        depth = 0
        end = start
        for i in range(start, len(html)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(html[start:end])
        except Exception:
            try:
                return json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', html[start:end])))
            except Exception:
                return None

    def _smartplay(self, enc_url):
        try:
            art = self._get(f'{self.host}/static/player/artplayer/?url={quote(enc_url)}')
            vkey = self._re1(r'playPageUrl\s*=\s*"([^"]+)"', art)
            code = self._re1(r'secretKeySeed\s*=\s*"([^"]+)"', art)
            timestamp = self._re1(r'timestamp\s*=\s*"([^"]+)"', art)
            if not vkey or not code:
                return ''
            t = int(time.time())
            data = self._post_json(SMART_API, {
                'vkey': vkey, 'code': code, 't': t,
                'signature': hashlib.md5(str(t).encode()).hexdigest(),
            })
            out = str((data or {}).get('url') or '')
            if not out:
                return ''
            if out.startswith('http'):
                return out
            # AES 解密
            if timestamp and AES is not None:
                plain = self._aes_decrypt(out, timestamp)
                if plain.startswith('http'):
                    return plain
            return ''
        except Exception as e:
            print('smartplay', e)
            return ''

    def _aes_decrypt(self, cipher_b64, timestamp):
        """MD5(timestamp+SALT) → iv=前16hex字符(utf8) key=后16hex字符(utf8)"""
        try:
            h = hashlib.md5((str(timestamp) + AES_SALT).encode()).hexdigest()
            key = h[16:32].encode('utf-8')
            iv = h[0:16].encode('utf-8')
            data = base64.b64decode(cipher_b64)
            pt = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
            pad = pt[-1]
            if 1 <= pad <= 16:
                pt = pt[:-pad]
            return pt.decode('utf-8', 'ignore')
        except Exception as e:
            print('aes', e)
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
                return unquote(base64.b64decode(raw + '=' * ((4 - len(raw) % 4) % 4)).decode('utf-8', 'ignore'))
        except Exception:
            pass
        return raw

    def _is_media(self, url):
        u = str(url or '').lower()
        if not u.startswith('http'):
            return False
        if re.search(r'\.(m3u8|mp4|flv|mkv)(?:[?#]|$)', u):
            return True
        return any(x in u for x in ('samtory', 'pcdn', 'auth_key=', 'getm3u8', 'nbyjson'))

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

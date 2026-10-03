# -*- coding: utf-8 -*-
# NO视频 https://www.novipnoad.net
# 分类路径型；播放 player.novipnoad.net + RC4(默认 key 52b7ac39)
import sys, re, json, base64
import urllib.request
import urllib.parse
import ssl

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):
    host = 'https://www.novipnoad.net'
    player = 'https://player.novipnoad.net'
    decrypt_key = '52b7ac39'
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'

    CLASSES = [
        {'type_id': 'movie', 'type_name': '电影'},
        {'type_id': 'anime', 'type_name': '动画'},
        {'type_id': 'shows', 'type_name': '综艺'},
        {'type_id': 'tv-western', 'type_name': '欧美剧'},
        {'type_id': 'tv-japan', 'type_name': '日剧'},
        {'type_id': 'tv-korea', 'type_name': '韩剧'},
        {'type_id': 'tv-taiwan', 'type_name': '台剧'},
        {'type_id': 'tv-thailand', 'type_name': '泰剧'},
        {'type_id': 'tv-hongkong', 'type_name': '港剧'},
        {'type_id': 'tv-turkey', 'type_name': '土耳其剧'},
    ]
    TID_PATH = {
        'movie': 'movie/',
        'anime': 'anime/',
        'shows': 'shows/',
        'tv-western': 'tv/western/',
        'tv-japan': 'tv/japan/',
        'tv-korea': 'tv/korea/',
        'tv-taiwan': 'tv/taiwan/',
        'tv-thailand': 'tv/thailand/',
        'tv-hongkong': 'tv/hongkong/',
        'tv-turkey': 'tv/turkey/',
    }

    def init(self, extend=''):
        if isinstance(extend, str) and extend.strip():
            try:
                if extend.strip().startswith('{'):
                    cfg = json.loads(extend)
                    if cfg.get('host'):
                        self.host = str(cfg['host']).rstrip('/')
                    if cfg.get('player'):
                        self.player = str(cfg['player']).rstrip('/')
                    if cfg.get('decryptKey'):
                        self.decrypt_key = str(cfg['decryptKey'])
                elif extend.startswith('http'):
                    self.host = extend.rstrip('/')
            except Exception:
                pass
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.headers = {
            'User-Agent': self.UA,
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def getName(self):
        return 'NO视频'

    def _get(self, url, extra_headers=None):
        headers = dict(self.headers)
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20, context=self.ctx) as resp:
            data = resp.read()
            try:
                return data.decode('utf-8')
            except Exception:
                return data.decode('latin1', errors='ignore')

    def _abs(self, u):
        if not u:
            return ''
        u = str(u).strip()
        if u.startswith('http'):
            return u
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return self.host + '/' + u

    def homeContent(self, filter):
        result = {'class': list(self.CLASSES)}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        try:
            html = self._get(self.host + '/')
            return {'list': self._parse_list(html)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        key = str(tid or 'movie').strip('/')
        path = self.TID_PATH.get(key) or self.TID_PATH.get(key.replace('/', '-')) or (key.replace('-', '/') + '/')
        url = '%s/%s' % (self.host, path)
        if page > 1:
            url += 'page/%s/' % page
        try:
            html = self._get(url)
        except Exception:
            html = ''
        if (not html) or ('Just a moment' in html):
            try:
                html = self._get(url, {'User-Agent': self.MOBILE_UA})
            except Exception:
                html = html or ''
        items = self._parse_list(html)
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if len(items) >= 20 else page,
            'limit': 40,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg='1'):
        page = max(1, int(pg or 1))
        url = '%s/page/%s/?s=%s' % (self.host, page, urllib.parse.quote(str(key)))
        html = self._get(url, {'User-Agent': self.MOBILE_UA})
        items = self._parse_list(html)
        return {'list': items, 'page': page, 'pagecount': page + 1 if items else page}

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        parts = re.split(r'class="[^"]*video-item[^"]*"', html, flags=re.I)
        for block in parts[1:]:
            block = block[:1200]
            m = re.search(r'href="(https?://[^"]+\.html)"', block, re.I) or re.search(
                r'href="(/[^"]+\.html)"', block, re.I
            )
            if not m:
                continue
            link = self._abs(m.group(1))
            idm = re.search(r'/(\d+)\.html', link)
            if not idm:
                continue
            if link in seen:
                continue
            seen.add(link)
            name = ''
            nm = re.search(r'title="([^"]+)"', block)
            if nm:
                name = re.sub(r'^【.*?】', '', nm.group(1)).strip()
            if not name:
                nm = re.search(r'<h3[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)</a>', block, re.I)
                if nm:
                    name = re.sub(r'<[^>]+>', '', nm.group(1))
                    name = re.sub(r'^【.*?】', '', name).strip()
            if not name:
                name = '影片' + idm.group(1)
            pic = ''
            pm = re.search(r'data-original="([^"]+)"', block) or re.search(
                r'src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I
            )
            if pm:
                pic = self._abs(pm.group(1))
            remarks = ''
            rm = re.search(r'class="remarks"[^>]*>([\s\S]*?)<', block, re.I)
            if rm:
                remarks = re.sub(r'<[^>]+>', '', rm.group(1)).strip()
            items.append({
                'vod_id': link,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        return items

    def _extract_play_info(self, html):
        vid, pkey = '', ''
        m = re.search(r'window\.playInfo\s*=\s*(\{[^<]*?\})\s*;', html) or re.search(
            r'playInfo\s*=\s*(\{[^<]*?\})\s*;', html
        )
        if m:
            try:
                fixed = re.sub(r'([\{,])\s*(\w+)\s*:', r'\1"\2":', m.group(1))
                info = json.loads(fixed)
                vid = info.get('vid') or ''
                pkey = info.get('pkey') or ''
            except Exception:
                pass
        if not pkey:
            pm = re.search(r'pkey\s*:\s*["\']([^"\']+)["\']', html)
            if pm:
                pkey = pm.group(1)
        if not vid:
            vm = re.search(r'vid\s*:\s*["\']([^"\']+)["\']', html)
            if vm:
                vid = vm.group(1)
        return vid, pkey

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = raw if str(raw).startswith('http') else self._abs(raw)
        html = self._get(url)
        if not html or 'Just a moment' in html:
            return {'list': []}
        name = ''
        nm = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.I)
        if nm:
            name = re.sub(r'^【.*?】', '', nm.group(1)).strip()
        if not name:
            nm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
            if nm:
                name = re.sub(r'<[^>]+>', '', nm.group(1)).strip()
        pic = ''
        pm = re.search(r'property="og:image"\s+content="([^"]+)"', html, re.I)
        if pm:
            pic = pm.group(1)
        content = ''
        cm = re.search(r'class="[^"]*item-content[^"]*"[^>]*>([\s\S]*?)</div>', html, re.I)
        if cm:
            content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()[:300]

        vid, pkey = self._extract_play_info(html)
        play_urls = []
        for m in re.finditer(
            r'class="[^"]*multilink-btn[^"]*"[^>]*data-vid="([^"]+)"[^>]*>([\s\S]*?)</(?:a|button|div|span)>',
            html,
            re.I,
        ):
            n = re.sub(r'<[^>]+>', '', m.group(2)).strip() or '线路'
            play_urls.append('%s$%s|%s|%s' % (n, m.group(1), pkey, urllib.parse.quote(url, safe='')))
        if not play_urls and vid:
            play_urls.append('正片$%s|%s|%s' % (vid, pkey, urllib.parse.quote(url, safe='')))
        if not play_urls:
            play_urls.append('正片$%s' % url)
        return {'list': [{
            'vod_id': url,
            'vod_name': name,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': 'NO视频',
            'vod_play_url': '#'.join(play_urls),
        }]}

    def _rc4(self, data, key):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        out = []
        for ch in data:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            out.append(chr(ord(ch) ^ s[(s[i] + s[j]) % 256]))
        return ''.join(out)

    def _try_decrypt(self, cipher_b64, keys):
        try:
            raw = base64.b64decode(re.sub(r'[^A-Za-z0-9+/=]', '', cipher_b64))
            data = raw.decode('latin1')
        except Exception:
            return ''
        for key in keys:
            if not key:
                continue
            try:
                plain = self._rc4(data, key)
                if plain and plain[0] == '{':
                    obj = json.loads(plain)
                    qs = obj.get('quality') or []
                    if qs:
                        idx = obj.get('defaultQuality') or 0
                        if not isinstance(idx, int) or idx >= len(qs):
                            idx = 0
                        u = (qs[idx] or {}).get('url') or ''
                        if u:
                            return u
            except Exception:
                continue
        return ''

    def _resolve_player(self, vid, pkey, ref):
        if not vid:
            return ''
        player_url = '%s/v1/?url=%s' % (self.player, urllib.parse.quote(vid))
        if pkey:
            player_url += '&pkey=' + urllib.parse.quote(pkey)
        if ref:
            player_url += '&ref=' + urllib.parse.quote(ref)
        try:
            page = self._get(player_url, {'Referer': self.host + '/'})
        except Exception:
            return ''
        m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', page, re.I)
        if m:
            return m.group(1)
        dm = re.search(r"params\['device'\]\s*=\s*'(\w+)'", page) or re.search(
            r"device['\"]\s*[:=]\s*['\"](\w+)['\"]", page
        )
        if not dm:
            return ''
        device = dm.group(1)
        php_url = '%s/v1/player.php?id=%s&device=%s' % (
            self.player, urllib.parse.quote(vid), device
        )
        try:
            php = self._get(php_url, {'Referer': player_url})
        except Exception:
            return ''
        jm = re.search(r"const\s+jsapi\s*=\s*'(.*?)'", php) or re.search(r"jsapi\s*=\s*'(.*?)'", php)
        if jm:
            try:
                js = self._get(jm.group(1), {'Referer': self.player + '/'})
            except Exception:
                js = ''
            cm = re.search(r"var\s+videoUrl\s*=\s*JSON\.decrypt\(\s*['\"](.*?)['\"]\s*\)\s*;", js)
            if cm:
                u = self._try_decrypt(cm.group(1), [self.decrypt_key, '52b7ac39'])
                if u:
                    return u
            m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', js, re.I)
            if m:
                return m.group(1)
        m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', php, re.I)
        if m:
            return m.group(1)
        return ''

    def playerContent(self, flag, id, vipFlags):
        raw = str(id)
        headers = {
            'User-Agent': self.UA,
            'Referer': self.player + '/',
            'Origin': self.player,
        }
        if raw.startswith('http') and ('.m3u8' in raw or '.mp4' in raw):
            return {'parse': 0, 'jx': 0, 'url': raw, 'header': headers}
        if '|' in raw:
            parts = raw.split('|')
            vid = parts[0]
            pkey = parts[1] if len(parts) > 1 else ''
            ref = parts[2] if len(parts) > 2 else self.host + '/'
            try:
                ref = urllib.parse.unquote(ref)
            except Exception:
                pass
            u = self._resolve_player(vid, pkey, ref)
            if u:
                return {'parse': 0, 'jx': 0, 'url': u, 'header': headers}
            player_url = '%s/v1/?url=%s' % (self.player, urllib.parse.quote(vid))
            if pkey:
                player_url += '&pkey=' + urllib.parse.quote(pkey)
            player_url += '&ref=' + urllib.parse.quote(ref)
            return {'parse': 1, 'jx': 0, 'url': player_url, 'header': headers}
        if raw.startswith('http'):
            try:
                html = self._get(raw)
                vid, pkey = self._extract_play_info(html)
                if vid:
                    u = self._resolve_player(vid, pkey, raw)
                    if u:
                        return {'parse': 0, 'jx': 0, 'url': u, 'header': headers}
            except Exception:
                pass
            return {'parse': 1, 'jx': 0, 'url': raw, 'header': self.headers}
        return {'parse': 1, 'jx': 0, 'url': raw, 'header': self.headers}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

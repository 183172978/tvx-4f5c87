# -*- coding: utf-8 -*-
# 看片狂人 - 分类/播放加固版
# 多镜像回退加载分类；data-play 解码；vidara 二次 m3u8
import re
import json
import sys
import base64
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

try:
    import requests
    requests.packages.urllib3.disable_warnings()  # type: ignore
except Exception:
    requests = None

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
DEFAULT_HOST = 'https://www.kpkuang.org'
HOSTS = [
    'https://www.kpkuang.org',
    'https://kpkuang.one',
    'https://www.kpkuang.com',
    'https://kpkuang.us',
    'https://www.kpkuang.de',
    'https://www.kpkuang.fun',
    'https://kpkuang.fun',
]
CATS = [
    ('1', '电影'),
    ('2', '连续剧'),
    ('3', '综艺'),
    ('4', '动漫'),
    ('37', '短剧'),
]


class Spider(BaseSpider):

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = DEFAULT_HOST
        self.headers = {
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        self._sess = None
        if requests is not None:
            try:
                self._sess = requests.Session()
                self._sess.trust_env = False
                self._sess.headers.update(self.headers)
            except Exception:
                self._sess = None

    def getName(self):
        return '看片狂人'

    def init(self, extend=''):
        ext = extend
        if isinstance(ext, dict):
            ext = ext.get('ext') or ext.get('host') or ext.get('url') or ''
        if isinstance(ext, (list, tuple)):
            ext = ext[0] if ext else ''
        ext = str(ext or '').strip().strip('"').strip("'")
        if ext.startswith('{'):
            try:
                o = json.loads(ext)
                ext = o.get('host') or o.get('url') or ''
            except Exception:
                pass
        if ext.startswith('http'):
            self.host = ext.rstrip('/')
        else:
            self.host = DEFAULT_HOST
        self.headers['Referer'] = self.host + '/'
        if self._sess is not None:
            self._sess.headers.update(self.headers)
        # 预热：探测可用镜像
        self._pick_live_host()

    def _pick_live_host(self):
        order = [self.host] + [h for h in HOSTS if h != self.host]
        for h in order:
            html = self._get_raw(h + '/', timeout=8, referer=h + '/')
            if html and ('fed-list-item' in html or '/vodtype/' in html):
                self.host = h
                self.headers['Referer'] = h + '/'
                if self._sess is not None:
                    self._sess.headers.update(self.headers)
                return

    def destroy(self):
        if self._sess is not None:
            try:
                self._sess.close()
            except Exception:
                pass

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, 'text/plain', '']

    def _get_raw(self, url, timeout=15, referer=None):
        headers = dict(self.headers)
        headers['Referer'] = referer or (self.host + '/')
        if self._sess is not None:
            try:
                r = self._sess.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
                text = r.text or ''
                if r.status_code == 200 and 'Just a moment' not in text[:1000]:
                    return text
            except Exception:
                pass
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _get(self, path_or_url, timeout=15, referer=None):
        """带多镜像回退的 GET。path 以 / 开头时拼 host。"""
        if path_or_url.startswith('http'):
            html = self._get_raw(path_or_url, timeout=timeout, referer=referer)
            if html:
                return html
            # 尝试替换 host
            m = re.match(r'https?://[^/]+(/.*)?$', path_or_url)
            path = m.group(1) if m and m.group(1) else '/'
        else:
            path = path_or_url if path_or_url.startswith('/') else '/' + path_or_url

        hosts = [self.host] + [h for h in HOSTS if h != self.host]
        for h in hosts:
            html = self._get_raw(h + path, timeout=timeout, referer=h + '/')
            if html and len(html) > 500:
                # 成功则记住
                if h != self.host and ('fed-list-item' in html or '/voddetail/' in html or 'data-play=' in html):
                    self.host = h
                    self.headers['Referer'] = h + '/'
                return html
        return ''

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        blocks = re.findall(r'<li[^>]*class="[^"]*fed-list-item[^"]*"[\s\S]*?</li>', html)
        if not blocks:
            # 宽松：任意含 voddetail 的块
            blocks = re.findall(r'<li[\s\S]*?/voddetail/\d+/[\s\S]*?</li>', html)
        for b in blocks:
            m = re.search(r'href="(/voddetail/(\d+)/?)"', b)
            if not m:
                m = re.search(r'href=\'(/voddetail/(\d+)/?)\'', b)
            if not m:
                continue
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = ''
            for pat in [
                r'class="cinema_title"[^>]*>([^<]+)',
                r'title="([^"]+)"',
                r"title='([^']+)'",
                r'alt="([^"]+)"',
                r'fed-list-title[^>]*>([^<]+)',
            ]:
                tm = re.search(pat, b)
                if tm and tm.group(1).strip() and tm.group(1).strip() not in ('专题',):
                    title = re.sub(r'\s+', ' ', tm.group(1)).strip()
                    break
            if not title:
                continue
            pic = ''
            pm = re.search(r'data-original="(https?://[^"]+)"', b)
            if not pm:
                pm = re.search(r'(?:data-src|src)="(https?://[^"]+)"', b)
            if pm:
                pic = pm.group(1)
            remarks = ''
            rm = re.search(r'fed-list-name[^>]*>([^<]+)', b)
            if rm:
                remarks = re.sub(r'&nbsp;?', ' ', rm.group(1))
                remarks = re.sub(r'\s+', ' ', remarks).strip()
            items.append({
                'vod_id': str(vid),
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        # 再兜底：仅链接
        if not items:
            for m in re.finditer(r'href="(/voddetail/(\d+)/)"[^>]*>([^<]{0,5})', html):
                pass
            for m in re.finditer(r'/voddetail/(\d+)/[^>]{0,80}(?:title|cinema_title|alt)="([^"]+)"', html):
                vid, title = m.group(1), m.group(2).strip()
                if vid in seen or not title:
                    continue
                seen.add(vid)
                items.append({'vod_id': str(vid), 'vod_name': title[:90], 'vod_pic': '', 'vod_remarks': ''})
        return items

    def homeContent(self, filter):
        classes = [{'type_id': str(a), 'type_name': b} for a, b in CATS]
        return {'class': classes, 'list': [], 'filters': {}}

    def homeVideoContent(self):
        html = self._get('/')
        return {'list': self._parse_list(html)[:48]}

    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1
        tid = str(tid or '1').strip()
        if page <= 1:
            path = '/vodtype/%s/' % tid
        else:
            path = '/vodtype/%s-%d/' % (tid, page)
        html = self._get(path)
        items = self._parse_list(html)
        # 若主路径失败，试不带尾斜杠 / 旧分页
        if not items:
            alt = [
                '/vodtype/%s' % tid if page <= 1 else '/vodtype/%s-%d' % (tid, page),
                '/vodtype/%s.html' % tid if page <= 1 else '/vodtype/%s-%d.html' % (tid, page),
                '/index.php/vod/type/id/%s.html' % tid,
            ]
            for p in alt:
                html = self._get(p)
                items = self._parse_list(html)
                if items:
                    break
        pagecount = page + 1 if len(items) >= 20 else page
        return {
            'list': items,
            'page': page,
            'pagecount': pagecount,
            'limit': len(items) or 24,
            'total': pagecount * max(len(items), 1),
        }

    def searchContent(self, key, quick, pg='1'):
        page = 1
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1
        kw = quote(str(key or ''))
        items = []
        for path in [
            '/vodsearch/%s-------------.html' % kw,
            '/vodsearch/-------------.html?wd=%s' % kw,
            '/index.php/vod/search.html?wd=%s' % kw,
        ]:
            items = self._parse_list(self._get(path))
            if items:
                break
        return {'list': items, 'page': page, 'pagecount': page + 1 if len(items) >= 12 else page}

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        vid = re.sub(r'\D', '', vid.split('/')[-1]) or vid
        html = self._get('/voddetail/%s/' % vid)
        if not html:
            return {'list': []}

        title = ''
        tm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html)
        if tm:
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
        if not title:
            tm = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.I)
            if tm:
                title = tm.group(1).strip()

        pic = ''
        pm = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if pm:
            pic = pm.group(1)
        if not pic:
            pm = re.search(r'data-original="(https?://[^"]+)"', html)
            if pm:
                pic = pm.group(1)

        def meta(label):
            m = re.search(r'%s[：:]\s*</[^>]+>\s*<[^>]+>([\s\S]*?)</' % label, html)
            if not m:
                m = re.search(r'%s[：:]\s*([^<\n]{1,80})' % label, html)
            return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

        content = ''
        cm = re.search(r'(?:剧情|简介)[：:]</[^>]+>\s*<[^>]+>([\s\S]*?)</div>', html)
        if cm:
            content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()

        play_from, play_url = [], []
        blocks = re.split(r'class="fed-play-item[^"]*"', html)
        for block in blocks[1:]:
            lab = re.search(r'uk-label">([^<]+)', block)
            name = lab.group(1).strip() if lab else ''
            if not name:
                continue
            eps = []
            for em in re.finditer(r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]*)', block):
                if em.group(2) != vid:
                    continue
                en = re.sub(r'\s+', ' ', em.group(5)).strip() or ('第%s集' % em.group(4))
                eps.append('%s$%s-%s-%s' % (en, em.group(2), em.group(3), em.group(4)))
            if eps:
                play_from.append(name)
                play_url.append('#'.join(eps))

        def score(n):
            n = n.lower()
            s = 0
            if any(k in n for k in ('云', 'm3u8', '资源', 'hd')):
                s += 10
            if 'vip' in n or '解析' in n:
                s -= 5
            return -s

        if play_from:
            paired = sorted(zip(play_from, play_url), key=lambda x: score(x[0]))
            play_from = [a for a, _ in paired]
            play_url = [b for _, b in paired]

        return {'list': [{
            'vod_id': str(vid),
            'vod_name': title or ('影片 ' + vid),
            'vod_pic': pic,
            'vod_year': meta('年份') or meta('上映'),
            'vod_area': meta('地区'),
            'vod_actor': meta('主演') or meta('演员'),
            'vod_director': meta('导演'),
            'type_name': meta('类型') or meta('分类'),
            'vod_content': content[:800],
            'vod_remarks': '',
            'vod_play_from': '$$$'.join(play_from) if play_from else '看片狂人',
            'vod_play_url': '$$$'.join(play_url) if play_url else '',
        }]}

    @staticmethod
    def _decode_data_play(raw):
        v = str(raw or '').strip()
        if not v or len(v) < 8:
            return ''
        for off in (3, 0, 1, 2, 4, 5):
            try:
                chunk = v[off:]
                data = base64.b64decode(chunk + '=' * ((-len(chunk)) % 4))
                if data.startswith(b'http'):
                    return data.decode('utf-8', 'ignore')
                idx = data.find(b'http')
                if idx >= 0:
                    return data[idx:].decode('utf-8', 'ignore')
            except Exception:
                continue
        return ''

    def _fetch_play_html(self, vid, sid, nid):
        path = '/vodplay/%s-%s-%s.html' % (vid, sid, nid)
        hosts = [self.host] + [h for h in HOSTS if h != self.host]
        for base in hosts:
            html = self._get_raw(base + path, referer=base + '/voddetail/%s/' % vid)
            if html and ('data-play=' in html or 'fed-play-iframe' in html):
                return html, base
        return '', self.host

    def _resolve_embed(self, url):
        if not url:
            return ''
        m = re.search(r'https?://(?:www\.)?vidara\.(?:to|so)/e/([a-zA-Z0-9]+)', url)
        if m and self._sess is not None:
            code = m.group(1)
            try:
                r = self._sess.post(
                    'https://vidara.to/api/stream',
                    headers={
                        'User-Agent': UA,
                        'Content-Type': 'application/json',
                        'Referer': 'https://vidara.to/e/' + code,
                        'Origin': 'https://vidara.to',
                    },
                    data=json.dumps({'filecode': code, 'device': 'pc'}),
                    timeout=12, verify=False,
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get('streaming_url'):
                        return str(data['streaming_url'])
            except Exception:
                pass
        if self._sess is not None and not self.isVideoFormat(url):
            try:
                r = self._sess.get(url, headers={'User-Agent': UA, 'Referer': self.host + '/'}, timeout=12, verify=False)
                text = r.text or ''
                hm = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', text)
                if hm:
                    return hm.group(1)
                hm = re.search(r'"streaming_url"\s*:\s*"(https?://[^"]+)"', text)
                if hm:
                    return hm.group(1)
            except Exception:
                pass
        return ''

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '').strip()
        hdr = {'User-Agent': UA, 'Referer': self.host + '/'}
        if raw.startswith('http'):
            if self.isVideoFormat(raw):
                return {'parse': 0, 'jx': 0, 'url': raw, 'header': hdr}
            resolved = self._resolve_embed(raw)
            if resolved:
                return {'parse': 0, 'jx': 0, 'url': resolved, 'header': {'User-Agent': UA, 'Referer': raw}}
            return {'parse': 1, 'jx': 0, 'url': raw, 'header': hdr}

        m = re.search(r'(\d+)-(\d+)-(\d+)', raw)
        if not m:
            return {'parse': 0, 'jx': 0, 'url': '', 'header': hdr}

        html, used_host = self._fetch_play_html(m.group(1), m.group(2), m.group(3))
        hdr['Referer'] = used_host + '/'
        play_url = ''
        if html:
            dm = re.search(r'data-play="([^"]*)"', html)
            if dm:
                play_url = self._decode_data_play(dm.group(1))
            if not play_url:
                hm = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html)
                if hm:
                    play_url = hm.group(1)
        if play_url.startswith('//'):
            play_url = 'https:' + play_url
        if play_url and not self.isVideoFormat(play_url):
            resolved = self._resolve_embed(play_url)
            if resolved:
                play_url = resolved
        if play_url and self.isVideoFormat(play_url):
            origin = re.match(r'https?://[^/]+', play_url)
            return {
                'parse': 0, 'jx': 0, 'url': play_url,
                'header': {
                    'User-Agent': UA,
                    'Referer': used_host + '/',
                    'Origin': origin.group(0) if origin else used_host,
                },
            }
        if play_url:
            return {'parse': 1, 'jx': 0, 'url': play_url, 'header': hdr}
        return {'parse': 0, 'jx': 0, 'url': '', 'header': hdr}


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print('host', sp.host)
    print(sp.homeContent(False))
    print(len(sp.categoryContent('1', '1', False, {})['list']))

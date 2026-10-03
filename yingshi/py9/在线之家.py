# -*- coding: utf-8 -*-
# 在线之家 (zxzj.run) TVBox 爬虫
# 列表 /vodtype/{id}.html  详情 /voddetail/{id}.html  播放 /vodplay/{id}-{sid}-{nid}.html
# player_aaaa encrypt: 0明文 1=unquote 2=base64 3=外链播放器
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
except Exception:
    requests = None

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
DEFAULT_HOST = 'https://www.zxzj.run'

CATS = [
    ('1', '电影'),
    ('2', '美剧'),
    ('3', '韩剧'),
    ('4', '日剧'),
    ('5', '泰剧'),
    ('6', '动漫'),
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
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self._sess = None
        if requests is not None:
            try:
                self._sess = requests.Session()
                self._sess.headers.update(self.headers)
            except Exception:
                self._sess = None

    def getName(self):
        return '在线之家'

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
            self.headers['Referer'] = self.host + '/'
            if self._sess is not None:
                self._sess.headers.update(self.headers)

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

    def _get(self, url, timeout=15):
        if not url.startswith('http'):
            url = self.host + url
        if self._sess is not None:
            try:
                r = self._sess.get(url, timeout=timeout, verify=False)
                if r.status_code == 200:
                    r.encoding = r.apparent_encoding or 'utf-8'
                    return r.text
            except Exception:
                pass
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=self.headers)
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        # stui-vodlist__thumb
        for m in re.finditer(
            r'<a[^>]*class="[^"]*stui-vodlist__thumb[^"]*"[^>]*href="(/voddetail/(\d+)\.html)"[^>]*title="([^"]+)"[^>]*(?:data-original|data-src|src)="([^"]+)"',
            html, re.I,
        ):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            pic = m.group(4)
            if pic.startswith('//'):
                pic = 'https:' + pic
            remarks = ''
            # 向后找 pic-text
            tail = html[m.end():m.end() + 200]
            rm = re.search(r'pic-text[^>]*>([^<]+)', tail)
            if rm:
                remarks = rm.group(1).strip()
            items.append({
                'vod_id': vid,
                'vod_name': m.group(3).strip()[:90],
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        if items:
            return items
        # 宽松
        for m in re.finditer(r'href="(/voddetail/(\d+)\.html)"[^>]*title="([^"]+)"', html):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            items.append({
                'vod_id': vid,
                'vod_name': m.group(3).strip()[:90],
                'vod_pic': '',
                'vod_remarks': '',
            })
        return items

    def homeContent(self, filter):
        return {
            'class': [{'type_id': a, 'type_name': b} for a, b in CATS],
            'filters': {},
        }

    def homeVideoContent(self):
        return {'list': self._parse_list(self._get(self.host + '/'))[:48]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        tid = str(tid).strip()
        if page <= 1:
            url = '%s/vodtype/%s.html' % (self.host, tid)
        else:
            url = '%s/vodtype/%s-%d.html' % (self.host, tid, page)
        items = self._parse_list(self._get(url))
        pagecount = page + 1 if len(items) >= 12 else page
        return {
            'list': items,
            'page': page,
            'pagecount': pagecount,
            'limit': len(items) or 24,
            'total': pagecount * max(len(items), 1),
        }

    def searchContent(self, key, quick, pg='1'):
        page = max(1, int(pg or 1))
        kw = quote(str(key or ''))
        url = '%s/vodsearch/-------------.html?wd=%s' % (self.host, kw)
        if page > 1:
            url = '%s/vodsearch/%s----------%d---.html' % (self.host, kw, page)
        items = self._parse_list(self._get(url))
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if len(items) >= 12 else page,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        vid = re.sub(r'\D', '', vid.split('/')[-1].replace('.html', '')) or vid
        html = self._get('%s/voddetail/%s.html' % (self.host, vid))
        if not html:
            return {'list': []}

        title = ''
        tm = re.search(r'<h1[^>]*class="title"[^>]*>([\s\S]*?)</h1>', html)
        if not tm:
            tm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html)
        if tm:
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()

        pic = ''
        pm = re.search(r'data-original="(https?://[^"]+)"', html)
        if not pm:
            pm = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if pm:
            pic = pm.group(1)

        def meta(label):
            m = re.search(label + r'[：:]\s*([^<\n]{1,80})', html)
            if m:
                return re.sub(r'<[^>]+>', '', m.group(1)).split('/')[0].strip()
            return ''

        content = ''
        cm = re.search(r'简介[：:]\s*<span[^>]*>([\s\S]*?)</span>', html)
        if not cm:
            cm = re.search(r'简介[：:]([\s\S]{0,400})', html)
        if cm:
            content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()

        play_from, play_url = [], []
        # stui-vodlist__head h3 + stui-content__playlist
        for m in re.finditer(
            r'<div class="stui-vodlist__head"[^>]*>[\s\S]*?<h3>([^<]+)</h3>[\s\S]*?<ul class="stui-content__playlist[^"]*">([\s\S]*?)</ul>',
            html,
        ):
            name = m.group(1).strip()
            if '猜你喜欢' in name or '热门' in name:
                continue
            body = m.group(2)
            eps = []
            for em in re.finditer(r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]*)', body):
                if em.group(2) != vid:
                    continue
                en = re.sub(r'\s+', ' ', em.group(5)).strip() or ('第%s集' % em.group(4))
                eps.append('%s$%s-%s-%s' % (en, em.group(2), em.group(3), em.group(4)))
            if eps:
                play_from.append(name)
                play_url.append('#'.join(eps))

        if not play_url:
            eps, seen = [], set()
            for em in re.finditer(r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]*)', html):
                if em.group(1) in seen:
                    continue
                seen.add(em.group(1))
                en = re.sub(r'\s+', ' ', em.group(5)).strip() or ('第%s集' % em.group(4))
                eps.append('%s$%s-%s-%s' % (en, em.group(2), em.group(3), em.group(4)))
            if eps:
                play_from = ['默认']
                play_url = ['#'.join(eps)]

        return {'list': [{
            'vod_id': vid,
            'vod_name': title or ('影片 ' + vid),
            'vod_pic': pic,
            'vod_year': meta('年份'),
            'vod_area': meta('地区'),
            'vod_actor': meta('主演'),
            'vod_director': meta('导演'),
            'type_name': meta('类型'),
            'vod_content': content[:800],
            'vod_play_from': '$$$'.join(play_from) if play_from else '在线之家',
            'vod_play_url': '$$$'.join(play_url) if play_url else '',
        }]}

    def _decode_player(self, html):
        mm = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>', html)
        if not mm:
            return ''
        try:
            obj = json.loads(mm.group(1))
            u = str(obj.get('url') or '').strip()
            enc = int(obj.get('encrypt') or 0)
            if enc == 1:
                u = unquote(u)
            elif enc == 2:
                try:
                    u = unquote(base64.b64decode(u + '=' * ((-len(u)) % 4)).decode('utf-8', 'ignore'))
                except Exception:
                    pass
            # encrypt 3 及 0：url 已是完整地址
            if u.startswith('//'):
                u = 'https:' + u
            return u if re.match(r'^https?:', u) else ''
        except Exception:
            return ''

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '').strip()
        m = re.search(r'(\d+)-(\d+)-(\d+)', raw)
        hdr = {'User-Agent': UA, 'Referer': self.host + '/'}
        if not m:
            return {'parse': 0, 'jx': 0, 'url': '', 'header': hdr}
        page = '%s/vodplay/%s-%s-%s.html' % (self.host, m.group(1), m.group(2), m.group(3))
        html = self._get(page)
        play_url = self._decode_player(html)
        if not play_url:
            hm = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html or '')
            if hm:
                play_url = hm.group(1)
        if not play_url:
            return {'parse': 1, 'jx': 0, 'url': page, 'header': hdr}
        # 直链媒体 parse0，外链播放器 parse1
        if self.isVideoFormat(play_url):
            return {'parse': 0, 'jx': 0, 'url': play_url, 'header': hdr}
        return {'parse': 1, 'jx': 0, 'url': play_url, 'header': hdr}


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print(sp.homeContent(False))
    c = sp.categoryContent('2', '1', False, {})
    print('list', len(c['list']), c['list'][:2] if c['list'] else None)
    if c['list']:
        d = sp.detailContent([c['list'][0]['vod_id']])
        print(d['list'][0]['vod_name'], d['list'][0]['vod_play_from'])
        pid = d['list'][0]['vod_play_url'].split('#')[0].split('$')[-1]
        print(sp.playerContent('', pid, []))

# -*- coding: utf-8 -*-
# 看片狂人 (kpkuang.fun) TVBox 爬虫
# 列表: /vodtype/{id}/  分页: /vodtype/{id}-{page}/
# 详情: /voddetail/{id}/  播放: /vodplay/{id}-{sid}-{nid}.html
# 主题: MacCMS FED；播放页可能触发 CF，优先解 player_aaaa，失败则 parse=1
import re
import json
import sys
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
DEFAULT_HOST = 'https://www.kpkuang.fun'

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
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        self._sess = None
        if requests is not None:
            try:
                self._sess = requests.Session()
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

    def _get(self, url, timeout=15, referer=None):
        if not url.startswith('http'):
            url = self.host + url
        headers = dict(self.headers)
        if referer:
            headers['Referer'] = referer
        if self._sess is not None:
            try:
                r = self._sess.get(url, headers=headers, timeout=timeout, verify=False)
                # CF challenge
                if r.status_code == 403 or 'Just a moment' in (r.text or '')[:500]:
                    return ''
                if r.status_code == 200:
                    r.encoding = r.apparent_encoding or 'utf-8'
                    return r.text
            except Exception:
                pass
        try:
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _abs(self, u):
        u = str(u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        # fed-list-item 卡片
        blocks = re.findall(r'<li[^>]*class="[^"]*fed-list-item[^"]*"[\s\S]*?</li>', html)
        if not blocks:
            blocks = re.split(r'<li[^>]*>', html)[1:]
        for b in blocks:
            m = re.search(r'href="(/voddetail/(\d+)/?)"', b)
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
                r'alt="([^"]+)"',
                r'fed-list-title[^>]*>([^<]+)',
            ]:
                tm = re.search(pat, b)
                if tm and tm.group(1).strip():
                    title = tm.group(1).strip()
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
                remarks = re.sub(r'\s+', ' ', rm.group(1)).strip()
            if not remarks:
                rm = re.search(r'fed-list-remarks[^>]*>([^<]+)', b)
                if rm:
                    remarks = rm.group(1).strip()
            items.append({
                'vod_id': vid,
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        return items

    def homeContent(self, filter):
        classes = [{'type_id': a, 'type_name': b} for a, b in CATS]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        return {'list': self._parse_list(html)[:48]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        tid = str(tid).strip()
        if page <= 1:
            url = '%s/vodtype/%s/' % (self.host, tid)
        else:
            url = '%s/vodtype/%s-%d/' % (self.host, tid, page)
        html = self._get(url)
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 24 else page
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
        # 站点搜索常被 CF 拦截，多路径尝试
        candidates = [
            '%s/vodsearch/%s-------------.html' % (self.host, kw),
            '%s/vodsearch/-------------.html?wd=%s' % (self.host, kw),
            '%s/?m=vod-search&wd=%s' % (self.host, kw),
        ]
        if page > 1:
            candidates = [
                '%s/vodsearch/%s----------%d---.html' % (self.host, kw, page),
            ] + candidates
        items = []
        for url in candidates:
            html = self._get(url, referer=self.host + '/')
            items = self._parse_list(html)
            if items:
                break
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if len(items) >= 12 else page,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        vid = re.sub(r'\D', '', vid.split('/')[-1]) or vid
        html = self._get('%s/voddetail/%s/' % (self.host, vid))
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
            if not m:
                return ''
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()

        content = ''
        cm = re.search(r'(?:剧情|简介)[：:]</[^>]+>\s*<[^>]+>([\s\S]*?)</div>', html)
        if cm:
            content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()

        play_from, play_url = [], []
        # 按 fed-play-item 分组
        blocks = re.split(r'class="fed-play-item[^"]*"', html)
        for block in blocks[1:]:
            lab = re.search(r'uk-label">([^<]+)', block)
            name = lab.group(1).strip() if lab else ''
            if not name:
                continue
            # 跳过非线路标签（年份/类型等）
            eps = []
            for em in re.finditer(
                r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]*)',
                block,
            ):
                if em.group(2) != vid:
                    continue
                en = re.sub(r'\s+', ' ', em.group(5)).strip() or ('第%s集' % em.group(4))
                eps.append('%s$%s-%s-%s' % (en, em.group(2), em.group(3), em.group(4)))
            if eps:
                play_from.append(name)
                play_url.append('#'.join(eps))

        if not play_url:
            # 兜底按 sid 分组
            by_sid = {}
            for em in re.finditer(r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]*)', html):
                if em.group(2) != vid:
                    continue
                sid = em.group(3)
                en = re.sub(r'\s+', ' ', em.group(5)).strip() or ('第%s集' % em.group(4))
                by_sid.setdefault(sid, []).append('%s$%s-%s-%s' % (en, em.group(2), sid, em.group(4)))
            for i, (sid, eps) in enumerate(by_sid.items()):
                play_from.append('线路' + sid)
                play_url.append('#'.join(eps))

        vod = {
            'vod_id': vid,
            'vod_name': title or ('影片 ' + vid),
            'vod_pic': pic,
            'vod_year': meta('年份') or meta('上映'),
            'vod_area': meta('地区'),
            'vod_actor': meta('主演') or meta('演员'),
            'vod_director': meta('导演'),
            'type_name': meta('类型') or meta('分类'),
            'vod_content': content[:800],
            'vod_remarks': meta('备注') or '',
            'vod_play_from': '$$$'.join(play_from) if play_from else '看片狂人',
            'vod_play_url': '$$$'.join(play_url) if play_url else '',
        }
        return {'list': [vod]}

    def _decode_player(self, html):
        if not html:
            return ''
        mm = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>', html)
        if not mm:
            mm = re.search(r'player_[a-z0-9]+\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>', html, re.I)
        if mm:
            try:
                obj = json.loads(mm.group(1))
                u = str(obj.get('url') or '').strip()
                enc = int(obj.get('encrypt') or 0)
                if enc == 1:
                    u = unquote(u)
                elif enc == 2:
                    import base64
                    try:
                        u = unquote(base64.b64decode(u + '=' * ((-len(u)) % 4)).decode('utf-8', 'ignore'))
                    except Exception:
                        pass
                if u.startswith('//'):
                    u = 'https:' + u
                if re.match(r'^https?:', u):
                    return u
            except Exception:
                pass
        hm = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html)
        if hm:
            return hm.group(1)
        hm = re.search(r'(https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*)', html)
        if hm:
            return hm.group(1)
        return ''

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '').strip()
        m = re.search(r'(\d+)-(\d+)-(\d+)', raw)
        hdr = {'User-Agent': UA, 'Referer': self.host + '/'}
        if not m:
            return {'parse': 1, 'jx': 0, 'url': raw, 'header': hdr}
        vid, sid, nid = m.group(1), m.group(2), m.group(3)
        page = '%s/vodplay/%s-%s-%s.html' % (self.host, vid, sid, nid)
        html = self._get(page, referer='%s/voddetail/%s/' % (self.host, vid))
        play_url = self._decode_player(html)
        if play_url:
            return {
                'parse': 0 if self.isVideoFormat(play_url) else 1,
                'jx': 0,
                'url': play_url,
                'header': hdr,
            }
        # 播放页常被 Cloudflare 拦截：交给壳解析
        return {'parse': 1, 'jx': 0, 'url': page, 'header': hdr}


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print(sp.homeContent(False))
    print(len(sp.categoryContent('1', '1', False, {})['list']))

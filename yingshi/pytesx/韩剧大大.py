# -*- coding: utf-8 -*-
# 韩剧大大 (hanjudada.com) TVBox 爬虫
# 列表: /vodtype/{id}.html  详情: /hanju/{id}.html  播放: /player/{id}-{sid}-{nid}.html
# 播放: player_aaaa encrypt=1 → urllib.parse.unquote
import re
import json
import sys
from urllib.parse import quote, unquote, urljoin

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
DEFAULT_HOST = 'https://www.hanjudada.com'

# 分类按站点年份导航
CATS = [
    ('122', '2026年韩剧'),
    ('121', '2025年韩剧'),
    ('120', '2024年韩剧'),
    ('119', '2023年韩剧'),
    ('118', '2022年韩剧'),
    ('117', '2021年韩剧'),
    ('116', '2020年韩剧'),
    ('96', '2019年韩剧'),
    ('97', '2018年韩剧'),
    ('98', '2017年韩剧'),
    ('99', '2016年韩剧'),
    ('100', '2015年韩剧'),
    ('101', '2014年韩剧'),
    ('102', '2013年韩剧'),
    ('103', '2012年韩剧'),
    ('104', '2011年韩剧'),
    ('105', '2010年韩剧'),
    ('106', '2009年韩剧'),
    ('107', '2008年韩剧'),
    ('108', '2007年韩剧'),
    ('109', '2006年韩剧'),
    ('110', '2005年韩剧'),
    ('111', '2004年韩剧'),
    ('112', '2003年韩剧'),
    ('113', '2002年韩剧'),
    ('114', '2001年韩剧'),
    ('115', '2000年及以前'),
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
        return '韩剧大大'

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

    # ---------------- 网络 ----------------
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
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=self.headers)
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'replace')
        except Exception:
            return ''

    # ---------------- 列表解析 ----------------
    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        # <li><a class="lianzai-img" href="/hanju/4417.html" title="..."><img src="..."/><h2>...</h2><p>...</p><i>已完结</i>
        blocks = re.split(r'<li>', html)
        for b in blocks[1:]:
            m = re.search(r'href="(/hanju/(\d+)\.html)"', b)
            if not m:
                continue
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = ''
            tm = re.search(r'title="([^"]+)"', b)
            if tm:
                title = tm.group(1).strip()
            if not title:
                hm = re.search(r'<h2>([^<]+)</h2>', b)
                if hm:
                    title = hm.group(1).strip()
            if not title:
                continue
            pic = ''
            pm = re.search(r'<img[^>]+src="([^"]+)"', b)
            if pm:
                pic = pm.group(1)
                if pic.startswith('//'):
                    pic = 'https:' + pic
                elif pic.startswith('/'):
                    pic = self.host + pic
            remarks = ''
            rm = re.search(r'<i>([^<]*)</i>', b)
            if rm:
                remarks = rm.group(1).strip()
            items.append({
                'vod_id': vid,
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        return items

    # ---------------- TVBox 接口 ----------------
    def homeContent(self, filter):
        classes = [{'type_id': cid, 'type_name': cname} for cid, cname in CATS]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        return {'list': self._parse_list(html)[:48]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        tid = str(tid).strip()
        # 站点多数分类一次列出，分页格式 /vodtype/{id}-{page}.html
        if page <= 1:
            url = '%s/vodtype/%s.html' % (self.host, tid)
        else:
            url = '%s/vodtype/%s-%d.html' % (self.host, tid, page)
        html = self._get(url)
        items = self._parse_list(html)
        # 估算页数
        pagecount = page
        if items and len(items) >= 24:
            pagecount = page + 1
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
        # 实测可用: /index.php?m=vod-search&wd=
        url = '%s/index.php?m=vod-search&wd=%s' % (self.host, kw)
        if page > 1:
            url += '&page=%d' % page
        html = self._get(url)
        items = self._parse_list(html)
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if len(items) >= 12 else page,
            'limit': len(items) or 24,
            'total': 9999,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        vid = re.sub(r'\D', '', vid.split('/')[-1].replace('.html', '')) or vid
        html = self._get('%s/hanju/%s.html' % (self.host, vid))
        if not html:
            return {'list': []}

        title = ''
        tm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html)
        if tm:
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            title = re.sub(r'\s*(已完结|更新至.*)$', '', title).strip()

        pic = ''
        pm = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if not pm:
            pm = re.search(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', html, re.I)
        if pm:
            pic = pm.group(1)

        def _dl(label):
            m = re.search(r'<dt>%s：</dt>\s*<dd>([\s\S]*?)</dd>' % label, html)
            if not m:
                return ''
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()

        actor = _dl('主演')
        director = _dl('导演')
        area = _dl('地区')
        year = _dl('年份')
        type_name = _dl('类型')
        content = ''
        cm = re.search(r'class="tjuqing">([\s\S]*?)</div>', html)
        if cm:
            content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()

        # 线路: id="playlist_{sid}" ... <span>线路名</span> ... <a href="/player/{id}-{sid}-{nid}.html">第xx集
        play_from, play_url = [], []
        blocks = re.split(r'<div[^>]+id="playlist_(\d+)"', html)
        # blocks: [before, sid1, content1, sid2, content2, ...]
        i = 1
        while i + 1 < len(blocks):
            sid = blocks[i]
            body = blocks[i + 1]
            # 线路名
            nm = '线路' + sid
            sm = re.search(r'<span>([^<]{1,20})</span>', body)
            if sm:
                nm = sm.group(1).strip() or nm
            eps = []
            for em in re.finditer(
                r'href="(/player/%s-%s-(\d+)\.html)"[^>]*>([\s\S]*?)</a>' % (vid, sid),
                body,
            ):
                name = re.sub(r'<[^>]+>', '', em.group(3)).strip() or ('第%s集' % em.group(2))
                eps.append('%s$%s-%s-%s' % (name, vid, sid, em.group(2)))
            if eps:
                play_from.append(nm)
                play_url.append('#'.join(eps))
            i += 2

        # 兜底扫全部 player 链接
        if not play_url:
            eps, seen = [], set()
            for em in re.finditer(r'href="(/player/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([\s\S]*?)</a>', html):
                key = em.group(1)
                if key in seen:
                    continue
                seen.add(key)
                name = re.sub(r'<[^>]+>', '', em.group(5)).strip() or ('第%s集' % em.group(4))
                eps.append('%s$%s-%s-%s' % (name, em.group(2), em.group(3), em.group(4)))
            if eps:
                play_from = ['默认']
                play_url = ['#'.join(eps)]

        vod = {
            'vod_id': vid,
            'vod_name': title or ('韩剧 ' + vid),
            'vod_pic': pic,
            'vod_year': year,
            'vod_area': area,
            'vod_actor': actor,
            'vod_director': director,
            'type_name': type_name,
            'vod_content': content[:800],
            'vod_remarks': '',
            'vod_play_from': '$$$'.join(play_from) if play_from else '韩剧大大',
            'vod_play_url': '$$$'.join(play_url) if play_url else '',
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '').strip()
        # id 形如 4417-2-1 或完整路径
        m = re.search(r'(\d+)-(\d+)-(\d+)', raw)
        if not m:
            return {'parse': 0, 'url': '', 'jx': 0}
        vid, sid, nid = m.group(1), m.group(2), m.group(3)
        url = '%s/player/%s-%s-%s.html' % (self.host, vid, sid, nid)
        html = self._get(url)
        play_url = ''
        mm = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>', html)
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
                play_url = u
            except Exception:
                pass
        if not play_url:
            # 兜底明文 m3u8
            hm = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html)
            if hm:
                play_url = hm.group(1)
        return {
            'parse': 0 if play_url else 1,
            'jx': 0,
            'url': play_url or url,
            'header': {
                'User-Agent': UA,
                'Referer': self.host + '/',
            },
        }


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print(sp.homeContent(False))
    print(sp.categoryContent('121', '1', False, {}))

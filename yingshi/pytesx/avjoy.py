# -*- coding: utf-8 -*-
"""
AVJOY https://cn.avjoy.ws
按可用 JS 对齐：分类 videos + search:关键词
兼容影视仓 / OK影视
"""
import re
from urllib.parse import quote

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    import requests as req_lib
except Exception:
    req_lib = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def fetch(self, url, headers=None, timeout=15, **kw):
            import requests as rq
            r = rq.get(url, headers=headers or {}, timeout=timeout, verify=False, **kw)
            class R:
                pass
            o = R()
            o.text = r.text
            o.content = getattr(r, 'content', b'')
            o.status_code = r.status_code
            o.url = r.url
            return o


HOST = 'https://cn.avjoy.ws'
HOSTS = [
    'https://cn.avjoy.ws',
    'https://www.avjoy.ws',
    'https://avjoy.ws',
]
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
)

# 与可用 JS 完全一致
CLASS_LIST = [
    {'type_id': 'videos', 'type_name': '最新视频'},
    {'type_id': 'search:中文字幕', 'type_name': '中文字幕'},
    {'type_id': 'search:无码', 'type_name': '无码'},
    {'type_id': 'search:有码', 'type_name': '有码'},
    {'type_id': 'search:自拍', 'type_name': '自拍'},
    {'type_id': 'search:探花', 'type_name': '探花'},
    {'type_id': 'search:国产', 'type_name': '国产'},
    {'type_id': 'search:FC2', 'type_name': 'FC2'},
    {'type_id': 'search:欧美', 'type_name': '欧美'},
    {'type_id': 'search:韩国', 'type_name': '韩国'},
    # 额外站点路径分类
    {'type_id': 'videos/amateur', 'type_name': 'Amateur・素人'},
    {'type_id': 'videos/anal', 'type_name': 'Anal・アナル'},
    {'type_id': 'videos/japan', 'type_name': 'Japan・日本'},
    {'type_id': 'videos/jav', 'type_name': 'JAV'},
]


class Spider(BaseSpider):

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.host = HOST
        self._ua = UA

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')
        return self

    def getName(self):
        return 'AVJOY'

    def isVideoFormat(self, url):
        low = (url or '').lower()
        return any(k in low for k in ('.m3u8', '.mp4', '.flv', '.ts'))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _headers(self):
        return {
            'User-Agent': self._ua,
            'Referer': self.host + '/videos',
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def _fetch(self, url, timeout=25):
        if not url:
            return ''
        if url.startswith('/'):
            url = self.host + url
        for h in HOSTS:
            if url.rstrip('/') == h.rstrip('/'):
                url = h + '/videos'
                break

        host_order = [self.host] + [x for x in HOSTS if x != self.host]
        tried = []
        for h in host_order:
            u = url
            for hh in HOSTS:
                if url.startswith(hh):
                    u = h + url[len(hh):]
                    break
            if u in tried:
                continue
            tried.append(u)
            text = ''
            if req_lib is not None:
                try:
                    r = req_lib.get(u, headers=self._headers(), timeout=timeout, verify=False)
                    if r.status_code == 200 and r.text and len(r.text) > 800:
                        text = r.text
                        self.host = h
                except Exception:
                    pass
            if not text:
                try:
                    r = self.fetch(u, headers=self._headers(), timeout=timeout)
                    text = getattr(r, 'text', '') or ''
                    if len(text) > 800:
                        self.host = h
                except Exception:
                    text = ''
            if text and len(text) > 800:
                if '\\/video' in text or 'href=\\"' in text:
                    text = (
                        text.replace('\\/', '/')
                        .replace('\\"', '"')
                        .replace('\\n', '\n')
                    )
                return text
        return ''

    def _parse_list(self, html):
        """与 JS parseList 一致"""
        results, seen = [], set()
        if not html:
            return results
        for m in re.finditer(r'href=["\'](/video/(\d+)/([^"\']+))["\']', html, re.I):
            path, vid, slug = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            block = html[max(0, m.start() - 100): m.start() + 500]
            pic = ''
            pm = re.search(
                r'(?:data-src|src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
                block, re.I
            )
            if not pm:
                pm = re.search(
                    r'(?:data-src|src)=["\'](/[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
                    block, re.I
                )
            if pm:
                pic = pm.group(1)
                if pic.startswith('/'):
                    pic = self.host + pic
            title = (slug or '').replace('-', ' ')
            tm = re.search(r'(?:alt|title)=["\']([^"\']{2,120})["\']', block)
            if tm:
                title = tm.group(1).strip()
            results.append({
                'vod_id': path,
                'vod_name': title[:120],
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return results

    def homeContent(self, filter=False):
        # 与 JS 一样先给 class；顺带带 list 方便部分壳
        try:
            lst = self._parse_list(self._fetch(self.host + '/videos'))[:24]
        except Exception:
            lst = []
        return {'class': list(CLASS_LIST), 'list': lst, 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._parse_list(self._fetch(self.host + '/videos'))[:24]}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        """完全按 JS category 逻辑"""
        try:
            page = max(1, int(str(pg) or 1))
        except Exception:
            page = 1
        tid = str(tid or 'videos').strip()

        # 兼容旧 path 分类
        if tid in ('全部影片', '全部', 'all', '最新视频'):
            tid = 'videos'
        if tid in ('amateur', '素人'):
            tid = 'videos/amateur'

        if tid.startswith('search:'):
            key = tid[7:]  # 与 JS tid.slice(7) 一致
            url = self.host + '/search/videos/' + quote(key)
            if page > 1:
                url += '?page=%d' % page
        elif tid.startswith('videos/') or tid.startswith('/videos/'):
            url = self.host + '/' + tid.lstrip('/')
            if page > 1:
                url += '?page=%d' % page
        else:
            # 默认 /videos 与 JS 一致
            url = self.host + '/videos'
            if page > 1:
                url += '?page=%d' % page

        html = self._fetch(url)
        vods = self._parse_list(html)

        # 空则再试一次 /videos
        if len(vods) < 2 and not tid.startswith('search:'):
            html = self._fetch(self.host + '/videos')
            vods = self._parse_list(html)

        return {
            'list': vods or [],
            'page': page,
            'pagecount': page + 1 if len(vods) >= 12 else page,
            'limit': 24,
            'total': 9999 if vods else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        try:
            page = max(1, int(str(pg) or 1))
        except Exception:
            page = 1
        url = self.host + '/search/videos/' + quote(str(key or '').strip())
        if page > 1:
            url += '?page=%d' % page
        vods = self._parse_list(self._fetch(url))
        return {
            'list': vods or [],
            'page': page,
            'pagecount': page + 1 if len(vods) >= 12 else page,
            'limit': 24,
            'total': 9999 if vods else 0,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        path = str(raw or '').strip()
        if not path.startswith('http'):
            path = self.host + (path if path.startswith('/') else '/video/' + path)
        html = self._fetch(path)
        name = ''
        m = re.search(r'<title>([^<]+)', html or '', re.I)
        if m:
            name = re.sub(r'\s*[-|].*AVJOY.*$', '', m.group(1), flags=re.I).strip()
        pic = ''
        m = re.search(r'og:image["\']\s+content=["\']([^"\']+)', html or '', re.I)
        if m:
            pic = m.group(1)
        plays, seen = [], set()
        for m in re.finditer(r'<source[^>]+src=["\']([^"\']+)["\']', html or '', re.I):
            u = m.group(1)
            if not u.startswith('http') or u in seen:
                continue
            seen.add(u)
            label = 'MP4'
            qm = re.search(r'(\d{3,4})p', u, re.I)
            if qm:
                label = qm.group(1) + 'P'
            plays.append((label, u))
        for m in re.finditer(r'(https?://[^"\'\s<>]+\.(?:mp4|m3u8)[^"\'\s<>]*)', html or '', re.I):
            u = m.group(1)
            if u in seen:
                continue
            seen.add(u)
            plays.append(('直链', u))
        if plays:
            play_from = '$$$'.join([n for n, _ in plays])
            play_url = '$$$'.join(['正片$%s' % u for _, u in plays])
        else:
            play_from = 'AVJOY'
            play_url = '正片$%s' % path
        return {'list': [{
            'vod_id': path,
            'vod_name': name or 'AVJOY',
            'vod_pic': pic,
            'vod_play_from': play_from,
            'vod_play_url': play_url,
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id or '').strip()
        if '$' in url and not url.startswith('http'):
            url = url.split('$')[-1]
        header = {
            'User-Agent': self._ua,
            'Referer': self.host + '/',
        }
        if re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I):
            return {'parse': 0, 'jx': 0, 'url': url, 'header': header}
        if '/video/' in url:
            d = self.detailContent([url])
            item = (d.get('list') or [{}])[0]
            pu = item.get('vod_play_url') or ''
            for part in pu.split('$$$'):
                if '$' in part:
                    u = part.split('$', 1)[-1]
                    if re.search(r'\.(m3u8|mp4)', u, re.I):
                        return {'parse': 0, 'jx': 0, 'url': u, 'header': header}
        return {'parse': 0, 'jx': 0, 'url': '', 'header': header}


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    h = sp.homeContent()
    print('class', [c['type_name'] for c in h['class'][:6]], 'list', len(h['list']))
    for tid in ['videos', 'search:中文字幕', 'search:无码', 'videos/amateur']:
        r = sp.categoryContent(tid, 1)
        print(tid, len(r['list']), (r['list'][0]['vod_name'][:28] if r['list'] else '-'))

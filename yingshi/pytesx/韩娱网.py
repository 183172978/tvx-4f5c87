# -*- coding: utf-8 -*-
"""
韩娱网 https://koreayule.com
风格对齐 dage.py（列表/详情/播放流程）
分类：首页分区 + sitemap 补全
播放：player_aaaa.url 直出 m3u8
"""
import re
import json
import sys
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://koreayule.com'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        self.channels = {
            'hot': '正在热播',
            'tv': '韩剧',
            'movie': '韩国电影',
            'zongyi': '韩综',
            'dongman': '韩漫',
        }
        self._sitemap_cache = {}

    def getName(self):
        return '韩娱网'

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')

    def _headers(self, referer=None):
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or (self.host + '/'),
        }

    def _get(self, url, referer=None):
        try:
            headers = self._headers(referer)
            if not url.startswith('http'):
                url = self.host + (url if url.startswith('/') else '/' + url)
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=headers, timeout=20, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('GET error', url, e)
            return ''

    def _abs(self, path):
        if not path:
            return ''
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return 'https:' + path
        return self.host + (path if path.startswith('/') else '/' + path)

    def _parse_cards(self, html, prefix=None):
        """解析 mj-card 列表，prefix 如 /tv/ /movie/ 过滤"""
        items = []
        seen = set()
        if not html:
            return items
        blocks = re.split(r'class="mj-card(?:\s|"|[^"]*mj-animate)', html)
        for b in blocks[1:]:
            hm = re.search(
                r'href="(/(?:tv|movie|zongyi|dongman)/([^"?#]+))"',
                b
            )
            if not hm:
                continue
            path = hm.group(1).rstrip('/')
            if prefix and not path.startswith(prefix.rstrip('/')):
                continue
            if path in seen:
                continue
            seen.add(path)
            title = ''
            # 卡片标题常在下方
            tm = re.search(
                r'class="[^"]*mj-card__title[^"]*"[^>]*>([\s\S]*?)<',
                b
            )
            if tm:
                title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            if not title:
                am = re.search(r'alt="([^"]+)"', b)
                if am:
                    title = am.group(1).strip()
            if not title:
                title = hm.group(2).replace('-', ' ')
            pic = ''
            im = re.search(
                r'data-src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                b, re.I
            )
            if not im:
                im = re.search(
                    r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    b, re.I
                )
            if im:
                pic = im.group(1)
            note = ''
            nm = re.search(
                r'class="[^"]*mj-card__(?:badge|meta|note)[^"]*"[^>]*>([\s\S]*?)<',
                b
            )
            if nm:
                note = re.sub(r'<[^>]+>', '', nm.group(1)).strip()
            items.append({
                'vod_id': path,
                'vod_name': title[:120],
                'vod_pic': pic,
                'vod_remarks': note or '韩娱网',
            })
        return items

    def _sitemap_list(self, kind):
        """从 sitemap 提取某类路径"""
        if kind in self._sitemap_cache:
            return self._sitemap_cache[kind]
        html = self._get(self.host + '/sitemap')
        paths = re.findall(
            r'href="(/%s/[a-z0-9\-]+)"' % re.escape(kind),
            html or ''
        )
        # 去重保序
        seen, out = set(), []
        for p in paths:
            p = p.rstrip('/')
            if p not in seen:
                seen.add(p)
                out.append(p)
        self._sitemap_cache[kind] = out
        return out

    def homeContent(self, filter=False):
        return {
            'class': [
                {'type_id': k, 'type_name': v}
                for k, v in self.channels.items()
            ],
            'filters': {},
        }

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        return {'list': self._parse_cards(html)[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or 'hot')
        size = 24
        videos = []

        if tid == 'hot':
            html = self._get(self.host + '/')
            videos = self._parse_cards(html)
            # 热播只取首页
            start = (pg - 1) * size
            page_items = videos[start:start + size]
            return {
                'list': page_items,
                'page': pg,
                'pagecount': max(1, (len(videos) + size - 1) // size),
                'limit': size,
                'total': len(videos),
            }

        # tv / movie / zongyi / dongman
        prefix = '/' + tid + '/'
        # 先首页分区
        html = self._get(self.host + '/')
        home_items = self._parse_cards(html, prefix=prefix)
        # sitemap 补全
        sm_paths = self._sitemap_list(tid)
        seen = {x['vod_id'] for x in home_items}
        for p in sm_paths:
            if p in seen:
                continue
            slug = p.rsplit('/', 1)[-1]
            home_items.append({
                'vod_id': p,
                'vod_name': slug.replace('-', ' '),
                'vod_pic': '',
                'vod_remarks': '韩娱网',
            })
            seen.add(p)

        start = (pg - 1) * size
        page_items = home_items[start:start + size]
        return {
            'list': page_items,
            'page': pg,
            'pagecount': max(1, (len(home_items) + size - 1) // size),
            'limit': size,
            'total': len(home_items),
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        path = str(raw or '').strip()
        if not path:
            return {'list': []}
        if path.startswith('http'):
            detail_url = path
            m = re.search(r'https?://[^/]+(/.+)', path)
            path = m.group(1) if m else path
        else:
            if not path.startswith('/'):
                path = '/tv/' + path
            detail_url = self._abs(path)

        # 去掉集数
        base = re.sub(r'/\d+\?.*$', '', path)
        base = re.sub(r'\?.*$', '', base)
        detail_url = self._abs(base)

        html = self._get(detail_url)
        if not html:
            return {'list': []}

        title = ''
        m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
        if m:
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not title:
            m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                title = m.group(1).split('_')[0].split('|')[0].strip()

        pic = ''
        m = re.search(
            r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
            html, re.I
        )
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(
                r'data-src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                html, re.I
            )
            if m:
                pic = m.group(1)

        # 多线路 sid
        # /tv/slug/1?sid=3
        groups = {}  # sid -> [(epname, url)]
        order = []
        for m in re.finditer(
            r'href="((/(?:tv|movie|zongyi|dongman)/[^"/]+)/(\d+)\?sid=(\d+))"[^>]*>([\s\S]{0,60}?)</a>',
            html, re.I
        ):
            full, _base, nid, sid, text = m.groups()
            name = re.sub(r'<[^>]+>', '', text).strip() or ('第%s集' % nid)
            if sid not in groups:
                groups[sid] = []
                order.append(sid)
            groups[sid].append((name, self._abs(full)))

        # 电影可能只有一集
        if not groups:
            # 尝试直接进播放
            for m in re.finditer(
                r'href="((/(?:tv|movie|zongyi|dongman)/[^"/]+)/\d+\?sid=\d+)"',
                html
            ):
                sid = re.search(r'sid=(\d+)', m.group(1)).group(1)
                if sid not in groups:
                    groups[sid] = []
                    order.append(sid)
                groups[sid].append(('正片', self._abs(m.group(1))))

        play_from, play_url = [], []
        for i, sid in enumerate(order):
            eps = groups[sid]
            if not eps:
                continue
            # 去重保序
            seen_u, uniq = set(), []
            for n, u in eps:
                if u in seen_u:
                    continue
                seen_u.add(u)
                uniq.append('%s$%s' % (n, u))
            play_from.append('线路' + sid)
            play_url.append('#'.join(uniq))

        if not play_from:
            # 默认第一集
            play_from = ['线路1']
            play_url = ['第1集$%s/1?sid=3' % detail_url.rstrip('/')]

        return {
            'list': [{
                'vod_id': base,
                'vod_name': title or base,
                'vod_pic': pic,
                'vod_remarks': '韩娱网',
                'vod_content': '',
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        """搜索：sitemap + 首页模糊匹配（站内搜索为前端渲染）"""
        pg = int(pg or 1)
        key = str(key or '').strip().lower()
        if not key:
            return {'list': []}
        results = []
        seen = set()
        # 首页
        for it in self._parse_cards(self._get(self.host + '/')):
            if key in (it.get('vod_name') or '').lower() or key.replace(' ', '-') in (it.get('vod_id') or ''):
                if it['vod_id'] not in seen:
                    results.append(it)
                    seen.add(it['vod_id'])
        # sitemap 各类型
        for kind in ('tv', 'movie', 'zongyi', 'dongman'):
            for p in self._sitemap_list(kind):
                slug = p.rsplit('/', 1)[-1]
                name = slug.replace('-', ' ')
                if key in name.lower() or key.replace(' ', '-') in slug:
                    if p not in seen:
                        results.append({
                            'vod_id': p,
                            'vod_name': name,
                            'vod_pic': '',
                            'vod_remarks': '韩娱网',
                        })
                        seen.add(p)
        size = 24
        start = (pg - 1) * size
        page_items = results[start:start + size]
        return {
            'list': page_items,
            'page': pg,
            'pagecount': max(1, (len(results) + size - 1) // size),
            'limit': size,
            'total': len(results),
        }

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}

        # 播放页
        url = play if play.startswith('http') else self._abs(play)
        html = self._get(url)
        # player_aaaa
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html or '', re.S)
        if m:
            try:
                # 截到第一个完整 JSON
                text = m.group(1)
                # 容错：只取到匹配的 }
                depth, end = 0, 0
                for i, ch in enumerate(text):
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                obj = json.loads(text[:end] if end else text)
                real = (obj.get('url') or '').replace('\\/', '/')
                if real.startswith('http'):
                    return {'parse': 0, 'jx': 0, 'url': real, 'header': header}
            except Exception as e:
                print('player_aaaa parse', e)

        m3 = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html or '')
        for u in m3:
            if 'preview' not in u.lower():
                return {'parse': 0, 'jx': 0, 'url': u.replace('&amp;', '&'), 'header': header}

        return {'parse': 1, 'jx': 0, 'url': url, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

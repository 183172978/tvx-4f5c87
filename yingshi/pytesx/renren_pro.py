# -*- coding: utf-8 -*-
# 人人影视PRO https://www.renren.pro
# 模板参考: javmenu.py
import re
import json
import sys
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


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://www.renren.pro'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        )
        # 站点实际仅有影片库列表，首页作推荐
        self.channels = {
            'all': {'name': '全部', 'path': '/list/all'},
            'home': {'name': '最新热播', 'path': '/'},
        }

    def getName(self):
        return '人人影视PRO'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('host'):
                    self.host = conf['host'].rstrip('/')
            except Exception:
                pass

    def _headers(self, referer=None):
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or (self.host + '/'),
        }

    def _get(self, url, referer=None):
        try:
            if requests is None:
                import urllib.request
                req = urllib.request.Request(url, headers=self._headers(referer))
                with urllib.request.urlopen(req, timeout=18) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self._headers(referer), timeout=18, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('GET error', url, e)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        if not u.startswith('http'):
            return self.host + '/' + u
        return u

    def _parse_list(self, html):
        """从列表/首页/搜索页提取影片"""
        videos, seen = [], set()
        if not html:
            return videos

        # 优先匹配 .module-item 块
        for block in re.finditer(
            r'<div[^>]*class="[^"]*module-item[^"]*"[^>]*>([\s\S]*?)</div>\s*(?=<div[^>]*class="[^"]*module-item|</div>\s*</div>\s*<div|$)',
            html, re.I
        ):
            chunk = block.group(0)
            hm = re.search(r'href="(/play/[a-f0-9-]+)"', chunk, re.I)
            if not hm:
                continue
            href = hm.group(1)
            if href in seen:
                continue
            seen.add(href)

            title = ''
            tm = re.search(r'title="([^"]{2,120})"', chunk)
            if tm:
                title = tm.group(1).strip()
            if not title:
                tm = re.search(r'class="[^"]*module-item-title[^"]*"[^>]*>([^<]+)', chunk)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                tm = re.search(r'alt="([^"]{2,120})"', chunk)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                continue

            pic = ''
            for pat in (
                r'data-src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                r'src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
            ):
                pm = re.search(pat, chunk, re.I)
                if pm and 'logo' not in pm.group(1).lower() and 'loading' not in pm.group(1).lower():
                    pic = self._abs(pm.group(1))
                    break

            remarks = ''
            rm = re.search(r'class="[^"]*module-item-text[^"]*"[^>]*>([^<]+)', chunk)
            if rm:
                remarks = rm.group(1).strip()
            if not remarks:
                rm = re.search(r'class="[^"]*module-item-caption[^"]*"[^>]*>([\s\S]*?)</div>', chunk)
                if rm:
                    remarks = re.sub(r'<[^>]+>', ' ', rm.group(1)).strip()[:40]

            videos.append({
                'vod_id': self._abs(href),
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': remarks,
            })

        # 兜底：直接扫 /play/uuid 链接（搜索页等）
        if not videos:
            for m in re.finditer(r'href="(/play/[a-f0-9-]+)"[^>]*(?:title="([^"]*)")?', html, re.I):
                href, title = m.group(1), (m.group(2) or '').strip()
                if href in seen:
                    continue
                # 排除纯剧集子链接（含第二个 uuid）
                if href.count('/') > 2:
                    continue
                seen.add(href)
                if not title or title in ('立即播放', '立刻播放', 'HD中字', '正片'):
                    # 尝试附近文本
                    block = html[max(0, m.start() - 100):m.end() + 300]
                    tm = re.search(r'(?:title|alt)="([^"]{2,100})"', block)
                    if tm:
                        title = tm.group(1).strip()
                    else:
                        continue
                pic = ''
                block = html[max(0, m.start() - 300):m.end() + 400]
                pm = re.search(r'(?:data-src|src)="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I)
                if pm and 'logo' not in pm.group(1).lower():
                    pic = self._abs(pm.group(1))
                videos.append({
                    'vod_id': self._abs(href),
                    'vod_name': title[:90],
                    'vod_pic': pic,
                    'vod_remarks': '',
                })

        return videos

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'all')
        info = self.channels.get(tid) or self.channels['all']
        path = info['path']
        if path == '/':
            # 首页无分页
            if pg > 1:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 24, 'total': 0}
            url = self.host + '/'
        else:
            if pg <= 1:
                url = self.host + path
            else:
                url = self.host + path + '?page=%d' % pg
        html = self._get(url)
        videos = self._parse_list(html)
        pagecount = pg
        if videos and (len(videos) >= 20 or re.search(r'[?&]page=%d' % (pg + 1), html) or '下一页' in html):
            pagecount = pg + 1
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': 9999,
        }

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        page_url = str(ids[0])
        if not page_url.startswith('http'):
            page_url = self.host + (page_url if page_url.startswith('/') else '/play/' + page_url)
        # 只取主 uuid，去掉可能的集数后缀
        base = re.match(r'(https?://[^/]+/play/[a-f0-9-]+)', page_url, re.I)
        if base:
            page_url = base.group(1)

        html = self._get(page_url)
        if not html:
            return result

        name = ''
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            name = re.sub(r'\s*[-|—].*$', '', m.group(1)).strip()
            name = re.sub(r'\s*第\d+集.*$', '', name).strip()
        if not name:
            m = re.search(r'class="[^"]*video-info[^"]*"[^>]*>[\s\S]*?<h1[^>]*>([^<]+)', html)
            if m:
                name = m.group(1).strip()

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            pic = self._abs(m.group(1))

        desc = ''
        m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            desc = m.group(1).strip()[:500]

        # 收集剧集链接：/play/{vod}/{ep}
        plays = []
        seen = set()
        for m in re.finditer(
            r'href="(/play/[a-f0-9-]+/[a-f0-9-]+)"[^>]*>\s*([^<]{1,30})\s*<',
            html, re.I
        ):
            href, ep_name = m.group(1), m.group(2).strip()
            if href in seen:
                continue
            if not re.search(r'第?\d+|集|正片|HD|全', ep_name):
                # 仍接受纯数字按钮
                if not re.match(r'^\d+$', ep_name):
                    continue
            seen.add(href)
            plays.append((ep_name, self._abs(href)))

        # 无分集时，当前页本身可播
        if not plays:
            plays = [('正片', page_url)]

        # 去重保持顺序
        play_url = '#'.join(['%s$%s' % (n, u) for n, u in plays])
        vod = {
            'vod_id': page_url,
            'vod_name': name or '人人影视',
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': '人人影视PRO',
            'vod_play_url': play_url,
        }
        result['list'] = [vod]
        return result

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 0}
        url = self.host + '/search?wd=' + quote(key)
        if pg > 1:
            url += '&page=%d' % pg
        html = self._get(url)
        videos = self._parse_list(html)
        # 搜索页结构可能不同，加强兜底
        if not videos:
            for m in re.finditer(r'href="(/play/[a-f0-9-]+)"', html, re.I):
                href = m.group(1)
                if href.count('/') > 2:
                    continue
                block = html[max(0, m.start() - 200):m.end() + 400]
                title = ''
                tm = re.search(r'(?:title|alt)="([^"]{2,100})"', block)
                if tm:
                    title = tm.group(1).strip()
                if not title or title in ('立即播放', '立刻播放'):
                    continue
                pic = ''
                pm = re.search(r'(?:data-src|src)="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I)
                if pm:
                    pic = self._abs(pm.group(1))
                videos.append({
                    'vod_id': self._abs(href),
                    'vod_name': title[:90],
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
        # 去重
        seen, uniq = set(), []
        for v in videos:
            if v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            uniq.append(v)
        return {
            'list': uniq,
            'page': pg,
            'pagecount': pg + 1 if len(uniq) >= 12 else pg,
            'limit': 24,
            'total': len(uniq),
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
        }
        play = str(id or '').strip()
        # 已是直链
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}

        if not play.startswith('http'):
            play = self._abs(play)
        html = self._get(play, referer=self.host + '/')
        if not html:
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

        # Artplayer url
        m = re.search(r'new\s+Artplayer\s*\(\s*\{[\s\S]{0,1200}?url\s*:\s*["\'](https?://[^"\']+)["\']', html, re.I)
        if m:
            u = m.group(1).replace('&amp;', '&')
            if re.search(r'\.(m3u8|mp4)', u, re.I):
                return {'parse': 0, 'url': u, 'header': header}

        # 通用 m3u8
        for u in re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html):
            u = u.replace('&amp;', '&')
            if 'vod.jpg' in u.lower():
                continue
            return {'parse': 0, 'url': u, 'header': header}

        for u in re.findall(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html):
            u = u.replace('&amp;', '&')
            return {'parse': 0, 'url': u, 'header': header}

        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

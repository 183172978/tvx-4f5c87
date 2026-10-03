#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
西瓜视频 https://m.ixigua.com / https://www.ixigua.com
分类通过关键词搜索实现；多端点兜底解析列表与播放地址。
"""
import base64
import json
import random
import re
import sys
import urllib.parse
import zlib

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    """西瓜视频"""

    def __init__(self):
        self.siteUrl = 'https://m.ixigua.com'
        self.pcUrl = 'https://www.ixigua.com'
        self.playHosts = [
            'https://ib.365yg.com',
            'https://ib.snssdk.com',
            'https://i.snssdk.com',
        ]
        self.userAgent = (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        )
        self.pcUA = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # 分类：用搜索关键词模拟频道
        self.channels = {
            'hot': {'name': '热门', 'kw': '热门'},
            'movie': {'name': '影视', 'kw': '电影'},
            'tv': {'name': '电视剧', 'kw': '电视剧'},
            'short': {'name': '短剧', 'kw': '短剧'},
            'funny': {'name': '搞笑', 'kw': '搞笑'},
            'life': {'name': '生活', 'kw': '生活'},
            'food': {'name': '美食', 'kw': '美食'},
            'game': {'name': '游戏', 'kw': '游戏'},
            'sport': {'name': '体育', 'kw': '体育'},
            'music': {'name': '音乐', 'kw': '音乐'},
            'tech': {'name': '科技', 'kw': '科技'},
            'doc': {'name': '纪录片', 'kw': '纪录片'},
        }
        self._session = None

    def getName(self):
        return '西瓜视频'

    def init(self, extend=""):
        pass

    def _headers(self, mobile=True, referer=None):
        return {
            'User-Agent': self.userAgent if mobile else self.pcUA,
            'Referer': referer or (self.siteUrl + '/' if mobile else self.pcUrl + '/'),
            'Accept': 'application/json, text/plain, */*, text/html;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': self.pcUrl,
        }

    def fetch(self, url, headers=None, params=None, mobile=True):
        if headers is None:
            headers = self._headers(mobile=mobile)
        try:
            if requests:
                if self._session is None:
                    self._session = requests.Session()
                resp = self._session.get(url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15).read()

            class R:
                def __init__(self, raw):
                    self.text = raw.decode('utf-8', 'ignore')
                    self.content = raw

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_text(self, url, params=None, mobile=True):
        resp = self.fetch(url, params=params, mobile=mobile)
        return getattr(resp, 'text', '') if resp else ''

    def fetch_json(self, url, params=None, mobile=True):
        resp = self.fetch(url, params=params, mobile=mobile)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            text = getattr(resp, 'text', '') or ''
            # 去掉 jsonp 包装
            m = re.search(r'(?:callback|jsonp)\s*\(\s*(\{[\s\S]+\}|[[\s\S]+])\s*\)', text, re.I)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
            m = re.search(r'(\{[\s\S]+\})', text)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    return {}
            return {}

    def _abs(self, u):
        if not u:
            return ''
        u = str(u)
        if u.startswith('//'):
            return 'https:' + u
        return u

    def _ssr(self, html):
        """解析页面内嵌 SSR / RENDER_DATA"""
        if not html:
            return {}
        patterns = (
            r'<script[^>]*id=["\']RENDER_DATA["\'][^>]*>([^<]+)</script>',
            r'window\._RENDER_DATA\s*=\s*["\']([^"\']+)["\']',
            r'window\._ROUTER_DATA\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>',
            r'window\._SSR_HYDRATED_DATA\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]*?\})\s*;',
            r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>([^<]+)</script>',
        )
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if not m:
                continue
            raw = m.group(1).strip()
            try:
                if raw.startswith('%') or '%7B' in raw[:12] or '%22' in raw[:12]:
                    raw = urllib.parse.unquote(raw)
                return json.loads(raw)
            except Exception:
                try:
                    # 双重编码
                    raw2 = urllib.parse.unquote(urllib.parse.unquote(raw))
                    return json.loads(raw2)
                except Exception:
                    continue
        return {}

    def _walk(self, obj, acc=None):
        if acc is None:
            acc = []
        if isinstance(obj, dict):
            gid = (
                obj.get('group_id')
                or obj.get('gid')
                or obj.get('item_id')
                or obj.get('video_id')
                or obj.get('aweme_id')
            )
            title = obj.get('title') or obj.get('name') or obj.get('content') or obj.get('desc')
            # 数字 id 至少 10 位，或 v 开头的 vid
            if gid and title:
                acc.append(obj)
            for v in obj.values():
                self._walk(v, acc)
        elif isinstance(obj, list):
            for v in obj:
                self._walk(v, acc)
        return acc

    def _pic_from(self, item):
        for key in (
            'cover', 'poster_url', 'image_url', 'middle_image', 'large_image',
            'origin_cover', 'video_cover', 'cover_image', 'thumb_url',
        ):
            val = item.get(key)
            if isinstance(val, dict):
                pic = val.get('url') or val.get('url_list') or ''
                if isinstance(pic, list):
                    pic = pic[0] if pic else ''
                if isinstance(pic, dict):
                    pic = pic.get('url') or ''
                if pic:
                    return self._abs(pic)
            elif isinstance(val, str) and val.startswith('http'):
                return self._abs(val)
            elif isinstance(val, list) and val:
                first = val[0]
                if isinstance(first, str):
                    return self._abs(first)
                if isinstance(first, dict):
                    return self._abs(first.get('url') or '')
        return ''

    def _map(self, item):
        if not isinstance(item, dict):
            return None
        # 部分搜索结果包在 data / cell / item 里
        if 'data' in item and isinstance(item['data'], dict) and (
            item['data'].get('title') or item['data'].get('group_id')
        ):
            item = item['data']
        vid = str(
            item.get('group_id')
            or item.get('gid')
            or item.get('item_id')
            or item.get('video_id')
            or item.get('aweme_id')
            or item.get('id')
            or ''
        )
        name = (
            item.get('title')
            or item.get('name')
            or item.get('content')
            or item.get('desc')
            or vid
        )
        name = re.sub(r'<[^>]+>', '', str(name)).strip()
        pic = self._pic_from(item)
        user = item.get('user_info') or item.get('user') or item.get('author') or item.get('source') or {}
        remarks = ''
        if isinstance(user, dict):
            remarks = user.get('name') or user.get('nickname') or user.get('source_name') or ''
        elif isinstance(user, str):
            remarks = user
        dur = item.get('video_duration') or item.get('duration') or item.get('video_length') or 0
        try:
            dur = int(float(dur))
            if dur > 0:
                remarks = (remarks + ' ' if remarks else '') + '%d:%02d' % (dur // 60, dur % 60)
        except Exception:
            pass
        # 过滤无效 id
        if not vid:
            return None
        if not re.search(r'\d{10,}', vid) and not re.match(r'^v[0-9a-zA-Z]+$', vid):
            return None
        if not name:
            return None
        return {
            'vod_id': vid,
            'vod_name': name[:80],
            'vod_pic': pic,
            'vod_remarks': str(remarks).strip(),
        }

    def _from_html(self, html):
        videos, seen = [], set()
        data = self._ssr(html)
        for item in self._walk(data):
            v = self._map(item)
            if v and v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                videos.append(v)
        # 正则兜底
        for m in re.finditer(
            r'(?:href|url)=["\'](?:https?://(?:www|m)\.ixigua\.com)?/(?:video/)?(\d{10,})[^"\']*["\']'
            r'[^>]{0,200}?(?:title|alt)=["\']([^"\']+)["\']',
            html or '',
            re.I,
        ):
            vid, name = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if vid in seen or not name or len(name) < 2:
                continue
            seen.add(vid)
            videos.append({'vod_id': vid, 'vod_name': name[:80], 'vod_pic': '', 'vod_remarks': ''})
        for m in re.finditer(
            r'["\']group_id["\']\s*:\s*["\']?(\d{10,})["\']?[^}]{0,300}["\']title["\']\s*:\s*["\']([^"\']+)["\']',
            html or '',
        ):
            vid, name = m.group(1), m.group(2).strip()
            if vid in seen or not name:
                continue
            seen.add(vid)
            videos.append({'vod_id': vid, 'vod_name': name[:80], 'vod_pic': '', 'vod_remarks': ''})
        return videos

    def _dedupe(self, videos):
        seen, out = set(), []
        for v in videos:
            if not v or v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            out.append(v)
        return out

    def _search_api(self, key, offset=0):
        """多端点搜索 API"""
        videos = []
        q = urllib.parse.quote(key)
        endpoints = [
            # PC complex search
            ('%s/api/searchv2/complex/%s/%s' % (self.pcUrl, q, offset), False, None),
            ('%s/api/searchv2/complex/%s/%s?aid=1768&device_platform=webapp' % (self.pcUrl, q, offset), False, None),
            # mobile
            ('%s/api/searchv2/complex/%s/%s' % (self.siteUrl, q, offset), True, None),
            # 带 query 形式
            (self.pcUrl + '/api/searchv2/complex/' + q + '/' + str(offset), False, {'aid': '1768'}),
        ]
        for url, mobile, params in endpoints:
            data = self.fetch_json(url, params=params, mobile=mobile)
            if not data or not isinstance(data, dict):
                continue
            # 常见结构 data.data / data / list
            items = None
            d = data.get('data')
            if isinstance(d, dict):
                items = d.get('data') or d.get('list') or d.get('video_list') or d.get('items')
            if items is None and isinstance(d, list):
                items = d
            if items is None:
                items = data.get('list') or data.get('data')
            if not items:
                # 深度遍历
                items = self._walk(data)
            if not items:
                continue
            for it in items:
                node = it
                if isinstance(it, dict) and isinstance(it.get('data'), dict):
                    node = it['data']
                v = self._map(node if isinstance(node, dict) else it)
                if v:
                    videos.append(v)
            if videos:
                break
        return videos

    def _search_html(self, key, offset=0):
        videos = []
        q = urllib.parse.quote(key)
        pages = [
            '%s/search/?keyword=%s' % (self.siteUrl, q),
            '%s/search/?keyword=%s&offset=%s' % (self.pcUrl, q, offset),
            '%s/search/?keyword=%s' % (self.pcUrl, q),
        ]
        for url in pages:
            html = self.fetch_text(url, mobile=('m.ixigua' in url))
            if not html or len(html) < 500:
                continue
            videos = self._from_html(html)
            if videos:
                break
        return videos

    def _search(self, key, offset=0):
        videos = self._search_api(key, offset)
        if not videos:
            videos = self._search_html(key, offset)
        return self._dedupe(videos)

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            # 首页推荐
            for url in (self.siteUrl + '/', self.pcUrl + '/'):
                html = self.fetch_text(url, mobile=('m.ixigua' in url))
                videos = self._from_html(html)
                if videos:
                    break
            if not videos:
                videos = self._search('热门', 0)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            info = self.channels.get(str(tid), {'kw': str(tid)})
            kw = info.get('kw') or tid
            videos = self._search(kw, (pg - 1) * 20)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        has_more = len(videos) >= 8
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if has_more else pg,
            'limit': 20,
            'total': 9999 if has_more else len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            videos = self._search(key, (pg - 1) * 20)
        except Exception as e:
            print('搜索失败: %s' % e)
        has_more = len(videos) >= 8
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if has_more else pg,
            'limit': 20,
            'total': len(videos),
        }

    def _detail_page(self, vid):
        candidates = [
            '%s/%s' % (self.pcUrl, vid),
            '%s/video/%s' % (self.siteUrl, vid),
            '%s/%s' % (self.siteUrl, vid),
            '%s/video/%s' % (self.pcUrl, vid),
        ]
        for url in candidates:
            html = self.fetch_text(url, mobile=('m.ixigua' in url))
            if html and len(html) > 800:
                return html, url
        return '', ''

    def _play_from_vid(self, video_id):
        """通过 vxxxx 形式的 video_id 拉取播放地址"""
        if not video_id:
            return ''
        video_id = str(video_id).strip()
        if not video_id.startswith('v'):
            return ''
        r = str(random.randint(100000000, 999999999))
        path = '/video/urls/v/1/toutiao/mp4/%s?r=%s' % (video_id, r)
        s = zlib.crc32(path.encode('utf-8'))
        if s > 0x7FFFFFFF:
            s -= 0x100000000
        for host in self.playHosts:
            try:
                data = self.fetch_json(host + path + '&s=' + str(s), mobile=False)
                vlist = ((data.get('data') or {}).get('video_list')) or {}
                if not vlist and isinstance(data.get('video_list'), dict):
                    vlist = data['video_list']
                # 优先高清
                for key in sorted(vlist.keys(), reverse=True):
                    item = vlist.get(key) or {}
                    enc = item.get('main_url') or item.get('backup_url_1') or item.get('backup_url') or ''
                    if not enc:
                        continue
                    try:
                        best = base64.b64decode(enc).decode('utf-8', 'ignore')
                        if best and best.startswith('http'):
                            return best
                    except Exception:
                        if str(enc).startswith('http'):
                            return enc
            except Exception as e:
                print('play host fail %s: %s' % (host, e))
        return ''

    def _extract_play_id(self, data, html=''):
        text = ''
        try:
            text = json.dumps(data, ensure_ascii=False)
        except Exception:
            pass
        text += '\n' + (html or '')
        for pat in (
            r'"vid"\s*:\s*"(v[0-9a-zA-Z]+)"',
            r'"video_id"\s*:\s*"(v[0-9a-zA-Z]+)"',
            r'"play_vid"\s*:\s*"(v[0-9a-zA-Z]+)"',
            r'video_id=(v[0-9a-zA-Z]+)',
        ):
            m = re.search(pat, text)
            if m:
                return m.group(1)
        return ''

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        name, pic, desc, remarks, actor = vid, '', '', '', ''
        play_id = ''
        try:
            html, page_url = self._detail_page(vid)
            data = self._ssr(html)
            play_id = self._extract_play_id(data, html)
            items = self._walk(data)
            if items:
                first = items[0]
                mapped = self._map(first) or {}
                name = mapped.get('vod_name') or name
                pic = mapped.get('vod_pic') or pic
                remarks = mapped.get('vod_remarks') or remarks
                user = first.get('user_info') or first.get('user') or first.get('author') or {}
                if isinstance(user, dict):
                    actor = user.get('name') or user.get('nickname') or ''
                desc = (
                    first.get('abstract')
                    or first.get('content')
                    or first.get('title')
                    or first.get('desc')
                    or ''
                )
            if not name or name == vid:
                tm = re.search(r'<title>([^<]+)</title>', html or '')
                if tm:
                    name = re.sub(r'\s*[-_|].*$', '', tm.group(1)).strip() or name
            if not play_id:
                play_id = self._extract_play_id({}, html)
        except Exception as e:
            print('获取详情失败: %s' % e)
        play_token = play_id or vid
        return {'list': [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': remarks,
            'vod_actor': actor,
            'vod_content': str(desc).replace('\n\n', '\n').strip(),
            'vod_play_from': '西瓜视频',
            'vod_play_url': '播放$%s' % play_token,
        }]}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.pcUrl + '/',
            'Origin': self.pcUrl,
        }
        play_id = str(id or '')
        if self.isVideoFormat(play_id) and play_id.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play_id, 'header': header}
        url = ''
        try:
            if play_id.startswith('v'):
                url = self._play_from_vid(play_id)
            if not url:
                html, _ = self._detail_page(play_id)
                data = self._ssr(html)
                vid = self._extract_play_id(data, html)
                if vid:
                    url = self._play_from_vid(vid)
                if not url:
                    m3 = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', html or '')
                    if m3:
                        url = m3.group(0).replace('\\/', '/')
        except Exception as e:
            print('获取播放内容失败: %s' % e)
        if url:
            return {'parse': 0, 'jx': '0', 'url': url, 'header': header}
        # 无法直链时回退详情页，交给播放器解析
        page = self.siteUrl + '/video/' + re.sub(r'\D', '', play_id) if re.search(r'\d{10,}', play_id) else (
            self.siteUrl + '/' + play_id
        )
        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    print('--- category movie ---')
    print(json.dumps(spider.categoryContent('movie', 1, {}, {}), ensure_ascii=False)[:600])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pexels 视频
优先官方 API（api.pexels.com，可不带 Key 有限流）
可选 extend 传入 apiKey 提高配额
"""
import json
import re
import sys
import urllib.parse

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
    def __init__(self):
        self.siteUrl = 'https://www.pexels.com'
        self.api = 'https://api.pexels.com/videos'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        self.apiKey = ''
        self.per_page = 24
        self.channels = {
            'videos': {'name': '精选', 'query': ''},
            'nature': {'name': '自然', 'query': 'nature'},
            'city': {'name': '城市', 'query': 'city'},
            'people': {'name': '人物', 'query': 'people'},
            'animals': {'name': '动物', 'query': 'animals'},
            'food': {'name': '美食', 'query': 'food'},
            'travel': {'name': '旅行', 'query': 'travel'},
            'sport': {'name': '运动', 'query': 'sport'},
            'ocean': {'name': '海洋', 'query': 'ocean'},
            'night': {'name': '夜景', 'query': 'night'},
            'tech': {'name': '科技', 'query': 'technology'},
        }

    def getName(self):
        return 'Pexels视频'

    def init(self, extend=""):
        if not extend:
            return
        try:
            if isinstance(extend, str) and extend.strip().startswith('{'):
                ext = json.loads(extend)
                if ext.get('apiKey'):
                    self.apiKey = str(ext['apiKey']).strip()
            elif isinstance(extend, str) and len(extend.strip()) > 16:
                self.apiKey = extend.strip()
        except Exception:
            pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Accept': 'application/json, text/html;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
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

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_text(self, url, params=None):
        resp = self.fetch(url, params=params)
        return getattr(resp, 'text', '') if resp else ''

    def _api(self, path, params=None):
        """调用官方 API；无 Key 也可访问 popular/search（有限流）"""
        headers = {
            'User-Agent': self.userAgent,
            'Accept': 'application/json',
        }
        if self.apiKey:
            headers['Authorization'] = self.apiKey
        resp = self.fetch(self.api + path, headers=headers, params=params)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _parseVideoItem(self, item):
        if not isinstance(item, dict):
            return None
        vid = str(item.get('id') or '')
        if not vid:
            return None
        url = str(item.get('url') or '')
        slug = ''
        m = re.search(r'/video/([^/?]+)', url)
        if m:
            slug = re.sub(r'-\d+$', '', m.group(1)).replace('-', ' ').strip()
        title = slug.title() if slug else ('Pexels #%s' % vid)
        user = ''
        if isinstance(item.get('user'), dict):
            user = item['user'].get('name') or ''
        elif item.get('photographer'):
            user = item.get('photographer')
        duration = item.get('duration') or 0
        pic = item.get('image') or ''
        pics = item.get('video_pictures') or []
        if not pic and pics:
            pic = (pics[0] or {}).get('picture') or ''
        remarks = ''
        if duration:
            remarks = '%ds' % int(duration)
        if user:
            remarks = (remarks + ' · ' + user) if remarks else user
        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_remarks': remarks,
            'vod_actor': user,
        }

    def _walk_videos(self, obj, acc=None):
        if acc is None:
            acc = []
        if isinstance(obj, dict):
            if obj.get('id') and (obj.get('video_files') or obj.get('image')):
                marker = str(obj.get('url') or obj.get('type') or 'video').lower()
                if 'video' in marker or obj.get('video_files'):
                    acc.append(obj)
            for v in obj.values():
                self._walk_videos(v, acc)
        elif isinstance(obj, list):
            for v in obj:
                self._walk_videos(v, acc)
        return acc

    def _from_html(self, path):
        url = path if str(path).startswith('http') else self.siteUrl + path
        html = self.fetch_text(url)
        videos = []
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html or '', re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                seen = set()
                for item in self._walk_videos(data.get('props') or data):
                    v = self._parseVideoItem(item)
                    if v and v['vod_id'] not in seen:
                        seen.add(v['vod_id'])
                        videos.append(v)
            except Exception as e:
                print('解析 NEXT_DATA 失败: %s' % e)
        if videos:
            return videos
        for href, name in re.findall(
            r'href="(https://www\.pexels\.com/[^"]*/video/([^"/]+))"',
            html or '',
        ):
            mid = re.search(r'-(\d+)/?$', href)
            vid = mid.group(1) if mid else name
            title = re.sub(r'-\d+$', '', name).replace('-', ' ').title()
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': '',
                'vod_remarks': '',
            })
        return videos

    def _list(self, query, pg=1):
        pg = int(pg or 1)
        # 1) 官方 API（优先，不强制 Key）
        try:
            if query:
                data = self._api('/search', {
                    'query': query,
                    'page': str(pg),
                    'per_page': str(self.per_page),
                })
            else:
                data = self._api('/popular', {
                    'page': str(pg),
                    'per_page': str(self.per_page),
                })
            items = data.get('videos') or []
            if items:
                videos = []
                for x in items:
                    v = self._parseVideoItem(x)
                    if v:
                        videos.append(v)
                total = int(data.get('total_results') or len(videos))
                pagecount = max(1, (total + self.per_page - 1) // self.per_page)
                # 无 key 时 total 常固定 8000，按有下一页估算
                if data.get('next_page') and pagecount <= pg:
                    pagecount = pg + 1
                return videos, pagecount, total
        except Exception as e:
            print('API 列表失败: %s' % e)

        # 2) HTML 兜底（可能被 Cloudflare 拦截）
        if query:
            path = '/search/videos/%s/' % urllib.parse.quote(query)
        else:
            path = '/videos/'
        if pg > 1:
            path = path.rstrip('/') + '/?page=' + str(pg)
        videos = self._from_html(path)
        return videos, (pg + 1 if len(videos) >= 12 else pg), len(videos)

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        result = {'class': classes}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos = []
        try:
            videos, _, _ = self._list('', 1)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos, pagecount, total = [], pg, 0
        try:
            info = self.channels.get(str(tid), self.channels['videos'])
            videos, pagecount, total = self._list(info.get('query') or '', pg)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': self.per_page,
            'total': total or len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos, pagecount, total = [], pg, 0
        try:
            videos, pagecount, total = self._list(str(key or '').strip(), pg)
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': self.per_page,
            'total': total or len(videos),
        }

    def _best_file(self, item):
        files = item.get('video_files') or []
        mp4s = []
        for f in files:
            if not isinstance(f, dict):
                continue
            link = f.get('link') or ''
            if not link:
                continue
            ft = str(f.get('file_type') or '').lower()
            if 'mp4' not in ft and '.mp4' not in link:
                continue
            mp4s.append((int(f.get('height') or 0), f.get('quality') or '', link))
        mp4s.sort(key=lambda x: x[0], reverse=True)
        return mp4s

    def _fetch_detail(self, vid):
        # 正确详情路径: /videos/videos/{id}
        item = self._api('/videos/' + str(vid)) or {}
        if item.get('id'):
            return item
        # 部分环境路径不同
        item = self._api('/' + str(vid)) or {}
        if item.get('id'):
            return item
        return {}

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        try:
            item = self._fetch_detail(vid)
            if not item.get('id'):
                html = self.fetch_text(self.siteUrl + '/video/' + vid + '/')
                if not html:
                    html = self.fetch_text(self.siteUrl + '/zh-cn/video/' + vid + '/')
                m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html or '', re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        found = self._walk_videos(data)
                        for it in found:
                            if str(it.get('id')) == vid:
                                item = it
                                break
                        if not item and found:
                            item = found[0]
                    except Exception:
                        pass
                if not item.get('video_files'):
                    files = re.findall(r'https://[^"\']+\.mp4[^"\']*', html or '')
                    if files:
                        item = item or {'id': vid}
                        item['video_files'] = [
                            {'link': u.replace('\\/', '/'), 'height': 0} for u in dict.fromkeys(files)
                        ]
            parsed = self._parseVideoItem(item) if item else {
                'vod_id': vid, 'vod_name': 'Pexels #%s' % vid, 'vod_pic': '', 'vod_remarks': ''
            }
            parts = []
            for h, q, link in self._best_file(item or {}):
                label = str(h) + 'p' if h else (q or 'MP4')
                parts.append('%s$%s' % (label, link))
            if not parts:
                parts.append('网页$%s/video/%s/' % (self.siteUrl, vid))
            return {'list': [{
                'vod_id': vid,
                'vod_name': parsed.get('vod_name') or vid,
                'vod_pic': parsed.get('vod_pic') or '',
                'vod_remarks': parsed.get('vod_remarks') or '',
                'vod_actor': parsed.get('vod_actor') or '',
                'vod_content': 'Pexels 免费可商用素材，使用时请保留作者署名。',
                'vod_play_from': 'Pexels',
                'vod_play_url': '#'.join(parts),
            }]}
        except Exception as e:
            print('获取详情失败: %s' % e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
        }
        play_url = str(id or '')
        if self.isVideoFormat(play_url):
            return {'parse': 0, 'jx': '0', 'url': play_url, 'header': header}
        m = re.search(r'(\d{4,})', play_url)
        vid = m.group(1) if m else play_url
        item = self._fetch_detail(vid)
        files = self._best_file(item)
        if files:
            return {'parse': 0, 'jx': '0', 'url': files[0][2], 'header': header}
        html = self.fetch_text(self.siteUrl + '/video/' + vid + '/')
        mp4 = re.search(r'https://[^"\']+\.mp4[^"\']*', html or '')
        if mp4:
            return {'parse': 0, 'jx': '0', 'url': mp4.group(0).replace('\\/', '/'), 'header': header}
        return {
            'parse': 1,
            'jx': '0',
            'url': self.siteUrl + '/video/' + vid + '/',
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.webm', '.mov'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    print('--- category nature ---')
    print(json.dumps(spider.categoryContent('nature', 1, {}, {}), ensure_ascii=False)[:800])

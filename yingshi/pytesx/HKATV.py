#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
亚洲电视 ATV / HKATV
官网: https://www.hkatv.com
内容 API: https://srv-prod.hkatv.vip/c
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
        self.siteUrl = 'https://www.hkatv.com'
        self.api = 'https://srv-prod.hkatv.vip/c'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # categoryId 来自 contentGetCategory
        self.channels = {
            '4': {'name': '微视频'},
            '2': {'name': '推荐'},
            '3': {'name': '微头条'},
            '22': {'name': '资讯'},
            '5': {'name': '香港'},
            '25': {'name': '热榜'},
            '48': {'name': '社团'},
        }

    def getName(self):
        return '亚洲电视 ATV'

    def init(self, extend=""):
        if not extend:
            return
        try:
            if isinstance(extend, str) and extend.startswith('http'):
                self.api = extend.rstrip('/')
            elif isinstance(extend, str) and extend.strip().startswith('{'):
                ext = json.loads(extend)
                if ext.get('api'):
                    self.api = str(ext['api']).rstrip('/')
        except Exception:
            pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Origin': self.siteUrl,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-HK,zh-CN;q=0.9,zh;q=0.8',
            }
        try:
            if requests:
                return requests.get(url, headers=headers, params=params, timeout=15)
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15).read()

            class R:
                def __init__(self, raw):
                    self.text = raw.decode('utf-8', 'ignore')
                    self.status_code = 200

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_json(self, path, params=None):
        url = path if str(path).startswith('http') else self.api + path
        resp = self.fetch(url, params=params)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            text = getattr(resp, 'text', '') or ''
            m = re.search(r'\{[\s\S]+\}', text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return {}
            return {}

    def _abs(self, u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _pick_play(self, item):
        if not isinstance(item, dict):
            return ''
        for k in ('hls1080P', 'hls720P', 'hls480P'):
            u = item.get(k) or ''
            if u and str(u).startswith('http'):
                return str(u)
        content = str(item.get('content') or item.get('sourceUrl') or '')
        if content.startswith('http') and any(x in content for x in ('.mp4', '.m3u8', '.flv')):
            return content.split()[0]
        # resources
        res = item.get('resources')
        if isinstance(res, list):
            for r in res:
                if isinstance(r, dict):
                    u = r.get('url') or r.get('src') or ''
                    if u:
                        return u
                elif isinstance(r, str) and r.startswith('http'):
                    return r
        return ''

    def _map(self, item):
        if not isinstance(item, dict):
            return None
        vid = str(item.get('id') or '')
        if not vid:
            return None
        title = item.get('title') or item.get('name') or vid
        title = re.sub(r'<[^>]+>', '', str(title)).strip()
        if len(title) > 60:
            title = title[:60] + '…'
        pic = (
            item.get('coverUrl')
            or item.get('videoPreviewPic')
            or ''
        )
        remarks = item.get('categoryName') or item.get('duration') or 'ATV'
        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': self._abs(pic),
            'vod_remarks': str(remarks),
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        # 尝试从接口刷新分类名
        try:
            data = self.fetch_json('/content/contentGetCategory')
            items = data.get('data') or []
            if items:
                classes = []
                for c in items:
                    cid = str(c.get('id') or '')
                    name = c.get('name') or cid
                    if not cid or name in ('关注',):
                        continue
                    if c.get('homeShow') in (0, '0'):
                        continue
                    classes.append({'type_id': cid, 'type_name': name})
                    self.channels[cid] = {'name': name}
                if not classes:
                    classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        except Exception:
            pass
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            data = self.fetch_json('/content/contentList', {'page': 1, 'pageSize': 24, 'categoryId': 4})
            for x in (data.get('data') or []):
                v = self._map(x)
                if v:
                    videos.append(v)
            if not videos:
                data = self.fetch_json('/content/contentList', {'page': 1, 'pageSize': 24})
                for x in (data.get('data') or []):
                    v = self._map(x)
                    if v:
                        videos.append(v)
        except Exception as e:
            print('首页失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        total = 0
        try:
            params = {
                'page': pg,
                'pageSize': 24,
                'categoryId': int(tid) if str(tid).isdigit() else 4,
            }
            data = self.fetch_json('/content/contentList', params)
            items = data.get('data') or []
            total = int(data.get('count') or 0)
            for x in items:
                v = self._map(x)
                if v:
                    videos.append(v)
        except Exception as e:
            print('分类失败: %s' % e)
        pagecount = max(1, (total + 23) // 24) if total else (pg + 1 if len(videos) >= 12 else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': total or len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            # 接口若无专用搜索，则用列表关键词过滤 / 多分类拉取
            q = str(key or '').strip()
            for cid in list(self.channels.keys())[:5]:
                data = self.fetch_json('/content/contentList', {
                    'page': pg,
                    'pageSize': 30,
                    'categoryId': int(cid),
                })
                for x in (data.get('data') or []):
                    title = str(x.get('title') or '')
                    if q and q not in title:
                        continue
                    v = self._map(x)
                    if v:
                        videos.append(v)
                if len(videos) >= 24:
                    break
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos[:48],
            'page': pg,
            'pagecount': pg,
            'limit': 24,
            'total': len(videos),
        }

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        try:
            item = self.fetch_json('/content/contentDetail', {'id': vid})
            if not item or not isinstance(item, dict):
                item = {}
            # 若详情无视频，再拉列表项兜底
            if not self._pick_play(item):
                data = self.fetch_json('/content/contentList', {'page': 1, 'pageSize': 50})
                for x in (data.get('data') or []):
                    if str(x.get('id')) == vid:
                        item = x
                        break
            name = re.sub(r'<[^>]+>', '', str(item.get('title') or vid)).strip()
            pic = self._abs(item.get('coverUrl') or item.get('videoPreviewPic') or '')
            desc = item.get('description') or item.get('content') or ''
            if isinstance(desc, str) and desc.startswith('http'):
                desc = name
            desc = re.sub(r'<[^>]+>', '', str(desc)).strip()[:500]
            remarks = item.get('categoryName') or item.get('duration') or 'ATV'

            plays = []
            # 多清晰度
            for label, key in (('1080P', 'hls1080P'), ('720P', 'hls720P'), ('480P', 'hls480P')):
                u = item.get(key) or ''
                if u and str(u).startswith('http'):
                    plays.append('%s$%s' % (label, u))
            direct = self._pick_play(item)
            if direct and not any(direct in p for p in plays):
                plays.insert(0, '播放$%s' % direct)

            if not plays:
                plays = ['页面$%s/zh-CN/video/play?id=%s' % (self.siteUrl, vid)]

            return {'list': [{
                'vod_id': vid,
                'vod_name': name[:80],
                'vod_pic': pic,
                'vod_remarks': str(remarks),
                'vod_actor': '',
                'vod_director': '',
                'vod_content': desc,
                'vod_play_from': 'ATV',
                'vod_play_url': '#'.join(plays),
            }]}
        except Exception as e:
            print('详情失败: %s' % e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '')
        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # id 可能仍是内容 id
        if play.isdigit():
            item = self.fetch_json('/content/contentDetail', {'id': play})
            u = self._pick_play(item or {})
            if u:
                return {'parse': 0, 'jx': '0', 'url': u, 'header': header}

        return {
            'parse': 1,
            'jx': '1',
            'url': play if play.startswith('http') else self.siteUrl + '/zh-CN/video/play?id=' + play,
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd', 'hkatv.vip', 'auth_key='))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    r = spider.categoryContent('4', 1, {}, {})
    print('list', len(r['list']), r['list'][0] if r['list'] else None)
    if r['list']:
        d = spider.detailContent([r['list'][0]['vod_id']])
        print('detail', d['list'][0]['vod_name'][:40], d['list'][0]['vod_play_url'][:100])
        token = d['list'][0]['vod_play_url'].split('#')[0].split('$')[-1]
        print(json.dumps(spider.playerContent('ATV', token, []), ensure_ascii=False)[:220])

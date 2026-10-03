#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 源 - 修复播放
策略：ANDROID/WEB player 直链 → Invidious/Piped → parse=1 官方页
"""
import json
import re
import sys

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://www.youtube.com'
        self.innertube = 'https://www.youtube.com/youtubei/v1'
        self.api_key = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        self.android_key = 'AIzaSyA8eiZmM1FaDVzG9thLM72nEVRaRToynfQ'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        self.android_ua = 'com.google.android.youtube/19.28.35 (Linux; U; Android 13) gzip'
        self.client = {
            'clientName': 'WEB',
            'clientVersion': '2.20240101.00.00',
            'hl': 'zh-CN',
            'gl': 'US',
        }
        self.channels = {
            'trending': {'name': '热门', 'q': 'trending'},
            'movie': {'name': '电影', 'q': '电影 完整版'},
            'tv': {'name': '电视剧', 'q': '电视剧 全集'},
            'music': {'name': '音乐', 'q': '音乐 MV'},
            'game': {'name': '游戏', 'q': '游戏 实况'},
            'news': {'name': '新闻', 'q': '新闻 热点'},
            'sport': {'name': '体育', 'q': '体育 比赛'},
            'tech': {'name': '科技', 'q': '科技 数码'},
            'live': {'name': '直播', 'q': '直播 live'},
            'kids': {'name': '少儿', 'q': '少儿 动画'},
        }
        self.proxy_apis = [
            ('invidious', 'https://inv.nadeko.net'),
            ('invidious', 'https://invidious.nerdvpn.de'),
            ('invidious', 'https://yewtu.be'),
            ('invidious', 'https://invidious.jing.rocks'),
            ('piped', 'https://pipedapi.adminforge.de'),
            ('piped', 'https://pipedapi.kavin.rocks'),
            ('piped', 'https://api.piped.private.coffee'),
        ]

    def getName(self):
        return 'YouTube'

    def init(self, extend=''):
        if not extend:
            return
        try:
            if isinstance(extend, str) and extend.strip().startswith('{'):
                extend = json.loads(extend)
            if isinstance(extend, dict):
                if extend.get('apiKey'):
                    self.api_key = str(extend['apiKey'])
                if extend.get('gl'):
                    self.client['gl'] = str(extend['gl'])
                if extend.get('hl'):
                    self.client['hl'] = str(extend['hl'])
        except Exception:
            pass

    def fetch(self, url, headers=None, method='GET', data=None, timeout=12):
        if requests is None:
            return None
        if headers is None:
            headers = {
                'User-Agent': self.ua,
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': self.host + '/',
            }
        try:
            if method.upper() == 'POST':
                headers = dict(headers)
                headers.setdefault('Content-Type', 'application/json')
                headers.setdefault('Origin', self.host)
                r = requests.post(url, headers=headers, data=json.dumps(data or {}), timeout=timeout)
            else:
                r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code >= 400:
                return None
            return r
        except Exception as e:
            print('fetch fail', url, e)
            return None

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._search_list('trending', 1)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        q = self.channels.get(str(tid), {'q': str(tid)}).get('q', str(tid))
        videos = self._search_list(q, pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 30,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = self._search_list(key, pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 10 else pg,
            'limit': 30,
            'total': len(videos),
        }

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def detailContent(self, ids):
        vid = self._normalize_vid(ids[0] if isinstance(ids, (list, tuple)) else ids)
        name, pic, content, actor = vid, 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % vid, '', ''
        stream_url, meta = self._stream_from_player(vid)
        if meta:
            name = meta.get('title') or name
            content = meta.get('shortDescription') or ''
            actor = meta.get('author') or ''
            th = ((meta.get('thumbnail') or {}).get('thumbnails')) or []
            if th:
                pic = th[-1].get('url') or pic
        play_from, play_url = [], []
        if stream_url:
            play_from.append('直链')
            play_url.append('播放$' + stream_url)
        play_from.append('YouTube')
        play_url.append('播放$' + vid)
        play_from.append('解析')
        play_url.append('播放$' + self.host + '/watch?v=' + vid)
        return {
            'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_content': content,
                'vod_actor': actor,
                'vod_remarks': 'YouTube',
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '')
        hdr = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        if raw.startswith('http') and any(x in raw.lower() for x in ('.m3u8', '.mp4', '.webm', 'googlevideo.com')):
            return {
                'parse': 0,
                'url': raw,
                'header': dict(hdr, **{'User-Agent': self.android_ua}),
            }

        vid = self._normalize_vid(raw)
        url, _ = self._stream_from_player(vid)
        if not url:
            url = self._stream_from_proxy(vid)
        if url:
            return {
                'parse': 0,
                'jx': 0,
                'url': url,
                'header': dict(hdr, **{
                    'User-Agent': self.android_ua,
                    'Referer': self.host + '/watch?v=' + vid,
                }),
            }
        watch = self.host + '/watch?v=' + vid
        return {
            'parse': 1,
            'jx': '1',
            'url': watch,
            'header': hdr,
        }

    def isVideoFormat(self, url):
        if not url or not str(url).startswith('http'):
            return False
        low = str(url).lower()
        return any(x in low for x in ('.mp4', '.m3u8', '.webm', 'googlevideo.com'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    # ---- helpers ----
    def _normalize_vid(self, s):
        s = str(s or '')
        m = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', s) or re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', s) or re.search(r'embed/([a-zA-Z0-9_-]{11})', s)
        if m:
            return m.group(1)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', s):
            return s
        return re.sub(r'[?#].*', '', s.split('/')[-1])

    def _search_list(self, query, pg=1):
        q = str(query or '')
        if int(pg) > 1:
            q = '%s p%s' % (q, pg)
        r = self.fetch(
            self.innertube + '/search?key=' + self.api_key,
            method='POST',
            data={'context': {'client': self.client}, 'query': q},
        )
        if r is None:
            return []
        try:
            data = r.json()
        except Exception:
            return []
        out = []
        self._walk_videos(data, out)
        return self._dedupe(out)

    def _walk_videos(self, obj, out):
        if obj is None:
            return
        if isinstance(obj, list):
            for i in obj:
                self._walk_videos(i, out)
            return
        if not isinstance(obj, dict):
            return
        node = obj.get('videoRenderer') or obj.get('gridVideoRenderer') or obj.get('compactVideoRenderer')
        if node and node.get('videoId'):
            vid = node['videoId']
            name = self._title(node.get('title')) or self._title(node.get('headline')) or vid
            thumbs = ((node.get('thumbnail') or {}).get('thumbnails')) or []
            pic = thumbs[-1].get('url') if thumbs else ('https://i.ytimg.com/vi/%s/hqdefault.jpg' % vid)
            remarks = []
            for key in ('lengthText', 'viewCountText'):
                t = self._title(node.get(key))
                if t:
                    remarks.append(t)
            out.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': ' · '.join(remarks),
            })
            return
        for v in obj.values():
            self._walk_videos(v, out)

    def _title(self, node):
        if not node:
            return ''
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            if node.get('simpleText'):
                return node['simpleText']
            runs = node.get('runs')
            if isinstance(runs, list):
                return ''.join(x.get('text', '') for x in runs)
        return ''

    def _dedupe(self, items):
        seen, res = set(), []
        for it in items:
            vid = it.get('vod_id')
            if not vid or vid in seen:
                continue
            seen.add(vid)
            res.append(it)
        return res

    def _pick_stream(self, sd):
        if not sd:
            return ''
        if sd.get('hlsManifestUrl'):
            return sd['hlsManifestUrl']
        formats = [f for f in (sd.get('formats') or []) if f.get('url')]
        if formats:
            formats.sort(key=lambda f: f.get('height') or f.get('bitrate') or 0, reverse=True)
            return formats[0]['url']
        adaptive = [
            f for f in (sd.get('adaptiveFormats') or [])
            if f.get('url') and 'video' in (f.get('mimeType') or '')
        ]
        if adaptive:
            adaptive.sort(key=lambda f: f.get('height') or f.get('bitrate') or 0, reverse=True)
            return adaptive[0]['url']
        return ''

    def _stream_from_player(self, vid):
        # ANDROID
        try:
            r = self.fetch(
                self.innertube + '/player?key=' + self.android_key,
                method='POST',
                data={
                    'context': {
                        'client': {
                            'clientName': 'ANDROID',
                            'clientVersion': '19.28.35',
                            'androidSdkVersion': 33,
                            'hl': 'zh-CN',
                            'gl': 'US',
                            'userAgent': self.android_ua,
                        }
                    },
                    'videoId': vid,
                    'contentCheckOk': True,
                    'racyCheckOk': True,
                },
                headers={
                    'User-Agent': self.android_ua,
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Format-Version': '2',
                },
                timeout=12,
            )
            if r is not None:
                data = r.json()
                url = self._pick_stream(data.get('streamingData') or {})
                meta = data.get('videoDetails') or {}
                if url:
                    return url, meta
                if meta:
                    # WEB 再试
                    pass
                else:
                    meta = {}
            else:
                meta = {}
        except Exception:
            meta = {}

        try:
            r = self.fetch(
                self.innertube + '/player?key=' + self.api_key,
                method='POST',
                data={
                    'context': {'client': self.client},
                    'videoId': vid,
                    'contentCheckOk': True,
                    'racyCheckOk': True,
                },
                timeout=12,
            )
            if r is not None:
                data = r.json()
                url = self._pick_stream(data.get('streamingData') or {})
                meta = data.get('videoDetails') or meta
                return url, meta
        except Exception:
            pass
        return '', meta if isinstance(meta, dict) else {}

    def _stream_from_proxy(self, vid):
        for typ, base in self.proxy_apis:
            try:
                if typ == 'invidious':
                    r = self.fetch(base + '/api/v1/videos/' + vid, timeout=10)
                    if r is None:
                        continue
                    data = r.json()
                    if data.get('hlsUrl'):
                        return data['hlsUrl']
                    fmts = data.get('formatStreams') or []
                    if fmts:
                        return fmts[-1].get('url') or ''
                else:
                    r = self.fetch(base + '/streams/' + vid, timeout=10)
                    if r is None:
                        continue
                    data = r.json()
                    if data.get('hls'):
                        return data['hls']
                    vs = data.get('videoStreams') or []
                    with_audio = [v for v in vs if not v.get('videoOnly') and v.get('url')]
                    pool = with_audio or [v for v in vs if v.get('url')]
                    if pool:
                        pool.sort(key=lambda x: x.get('height') or 0, reverse=True)
                        return pool[0]['url']
            except Exception:
                continue
        return ''


if __name__ == '__main__':
    sp = Spider()
    print(json.dumps(sp.homeContent(True), ensure_ascii=False)[:200])
    cat = sp.categoryContent('music', 1, {}, {})
    print('music', len(cat.get('list') or []))
    if cat.get('list'):
        vid = cat['list'][0]['vod_id']
        print('vid', vid, cat['list'][0]['vod_name'][:40])
        p = sp.playerContent('YouTube', vid, [])
        print('play parse', p.get('parse'), 'url', (p.get('url') or '')[:100])

# -*- coding: utf-8 -*-
"""
养生 / 北京BTV 栏目 (btime.com)
- 列表: pc.api.btime.com/btimeweb/infoFlow
- 播放: app.api.btime.com/video/play?id=
参考 爱看机器人.py 结构
"""
import sys
import re
import json
import time
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


LIST_API = 'https://pc.api.btime.com/btimeweb/infoFlow'
PLAY_API = 'https://app.api.btime.com/video/play'
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
HEADERS = {
    'User-Agent': UA,
    'Referer': 'https://www.btime.com/',
    'Accept': 'application/json, text/plain, */*',
}

CLASS_NAMES = [
    '北京news', '法治进行时', '养生堂', '暖暖的味道', '档案', '生命缘',
    '我是大医生', '为你喝彩', '向前一步', '科普中国直击最前沿', '天下财经', '七色光日播版',
]
CLASS_URLS = [
    'btv_983ba33ce3932fcdf206f0d5bf7cfce1',
    'btv_c3a9e0f80bc7de951583f00b81f363dc',
    'btv_08da67cea600bf3c78973427bfaba12d',
    'btv_92f0d4ecfca32b5ef804924c979665f3',
    'btv_b0dbe496b5671f33b955ca684f407c39',
    'btv_67074b2d5504351caf217d48dc7fea01',
    'btv_06ed423197a0ef0cab055a475b8e3b4b',
    'btv_478e6ff2a2793844cf15819bd5051b67',
    'btv_d968bb6d0e9955d7cf8efe6fcc7b511f',
    'btv_49259afbd8fe430d521ea679b55d0e01',
    'btv_e43595fd6af4fa2d717eae86255fbb92',
    'btv_0faa0e4ea571ce2c979981c20921f239',
]


class Spider(Spider):

    def init(self, extend=''):
        self.headers = dict(HEADERS)

    def getName(self):
        return '养生BTV'

    def isVideoFormat(self, url):
        return any(x in str(url) for x in ['.m3u8', '.mp4', '.flv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _get(self, url):
        r = self.fetch(url, headers=self.headers)
        return r.text if hasattr(r, 'text') else str(r)

    def _get_json(self, url):
        try:
            return json.loads(self._get(url))
        except Exception:
            return {}

    def homeContent(self, filter=False):
        classes = []
        filters = {}
        years = [{'n': str(y), 'v': str(y)} for y in range(2026, 2018, -1)]
        for name, tid in zip(CLASS_NAMES, CLASS_URLS):
            classes.append({'type_id': tid, 'type_name': name})
            filters[tid] = [{'name': '年份', 'key': 'year', 'value': years}]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        try:
            tid = CLASS_URLS[2]  # 养生堂
            return {'list': self._fetch_list(tid, '2025', 1)[:20]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        pg = max(int(str(pg) or 1), 1)
        extend = extend or {}
        year = str(extend.get('year') or '2025')
        try:
            items = self._fetch_list(tid, year, pg)
            return {
                'list': items,
                'page': pg,
                'pagecount': pg + 1 if len(items) >= 15 else pg,
                'limit': 20,
                'total': 9999,
            }
        except Exception as e:
            print('category', e)
            return {'list': [], 'page': pg, 'pagecount': 0}

    def detailContent(self, ids):
        raw = str(ids[0]) if ids else ''
        gid, title = self._unpack(raw)
        return {'list': [{
            'vod_id': raw,
            'vod_name': title or gid,
            'vod_pic': '',
            'vod_remarks': '北京BTV',
            'vod_content': '请勿相信视频内任何广告',
            'vod_play_from': '北京BTV',
            'vod_play_url': f'{title or "播放"}${gid}',
        }]}

    def searchContent(self, key, quick=False, pg=1):
        return {'list': [], 'page': int(pg or 1)}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            gid = str(id or '').split('~')[0]
            data = self._get_json(f'{PLAY_API}?id={quote(gid)}')
            streams = (data.get('data') or {}).get('video_stream') or []
            multi = (data.get('data') or {}).get('video_streams') or []
            url = ''
            if streams and isinstance(streams, list) and streams[0].get('stream_url'):
                url = streams[0]['stream_url']
            if not url and multi:
                first = multi[0]
                if isinstance(first, dict) and first.get('stream_url'):
                    url = first['stream_url']
                elif isinstance(first, list) and first and first[0].get('stream_url'):
                    url = first[0]['stream_url']
            if not url:
                return {'parse': 1, 'url': gid, 'header': self.headers}
            return {
                'parse': 0, 'jx': 0, 'url': url,
                'header': {'User-Agent': UA, 'Referer': 'https://www.btime.com/'},
            }
        except Exception as e:
            print('play', e)
            return {'parse': 1, 'url': str(id), 'header': self.headers}

    def _fetch_list(self, tid, year, pg):
        list_id = f'{tid}_s0_{year}'
        url = f'{LIST_API}?list_id={quote(list_id)}&refresh={pg}&count=20&expands=pageinfo&_={int(time.time()*1000)}'
        data = self._get_json(url)
        arr = ((data.get('data') or {}).get('list')) or []
        items = []
        for it in arr:
            d = it.get('data') or {}
            covers = d.get('covers') or []
            title = d.get('title') or ''
            gid = it.get('gid') or ''
            items.append({
                'vod_id': self._pack(gid, title),
                'vod_name': title,
                'vod_pic': covers[0] if covers else '',
                'vod_remarks': d.get('pdate_ymd') or '',
            })
        return items

    def _pack(self, gid, title):
        return f"{gid}~{str(title or '').replace('~', ' ')}"

    def _unpack(self, raw):
        s = str(raw or '')
        i = s.find('~')
        if i < 0:
            return s, s
        return s[:i], s[i + 1:]

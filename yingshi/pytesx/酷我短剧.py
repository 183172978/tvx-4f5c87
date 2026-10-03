# -*- coding: utf-8 -*-
"""
酷我短剧 (kuwo_open)
对应 kuwo_open.js；风格对齐 大师兄影视.py
API: http://wapi.kuwo.cn/openapi/v1/shortplay
播放: nmobi.kuwo.cn get_url_by_vid → 直出 mp4
"""
import json
import re
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
    HOST = 'http://wapi.kuwo.cn'
    PLAY_HOST = 'http://nmobi.kuwo.cn'
    UA = (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 '
        'Mobile/15E148 Safari/604.1'
    )

    # moduleId 分类（与原 JS 一致 10-16）
    CLASSES = [
        {'type_id': '10', 'type_name': '热门短剧'},
        {'type_id': '11', 'type_name': '都市情感'},
        {'type_id': '12', 'type_name': '逆袭爽剧'},
        {'type_id': '13', 'type_name': '甜宠爱情'},
        {'type_id': '14', 'type_name': '古装穿越'},
        {'type_id': '15', 'type_name': '战神霸总'},
        {'type_id': '16', 'type_name': '更多精选'},
    ]

    def init(self, extend=''):
        self.header = {
            'User-Agent': self.UA,
            'Accept': '*/*',
            'Referer': 'http://www.kuwo.cn/',
        }

    def getName(self):
        return '酷我短剧'

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv'))

    def _get(self, url):
        try:
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.header)
                with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.header, timeout=12)
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _json(self, text):
        try:
            return json.loads(text) if text else None
        except Exception:
            return None

    def homeContent(self, filter=False):
        return {'class': list(self.CLASSES), 'filters': {}}

    def homeVideoContent(self):
        return self.categoryContent('10', 1, False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        mid = str(tid or '10')
        url = (
            '%s/openapi/v1/shortplay/moduleMore?currentPage=%s&moduleId=%s&rn=12'
            % (self.HOST, pg, mid)
        )
        data = self._json(self._get(url))
        items = []
        pagecount = 1
        if data:
            body = data.get('data') or data
            raw = body.get('list') if isinstance(body, dict) else []
            pagecount = int((body or {}).get('pages') or 1)
            for it in (raw or []):
                aid = str(it.get('url') or it.get('albumId') or '')
                if not aid and it.get('routeData'):
                    try:
                        rd = it['routeData']
                        if isinstance(rd, str):
                            rd = json.loads(rd)
                        aid = str((rd.get('params') or {}).get('albumId') or '')
                    except Exception:
                        pass
                if not aid:
                    continue
                items.append({
                    'vod_id': aid,
                    'vod_name': it.get('title') or '',
                    'vod_pic': it.get('img') or '',
                    'vod_remarks': it.get('currrentDesc') or it.get('subTitle') or '',
                })
        return {
            'list': items,
            'page': pg,
            'pagecount': pagecount,
            'limit': 12,
            'total': pagecount * 12,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        album_id = str(raw).strip()
        if not album_id:
            return {'list': []}
        url = '%s/openapi/v1/shortplay/videoList?albumId=%s' % (self.HOST, album_id)
        data = self._json(self._get(url))
        if not data:
            return {'list': []}
        body = data.get('data') or data
        shortinfo = body.get('shortinfo') if isinstance(body, dict) else {}
        if not isinstance(shortinfo, dict):
            shortinfo = {}
        eps = body.get('list') if isinstance(body, dict) else []
        name = shortinfo.get('title') or shortinfo.get('name') or ('短剧' + album_id)
        pic = shortinfo.get('img') or shortinfo.get('cover') or ''
        remarks = shortinfo.get('currrentDesc') or ''
        content = shortinfo.get('description') or shortinfo.get('subTitle') or ''

        parts = []
        for i, ep in enumerate(eps or []):
            ep_name = ep.get('name') or ('第%d集' % (i + 1))
            # 播放用 mvpayinfo.vid
            mp = ep.get('mvpayinfo') or {}
            vid = mp.get('vid') or ep.get('vid') or ep.get('id')
            if not vid:
                continue
            parts.append('%s$%s' % (ep_name, vid))

        return {
            'list': [{
                'vod_id': album_id,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_content': content,
                'vod_play_from': '酷我短剧',
                'vod_play_url': '#'.join(parts),
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        # 原 JS 搜索能力有限：遍历分类简单匹配标题
        pg = int(pg or 1)
        key = str(key or '').strip().lower()
        if not key:
            return {'list': []}
        result = []
        for c in self.CLASSES:
            data = self.categoryContent(c['type_id'], 1, False, {})
            for it in data.get('list') or []:
                if key in (it.get('vod_name') or '').lower():
                    result.append(it)
        return {'list': result, 'page': pg, 'pagecount': 1}

    def playerContent(self, flag, id, vipFlags=None):
        vid = str(id or '').strip()
        if '$' in vid:
            vid = vid.split('$')[-1].strip()
        header = {
            'User-Agent': self.UA,
            'Referer': 'http://www.kuwo.cn/',
        }
        if not vid:
            return {'parse': 0, 'url': '', 'header': header}
        # 已是直链
        if vid.startswith('http') and self.isVideoFormat(vid):
            return {'parse': 0, 'url': vid, 'header': header}

        url = '%s/mobi.s?f=web&type=get_url_by_vid&vid=%s' % (self.PLAY_HOST, vid)
        text = self._get(url)
        play = ''
        if text:
            m = re.search(r'url=(https?://[^\s\r\n]+)', text)
            if m:
                play = m.group(1).strip()
            if not play:
                for line in text.replace('\r', '\n').split('\n'):
                    line = line.strip()
                    if line.startswith('url='):
                        play = line[4:].strip()
                        break
        if play:
            return {'parse': 0, 'url': play, 'header': header}
        return {'parse': 0, 'url': '', 'header': header}

    def localProxy(self, param):
        return None

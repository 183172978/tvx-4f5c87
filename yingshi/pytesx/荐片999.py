# -*- coding: utf-8 -*-
"""
荐片999
对应 荐片999.js；风格对齐 大师兄影视.py
API: https://api.ztcgi.com
播放: 直链 m3u8/mp4 或 tvbox-xg: 协议
"""
import base64
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
    HOST = 'https://api.ztcgi.com'
    UA = (
        'Mozilla/5.0 (Linux; Android 9; V2196A Build/PQ3A.190705.08211809; wv) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 '
        'Mobile Safari/537.36;webank/h5face;webank/1.0;netType:NETWORK_WIFI;'
        'appVersion:416;packageName:com.jp3.xg3'
    )

    CLASSES = [
        {'type_id': '1', 'type_name': '电影'},
        {'type_id': '2', 'type_name': '电视剧'},
        {'type_id': '3', 'type_name': '动漫'},
        {'type_id': '4', 'type_name': '综艺'},
    ]

    FILTER_ITEM = [
        {
            'key': 'cateId',
            'name': '分类',
            'value': [
                {'v': '1', 'n': '剧情'}, {'v': '2', 'n': '爱情'}, {'v': '3', 'n': '动画'},
                {'v': '4', 'n': '喜剧'}, {'v': '5', 'n': '战争'}, {'v': '6', 'n': '歌舞'},
                {'v': '7', 'n': '古装'}, {'v': '8', 'n': '奇幻'}, {'v': '9', 'n': '冒险'},
                {'v': '10', 'n': '动作'}, {'v': '11', 'n': '科幻'}, {'v': '12', 'n': '悬疑'},
                {'v': '13', 'n': '犯罪'}, {'v': '14', 'n': '家庭'}, {'v': '15', 'n': '传记'},
                {'v': '16', 'n': '运动'}, {'v': '18', 'n': '惊悚'}, {'v': '20', 'n': '短片'},
                {'v': '21', 'n': '历史'}, {'v': '22', 'n': '音乐'}, {'v': '23', 'n': '西部'},
                {'v': '24', 'n': '武侠'}, {'v': '25', 'n': '恐怖'},
            ],
        },
        {
            'key': 'area',
            'name': '地区',
            'value': [
                {'v': '1', 'n': '国产'}, {'v': '3', 'n': '中国香港'}, {'v': '6', 'n': '中国台湾'},
                {'v': '5', 'n': '美国'}, {'v': '18', 'n': '韩国'}, {'v': '2', 'n': '日本'},
            ],
        },
        {
            'key': 'year',
            'name': '年代',
            'value': [
                {'v': '107', 'n': '2025'}, {'v': '119', 'n': '2024'}, {'v': '153', 'n': '2023'},
                {'v': '101', 'n': '2022'}, {'v': '118', 'n': '2021'}, {'v': '16', 'n': '2020'},
                {'v': '7', 'n': '2019'}, {'v': '22', 'n': '2016'}, {'v': '2015', 'n': '2015以前'},
            ],
        },
        {
            'key': 'sort',
            'name': '排序',
            'value': [
                {'v': 'update', 'n': '最新'},
                {'v': 'hot', 'n': '最热'},
                {'v': 'rating', 'n': '评分'},
            ],
        },
    ]

    def init(self, extend=''):
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
        self.header = {
            'User-Agent': self.UA,
            'Accept': '*/*',
            'Referer': self.HOST,
        }
        self.imghost = 'https://img.jianpian.com'
        try:
            text = self._get('%s/api/appAuthConfig' % self.HOST)
            j = self._json(text)
            if j and j.get('data') and j['data'].get('imgDomain'):
                self.imghost = 'https://%s' % j['data']['imgDomain']
        except Exception:
            pass

    def getName(self):
        return '荐片999'

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.m3u8', '.mp4', '.flv', '.mkv'))

    def _get(self, url):
        try:
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.header)
                with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.header, timeout=15, verify=False)
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _json(self, text):
        try:
            return json.loads(text) if text else None
        except Exception:
            return None

    def _pic(self, path):
        if not path:
            return ''
        path = str(path).strip()
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return 'https:' + path
        return self.imghost + path

    @staticmethod
    def _b64e(s):
        return base64.b64encode(str(s or '').encode('utf-8')).decode('ascii')

    @staticmethod
    def _b64d(s):
        try:
            return base64.b64decode(str(s or '')).decode('utf-8')
        except Exception:
            return ''

    def homeContent(self, filter=False):
        filters = {c['type_id']: self.FILTER_ITEM for c in self.CLASSES}
        return {'class': list(self.CLASSES), 'filters': filters}

    def homeVideoContent(self):
        text = self._get('%s/api/slide/list?pos_id=88' % self.HOST)
        j = self._json(text)
        items = []
        if j and j.get('data'):
            for it in j['data']:
                items.append({
                    'vod_id': it.get('jump_id'),
                    'vod_name': it.get('title') or '',
                    'vod_pic': self._pic(it.get('thumbnail')),
                    'vod_remarks': '',
                })
        return {'list': items}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        ext = extend or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}
        url = (
            '%s/api/crumb/list?fcate_pid=%s&category_id=&area=%s&year=%s'
            '&type=%s&sort=%s&page=%s'
            % (
                self.HOST,
                tid,
                ext.get('area') or '',
                ext.get('year') or '',
                ext.get('cateId') or '',
                ext.get('sort') or '',
                pg,
            )
        )
        j = self._json(self._get(url))
        items = []
        if j and j.get('data'):
            for it in j['data']:
                items.append({
                    'vod_id': it.get('id'),
                    'vod_name': it.get('title') or '',
                    'vod_pic': self._pic(it.get('path')),
                    'vod_remarks': it.get('mask') or '',
                })
        return {
            'list': items,
            'page': pg,
            'pagecount': 99,
            'limit': 20,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        kw = quote(str(key or '').strip())
        if not kw:
            return {'list': []}
        url = (
            '%s/api/v2/search/videoV2?key=%s&category_id=88&page=%s&pageSize=20'
            % (self.HOST, kw, pg)
        )
        j = self._json(self._get(url))
        items = []
        if j and j.get('data'):
            for it in j['data']:
                items.append({
                    'vod_id': it.get('id'),
                    'vod_name': it.get('title') or '',
                    'vod_pic': self._pic(it.get('thumbnail')),
                    'vod_remarks': it.get('mask') or '',
                })
        return {'list': items, 'page': pg, 'pagecount': 10}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        vod_id = str(raw).strip()
        if not vod_id:
            return {'list': []}
        j = self._json(self._get('%s/api/video/detailv2?id=%s' % (self.HOST, vod_id)))
        if not j or not j.get('data'):
            return {'list': []}
        data = j['data']
        play_from = []
        play_url = []
        sources = data.get('source_list_source') or []
        for src in sources:
            name = str(src.get('name') or '线路').replace('常规线路', '边下边播')
            eps = []
            for ep in (src.get('source_list') or []):
                ep_name = ep.get('source_name') or '播放'
                ep_url = ep.get('url') or ''
                if not ep_url:
                    continue
                # 详情存 base64，播放时解码（与 JS 一致）
                eps.append('%s$%s' % (ep_name, self._b64e(ep_url)))
            if eps:
                play_from.append(name)
                play_url.append('#'.join(eps))

        return {
            'list': [{
                'vod_id': data.get('id') or vod_id,
                'vod_name': data.get('title') or '',
                'vod_pic': self._pic(data.get('thumbnail')),
                'vod_year': data.get('year') or '',
                'vod_area': data.get('area') or '',
                'vod_remarks': data.get('mask') or '',
                'vod_content': data.get('description') or '',
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        real = self._b64d(id)
        if not real:
            real = str(id or '')
        header = {
            'User-Agent': self.UA,
            'Referer': self.HOST,
        }
        if not real:
            return {'parse': 1, 'url': '', 'header': header}
        play = real
        if '.m3u8' not in real and '.mp4' not in real:
            play = 'tvbox-xg:' + real
        return {
            'parse': 0,
            'url': play,
            'header': header,
        }

    def localProxy(self, param):
        return None

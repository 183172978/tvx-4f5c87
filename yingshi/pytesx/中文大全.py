# -*- coding: utf-8 -*-
# 中文大全 https://kklwqis10.jvlookzw04.cn/index
# API: https://zdap.gkquu.cn:4438/zd  (AES 加密响应)
# 模板参考: 91成人短剧.py
import re
import json
import sys
import time
import random
import hashlib
import base64
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

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad as _unpad
        HAS_CRYPTO = 'pycryptodome'
    except ImportError:
        pass


class Spider(BaseSpider):
    AES_KEY = b'mh_aes=19@#$@%@#'
    AES_IV = b'5e1y6w452uqw9jq8'
    SIGN_SALT = '@1243asd31**21#'

    def __init__(self):
        self.web = 'https://kklwqis10.jvlookzw04.cn'
        self.api = 'https://zdap.gkquu.cn:4438/zd'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        )
        self.guid = 'web' + ''.join(random.choice('0123456789abcdef') for _ in range(16))
        self.channels = {
            'day': {'name': '热门推荐', 'path': '/sp/getDayLovelyList', 'extra': {}},
            'short': {'name': '短视频', 'path': '/sp/getShortVideoData', 'extra': {}},
            'p10': {'name': '类型1', 'path': '/sp/getLovelyList', 'extra': {'plateId': 10}},
            'p11': {'name': '类型2', 'path': '/sp/getLovelyList', 'extra': {'plateId': 11}},
            'p12': {'name': '类型3', 'path': '/sp/getLovelyList', 'extra': {'plateId': 12}},
            'p13': {'name': '类型4', 'path': '/sp/getLovelyList', 'extra': {'plateId': 13}},
            'p15': {'name': '网红专区', 'path': '/sp/getLovelyList', 'extra': {'plateId': 15}},
            'p17': {'name': '绅士专区', 'path': '/sp/getLovelyList', 'extra': {'plateId': 17}},
        }

    def getName(self):
        return '中文大全'

    def init(self, extend=""):
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else {}
                if conf.get('web'):
                    self.web = conf['web'].rstrip('/')
                if conf.get('api'):
                    self.api = conf['api'].rstrip('/')
                if conf.get('host'):
                    self.web = conf['host'].rstrip('/')
            except Exception:
                pass

    def _nonce(self, n=32):
        chars = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'
        return ''.join(random.choice(chars) for _ in range(n))

    def _decrypt(self, b64_data):
        if not b64_data:
            return ''
        try:
            raw = base64.b64decode(b64_data)
            if HAS_CRYPTO is True:
                cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV))
                dec = cipher.decryptor()
                data = dec.update(raw) + dec.finalize()
                unpadder = PKCS7(128).unpadder()
                return (unpadder.update(data) + unpadder.finalize()).decode('utf-8')
            if HAS_CRYPTO == 'pycryptodome':
                cipher = AES.new(self.AES_KEY, AES.MODE_CBC, self.AES_IV)
                return _unpad(cipher.decrypt(raw), 16).decode('utf-8')
        except Exception as e:
            print('AES decrypt error', e)
        return ''

    def _api_get(self, path, params=None):
        params = dict(params or {})
        ts = str(int(time.time() * 1000))
        nonce = self._nonce()
        sign = hashlib.md5((ts + self.guid + nonce + self.SIGN_SALT).encode()).hexdigest().upper()
        headers = {
            'User-Agent': self.ua,
            'Content-Type': 'application/x-www-form-urlencoded',
            'token': self.guid,
            'sign': sign,
            'timestamp': ts,
            'nonce': nonce,
            'url': path,
            'Referer': self.web + '/',
            'Origin': self.web,
        }
        url = self.api + path
        try:
            if requests is None:
                import urllib.request
                import urllib.parse
                q = urllib.parse.urlencode(params)
                full = url + ('?' + q if q else '')
                req = urllib.request.Request(full, headers=headers)
                with urllib.request.urlopen(req, timeout=18) as resp:
                    text = resp.read().decode('utf-8', 'ignore')
            else:
                r = requests.get(url, headers=headers, params=params, timeout=18, verify=False)
                text = r.text if r.status_code == 200 else ''
            if not text:
                return {}
            j = json.loads(text)
            if j.get('returnData'):
                plain = self._decrypt(j['returnData'])
                if plain:
                    return json.loads(plain)
            return j
        except Exception as e:
            print('API error', path, e)
            return {}

    def _map_videos(self, data):
        out = []
        arr = (data or {}).get('videoList') or []
        for it in arr:
            play = it.get('videoUrlOne') or it.get('videoUrlTwo') or it.get('videoUrlThree') or ''
            pic = it.get('videoCover') or ''
            if pic.startswith('//'):
                pic = 'https:' + pic
            title = it.get('videoTitle') or it.get('videoDes') or str(it.get('videoId') or '')
            out.append({
                'vod_id': play or str(it.get('videoId') or ''),
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': it.get('videoTag') or it.get('duration') or '',
            })
        return out

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        data = self._api_get('/sp/getDayLovelyList', {'pageNo': 1, 'pageSize': 24, 'videoId': ''})
        return {'list': self._map_videos(data)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'day')
        info = self.channels.get(tid) or self.channels['day']
        params = {'pageNo': pg, 'pageSize': 25, 'videoId': ''}
        params.update(info.get('extra') or {})
        data = self._api_get(info['path'], params)
        videos = self._map_videos(data)
        pagecount = pg + 1 if len(videos) >= 15 else pg
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 25,
            'total': 9999,
        }

    def detailContent(self, ids):
        result = {'list': []}
        if not ids:
            return result
        raw = str(ids[0])
        # vod_id 可能直接是 m3u8
        if re.search(r'\.(m3u8|mp4)(\?|$)', raw, re.I):
            play = raw
            name = '视频'
        else:
            play = raw
            name = '视频'
        # 多线路：用 | 分隔
        plays = []
        for i, u in enumerate(raw.split('|')):
            u = u.strip()
            if u and re.search(r'\.(m3u8|mp4)(\?|$)', u, re.I):
                plays.append(('线路%d' % (i + 1), u))
        if not plays and play:
            plays = [('播放', play)]
        play_url = '#'.join(['%s$%s' % (n, u) for n, u in plays])
        vod = {
            'vod_id': raw,
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': '中文大全',
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
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 25, 'total': 0}
        data = self._api_get('/sp/getSearchList', {
            'searchName': key,
            'pageNo': pg,
            'pageSize': 25,
            'plateId': 10,
            'videoId': '',
        })
        videos = self._map_videos(data)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 15 else pg,
            'limit': 25,
            'total': len(videos),
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.ua,
            'Referer': self.web + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(m3u8|mp4)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}
        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

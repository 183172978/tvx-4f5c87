#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优视频 UVOD  https://www.uvod.tv
API: https://api-h5.uvod.tv  (RSA+AES 混合加密，响应需解密)
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding as apadding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass

# 前端 chunk-common 内置密钥（与站点一致）
_CLIENT_PRIVATE = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAJ4FBai1Y6my4+fc
8AD5tyYzxgN8Q7M/PuFv+8i1Xje8ElXYVwzvYd1y/cNxwgW4RX0tDy9ya562V33x
6SyNr29DU6XytOeOlOkxt3gd5169K4iFaJ0l0wA4koMTcCAYVxC9B4+zzS5djYmF
MuRGfYgKYNH99vfY7BZjdAY68ty5AgMBAAECgYB1rbvHJj5wVF7Rf4Hk2BMDCi9+
zP4F8SW88Y6KrDbcPt1QvOonIea56jb9ZCxf4hkt3W6foRBwg86oZo2FtoZcpCJ+
rFqUM2/wyV4CuzlL0+rNNSq7bga7d7UVld4hQYOCffSMifyF5rCFNH1py/4Dvswm
pi5qljf+dPLSlxXl2QJBAMzPJ/QPAwcf5K5nngQtbZCD3nqDFpRixXH4aUAIZcDz
S1RNsHrT61mEwZ/thQC2BUJTQNpGOfgh5Ecd1MnURwsCQQDFhAFfmvK7svkygoKX
t55ARNZy9nmme0StMOfdb4Q2UdJjfw8+zQNtKFOM7VhB7ijHcfFuGsE7UeXBe20n
g/XLAkEAv9SoT2hgJaQxxUk4MCF8pgddstJlq8Z3uTA7JMa4x+kZfXTm/6TOo6I8
2VbXZLsYYe8op0lvsoHMFvBSBljV0QJBAKhxyoYRa98dZB5qZRskciaXTlge0WJk
kA4vvh3/o757izRlQMgrKTfng1GVfIZFqKtnBiIDWTXQw2N9cnqXtH8CQAx+CD5t
l1iT0cMdjvlMg2two3SnpOjpo7gALgumIDHAmsUWhocLtcrnJI032VQSUkNnLq9z
EIfmHDz0TPVNHBQ=
-----END PRIVATE KEY-----"""

_SERVER_PUBLIC = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCeBQWotWOpsuPn3PAA+bcmM8YD
fEOzPz7hb/vItV43vBJV2FcM72Hdcv3DccIFuEV9LQ8vcmuetld98eksja9vQ1Ol
8rTnjpTpMbd4HedevSuIhWidJdMAOJKDE3AgGFcQvQePs80uXY2JhTLkRn2ICmDR
/fb32OwWY3QGOvLcuQIDAQAB
-----END PUBLIC KEY-----"""

_AES_IV = b'abcdefghijklmnop'

_QUALITY_NAME = {1: '标清', 2: '高清', 3: '超清', 4: '蓝光', 5: '4K'}


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://www.uvod.tv'
        self.api = 'https://api-h5.uvod.tv'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # parent_category_id
        self.channels = {
            '100': {'name': '电影'},
            '101': {'name': '电视剧'},
            '102': {'name': '综艺'},
            '103': {'name': '动漫'},
            '104': {'name': '体育'},
            '105': {'name': '纪录片'},
            '106': {'name': '午夜'},
        }
        self._priv = None
        self._pub = None
        if HAS_CRYPTO:
            self._priv = serialization.load_pem_private_key(
                _CLIENT_PRIVATE.encode(), password=None, backend=default_backend()
            )
            self._pub = serialization.load_pem_public_key(
                _SERVER_PUBLIC.encode(), backend=default_backend()
            )

    def getName(self):
        return '优视频 UVOD'

    def init(self, extend=""):
        pass

    # ---------- crypto ----------
    def _aes_encrypt(self, data, key):
        cipher = Cipher(algorithms.AES(key), modes.CBC(_AES_IV), backend=default_backend())
        enc = cipher.encryptor()
        pad_len = 16 - (len(data) % 16)
        data = data + bytes([pad_len] * pad_len)
        return base64.b64encode(enc.update(data) + enc.finalize()).decode()

    def _aes_decrypt(self, b64, key):
        raw = base64.b64decode(b64)
        cipher = Cipher(algorithms.AES(key), modes.CBC(_AES_IV), backend=default_backend())
        dec = cipher.decryptor()
        out = dec.update(raw) + dec.finalize()
        return out[: -out[-1]].decode('utf-8', 'ignore')

    def _encrypt_body(self, obj):
        key = (''.join(chr(65 + (b % 26)) for b in os.urandom(16))).encode()
        plain = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode()
        aes_part = self._aes_encrypt(plain, key)
        rsa_part = base64.b64encode(
            self._pub.encrypt(key, apadding.PKCS1v15())
        ).decode()
        return aes_part + '.' + rsa_part

    def _decrypt_body(self, text):
        a, b = str(text).split('.', 1)
        key = self._priv.decrypt(base64.b64decode(b), apadding.PKCS1v15())
        return self._aes_decrypt(a, key)

    def _sign(self, token, query, ts):
        return hashlib.md5(('%s-%s-%s' % (token, query, ts)).encode()).hexdigest()

    def _filter_ksort(self, body):
        e = {}
        for k, v in (body or {}).items():
            if v in (0, '0', '', False, None):
                continue
            e[k] = v
        return {k: e[k] for k in sorted(e.keys())}

    def api_post(self, path, body=None):
        if not HAS_CRYPTO:
            print('缺少 cryptography 库，无法调用 UVOD 加密接口')
            return {}
        body = body or {}
        e = self._filter_ksort(body)
        ts = int(time.time() * 1000)
        query = urllib.parse.urlencode(e, doseq=True).lower()
        sig = self._sign('', query, ts)
        headers = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
            'Content-Type': 'application/json',
            'X-TOKEN': '',
            'X-TIMESTAMP': str(ts),
            'X-SIGNATURE': sig,
        }
        url = self.api + path
        try:
            if requests:
                resp = requests.post(
                    url, data=self._encrypt_body(body), headers=headers, timeout=15
                )
                text = resp.text
            else:
                from urllib.request import Request, urlopen
                req = Request(url, data=self._encrypt_body(body).encode(), headers=headers)
                text = urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
            plain = self._decrypt_body(text)
            return json.loads(plain)
        except Exception as ex:
            print('api_post 失败 %s: %s' % (path, ex))
            return {}

    def _map_video(self, item):
        if not isinstance(item, dict):
            return None
        vid = str(item.get('id') or item.get('video_id') or '')
        if not vid:
            return None
        return {
            'vod_id': vid,
            'vod_name': item.get('title') or item.get('name') or vid,
            'vod_pic': item.get('pic') or item.get('cover') or '',
            'vod_remarks': str(
                item.get('state')
                or item.get('remark')
                or item.get('last_fragment_symbol')
                or ''
            ),
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            data = self.api_post('/video/latest', {'page': 1, 'pageSize': 24})
            items = ((data.get('data') or {}).get('video_latest_list')) or []
            if not items:
                items = ((data.get('data') or {}).get('video_list')) or []
            for x in items:
                v = self._map_video(x)
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
            body = {
                'page': pg,
                'pageSize': 24,
                'parent_category_id': int(tid) if str(tid).isdigit() else 100,
            }
            data = self.api_post('/video/list', body)
            d = data.get('data') or {}
            items = d.get('video_list') or []
            total = int(d.get('video_total') or 0)
            for x in items:
                v = self._map_video(x)
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
            data = self.api_post('/search', {
                'page': pg,
                'pageSize': 24,
                'keyword': str(key or ''),
            })
            d = data.get('data') or {}
            items = d.get('video_list') or d.get('list') or []
            if isinstance(d, list):
                items = d
            for x in items:
                v = self._map_video(x)
                if v:
                    videos.append(v)
            if not videos:
                data = self.api_post('/video/keyword', {
                    'page': pg,
                    'pageSize': 24,
                    'keyword': str(key or ''),
                })
                items = ((data.get('data') or {}).get('video_list')) or []
                for x in items:
                    v = self._map_video(x)
                    if v:
                        videos.append(v)
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        try:
            data = self.api_post('/video/info', {'id': int(vid) if vid.isdigit() else vid})
            root = data.get('data') or {}
            info = root.get('video') or root
            frags = root.get('video_fragment_list') or []
            name = info.get('title') or vid
            pic = info.get('pic') or ''
            content = info.get('description') or ''
            remarks = info.get('state') or info.get('remark') or ''
            actor = info.get('starring') or ''
            director = info.get('director') or ''
            year = str(info.get('year') or '')

            # 选集：symbol 为集数，qualities 为清晰度列表
            # 播放 id 编码:  videoId|fragmentId|quality
            if not frags:
                frags = [{'id': 0, 'symbol': '1', 'qualities': [3, 4]}]

            qset = []
            for f in frags:
                for q in (f.get('qualities') or [3]):
                    if q not in qset:
                        qset.append(q)
            qset = sorted(qset)

            play_from, play_urls = [], []
            for q in qset:
                label = _QUALITY_NAME.get(int(q), 'Q%s' % q)
                parts = []
                for f in frags:
                    if q not in (f.get('qualities') or [q]):
                        continue
                    ep = str(f.get('symbol') or f.get('id') or '1')
                    token = '%s|%s|%s' % (vid, f.get('id'), q)
                    parts.append('%s$%s' % (ep, token))
                if parts:
                    play_from.append(label)
                    play_urls.append('#'.join(parts))

            if not play_urls:
                play_from = ['UVOD']
                play_urls = ['1$%s|0|3' % vid]

            return {'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_year': year,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': str(content).strip(),
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls),
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
        if play.startswith('http') and self.isVideoFormat(play):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # videoId|fragmentId|quality
        parts = play.split('|')
        if len(parts) >= 2:
            video_id = parts[0]
            frag_id = parts[1]
            quality = int(parts[2]) if len(parts) > 2 and str(parts[2]).isdigit() else 3
            try:
                data = self.api_post('/video/source', {
                    'video_id': int(video_id) if str(video_id).isdigit() else video_id,
                    'video_fragment_id': int(frag_id) if str(frag_id).isdigit() else frag_id,
                    'quality': quality,
                })
                src = ((data.get('data') or {}).get('video_soruce') or
                       (data.get('data') or {}).get('video_source') or {})
                url = src.get('url') or ''
                if url:
                    return {'parse': 0, 'jx': '0', 'url': url, 'header': header}
                # 尝试其它清晰度
                for q in (4, 3, 2, 1):
                    if q == quality:
                        continue
                    data = self.api_post('/video/source', {
                        'video_id': int(video_id) if str(video_id).isdigit() else video_id,
                        'video_fragment_id': int(frag_id) if str(frag_id).isdigit() else frag_id,
                        'quality': q,
                    })
                    src = ((data.get('data') or {}).get('video_soruce') or {})
                    url = src.get('url') or ''
                    if url:
                        return {'parse': 0, 'jx': '0', 'url': url, 'header': header}
            except Exception as e:
                print('播放失败: %s' % e)

        return {
            'parse': 1,
            'jx': '1',
            'url': self.siteUrl + '/play?video_id=' + play.split('|')[0],
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd', 'oledsa.com'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    r = spider.categoryContent('100', 1, {}, {})
    print('list', len(r['list']), r['list'][0] if r['list'] else None)
    if r['list']:
        d = spider.detailContent([r['list'][0]['vod_id']])
        print('detail', d['list'][0]['vod_name'], d['list'][0]['vod_play_from'])
        token = d['list'][0]['vod_play_url'].split('#')[0].split('$')[-1]
        print(json.dumps(spider.playerContent('超清', token, []), ensure_ascii=False)[:250])

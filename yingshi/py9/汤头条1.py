# TBR 视频源（加密 API）
# 网站: https://dpi4.tbrapi.org

# coding=utf-8
# !/usr/bin/python

import sys
sys.path.append('..')

from base.spider import BaseSpider
import requests
from urllib.parse import quote
import json
import base64
import hashlib
import re
import os
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

TIMEOUT = 10
try:
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tbr_error.log')
except Exception:
    LOG_FILE = os.path.join(os.getcwd(), 'tbr_error.log')


class Spider(BaseSpider):
    def getName(self):
        return "TBR"

    filterable = False
    searchable = True
    host = 'https://dpi4.tbrapi.org'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    _aes_key = '7205a6c3883caf95b52db5b534e12ec3'
    _aes_iv = '81d7beac44a86f43'
    _sign_key = '7205a6c3883caf95b52db5b534e12ec3'
    _img_key = 'f5d965df75336270'
    _img_iv = '97b60394abc2fbe1'

    _system_params = {
        'system_oauth_type': 'pwa',
        'system_oauth_id': 'egzmJgnUCTYIlCxD_1722416055782',
        'system_oauth_new_id': '',
        'system_version': '3.0.1',
        'system_token': '',
        'system_app_type': '',
        'system_build': '',
        'system_build_id': '',
    }

    def init(self, extend=""):
        print("============{0}============".format(extend))
        print("[TBR] log file: {}".format(LOG_FILE))

    def _log(self, msg):
        line = "[{}] {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            pass
        print(msg)

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def _aes_encrypt(self, plaintext):
        cipher = AES.new(self._aes_key.encode('utf-8'), AES.MODE_CFB, self._aes_iv.encode('utf-8'), segment_size=128)
        encrypted = cipher.encrypt(plaintext.encode('utf-8'))
        return encrypted.hex().upper()

    def _aes_decrypt(self, ciphertext):
        cipher = AES.new(self._aes_key.encode('utf-8'), AES.MODE_CFB, self._aes_iv.encode('utf-8'), segment_size=128)
        decrypted = cipher.decrypt(bytes.fromhex(ciphertext))
        try:
            return decrypted.decode('utf-8')
        except UnicodeDecodeError:
            return decrypted.decode('latin-1')

    def _generate_sign(self, data, timestamp):
        s = 'client=pwa&data=' + data + '&timestamp=' + str(timestamp) + self._sign_key
        sha256_hex = hashlib.sha256(s.encode()).hexdigest()
        return hashlib.md5(sha256_hex.encode()).hexdigest()

    def _api_request(self, endpoint, params):
        data = dict(self._system_params)
        data.update(params)
        data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

        encrypted_data = self._aes_encrypt(data_json)
        timestamp = int(datetime.now().timestamp())
        sign = self._generate_sign(encrypted_data, timestamp)

        body = {
            'client': 'pwa',
            'timestamp': timestamp,
            'data': encrypted_data,
            'sign': sign,
        }

        url = self.host + endpoint
        try:
            r = requests.post(url, data=body, headers=self.headers, timeout=TIMEOUT, verify=False)
            r.raise_for_status()
            resp = r.json()
            if 'data' not in resp or not resp['data']:
                return None
            decrypted = self._aes_decrypt(resp['data'])
            return json.loads(decrypted)
        except Exception as e:
            self._log('[api] 请求失败: {} {}'.format(endpoint, e))
            return None

    def _decrypt_image_url(self, encrypted_url):
        if not encrypted_url:
            return ''

        if encrypted_url.startswith('http'):
            img_url = encrypted_url
        elif encrypted_url.startswith('{') and '"ori"' in encrypted_url:
            # 新格式: JSON 对象 {"ori":"https:\/\/...", "360":"...", "720":"..."}
            try:
                img_info = json.loads(encrypted_url)
                img_url = img_info.get('ori', '')
                if not img_url:
                    img_url = img_info.get('720', img_info.get('360', encrypted_url))
                if not img_url.startswith('http'):
                    self._log('[img] JSON格式解析后非http: {}'.format(str(img_info)[:100]))
                    return encrypted_url
            except Exception as e:
                self._log('[img] JSON解析失败: {}'.format(e))
                return encrypted_url
        elif encrypted_url.isalnum():
            try:
                cipher = AES.new(self._img_key.encode('utf-8'), AES.MODE_CBC, self._img_iv.encode('utf-8'))
                decrypted = cipher.decrypt(bytes.fromhex(encrypted_url))
                img_url = decrypted.rstrip(b'\x00').decode('utf-8')
            except Exception as e:
                self._log('[img] URL解密失败: {}'.format(e))
                return encrypted_url
        else:
            return encrypted_url

        if not img_url.startswith('http'):
            return encrypted_url

        img_url_b64 = base64.b64encode(img_url.encode('utf-8')).decode('utf-8')
        base_proxy = self.getProxyUrl()
        if not base_proxy:
            base_proxy = 'http://127.0.0.1:9980/proxy?do=py'
        if '?' in base_proxy:
            return base_proxy + '&type=tbr_img&url=' + quote(img_url_b64, safe='')
        else:
            return base_proxy + '?type=tbr_img&url=' + quote(img_url_b64, safe='')

    def _process_play_url(self, url):
        # 原始 preview_video URL 直接可用，不再做域名替换
        # 仅清理无用的 seconds 参数
        url = url.replace('&seconds=30', '')
        return url

    def homeContent(self, filter):
        result = {}
        class_names = '推荐&制片厂&最新&经典三级&经典电影&国产&动漫CG&欧美&日韩&小视频&合集&分类'.split('&')
        class_ids = 'recommend&factory&newest&classic&classic_movie&domestic&anime&western&asian&smallvideo&compilation&categories'.split('&')
        classes = []
        for i in range(len(class_names)):
            classes.append({
                'type_name': class_names[i],
                'type_id': class_ids[i]
            })
        result['class'] = classes
        result['type'] = '视频'
        return result

    def homeVideoContent(self):
        api_result = self._api_request('/pwa.php/api/MvList/recommend', {'page': '1', '_t': '1'})
        video_list = []
        if api_result and 'data' in api_result:
            data = api_result['data']
            if isinstance(data, dict) and data.get('list'):
                items = data['list']
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for item in items:
                video_list.append({
                    'vod_id': item.get('preview_video', ''),
                    'vod_name': item.get('title', ''),
                    'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                    'vod_remarks': item.get('duration_str', ''),
                })
        return {'list': video_list}

    def categoryContent(self, tid, pg, filter, extend):
        video_list = []

        if tid == 'categories':
            result = self._api_request('/pwa.php/api/MvSearch/getStyle', {})
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    categories = data['list']
                elif isinstance(data, list):
                    categories = data
                else:
                    categories = []
                for category in categories:
                    if category.get('child'):
                        for sub in category['child']:
                            video_list.append({
                                'vod_id': 'style:' + str(sub.get('id', '')),
                                'vod_name': sub.get('name', ''),
                                'vod_pic': '',
                                'vod_remarks': '',
                                'vod_tag': 'folder',
                            })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid.startswith('style:'):
            style_id = tid.replace('style:', '')
            result = self._api_request('/pwa.php/api/MvList/style', {
                'page': str(pg),
                'size': '15',
                'id': style_id,
                'orderBy': 'id',
            })
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid.startswith('creator:'):
            uuid = tid.replace('creator:', '')
            p0 = (pg - 1) * 50
            result = self._api_request('/pwa.php/api/Creator/featured', {
                'size': '15',
                'uuid': uuid,
                'lastId': str(p0),
            })
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid == 'smallvideo':
            tag = extend.get('tag', 'recommend') if isinstance(extend, dict) else 'recommend'
            result = self._api_request('/pwa.php/api/MvList/smallVideoByTag', {
                'page': str(pg),
                'tag': tag,
            })
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid == 'featured_long':
            result = self._api_request('/pwa.php/api/topic/feature', {'page': str(pg)})
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid == 'featured_small':
            result = self._api_request('/pwa.php/api/topic/small', {'page': str(pg)})
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid == 'compilation':
            result = self._api_request('/pwa.php/api/compilation/list', {
                'page': str(pg),
                'sort': 'new',
            })
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': 'compilation:' + str(item.get('id', '')),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('image', '')),
                        'vod_remarks': item.get('date', ''),
                        'vod_tag': 'folder',
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        if tid.startswith('compilation:'):
            compilation_id = tid.replace('compilation:', '')
            result = self._api_request('/pwa.php/api/compilation/mvlist', {
                'limit': '10',
                'id': compilation_id,
                'page': str(pg),
            })
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data.get('list'):
                    items = data['list']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                for item in items:
                    video_list.append({
                        'vod_id': item.get('preview_video', ''),
                        'vod_name': item.get('title', ''),
                        'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                        'vod_remarks': item.get('duration_str', ''),
                    })
            return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

        tab_id_map = {
            'recommend': '1',
            'factory': '2',
            'newest': '10',
            'classic': '5',
            'classic_movie': '6',
            'domestic': '4',
            'anime': '12',
            'western': '2',
            'asian': '1',
        }
        tab_id = tab_id_map.get(tid, '1')

        if tid == 'recommend':
            result = self._api_request('/pwa.php/api/MvList/recommend', {
                'page': str(pg),
                '_t': '1',
            })
        elif tid == 'factory':
            result = self._api_request('/pwa.php/api/MvList/featuredzpc', {
                'page': str(pg),
                '_t': '1',
            })
        else:
            result = self._api_request('/pwa.php/api/MvList/featured', {
                'page': str(pg),
                'tabId': tab_id,
            })

        if result and 'data' in result:
            data = result['data']
            if isinstance(data, dict) and data.get('list'):
                items = data['list']
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for item in items:
                video_list.append({
                    'vod_id': item.get('preview_video', ''),
                    'vod_name': item.get('title', ''),
                    'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                    'vod_remarks': item.get('duration_str', ''),
                })

        return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 15, 'total': 99999}

    def detailContent(self, ids):
        play_url = ids[0]
        final_url = self._process_play_url(play_url)

        vod = {
            'vod_id': play_url,
            'vod_name': '视频',
            'vod_pic': '',
            'vod_content': '',
            'vod_play_from': '播放',
            'vod_play_url': '播放$' + final_url,
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg=1):
        result = self._api_request('/pwa.php/api/MvSearch/video', {
            'page': str(pg),
            'size': '15',
            'keyword': key,
        })

        video_list = []
        if result and 'data' in result:
            data = result['data']
            if isinstance(data, dict) and data.get('list'):
                items = data['list']
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for item in items:
                video_list.append({
                    'vod_id': item.get('preview_video', ''),
                    'vod_name': item.get('title', ''),
                    'vod_pic': self._decrypt_image_url(item.get('thumb_cover_str', '')),
                    'vod_remarks': item.get('duration_str', ''),
                })

        return {'list': video_list, 'page': pg, 'pagecount': 9999, 'limit': 24, 'total': 99999}

    def playerContent(self, flag, id, vipFlags=None):
        return {
            'parse': 0,
            'playUrl': '',
            'url': id,
            'header': json.dumps({
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.host + '/',
            }),
        }

    def localProxy(self, params):
        try:
            if params.get('type') != 'tbr_img':
                return [404, 'text/plain', 'not found']

            img_url_b64 = params.get('url', '')
            if not img_url_b64:
                return [400, 'text/plain', 'missing url']

            from urllib.parse import unquote
            img_url_b64 = unquote(img_url_b64)
            padding = 4 - len(img_url_b64) % 4
            if padding != 4:
                img_url_b64 += '=' * padding

            img_url = base64.b64decode(img_url_b64).decode('utf-8')

            img_headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'Referer': self.host + '/',
            }

            r = requests.get(img_url, headers=img_headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200:
                self._log('[proxy] 图片下载失败: HTTP {}'.format(r.status_code))
                return [404, 'text/plain', 'image not found']

            encrypted_data = r.content

            header = encrypted_data[:10]
            if header[:3] == b'\xff\xd8\xff':
                return [200, 'image/jpeg', encrypted_data, {'Content-Length': str(len(encrypted_data))}]
            elif header[:4] == b'\x89PNG':
                return [200, 'image/png', encrypted_data, {'Content-Length': str(len(encrypted_data))}]

            cipher = AES.new(self._img_key.encode('utf-8'), AES.MODE_CBC, self._img_iv.encode('utf-8'))
            try:
                decrypted = cipher.decrypt(encrypted_data)
                decrypted = decrypted.rstrip(b'\x00')
            except Exception as e:
                self._log('[proxy] 解密失败: {}'.format(e))
                return [500, 'text/plain', 'decryption failed']

            if not decrypted:
                self._log('[proxy] 解密后为空')
                return [500, 'text/plain', 'decryption failed']

            if decrypted[:3] == b'\xff\xd8\xff':
                return [200, 'image/jpeg', decrypted, {'Content-Length': str(len(decrypted))}]
            elif decrypted[:4] == b'\x89PNG':
                return [200, 'image/png', decrypted, {'Content-Length': str(len(decrypted))}]
            elif len(decrypted) > 12 and decrypted[:4] == b'RIFF' and decrypted[8:12] == b'WEBP':
                return [200, 'image/webp', decrypted, {'Content-Length': str(len(decrypted))}]

            dec_header = decrypted[:10].decode('ascii', errors='ignore')
            if dec_header[:4] == '/9j/' or dec_header[:4] == 'iVBOR' or dec_header[:4] == 'UklGR':
                try:
                    final_img = base64.b64decode(decrypted)
                    if final_img[:3] == b'\xff\xd8\xff':
                        return [200, 'image/jpeg', final_img, {'Content-Length': str(len(final_img))}]
                    elif final_img[:4] == b'\x89PNG':
                        return [200, 'image/png', final_img, {'Content-Length': str(len(final_img))}]
                    elif len(final_img) > 12 and final_img[:4] == b'RIFF' and final_img[8:12] == b'WEBP':
                        return [200, 'image/webp', final_img, {'Content-Length': str(len(final_img))}]
                except Exception:
                    pass

            self._log('[proxy] 未知图片格式')
            return [200, 'image/jpeg', decrypted, {'Content-Length': str(len(decrypted))}]

        except Exception as e:
            self._log('[proxy] 错误: {}'.format(e))
            return [500, 'text/plain', str(e)]

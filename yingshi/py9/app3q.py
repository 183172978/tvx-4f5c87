# -*- coding: utf-8 -*-
"""
 {
    "key": "布布[PY-3Q][模板]",
    "name": "布布[PY-3Q][模板]",
    "type": 3,
    "api": "./py/app/app3q.py",
    "searchable": 1,
    "quickSearch": 1,
    "filterable": 1,
    "ext": "https://bubutv.top/" //https://asd123sx23xdacsx.top/
},
"""
import json
import re
import sys
import time
import random
import secrets
import hashlib
import urllib3
from base.spider import Spider  # 假设基类提供 fetch, getCache, setCache 等方法

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')


class Spider(Spider):
    """自定义爬虫，对接 3qys 影视 API"""

    def __init__(self):
        super().__init__()
        self.host = ''
        self.device_id = self._load_or_generate_device_id()

    def init(self, extend=''):
        """
        初始化主机地址
        extend: 可以是完整 URL 或包含 host 的 JSON 字符串
        """
        ext = extend.strip()
        if not ext:
            self.host = 'https://asd123sx23xdacsx.top/'
            return

        try:
            if ext.startswith('http'):
                host = ext
            else:
                arr = json.loads(ext)
                host = arr['host']
            self.host = host.rstrip('/') + '/'   # 保证末尾有斜杠
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            # 若解析失败，置空并记录日志（可根据需要替换为 print）
            self.host = 'https://asd123sx23xdacsx.top/'
            print(f"[init] 解析失败: {e}")

    def _load_or_generate_device_id(self):
        """从缓存加载或生成新的 device_id，长度为 16 位十六进制"""
        cache_key = 'com.sunshine.tv_3qys_B7k7Dt56Rn'
        cached = self.getCache(cache_key)
        if isinstance(cached, str) and len(cached) == 16:
            return cached
        new_id = ''.join(secrets.choice('0123456789abcdef') for _ in range(16))
        self.setCache(cache_key, new_id)
        return new_id

    def headers(self):
        """生成请求头，包含签名和设备信息"""
        timestamp = str(int(time.time()))
        nonce = ''.join(random.choice('0123456789') for _ in range(3))
        ver, pkg = '3', 'com.sunshine.tv'

        sign_str = (
            f"finger=SF-C3B2B41F6EFFFF9869176CF68F6790E8F07506FC88632C94B4F5F0430D5498CA"
            f"&id={pkg}&nonce={nonce}&sk=SK-thanks&time={timestamp}&v={ver}"
        )
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest().upper()

        return {
            'User-Agent': 'okhttp/4.12.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'x-aid': pkg,
            'x-ave': ver,
            'x-time': timestamp,
            'x-nonc': nonce,
            'x-sign': sign,
            'x-device-id': self.device_id,
            'x-device-brand': 'vivo',
            'x-device-model': 'V2309A',
            'x-update-id': '0245861b-2ebf-5524-389d-f983830651ec'
        }

    def _safe_fetch_json(self, url, **kwargs):
        """安全地获取 JSON 响应，出错时返回空字典"""
        try:
            resp = self.fetch(url, headers=self.headers(), verify=False, **kwargs)
            return resp.json()
        except Exception as e:
            print(f"[fetch] 请求失败: {url} - {e}")
            return {}

    def arr2vods(self, arr):
        """转换 API 返回的视频列表为统一格式"""
        videos = []
        if not isinstance(arr, list):
            return videos
        for i in arr:
            if not isinstance(i, dict):
                continue
            type_name = i.get('type_name', '')
            vod_class = i.get('vod_class', '')
            if vod_class:
                type_name = f"{type_name},{vod_class}"
            videos.append({
                'vod_id': i.get('vod_id', ''),
                'vod_name': i.get('vod_name', ''),
                'vod_pic': i.get('vod_pic', ''),
                'vod_remarks': i.get('vod_remarks', ''),
                'type_name': type_name,
                'vod_year': i.get('vod_year', '')
            })
        return videos

    def homeContent(self, filter):
        """首页内容：分类和推荐视频"""
        if not self.host:
            return None
        data = self._safe_fetch_json(f'{self.host}/api.php/app/index/home')
        categories = data.get('data', {}).get('categories', [])
        videos, classes = [], []
        for cat in categories:
            if not isinstance(cat, dict):
                continue
            type_name = cat.get('type_name', '')
            if type_name:
                classes.append({'type_id': type_name, 'type_name': type_name})
            videos.extend(self.arr2vods(cat.get('videos', [])))
        return {'class': classes, 'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        """分类列表（带分页）"""
        if not self.host:
            return {}
        limit = 15
        url = f'{self.host}/api.php/app/filter/vod?type_name={tid}&page={pg}&sort=hits&limit={limit}'
        data = self._safe_fetch_json(url)
        videos = self.arr2vods(data.get('data', []))
        page = int(pg)
        # 根据返回条数判断是否有下一页（接口返回的 total 不可靠）
        pagecount = page + 1 if len(videos) == limit else page
        return {
            'page': page,
            'pagecount': pagecount,
            'limit': limit,
            'total': pagecount * limit,
            'list': videos
        }

    def searchContent(self, key, quick, pg='1'):
        """搜索"""
        if not self.host:
            return {}
        limit = 15
        url = f'{self.host}/api.php/app/search/index?wd={key}&page={pg}&limit={limit}'
        data = self._safe_fetch_json(url)
        videos = self.arr2vods(data.get('data', []))
        page = int(pg)
        pagecount = page + 1 if len(videos) == limit else page
        return {
            'page': page,
            'pagecount': pagecount,
            'limit': limit,
            'total': pagecount * limit,
            'list': videos
        }

    def detailContent(self, ids):
        """视频详情和播放源"""
        if not self.host or not ids:
            return {'list': []}
        vod_id = ids[0]
        url = f'{self.host}/api.php/app/vod/get_detail?vod_id={vod_id}'
        data = self._safe_fetch_json(url)
        detail_list = data.get('data', [])
        if not detail_list:
            return {'list': []}
        detail = detail_list[0]
        if not isinstance(detail, dict):
            return {'list': []}

        shows, play_urls = [], []
        raw_shows = detail.get('vod_play_from', '').split('$$$')
        raw_urls_list = detail.get('vod_play_url', '').split('$$$')

        # 获取播放器配置（用于解码标识）
        player_configs = data.get('vodplayer', [])
        # 构建配置映射，便于快速查找
        config_map = {cfg.get('from'): cfg for cfg in player_configs if isinstance(cfg, dict)}

        for show_code, urls_str in zip(raw_shows, raw_urls_list):
            if not show_code or not urls_str:
                continue
            need_parse = 0
            is_show = 0
            name = show_code
            # 查找对应的播放器配置
            if show_code in config_map:
                cfg = config_map[show_code]
                is_show = 1
                need_parse = cfg.get('decode_status', 0)
                # 如果 show 字段存在且与 from 不同，则展示更友好的名称
                if cfg.get('show') and cfg['show'].casefold() != show_code.casefold():
                    name = f"{cfg['show']}\u2005({show_code})"

            if is_show == 1:
                episodes = []
                for url_item in urls_str.split('#'):
                    if '$' in url_item:
                        episode, url = url_item.split('$', 1)
                        # 拼接编码: 源名称@是否需要解析@真实URL
                        episodes.append(f"{episode}${show_code}@{need_parse}@{url}")
                if episodes:
                    play_urls.append('#'.join(episodes))
                    shows.append(name)

        video = {
            'vod_id': detail.get('vod_id', ''),
            'vod_name': detail.get('vod_name', ''),
            'vod_pic': detail.get('vod_pic', ''),
            'vod_remarks': detail.get('vod_remarks', ''),
            'vod_year': detail.get('vod_year', ''),
            'vod_area': detail.get('vod_area', ''),
            'vod_actor': detail.get('vod_actor', ''),
            'vod_director': detail.get('vod_director', ''),
            'vod_content': detail.get('vod_content', ''),
            'vod_play_from': '$$$'.join(shows),
            'vod_play_url': '$$$'.join(play_urls),
            'type_name': detail.get('vod_class', '')
        }
        return {'list': [video]}

    def playerContent(self, flag, vid, vip_flags):
        """获取播放地址，支持解析接口"""
        if not self.host:
            return {'jx': 0, 'parse': 0, 'url': '', 'header': {}}
        # vid 格式: play_from@need_parse@url
        parts = vid.split('@', 2)
        if len(parts) < 3:
            return {'jx': 0, 'parse': 0, 'url': vid, 'header': {}}
        play_from, need_parse, raw_url = parts
        jx, url = 0, ''
        if need_parse == '1':
            try:
                decode_url = f'{self.host}/api.php/app/decode/url/?url={raw_url}&vodFrom={play_from}'
                resp = self.fetch(decode_url, headers=self.headers(), timeout=30, verify=False)
                data = resp.json()
                play_url = data.get('data', '')
                if play_url.startswith('http'):
                    url = play_url
            except Exception:
                pass
        if not url:
            url = raw_url
            # 判断是否为主流视频站，需要跳转
            if re.search(r'(?:www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com', raw_url):
                jx = 1
        return {
            'jx': jx,
            'parse': 0,
            'url': url,
            'header': {'User-Agent': 'com.sunshine.tv/1.2.0 (Linux;Android 15) AndroidXMedia3/1.4.1'}
        }

    # ---------- 以下为框架可能要求实现但本爬虫用不到的方法，保留空实现 ----------
    def homeVideoContent(self):
        pass

    def getName(self):
        return "3qys影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
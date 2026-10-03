#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯视频 Spider
兼容 TVBox / OK影视 / 影视仓 等
播放方式与爱奇艺一致：非直链走解析站 (parse=1, jx=1)
"""
from bs4 import BeautifulSoup
import urllib.parse
import requests
import json
import time
import re
import sys

sys.path.append('../../')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=""):
            pass

class Spider(Spider):
    def __init__(self):
        self.siteUrl = 'https://v.qq.com'
        self.searchApi = 'https://pbaccess.video.qq.com/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch'
        self.nodeApi = 'https://node.video.qq.com'
        self.episodeApi = 'https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData'
        # 使用移动端 UA，提升 OK影视 等兼容性（与爱奇艺一致）
        self.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        
        self.channels = {
            '1': {'name': '电影', 'keyword': '电影'},
            '2': {'name': '电视剧', 'keyword': '电视剧'},
            '3': {'name': '动漫', 'keyword': '动漫'},
            '4': {'name': '综艺', 'keyword': '综艺'},
            '5': {'name': '纪录片', 'keyword': '纪录片'},
            '6': {'name': '少儿', 'keyword': '少儿动画'},
            '7': {'name': '游戏', 'keyword': '游戏'},
        }
        
        self.filters = {
            "1": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "更早", "v": "2021"}
                ]}
            ],
            "2": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "更早", "v": "2022"}
                ]}
            ],
            "3": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "更早", "v": "2023"}
                ]}
            ],
            "4": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "更早", "v": "2024"}
                ]}
            ],
            "5": [],
            "6": [],
            "7": []
        }

    def getName(self):
        return "腾讯视频"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        result = {}
        classes = []
        for k, v in self.channels.items():
            classes.append({
                'type_id': str(k),
                'type_name': v['name']
            })
        result['class'] = classes
        if filter:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        result = {'list': []}
        try:
            videos = []
            for kw in ['热播电视剧', '热门电影', '热门动漫', '热门综艺']:
                items = self._search_api(kw, page=0, pagesize=8)
                for it in items:
                    if it.get('vod_id') and it.get('vod_name'):
                        videos.append(it)
                if len(videos) >= 24:
                    break
            result['list'] = videos[:24]
        except Exception as e:
            print(f"获取首页视频失败: {e}")
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {
            'list': [],
            'page': int(pg) if pg else 1,
            'pagecount': 1,
            'limit': 30,
            'total': 0
        }
        try:
            tid = str(tid)
            channel_info = self.channels.get(tid, {})
            keyword = channel_info.get('keyword') or channel_info.get('name') or '电影'
            # 支持筛选年份追加到搜索词
            if extend and isinstance(extend, dict):
                year = extend.get('year') or ''
                if year:
                    keyword = f"{keyword} {year}"
            page = max(int(pg) - 1, 0) if pg else 0
            videos = self._search_api(keyword, page=page, pagesize=30)
            # 简单过滤：尽量保留带封面的正片
            videos = [v for v in videos if v.get('vod_id') and v.get('vod_name')]
            result['list'] = videos
            result['page'] = int(pg) if pg else 1
            result['pagecount'] = (int(pg) + 1) if len(videos) >= 15 else (int(pg) if pg else 1)
            result['limit'] = 30
            result['total'] = len(videos) * (int(pg) if pg else 1)
        except Exception as e:
            print(f"获取分类内容失败: {e}")
        return result

    def _search_api(self, key, page=0, pagesize=20):
        videos = []
        try:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': 'https://v.qq.com/',
                'Origin': 'https://v.qq.com',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            params = {'vversion_platform': '2'}
            payload = {
                'version': '25020601',
                'clientType': 1,
                'filterValue': '',
                'uuid': '',
                'query': str(key),
                'retry': 0,
                'pagenum': int(page),
                'isPrefetch': False,
                'pagesize': int(pagesize),
                'queryFrom': 0,
                'searchDatakey': '',
                'searchFilterValue': '',
            }
            r = requests.post(self.searchApi, params=params, json=payload, headers=headers, timeout=12)
            r.raise_for_status()
            data = r.json()
            items = (data.get('data') or {}).get('normalList', {}).get('itemList') or []
            for it in items:
                try:
                    doc = it.get('doc') or {}
                    vi = it.get('videoInfo') or {}
                    vid = str(doc.get('id') or '').strip()
                    title = (vi.get('title') or '').replace('<em>', '').replace('</em>', '').strip()
                    if not vid or not title:
                        continue
                    pic = vi.get('imgUrl') or ''
                    if pic.startswith('//'):
                        pic = 'https:' + pic
                    year = str(vi.get('year') or '')
                    type_name = vi.get('typeName') or ''
                    remarks = f"{type_name} {year}".strip()
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remarks
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"搜索接口失败: {e}")
        return videos

    def detailContent(self, ids):
        result = {'list': []}
        try:
            if not ids:
                return result
            video_id = str(ids[0])
            cid = video_id.split('_')[0] if '_' in video_id else video_id
            
            album_name = ''
            album_pic = ''
            album_desc = ''
            actors = []
            directors = []
            episodes = []
            
            headers = {
                'User-Agent': self.userAgent,
                'Referer': 'https://v.qq.com/',
                'Accept': 'application/json, text/plain, */*',
            }
            
            # 1. 基础信息
            try:
                info_url = f'{self.nodeApi}/x/api/float_vinfo2'
                r = requests.get(info_url, params={'cid': cid}, headers=headers, timeout=10)
                if r.status_code == 200:
                    text = r.text.strip()
                    if '(' in text[:30]:
                        m = re.search(r'\((\{.*\})\)\s*;?\s*$', text, re.DOTALL)
                        if m:
                            text = m.group(1)
                    data = json.loads(text)
                    c = data.get('c') or data.get('data') or {}
                    if isinstance(c, dict):
                        album_name = c.get('title') or c.get('name') or ''
                        album_desc = c.get('description') or c.get('desc') or ''
                        album_pic = c.get('pic') or c.get('img') or ''
                        if album_pic.startswith('//'):
                            album_pic = 'https:' + album_pic
                    nam = data.get('nam') or []
                    if isinstance(nam, list) and nam:
                        if isinstance(nam[0], list):
                            actors = [str(x) for x in nam[0] if x]
                        else:
                            actors = [str(x) for x in nam if x]
            except Exception as e:
                print(f"float_vinfo2 失败: {e}")
            
            # 2. 剧集列表
            try:
                ep_url = self.episodeApi + '?video_appid=3000010&vplatform=2'
                payload = {
                    "page_params": {
                        "req_from": "web",
                        "page_type": "detail_operation",
                        "page_id": "vsite_episode_list",
                        "id_type": "1",
                        "cid": cid,
                        "page_num": "",
                        "page_size": "100",
                        "page_context": ""
                    },
                    "has_cache": 1
                }
                h2 = dict(headers)
                h2['Content-Type'] = 'application/json'
                r = requests.post(ep_url, json=payload, headers=h2, timeout=12)
                if r.status_code == 200:
                    ep_data = r.json()
                    module_list = (ep_data.get('data') or {}).get('module_list_datas') or []
                    for mod in module_list:
                        for md in (mod.get('module_datas') or []):
                            item_datas = (md.get('item_data_lists') or {}).get('item_datas') or []
                            for item in item_datas:
                                params = item.get('item_params') or {}
                                title = params.get('union_title') or params.get('title') or ''
                                vid = params.get('vid') or ''
                                if vid:
                                    # 与爱奇艺一样给可解析的页面链接
                                    play_url = f'https://v.qq.com/x/cover/{cid}/{vid}.html'
                                    episodes.append({'name': title or f'第{len(episodes)+1}集', 'url': play_url})
                            if episodes:
                                break
                        if episodes:
                            break
            except Exception as e:
                print(f"剧集列表失败: {e}")
            
            # 无剧集时至少给一个入口
            if not episodes:
                episodes = [{
                    'name': album_name or '正片',
                    'url': f'https://v.qq.com/x/cover/{cid}.html'
                }]
            
            if not album_name:
                album_name = cid
            
            play_from = '腾讯视频'
            play_urls = []
            for ep in episodes:
                name = (ep.get('name') or '').replace('#', '').replace('$', '')
                url = ep.get('url') or ''
                if url:
                    play_urls.append(f"{name}${url}")
            
            vod = {
                "vod_id": video_id,
                "vod_name": album_name,
                "vod_pic": album_pic,
                "vod_remarks": f"共{len(episodes)}集" if len(episodes) > 1 else "正片",
                "vod_actor": ' '.join(actors[:10]) if actors else '',
                "vod_director": ' '.join(directors[:5]) if directors else '',
                "vod_content": (album_desc or '').replace('\n\n', '\n').strip(),
                "vod_play_from": play_from,
                "vod_play_url": '#'.join(play_urls)
            }
            result['list'] = [vod]
        except Exception as e:
            print(f"获取详情失败: {e}")
            result['list'] = []
        return result

    def searchContent(self, key, quick, pg=1):
        result = {
            'list': [],
            'page': int(pg) if pg else 1,
            'pagecount': 1,
            'limit': 25,
            'total': 0
        }
        try:
            page = max(int(pg) - 1, 0) if pg else 0
            videos = self._search_api(key, page=page, pagesize=25)
            videos = [v for v in videos if v.get('vod_id') and v.get('vod_name')]
            result['list'] = videos
            result['page'] = int(pg) if pg else 1
            result['pagecount'] = 999 if len(videos) >= 15 else (int(pg) if pg else 1)
            result['limit'] = 25
            result['total'] = len(videos)
        except Exception as e:
            print(f"搜索失败: {e}")
        return result

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        """与爱奇艺一致：非直链走解析站，提升 OK影视 兼容性"""
        result = {
            "parse": 1,
            "url": "",
            "jx": "1",
            "header": {
                "User-Agent": self.userAgent,
                "Referer": "https://v.qq.com/",
                "Origin": "https://v.qq.com"
            }
        }
        try:
            play_url = str(id or '').strip()
            if play_url.startswith('http'):
                play_url = play_url.replace('http://', 'https://')
                play_url = play_url.replace('https://www.v.qq.com/', 'https://v.qq.com/')
                play_url = play_url.replace('https://m.v.qq.com/', 'https://v.qq.com/')
            
            if self.isVideoFormat(play_url):
                result["parse"] = 0
                result["url"] = play_url
                result.pop("jx", None)
            else:
                result["parse"] = 1
                result["url"] = play_url
                result["jx"] = "1"
        except Exception as e:
            print(f"获取播放内容失败: {e}")
        return result

    def isVideoFormat(self, url):
        if not url or not str(url).startswith('http'):
            return False
        video_formats = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.flv', '.webm']
        u = str(url).lower()
        for fmt in video_formats:
            if fmt in u:
                return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))

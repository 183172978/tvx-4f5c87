# coding=utf-8
#!/usr/bin/python

"""
内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
"""

import sys
import json
import re
import urllib.parse
import requests

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def getName(self):
        return "酷影聚"

    def init(self, extend=""):
        self.host = "https://kuyingju.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host,
        }
        self.classes = []
        self.filters = {}
        self.home_videos = None
        self._load_config()
        print(f"[酷影聚] 初始化完成, 分类: {len(self.classes)}, 筛选: {len(self.filters)}")
    
    def _load_config(self):
        """加载分类和筛选配置"""
        self.classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '连续剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '46', 'type_name': '短剧'},
        ]
        
        common_filters = [
            {
                'key': 'class',
                'name': '剧情',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '喜剧', 'v': '喜剧'},
                    {'n': '爱情', 'v': '爱情'},
                    {'n': '恐怖', 'v': '恐怖'},
                    {'n': '动作', 'v': '动作'},
                    {'n': '科幻', 'v': '科幻'},
                    {'n': '剧情', 'v': '剧情'},
                    {'n': '战争', 'v': '战争'},
                    {'n': '警匪', 'v': '警匪'},
                    {'n': '犯罪', 'v': '犯罪'},
                    {'n': '动画', 'v': '动画'},
                    {'n': '奇幻', 'v': '奇幻'},
                    {'n': '武侠', 'v': '武侠'},
                    {'n': '冒险', 'v': '冒险'},
                    {'n': '悬疑', 'v': '悬疑'},
                    {'n': '惊悚', 'v': '惊悚'},
                    {'n': '古装', 'v': '古装'},
                    {'n': '历史', 'v': '历史'},
                ]
            },
            {
                'key': 'area',
                'name': '地区',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '大陆', 'v': '大陆'},
                    {'n': '香港', 'v': '香港'},
                    {'n': '台湾', 'v': '台湾'},
                    {'n': '美国', 'v': '美国'},
                    {'n': '法国', 'v': '法国'},
                    {'n': '英国', 'v': '英国'},
                    {'n': '日本', 'v': '日本'},
                    {'n': '韩国', 'v': '韩国'},
                    {'n': '德国', 'v': '德国'},
                    {'n': '泰国', 'v': '泰国'},
                    {'n': '印度', 'v': '印度'},
                    {'n': '其他', 'v': '其他'},
                ]
            },
            {
                'key': 'year',
                'name': '年份',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '2026', 'v': '2026'},
                    {'n': '2025', 'v': '2025'},
                    {'n': '2024', 'v': '2024'},
                    {'n': '2023', 'v': '2023'},
                    {'n': '2022', 'v': '2022'},
                    {'n': '2021', 'v': '2021'},
                    {'n': '2020', 'v': '2020'},
                    {'n': '2019', 'v': '2019'},
                    {'n': '2018', 'v': '2018'},
                ]
            },
            {
                'key': 'lang',
                'name': '语言',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '国语', 'v': '国语'},
                    {'n': '英语', 'v': '英语'},
                    {'n': '粤语', 'v': '粤语'},
                    {'n': '韩语', 'v': '韩语'},
                    {'n': '日语', 'v': '日语'},
                    {'n': '其它', 'v': '其它'},
                ]
            },
            {
                'key': 'by',
                'name': '排序',
                'value': [
                    {'n': '时间', 'v': 'time'},
                    {'n': '人气', 'v': 'hits'},
                    {'n': '评分', 'v': 'score'},
                ]
            }
        ]
        
        for cls in self.classes:
            self.filters[cls['type_id']] = common_filters

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        """首页内容"""
        result = {}
        result['class'] = self.classes
        result['filters'] = self.filters
        
        if self.home_videos is not None:
            result['list'] = self.home_videos
            return result
        
        try:
            first_tid = self.classes[0]['type_id'] if self.classes else '1'
            videos = self._fetch_category_videos(first_tid, '1', {})
            self.home_videos = videos
            result['list'] = videos
        except Exception as e:
            print(f"[酷影聚] Home content error: {e}")
            result['list'] = []
            
        return result

    def homeVideoContent(self):
        return {'list': self.home_videos or []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类视频列表"""
        result = {}
        try:
            videos = self._fetch_category_videos(tid, pg, extend)
            result['list'] = videos
            result['page'] = int(pg)
            result['pagecount'] = 999
            result['limit'] = 24
            result['total'] = 99999
        except Exception as e:
            print(f"[酷影聚] Category error: {e}")
            result['list'] = []
        return result

    def detailContent(self, ids):
        """获取视频详情和播放列表"""
        try:
            vid = ids[0]
            detail_url = f"{self.host}/index.php/vod/detail/id/{vid}.html"
            print(f"[酷影聚] 获取详情: {detail_url}")
            
            res = requests.get(detail_url, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            title = ''
            title_match = re.search(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>', html)
            if title_match:
                title = title_match.group(1).strip()
            
            pic = ''
            pic_match = re.search(r'<img[^>]+class="[^"]*lazyload[^"]*"[^>]+data-original="([^"]+)"', html)
            if pic_match:
                pic = pic_match.group(1)
            
            type_name = ''
            type_match = re.search(r'类型：([^/]+)', html)
            if type_match:
                type_name = type_match.group(1).strip()
            
            area = ''
            area_match = re.search(r'地区：</span>\s*([^<]+)</p>', html)
            if not area_match:
                area_match = re.search(r'/\s*地区：([^/\s<]+)', html)
            if area_match:
                area = area_match.group(1).strip()
            
            year = ''
            year_match = re.search(r'年份：(\d{4})', html)
            if year_match:
                year = year_match.group(1)
            
            remarks = ''
            remarks_match = re.search(r'状态：<span[^>]*>([^<]+)</span>', html)
            if remarks_match:
                remarks = remarks_match.group(1).strip()
            
            actor = ''
            actor_section = re.search(r'主演：(.*?)</p>', html, re.DOTALL)
            if actor_section:
                actors = re.findall(r'>([^<]+)</a>', actor_section.group(1))
                actor = ','.join(actors[:15]) if actors else ''
            
            director = ''
            dir_match = re.search(r'导演：(.*?)</p>', html, re.DOTALL)
            if dir_match:
                dirs = re.findall(r'>([^<]+)</a>', dir_match.group(1))
                director = ','.join(dirs) if dirs else ''
            
            desc = ''
            desc_match = re.search(r'<span class="detail-content"[^>]*>([^<]+)</span>', html)
            if desc_match:
                desc = desc_match.group(1).strip()
            
            play_from = []
            play_url = []
            
            source_pattern = r'<a href="#playlist(\d+)"[^>]*data-toggle="tab">([^<]+)</a>'
            sources = re.findall(source_pattern, html)
            
            for sid, sname in sources:
                sname = sname.strip()
                playlist_pattern = rf'id="playlist{sid}"[^>]*>.*?<ul[^>]*class="[^"]*stui-content__playlist[^"]*"[^>]*>(.*?)</ul>'
                playlist_match = re.search(playlist_pattern, html, re.DOTALL)
                if playlist_match:
                    ep_pattern = r'href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]+)</a>'
                    episodes = re.findall(ep_pattern, playlist_match.group(1))
                    if episodes:
                        play_from.append(sname)
                        ep_list = [f"{ep[1].strip()}${self.host}{ep[0]}" for ep in episodes]
                        play_url.append('#'.join(ep_list))
            
            if play_from and play_url:
                sorted_pairs = sorted(zip(play_from, play_url), key=lambda x: 1 if '高清' in x[0] else 0)
                play_from, play_url = zip(*sorted_pairs)
                play_from, play_url = list(play_from), list(play_url)
            
            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_year': year,
                'vod_area': area,
                'vod_remarks': remarks,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url)
            }
            
            print(f"[酷影聚] 详情: {title}, 类型: {type_name}, 年份: {year}, 线路: {len(play_from)}")
            return {'list': [vod]}
            
        except Exception as e:
            print(f"[酷影聚] Detail error: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索视频"""
        result = {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}
        try:
            search_url = f"{self.host}/index.php/vod/search.html"
            print(f"[酷影聚] 搜索: {key}")
            
            data = {'wd': key}
            res = requests.post(search_url, headers=self.headers, data=data, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            videos = self._extract_videos_from_html(html)
            result['list'] = videos
            result['page'] = int(pg)
            result['pagecount'] = 10
            result['total'] = len(videos)
            print(f"[酷影聚] 搜索到 {len(videos)} 个结果")
            
        except Exception as e:
            print(f"[酷影聚] Search error: {e}")
            
        return result

    def playerContent(self, flag, id, vipFlags):
        """
        获取播放链接
        flag: 线路名称
        id: 播放页URL
        
        播放链接验证分析:
        - 网站使用 player_aaaa 变量存储播放信息
        - url 字段通常是第三方平台链接(如腾讯视频)，需要解析
        - from 字段表示播放源(qq/youku/iqiyi等)
        - 直接复制播放链接失败是因为这些平台有自己的验证机制
        - 解决方案: 设置 parse=1 让TVBox播放器调用解析接口
        """
        try:
            print(f"[酷影聚] 获取播放链接: {id}")
            
            res = requests.get(id, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            player_match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;?\s*(?:</script>|var)', html, re.DOTALL)
            if player_match:
                try:
                    player_json = player_match.group(1)
                    player_data = json.loads(player_json)
                    
                    play_url = player_data.get('url', '').replace('\\/', '/')
                    play_from = player_data.get('from', '')
                    
                    if play_url:
                        print(f"[酷影聚] 播放URL: {play_url[:100]}...")
                        print(f"[酷影聚] 播放源: {play_from}")
                        
                        play_header = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': self.host
                        }
                        
                        if '.m3u8' in play_url or '.mp4' in play_url:
                            return {'parse': 0, 'url': play_url, 'header': play_header}
                        else:
                            return {'parse': 1, 'url': play_url, 'header': play_header}
                            
                except json.JSONDecodeError as e:
                    print(f"[酷影聚] JSON解析失败: {e}")
            
            url_match = re.search(r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"', html)
            if url_match:
                play_url = url_match.group(1).replace('\\/', '/')
                print(f"[酷影聚] 备用播放URL: {play_url[:80]}...")
                return {'parse': 0, 'url': play_url, 'header': {'User-Agent': 'Mozilla/5.0', 'Referer': self.host}}
            
            return {'parse': 1, 'url': id}
            
        except Exception as e:
            print(f"[酷影聚] Player error: {e}")
            return {'parse': 1, 'url': id}

    def _fetch_category_videos(self, tid, pg, extend):
        """
        获取分类视频列表
        tid: 分类ID
        pg: 页码
        extend: 筛选条件 {'class': '', 'area': '', 'year': '', 'lang': '', 'by': ''}
        """
        page = int(pg) if pg else 1
        
        url_parts = []
        
        if extend:
            if extend.get('class'):
                url_parts.append(f"class/{urllib.parse.quote(extend['class'])}")
            if extend.get('area'):
                url_parts.append(f"area/{urllib.parse.quote(extend['area'])}")
        
        url_parts.append(f"id/{tid}")
        
        if extend:
            if extend.get('year'):
                url_parts.append(f"year/{extend['year']}")
            if extend.get('lang'):
                url_parts.append(f"lang/{urllib.parse.quote(extend['lang'])}")
            if extend.get('by'):
                url_parts.append(f"by/{extend['by']}")
        
        url_parts.append(f"page/{page}")
        
        url = f"{self.host}/index.php/vod/show/{'/'.join(url_parts)}.html"
        
        if not extend or not any(extend.values()):
            url = f"{self.host}/index.php/vod/show/id/{tid}/page/{page}.html"
        
        print(f"[酷影聚] 获取列表: {url}")
        
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            return self._extract_videos_from_html(res.text)
        except Exception as e:
            print(f"[酷影聚] Fetch error: {e}")
            return []

    def _extract_videos_from_html(self, html):
        """从HTML提取视频列表"""
        videos = []
        seen_ids = set()
        
        pattern = r'<a[^>]+class="[^"]*stui-vodlist__thumb[^"]*lazyload[^"]*"[^>]+href="/index\.php/vod/detail/id/(\d+)\.html"[^>]+title="([^"]+)"[^>]+data-original="([^"]+)"[^>]*>.*?<span[^>]*class="[^"]*pic-text[^"]*"[^>]*><b>([^<]*)</b></span>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for vid, title, pic, remarks in matches:
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': title.strip(),
                'vod_pic': pic,
                'vod_remarks': remarks.strip()
            })
        
        if not videos:
            box_pattern = r'<div[^>]*class="[^"]*stui-vodlist__box[^"]*"[^>]*>(.*?)</div>\s*</li>'
            boxes = re.findall(box_pattern, html, re.DOTALL)
            
            for box in boxes:
                vid_match = re.search(r'href="/index\.php/vod/detail/id/(\d+)\.html"', box)
                title_match = re.search(r'title="([^"]+)"', box)
                pic_match = re.search(r'data-original="([^"]+)"', box)
                remarks_match = re.search(r'<span[^>]*class="[^"]*pic-text[^"]*"[^>]*><b>([^<]*)</b></span>', box)
                
                if vid_match and title_match:
                    vid = vid_match.group(1)
                    if vid in seen_ids:
                        continue
                    seen_ids.add(vid)
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title_match.group(1).strip(),
                        'vod_pic': pic_match.group(1) if pic_match else '',
                        'vod_remarks': remarks_match.group(1).strip() if remarks_match else ''
                    })
        
        print(f"[酷影聚] 提取视频: {len(videos)} 个")
        return videos

    def localProxy(self, param):
        return None
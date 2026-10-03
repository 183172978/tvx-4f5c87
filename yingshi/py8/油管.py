#coding=utf-8
#!/usr/bin/python
import re
import sys
import json
import time
from datetime import datetime
from urllib.parse import quote, unquote
import html

import requests

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "YouTube视频"

    def init(self, extend):
        try:
            self.extendDict = json.loads(extend)
        except:
            self.extendDict = {}
        
        # 代理配置 - 支持简化格式
        self.proxies = {}
        self.proxy_str = None  # 保存字符串格式的代理
        if 'proxy' in self.extendDict:
            proxy_val = self.extendDict['proxy']
            if proxy_val:
                if isinstance(proxy_val, dict):
                    # 如果是字典格式
                    self.proxies = proxy_val
                    if 'http' in proxy_val:
                        self.proxy_str = proxy_val['http'].replace('http://', '')
                elif isinstance(proxy_val, str):
                    # 如果是字符串格式 "127.0.0.1:1072"
                    self.proxy_str = proxy_val
                    self.proxies = {
                        'http': f'http://{proxy_val}',
                        'https': f'http://{proxy_val}'
                    }
        
        # 加载自定义分类配置
        self.config = {}
        if 'json' in self.extendDict:
            try:
                config_url = self.extendDict['json']
                if config_url.startswith('./'):
                    import os
                    config_path = os.path.join(os.path.dirname(__file__), config_url[2:])
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                else:
                    r = requests.get(config_url, timeout=10)
                    self.config = r.json()
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.config = {}
        
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.youtube.com"
        }
        
        # 存储continuation token的缓存
        self.continuation_cache = {}

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        
        if 'class' in self.config:
            result['class'] = self.config['class']
        else:
            result['class'] = [
                {'type_id': '全部', 'type_name': '全部'},
                {'type_id': '音乐', 'type_name': '音乐'},
                {'type_id': '游戏', 'type_name': '游戏'}
            ]
        
        if filter and 'filters' in self.config:
            result['filters'] = self.config['filters']
        
        return result

    def homeVideoContent(self):
        result = {}
        videos = []
        
        try:
            url = "https://www.youtube.com/results?search_query=热门视频"
            r = requests.get(url, headers=self.header, timeout=10, proxies=self.proxies)
            videos = self._extract_videos_fixed(r.text, 20)
        except Exception as e:
            print(f"首页视频获取失败: {e}")
        
        result['list'] = videos[:20]
        return result

    def categoryContent(self, cid, page, filter, ext):
        page = int(page)
        result = {}
        videos = []
        has_more = False
        
        print(f"处理分类: cid={cid}, page={page}")
        print(f"ext参数: {ext}")
        
        # 获取最终的搜索关键词
        if ext and 'tid' in ext and ext['tid']:
            raw_keyword = ext['tid']
            print(f"原始关键词: {raw_keyword}")
            
            # 处理多关键词（逗号分隔）
            if ',' in raw_keyword:
                # 多关键词，拆分为列表
                keywords = [x.strip() for x in raw_keyword.split(',')]
                print(f"拆分为多关键词: {keywords}")
                
                # 分离频道项和搜索词项
                channel_items = []
                search_items = []
                for kw in keywords:
                    if '@' in kw:
                        channel_items.append(kw)
                    else:
                        search_items.append(kw)
                
                # 第一页：显示所有频道文件夹
                if page == 1:
                    for item in channel_items:
                        parts = item.split('@')
                        display_name = parts[0].strip() if parts[0].strip() else parts[1]
                        channel_name = parts[1].strip()
                        videos.append({
                            "vod_id": f"channel_{channel_name}",
                            "vod_name": display_name,
                            "vod_pic": "https://www.youtube.com/s/desktop/2ad2ef02/img/favicon_144x144.png",
                            "vod_remarks": "频道"
                        })
                
                # 获取所有搜索词的当前页视频
                all_has_more = False
                for item in search_items:
                    item_videos, item_has_more = self._handle_pagination(
                        page=page,
                        search_keyword=item,
                        cache_prefix=f"search_{item}"
                    )
                    videos.extend(item_videos)
                    if item_has_more:
                        all_has_more = True
                
                has_more = all_has_more
                
            elif '@' in raw_keyword:
                # 单个频道
                parts = raw_keyword.split('@')
                channel_name = parts[1].strip()
                print(f"单个频道: {channel_name}, 页码: {page}")
                
                videos, has_more = self._handle_pagination(
                    page=page,
                    channel_name=channel_name,
                    cache_prefix=f"channel_{channel_name}"
                )
            else:
                # 单个搜索词
                print(f"单个搜索词: {raw_keyword}, 页码: {page}")
                videos, has_more = self._handle_pagination(
                    page=page,
                    search_keyword=raw_keyword,
                    cache_prefix=f"search_{raw_keyword}"
                )
        
        # 处理LIST类型（无ext参数时的第一页）
        elif cid.startswith('LIST:'):
            items = cid[5:].split(',')
            
            # 分离频道项和搜索词项
            channel_items = []
            search_items = []
            for item in items:
                item = item.strip()
                if '@' in item:
                    channel_items.append(item)
                else:
                    search_items.append(item)
            
            if page == 1:
                # 第一页：添加所有频道文件夹
                for item in channel_items:
                    parts = item.split('@')
                    display_name = parts[0].strip() if parts[0].strip() else parts[1]
                    channel_name = parts[1].strip()
                    videos.append({
                        "vod_id": f"channel_{channel_name}",
                        "vod_name": display_name,
                        "vod_pic": "https://www.youtube.com/s/desktop/2ad2ef02/img/favicon_144x144.png",
                        "vod_remarks": "频道"
                    })
                
                # 获取所有搜索词的第一页视频
                all_has_more = False
                for item in search_items:
                    item_videos, item_has_more = self._handle_pagination(
                        page=1,
                        search_keyword=item,
                        cache_prefix=f"search_{item}"
                    )
                    videos.extend(item_videos)
                    if item_has_more:
                        all_has_more = True
                
                has_more = all_has_more
            
            else:
                # 后续页：获取所有搜索词的后续页
                all_has_more = False
                for item in search_items:
                    item_videos, item_has_more = self._handle_pagination(
                        page=page,
                        search_keyword=item,
                        cache_prefix=f"search_{item}"
                    )
                    videos.extend(item_videos)
                    if item_has_more:
                        all_has_more = True
                
                has_more = all_has_more
        
        # 处理频道文件夹
        elif cid.startswith('channel_'):
            channel_name = cid[8:]
            videos, has_more = self._handle_pagination(
                page=page,
                channel_name=channel_name,
                cache_prefix=f"channel_{channel_name}"
            )
        
        # 普通搜索（无ext参数）
        else:
            search_keyword = cid
            videos, has_more = self._handle_pagination(
                page=page,
                search_keyword=search_keyword,
                cache_prefix=f"search_{search_keyword}"
            )
        
        # 去重
        seen = set()
        unique_videos = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique_videos.append(v)
        
        result['list'] = unique_videos
        result['page'] = page
        result['pagecount'] = page + 1 if has_more else page
        result['limit'] = len(unique_videos)
        result['total'] = len(unique_videos)
        
        print(f"返回结果: page={page}, pagecount={result['pagecount']}, 视频数={len(unique_videos)}")
        
        return result

    def _handle_pagination(self, page, search_keyword=None, channel_name=None, cache_prefix=None):
        """统一的翻页处理函数"""
        videos = []
        has_more = False
        
        # 确定基础URL和API URL
        if channel_name:
            base_url = f"https://www.youtube.com/@{channel_name}/videos"
            api_url = "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        else:
            base_url = f"https://www.youtube.com/results?search_query={quote(search_keyword)}"
            api_url = "https://www.youtube.com/youtubei/v1/search?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        
        if page == 1:
            # 第一页：直接访问页面
            try:
                r = requests.get(base_url, headers=self.header, timeout=15, proxies=self.proxies)
                html_content = r.text
                
                # 提取视频
                videos = self._extract_videos_fixed(html_content, 30)
                
                # 提取continuation token
                continuation = self._extract_continuation_token(html_content)
                if continuation:
                    self.continuation_cache[f"{cache_prefix}_2"] = continuation
                    has_more = True
                    print(f"找到continuation token，保存到 {cache_prefix}_2")
                    
            except Exception as e:
                print(f"获取第一页失败: {e}")
        else:
            # 后续页面：使用continuation token
            continuation = self.continuation_cache.get(f"{cache_prefix}_{page}")
            print(f"使用continuation token: {continuation[:50] if continuation else 'None'} 来自 {cache_prefix}_{page}")
            
            if continuation:
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": "2.20260310.01.00"
                        }
                    },
                    "continuation": continuation
                }
                
                try:
                    r = requests.post(api_url, json=payload, headers=self.header, timeout=15, proxies=self.proxies)
                    if r.status_code == 200:
                        data = r.json()
                        videos = self._extract_videos_from_api(data, 30)
                        
                        next_token = self._extract_next_continuation(data)
                        if next_token:
                            self.continuation_cache[f"{cache_prefix}_{page+1}"] = next_token
                            has_more = True
                            print(f"找到下一个continuation token，保存到 {cache_prefix}_{page+1}")
                        else:
                            print(f"没有更多continuation token")
                    else:
                        print(f"API请求失败: {r.status_code}")
                except Exception as e:
                    print(f"API请求异常: {e}")
            else:
                print(f"未找到continuation token")
        
        return videos, has_more

    def detailContent(self, did):
        video_id = did[0]
        print(f"获取详情: {video_id}")
        
        # 处理频道文件夹
        if video_id.startswith('channel_'):
            channel_name = video_id[8:]
            
            all_videos = []
            page = 1
            max_pages = 10
            max_videos = 100
            cache_prefix = f"channel_{channel_name}"
            continuation = None
            
            while page <= max_pages and len(all_videos) < max_videos:
                if page == 1:
                    channel_url = f"https://www.youtube.com/@{channel_name}/videos"
                    print(f"获取UP主频道视频第{page}页: {channel_url}")
                    try:
                        r = requests.get(channel_url, headers=self.header, timeout=15, proxies=self.proxies)
                        html_content = r.text
                        
                        page_videos = self._extract_videos_fixed(html_content, 30)
                        if page_videos:
                            all_videos.extend(page_videos)
                            print(f"第{page}页获取到 {len(page_videos)} 个视频，累计 {len(all_videos)} 个")
                        
                        continuation = self._extract_continuation_token(html_content)
                        if not continuation:
                            print("没有找到continuation token，停止翻页")
                            break
                            
                    except Exception as e:
                        print(f"获取第一页失败: {e}")
                        break
                else:
                    if not continuation:
                        print("没有continuation token，停止翻页")
                        break
                    
                    api_url = "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
                    payload = {
                        "context": {
                            "client": {
                                "clientName": "WEB",
                                "clientVersion": "2.20260310.01.00"
                            }
                        },
                        "continuation": continuation
                    }
                    
                    try:
                        r = requests.post(api_url, json=payload, headers=self.header, timeout=15, proxies=self.proxies)
                        if r.status_code == 200:
                            data = r.json()
                            page_videos = self._extract_videos_from_api(data, 30)
                            if page_videos:
                                all_videos.extend(page_videos)
                                print(f"第{page}页获取到 {len(page_videos)} 个视频，累计 {len(all_videos)} 个")
                            
                            continuation = self._extract_next_continuation(data)
                            if not continuation:
                                print("没有更多continuation token，停止翻页")
                                break
                        else:
                            print(f"API返回错误: {r.status_code}")
                            break
                    except Exception as e:
                        print(f"获取第{page}页失败: {e}")
                        break
                
                page += 1
                time.sleep(1)
            
            if not all_videos:
                return {'list': []}
            
            if len(all_videos) > max_videos:
                all_videos = all_videos[:max_videos]
            
            play_url_parts = []
            for v in all_videos:
                safe_title = self._safe_title(v['vod_name'])
                play_url_parts.append(f"{safe_title}${v['vod_id']}")
            
            play_url = '#'.join(play_url_parts)
            
            vod = {
                "vod_id": video_id,
                "vod_name": f"{channel_name}的频道 ({len(all_videos)}个视频)",
                "vod_pic": "https://www.youtube.com/s/desktop/2ad2ef02/img/favicon_144x144.png",
                "vod_play_from": "UP主频道",
                "vod_play_url": play_url,
                "vod_content": f"{channel_name}的YouTube频道，共{len(all_videos)}个视频"
            }
            
            return {'list': [vod]}
        
        # 正常视频详情
        try:
            video_title = self._get_video_title(video_id)
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            r = requests.get(video_url, headers=self.header, timeout=15, proxies=self.proxies)
            html_content = r.text
            
            channel_display_name = self._extract_channel_display_name(html_content)
            channel_identifier = self._get_channel_identifier_by_search(channel_display_name)
            
            related_videos = self._extract_related_videos_fixed(html_content, video_id, 30)
            
            # 获取UP主频道的视频列表 - 增加到99个
            channel_videos = []
            if channel_identifier:
                encoded_identifier = quote(channel_identifier, safe='')
                channel_url = f"https://www.youtube.com/@{encoded_identifier}/videos"
                print(f"获取UP主 {channel_identifier} 的频道视频: {channel_url}")
                
                # 获取多页视频
                page = 1
                max_pages = 10
                max_videos = 100
                continuation = None
                
                while page <= max_pages and len(channel_videos) < max_videos:
                    if page == 1:
                        try:
                            r2 = requests.get(channel_url, headers=self.header, timeout=10, proxies=self.proxies)
                            html_content = r2.text
                            
                            page_videos = self._extract_videos_fixed(html_content, 30)
                            if page_videos:
                                channel_videos.extend(page_videos)
                                print(f"UP主第{page}页获取到 {len(page_videos)} 个视频，累计 {len(channel_videos)} 个")
                            
                            continuation = self._extract_continuation_token(html_content)
                            if not continuation:
                                print("没有找到continuation token，停止翻页")
                                break
                                
                        except Exception as e:
                            print(f"获取UP主第一页失败: {e}")
                            break
                    else:
                        if not continuation:
                            break
                        
                        api_url = "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
                        payload = {
                            "context": {
                                "client": {
                                    "clientName": "WEB",
                                    "clientVersion": "2.20260310.01.00"
                                }
                            },
                            "continuation": continuation
                        }
                        
                        try:
                            r2 = requests.post(api_url, json=payload, headers=self.header, timeout=15, proxies=self.proxies)
                            if r2.status_code == 200:
                                data = r2.json()
                                page_videos = self._extract_videos_from_api(data, 30)
                                if page_videos:
                                    channel_videos.extend(page_videos)
                                    print(f"UP主第{page}页获取到 {len(page_videos)} 个视频，累计 {len(channel_videos)} 个")
                                
                                continuation = self._extract_next_continuation(data)
                                if not continuation:
                                    print("没有更多continuation token，停止翻页")
                                    break
                            else:
                                print(f"UP主API返回错误: {r2.status_code}")
                                break
                        except Exception as e:
                            print(f"获取UP主第{page}页失败: {e}")
                            break
                    
                    page += 1
                    time.sleep(0.5)
                
                print(f"最终获取到 {len(channel_videos)} 个UP主视频")
            
            vod = {
                "vod_id": video_id,
                "vod_name": video_title[:100] + ('...' if len(video_title) > 100 else ''),
                "vod_pic": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "vod_content": '',
                "vod_actor": channel_identifier,
                "vod_remarks": ''
            }
            
            play_url1 = f"{self._safe_title(video_title)}${video_id}"
            
            play_url2_parts = []
            for cv in channel_videos[:100]:
                if cv['vod_id'] != video_id:
                    play_url2_parts.append(f"{self._safe_title(cv['vod_name'])}${cv['vod_id']}")
            
            play_url3_parts = []
            for rv in related_videos[:30]:
                if rv['vod_id'] != video_id:
                    play_url3_parts.append(f"{self._safe_title(rv['vod_name'])}${rv['vod_id']}")
            
            if channel_identifier:
                vod['vod_director'] = f'[a=cr:{{"id":"channel_{channel_identifier}","name":"{channel_identifier}"}}/]{channel_identifier}[/a]'
            
            vod['vod_play_from'] = '当前视频$$$UP主频道$$$相关视频'
            vod['vod_play_url'] = f"{play_url1}$$${'#'.join(play_url2_parts)}$$${'#'.join(play_url3_parts)}"
            
            return {'list': [vod]}
            
        except Exception as e:
            print(f"Detail error: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        if quick:
            return {'list': []}
            
        page = int(pg) if pg else 1
        
        videos, has_more = self._handle_pagination(
            page=page,
            search_keyword=key,
            cache_prefix=f"search_{key}"
        )
        
        seen = set()
        unique_videos = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique_videos.append(v)
        
        return {
            'list': unique_videos,
            'page': page,
            'pagecount': page + 1 if has_more else page,
            'limit': len(unique_videos),
            'total': len(unique_videos)
        }

    def playerContent(self, flag, pid, vipFlags):
        result = {}
        
        if '$' in pid:
            video_id = pid.split('$')[-1]
        else:
            video_id = pid
        
        result["parse"] = 1
        result["url"] = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
        result["header"] = self.header
        
        # 内置代理 - 只传字符串格式，不传字典
        if self.proxy_str:
            result["proxy"] = self.proxy_str
            print(f"使用内置代理: {self.proxy_str}")
        
        return result

    # ==================== 精简版核心方法（只保留主方法，删除备用） ====================

    def _get_vod_remarks(self, title, duration):
        """统一获取视频备注"""
        if duration:
            return duration
        live_keywords = ['live', '直播', '生放送', 'LIVE', '🔴', '🟢', '🔵']
        for keyword in live_keywords:
            if keyword in title:
                return "🟢 直播"
        return "🟢 直播"

    def _extract_continuation_token(self, html_content):
        """从HTML中提取continuation token - 只保留主方法"""
        try:
            pattern = r'var ytInitialData = ({.*?});</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            if not match:
                return None
            
            data = json.loads(match.group(1))
            
            def find_token(obj):
                if isinstance(obj, dict):
                    if 'continuationCommand' in obj and 'token' in obj['continuationCommand']:
                        return obj['continuationCommand']['token']
                    if 'continuation' in obj and isinstance(obj['continuation'], str):
                        return obj['continuation']
                    for value in obj.values():
                        result = find_token(value)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_token(item)
                        if result:
                            return result
                return None
            
            return find_token(data)
        except Exception as e:
            print(f"提取continuation token失败: {e}")
            return None

    def _extract_next_continuation(self, data):
        """从API响应中提取下一个continuation token"""
        try:
            def find_token(obj):
                if isinstance(obj, dict):
                    if 'continuationCommand' in obj and 'token' in obj['continuationCommand']:
                        return obj['continuationCommand']['token']
                    if 'continuation' in obj and isinstance(obj['continuation'], str):
                        return obj['continuation']
                    for value in obj.values():
                        result = find_token(value)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_token(item)
                        if result:
                            return result
                return None
            return find_token(data)
        except Exception as e:
            print(f"提取下一个continuation token失败: {e}")
            return None

    def _extract_videos_from_api(self, data, limit=30):
        """从API响应中提取视频列表"""
        videos = []
        
        try:
            def extract_videos(obj):
                items = []
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        items.append(obj)
                    elif 'compactVideoRenderer' in obj:
                        items.append(obj)
                    else:
                        for value in obj.values():
                            items.extend(extract_videos(value))
                elif isinstance(obj, list):
                    for item in obj:
                        items.extend(extract_videos(item))
                return items
            
            video_items = extract_videos(data)
            
            seen = set()
            for item in video_items[:limit]:
                if 'videoRenderer' in item:
                    video = self._parse_video_renderer(item['videoRenderer'])
                elif 'compactVideoRenderer' in item:
                    video = self._parse_compact_video_renderer(item['compactVideoRenderer'])
                else:
                    continue
                
                if video and video['vod_id'] not in seen:
                    seen.add(video['vod_id'])
                    videos.append(video)
                    
        except Exception as e:
            print(f"从API提取视频失败: {e}")
        
        return videos

    def _parse_video_renderer(self, renderer):
        """解析videoRenderer"""
        try:
            video_id = renderer.get('videoId', '')
            if len(video_id) != 11:
                return None
            
            title = ''
            if 'title' in renderer:
                if 'runs' in renderer['title']:
                    runs = renderer['title']['runs']
                    if runs and 'text' in runs[0]:
                        title = runs[0]['text']
                elif 'simpleText' in renderer['title']:
                    title = renderer['title']['simpleText']
            
            if not title:
                return None
            
            title = html.unescape(title)
            
            duration = ''
            if 'lengthText' in renderer and 'simpleText' in renderer['lengthText']:
                duration = renderer['lengthText']['simpleText']
            
            vod_remarks = self._get_vod_remarks(title, duration)
            
            return {
                "vod_id": video_id,
                "vod_name": title,
                "vod_pic": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "vod_remarks": vod_remarks
            }
        except:
            return None

    def _parse_compact_video_renderer(self, renderer):
        """解析compactVideoRenderer"""
        try:
            video_id = renderer.get('videoId', '')
            if len(video_id) != 11:
                return None
            
            title = ''
            if 'title' in renderer:
                if 'runs' in renderer['title']:
                    runs = renderer['title']['runs']
                    if runs and 'text' in runs[0]:
                        title = runs[0]['text']
                elif 'simpleText' in renderer['title']:
                    title = renderer['title']['simpleText']
            
            if not title:
                return None
            
            title = title.replace('\\u0026', '&').replace('\\"', '"')
            title = html.unescape(title)
            
            duration = ''
            if 'lengthText' in renderer:
                if 'simpleText' in renderer['lengthText']:
                    duration = renderer['lengthText']['simpleText']
                elif 'runs' in renderer['lengthText']:
                    runs = renderer['lengthText']['runs']
                    if runs and 'text' in runs[0]:
                        duration = runs[0]['text']
            
            vod_remarks = self._get_vod_remarks(title, duration)
            
            return {
                "vod_id": video_id,
                "vod_name": title,
                "vod_pic": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "vod_remarks": vod_remarks
            }
        except:
            return None

    def _extract_videos_fixed(self, html_content, limit=50):
        """从HTML中提取视频列表 - 只保留ytInitialData方法"""
        videos = []
        
        try:
            pattern = r'var ytInitialData = ({.+?});</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                print("未找到 ytInitialData")
                return videos
            
            data = json.loads(match.group(1))
            
            def find_videos(obj):
                items = []
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        items.append(obj)
                    elif 'compactVideoRenderer' in obj:
                        items.append(obj)
                    else:
                        for value in obj.values():
                            items.extend(find_videos(value))
                elif isinstance(obj, list):
                    for item in obj:
                        items.extend(find_videos(item))
                return items
            
            video_items = find_videos(data)
            
            seen = set()
            for item in video_items[:limit]:
                if 'videoRenderer' in item:
                    video = self._parse_video_renderer(item['videoRenderer'])
                elif 'compactVideoRenderer' in item:
                    video = self._parse_compact_video_renderer(item['compactVideoRenderer'])
                else:
                    continue
                
                if video and video['vod_id'] not in seen:
                    seen.add(video['vod_id'])
                    videos.append(video)
                    
        except Exception as e:
            print(f"提取视频失败: {e}")
        
        return videos

    def _extract_related_videos_fixed(self, html_content, current_video_id, limit=30):
        """从视频页面提取相关视频 - 只保留ytInitialData方法"""
        videos = []
        
        try:
            pattern = r'var ytInitialData = ({.+?});</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                return videos
            
            data = json.loads(match.group(1))
            
            if 'contents' in data:
                if 'twoColumnWatchNextResults' in data['contents']:
                    secondary = data['contents']['twoColumnWatchNextResults'].get('secondaryResults', {})
                    if 'secondaryResults' in secondary:
                        results = secondary['secondaryResults'].get('results', [])
                        seen = set([current_video_id])
                        for item in results:
                            if 'compactVideoRenderer' in item:
                                renderer = item['compactVideoRenderer']
                                video_id = renderer.get('videoId', '')
                                if len(video_id) == 11 and video_id not in seen:
                                    seen.add(video_id)
                                    
                                    title = ''
                                    if 'title' in renderer:
                                        if 'runs' in renderer['title']:
                                            runs = renderer['title']['runs']
                                            if runs and 'text' in runs[0]:
                                                title = runs[0]['text']
                                        elif 'simpleText' in renderer['title']:
                                            title = renderer['title']['simpleText']
                                    
                                    if title:
                                        title = html.unescape(title)
                                        
                                        duration = ''
                                        if 'lengthText' in renderer:
                                            if 'simpleText' in renderer['lengthText']:
                                                duration = renderer['lengthText']['simpleText']
                                            elif 'runs' in renderer['lengthText']:
                                                runs = renderer['lengthText']['runs']
                                                if runs and 'text' in runs[0]:
                                                    duration = runs[0]['text']
                                        
                                        vod_remarks = self._get_vod_remarks(title, duration)
                                        
                                        videos.append({
                                            "vod_id": video_id,
                                            "vod_name": title,
                                            "vod_pic": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                                            "vod_remarks": vod_remarks
                                        })
                                        
                                        if len(videos) >= limit:
                                            break
        except Exception as e:
            print(f"提取相关视频失败: {e}")
        
        return videos

    def _safe_title(self, title, max_len=80):
        """安全处理标题"""
        if not title:
            return "未知标题"
        title = str(title)
        for char in ['#', '$', '/', '\\', '?', '&', '=', '+', '%', '@', '!', '*', '|', '<', '>', '"', "'"]:
            title = title.replace(char, '·')
        if len(title) > max_len:
            title = title[:max_len] + '...'
        return title

    def _get_video_title(self, video_id):
        """获取视频真实标题"""
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            r = requests.get(oembed_url, headers=self.header, timeout=5, proxies=self.proxies)
            if r.status_code == 200:
                data = r.json()
                return html.unescape(data.get('title', video_id))
        except:
            pass
        return video_id

    def _extract_channel_display_name(self, html_content):
        """从视频页面提取UP主显示名称"""
        try:
            pattern = r'"ownerChannelName":"([^"]+)"'
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
            
            pattern = r'"author":"([^"]+)"'
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        except:
            pass
        return ''

    def _get_channel_identifier_by_search(self, channel_name):
        """通过搜索获取频道的真实标识符"""
        if not channel_name:
            return ''
        
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote(channel_name)}"
            r = requests.get(search_url, headers=self.header, timeout=10, proxies=self.proxies)
            html_content = r.text
            
            pattern = r'@([^"\s<>/?&#]+)'
            matches = re.findall(pattern, html_content)
            
            if matches:
                identifier = max(matches, key=len)
                decoded_identifier = unquote(identifier)
                return decoded_identifier
            
        except Exception as e:
            print(f"搜索频道标识符失败: {e}")
        
        return channel_name

    def removeHtmlTags(self, src):
        from re import sub, compile
        clean = compile('<.*?>')
        return sub(clean, '', src)

    def cleanText(self, text):
        return text.replace('\n', '').replace('\r', '').replace('\t', '')

    def getCache(self, key):
        return None

    def setCache(self, key, value):
        pass

    def delCache(self, key):
        pass

    def destroy(self):
        pass
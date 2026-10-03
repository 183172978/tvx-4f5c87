#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
        self.siteUrl = 'https://a123tv.com'
        self.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

        self.channels = {
            '10': {'name': '电影'},
            '11': {'name': '连续剧'},
            '12': {'name': '综艺'},
            '13': {'name': '动漫'},
            '15': {'name': '福利'},
        }

        self.filters = {
            "10": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "动作片", "v": "1001"},
                    {"n": "喜剧片", "v": "1002"},
                    {"n": "爱情片", "v": "1003"},
                    {"n": "科幻片", "v": "1004"},
                    {"n": "恐怖片", "v": "1005"},
                    {"n": "剧情片", "v": "1006"},
                    {"n": "战争片", "v": "1007"},
                    {"n": "纪录片", "v": "1008"},
                    {"n": "动漫电影", "v": "1010"},
                    {"n": "奇幻片", "v": "1011"},
                    {"n": "动画片", "v": "1013"},
                    {"n": "犯罪片", "v": "1014"},
                    {"n": "悬疑片", "v": "1016"},
                    {"n": "邵氏电影", "v": "1019"},
                    {"n": "歌舞片", "v": "1022"},
                    {"n": "家庭片", "v": "1024"},
                    {"n": "古装片", "v": "1025"},
                    {"n": "历史片", "v": "1026"},
                    {"n": "4K电影", "v": "1027"}
                ]}
            ],
            "11": [
                {"key": "class", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国产剧", "v": "1101"},
                    {"n": "香港剧", "v": "1102"},
                    {"n": "台湾剧", "v": "1105"},
                    {"n": "韩国剧", "v": "1103"},
                    {"n": "欧美剧", "v": "1104"},
                    {"n": "日本剧", "v": "1106"},
                    {"n": "泰国剧", "v": "1108"},
                    {"n": "港台剧", "v": "1110"},
                    {"n": "日韩剧", "v": "1111"},
                    {"n": "海外剧", "v": "1107"}
                ]}
            ],
            "12": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地综艺", "v": "1201"},
                    {"n": "港台综艺", "v": "1202"},
                    {"n": "日韩综艺", "v": "1203"},
                    {"n": "欧美综艺", "v": "1204"},
                    {"n": "国外综艺", "v": "1205"}
                ]}
            ],
            "13": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国产动漫", "v": "1301"},
                    {"n": "日韩动漫", "v": "1302"},
                    {"n": "欧美动漫", "v": "1303"},
                    {"n": "海外动漫", "v": "1305"},
                    {"n": "里番", "v": "1307"}
                ]}
            ],
            "15": [
                {"key": "class", "name": "分类", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "韩国情色片", "v": "1551"},
                    {"n": "日本情色片", "v": "1552"},
                    {"n": "大陆情色片", "v": "1555"},
                    {"n": "香港情色片", "v": "1553"},
                    {"n": "台湾情色片", "v": "1554"},
                    {"n": "美国情色片", "v": "1556"},
                    {"n": "欧洲情色片", "v": "1557"},
                    {"n": "印度情色片", "v": "1558"},
                    {"n": "东南亚情色片", "v": "1559"},
                    {"n": "其它情色片", "v": "1550"}
                ]}
            ]
        }

    def getName(self):
        return "123TV"

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        try:
            if params:
                response = requests.get(url, headers=headers, params=params, timeout=15)
            else:
                response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            return None

    def _fix_pic(self, url):
        if not url:
            return ''
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return 'https:' + url
        return self.siteUrl + (url if url.startswith('/') else '/' + url)

    def _parse_list(self, html):
        """解析列表页，适配当前 a123tv 新结构"""
        videos = []
        if not html:
            return videos

        # 主正则
        pattern = re.compile(
            r'<a class="w4-item" href="([^"]+)"[\s\S]*?'
            r'<img[^>]*data-src="([^"]+)"[\s\S]*?'
            r'<div class="s">[\s\S]*?<span>([^<]*)</span>[\s\S]*?'
            r'<div class="t"[^>]*(?:title="([^"]*)")?[^>]*>([^<]*)</div>[\s\S]*?'
            r'<div class="i">([^<]*)</div>',
            re.I
        )
        for m in pattern.finditer(html):
            vod_id = m.group(1).strip()
            pic = m.group(2).strip()
            remarks = (m.group(3) or '').strip()
            name = (m.group(4) or m.group(5) or '').strip()
            info = (m.group(6) or '').strip()
            if not vod_id or not name:
                continue
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": self._fix_pic(pic),
                "vod_remarks": remarks or info
            })

        # 宽松兜底
        if not videos:
            loose = re.compile(
                r'<a class="w4-item" href="([^"]+)"[\s\S]*?'
                r'data-src="([^"]+)"[\s\S]*?'
                r'<div class="t"[^>]*>([^<]+)</div>[\s\S]*?'
                r'<div class="i">([^<]*)</div>',
                re.I
            )
            for m in loose.finditer(html):
                videos.append({
                    "vod_id": m.group(1).strip(),
                    "vod_name": (m.group(3) or '').strip(),
                    "vod_pic": self._fix_pic(m.group(2)),
                    "vod_remarks": (m.group(4) or '').strip()
                })
        return videos

    def homeContent(self, filter):
        result = {}
        classes = []
        for k, v in self.channels.items():
            classes.append({
                'type_id': k,
                'type_name': v['name']
            })
        result['class'] = classes
        if filter:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        result = {}
        videos = []
        try:
            resp = self.fetch(self.siteUrl)
            if resp:
                videos = self._parse_list(resp.text)[:24]
        except Exception as e:
            print(f"获取首页视频失败: {e}")
        result['list'] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        pg = int(pg) if pg else 1
        try:
            # 处理筛选
            real_tid = tid
            if extend and isinstance(extend, dict) and extend.get('class'):
                real_tid = extend['class']
            if not real_tid:
                real_tid = tid

            if pg == 1:
                url = f'{self.siteUrl}/t/{real_tid}.html'
            else:
                url = f'{self.siteUrl}/t/{real_tid}/p{pg}.html'

            resp = self.fetch(url)
            if resp:
                html = resp.text
                videos = self._parse_list(html)

                # 解析最大页数
                pagecount = pg
                page_re = re.compile(r'/p(\d+)\.html[^>]*>\s*(\d+)\s*</a>')
                for m in page_re.finditer(html):
                    n = int(m.group(2))
                    if n > pagecount:
                        pagecount = n
                if pagecount <= pg and len(videos) >= 20:
                    pagecount = pg + 1
            else:
                pagecount = pg
        except Exception as e:
            print(f"获取分类内容失败: {e}")
            pagecount = pg

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = pagecount
        result['limit'] = 24
        result['total'] = 9999
        return result

    def detailContent(self, ids):
        result = {}
        try:
            video_id = ids[0]
            url = video_id if video_id.startswith('http') else (
                self.siteUrl + (video_id if video_id.startswith('/') else '/' + video_id)
            )
            resp = self.fetch(url)
            if not resp:
                result['list'] = []
                return result

            html = resp.text
            vod = {
                "vod_id": video_id,
                "vod_name": '',
                "vod_pic": '',
                "vod_remarks": '',
                "vod_year": '',
                "vod_area": '',
                "vod_actor": '',
                "vod_director": '',
                "vod_content": '',
                "vod_play_from": '',
                "vod_play_url": ''
            }

            # 标题
            title_m = re.search(r'<li class="on"><h1>([^<]+)</h1>', html) or re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if title_m:
                vod['vod_name'] = title_m.group(1).strip()

            # 封面
            pic_m = re.search(r'data-poster="([^"]+)"', html) or re.search(r'og:image"[^>]*content="([^"]+)"', html)
            if pic_m:
                vod['vod_pic'] = self._fix_pic(pic_m.group(1))

            # 描述 / 演员 / 地区 / 导演
            desc_m = re.search(r'name="description" content="([^"]*)"', html)
            if desc_m:
                content = desc_m.group(1)
                vod['vod_content'] = content
                actor_m = re.search(r'演员[：:](.*?)(?:[。.]|$)', content)
                if actor_m:
                    vod['vod_actor'] = actor_m.group(1).strip()
                area_m = re.search(r'地区[：:](.*?)(?:[。.]|$)', content)
                if area_m:
                    vod['vod_area'] = area_m.group(1).strip()
                dir_m = re.search(r'导演[：:](.*?)(?:[。.]|$)', content)
                if dir_m:
                    vod['vod_director'] = dir_m.group(1).strip()

            # 解析播放源（新版 pp 已直接带 m3u8）
            script_m = re.search(r'var pp=(\{[\s\S]*?\});', html)
            if script_m:
                try:
                    pp = json.loads(script_m.group(1))
                    if pp and isinstance(pp.get('la'), list):
                        from_arr = []
                        url_arr = []
                        for idx, line in enumerate(pp['la']):
                            # line: [id, name, epCount, ?, m3u8?]
                            line_id = line[0] if len(line) > 0 else ''
                            line_name = line[1] if len(line) > 1 else f'线路{idx + 1}'
                            ep_count = int(line[2]) if len(line) > 2 and str(line[2]).isdigit() else 1
                            direct_url = ''
                            if len(line) > 4 and isinstance(line[4], str) and line[4].startswith('http'):
                                direct_url = line[4]

                            episodes = []
                            if direct_url and ep_count <= 1:
                                # 电影 / 单集直接用 m3u8
                                episodes.append(f'正片${direct_url}')
                            else:
                                # 多集或无直链 → 走播放页
                                no = pp.get('no', '')
                                for i in range(ep_count):
                                    ep_name = '正片' if ep_count == 1 else f'第{i + 1}集'
                                    play_path = f'/v/{no}/{line_id}z{i}.html'
                                    episodes.append(f'{ep_name}${play_path}')
                            if episodes:
                                from_arr.append(line_name)
                                url_arr.append('#'.join(episodes))

                        vod['vod_play_from'] = '$$$'.join(from_arr)
                        vod['vod_play_url'] = '$$$'.join(url_arr)
                        if len(from_arr) > 1:
                            vod['vod_remarks'] = f'{len(from_arr)}条线路'
                        elif ep_count > 1:
                            vod['vod_remarks'] = f'共{ep_count}集'
                except Exception as e:
                    print(f"解析pp失败: {e}")

            # 兜底：从页面提取第一个 data-src
            if not vod['vod_play_url']:
                data_src = re.search(r'data-src="(https?://[^"]+\.(?:m3u8|mp4)[^"]*)"', html, re.I)
                if data_src:
                    vod['vod_play_from'] = '默认'
                    vod['vod_play_url'] = f'正片${data_src.group(1)}'

            result['list'] = [vod]
        except Exception as e:
            print(f"获取详情失败: {e}")
            result['list'] = []
        return result

    def searchContent(self, key, quick, pg=1):
        result = {}
        videos = []
        pg = int(pg) if pg else 1
        try:
            encoded = urllib.parse.quote(key)
            if pg == 1:
                url = f'{self.siteUrl}/s/{encoded}.html'
            else:
                url = f'{self.siteUrl}/s/{encoded}/p{pg}.html'
            resp = self.fetch(url)
            if resp:
                videos = self._parse_list(resp.text)
            result = {
                'list': videos,
                'page': pg,
                'pagecount': pg + 1 if len(videos) >= 20 else pg,
                'limit': 24,
                'total': 9999
            }
        except Exception as e:
            print(f"搜索失败: {e}")
            result = {'list': videos, 'page': pg, 'pagecount': pg, 'limit': 24, 'total': len(videos)}
        return result

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            play_id = id

            # 已经是直链
            if play_id.startswith('http') and re.search(r'\.(m3u8|mp4|flv|mkv|ts)', play_id, re.I):
                result["parse"] = 0
                result["url"] = play_id
                result["header"] = {
                    "User-Agent": self.userAgent,
                    "Referer": self.siteUrl + "/"
                }
                return result

            # 需要请求播放页
            if not play_id.startswith('http'):
                final_url = self.siteUrl + (play_id if play_id.startswith('/') else '/' + play_id)
            else:
                final_url = play_id

            resp = self.fetch(final_url)
            video_url = ''
            if resp:
                html = resp.text

                # 优先 data-src
                data_src = re.search(r'data-src="(https?://[^"]+)"', html, re.I)
                if data_src:
                    video_url = data_src.group(1)

                # 再从 pp 找
                if not video_url:
                    script_m = re.search(r'var pp=(\{[\s\S]*?\});', html)
                    if script_m:
                        try:
                            pp = json.loads(script_m.group(1))
                            if pp and isinstance(pp.get('la'), list):
                                for line in pp['la']:
                                    if len(line) > 4 and isinstance(line[4], str) and line[4].startswith('http'):
                                        video_url = line[4]
                                        break
                        except Exception:
                            pass

                # 页面其他 m3u8
                if not video_url:
                    m3u8 = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html, re.I)
                    if m3u8:
                        video_url = m3u8.group(1)

            if video_url:
                result["parse"] = 0
                result["url"] = video_url
            else:
                result["parse"] = 1
                result["url"] = final_url
                result["jx"] = "1"

            result["header"] = {
                "User-Agent": self.userAgent,
                "Referer": self.siteUrl + "/"
            }
        except Exception as e:
            print(f"获取播放内容失败: {e}")
            result["parse"] = 1
            result["url"] = id
            result["header"] = {"User-Agent": self.userAgent}
        return result

    def isVideoFormat(self, url):
        video_formats = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.flv', '.webm']
        if url and url.startswith('http'):
            for fmt in video_formats:
                if url.lower().find(fmt) > -1:
                    return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))

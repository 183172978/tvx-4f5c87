# coding=utf-8
import sys
sys.path.append('..')
from base.spider import Spider
import json
import urllib.parse
import re
from lxml import etree

class Spider(Spider):
    def init(self, extend=""):
        self.homeUrl = "https://ww98.taiee.xyz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Android; Mobile) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
            "Referer": self.homeUrl
        }

    # 首页推荐数据
    def homeContent(self, filter):
        result = {
            "class": [
                {"type_id": "20", "type_name": "电影"},
                {"type_id": "21", "type_name": "剧集"},
                {"type_id": "22", "type_name": "综艺"},
                {"type_id": "23", "type_name": "动漫"}
            ],
            "list": [],
            "page": 1
        }
        # 首页推荐区域（相关影视板块）
        html = self.fetch(self.homeUrl, headers=self.headers).text
        tree = etree.HTML(html)
        vod_list = tree.xpath('//div[contains(@class,"public-list-box")]')
        for item in vod_list:
            vod = {}
            # 详情链接
            link = item.xpath('.//a[@class="public-list-exp"]/@href')
            if not link:
                continue
            vod["vod_id"] = link[0].split("/id/")[-1].replace(".html", "")
            vod["vod_detail_url"] = self.homeUrl + link[0]
            # 片名
            name = item.xpath('.//a[@class="time-title"]/text()')
            vod["vod_name"] = name[0].strip() if name else "未知影片"
            # 封面图 data-src懒加载
            pic = item.xpath('.//img/@data-src')
            vod["vod_pic"] = pic[0] if pic else ""
            result["list"].append(vod)
        return result

    # 分类列表
    def categoryContent(self, tid, pg, filter, ext):
        result = {"list": [], "page": pg, "pagecount": 10, "limit": 24}
        url = f"{self.homeUrl}/index.php/vod/type/id/{tid}/page/{pg}.html"
        html = self.fetch(url, headers=self.headers).text
        tree = etree.HTML(html)
        vod_list = tree.xpath('//div[contains(@class,"public-list-box")]')
        for item in vod_list:
            vod = {}
            link = item.xpath('.//a[@class="public-list-exp"]/@href')
            if not link:
                continue
            vod["vod_id"] = link[0].split("/id/")[-1].replace(".html", "")
            vod["vod_detail_url"] = self.homeUrl + link[0]
            name = item.xpath('.//a[@class="time-title"]/text()')
            vod["vod_name"] = name[0].strip() if name else ""
            pic = item.xpath('.//img/@data-src')
            vod["vod_pic"] = pic[0] if pic else ""
            result["list"].append(vod)
        return result

    # 搜索影片
    def searchContent(self, key, quick, pg):
        result = {"list": [], "page": pg, "pagecount": 5}
        search_url = f"{self.homeUrl}/index.php/vod/search.html?wd={urllib.parse.quote(key)}"
        html = self.fetch(search_url, headers=self.headers).text
        tree = etree.HTML(html)
        vod_list = tree.xpath('//div[contains(@class,"public-list-box")]')
        for item in vod_list:
            vod = {}
            link = item.xpath('.//a[@class="public-list-exp"]/@href')
            if not link:
                continue
            vod["vod_id"] = link[0].split("/id/")[-1].replace(".html", "")
            vod["vod_detail_url"] = self.homeUrl + link[0]
            name = item.xpath('.//a[@class="time-title"]/text()')
            vod["vod_name"] = name[0].strip() if name else ""
            pic = item.xpath('.//img/@data-src')
            vod["vod_pic"] = pic[0] if pic else ""
            result["list"].append(vod)
        return result

    # 详情页：简介、演员、年份、分集列表
    def detailContent(self, ids):
        vod_id = ids[0]
        detail_url = f"{self.homeUrl}/index.php/vod/detail/id/{vod_id}.html"
        html = self.fetch(detail_url, headers=self.headers).text
        tree = etree.HTML(html)
        vod = {}
        vod["vod_id"] = vod_id
        # 片名
        title = tree.xpath('//h2[@class="player-title-link"]/text()')
        vod["vod_name"] = title[0].strip() if title else ""
        # 封面
        pic = tree.xpath('//div[@class="card-top cf"]//img/@data-src')
        vod["vod_pic"] = pic[0] if pic else ""
        # 年份、地区、类型
        year = tree.xpath('//a[contains(@href,"year")]/text()')
        vod["vod_year"] = year[0] if year else ""
        area = tree.xpath('//a[contains(@href,"area")]/text()')
        vod["vod_area"] = area[0] if area else ""
        type_list = tree.xpath('//a[contains(@href,"class")]/text()')
        vod["vod_type"] = ",".join(type_list) if type_list else ""
        # 演员
        actor_list = tree.xpath('//div[@class="card-top cf"]//a[contains(@href,"actor")]/text()')
        vod["vod_actor"] = ",".join(actor_list) if actor_list else "未知演员"
        # 简介
        desc = tree.xpath('//div[@class="card-text"]/text()')
        vod["vod_content"] = desc[0].strip() if desc else "暂无简介"
        # 分集播放列表
        play_list = []
        episode_items = tree.xpath('//ul[@class="anthology-list-play"]/li')
        for ep in episode_items:
            ep_name = ep.xpath('.//span/text()')
            ep_link = ep.xpath('.//a/@href')
            if ep_name and ep_link:
                play_list.append({
                    "name": ep_name[0].strip(),
                    "url": self.homeUrl + ep_link[0]
                })
        vod["vod_play_from"] = ["TX线路"]
        vod["vod_play_url"] = ["$".join([f"{item['name']}${item['url']}" for item in play_list])]
        return {"list": [vod]}

    # 播放页解析真实m3u8（核心，提取iframe内腾讯视频地址）
    def playerContent(self, link, vodId, playFrom, pg):
        html = self.fetch(link, headers=self.headers).text
        # 提取player_aaaa里的url（腾讯原链接）
        player_data = re.search(r'var player_aaaa=(\{.*?\})', html, re.S)
        real_m3u8 = ""
        if player_data:
            json_str = player_data.group(1)
            data = json.loads(json_str)
            real_m3u8 = data.get("url", "")
        return {
            "parse": 0,
            "url": real_m3u8,
            "header": self.headers,
            "playErr": ""
        }

    def searchable(self):
        return True

    def isVideo(self):
        return True

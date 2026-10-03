# coding=utf-8
#!/usr/bin/python
# ========== 固定头部（所有TVBox爬虫通用，不可修改）==========
import sys
sys.path.append('..')
import json
import urllib.parse
import re
from lxml import etree
from urllib.parse import urljoin
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        # 唯一自定义：站点域名
        self.host = "https://www.china-eae.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    # ==================== 固定函数：首页分类 ====================
    def homeContent(self, filter):
        res = self.fetch(self.host, headers=self.headers)
        html = etree.HTML(res.text)
        class_list = []
        # 提取顶部导航分类
        class_items = html.xpath('//ul[@class="stui-header__menu"]//div[@class="flickity-slider"]/li/a')
        for item in class_items:
            tid_name = item.xpath('./text()')[0].strip()
            tid_url = urljoin(self.host, item.xpath('./@href')[0])
            class_list.append({
                "type_id": tid_url,
                "type_name": tid_name
            })
        return {
            'class': class_list,
            'list': []
        }

    # ==================== 固定函数：分类分页 ====================
    def categoryContent(self, tid, pg, filter, extend):
        # tid是分类完整url，pg页码
        page_url = f"{tid}?page={pg}"
        res = self.fetch(page_url, headers=self.headers)
        html = etree.HTML(res.text)
        vod_items = html.xpath('//ul[@class="stui-vodlist clearfix"]/li')
        vod_list = []
        for li in vod_items:
            vod = self.parse_vod_item(li)
            vod_list.append(vod)
        return {
            'list': vod_list,
            'page': int(pg),
            'pagecount': 10
        }

    # ==================== 固定函数：搜索 ====================
    def searchContent(self, key, quick, pg='1'):
        wd = urllib.parse.quote(key)
        search_url = f"{self.host}/msfw/search/-------------.html?wd={wd}&page={pg}"
        res = self.fetch(search_url, headers=self.headers)
        html = etree.HTML(res.text)
        vod_items = html.xpath('//ul[@class="stui-vodlist clearfix"]/li')
        vod_list = []
        for li in vod_items:
            vod = self.parse_vod_item(li)
            vod_list.append(vod)
        return {
            'list': vod_list,
            'page': int(pg),
            'pagecount': 8,
            'limit': 24,
            'total': int(pg)*24
        }

    # ==================== 自定义工具：解析单条影片列表数据 ====================
    def parse_vod_item(self, li_xpath):
        vod_href = li_xpath.xpath('.//a[@class="stui-vodlist__thumb lazyload"]/@href')[0]
        vod_id = vod_href.replace("/about/","").replace(".html","")
        vod_pic = li_xpath.xpath('.//a[@class="stui-vodlist__thumb lazyload"]/@data-original')[0]
        vod_name = li_xpath.xpath('.//h4[@class="title text-overflow"]/a/@title')[0]
        vod_remarks = li_xpath.xpath('.//span[@class="pic-text text-right"]/text()')[0].strip()
        try:
            vod_actor = li_xpath.xpath('.//p[@class="text text-overflow text-muted hidden-xs"]/text()')[0].strip()
        except:
            vod_actor = ""
        return {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_remarks": vod_remarks,
            "vod_actor": vod_actor
        }

    # ==================== 固定函数：详情页（播放线路，需补全播放地址解析） ====================
    def detailContent(self, ids):
        vod_list = []
        for vid in ids:
            detail_url = f"{self.host}/about/{vid}.html"
            res = self.fetch(detail_url, headers=self.headers)
            html = etree.HTML(res.text)
            vod_name = html.xpath('//h1/@title')[0]
            # 此处需自行解析页面内m3u8/mp4播放线路，示例占位
            play_url = "需解析详情页script内播放地址"
            vod_list.append({
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_play_url": play_url
            })
        return {"list": vod_list}

    # ==================== 固定函数：播放器解析 ====================
    def playerContent(self, flag, url, headers):
        return {
            'parse': 0,
            'url': url,
            'header': headers,
            'playType': 1
        }

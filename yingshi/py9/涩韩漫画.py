# -*- coding: utf-8 -*-
# TVBox爬虫 - 绅士漫画
# 参考：绅士漫画.py（成功脚本）

import sys
import json
import re
import requests
import urllib.parse
from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self): 
        return "绅士漫画"

    def init(self, extend=""):
        self.baseUrl = "https://www.wnacg.com"
        self.session = requests.Session()
        self.ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        self.headers = {
            'User-Agent': self.ua,
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Cookie': 'age_verify=1; popup_agreement=1'
        }

    def get_header(self, url=None):
        h = self.headers.copy()
        h['Referer'] = url if url else self.baseUrl + '/'
        return h

    def homeContent(self, filter):
        classes = [
            {"type_name": "同人/汉化", "type_id": "1"},
            {"type_name": "单行/汉化", "type_id": "9"},
            {"type_name": "短篇/汉化", "type_id": "10"},
            {"type_name": "韩漫/汉化", "type_id": "20"},
            {"type_name": "Cosplay", "type_id": "3"},
            {"type_name": "CG画集", "type_id": "2"},
            {"type_name": "3D漫画", "type_id": "23"},
        ]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("1", "1", None, {})

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        url = f"{self.baseUrl}/albums-index-page-{pg}-cate-{tid}.html"
        return self.parse_list(url, pg)

    def searchContent(self, key, quick, pg="1"):
        key = urllib.parse.quote(key)
        pg = int(pg) if pg else 1
        url = f"{self.baseUrl}/search/?q={key}&f=_all&s=create_time_DESC&p={pg}"
        return self.parse_list(url, pg)

    def parse_list(self, url, pg):
        try:
            r = self.session.get(url, headers=self.get_header(url), timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            box = soup.select_one('.gallary_wrap') or soup.select_one('#classify_container')
            items = box.select('li') if box else soup.select('.gallary_item')
            
            videos = []
            for item in items:
                a = item.select_one('a')
                if not a or "page-" in a.get('href', ''):
                    continue
                
                title = a.get('title') or a.get_text(strip=True)
                title = re.sub(r'^\s*\[[^\]]+\]|\d{4}-\d{2}-\d{2}.*', '', title).strip()
                
                img = item.select_one('img')
                pic = img.get('src') or img.get('data-src') or ""
                if pic.startswith("//"):
                    pic = "https:" + pic
                
                # 提取图片数和日期
                info_text = item.get_text()
                count_m = re.search(r'(\d+)\s*[张張P]', info_text)
                count = count_m.group(1) + "P" if count_m else ""
                date_m = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                date = date_m.group(1) if date_m else ""
                remark = f"{date} {count}".strip()
                
                videos.append({
                    "vod_id": a['href'],
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
            return {"list": videos, "page": pg, "pagecount": 999, "limit": len(videos), "total": 9999}
        except Exception as e:
            print(f"parse_list error: {e}")
            return {"list": []}

    def detailContent(self, ids):
        vid = ids[0]
        url = self.baseUrl + vid if vid.startswith('/') else vid
        try:
            r = self.session.get(url, headers=self.get_header(self.baseUrl), timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            h = soup.select_one('h2') or soup.select_one('h1')
            title = h.get_text(strip=True) if h else "未知标题"
            
            img = soup.select_one('.pic_box img')
            cover = img.get('src') if img else ""
            if cover.startswith("//"):
                cover = "https:" + cover

            # 强制转换为 Gallery 模式
            play_url = vid.replace("index", "gallery")
            if not play_url.startswith("http"):
                play_url = self.baseUrl + play_url
            
            return {"list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_type": "漫画",
                "vod_play_from": "绅士漫画",
                "vod_play_url": f"全集${play_url}"
            }]}
        except Exception as e:
            print(f"detailContent error: {e}")
            return {"list": [{"vod_id": vid, "vod_name": "加载失败", "vod_play_from": "绅士漫画", "vod_play_url": f"全集${url}"}]}

    def playerContent(self, flag, id, vipFlags):
        try:
            r = self.session.get(id, headers=self.get_header(id), timeout=15)
            html = r.text.replace(r'\/', '/')
            
            img_list = []
            # 广谱正则提取 + 缩略图还原
            for m in re.findall(r'((?:https?:|//)[^"\'\s<>\[\]{}]+?\.(?:jpg|png|webp|jpeg))', html, re.I):
                url = "https:" + m if m.startswith("//") else m
                if any(x in url.lower() for x in ['logo', 'icon', 'avatar', 'banner', 'button']):
                    continue
                # 缩略图还原为大图
                if "thumb" in url.lower():
                    url = url.replace("thumb_", "").replace("_thumb", "")
                if url not in img_list:
                    img_list.append(url)
            
            if not img_list:
                return {"parse": 0, "url": "", "msg": "未找到图片"}
            
            # 使用 pics:// 协议，用 && 分隔
            return {
                "parse": 0,
                "playUrl": "",
                "url": "pics://" + "&&".join(img_list),
                "header": json.dumps(self.get_header(id))
            }
        except Exception as e:
            return {"parse": 0, "url": "", "msg": f"Err:{e}"}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None
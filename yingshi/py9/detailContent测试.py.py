
import json
import re
import html
import time
import hashlib
import requests
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

xurl = "https://12gy.com/voddetail/41203.html"  # 网站URL

# 请求头设置，模拟浏览器访问
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

# 请求详情页
detail = requests.get(url=xurl, headers=headerx)
detail.encoding = "utf-8"
res = detail.text
doc = BeautifulSoup(res, "lxml")

# 初始化VOD字典
vod = {}

# ========== 提取视频基本信息 ==========
#视频ID
vod["vod_id"] = xurl

# 标题
title_tag = doc.select_one('h3')
if title_tag:
    vod["vod_name"] = title_tag.get_text()

# 类型
type_info = doc.select_one('.slide-info:-soup-contains(类型)')
if type_info:
    vod["type_name"] = type_info.get_text().replace('类型 :', '').replace('类型:', '').strip()

# 封面图
pic_tag = doc.select_one('.detail-pic img')
if pic_tag:
    vod["vod_pic"] = pic_tag.get('data-src', '') or pic_tag.get('src', '')
    if vod["vod_pic"]:
        vod["vod_pic"] = urljoin(xurl, vod["vod_pic"])

# 备注
remarks_tag = doc.select_one('.cor5')
if remarks_tag:
    vod["vod_remarks"] = remarks_tag.get_text()

# 年份
year_tags = doc.select('.slide-info-remarks')
if len(year_tags) > 1:
    vod["vod_year"] = year_tags[1].get_text()

# 地区
if len(year_tags) > 2:
    vod["vod_area"] = year_tags[2].get_text()

# 导演
director_info = doc.select_one('.slide-info:-soup-contains(导演)')
if director_info:
    director_text = director_info.get_text()
    director_text = director_text.replace('导演 :', '').replace('导演:', '').replace('/', ' ').strip()
    vod["vod_director"] = director_text

# 演员
actor_info = doc.select_one('.slide-info:-soup-contains(演员)')
if actor_info:
    actor_text = actor_info.get_text()
    actor_text = actor_text.replace('演员 :', '').replace('演员:', '').replace('/', ' ').strip()
    vod["vod_actor"] = actor_text

# 简介

content_tag = doc.select_one('.text.cor3')
if content_tag:
    vod["vod_content"] = content_tag.get_text()
    
# ========== 提取播放列表 ==========

# 提取播放源标签
ktabs = []
anthology_tabs = doc.select('.anthology-tab a')
for tab in anthology_tabs:
    tab_text = tab.get_text()
    # 移除末尾数字并清理
    tab_text = re.sub(r'\s*\d+$', '', tab_text).strip()
    ktabs.append(tab_text)
vod["vod_play_from"] = '$$$'.join(ktabs)

# 提取播放列表
klists = []
anthology_lists = doc.select('.anthology-list-play')
for rp in anthology_lists:
    episodes = rp.select('a')
    klist = []
    for episode in episodes:
        episode_name = episode.get_text()
        episode_url = episode.get('href', '')
        if episode_url:
            episode_url = urljoin(xurl, episode_url)
        episode_item = f'{episode_name}${episode_url}'
        klist.append(episode_item)
    # 用#连接同一播放源的剧集
    klists.append('#'.join(klist))

# 用$$$连接不同播放源
vod["vod_play_url"] = '$$$'.join(klists)

result = {
    'list': [vod]
}

# 打印结果
print(json.dumps(result, ensure_ascii=False, indent=2))
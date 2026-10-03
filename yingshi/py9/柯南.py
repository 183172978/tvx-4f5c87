#coding=utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox / 影视仓  Python源脚本
站点: 柯南影视 (www.knvod.com)
模板: MacCMS v10 + ds3
说明: 需手机UA访问，7.1起关闭PC端
"""

import sys
import re
import json
import requests
from urllib.parse import quote
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.site = 'https://www.knvod.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://www.knvod.com/'
        })
        self.cateManual = {
            '电影': '1',
            '连续剧': '2',
            '动漫': '3',
            '综艺': '4'
        }

    def init(self, extend=""):
        pass

    def getName(self):
        return "柯南影视"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {'class': [], 'filters': {}, 'list': [], 'parse': 0, 'jx': 0}
        for k, v in self.cateManual.items():
            result['class'].append({
                'type_id': str(v),
                'type_name': k
            })
        return result

    def homeVideoContent(self):
        videos = []
        try:
            r = self.session.get(self.site, timeout=15)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('div.public-list-box')
            seen = set()
            for item in items.items():
                a = item.find('a.public-list-exp')
                href = a.attr('href') or ''
                vid = self.getVid(href)
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                title = a.attr('title') or ''
                img = item.find('img.lazy')
                pic = img.attr('data-src') or img.attr('src') or ''
                if 'loading' in pic or 'zanwupic' in pic:
                    pic = ''
                note = item.find('.public-list-prb').text().strip()
                if title:
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {'list': videos, 'parse': 0, 'jx': 0}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            if page == 1:
                url = f'{self.site}/vshow/{tid}-----------.html'
            else:
                url = f'{self.site}/vshow/{tid}-----------{page}.html'

            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('div.public-list-box')
            for item in items.items():
                a = item.find('a.public-list-exp')
                href = a.attr('href') or ''
                vid = self.getVid(href)
                if not vid:
                    continue
                title = a.attr('title') or ''
                img = item.find('img.lazy')
                pic = img.attr('data-src') or img.attr('src') or ''
                if 'loading' in pic or 'zanwupic' in pic:
                    pic = ''
                note = item.find('.public-list-prb').text().strip()
                if title:
                    result['list'].append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'categoryContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) > 0 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    def detailContent(self, ids):
        result = {'list': [], 'parse': 0, 'jx': 0}
        vid = ids[0] if ids else ''
        if not vid:
            return result
        try:
            url = f'{self.site}/vdetail/{vid}.html'
            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            doc = pq(r.text)

            # 标题从title标签提取
            title_match = re.search(r'<title>《(.+?)》', r.text)
            title = title_match.group(1) if title_match else ''
            if not title:
                title = doc('h1').text().strip()

            # 图片
            pic = ''
            img = doc('img.lazy1')
            if img.length:
                pic = img.attr('data-src') or img.attr('src') or ''
            if not pic:
                img = doc('.video-cover img')
                if img.length:
                    pic = img.attr('data-src') or img.attr('src') or ''

            # 剧情从meta description提取
            desc = ''
            desc_match = re.search(r'<meta name="description" content="(.+?)"', r.text)
            if desc_match:
                desc = desc_match.group(1)
                # 去掉剧情介绍前缀
                desc = desc.replace('剧情介绍：', '').strip()

            # 从页面文本提取导演/主演（ds3模板中信息在特定div中）
            actor = ''
            director = ''
            # 尝试从页面中提取
            info_text = doc('.slide-info').text()
            if '主演' in info_text:
                actor_match = re.search(r'主演[:：]\s*([^\n]+)', info_text)
                if actor_match:
                    actor = actor_match.group(1).strip()
            if '导演' in info_text:
                director_match = re.search(r'导演[:：]\s*([^\n]+)', info_text)
                if director_match:
                    director = director_match.group(1).strip()

            # 播放线路和集数
            play_from = []
            play_url = []

            # 获取所有线路标签
            tabs = doc('.anthology-tab a')
            panels = doc('.anthology-list-box')

            tab_list = []
            panel_list = []
            for t in tabs.items():
                tab_list.append(t)
            for p in panels.items():
                panel_list.append(p)

            for i, tab in enumerate(tab_list):
                tab_text = tab.text().strip() or f'线路{i+1}'
                # 把末尾的集数用括号括起来，如 "4K48" → "4K (48)"
                m = re.search(r'^(.+?)(\d+)$', tab_text)
                if m:
                    tab_name = f'{m.group(1)} ({m.group(2)})'
                else:
                    tab_name = tab_text
                play_from.append(tab_name)

                episodes = []
                if i < len(panel_list):
                    for link in panel_list[i].find('.anthology-list-play li a').items():
                        ep_name = link.text().strip()
                        ep_href = link.attr('href') or ''
                        if ep_name and ep_href:
                            episodes.append(f'{ep_name}${ep_href}')

                play_url.append('#'.join(episodes))

            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from) if play_from else '',
                'vod_play_url': '$$$'.join(play_url) if play_url else ''
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            play_url = id
            if id and not id.startswith('http'):
                play_url = self.site + id

            # 请求播放页获取iframe
            r = self.session.get(play_url, timeout=15)
            r.encoding = 'utf-8'

            # 提取iframe播放器URL
            iframe_url = ''
            m = re.search(r'<iframe[^>]+src="([^"]+)"', r.text)
            if m:
                iframe_url = m.group(1)
            else:
                m2 = re.search(r"src='([^']+player[^']+)'", r.text)
                if m2:
                    iframe_url = m2.group(1)

            # 如果有iframe，返回iframe地址让TVbox解析
            # 否则返回播放页URL
            if iframe_url:
                result['parse'] = 1
                result['url'] = iframe_url
                result['jx'] = 0
                result['header'] = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'Referer': self.site + '/'
                }
            else:
                result['parse'] = 1
                result['url'] = play_url
                result['jx'] = 0
                result['header'] = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'Referer': self.site + '/'
                }
        except Exception as e:
            print(f'playerContent error: {e}')
            result['parse'] = 1
            result['url'] = id
            result['jx'] = 0
            result['header'] = {}
        return result

    def searchContent(self, key, quick, pg='1'):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            url = f'{self.site}/search/-------------.html?wd={key}'
            if page > 1:
                url += f'&page={page}'

            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            doc = pq(r.text)

            items = doc('.search-box')
            for item in items.items():
                a = item.find('a.public-list-exp')
                href = a.attr('href') or ''
                vid = self.getVid(href)
                if not vid:
                    continue

                img = item.find('img')
                title = (img.attr('alt') or '').replace('封面图', '').strip()
                pic = img.attr('data-src') or img.attr('src') or ''
                if 'loading' in pic or 'zanwupic' in pic:
                    pic = ''
                note = item.find('.public-list-prb').text().strip()
                if title:
                    result['list'].append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'searchContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) > 0 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    def localProxy(self, params):
        return [200, "video/MP2T", {}, ""]

    def getVid(self, url):
        if not url:
            return ''
        m = re.search(r'/vdetail/(\d+)\.html', url)
        if m:
            return m.group(1)
        m = re.search(r'/vplay/(\d+)-', url)
        if m:
            return m.group(1)
        return ''

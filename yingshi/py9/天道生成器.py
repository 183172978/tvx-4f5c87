#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    【遮天世界·天道生成器】                                    ║
║              自动分析源站结构 → 生成爬虫PY文件 → 保存至资料库                  ║
║                                                                              ║
║  用法: python 天道生成器.py <源站URL> [选项]                                  ║
║  示例: python 天道生成器.py https://example.com --realm 2 --name 示例禁区       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import re
import json
import base64
import hashlib
import time
import random
import argparse
import urllib.request
from urllib.parse import urljoin, urlparse, quote
from datetime import datetime
from typing import List, Dict

# ─── 天道配置 ─────────────────────────────────────────────────────────────────
DEFAULT_OUTPUT_DIR = "/mnt/agents/upload"  # 资料库目录
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ─── 境界映射 ─────────────────────────────────────────────────────────────────
REALM_MAP = {
    1: ("轮海境", "简单静态页面，直接正则/CSS提取"),
    2: ("道宫境", "需处理Base64/URL编码"),
    3: ("四极境", "需处理JS变量/JSON嵌套"),
    4: ("化龙境", "需处理iframe嵌套/二次请求"),
    5: ("仙台境", "需处理签名验证/动态Cookie"),
    6: ("大帝境", "需处理AES/RSA/复杂加密"),
}


class HeavenlyDaoGenerator:
    """天道生成器 —— 源站结构分析与爬虫代码自动生成"""

    def __init__(self, url: str, name: str = "", realm: int = 1, output_dir: str = DEFAULT_OUTPUT_DIR):
        self.url = url.rstrip('/')
        self.domain = urlparse(self.url).netloc
        self.name = name or self.domain.replace('.', '_')
        self.realm = realm
        self.realm_name = REALM_MAP.get(realm, ("未知", ""))[0]
        self.output_dir = output_dir
        self.html_cache = {}
        self.detected_patterns = {}
        self.headers = {
            'User-Agent': DEFAULT_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.url + '/',
        }

    def _log(self, msg: str):
        print(f"[天道] {msg}")

    def _fetch(self, url: str, timeout: int = 15) -> str:
        if url in self.html_cache:
            return self.html_cache[url]
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        text = data.decode(enc, errors='ignore')
                        break
                    except:
                        continue
                else:
                    text = data.decode('utf-8', errors='ignore')
                self.html_cache[url] = text
                return text
        except Exception as e:
            self._log(f"获取失败 {url}: {e}")
            return ""

    def detect_site_structure(self) -> Dict:
        self._log(f"开始探测禁区: {self.url}")
        self._log(f"当前境界: {self.realm_name}")
        html = self._fetch(self.url)
        if not html:
            self._log("首页获取失败，使用兜底模式")
            return self._fallback_structure()

        result = {
            'has_categories': False,
            'category_method': '',
            'has_pagination': False,
            'pagination_pattern': '',
            'list_selector': '',
            'detail_pattern': '',
            'play_method': '',
            'encryption_found': [],
        }
        result.update(self._detect_categories(html))
        result.update(self._detect_list_structure(html))
        result['encryption_found'] = self._detect_encryption(html)
        result.update(self._detect_detail_structure(html))
        self.detected_patterns = result
        return result

    def _detect_categories(self, html: str) -> Dict:
        result = {'has_categories': False, 'category_method': 'hardcoded'}
        nav_patterns = [
            (r'<nav[^>]*>.*?</nav>', 'nav标签'),
            (r'<div[^>]*class="[^"]*(?:menu|nav|category)[^"]*"[^>]*>.*?</div>', 'div.menu'),
            (r'<ul[^>]*class="[^"]*(?:menu|nav|category)[^"]*"[^>]*>.*?</ul>', 'ul.menu'),
        ]
        for pattern, desc in nav_patterns:
            m = re.search(pattern, html, re.S | re.I)
            if m:
                nav_html = m.group(0)
                links = re.findall(r'<a[^>]*href="([^"]*(?:type|category|class|list)[^"]*)"[^>]*>(.*?)</a>', nav_html, re.S | re.I)
                if len(links) >= 3:
                    result['has_categories'] = True
                    result['category_method'] = 'regex_nav'
                    result['category_pattern'] = r'<a[^>]*href="([^"]*(?:type|category|class|list)[^"]*)"[^>]*>(.*?)</a>'
                    result['category_sample'] = links[:5]
                    self._log(f"发现导航分类 [{desc}]: {len(links)}个")
                    break

        if not result['has_categories']:
            api_patterns = [
                r'"categories"\s*:\s*(\[.*?\])',
                r'"class"\s*:\s*(\[.*?\])',
                r'"types"\s*:\s*(\[.*?\])',
            ]
            for pat in api_patterns:
                m = re.search(pat, html, re.S)
                if m:
                    try:
                        cats = json.loads(m.group(1))
                        if len(cats) >= 3:
                            result['has_categories'] = True
                            result['category_method'] = 'json_api'
                            result['category_sample'] = cats[:5]
                            self._log(f"发现JSON分类: {len(cats)}个")
                            break
                    except:
                        pass

        if not result['has_categories']:
            css_patterns = [
                ('#category ul li', 'ID选择器'),
                ('.category-list li', 'class选择器'),
                ('.nav-menu li', 'nav-menu'),
                ('header nav a', 'header nav'),
            ]
            for selector, desc in css_patterns:
                test = selector.replace(' ', '.*').replace('#', ' id="').replace('.', ' class="')
                if re.search(test, html, re.I):
                    result['has_categories'] = True
                    result['category_method'] = 'pyquery'
                    result['category_selector'] = selector
                    self._log(f"发现CSS分类结构 [{desc}]: {selector}")
                    break

        if not result['has_categories']:
            self._log("未探测到分类结构，将使用硬编码兜底")
        return result

    def _detect_list_structure(self, html: str) -> Dict:
        result = {'list_selector': '', 'has_pagination': False}
        list_patterns = [
            (r'<div[^>]*class="[^"]*(?:video-list|list|items|content)[^"]*"[^>]*>', 'div.list'),
            (r'<ul[^>]*class="[^"]*(?:video-list|list|items)[^"]*"[^>]*>', 'ul.list'),
            (r'<div[^>]*class="[^"]*(?:row|grid|cards)[^"]*"[^>]*>', 'div.grid'),
        ]
        for pattern, desc in list_patterns:
            if re.search(pattern, html, re.I):
                result['list_selector'] = desc
                self._log(f"发现列表结构: {desc}")
                break

        page_patterns = [
            r'<a[^>]*href="[^"]*page[=/]\d+[^"]*"',
            r'<a[^>]*>\d+</a>\s*<a[^>]*>\d+</a>',
            r'class="[^"]*(?:pagination|page|pages)[^"]*"',
            r'href="[^"]*[-_]\d+\.html"',
        ]
        for pat in page_patterns:
            if re.search(pat, html, re.I):
                result['has_pagination'] = True
                m = re.search(r'href="([^"]*)(?:page[=/]|[-_])(\d+)([^"]*)"', html, re.I)
                if m:
                    result['pagination_pattern'] = f"{m.group(1)}{'{pg}'}{m.group(3)}"
                self._log("发现分页结构")
                break
        return result

    def _detect_encryption(self, html: str) -> List[str]:
        found = []
        if re.search(r'document\.write\(d\([\'"]', html):
            found.append('document.write(d())')
        if re.search(r'base64\.decode|atob\(', html, re.I):
            found.append('Base64')
        if re.search(r'CryptoJS|aes|AES', html):
            found.append('AES/CryptoJS')
        if re.search(r'player_[a-z]+\s*=\s*\{', html):
            found.append('player_json')
        if re.search(r'var\s+hlsUrl\s*=', html):
            found.append('hlsUrl')
        if re.search(r'magnet:\?xt=urn:btih:', html):
            found.append('Magnet')
        if re.search(r'MD5|md5|sign|signature', html, re.I):
            found.append('MD5/Sign')
        if found:
            self._log(f"发现加密/编码方式: {', '.join(found)}")
        return found

    def _detect_detail_structure(self, html: str) -> Dict:
        result = {'detail_pattern': '', 'play_method': ''}
        video_links = re.findall(r'href="([^"]*(?:detail|video|play|v/)[^"]*)"', html, re.I)
        if video_links:
            sample_url = urljoin(self.url, video_links[0])
            self._log(f"尝试探测详情页: {sample_url}")
            detail_html = self._fetch(sample_url)
            if detail_html:
                if re.search(r'player_[a-z]+\s*=\s*\{', detail_html):
                    result['play_method'] = 'player_json'
                elif re.search(r'\.m3u8', detail_html):
                    result['play_method'] = 'direct_m3u8'
                elif re.search(r'<iframe[^>]+src=', detail_html, re.I):
                    result['play_method'] = 'iframe'
                elif re.search(r'magnet:', detail_html):
                    result['play_method'] = 'magnet'
                if result['play_method']:
                    self._log(f"详情页播放方式: {result['play_method']}")
        return result

    def _fallback_structure(self) -> Dict:
        return {
            'has_categories': False,
            'category_method': 'hardcoded',
            'has_pagination': True,
            'pagination_pattern': '/page/{pg}.html',
            'list_selector': 'div.item',
            'detail_pattern': '/video/{vid}.html',
            'play_method': 'unknown',
            'encryption_found': [],
        }

    def generate_spider_code(self) -> str:
        d = self.detected_patterns
        category_code = self._gen_category_code(d)
        list_code = self._gen_list_code(d)
        detail_code = self._gen_detail_code(d)
        search_code = self._gen_search_code()
        play_code = self._gen_play_code()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        code = f'''# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  【遮天世界·禁区档案】                                                        ║
║  禁区名称: {self.name}
║  禁区地址: {self.url}
║  境界等级: {self.realm_name} (Level {self.realm})
║  生成时间: {now}
║  天道生成器自动创建 —— 请根据实际情况微调
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import re
import json
import base64
import hashlib
import time
import random
from urllib.parse import quote, unquote, urljoin, urlparse

sys.path.append('..')
from base.spider import Spider as BaseSpider

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    requests = None


class Spider(BaseSpider):
    """
    【功法阁】{self.name} 爬虫
    境界: {self.realm_name}
    """

    host = "{self.url}"
    headers = {{
        'User-Agent': '{DEFAULT_UA}',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': '{self.url}/',
    }}
    REALM = {self.realm}

    def __init__(self):
        super().__init__()
        self.session = requests.Session() if requests else None
        if self.session:
            self.session.verify = False
            self.session.headers.update(self.headers)
        self._categories_cache = None
        self._debug = True

    def _log(self, msg):
        if self._debug:
            print(f'[{{self.getName()}}] {{msg}}')

    def getName(self):
        return "{self.name}"

    def isVideoFormat(self, url):
        if not url:
            return False
        return '.m3u8' in url or '.mp4' in url or '.ts' in url or url.startswith('magnet:')

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
            except:
                pass

    def localProxy(self, param):
        EMPTY_GIF = b'\\x47\\x49\\x46\\x38\\x39\\x61\\x01\\x00\\x01\\x00\\x80\\x00\\x00\\xff\\xff\\xff\\x00\\x00\\x00!\\xf9\\x04\\x01\\x00\\x00\\x00\\x00,\\x00\\x00\\x00\\x00\\x01\\x00\\x01\\x00\\x00\\x02\\x02D\\x01\\x00;'
        if not param or not param.startswith('http'):
            return [200, 'image/gif', EMPTY_GIF]
        try:
            r = self.session.get(param, headers={{'User-Agent': 'Mozilla/5.0'}}, timeout=15)
            return [200, r.headers.get('Content-Type', 'application/octet-stream'), r.content]
        except:
            return [200, 'image/gif', EMPTY_GIF]

    def _fetch(self, url, referer=None, retries=3, timeout=15):
        if not self.session:
            return ''
        for attempt in range(retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 1.5))
                headers = dict(self.headers)
                if referer:
                    headers['Referer'] = referer
                r = self.session.get(url, headers=headers, timeout=timeout, verify=False)
                r.encoding = 'utf-8'
                if r.status_code == 200:
                    if "Just a moment" in r.text or "cf-browser-verification" in r.text:
                        self._log(f'遭遇Cloudflare: {{url}}')
                        continue
                    return r.text
                elif r.status_code in [403, 429, 503]:
                    self._log(f'被拦截 [{{r.status_code}}]，重试 {{attempt+1}}')
                    continue
            except Exception as e:
                self._log(f'异常 {{e}}，重试 {{attempt+1}}')
        return ''

{category_code}

{list_code}

{detail_code}

{search_code}

{play_code}

    @staticmethod
    def _clean(text):
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', str(text))
        for old, new in {{'&nbsp;': ' ', '&amp;': '&', '&quot;': '"', '&lt;': '<', '&gt;': '>'}}.items():
            text = text.replace(old, new)
        return re.sub(r'\\s+', ' ', text).strip()

    @staticmethod
    def _b64decode(s):
        try:
            padding = 4 - len(s) % 4
            if padding != 4:
                s += '=' * padding
            return base64.b64decode(s).decode('utf-8', errors='ignore')
        except:
            return s

    def liveContent(self, url):
        pass


if __name__ == '__main__':
    spider = Spider()
    print(f"[天道] {{spider.getName()}} 已加载")
    print(f"[天道] 境界: {self.realm_name}")
    print(f"[天道] 请运行 TVBox/影视仓 进行测试")
'''
        return code

    def _gen_category_code(self, d: Dict) -> str:
        method = d.get('category_method', 'hardcoded')
        if method == 'regex_nav':
            return '''    def homeContent(self, filter):
        html = self._fetch(self.host)
        if not html:
            return self._fallback_home()
        classes = []
        seen = set()
        pattern = r'<a[^>]*href="([^"]*(?:type|category|list)[^"]*)"[^>]*>(.*?)</a>'
        for href, name in re.findall(pattern, html, re.S | re.I):
            name = self._clean(name)
            if name and name not in seen and name not in ('首页', '更多', '搜索'):
                seen.add(name)
                id_match = re.search(r'/(?:type|category|list)[/=]?(\\d+)', href)
                tid = id_match.group(1) if id_match else href
                classes.append({'type_name': name, 'type_id': tid})
        if not classes:
            return self._fallback_home()
        self._categories_cache = classes
        videos = self._parse_list(html)
        return {'class': classes, 'list': videos}

    def _fallback_home(self):
        classes = [
            {'type_name': '最新更新', 'type_id': '1'},
            {'type_name': '热门推荐', 'type_id': '2'},
        ]
        return {'class': classes, 'list': []}

    def homeVideoContent(self):
        return self.categoryContent('1', '1', None, None)'''
        elif method == 'json_api':
            return '''    def homeContent(self, filter):
        html = self._fetch(self.host)
        classes = []
        m = re.search(r'"categories"\\s*:\\s*(\\[.*?\\])', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                for item in data:
                    classes.append({
                        'type_name': str(item.get('name', '')),
                        'type_id': str(item.get('id', ''))
                    })
            except:
                pass
        if not classes:
            classes = [{'type_name': '全部', 'type_id': 'all'}]
        self._categories_cache = classes
        videos = self._parse_list(html)
        return {'class': classes, 'list': videos}

    def homeVideoContent(self):
        return self.categoryContent('all', '1', None, None)'''
        elif method == 'pyquery':
            selector = d.get('category_selector', '#category ul li')
            return f'''    def homeContent(self, filter):
        try:
            from pyquery import PyQuery as pq
            html = self._fetch(self.host)
            data = pq(html)
            classes = []
            for item in data('{selector}').items():
                type_id = item('a').attr('href') or ''
                type_name = item.text()
                if type_id and type_name:
                    classes.append({{'type_name': type_name.strip(), 'type_id': type_id.strip()}})
            self._categories_cache = classes
            videos = self._parse_list(html)
            return {{'class': classes, 'list': videos}}
        except Exception as e:
            self._log(f'homeContent error: {{e}}')
            return {{'class': [], 'list': []}}

    def homeVideoContent(self):
        return self.categoryContent('1', '1', None, None)'''
        else:
            return '''    def homeContent(self, filter):
        classes = [
            {'type_name': '最新更新', 'type_id': 'latest'},
            {'type_name': '热门推荐', 'type_id': 'hot'},
            {'type_name': '国产精品', 'type_id': 'guochan'},
            {'type_name': '日韩专区', 'type_id': 'rihan'},
            {'type_name': '欧美大片', 'type_id': 'oumei'},
        ]
        self._categories_cache = classes
        html = self._fetch(self.host)
        videos = self._parse_list(html) if html else []
        return {'class': classes, 'list': videos}

    def homeVideoContent(self):
        if self._categories_cache:
            return self.categoryContent(self._categories_cache[0]['type_id'], '1', None, None)
        return {'list': []}'''

    def _gen_list_code(self, d: Dict) -> str:
        has_page = d.get('has_pagination', True)
        page_code = ""
        if has_page:
            page_code = """
        total_pages = page + 1
        if html:
            page_links = re.findall(r'/type/%s[-_](\\d+)\\.html' % tid, html)
            if page_links:
                total_pages = max(int(p) for p in page_links)"""
        return f'''    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = f"{{self.host}}/type/{{tid}}-{{page}}.html" if page > 1 else f"{{self.host}}/type/{{tid}}.html"
        html = self._fetch(url)
        videos = self._parse_list(html) if html else []
        {page_code}
        return {{
            'list': videos,
            'page': page,
            'pagecount': max(total_pages, page) if 'total_pages' in dir() else page + 1,
            'limit': len(videos),
            'total': 999999
        }}

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        seen = set()
        cards = re.findall(r'(<(?:div|article|li)[^>]*class="[^"]*(?:item|post|video|card)[^"]*"[^>]*>.*?</(?:div|article|li)>)', html, re.S | re.I)
        if not cards:
            cards = re.findall(r'(<div class="thumbnail[^"]*"[^>]*>.*?</div>\\s*</div>)', html, re.S | re.I)
        for card in cards:
            try:
                href_match = re.search(r'href="([^"]+)"', card)
                vod_id = href_match.group(1) if href_match else ''
                title_match = re.search(r'title="([^"]+)"', card)
                vod_name = title_match.group(1) if title_match else ''
                if not vod_name:
                    alt_match = re.search(r'alt="([^"]+)"', card)
                    vod_name = alt_match.group(1) if alt_match else ''
                if not vod_name:
                    h_match = re.search(r'<h[2-6][^>]*>(.*?)</h[2-6]>', card, re.S)
                    if h_match:
                        vod_name = self._clean(h_match.group(1))
                vod_name = self._clean(vod_name)
                pic_match = re.search(r'(?:data-src|data-original|src)="([^"]+)"', card)
                vod_pic = pic_match.group(1) if pic_match else ''
                if vod_pic and not vod_pic.startswith('http'):
                    vod_pic = urljoin(self.host, vod_pic)
                remark_match = re.search(r'<span[^>]*class="[^"]*(?:duration|time|date|label)[^"]*"[^>]*>(.*?)</span>', card, re.I)
                vod_remarks = self._clean(remark_match.group(1)) if remark_match else ''
                if vod_id and vod_name and vod_id not in seen:
                    seen.add(vod_id)
                    videos.append({{
                        'vod_id': vod_id,
                        'vod_name': vod_name,
                        'vod_pic': vod_pic,
                        'vod_remarks': vod_remarks
                    }})
            except Exception:
                continue
        return videos'''

    def _gen_detail_code(self, d: Dict) -> str:
        play_method = d.get('play_method', 'unknown')
        if play_method == 'player_json':
            play_extract = '''        player_match = re.search(r'var\\s+player_[a-z]+\\s*=\\s*({.*?});', html, re.S)
        if player_match:
            try:
                pdata = json.loads(player_match.group(1))
                raw_url = pdata.get('url', '')
                if raw_url:
                    decoded = unquote(raw_url)
                    if decoded.startswith('http'):
                        play_urls.append(('主线路', decoded))
            except:
                pass'''
        elif play_method == 'iframe':
            play_extract = '''        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
        if iframe_match:
            src = iframe_match.group(1)
            if not src.startswith('http'):
                src = urljoin(self.host, src)
            play_urls.append(('嵌套线路', src))'''
        else:
            play_extract = '''        direct = re.findall(r'(https?://[^\\s"\'<>]+\\.(?:m3u8|mp4|flv)(?:\\?[^\\s"\'<>]*)?)', html)
        for link in set(direct):
            play_urls.append(('直连', link))
        for src in set(re.findall(r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html)):
            if any(k in src for k in ['play', 'm3u8', 'embed', 'player']):
                full = urljoin(self.host, src) if not src.startswith('http') else src
                play_urls.append(('嵌套', full))
        for b64 in re.findall(r'["\']([A-Za-z0-9+/]{20,}={0,2})["\']', html):
            try:
                decoded = self._b64decode(b64)
                if decoded.startswith('http') and any(ext in decoded for ext in ['.m3u8', '.mp4']):
                    play_urls.append(('Base64', decoded))
            except:
                pass
        for mag in re.finditer(r'magnet:\\?xt=urn:btih:[A-Za-z0-9]+[^\\s"\'<>]*', html):
            play_urls.append(('BT', mag.group(0)))'''
        return f'''    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        if vid.startswith('http'):
            url = vid
        else:
            url = f"{{self.host}}/detail/{{vid}}.html"
        html = self._fetch(url)
        if not html:
            return {{'list': []}}
        title = ''
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            title = self._clean(m.group(1))
        if not title:
            m = re.search(r'<title>(.*?)</title>', html)
            if m:
                title = self._clean(m.group(1)).split('-')[0]
        cover = ''
        for pat in [
            r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
            r'<img[^>]+data-original="([^"]+)"',
            r'<video[^>]+poster="([^"]+)"',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                cover = m.group(1)
                if cover and not cover.startswith('http'):
                    cover = urljoin(self.host, cover)
                break
        content = ''
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
        if m:
            content = m.group(1)
        play_urls = []
{play_extract}
        if play_urls:
            sources = []
            urls = []
            for label, purl in play_urls:
                sources.append(label)
                urls.append(f'{{label}}${{purl}}')
            vod_play_from = '#'.join(sources)
            vod_play_url = '#'.join(urls)
        else:
            vod_play_from = '默认线路'
            vod_play_url = f'正片${{url}}'
        return {{
            'list': [{{
                'vod_id': vid,
                'vod_name': title or vid,
                'vod_pic': cover,
                'vod_content': content,
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
            }}]
        }}'''

    def _gen_search_code(self) -> str:
        return '''    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        url = f"{self.host}/search?wd={quote(key)}&page={page}"
        html = self._fetch(url)
        videos = self._parse_list(html) if html else []
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1,
            'limit': len(videos),
            'total': 999999
        }'''

    def _gen_play_code(self) -> str:
        return '''    def playerContent(self, flag, id, vipFlags):
        result = {
            'parse': 0,
            'url': id or '',
            'header': {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.host + '/'
            }
        }
        if not id:
            return result
        if any(ext in id for ext in ['.m3u8', '.mp4', '.flv', '.ts']):
            return result
        if id.startswith('magnet:'):
            result['parse'] = 1
            return result
        if 'play' in id or 'player' in id:
            html = self._fetch(id, referer=self.host)
            if html:
                for pat in [
                    r'["\'](https?://[^"\'\s]*\.m3u8[^"\'\s]*)["\']',
                    r'file:\s*["\']([^"\']+)["\']',
                    r'url:\s*["\']([^"\']+)["\']',
                ]:
                    m = re.search(pat, html)
                    if m:
                        result['url'] = m.group(1)
                        result['header']['Referer'] = id
                        return result
        result['parse'] = 1
        return result'''

    def save_to_file(self, code: str) -> str:
        filename = f"{self.name}.py"
        filepath = os.path.join(self.output_dir, filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{self.name}_{counter}.py"
            filepath = os.path.join(self.output_dir, filename)
            counter += 1
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        self._log(f"功法已刻入禁区档案: {filepath}")
        return filepath

    def generate(self) -> str:
        self._log("=" * 60)
        self._log("天道生成器启动")
        self._log("=" * 60)
        self.detect_site_structure()
        code = self.generate_spider_code()
        filepath = self.save_to_file(code)
        self._print_report(filepath)
        return filepath

    def _print_report(self, filepath: str):
        d = self.detected_patterns
        print()
        print("╔" + "═" * 58 + "╗")
        print("║" + "【天道生成报告】".center(54) + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║  禁区名称: {self.name:<42} ║")
        print(f"║  禁区地址: {self.url:<42} ║")
        print(f"║  境界等级: {self.realm_name} (Level {self.realm}){'':<26} ║")
        print(f"║  档案路径: {filepath:<42} ║")
        print("╠" + "═" * 58 + "╣")
        print("║【探测结果】" + " " * 47 + "║")
        print(f"║  分类提取: {d.get('category_method', 'unknown'):<42} ║")
        print(f"║  分页结构: {'有' if d.get('has_pagination') else '无':<42} ║")
        print(f"║  播放方式: {d.get('play_method', 'unknown'):<42} ║")
        enc = d.get('encryption_found', [])
        print(f"║  加密发现: {', '.join(enc) if enc else '无':<42} ║")
        print("╠" + "═" * 58 + "╣")
        print("║【后续操作】" + " " * 47 + "║")
        print("║  1. 打开生成的py文件，根据实际URL规则修改路径" + " " * 12 + "║")
        print("║  2. 测试分类、列表、详情、播放各环节是否正常" + " " * 13 + "║")
        print("║  3. 如有加密方式未识别，手动补充到武器店区域" + " " * 13 + "║")
        print("╚" + "═" * 58 + "╝")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='遮天世界·天道生成器 —— 自动分析源站并生成爬虫PY文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python 天道生成器.py https://example.com
  python 天道生成器.py https://example.com --name 示例禁区 --realm 2
  python 天道生成器.py https://example.com --name 示例禁区 --realm 3 --output /path

境界说明:
  1=轮海境(简单静态)  2=道宫境(Base64编码)  3=四极境(JS变量)
  4=化龙境(iframe)    5=仙台境(签名验证)    6=大帝境(复杂加密)
        """
    )
    parser.add_argument('url', help='源站URL (如 https://example.com)')
    parser.add_argument('--name', '-n', default='', help='禁区名称 (默认使用域名)')
    parser.add_argument('--realm', '-r', type=int, default=1, choices=range(1, 7),
                        help='境界等级 1-6 (默认1)')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR, help=f'输出目录 (默认{DEFAULT_OUTPUT_DIR})')

    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    generator = HeavenlyDaoGenerator(args.url, args.name, args.realm, output_dir)
    generator.generate()


if __name__ == '__main__':
    main()

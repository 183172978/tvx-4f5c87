import sys, re, json, requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from base.spider import Spider
# 忽略 SSL 证书警告
requests.packages.urllib3.disable_warnings()

class Spider(Spider):
    def getName(self): return "74P福利(漫画+小说)"
    
    def init(self, extend=""):
        super().init(extend)
        self.base_url = "https://www.74p.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': '_tj_vid=b1f7ad3c-348c-4640-9a76-6b3af67b4ce8; session=MTc3NzEwMzIxOXxEWDhFQVFMX2dBQUJFQUVRQUFCdV80QUFBd1p6ZEhKcGJtY01DQUFHVlhObGNrbGtCbk4wY21sdVp3d0dBQVEwTlRNeEJuTjBjbWx1Wnd3S0FBaFZjMlZ5VG1GdFpRWnpkSEpwYm1jTURnQU1jMmhoWjNWaE9EZzRNVFk0Qm5OMGNtbHVad3dMQUFsVmMyVnlSM0p2ZFhBR2MzUnlhVzVuREFNQUFUQT18gvrE7G9PtSdGBC4ge-PtnIAbvGbP0wzsxQqZk6UvdEA=; username=shagua888168; uid=4531; UserGroup=0; login=1; _tj_sid=fafbb376-76f8-4714-82d4-e2fe0f807ad5; _tj_slt=1777265108198',
            'Referer': self.base_url + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def destroy(self):
        if hasattr(self, 'session'): self.session.close()

    def fetch(self, url, headers=None):
        req_headers = headers or self.headers.copy()
        try:
            return self.session.get(url, headers=req_headers, timeout=10, verify=False, allow_redirects=True)
        except:
            return None

    def homeContent(self, filter):
        cats = [
            {"type_name": "=== 写真 ===", "type_id": "ignore"},
            {"type_name": "秀人网", "type_id": "xiurenwang"},
            {"type_name": "语画界", "type_id": "yuhuajie"},
            {"type_name": "花漾", "type_id": "huayang"},
            {"type_name": "星颜社", "type_id": "xingyanshe"},
            {"type_name": "嗲囡囡", "type_id": "feilin"},
            {"type_name": "爱蜜社", "type_id": "aimishe"},
            {"type_name": "波萝社", "type_id": "boluoshe"},
            {"type_name": "尤物馆", "type_id": "youwuguan"},
            {"type_name": "优星馆", "type_id": "uxing"},
            {"type_name": "影私荟", "type_id": "wings"},
            {"type_name": "星乐园", "type_id": "xingleyuan"},
            {"type_name": "蜜桃社", "type_id": "miitao"},
            {"type_name": "顽味生活", "type_id": "taste"},
            {"type_name": "魅妍社", "type_id": "meiyanshe"},
            {"type_name": "美媛馆", "type_id": "meiyuanguan"},
            {"type_name": "糖果画报", "type_id": "candyhuabao"},
            {"type_name": "花の颜", "type_id": "huayan"},
            {"type_name": "模范学院", "type_id": "mofanxueyuan"},
            {"type_name": "艺图语", "type_id": "yituyu"},
            {"type_name": "爱美足", "type_id": "mzsock"},
            {"type_name": "=== 漫画 ===", "type_id": "ignore"},
            {"type_name": "日本漫画", "type_id": "comic/category/jp"},
            {"type_name": "韩国漫画", "type_id": "comic/category/kr"},
            {"type_name": "=== 小说 ===", "type_id": "ignore"},
            {"type_name": "都市", "type_id": "novel/category/Urban"},
            {"type_name": "校园", "type_id": "novel/category/campus"},
            {"type_name": "乱伦", "type_id": "novel/category/Incestuous"},
            {"type_name": "玄幻", "type_id": "novel/category/Xuanhuan"},
            {"type_name": "系统", "type_id": "novel/category/Goldfinger"},
            {"type_name": "穿越", "type_id": "novel/category/traverse"},
            {"type_name": "武侠", "type_id": "novel/category/Wuxia"},
            {"type_name": "奇幻", "type_id": "novel/category/Fantasy"},
            {"type_name": "乡村", "type_id": "novel/category/Rural"},
            {"type_name": "历史", "type_id": "novel/category/Historical"},
            {"type_name": "明星", "type_id": "novel/category/Celebrity"},
            {"type_name": "异能", "type_id": "novel/category/Superpower"},
            {"type_name": "科幻", "type_id": "novel/category/Science"},
            {"type_name": "同人", "type_id": "novel/category/Fan"}
        ]
        return {'class': [c for c in cats if c['type_id'] != 'ignore']}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        url = f"{self.base_url}/{tid}/page/{pg}"
        return self._get_post_list(url, pg)

    def _get_post_list(self, url, pg):
        resp = self.fetch(url)
        vlist = []
        if resp and resp.status_code == 200:
            resp.encoding = 'utf-8'
            html = resp.text
            
            list_block = html
            main_block = re.search(r'(?:id="index_ajax_list"|class="site-main")[^>]*>(.*?)<(?:footer|aside)', html, re.S)
            if main_block: list_block = main_block.group(1)
            
            items = re.findall(r'<li[^>]*>(.*?)</li>', list_block, re.S)
            for item in items:
                href_match = re.search(r'href=["\']([^"\']+)["\']', item)
                if not href_match: continue
                href = href_match.group(1)
                
                if any(x in href for x in ['.css', '.js', 'templates/', 'wp-includes']): continue
                img_match = re.search(r'data-original=["\']([^"\']+)["\']', item)
                if not img_match: img_match = re.search(r'src=["\']([^"\']+)["\']', item)
                pic = img_match.group(1) if img_match else ""
                
                if not pic: pic = "https://www.74p.net/static/images/cover.png"
                
                title_match = re.search(r'title=["\']([^"\']+)["\']', item)
                name = title_match.group(1) if title_match else re.sub(r'<[^>]+>', '', item).strip().split('\n')[0]
                if name.startswith('.') or '{' in name or len(name) > 100: continue
                
                if href.startswith('//'): href = 'https:' + href
                elif href.startswith('/'): href = self.base_url + href
                vlist.append({
                    'vod_id': href,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': '点击查看',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        
        return {'list': vlist, 'page': pg, 'pagecount': pg + 1 if len(vlist) >= 15 else pg, 'limit': 20, 'total': 9999}

    def searchContent(self, key, quick, pg=1):
        search_path = f"/search/{key}"
        headers = self.headers.copy()
        if "漫画" in key: headers['Referer'] = f"{self.base_url}/comic"
        else: headers['Referer'] = f"{self.base_url}/novel"
        if int(pg) > 1: url = f"{self.base_url}{search_path}/page/{pg}"
        else: url = f"{self.base_url}{search_path}"
        return self._get_post_list(url, int(pg))

    # ==========================
    # 详情页：自动区分 漫画 / 小说
    # ==========================
    def detailContent(self, ids):
        url = ids[0]
        resp = self.fetch(url)
        if not resp: return {'list': []}
        resp.encoding = 'utf-8'
        html = resp.text
        
        is_novel = '/novel/' in url
        vod = {
            'vod_id': url,
            'vod_name': '',
            'vod_pic': '',
            'type_name': '小说' if is_novel else '漫画',
            'vod_content': '',
            'vod_play_from': '74P小说' if is_novel else '74P漫画',
            'vod_play_url': ''
        }

        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if h1: vod['vod_name'] = h1.group(1)
        
        desc_match = re.search(r'<div class="entry-content"[^>]*>(.*?)</div>', html, re.S)
        if desc_match: 
            clean_desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            vod['vod_content'] = clean_desc[:200]
        
        play_list = []
        chapter_links = re.findall(r'<a[^>]+href=["\']([^"\']*/(?:comic|novel)/chapter/[^"\']+)["\'][^>]*>(.*?)</a>', html)
        
        if chapter_links:
            for href, name in chapter_links:
                if href.startswith('//'): href = 'https:' + href
                elif href.startswith('/'): href = self.base_url + href
                name = name.strip()
                play_list.append(f"{name}${href}")
        else:
            play_list.append(f"在线观看${url}")

        vod['vod_play_url'] = "#".join(play_list)
        return {'list': [vod]}

    # ==========================
    # 播放核心：漫画用pics，小说用novel
    # ==========================
    def playerContent(self, flag, id, vipFlags):
        # 自动判断：小说 / 漫画
        if '/novel/' in id:
            return self._player_novel(flag, id)
        else:
            return self._player_comic(flag, id)

    # ==========================
    # 漫画阅读器（原图不变）
    # ==========================
    def _player_comic(self, flag, id):
        images = self._scrape_all_images(id)
        novel_data = "&&".join(images)
        return {
            "parse": 0,
            "playUrl": "",
            "url": f'pics://{novel_data}',
            "header": ""
        }

    # ==========================
    # 小说阅读器（标准模板格式）
    # ==========================
    def _player_novel(self, flag, pid):
        try:
            url = pid if pid.startswith('http') else self.base_url + pid
            resp = self.fetch(url)
            if not resp: raise Exception("请求失败")
            resp.encoding = 'utf-8'
            html = resp.text

            # 标题
            title = ""
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html)
            if title_match:
                title = title_match.group(1).strip()

            # 正文提取
            content = ""
            content_match = re.search(r'(?:class="entry-content|id="content")[^>]*>(.*?)</div', html, re.S)
            if content_match:
                content_html = content_match.group(1)
                content_html = re.sub(r'<br\s*/?>', '\n', content_html)
                content_html = re.sub(r'<p[^>]*>', '\n', content_html)
                content_html = re.sub(r'<[^>]+>', '', content_html)
                lines = [line.strip() for line in content_html.splitlines() if line.strip()]
                content = "\n".join(lines)

            if not content:
                content = "正文获取失败"

            data = {"title": title, "content": content}
            return {
                "parse": 0,
                "playUrl": "",
                "url": "novel://" + json.dumps(data, ensure_ascii=False),
                "header": ""
            }
        except Exception as e:
            return {
                "parse": 0,
                "playUrl": "",
                "url": "novel://" + json.dumps({"title": "错误", "content": str(e)}, ensure_ascii=False),
                "header": ""
            }

    # ==========================
    # 工具：翻页抓取所有图片
    # ==========================
    def _scrape_all_images(self, url):
        images = []
        visited = set()
        current_url = url
        page = 1
        max_pages = 50 
        
        while page <= max_pages:
            if current_url in visited: break
            visited.add(current_url)
            
            resp = self.fetch(current_url)
            if not resp or resp.status_code != 200: break
            resp.encoding = 'utf-8'
            html = resp.text
            
            content_match = re.search(r'(?:id="content"|class="entry-content"|class="single-content")[^>]*>(.*?)<(?:div class="related|footer|section)', html, re.S)
            content_html = content_match.group(1) if content_match else html
            
            img_matches = re.findall(r'<img[^>]+(?:src|data-original|data-src)=["\']([^"\']+)["\']', content_html)
            for src in img_matches:
                if any(x in src.lower() for x in ['.gif', '.svg', 'logo', 'avatar', 'icon']): continue
                if src.startswith('//'): src = 'https:' + src
                elif src.startswith('/'): src = self.base_url + src
                if src not in images:
                    images.append(src)
            
            next_url = None
            next_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:下一页|Next|»)', html, re.I)
            if not next_match:
                next_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*next[^"\']*["\']', html, re.I)
            
            if not next_match and '/comic/chapter/' not in current_url and 'page' in current_url:
                 base = current_url.rsplit('/', 1)[0]
                 candidate = f"{base}/{page+1}"
                 next_url = candidate
            elif next_match:
                href = next_match.group(1)
                if href.startswith('//'): next_url = 'https:' + href
                elif href.startswith('/'): next_url = self.base_url + href
                else: next_url = href
            
            if not next_url: break
            current_url = next_url
            page += 1
            
        return images

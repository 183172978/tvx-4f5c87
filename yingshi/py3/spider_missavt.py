import sys, re, json, requests, html as htmlmod, base64
from base.spider import Spider
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
requests.packages.urllib3.disable_warnings()


class Spider(Spider):
    def getName(self):
        return "MissAVt"

    def init(self, extend=""):
        super().init(extend)
        self.domains = [
            "https://both.hhfvdqsw.cc",
            "https://missavt23.com",
            "https://missavt.com",
        ]
        self.site_url = self.domains[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.site_url + "/",
        }
        self.sess = requests.Session()
        self.page_size = 24
        self._categories = None
        # AES 解密参数
        self._aes_key = b'f5d965df75336270'
        self._aes_iv = b'97b60394abc2fbe1'

    # ── 域名切换 ──────────────────────────────────────────────
    def _try_domains(self, path):
        """依次尝试多个域名，返回第一个成功的 HTML"""
        import urllib.request, urllib.parse, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        encoded_path = urllib.parse.quote(path, safe='/:?&=#')
        for domain in self.domains:
            url = domain + encoded_path
            req = urllib.request.Request(url, headers={
                **self.headers,
                "Referer": domain + "/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })
            try:
                with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                    if resp.status == 200:
                        html = resp.read().decode("utf-8", errors="replace")
                        if len(html) > 500:
                            self.site_url = domain
                            self.headers["Referer"] = domain + "/"
                            return html
            except Exception:
                continue
        return ""

    def _fetch(self, path):
        import urllib.request, urllib.parse, ssl
        encoded_path = urllib.parse.quote(path, safe='/:?&=#')
        url = self.site_url + encoded_path
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            **self.headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        try:
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return self._try_domains(path)

    def _decrypt_pic(self, pic_url):
        """解密 AES 加密的缩略图，返回 base64 data URL"""
        if not pic_url:
            return pic_url
        try:
            resp = self.sess.get(pic_url, headers=self.headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return pic_url
            encrypted = resp.content
            if len(encrypted) < 16:
                return pic_url
            # AES-CBC 解密
            cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_iv)
            decrypted = cipher.decrypt(encrypted)
            decrypted = unpad(decrypted, AES.block_size)
            # 转为 base64 data URL
            b64 = base64.b64encode(decrypted).decode()
            return "data:image/jpeg;base64," + b64
        except Exception:
            return pic_url

    # ── 分类列表 ──────────────────────────────────────────────
    def _get_categories(self):
        if self._categories:
            return self._categories
        cats = [
            {"type_name": "有码AV",       "type_id": "censored"},
            {"type_name": "中文字幕",      "type_id": "chinese-subtitle"},
            {"type_name": "人妻熟女",      "type_id": "renqishunv"},
            {"type_name": "制服诱惑",      "type_id": "zhifuyouhuo"},
            {"type_name": "调教SM",        "type_id": "tiaojiaoSM"},
            {"type_name": "家庭乱伦",      "type_id": "jiatingluanlun"},
            {"type_name": "国产传媒",      "type_id": "domestic-media"},
            {"type_name": "麻豆传媒",      "type_id": "madou"},
            {"type_name": "swag",          "type_id": "swag"},
            {"type_name": "糖心vlog",      "type_id": "sweet-heart-vlog"},
            {"type_name": "ed mosaic",     "type_id": "ed-mosaic"},
            {"type_name": "抖阴",          "type_id": "douyin"},
            {"type_name": "91制片厂",      "type_id": "91-studio"},
            {"type_name": "兔子先生",      "type_id": "mr-rabbit"},
            {"type_name": "杏吧探花",      "type_id": "xingbatanhua"},
            {"type_name": "无码流出",      "type_id": "uncensored-leak"},
            {"type_name": "FC2",           "type_id": "fc2"},
            {"type_name": "东京热",        "type_id": "tokyohot"},
            {"type_name": "人妻斩",        "type_id": "marriedslash"},
            {"type_name": "HEYZO",         "type_id": "heyzo"},
            {"type_name": "无码破解",      "type_id": "reducing-mosaic"},
            {"type_name": "10musume",      "type_id": "10musume"},
            {"type_name": "pacopacomama",  "type_id": "pacopacomama"},
            {"type_name": "xxx-av",        "type_id": "xxx-av"},
            {"type_name": "Caribbeancompr","type_id": "Caribbeancompr"},
            {"type_name": "Caribbeancom",  "type_id": "Caribbeancom"},
            {"type_name": "一本道",        "type_id": "1pondo"},
            {"type_name": "素人",          "type_id": "amateur"},
            {"type_name": "SIRO",          "type_id": "SIRO"},
            {"type_name": "lulu",          "type_id": "luxu"},
            {"type_name": "gana",          "type_id": "gana"},
            {"type_name": "PRESTIGE PREMIUM","type_id": "PRESTIGE-PREMIUM"},
            {"type_name": "S-CUTE",        "type_id": "S-CUTE"},
            {"type_name": "ARA",           "type_id": "ARA"},
        ]
        self._categories = cats
        return cats

    # ── HTML 解析 ─────────────────────────────────────────────
    @staticmethod
    def _parse_video_items(html_text):
        """从列表页提取视频（列表页 data-url 直接带 m3u8）"""
        results = []
        # 按 video-item 块分割
        blocks = re.split(r'<div\s+class="video-item">', html_text)
        for block in blocks[1:]:  # 跳过第一个（非视频内容）
            # m3u8 URL from data-url on .poster div
            m3u8 = ""
            du = re.search(r'data-url="(https?://[^"]+\.m3u8[^"]*)"', block)
            if du:
                m3u8 = du.group(1)

            # 封面图 + alt 标题
            thumb = ""
            alt_title = ""
            img = re.search(r'<img[^>]*data-src="(https?://[^"]+)"[^>]*alt="([^"]*)"', block, re.DOTALL)
            if not img:
                img = re.search(r'<img[^>]*alt="([^"]*)"[^>]*data-src="(https?://[^"]+)"', block, re.DOTALL)
                if img:
                    alt_title = img.group(1)
                    thumb = img.group(2)
            if img and not thumb:
                thumb = img.group(1)
                alt_title = img.group(2)

            # 番号/链接
            link = re.search(r'href="/watch/([^/]+)/"', block)
            vid = link.group(1) if link else ""

            # 时长
            duration = ""
            dur = re.search(r'(\d+:\d+:\d+)', block)
            if dur:
                duration = dur.group(1)

            if vid:
                results.append({
                    "vod_id": vid,
                    "vod_pic": thumb,
                    "vod_remarks": duration,
                    "_m3u8": m3u8,
                    "_alt_title": alt_title,
                })

        # 标题提取：优先匹配 line-clamp 的 <a> 标签（分类页）
        title_map = {}
        for m in re.finditer(
            r'<a\s[^>]*class="[^"]*line-clamp[^"]*"[^>]*href="/watch/([^/]+)/"[^>]*>(.*?)</a>',
            html_text, re.DOTALL
        ):
            vid = m.group(1)
            title = htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(2)).strip())
            if title:
                title_map[vid] = title

        # 合并标题：优先 line-clamp，其次 alt，最后 vid
        for item in results:
            vid = item["vod_id"]
            if vid in title_map:
                item["vod_name"] = title_map[vid]
            elif item.get("_alt_title"):
                item["vod_name"] = htmlmod.unescape(item["_alt_title"]).strip()
            else:
                item["vod_name"] = vid.upper()

        return results

    @staticmethod
    def _parse_pagination(html_text):
        """提取分页信息，优先读 data-last-page 属性"""
        # 优先：data-last-page="1072"
        m = re.search(r'data-last-page="(\d+)"', html_text)
        if m:
            return int(m.group(1))
        # fallback：从 href 推算
        pages = re.findall(r'href="[^"]*/(\d+)/?"', html_text)
        max_page = 1
        for p in pages:
            try:
                n = int(p)
                if 2 <= n <= 9999:
                    max_page = max(max_page, n)
            except ValueError:
                pass
        next_match = re.search(r'rel="next"\s+href="[^"]*/(\d+)/?"', html_text)
        if next_match:
            max_page = max(max_page, int(next_match.group(1)) + 1)
        return max_page

    # ── TVBox 接口 ────────────────────────────────────────────
    def homeContent(self, filter):
        return {"class": self._get_categories(), "header": self.headers}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        path = f"/category/{tid}/" if pg == 1 else f"/category/{tid}/{pg}/"

        # 首次用备用域名探测
        html_text = self._try_domains(path) if pg == 1 else self._fetch(path)
        if not html_text:
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.page_size, "total": 0}

        items = self._parse_video_items(html_text)
        total_page = self._parse_pagination(html_text)

        video_list = []
        for item in items:
            video_list.append({
                "vod_id": item["vod_id"],
                "vod_name": item["vod_name"],
                "vod_pic": self._decrypt_pic(item["vod_pic"]),
                "vod_remarks": item["vod_remarks"],
            })

        return {
            "list": video_list,
            "page": pg,
            "pagecount": total_page,
            "limit": self.page_size,
            "total": 9999,
            "header": self.headers,
        }

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        if not vid:
            return {"list": []}

        m3u8 = ""
        title = ""
        thumb = ""

        # 优先从 watch 页获取完整信息
        html_text = self._fetch(f"/watch/{vid}/")
        if html_text:
            # 标题
            t = re.search(r'<title>([^<]+)</title>', html_text)
            if t:
                full_title = htmlmod.unescape(t.group(1)).strip()
                # 去掉站点后缀
                title = re.split(r'\s*[-–|]\s*MissAVt\s*$', full_title)[0].strip()
            # 封面
            og = re.search(r'property="og:image"\s+content="([^"]+)"', html_text)
            if og:
                thumb = og.group(1)
            else:
                tn = re.search(r'"thumbnailUrl"\s*:\s*"(https?://[^"]+)"', html_text)
                if tn:
                    thumb = tn.group(1)
            # m3u8（从 watch 页可能不直接有，需要 embed）
            src = re.search(r'(https?://[^"\'"]+\.m3u8[^"\'"]*)', html_text)
            if src:
                m3u8 = src.group(1)

        # 备用：从 embed 页拿 m3u8 和标题
        if not m3u8:
            embed_html = self._fetch(f"/embed/{vid}/")
            if embed_html:
                src = re.search(r'<source\s+src="(https?://[^"]+\.m3u8[^"]*)"', embed_html)
                if src:
                    m3u8 = src.group(1)
                if not title:
                    t = re.search(r'<title>([^<]+)</title>', embed_html)
                    if t:
                        full_title = htmlmod.unescape(t.group(1)).strip()
                        title = re.split(r'\s*[-–|]\s*在线观看\s*$', full_title)[0].strip()

        if not m3u8:
            return {"list": []}

        if not title:
            title = vid.upper()

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": thumb,
                "vod_play_from": "MissAVt",
                "vod_play_url": title + "$" + m3u8,
            }],
            "header": self.headers,
        }

    def searchContent(self, key, quick, pg=1):
        pg = int(pg) if str(pg).isdigit() else 1
        path = f"/search/{key}/" if pg == 1 else f"/search/{key}/{pg}/"
        html_text = self._try_domains(path) if pg == 1 else self._fetch(path)
        if not html_text:
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.page_size, "total": 0}

        items = self._parse_video_items(html_text)
        total_page = self._parse_pagination(html_text)

        video_list = [{
            "vod_id": item["vod_id"],
            "vod_name": item["vod_name"],
            "vod_pic": self._decrypt_pic(item["vod_pic"]),
            "vod_remarks": item["vod_remarks"],
        } for item in items]

        return {
            "list": video_list,
            "page": pg,
            "pagecount": total_page,
            "limit": self.page_size,
            "total": 9999,
            "header": self.headers,
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 0, "url": "", "header": {}}
        play_url = id.split("$")[1] if "$" in id else id
        return {
            "parse": 0,
            "url": play_url,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.site_url + "/",
            },
        }

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

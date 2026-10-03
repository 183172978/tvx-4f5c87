#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
肉视频 rou.video
- 列表/详情：沿用原版稳定逻辑
- 播放：区分两种 CDN
  1) 正文即 #EXTM3U（index.jpg）→ 改扩展名为 .m3u8 直通
  2) PNG 壳 + roUd 块 → localProxy 解包
     roUd[0]==1 zlib→m3u8；roUd[0]==0 → TS 分片
"""
import re
import json
import base64
import html as html_lib
import urllib.request
import urllib.parse
import http.cookiejar
import gzip
import zlib
import ssl
import struct

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"
        def getProxyUrl(self, local=True):
            return "http://127.0.0.1:9978/proxy?do=py"


class Spider(SpiderBase):
    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.navUrls = ["https://x99dh.cc", "https://x99dh.one"]
        self.defaultHost = "https://rou.video"
        self.fallbackHosts = [
            "https://rou.video",
            "https://www.rou.video",
            "https://rouvb1.xyz",
            "https://rouva8.xyz",
            "https://rouva7.xyz",
            "https://rouva5.xyz",
            "https://rouva3.xyz",
        ]
        self.siteUrl = self.defaultHost
        self.siteName = "rouAV"
        self._ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        self.options = {}

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
        )

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        cached = self.getCache("rouav_dynamic_site_url")
        if cached and str(cached).startswith("http"):
            self.siteUrl = str(cached).strip().rstrip("/")
        else:
            self._refresh_site_url()
        return True

    def getName(self):
        return "肉视频"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(
            k in low
            for k in (
                ".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd",
                "index.png", "index.jpg", "index.m3u8", "/hls/", "type=rouhls", "type=routs",
            )
        )

    def manualVideoCheck(self):
        return False

    # ---------- 站点 ----------
    def _is_alive(self, base):
        try:
            chk = self._fetch(base + "/v?order=createdAt", check_host=False)
            text = chk.get("text") or ""
            return (
                chk.get("code") == 200
                and len(text) > 500
                and ("__NEXT_DATA__" in text or "videos" in text)
            )
        except Exception:
            return False

    def _refresh_site_url(self):
        headers = {
            "User-Agent": self._ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        for nav in self.navUrls:
            text = ""
            try:
                req = urllib.request.Request(nav, headers=headers)
                with self.opener.open(req, timeout=8) as resp:
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    text = raw.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if not text:
                continue
            for h in re.findall(r"https?://(?:www\.)?rou[a-z0-9.-]+", text, re.I):
                try:
                    p = urllib.parse.urlparse(h)
                    base = "%s://%s" % (p.scheme, p.netloc)
                    if self._is_alive(base):
                        self.siteUrl = base
                        self.setCache("rouav_dynamic_site_url", base)
                        return True
                except Exception:
                    continue
        for base in self.fallbackHosts:
            if self._is_alive(base):
                self.siteUrl = base
                self.setCache("rouav_dynamic_site_url", base)
                return True
        self.siteUrl = self.defaultHost
        return False

    def _fetch(self, target_url, referer="", check_host=True):
        if not target_url:
            return {"code": 0, "text": "", "err": "", "final_url": "", "body": b""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url

        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/v"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Origin": self.siteUrl,
        }
        domain_retried = False
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=15) as resp:
                    code = resp.getcode()
                    final_url = resp.geturl()
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        try:
                            raw = gzip.decompress(raw)
                        except Exception:
                            pass
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            try:
                                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                            except Exception:
                                pass
                    try:
                        text = raw.decode("utf-8")
                    except Exception:
                        text = raw.decode("latin1", errors="ignore")
                    return {
                        "code": code,
                        "text": text,
                        "err": "",
                        "final_url": final_url,
                        "body": raw if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8", "ignore"),
                    }
            except urllib.error.HTTPError as e:
                if e.code in (404, 451, 500, 502, 503) and check_host and not domain_retried:
                    old = urllib.parse.urlparse(self.siteUrl).netloc
                    self.delCache("rouav_dynamic_site_url")
                    if self._refresh_site_url():
                        domain_retried = True
                        target_url = target_url.replace(old, urllib.parse.urlparse(self.siteUrl).netloc)
                        continue
                if e.code in (451, 403, 429) and attempt == 0:
                    continue
                try:
                    err_raw = e.read()
                except Exception:
                    err_raw = b""
                return {
                    "code": e.code,
                    "text": err_raw.decode("utf-8", "ignore"),
                    "err": str(e),
                    "final_url": target_url,
                    "body": err_raw,
                }
            except Exception as e:
                if check_host and not domain_retried:
                    old = urllib.parse.urlparse(self.siteUrl).netloc
                    self.delCache("rouav_dynamic_site_url")
                    if self._refresh_site_url():
                        domain_retried = True
                        target_url = target_url.replace(old, urllib.parse.urlparse(self.siteUrl).netloc)
                        continue
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "err": str(e), "final_url": target_url, "body": b""}
        return {"code": -1, "text": "", "err": "fail", "final_url": target_url, "body": b""}

    def _fetch_bin(self, url, referer=""):
        """只取字节，用于解包"""
        if url.startswith("/"):
            url = self.siteUrl + url
        headers = {
            "User-Agent": self._ua,
            "Referer": referer or (self.siteUrl + "/"),
            "Accept": "*/*",
            "Origin": self.siteUrl,
            "Connection": "keep-alive",
        }
        req = urllib.request.Request(url, headers=headers)
        with self.opener.open(req, timeout=20) as resp:
            raw = resp.read()
            enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
            if raw[:2] == b"\x1f\x8b" or enc == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return resp.geturl(), raw

    # ---------- roUd 解包 ----------
    @staticmethod
    def _png_roud(body):
        if not body or len(body) < 8 or body[:4] != b"\x89PNG":
            return None
        pos = 8
        while pos + 8 <= len(body):
            length = struct.unpack(">I", body[pos : pos + 4])[0]
            ctype = body[pos + 4 : pos + 8]
            data = body[pos + 8 : pos + 8 + length]
            if ctype == b"roUd":
                return data
            pos += 12 + length
            if ctype == b"IEND":
                break
        return None

    def _unwrap(self, body):
        """返回 (kind, data) kind=m3u8|ts|raw"""
        if not body:
            return "raw", body
        if body.startswith(b"#EXT"):
            return "m3u8", body
        if body[:1] == b"G" or (len(body) and body[0] == 0x47):
            return "ts", body
        roud = self._png_roud(body)
        if not roud or len(roud) < 2:
            return "raw", body
        flag, payload = roud[0], roud[1:]
        if flag == 1:
            try:
                return "m3u8", zlib.decompress(payload)
            except Exception:
                try:
                    return "m3u8", zlib.decompress(payload, -zlib.MAX_WBITS)
                except Exception:
                    return "raw", body
        if flag == 0:
            return "ts", payload
        try:
            return "m3u8", zlib.decompress(payload)
        except Exception:
            if payload and payload[0] == 0x47:
                return "ts", payload
            return "raw", body

    @staticmethod
    def _to_m3u8_name(url):
        if not url:
            return url
        u = str(url)
        for a, b in (
            ("index.jpg", "index.m3u8"),
            ("index.png", "index.m3u8"),
            ("index.jpeg", "index.m3u8"),
        ):
            u = u.replace(a, b)
        return u

    def _proxy_link(self, type_name, target_url):
        """
        标准 TVBox 代理：getProxyUrl() 已含 do=py，只追加 url 与 type
        播放器请求后由框架回调 localProxy(param)
        """
        try:
            base = self.getProxyUrl(True)
        except Exception:
            try:
                base = self.getProxyUrl()
            except Exception:
                base = "http://127.0.0.1:9978/proxy?do=py"
        if not base:
            base = "http://127.0.0.1:9978/proxy?do=py"
        sep = "&" if "?" in base else "?"
        return "%s%surl=%s&type=%s" % (
            base,
            sep,
            urllib.parse.quote(target_url, safe=""),
            type_name,
        )

    # ---------- 列表 ----------
    def homeContent(self, filter):
        result = {
            "class": [
                {"type_name": "🔥 最新发布", "type_id": "/v?order=createdAt"},
                {"type_name": "👑 最多播放", "type_id": "/v?order=viewCount"},
                {"type_name": "❤️ 最受喜爱", "type_id": "/v?order=likeCount"},
                {"type_name": "🤖 AI成人短剧", "type_id": "/t/AI短劇"},
                {"type_name": "📱 自拍流出", "type_id": "/t/自拍流出"},
                {"type_name": "🕵️ 探花精选", "type_id": "/t/探花"},
                {"type_name": "🇨🇳 国产AV", "type_id": "/t/國產AV"},
                {"type_name": "🇯🇵 日本精选", "type_id": "/t/日本"},
                {"type_name": "🀄 中文字幕", "type_id": "/t/中文字幕"},
                {"type_name": "麻豆传媒", "type_id": "/t/麻豆傳媒"},
                {"type_name": "糖心Vlog", "type_id": "/t/糖心Vlog"},
                {"type_name": "蜜桃传媒", "type_id": "/t/蜜桃影像傳媒"},
                {"type_name": "香蕉视频", "type_id": "/t/香蕉視頻傳媒"},
                {"type_name": "星空无限", "type_id": "/t/星空無限傳媒"},
                {"type_name": "天美传媒", "type_id": "/t/天美傳媒"},
                {"type_name": "OnlyFans", "type_id": "/t/OnlyFans"},
                {"type_name": "巨乳", "type_id": "/t/巨乳"},
                {"type_name": "人妻", "type_id": "/t/人妻"},
                {"type_name": "丝袜", "type_id": "/t/絲襪"},
                {"type_name": "熟女", "type_id": "/t/熟女"},
                {"type_name": "美少女", "type_id": "/t/美少女"},
                {"type_name": "中出", "type_id": "/t/中出"},
                {"type_name": "口交", "type_id": "/t/口交"},
                {"type_name": "痴女", "type_id": "/t/痴女"},
                {"type_name": "多人运动", "type_id": "/t/多人運動"},
                {"type_name": "NTR", "type_id": "/t/NTR"},
            ]
        }
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        res = self.categoryContent("/v?order=createdAt", "1", False, {})
        return {"list": (res.get("list") or [])[:20]}

    def _parse_vod_list(self, html_text):
        m_next = re.search(
            r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>([\s\S]*?)</script>',
            html_text or "",
            re.I,
        )
        if m_next:
            try:
                data_obj = json.loads(m_next.group(1).strip())
                video_list = data_obj.get("props", {}).get("pageProps", {}).get("videos", [])
                cards = []
                for v in video_list:
                    vid = v.get("id") or v.get("vid") or ""
                    if not vid:
                        continue
                    name = v.get("nameZh") or v.get("name") or "肉视频"
                    pic = v.get("coverImageUrl") or ""
                    dur_sec = v.get("duration") or 0
                    dur_str = "HD"
                    if dur_sec:
                        try:
                            m, s = divmod(int(dur_sec), 60)
                            h, m = divmod(m, 60)
                            dur_str = "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)
                        except Exception:
                            pass
                    payload = {"vid": str(vid).strip(), "title": html_lib.unescape(name)}
                    b64_info = base64.urlsafe_b64encode(
                        json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    ).decode("utf-8")
                    cards.append(
                        {
                            "vod_id": "pkg_" + b64_info,
                            "vod_name": html_lib.unescape(name),
                            "vod_pic": pic,
                            "vod_remarks": dur_str,
                            "style": {"type": "rect", "ratio": 1.78},
                        }
                    )
                if cards:
                    return cards
            except Exception:
                pass
        return []

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        page_num = int(pg) if str(pg).isdigit() else 1
        path = str(tid).strip()
        if not path.startswith("/"):
            path = "/" + path
        sep = "&" if "?" in path else "?"
        raw_path = "%s%spage=%d" % (path, sep, page_num)
        encoded_path = urllib.parse.quote(raw_path, safe="/?=&:%")
        res = self._fetch(self.siteUrl + encoded_path)
        cards = self._parse_vod_list(res.get("text", ""))
        return {
            "page": page_num,
            "pagecount": page_num + 1 if len(cards) >= 12 else page_num,
            "limit": len(cards),
            "total": 9999,
            "list": cards,
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        vid = ""
        cached_title = ""
        if str(raw_id).startswith("pkg_"):
            try:
                b64_str = raw_id[4:]
                pad = len(b64_str) % 4
                if pad:
                    b64_str += "=" * (4 - pad)
                pkg = json.loads(
                    base64.urlsafe_b64decode(b64_str.encode("utf-8")).decode("utf-8")
                )
                vid = pkg.get("vid", "")
                cached_title = pkg.get("title", "")
            except Exception:
                vid = str(raw_id).strip()
        else:
            vid = str(raw_id).strip()
            if vid.startswith("/v/"):
                vid = vid[3:]

        res = self._fetch("/v/%s" % vid)
        html_text = res.get("text", "")
        vod_name = cached_title
        vod_pic = ""
        tag_str = ""
        desc = ""

        m_next = re.search(
            r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>([\s\S]*?)</script>',
            html_text,
            re.I,
        )
        if m_next:
            try:
                data_obj = json.loads(m_next.group(1).strip())
                video_obj = data_obj.get("props", {}).get("pageProps", {}).get("video", {})
                if video_obj:
                    if not vod_name:
                        vod_name = video_obj.get("nameZh") or video_obj.get("name") or "肉视频"
                    vod_pic = video_obj.get("coverImageUrl") or ""
                    tags = video_obj.get("tagsZh") or video_obj.get("tags") or []
                    tag_str = (
                        ", ".join(str(t) for t in tags)
                        if isinstance(tags, list)
                        else str(tags)
                    )
                    desc = video_obj.get("description") or ""
            except Exception:
                pass
        if not vod_name:
            vod_name = "肉视频"

        content_parts = []
        if tag_str:
            content_parts.append("标签: %s" % tag_str)
        if desc:
            content_parts.append(desc)
        content_parts.append("节点: %s" % self.siteUrl)

        # 播放 ID 用「rou|最终或API地址」，player 里统一处理
        api = self.siteUrl + "/api/hls/" + vid
        final = api
        try:
            headers = {
                "User-Agent": self._ua,
                "Referer": self.siteUrl + "/v/" + vid,
                "Accept": "*/*",
            }
            req = urllib.request.Request(api, headers=headers)
            with self.opener.open(req, timeout=12) as resp:
                final = resp.geturl() or api
        except Exception:
            final = api

        # 专线：代理解包（兼容全部）; 直链：仅给 player 再判断
        play_proxy = self._proxy_link("rouhls", final)
        play_api_proxy = self._proxy_link("rouhls", api)

        return {
            "list": [
                {
                    "vod_id": raw_id,
                    "vod_name": html_lib.unescape(vod_name),
                    "vod_pic": vod_pic,
                    "vod_remarks": "HD正片",
                    "vod_content": "\n".join(content_parts),
                    "vod_play_from": "肉视频专线$$$API线路",
                    "vod_play_url": "正片$%s$$$正片$%s" % (play_proxy, play_api_proxy),
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id or "").strip()
        header = {
            "User-Agent": self._ua,
            "Referer": self.siteUrl + "/",
            "Origin": self.siteUrl,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        # 已是代理地址
        if "type=rouhls" in play_url or "type=routs" in play_url or "do=py" in play_url:
            return {"parse": 0, "jx": 0, "url": play_url, "header": header}

        # 原始 /api/hls 或 CDN → 包代理
        if play_url.startswith("http") or play_url.startswith("/"):
            if play_url.startswith("/"):
                play_url = self.siteUrl + play_url
            if "/api/hls/" in play_url:
                try:
                    _, final = None, play_url
                    req = urllib.request.Request(
                        play_url,
                        headers={
                            "User-Agent": self._ua,
                            "Referer": self.siteUrl + "/v",
                            "Accept": "*/*",
                        },
                    )
                    with self.opener.open(req, timeout=12) as resp:
                        final = resp.geturl() or play_url
                        body = resp.read(16)
                    # 若已是明文 m3u8，可尝试直通
                    if body.startswith(b"#EXT"):
                        direct = self._to_m3u8_name(final)
                        return {
                            "parse": 0,
                            "jx": 0,
                            "url": direct,
                            "header": header,
                            "format": "application/x-mpegURL",
                        }
                    play_url = final
                except Exception:
                    pass
            play_url = self._proxy_link("rouhls", play_url)

        return {
            "parse": 0,
            "jx": 0,
            "url": play_url,
            "header": header,
            "format": "application/x-mpegURL",
        }

    def localProxy(self, param):
        """
        type=rouhls → 解包得到 m3u8，分片改写为 type=routs
        type=routs  → 解包分片为 video/mp2t
        """
        try:
            if not param:
                return [404, "text/plain; charset=utf-8", b"no param"]
            # 兼容不同壳传参
            url = param.get("url") or param.get("path") or ""
            typ = (
                param.get("type")
                or param.get("do")
                or param.get("cate")
                or ""
            )
            if not url:
                return [404, "text/plain; charset=utf-8", b"missing url"]
            try:
                url = urllib.parse.unquote(url)
            except Exception:
                pass

            final, body = self._fetch_bin(url, referer=self.siteUrl + "/")
            kind, data = self._unwrap(body)

            if typ == "routs" or kind == "ts":
                if kind != "ts":
                    kind, data = self._unwrap(body)
                if kind == "ts" and data:
                    return [200, "video/mp2t", data]
                if body and body[0:1] == b"G":
                    return [200, "video/mp2t", body]
                return [200, "application/octet-stream", body]

            # rouhls：输出 m3u8
            if kind != "m3u8" or not data:
                return [502, "text/plain; charset=utf-8", b"unwrap m3u8 failed"]

            text = data.decode("utf-8", errors="ignore")
            lines = []
            for line in text.splitlines():
                s = line.strip()
                if s and not s.startswith("#") and s.startswith("http"):
                    lines.append(self._proxy_link("routs", s))
                else:
                    lines.append(line)
            out = "\n".join(lines) + "\n"
            return [200, "application/vnd.apple.mpegurl; charset=utf-8", out.encode("utf-8")]
        except Exception as e:
            return [500, "text/plain; charset=utf-8", str(e).encode("utf-8")]

    def searchContent(self, key, quick, pg="1"):
        if not key:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}
        page_num = int(pg) if str(pg).isdigit() else 1
        search_url = "/search?q=%s&page=%d" % (
            urllib.parse.quote(str(key).strip()),
            page_num,
        )
        res = self._fetch(search_url)
        cards = self._parse_vod_list(res.get("text", ""))
        return {
            "page": page_num,
            "pagecount": page_num + 1 if len(cards) >= 12 else page_num,
            "limit": len(cards),
            "total": 9999,
            "list": cards,
        }

    def action(self, action):
        if action == "toast":
            return {"msg": "当前主站: %s" % self.siteUrl}
        return {"msg": "ok"}

    def destroy(self):
        self.options = {}

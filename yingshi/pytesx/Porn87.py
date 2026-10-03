#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 蜂蜜影视（FongMi TV）原生 Python 蜘蛛 - Porn87
# 风格对齐 57短剧.py / 大师兄影视

import re
import json
import html as html_lib
import urllib.request
import urllib.parse
import http.cookiejar
import gzip
import zlib
import ssl

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://porn87.com"
        self._ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
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
        self.classes = [
            {"type_id": "create_time", "type_name": "最新"},
            {"type_id": "recent_views", "type_name": "热门"},
            {"type_id": "tag:高清日本AV", "type_name": "高清日本AV"},
            {"type_id": "tag:中港台", "type_name": "中港台"},
            {"type_id": "tag:人妻", "type_name": "人妻"},
            {"type_id": "tag:巨乳", "type_name": "巨乳"},
            {"type_id": "tag:素人", "type_name": "素人"},
            {"type_id": "tag:少女女友", "type_name": "少女女友"},
            {"type_id": "tag:口交", "type_name": "口交"},
            {"type_id": "tag:中出", "type_name": "中出"},
            {"type_id": "tag:偷拍", "type_name": "偷拍"},
            {"type_id": "tag:制服", "type_name": "制服"},
            {"type_id": "tag:名人明星", "type_name": "名人明星"},
            {"type_id": "tag:多P", "type_name": "多P"},
        ]

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        return "Porn87"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": "", "final_url": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url

        headers = {
            "User-Agent": self._ua,
            "Referer": referer or (self.siteUrl + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with self.opener.open(req, timeout=15) as resp:
                code = resp.getcode()
                final_url = resp.geturl()
                raw = resp.read()
                enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    try:
                        raw = zlib.decompress(raw)
                    except Exception:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                text = raw.decode("utf-8", "ignore")
                return {"code": code, "text": text, "bytes": raw, "err": "", "final_url": final_url}
        except Exception as e:
            return {"code": 0, "text": "", "bytes": b"", "err": str(e), "final_url": target_url}

    def _clean(self, s):
        s = html_lib.unescape(str(s or ""))
        s = re.sub(r"<[^>]+>", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _abs(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.siteUrl + url
        return url

    def _parse_cards(self, html_text):
        vod_list = []
        seen = set()
        # <a href="/main/html?id=5952"> ... <img class="video_thumbnail" src="..."> ... <span>title</span>
        pattern = re.compile(
            r'<a[^>]+href=["\'](/main/html\?id=(\d+))["\'][^>]*>([\s\S]*?)</a>',
            re.I,
        )
        for m in pattern.finditer(html_text or ""):
            path, vid, block = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            img_m = re.search(
                r'<img[^>]+(?:src|preview_image)=["\']([^"\']+)["\']',
                block,
                re.I,
            )
            pic = self._abs(img_m.group(1)) if img_m else ""
            title_m = re.search(r"<span[^>]*>([\s\S]*?)</span>", block, re.I)
            if not title_m:
                title_m = re.search(r"<p[^>]*>([\s\S]*?)</p>", block, re.I)
            name = self._clean(title_m.group(1) if title_m else "") or ("视频 " + vid)
            tips_m = re.search(r'class=["\']video_time["\'][^>]*>\s*<p>([^<]+)', block, re.I)
            tips = self._clean(tips_m.group(1)) if tips_m else ""
            vod_list.append(
                {
                    "vod_id": self._abs(path),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": tips,
                }
            )
        return vod_list

    def _cat_url(self, tid, page):
        page = max(1, int(page) if str(page).isdigit() else 1)
        tid = str(tid or "create_time")
        if tid.startswith("tag:"):
            name = tid[4:]
            q = urllib.parse.quote(name)
            if page <= 1:
                return "%s/main/tag?name=%s" % (self.siteUrl, q)
            return "%s/main/tag?name=%s&page=%d" % (self.siteUrl, q, page)
        # lineup
        if page <= 1:
            return "%s/main/tag?lineup=%s" % (self.siteUrl, tid)
        return "%s/main/tag?lineup=%s&page=%d" % (self.siteUrl, tid, page)

    def homeContent(self, filter=True):
        return {
            "class": self.classes,
            "filters": {},
            "list": [],
        }

    def homeVideoContent(self):
        res = self._fetch(self.siteUrl + "/")
        return {"list": self._parse_cards(res.get("text", ""))}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        url = self._cat_url(tid, page)
        res = self._fetch(url)
        vod_list = self._parse_cards(res.get("text", ""))
        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": len(vod_list),
            "total": 9999,
            "list": vod_list,
        }

    def _extract_m3u8(self, html_text):
        """从详情封面 hash 拼直链 m3u8；失败则抓 embed 页"""
        results = []
        seen = set()
        for m in re.finditer(
            r"https?://(cdn-\d+\.porn87\.com)/media/image_1/([a-z0-9]+)(?:_\d+)?\.(?:jpg|png|webp)",
            html_text or "",
            re.I,
        ):
            cdn, h = m.group(1), m.group(2)
            if h in seen:
                continue
            seen.add(h)
            u = "https://%s/media/video_1/%s.mp4/index.m3u8" % (cdn, h)
            results.append(u)
            if len(results) >= 3:
                break
        if results:
            return results
        # embed 直取
        emb = re.search(r"/main/embed\?id=(\d+)", html_text or "")
        if emb:
            er = self._fetch(self.siteUrl + "/main/embed?id=" + emb.group(1), self.siteUrl + "/")
            for m in re.finditer(
                r"https?://cdn[^\"'\s]+\.m3u8[^\"'\s]*",
                er.get("text", ""),
                re.I,
            ):
                u = m.group(0)
                if u not in seen:
                    seen.add(u)
                    results.append(u)
        return results

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        target = str(raw).strip()
        if not target.startswith("http"):
            target = urllib.parse.urljoin(self.siteUrl, target)
        res = self._fetch(target)
        html_text = res.get("text", "")
        if not html_text:
            return {"list": []}

        title_m = re.search(r"<title>(.*?)</title>", html_text, re.I)
        name = self._clean(title_m.group(1) if title_m else "") or "精彩视频"
        name = name.split("|")[0].split("-")[0].strip()

        pic_m = re.search(
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            html_text,
            re.I,
        )
        if not pic_m:
            pic_m = re.search(
                r'class=["\']video_thumbnail["\'][^>]+src=["\']([^"\']+)["\']',
                html_text,
                re.I,
            )
        pic = self._abs(pic_m.group(1)) if pic_m else ""

        m3u8s = self._extract_m3u8(html_text)
        if not m3u8s:
            m3u8s = [target]

        play_from = []
        play_url = []
        labels = ["播放", "线路2", "线路3"]
        for i, u in enumerate(m3u8s):
            lab = labels[i] if i < len(labels) else ("线路%d" % (i + 1))
            play_from.append(lab)
            play_url.append("正片$%s" % u)

        return {
            "list": [
                {
                    "vod_id": target,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_content": name,
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url),
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id).strip()
        headers = {
            "User-Agent": self._ua,
            "Referer": self.siteUrl + "/",
            "Origin": self.siteUrl,
            "Accept": "*/*",
        }
        is_page = not self.isVideoFormat(play_url)
        return {
            "parse": 1 if is_page else 0,
            "jx": 0,
            "url": play_url,
            "header": headers,
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        q = urllib.parse.quote(key or "")
        url = "%s/main/search?name=%s" % (self.siteUrl, q)
        if page > 1:
            url += "&page=%d" % page
        res = self._fetch(url)
        vod_list = self._parse_cards(res.get("text", ""))
        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": len(vod_list),
            "total": 9999,
            "list": vod_list,
        }

    def action(self, action):
        return {"msg": "Porn87 spider ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]

    def destroy(self):
        self.options = {}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 黄豆短剧 - 蜂蜜影视/TVBox 原生 Python 蜘蛛
# 内容站 https://hddj.tv  播放 /play/{id}/{ep}.m3u8
# type_id 全部使用 cat_ 前缀，规避 home/hot/video 等保留字导致「暂无数据」

import re
import json
import gzip
import zlib
import ssl
import http.cookiejar
import urllib.request
import urllib.parse

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
        self.siteUrl = "https://hddj.tv"
        self.htmlHost = "https://hddj.tv"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.options = {}
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
        )
        # slug 映射：type_id -> URL 路径
        self._slug_map = {
            "cat_home": "",
            "cat_mgdj": "mgdj",
            "cat_ai": "ai",
            "cat_yuandou": "yuandou",
            "cat_upzhubo": "up-zhubo",
            "cat_real": "real",
            "cat_erciyuan": "erciyuan",
            "cat_heiliao": "heiliao",
            "cat_vip": "vip-zone",
            "cat_brand": "brand",
            "cat_cbdj": "cbdj",
        }

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        host = self.options.get("host") or self.options.get("url") or ""
        if isinstance(host, str) and host.startswith("http"):
            self.htmlHost = host.rstrip("/")
            self.siteUrl = self.htmlHost
        return True

    def getName(self):
        return "黄豆短剧"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "err": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.htmlHost + target_url
        headers = {
            "User-Agent": self._ua,
            "Referer": referer or (self.htmlHost + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=15) as resp:
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    return {"code": resp.getcode(), "text": raw.decode("utf-8", "ignore"), "err": ""}
            except Exception as e:
                if attempt == 0:
                    continue
                return {"code": 0, "text": "", "err": str(e)}
        return {"code": 0, "text": "", "err": "fail"}

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.htmlHost + url
        return url

    def _clean(self, s):
        s = re.sub(r"<[^>]+>", " ", s or "")
        return re.sub(r"\s+", " ", s).strip()

    def _parse_cards(self, html_text):
        vod_list = []
        seen = set()
        html_text = html_text or ""

        for m in re.finditer(
            r'<article[^>]*class=["\'][^"\']*dm-card[^"\']*["\'][^>]*>([\s\S]*?)</article>',
            html_text,
            re.I,
        ):
            body = m.group(1)
            hm = re.search(
                r'href=["\'](?:https?://[^/]+)?(/series/details/([a-zA-Z0-9]+)\.html)["\']',
                body,
                re.I,
            )
            if not hm:
                continue
            sid = hm.group(2)
            if sid in seen:
                continue
            seen.add(sid)

            title = ""
            for pat in [
                r'aria-label=["\']([^"\']+)["\']',
                r'alt=["\']([^"\']+)["\']',
                r'title=["\']([^"\']+)["\']',
            ]:
                tm = re.search(pat, body, re.I)
                if tm:
                    title = self._clean(tm.group(1))
                    if title and title != "黄豆短剧":
                        break
                    title = ""
            if not title:
                title = "短剧%s" % sid[:8]

            pic = ""
            pm = re.search(
                r'<img[^>]+(?:src|data-src|data-original)=["\']([^"\']+)["\']',
                body,
                re.I,
            )
            if pm and "placeholder" not in pm.group(1) and "favicon" not in pm.group(1):
                pic = self._abs(pm.group(1))

            tips = ""
            rm = re.search(
                r'class=["\'][^"\']*dm-card-heat[^"\']*["\'][^>]*>([\s\S]*?)</span>',
                body,
                re.I,
            )
            if rm:
                tips = self._clean(rm.group(1))[:20]

            vod_list.append({
                "vod_id": sid,
                "vod_name": title[:80],
                "vod_pic": pic,
                "vod_remarks": tips or "黄豆",
            })
            if len(vod_list) >= 80:
                break

        if not vod_list:
            for m in re.finditer(
                r'/series/details/([a-zA-Z0-9]+)\.html',
                html_text,
                re.I,
            ):
                sid = m.group(1)
                if sid in seen:
                    continue
                seen.add(sid)
                vod_list.append({
                    "vod_id": sid,
                    "vod_name": "短剧%s" % sid[:8],
                    "vod_pic": "",
                    "vod_remarks": "黄豆",
                })
                if len(vod_list) >= 40:
                    break
        return vod_list

    def homeContent(self, filter):
        classes = [
            {"type_id": "cat_home", "type_name": "首页推荐"},
            {"type_id": "cat_mgdj", "type_name": "魔改短剧"},
            {"type_id": "cat_ai", "type_name": "AI短剧"},
            {"type_id": "cat_yuandou", "type_name": "原创短剧"},
            {"type_id": "cat_upzhubo", "type_name": "UP主播"},
            {"type_id": "cat_real", "type_name": "真人短剧"},
            {"type_id": "cat_erciyuan", "type_name": "二次元"},
            {"type_id": "cat_heiliao", "type_name": "黑料"},
            {"type_id": "cat_vip", "type_name": "VIP专区"},
            {"type_id": "cat_brand", "type_name": "品牌"},
            {"type_id": "cat_cbdj", "type_name": "重磅短剧"},
        ]
        result = {"class": classes}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        res = self.categoryContent("cat_home", 1, False, {})
        return {"list": res.get("list", [])[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1

        tid = str(tid or "cat_home").strip()
        # 兼容旧 id
        legacy = {
            "home": "cat_home", "mgdj": "cat_mgdj", "ai": "cat_ai",
            "yuandou": "cat_yuandou", "up-zhubo": "cat_upzhubo", "real": "cat_real",
            "erciyuan": "cat_erciyuan", "heiliao": "cat_heiliao",
            "vip-zone": "cat_vip", "brand": "cat_brand", "cbdj": "cat_cbdj",
        }
        if tid in legacy:
            tid = legacy[tid]

        slug = self._slug_map.get(tid, "")
        if tid == "cat_home" or slug == "":
            path = "/" if page <= 1 else ("/?page=%d" % page)
        else:
            path = "/category/%s/" % slug
            if page > 1:
                path += "?page=%d" % page

        res = self._fetch(self.htmlHost + path)
        html = res.get("text", "")
        vod_list = self._parse_cards(html)

        # 失败时回退首页，避免「暂无数据」
        if not vod_list and page == 1 and tid != "cat_home":
            res2 = self._fetch(self.htmlHost + "/")
            vod_list = self._parse_cards(res2.get("text", ""))

        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": 24,
            "total": 9999 if vod_list else 0,
            "list": vod_list,
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        sid = re.sub(r"\.html$", "", str(raw_id).strip("/").split("/")[-1])
        detail_url = "%s/series/details/%s.html" % (self.htmlHost, sid)
        res = self._fetch(detail_url)
        html = res.get("text", "")

        title = "短剧%s" % sid[:8]
        cover = ""
        m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
        if m:
            t = self._clean(m.group(1))
            if t:
                title = t
        m = re.search(r'aria-label=["\']([^"\']+)["\']', html)
        if m and title.startswith("短剧"):
            title = m.group(1).strip()
        m = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.I,
        )
        if m:
            cover = self._abs(m.group(1))

        ep_count = 1
        m = re.search(r'data-eps=["\'](\d+)["\']', html)
        if m:
            ep_count = max(1, int(m.group(1)))
        eps = [int(x) for x in re.findall(r"/play/%s/(\d+)" % re.escape(sid), html)]
        if eps:
            ep_count = max(ep_count, max(eps))

        episodes = []
        for i in range(1, ep_count + 1):
            play = "%s/play/%s/%d.m3u8" % (self.htmlHost, sid, i)
            episodes.append("第%d集$%s" % (i, play))

        return {
            "list": [{
                "vod_id": sid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_actor": "黄豆短剧",
                "vod_director": "hddj",
                "vod_content": title,
                "vod_play_from": "黄豆",
                "vod_play_url": "#".join(episodes) if episodes else "正片$%s" % detail_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id).strip()
        return {
            "parse": 0 if self.isVideoFormat(play_url) else 1,
            "jx": 0,
            "url": play_url,
            "header": {
                "User-Agent": self._ua,
                "Referer": self.htmlHost + "/",
                "Accept": "*/*",
            },
        }

    def searchContent(self, key, quick, pg="1"):
        page = 1
        try:
            page = int(pg)
        except Exception:
            page = 1
        q = urllib.parse.quote(key or "")
        url = "%s/search/?q=%s" % (self.htmlHost, q)
        if page > 1:
            url += "&page=%d" % page
        res = self._fetch(url)
        vod_list = self._parse_cards(res.get("text", ""))
        if not vod_list:
            for m in re.finditer(r"/series/details/([a-zA-Z0-9]+)\.html", res.get("text", "")):
                sid = m.group(1)
                vod_list.append({
                    "vod_id": sid,
                    "vod_name": key or sid,
                    "vod_pic": "",
                    "vod_remarks": "搜索",
                })
                if len(vod_list) >= 30:
                    break
        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": 24,
            "total": 9999 if vod_list else 0,
            "list": vod_list,
        }

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain", ""]

    def destroy(self):
        self.options = {}

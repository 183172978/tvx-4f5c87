#!/usr/bin/python
# -*- coding: utf-8 -*-
# 红豆短剧 v1.2 — 按 18AV 模式修复
# - 拉全部分集（分页）
# - 优先 m3u8(src)，备用 mp4(videourl)
# - 影视仓多线路：HLS$$$MP4
# - playerContent 直出 + 完整 Header
import json
import re
import sys

try:
    import requests
except ImportError:
    requests = None

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def getName(self):
        return "红豆短剧"

    def init(self, extend=""):
        self.host = "https://hdou.tv"
        self.api = "https://api.dramaplay.shop"
        self.image_host = "https://static.hdou.tv"
        self.limit = 24
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.classes = [
            {"type_id": "0", "type_name": "最新短剧"},
            {"type_id": "334", "type_name": "都市"},
            {"type_id": "155", "type_name": "古装"},
            {"type_id": "338", "type_name": "爱情"},
            {"type_id": "362", "type_name": "总裁"},
            {"type_id": "285", "type_name": "甜宠"},
            {"type_id": "332", "type_name": "逆袭"},
            {"type_id": "341", "type_name": "重生"},
            {"type_id": "306", "type_name": "穿越"},
            {"type_id": "397", "type_name": "玄幻"},
            {"type_id": "220", "type_name": "悬疑"},
            {"type_id": "320", "type_name": "萌宝"},
            {"type_id": "307", "type_name": "系统"},
            {"type_id": "250", "type_name": "校园"},
            {"type_id": "343", "type_name": "闪婚"},
        ]
        genres = [
            ("0", "全部"), ("334", "都市"), ("155", "古装"),
            ("338", "爱情"), ("362", "总裁"), ("285", "甜宠"),
            ("332", "逆袭"), ("341", "重生"), ("306", "穿越"),
            ("397", "玄幻"), ("220", "悬疑"), ("320", "萌宝"),
            ("307", "系统"), ("250", "校园"), ("343", "闪婚"),
            ("346", "马甲"), ("299", "神医"), ("260", "民国"),
            ("256", "武侠"), ("190", "宫廷"),
        ]
        genre_values = [{"n": name, "v": value} for value, name in genres]
        self.filters = {
            item["type_id"]: [{
                "key": "typeid",
                "name": "题材",
                "init": item["type_id"],
                "value": genre_values,
            }]
            for item in self.classes
        }
        if requests is not None:
            self.session = requests.Session()
        else:
            self.session = None
        if extend:
            try:
                conf = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith("{") else {}
                if conf.get("api"):
                    self.api = str(conf["api"]).rstrip("/")
                if conf.get("host"):
                    self.host = str(conf["host"]).rstrip("/")
                    self.headers["Referer"] = self.host + "/"
                    self.headers["Origin"] = self.host
            except Exception:
                pass

    def _get(self, path, params=None):
        url = self.api + path
        try:
            if self.session is not None:
                response = self.session.get(url, params=params, headers=self.headers, timeout=20)
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
            import urllib.request
            import urllib.parse
            import ssl
            qs = ("?" + urllib.parse.urlencode(params or {})) if params else ""
            req = urllib.request.Request(url + qs, headers=self.headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8", "ignore"))
        except Exception as e:
            print("GET error", url, e)
            return {}

    def _page(self, value):
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 1

    def _image(self, value):
        value = str(value or "").strip()
        if not value:
            return ""
        if value.startswith("//"):
            return "https:" + value
        if value.startswith(("http://", "https://")):
            return re.sub(r"(?<!:)//+", "/", value)
        return self.image_host + "/" + value.lstrip("/")

    def _remarks(self, item):
        total = item.get("sum") or item.get("video") or 0
        return str(item.get("tp") or (f"全{total}集" if total else item.get("text", "") or ""))

    def _items(self, rows):
        out = []
        for item in rows or []:
            if not item.get("id") or not item.get("name"):
                continue
            out.append({
                "vod_id": str(item.get("id", "")),
                "vod_name": str(item.get("name", "")),
                "vod_pic": self._image(item.get("img") or item.get("pic")),
                "vod_remarks": self._remarks(item),
            })
        return out

    def _list(self, pg=1, type_id="0", key=""):
        pg = self._page(pg)
        params = {"limit": self.limit, "offset": (pg - 1) * self.limit, "lx": 1}
        if str(type_id) not in ("", "0"):
            params["typeid"] = str(type_id)
        if key:
            params["keytext"] = str(key)
        data = self._get("/api/video/lists", params)
        total = int(data.get("total") or 0)
        rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        return {
            "page": pg,
            "pagecount": max(1, (total + self.limit - 1) // self.limit) if total else 1,
            "limit": self.limit,
            "total": total,
            "list": self._items(rows),
        }

    def homeContent(self, filter):
        result = self._list(1)
        return {"class": self.classes, "list": result["list"], "filters": self.filters}

    def homeVideoContent(self):
        return {"list": self._list(1)["list"]}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend if isinstance(extend, dict) else {}
        type_id = extend.get("typeid")
        return self._list(pg, tid if type_id in (None, "") else type_id)

    def _actors(self, value):
        if isinstance(value, list):
            return ",".join(str(item) for item in value if item)
        try:
            data = json.loads(value or "[]")
            return ",".join(str(item) for item in data if item) if isinstance(data, list) else ""
        except (TypeError, ValueError):
            return str(value or "")

    def _text(self, value):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(value or ""))).strip()

    def _fetch_all_episodes(self, vod_id):
        """分页拉全部分集，按 weigh/id 排序"""
        all_eps = []
        seen = set()
        page = 1
        total = None
        while page <= 30:
            data = self._get("/api/video/videoinfo", {
                "page": page, "uid": 0, "vid": str(vod_id), "mid": 0, "token": "",
            })
            rows = data.get("data") or data.get("result") or []
            if not isinstance(rows, list) or not rows:
                break
            if total is None:
                try:
                    total = int(data.get("total") or data.get("affectedDocs") or 0)
                except (TypeError, ValueError):
                    total = 0
            for ep in rows:
                eid = ep.get("id") or ep.get("_id")
                key = str(eid or "") + "|" + str(ep.get("name") or "")
                if key in seen:
                    continue
                seen.add(key)
                all_eps.append(ep)
            if total and len(all_eps) >= total:
                break
            if len(rows) < 10:
                break
            page += 1
        all_eps.sort(key=lambda item: (
            int(item.get("weigh") or 0) or 10 ** 9,
            int(item.get("id") or 0),
        ))
        return all_eps

    def _ep_name(self, episode, index):
        name = str(
            episode.get("name")
            or episode.get("fjname")
            or episode.get("title")
            or f"第{index}集"
        )
        return name.replace("$", " ").replace("#", " ").strip() or f"第{index}集"

    def _ep_urls(self, episode):
        """返回 (m3u8_or_hls, mp4_or_other)"""
        src = str(episode.get("src") or "").strip()
        vurl = str(episode.get("videourl") or episode.get("url") or "").strip()
        hls, mp4 = "", ""
        for u in (src, vurl):
            if not u:
                continue
            if u.startswith("//"):
                u = "https:" + u
            if re.search(r"\.m3u8(\?|$)", u, re.I):
                if not hls:
                    hls = u
            elif re.search(r"\.mp4(\?|$)", u, re.I):
                if not mp4:
                    mp4 = u
            else:
                if not hls:
                    hls = u
        return hls, mp4

    def detailContent(self, ids):
        result = []
        for vod_id in ids or []:
            vod_id = str(vod_id)
            info = self._get("/api/video/info", {"id": vod_id, "mid": 0})
            episodes = self._fetch_all_episodes(vod_id)

            hls_list = []
            mp4_list = []
            for index, episode in enumerate(episodes, 1):
                name = self._ep_name(episode, index)
                hls, mp4 = self._ep_urls(episode)
                if hls:
                    hls_list.append("%s$%s" % (name, hls))
                if mp4:
                    mp4_list.append("%s$%s" % (name, mp4))

            # 详情里的首集兜底
            if not hls_list and not mp4_list and info.get("videourl"):
                u = str(info["videourl"]).strip()
                if u.startswith("//"):
                    u = "https:" + u
                label = str(info.get("ji") or "第1集")
                if re.search(r"\.m3u8(\?|$)", u, re.I):
                    hls_list.append("%s$%s" % (label, u))
                else:
                    mp4_list.append("%s$%s" % (label, u))

            # 影视仓多线路：HLS$$$MP4（有则出）
            from_parts = []
            url_parts = []
            if hls_list:
                from_parts.append("红豆HLS")
                url_parts.append("#".join(hls_list))
            if mp4_list:
                from_parts.append("红豆MP4")
                url_parts.append("#".join(mp4_list))
            if not from_parts:
                from_parts.append("红豆")
                url_parts.append("")

            year = str(info.get("updatetime") or "")[:4]
            result.append({
                "vod_id": vod_id,
                "vod_name": str(info.get("name") or f"短剧{vod_id}"),
                "vod_pic": self._image(info.get("img") or info.get("pic")),
                "type_name": str(info.get("text") or "短剧"),
                "vod_year": year if year.isdigit() else "",
                "vod_area": "",
                "vod_remarks": self._remarks(info) or (f"全{len(episodes)}集" if episodes else ""),
                "vod_actor": self._actors(info.get("yyid")),
                "vod_director": "",
                "vod_content": self._text(info.get("story") or info.get("info")),
                "vod_play_from": "$$$".join(from_parts),
                "vod_play_url": "$$$".join(url_parts),
            })
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        return self._list(pg, "0", key)

    def searchContentPage(self, key, quick, pg=1):
        return self._list(pg, "0", key)

    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()
        if url.startswith("//"):
            url = "https:" + url
        header = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        # m3u8 常在 sgcdn.hdou.tv，补 Referer
        if "hdou" in url or "dramaplay" in url:
            header["Referer"] = self.host + "/"
        return {"parse": 0, "jx": 0, "url": url, "header": header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(m3u8|mp4|ts)(\?|$)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("home", len(sp.homeContent(False).get("list") or []))
    r = sp.categoryContent("0", 1, False, {})
    print("list", len(r.get("list") or []), r["list"][0]["vod_name"] if r.get("list") else None)
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        item = d["list"][0]
        print("name", item["vod_name"])
        print("from", item["vod_play_from"])
        print("remarks", item["vod_remarks"])
        urls = item["vod_play_url"].split("$$$")
        for i, part in enumerate(urls):
            eps = part.split("#")
            print("line", i, "eps", len(eps), "sample", eps[0][:80] if eps else "")
        first = urls[0].split("#")[0].split("$")[-1]
        p = sp.playerContent("红豆HLS", first, [])
        print("player", p["url"][:70], p["parse"])

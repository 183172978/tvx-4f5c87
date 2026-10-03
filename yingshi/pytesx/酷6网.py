#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酷6网 — 严格对齐可用 drpy 规则
host: https://www.ku6.com
列表: /video/feed  → data[].title / picPath / publisher / playUrl
播放: playUrl 含 detail.html 则 vid=split("~")[1]
      → https://news-stream.lsttnews.com/topic/recommend/vinfo?vid= → data.video.src
      否则 playUrl 即直链
"""
import json
import re
import gzip
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


HOST = "https://www.ku6.com"
PLAY_API = "https://news-stream.lsttnews.com/topic/recommend/vinfo?vid="
UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
)

# class_name / class_url 与 drpy 完全一致
CLASSES = [
    ("69", "资讯"),
    ("70", "娱乐"),
    ("76", "搞笑"),
    ("73", "少儿"),
    ("71", "自制节目"),
    ("72", "影视"),
    ("74", "音乐"),
    ("75", "原创"),
    ("80", "生活"),
    ("93", "游戏"),
    ("81", "健康"),
    ("47", "汽车"),
    ("149", "时事"),
]


class Spider(BaseSpider):
    def getName(self):
        return "酷6网"

    def init(self, extend=""):
        pass

    def _headers(self):
        return {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _decode(self, raw):
        if not raw:
            return ""
        if isinstance(raw, str):
            return raw
        if len(raw) >= 2 and raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw.decode("utf-8", "ignore")

    def fetch_text(self, url):
        try:
            if requests is not None:
                r = requests.get(url, headers=self._headers(), timeout=15, verify=False)
                return r.text or ""
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as resp:
                return self._decode(resp.read())
        except Exception as e:
            print("fetch", url, e)
            return ""

    def fetch_json(self, url):
        txt = self.fetch_text(url)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    def _abs_pic(self, u):
        if not u:
            return ""
        u = str(u).strip().replace("\\/", "/")
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return HOST + u
        return u

    def _feed(self, subject_id, page_no, page_size=20):
        """page_no 从 0 开始（与 homeUrl 一致）"""
        page_no = max(0, int(page_no or 0))
        page_size = int(page_size or 20)
        if subject_id and str(subject_id).isdigit():
            url = "%s/video/feed?subjectId=%s&pageNo=%d&pageSize=%d" % (
                HOST, subject_id, page_no, page_size
            )
        else:
            url = "%s/video/feed?pageNo=%d&pageSize=%d" % (HOST, page_no, page_size)
        d = self.fetch_json(url)
        if not isinstance(d, dict):
            return []
        data = d.get("data")
        if not isinstance(data, list):
            return []
        out = []
        for it in data:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title") or "").strip()
            pic = self._abs_pic(it.get("picPath") or "")
            pub = str(it.get("publisher") or "").strip()
            play = str(it.get("playUrl") or "").replace("\\/", "/").strip()
            if not title or not play:
                continue
            # 一级 id = playUrl（drpy: json:data;title;picPath;publisher;playUrl）
            out.append({
                "vod_id": play,
                "vod_name": title[:120],
                "vod_pic": pic,
                "vod_remarks": pub[:24],
                "style": {"type": "rect", "ratio": 1.78},
            })
        return out

    def homeContent(self, filter=False):
        return {
            "class": [{"type_id": a, "type_name": b} for a, b in CLASSES],
            "filters": {},
            "list": [],
        }

    def homeVideoContent(self):
        return {"list": self._feed("", 0, 20)}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or "76").strip()
        # 壳页码从 1 开始 → API pageNo 从 0 开始
        videos = self._feed(tid, pg - 1, 20)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 10 else max(pg, 1),
            "limit": 20,
            "total": 9999 if videos else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def searchContentPage(self, key, quick=False, pg=1):
        return self.searchContent(key, quick, pg)

    def _parse_vid(self, play):
        play = str(play or "")
        if "~" in play:
            return play.split("~")[-1].strip()
        m = re.search(r"[?&]vid=([^&]+)", play)
        if m:
            return m.group(1).strip()
        return ""

    def _resolve(self, play):
        """完整对齐 lazy 逻辑，返回 (media_url, title)"""
        play = str(play or "").strip()
        if not play:
            return "", ""
        # 直链
        if re.search(r"\.(mp4|m3u8|flv)(\?|$)", play, re.I) and play.startswith("http"):
            return play, ""
        # detail.html → vinfo
        if "detail.html" in play or "~" in play:
            vid = self._parse_vid(play)
            if vid:
                d = self.fetch_json(PLAY_API + urllib.parse.quote(vid))
                if isinstance(d, dict):
                    data = d.get("data") or {}
                    if not isinstance(data, dict):
                        data = {}
                    video = data.get("video") or {}
                    if not isinstance(video, dict):
                        video = {}
                    src = (
                        video.get("src")
                        or video.get("url")
                        or data.get("src")
                        or data.get("url")
                        or data.get("playUrl")
                        or ""
                    )
                    title = str(
                        data.get("title")
                        or video.get("title")
                        or data.get("name")
                        or ""
                    ).strip()
                    if src:
                        return str(src).replace("\\/", "/"), title
        # 纯 vid
        if re.match(r"^[\w\-]+$", play) and not play.startswith("http"):
            d = self.fetch_json(PLAY_API + urllib.parse.quote(play))
            if isinstance(d, dict):
                data = d.get("data") or {}
                video = (data.get("video") or {}) if isinstance(data, dict) else {}
                if isinstance(video, dict) and video.get("src"):
                    return str(video["src"]).replace("\\/", "/"), str(data.get("title") or "")
        if play.startswith("http"):
            return play, ""
        return "", ""

    def detailContent(self, ids):
        play = str((ids or [""])[0]).strip()
        if not play:
            return {"list": []}
        media, title = self._resolve(play)
        if not media:
            # 仍返回可点条目，playerContent 再试
            media = play
        if not title:
            title = "酷6网视频"
        return {"list": [{
            "vod_id": play,
            "vod_name": title,
            "vod_pic": "",
            "vod_content": "酷6网",
            "vod_play_from": "酷6",
            "vod_play_url": "正片$%s" % media,
            "style": {"type": "rect", "ratio": 1.78},
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Origin": HOST,
        }
        raw = str(id or "").strip()
        if "$" in raw:
            raw = raw.split("$")[-1].strip()
        media, _ = self._resolve(raw)
        if not media:
            media = raw
        is_direct = bool(media and re.search(r"\.(mp4|m3u8|flv)(\?|$)", media, re.I))
        if is_direct or (media.startswith("http") and "detail.html" not in media):
            return {
                "parse": 0,
                "jx": 0,
                "url": media,
                "header": header,
                "format": "application/x-mpegURL" if ".m3u8" in media.lower() else "video/mp4",
            }
        return {"parse": 0, "jx": 0, "url": media, "header": header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(mp4|m3u8|flv)(\?|$)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

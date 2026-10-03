# -*- coding: utf-8 -*-
"""七猫短剧 https://7maoduanju.com  按禁果短剧结构"""
import json
import re
import sys
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass


SITE = "https://7maoduanju.com"
API = "https://7maoduanju.com/api/toc/v1"
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)
BRAND = "七猫短剧"
TG = "https://t.me/tvshare23"
CARD = {"type": "rect", "ratio": 0.75}

CLASSES = [
    ("10000000-0000-4000-8000-0000000000c0", "热门短剧"),
    ("10000000-0000-4000-8000-000000000002", "原创短剧"),
    ("10000000-0000-4000-8000-0000000000b3", "AI短剧"),
    ("10000000-0000-4000-8000-000000000003", "AI漫剧"),
    ("10000000-0000-4000-8000-0000000000b1", "AI魔改"),
    ("10000000-0000-4000-8000-000000000005", "擦边短剧"),
    ("10000000-0000-4000-8000-0000000000b0", "真人短剧"),
    ("10000000-0000-4000-8000-0000000000b2", "AI换脸"),
    ("10000000-0000-4000-8000-0000000000b4", "影视综艺"),
]


class Spider(BaseSpider):
    def init(self, extend=""):
        self.session = requests.Session() if requests else None
        if self.session is not None:
            self.session.headers.update(
                {
                    "User-Agent": UA,
                    "Accept": "application/json, text/plain, */*",
                    "Referer": SITE + "/",
                    "Origin": SITE,
                }
            )
            self.session.verify = False

    def getName(self):
        return "七猫短剧"

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _get(self, path, params=None, timeout=12):
        if path.startswith("http"):
            url = path
        else:
            url = API + path
        try:
            if self.session is not None:
                r = self.session.get(url, params=params, timeout=timeout)
                return r.text or ""
            import urllib.request
            from urllib.parse import urlencode

            full = url
            if params:
                full += ("&" if "?" in url else "?") + urlencode(params)
            req = urllib.request.Request(
                full,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json",
                    "Referer": SITE + "/",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("get err", e)
            return ""

    def _json(self, path, params=None):
        txt = self._get(path, params)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    def _cover(self, u):
        raw = str(u or "").strip()
        if not raw:
            return "https://dummyimage.com/600x800/1e293b/fff.png&text=NO"
        if raw.startswith("http"):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return SITE + "/" + raw.lstrip("/")

    def _to_vod(self, it):
        if not isinstance(it, dict):
            return None
        vid = str(it.get("id") or "").strip()
        if not vid:
            return None
        ep = it.get("episodeCount") or ""
        heat = it.get("heat") or ""
        parts = []
        if ep:
            parts.append("全%s集" % ep)
        if heat:
            parts.append("热度%s" % heat)
        meta = " · ".join(parts)
        return {
            "vod_id": vid,
            "vod_name": str(it.get("title") or vid),
            "vod_pic": self._cover(it.get("coverUrl")),
            "vod_remarks": ("%s | %s" % (BRAND, meta)) if meta else BRAND,
            "style": CARD,
        }

    def homeContent(self, filter=False):
        return {
            "class": [{"type_id": t, "type_name": n} for t, n in CLASSES],
            "filters": {},
        }

    def homeVideoContent(self):
        data = self._json("/home") or {}
        list_v, seen = [], set()
        for block in data.get("blocks") or []:
            for it in block.get("items") or []:
                v = self._to_vod(it)
                if v and v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    list_v.append(v)
                if len(list_v) >= 30:
                    break
            if len(list_v) >= 30:
                break
        return {"list": list_v}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg or 1)
        data = self._json(
            "/browse",
            {"poolId": str(tid or ""), "page": page, "limit": 24},
        ) or {}
        items = data.get("items") or []
        vlist = [self._to_vod(it) for it in items if self._to_vod(it)]
        has_more = bool(data.get("hasMore"))
        return {
            "list": vlist,
            "page": page,
            "pagecount": page + 1 if has_more else page,
            "limit": 24,
            "total": page * 24 + 1 if has_more else len(vlist),
        }

    def searchContent(self, key, quick=False, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        key = str(key or "").strip()
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}
        data = self._json("/search", {"q": key})
        items = data if isinstance(data, list) else []
        vlist = [self._to_vod(it) for it in items if self._to_vod(it)]
        return {
            "list": vlist,
            "page": 1,
            "pagecount": 1,
            "limit": len(vlist) or 20,
            "total": len(vlist),
        }

    def detailContent(self, ids):
        vid = str((ids[0] if ids else "") or "").strip()
        data = self._json("/dramas/" + quote(vid)) or {}
        if not data:
            return {"list": []}
        title = str(data.get("title") or vid)
        cover = self._cover(data.get("coverUrl"))
        desc = str(data.get("description") or "")
        tags = data.get("tags") if isinstance(data.get("tags"), list) else []
        eps = data.get("episodes") if isinstance(data.get("episodes"), list) else []
        plays = []
        for i, ep in enumerate(eps):
            name = str(ep.get("title") or ("第%s集" % (ep.get("indexNo") or i + 1)))
            name = name.replace("$", "").replace("#", "")
            stream = str(ep.get("seoContentUrl") or "").strip()
            if stream:
                plays.append("%s$%s" % (name, stream))
            else:
                plays.append(
                    "%s$%s:%s:%s"
                    % (name, vid, ep.get("id") or "", ep.get("indexNo") or i + 1)
                )
        if not plays:
            plays.append("第1集$%s::1" % vid)
        return {
            "list": [
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": "%s | 全%d集" % (BRAND, len(plays)),
                    "vod_content": "【交流群 %s】\n%s" % (TG, desc or " · ".join(tags) or title),
                    "vod_actor": " · ".join(str(x) for x in tags),
                    "vod_play_from": "七猫专线",
                    "vod_play_url": "#".join(plays),
                    "style": CARD,
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags=None):
        head = {"User-Agent": UA, "Referer": SITE + "/", "Origin": SITE}
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        if play.startswith("http") and self.isVideoFormat(play):
            return {"parse": 0, "jx": 0, "url": play, "header": head}

        parts = play.split(":")
        vid = parts[0] if parts else ""
        ep_id = parts[1] if len(parts) > 1 else ""
        idx = parts[2] if len(parts) > 2 else ""
        if vid:
            data = self._json("/dramas/" + quote(vid)) or {}
            eps = data.get("episodes") if isinstance(data.get("episodes"), list) else []
            for i, ep in enumerate(eps):
                if (
                    (ep_id and str(ep.get("id")) == str(ep_id))
                    or (idx and str(ep.get("indexNo")) == str(idx))
                    or (not ep_id and not idx and i == 0)
                ):
                    stream = str(ep.get("seoContentUrl") or "").strip()
                    if stream:
                        return {"parse": 0, "jx": 0, "url": stream, "header": head}
            if eps and eps[0].get("seoContentUrl"):
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": str(eps[0]["seoContentUrl"]),
                    "header": head,
                }
        return {"parse": 1, "jx": 0, "url": SITE + "/", "header": head}


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("home", [c["type_name"] for c in sp.homeContent()["class"]])
    r = sp.categoryContent(CLASSES[0][0], 1)
    print("cat", len(r.get("list") or []))
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        main = d["list"][0]
        print("detail", main["vod_name"], main["vod_play_from"])
        print("url0", main["vod_play_url"].split("#")[0][:80])
        p = sp.playerContent("x", main["vod_play_url"].split("#")[0].split("$")[-1])
        print("play", p.get("parse"), str(p.get("url"))[:80])

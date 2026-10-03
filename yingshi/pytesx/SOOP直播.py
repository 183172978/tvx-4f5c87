# coding=utf-8
"""
SOOP 直播 · 按 StripChat 结构改写
列表：live.sooplive.co.kr/api/main_broad_list_api.php
播放：player_live_api.php → AID + broad_stream_assign → m3u8
"""
import re
import sys
import json
from urllib.parse import quote, urlencode

import requests

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def getProxyUrl(self, *a, **k):
            return "http://127.0.0.1:9978/proxy?do=py"


class Spider(BaseSpider):
    def init(self, extend="{}"):
        self.site = "https://m.sooplive.com"
        self.play_host = "https://play.sooplive.com"
        self.list_hosts = [
            "https://live.sooplive.co.kr",
            "https://live.sooplive.com",
        ]
        self.live_api_hosts = [
            "https://live.sooplive.com/afreeca/player_live_api.php",
            "https://live.sooplive.co.kr/afreeca/player_live_api.php",
        ]
        self.search_hosts = [
            "https://sch.sooplive.co.kr",
            "https://sch.sooplive.com",
        ]
        self.ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.6 Mobile/15E148 Safari/604.1"
        )
        self.session = requests.Session()
        self.channels = [
            ("all", "全部直播", ""),
            ("0004", "游戏", "0004"),
            ("0002", "生活", "0002"),
            ("0008", "音乐", "0008"),
            ("0010", "体育", "0010"),
            ("0006", "美食", "0006"),
            ("0012", "Talk", "0012"),
        ]

    def getName(self):
        return "SOOP直播"

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _headers(self, referer=None, origin=None):
        return {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7",
            "Referer": referer or (self.site + "/"),
            "Origin": origin or "https://play.sooplive.com",
        }

    def _get(self, url, params=None, referer=None, timeout=12):
        try:
            r = self.session.get(
                url,
                params=params,
                headers=self._headers(referer),
                timeout=timeout,
                verify=False,
            )
            if r is not None and r.status_code == 200:
                return r.text or ""
        except Exception:
            pass
        return ""

    def _post(self, url, data=None, referer=None, timeout=12):
        try:
            r = self.session.post(
                url,
                data=data or {},
                headers={
                    **self._headers(referer),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=timeout,
                verify=False,
            )
            if r is not None and r.status_code == 200:
                return r.text or ""
        except Exception:
            pass
        return ""

    def _json(self, text):
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]+\}", text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return {}

    def _pic(self, user_id):
        if not user_id:
            return ""
        pre = (user_id[:2] if len(user_id) >= 2 else user_id).lower()
        return "https://stimg.sooplive.com/LOGO/%s/%s/m/%s.webp" % (
            pre, user_id, user_id
        )

    def _map(self, item):
        if not isinstance(item, dict):
            return None
        uid = str(
            item.get("user_id")
            or item.get("bj_id")
            or item.get("userId")
            or item.get("bid")
            or ""
        )
        if not uid:
            return None
        bno = str(
            item.get("broad_no")
            or item.get("bno")
            or item.get("broadNo")
            or ""
        )
        title = (
            item.get("broad_title")
            or item.get("title")
            or item.get("broadTitle")
            or uid
        )
        nick = (
            item.get("user_nick")
            or item.get("bj_nick")
            or item.get("userNick")
            or uid
        )
        viewers = (
            item.get("total_view_cnt")
            or item.get("view_cnt")
            or item.get("pc_view_cnt")
            or item.get("viewer")
            or ""
        )
        cate = item.get("broad_cate_name") or item.get("category") or ""
        pic = item.get("broad_thumb") or item.get("thumb") or self._pic(uid)
        if pic and str(pic).startswith("//"):
            pic = "https:" + pic
        vod_id = uid + (("|" + bno) if bno else "")
        return {
            "vod_id": vod_id,
            "vod_name": str(title)[:80],
            "vod_pic": pic,
            "vod_remarks": ("%s人" % viewers) if viewers else (cate or nick),
            "vod_actor": nick,
            "style": {"type": "rect", "ratio": 1.78},
        }

    def _pick_list(self, js):
        if isinstance(js, list):
            return js
        if not isinstance(js, dict):
            return []
        d = js.get("data") if isinstance(js.get("data"), (dict, list)) else js
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            for k in ("broad", "list", "broad_list", "lives", "result", "CHANNEL"):
                v = d.get(k)
                if isinstance(v, list):
                    return v
                if isinstance(v, dict) and isinstance(v.get("broad"), list):
                    return v.get("broad")
        if isinstance(js.get("broad"), list):
            return js.get("broad")
        return []

    def _live_list(self, page=1, cate=""):
        page = int(page or 1)
        cate = str(cate or "")
        params_sets = [
            {
                "page": str(page),
                "order_type": "view_cnt",
                "selectType": "action",
                "selectValue": cate or "all",
            },
            {
                "m": "liveListHash",
                "pageNo": str(page),
                "pageSize": "30",
                "order_type": "view_cnt",
                "cate_no": cate,
            },
            {"m": "liveList", "page": str(page), "orderBy": "view_cnt"},
        ]
        paths = ["/api/main_broad_list_api.php", "/api.php"]
        for host in self.list_hosts:
            for path in paths:
                for params in params_sets:
                    text = self._get(host + path, params=params)
                    js = self._json(text)
                    items = self._pick_list(js)
                    videos = []
                    for it in items:
                        v = self._map(it)
                        if v:
                            videos.append(v)
                    if videos:
                        return videos
        return []

    def homeContent(self, filter):
        classes = [
            {"type_id": tid, "type_name": name}
            for tid, name, _ in self.channels
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._live_list(1, "")[:24]}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        cate = ""
        for t, _, c in self.channels:
            if str(tid) == t:
                cate = c
                break
        videos = self._live_list(pg, cate)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 20 else max(pg, 1),
            "limit": 30,
            "total": 9999 if videos else 0,
        }

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = str(key or "").strip()
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        videos = []
        param_sets = [
            {
                "m": "searchLiveList",
                "v": "1.0",
                "szKeyword": key,
                "nPageNo": str(pg),
                "nListCnt": "20",
            },
            {"m": "broadSearch", "szKeyword": key, "nPageNo": str(pg)},
        ]
        for host in self.search_hosts:
            for params in param_sets:
                text = self._get(host + "/api.php", params=params)
                js = self._json(text)
                for it in self._pick_list(js):
                    v = self._map(it)
                    if v:
                        videos.append(v)
                if videos:
                    break
            if videos:
                break
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 15 else pg,
            "limit": 20,
            "total": len(videos),
        }

    def _pick_id(self, ids):
        if ids is None:
            return ""
        if isinstance(ids, (list, tuple)):
            if not ids:
                return ""
            return str(ids[0]).strip()
        return str(ids).strip()

    def _live_channel(self, uid, bno=""):
        data = {
            "from_api": "0",
            "mode": "landing",
            "player_type": "html5",
            "stream_type": "common",
            "type": "live",
            "bid": uid,
            "bno": bno or "",
            "pwd": "",
        }
        referer = self.play_host + "/" + uid
        for api in self.live_api_hosts:
            text = self._post(api, data=data, referer=referer)
            js = self._json(text)
            ch = js.get("CHANNEL") if isinstance(js, dict) else {}
            if isinstance(ch, dict) and (ch.get("BNO") or ch.get("RESULT")):
                return ch
        return {}

    def _resolve_play(self, uid, bno=""):
        ch = self._live_channel(uid, bno)
        if not ch:
            return ""
        bno = str(ch.get("BNO") or bno or "")
        rmd = str(ch.get("RMD") or "").rstrip("/")
        cdn = str(ch.get("CDN") or "gs_cdn_pc_web")
        if not bno or not rmd:
            return ""

        # AID
        aid = ""
        referer = self.play_host + "/" + uid
        data = {
            "from_api": "0",
            "mode": "landing",
            "player_type": "html5",
            "stream_type": "common",
            "type": "aid",
            "bid": uid,
            "bno": bno,
            "pwd": "",
            "quality": "hd",
        }
        for api in self.live_api_hosts:
            text = self._post(api, data=data, referer=referer)
            js = self._json(text)
            aid = ((js.get("CHANNEL") or {}).get("AID") if isinstance(js, dict) else "") or ""
            if aid:
                break

        if "gs_cdn" in cdn:
            cdn_type = "gs_cdn_pc_web"
        elif "lg_cdn" in cdn:
            cdn_type = "lg_cdn_pc_web"
        elif "gcp" in cdn:
            cdn_type = "gs_cdn_pc_web"
        else:
            cdn_type = cdn or "gs_cdn_pc_web"

        # 多清晰度尝试
        for quality in ("original", "hd", "sd"):
            text = self._get(
                rmd + "/broad_stream_assign.html",
                params={
                    "return_type": cdn_type,
                    "broad_key": "%s-common-%s-hls" % (bno, quality),
                },
                referer=referer,
            )
            info = self._json(text)
            view_url = str(info.get("view_url") or "")
            if view_url:
                if aid:
                    sep = "&" if "?" in view_url else "?"
                    return view_url + sep + "aid=" + quote(aid)
                return view_url
        return ""

    def detailContent(self, ids):
        raw = self._pick_id(ids)
        if not raw:
            return {"list": []}
        parts = raw.split("|")
        uid = parts[0]
        bno = parts[1] if len(parts) > 1 else ""
        title, nick, pic = uid, uid, self._pic(uid)
        try:
            ch = self._live_channel(uid, bno)
            if ch:
                title = ch.get("TITLE") or title
                nick = ch.get("BJNICK") or nick
                if ch.get("BNO"):
                    bno = str(ch.get("BNO"))
        except Exception:
            pass
        play_id = uid + (("|" + bno) if bno else "")
        return {
            "list": [{
                "vod_id": play_id,
                "vod_name": str(title)[:80],
                "vod_pic": pic,
                "vod_actor": nick,
                "vod_remarks": "🔴 LIVE",
                "vod_content": "%s 正在直播" % nick,
                "vod_play_from": "SOOP",
                "vod_play_url": "直播$%s" % play_id,
                "style": {"type": "rect", "ratio": 1.78},
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        headers = {
            "User-Agent": self.ua,
            "Referer": self.play_host + "/",
            "Origin": "https://play.sooplive.com",
            "Accept": "*/*",
        }
        raw = str(id or "").strip()
        if "$" in raw:
            raw = raw.split("$")[-1].strip()
        if raw.startswith("http") and self.isVideoFormat(raw):
            return {"parse": 0, "jx": 0, "url": raw, "header": headers}

        parts = raw.split("|")
        uid = parts[0]
        bno = parts[1] if len(parts) > 1 else ""
        page = self.play_host + "/" + uid + (("/" + bno) if bno else "")

        try:
            url = self._resolve_play(uid, bno)
            if url:
                return {"parse": 0, "jx": 0, "url": url, "header": headers}
        except Exception as e:
            print("soop play err", e)
        return {"parse": 1, "jx": 0, "url": page, "header": headers}

    def localProxy(self, param):
        return None


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("home", [c["type_name"] for c in sp.homeContent(False)["class"]])
    r = sp.categoryContent("all", 1, False, {})
    print("cat", len(r.get("list") or []))
    if r.get("list"):
        print(" first", r["list"][0]["vod_name"][:40], r["list"][0]["vod_id"])
        d = sp.detailContent([r["list"][0]["vod_id"]])
        main = d["list"][0]
        print("detail", main.get("vod_name")[:40], main.get("vod_play_from"))
        p = sp.playerContent("SOOP", main["vod_play_url"].split("$")[-1], [])
        print("play", p.get("parse"), str(p.get("url"))[:100])

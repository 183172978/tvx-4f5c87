# -*- coding: utf-8 -*-
"""
哔哩哔哩 —— 由 bilibili99.js 移植
适配 OK影视 / 蜂蜜影视 / TVBox Python 源
分类：关键词搜索；播放：优先 dash 直链 / mp4 durl
"""
import re
import json
import time
import base64
import urllib.parse

try:
    import requests as _requests
    _HAS_REQUESTS = True
except Exception:
    _requests = None
    _HAS_REQUESTS = False

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        pass


def _log(*a):
    try:
        print("哔哩哔哩", *a)
    except Exception:
        pass


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# qn 清晰度
QN_NAME = {
    127: "8K",
    126: "杜比视界",
    125: "HDR",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    80: "1080P",
    74: "720P60",
    64: "720P",
    32: "480P",
    16: "360P",
}

AUDIO_ID = {30280: 192000, 30232: 132000, 30216: 64000}
CODEC = {12: "HEVC", 7: "AVC", 13: "AV1"}


class Spider(_BaseSpider):
    name = "哔哩哔哩"

    def init(self, extend=""):
        self.categories = [
            "音乐", "动画", "电影", "电视剧", "番剧", "综艺",
            "影视", "国创", "娱乐", "游戏", "搞笑", "纪录片",
        ]
        self.cookie = ""
        self.bili_jct = ""
        self.login = False
        self.vip = False
        self.timeout = 15

        # extend: cookie 字符串 或 {"cookie":"...","categories":"a#b#c"}
        try:
            if isinstance(extend, dict):
                ext = extend
            elif extend and str(extend).strip().startswith("{"):
                ext = json.loads(extend)
            else:
                ext = {}
                if extend and "DedeUserID" in str(extend):
                    ext["cookie"] = str(extend).strip()
            if ext.get("categories"):
                raw = ext["categories"]
                if isinstance(raw, list):
                    self.categories = [str(x).strip() for x in raw if str(x).strip()]
                else:
                    self.categories = [x.strip() for x in str(raw).split("#") if x.strip()]
            if ext.get("cookie"):
                self.cookie = str(ext["cookie"]).strip()
        except Exception as e:
            _log("init extend", e)

        if self.cookie:
            for c in self.cookie.split(";"):
                c = c.strip()
                if c.startswith("bili_jct="):
                    self.bili_jct = c.split("=", 1)[1].strip()

        if _HAS_REQUESTS:
            self.session = _requests.Session()
            self.session.headers.update(self._headers())
        else:
            self.session = None

        self._refresh_nav()
        return True

    def getName(self):
        return self.name

    def destroy(self):
        pass

    def _headers(self):
        h = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
        if self.cookie:
            h["Cookie"] = self.cookie
        return h

    def _http_get(self, url, params=None):
        try:
            if _HAS_REQUESTS:
                r = self.session.get(
                    url, params=params, headers=self._headers(),
                    timeout=self.timeout, verify=False
                )
                r.encoding = "utf-8"
                return r.text
            import urllib.request
            full = url
            if params:
                full += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
            req = urllib.request.Request(full, headers=self._headers())
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            _log("http", e)
            return ""

    def _get_json(self, url, params=None):
        try:
            return json.loads(self._http_get(url, params) or "{}")
        except Exception:
            return {}

    def _refresh_nav(self):
        try:
            js = self._get_json("https://api.bilibili.com/x/web-interface/nav")
            data = js.get("data") or {}
            self.login = bool(data.get("isLogin"))
            self.vip = int(data.get("vipStatus") or 0) > 0
        except Exception:
            pass

    def homeContent(self, filter=False):
        classes = [{"type_id": "首页", "type_name": "首页"}]
        for c in self.categories:
            classes.append({"type_id": c, "type_name": c})
        if self.bili_jct:
            classes.append({"type_id": "历史记录", "type_name": "历史记录"})

        order_filter = {
            "key": "order",
            "name": "排序",
            "value": [
                {"n": "综合排序", "v": "0"},
                {"n": "最多点击", "v": "click"},
                {"n": "最新发布", "v": "pubdate"},
                {"n": "最多弹幕", "v": "dm"},
                {"n": "最多收藏", "v": "stow"},
            ],
        }
        duration_filter = {
            "key": "duration",
            "name": "时长",
            "value": [
                {"n": "全部时长", "v": "0"},
                {"n": "60分钟以上", "v": "4"},
                {"n": "30~60分钟", "v": "3"},
                {"n": "10~30分钟", "v": "2"},
                {"n": "10分钟以下", "v": "1"},
            ],
        }
        filters = {}
        for c in classes:
            if c["type_id"] not in ("首页", "历史记录"):
                filters[c["type_id"]] = [order_filter, duration_filter]
        result = {"class": classes, "list": []}
        if filter:
            result["filters"] = filters
        return result

    def homeVideoContent(self):
        return self._rcmd(1)

    def _rcmd(self, page):
        js = self._get_json(
            "https://api.bilibili.com/x/web-interface/index/top/rcmd",
            {"ps": 14, "fresh_idx": page, "fresh_idx_1h": page},
        )
        items = (js.get("data") or {}).get("item") or []
        if not items:
            js = self._get_json(
                "https://api.bilibili.com/x/web-interface/popular",
                {"ps": 20, "pn": page},
            )
            items = (js.get("data") or {}).get("list") or []
        return {"list": self._map_items(items)}

    def _map_items(self, items):
        out = []
        for item in items or []:
            bvid = item.get("bvid")
            if not bvid:
                # 有些结构在 history 里
                bvid = (item.get("history") or {}).get("bvid")
            if not bvid:
                continue
            pic = item.get("pic") or item.get("cover") or ""
            if pic.startswith("//"):
                pic = "https:" + pic
            title = re.sub(r"<[^>]+>", "", item.get("title") or "")
            out.append({
                "vod_id": bvid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": self._fmt_dur(item.get("duration")),
            })
        return out

    def categoryContent(self, tid, pg, filter=False, extend=None):
        extend = extend or {}
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "首页")

        if tid == "首页":
            data = self._rcmd(page)
            lst = data.get("list") or []
            return {
                "list": lst,
                "page": page,
                "pagecount": page + 1 if lst else page,
                "limit": len(lst),
                "total": 9999,
            }

        if tid == "历史记录":
            js = self._get_json(
                "https://api.bilibili.com/x/v2/history",
                {"pn": page},
            )
            raw = js.get("data")
            if isinstance(raw, list):
                items = raw
            else:
                items = (raw or {}).get("list") or []
            # 历史项可能用 history.bvid
            mapped = []
            for it in items:
                bvid = it.get("bvid") or (it.get("history") or {}).get("bvid")
                if not bvid:
                    continue
                pic = it.get("pic") or it.get("cover") or ""
                if pic.startswith("//"):
                    pic = "https:" + pic
                mapped.append({
                    "vod_id": bvid,
                    "vod_name": re.sub(r"<[^>]+>", "", it.get("title") or ""),
                    "vod_pic": pic,
                    "vod_remarks": self._fmt_dur(it.get("duration")),
                })
            return {
                "list": mapped,
                "page": page,
                "pagecount": page + 1 if mapped else page,
                "limit": len(mapped),
                "total": 9999,
            }

        # 分类 = 关键词搜索（失败则热门兜底）
        params = {
            "search_type": "video",
            "keyword": tid,
            "page": page,
        }
        if extend.get("order") and str(extend.get("order")) not in ("0", ""):
            params["order"] = extend["order"]
        if extend.get("duration") and str(extend.get("duration")) not in ("0", ""):
            params["duration"] = extend["duration"]

        js = self._get_json(
            "https://api.bilibili.com/x/web-interface/search/type",
            params,
        )
        data = js.get("data") or {}
        items = data.get("result") or []
        videos = []
        for item in items:
            # type 可能是 "video" 或缺失
            t = item.get("type")
            if t not in (None, "", "video", "ketang"):
                continue
            bvid = item.get("bvid")
            if not bvid:
                continue
            pic = item.get("pic") or ""
            if pic.startswith("//"):
                pic = "https:" + pic
            videos.append({
                "vod_id": bvid,
                "vod_name": re.sub(r"<[^>]+>", "", item.get("title") or ""),
                "vod_pic": pic,
                "vod_remarks": self._fmt_dur(item.get("duration")),
            })

        if not videos:
            # 搜索被风控时用热门 + 关键词过滤标题
            js2 = self._get_json(
                "https://api.bilibili.com/x/web-interface/popular",
                {"ps": 30, "pn": page},
            )
            for item in (js2.get("data") or {}).get("list") or []:
                bvid = item.get("bvid")
                if not bvid:
                    continue
                title = re.sub(r"<[^>]+>", "", item.get("title") or "")
                pic = item.get("pic") or ""
                if pic.startswith("//"):
                    pic = "https:" + pic
                videos.append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": self._fmt_dur(item.get("duration")),
                })

        pc = int(data.get("numPages") or 0) or (page + 1 if videos else page)
        return {
            "list": videos,
            "page": page,
            "pagecount": pc,
            "limit": len(videos),
            "total": int(data.get("numResults") or 0) or len(videos),
        }

    def searchContent(self, key, quick, pg="1"):
        return self.categoryContent(key, pg, False, {})

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        bvid = str(ids[0] if isinstance(ids, (list, tuple)) else ids).strip()
        bvid = bvid.split("$")[-1]
        # 兼容 BV / av
        if bvid.lower().startswith("av"):
            js = self._get_json(
                "https://api.bilibili.com/x/web-interface/view",
                {"aid": bvid[2:]},
            )
        else:
            js = self._get_json(
                "https://api.bilibili.com/x/web-interface/view",
                {"bvid": bvid},
            )
        data = js.get("data") or {}
        if not data:
            return {"list": []}

        aid = data.get("aid")
        pages = data.get("pages") or [{"cid": data.get("cid"), "part": data.get("title") or "正片"}]
        pic = data.get("pic") or ""
        if pic.startswith("//"):
            pic = "https:" + pic

        # 探测可用清晰度
        cid0 = pages[0].get("cid") or data.get("cid")
        qn_list, qn_names = self._accept_quality(aid, cid0)

        # 多线路：dash / mp4
        dash_eps = []
        mp4_eps = []
        for i, pg in enumerate(pages):
            cid = pg.get("cid")
            part = re.sub(r"<[^>]+>", "", pg.get("part") or ("P%d" % (i + 1)))
            # 播放参数：aid|cid|qn1,qn2,...
            token = "%s|%s|%s" % (aid, cid, ",".join(str(q) for q in qn_list))
            # 每个清晰度一条选集
            for q, name in zip(qn_list, qn_names):
                dash_eps.append("%s-%s$%s|%s" % (part, name, token, q))
                mp4_eps.append("%s-%s$%s|%s" % (part, name, token, q))

        # 若无清晰度，至少一条
        if not dash_eps:
            token = "%s|%s|64" % (aid, cid0)
            dash_eps = ["正片$%s|64" % token]
            mp4_eps = list(dash_eps)

        vod = {
            "vod_id": data.get("bvid") or bvid,
            "vod_name": data.get("title") or bvid,
            "vod_pic": pic,
            "type_name": data.get("tname") or "",
            "vod_remarks": self._fmt_dur(data.get("duration")),
            "vod_content": (data.get("desc") or "")[:500],
            "vod_actor": (data.get("owner") or {}).get("name") or "",
            "vod_play_from": "dash$$$mp4",
            "vod_play_url": "#".join(dash_eps) + "$$$" + "#".join(mp4_eps),
        }
        return {"list": [vod]}

    def _accept_quality(self, aid, cid):
        js = self._get_json(
            "https://api.bilibili.com/x/player/playurl",
            {"avid": aid, "cid": cid, "qn": 127, "fnval": 4048, "fourk": 1},
        )
        data = js.get("data") or {}
        accept_q = data.get("accept_quality") or [64, 32, 16]
        accept_d = data.get("accept_description") or []
        qn_list = []
        names = []
        for i, q in enumerate(accept_q):
            q = int(q)
            # 未登录最高 720；登录非大会员最高 1080
            if not self.login and q > 64:
                continue
            if self.login and not self.vip and q > 80:
                continue
            qn_list.append(q)
            if i < len(accept_d) and accept_d[i]:
                names.append(str(accept_d[i]))
            else:
                names.append(QN_NAME.get(q, str(q)))
        if not qn_list:
            qn_list = [int(x) for x in accept_q[:5]]
            names = [QN_NAME.get(q, str(q)) for q in qn_list]
        return qn_list, names

    def playerContent(self, flag, id, vipFlags):
        header = {
            "User-Agent": UA,
            "Referer": "https://www.bilibili.com",
        }
        if self.cookie:
            header["Cookie"] = self.cookie

        raw = str(id or "").strip()
        if raw.startswith("http") and any(x in raw for x in (".m3u8", ".mp4", "bilivideo.com")):
            return {"parse": 0, "jx": 0, "url": raw, "header": header}

        # aid|cid|qnlist|qn  或  aid|cid|qn
        parts = raw.split("|")
        if len(parts) < 2:
            return {"parse": 1, "jx": 1, "url": "https://www.bilibili.com", "header": header}

        aid = parts[0]
        cid = parts[1]
        qn = 64
        if len(parts) >= 4:
            qn = int(parts[3] or 64)
        elif len(parts) == 3:
            # aid|cid|qn  或 aid|cid|qn1,qn2
            if "," in parts[2]:
                qn = int(parts[2].split(",")[0] or 64)
            else:
                qn = int(parts[2] or 64)

        try:
            if flag == "mp4":
                url = self._get_mp4(aid, cid, qn)
            else:
                url = self._get_dash_or_mp4(aid, cid, qn)
            if url:
                return {"parse": 0, "jx": 0, "url": url, "header": header}
        except Exception as e:
            _log("play", e)

        return {
            "parse": 1,
            "jx": 1,
            "url": "https://www.bilibili.com/video/av%s" % aid,
            "header": header,
        }

    def _get_mp4(self, aid, cid, qn):
        js = self._get_json(
            "https://api.bilibili.com/x/player/playurl",
            {"avid": aid, "cid": cid, "qn": qn, "fourk": 1},
        )
        data = js.get("data") or {}
        durl = data.get("durl") or []
        if durl and durl[0].get("url"):
            return durl[0]["url"]
        return ""

    def _get_dash_or_mp4(self, aid, cid, qn):
        js = self._get_json(
            "https://api.bilibili.com/x/player/playurl",
            {"avid": aid, "cid": cid, "qn": qn, "fnval": 4048, "fourk": 1},
        )
        data = js.get("data") or {}
        dash = data.get("dash") or {}
        videos = dash.get("video") or []
        # 匹配 qn
        chosen = None
        for v in videos:
            if int(v.get("id") or 0) == int(qn):
                chosen = v
                break
        if not chosen and videos:
            # 取最高
            videos = sorted(videos, key=lambda x: int(x.get("id") or 0), reverse=True)
            chosen = videos[0]
        if chosen and chosen.get("baseUrl"):
            return chosen["baseUrl"]
        # 回退 durl
        durl = data.get("durl") or []
        if durl and durl[0].get("url"):
            return durl[0]["url"]
        return ""

    @staticmethod
    def _fmt_dur(dur):
        if dur is None or dur == "":
            return ""
        try:
            if isinstance(dur, (int, float)):
                sec = int(dur)
            else:
                s = str(dur).strip()
                if ":" in s:
                    arr = s.split(":")
                    if len(arr) == 2:
                        sec = int(arr[0]) * 60 + int(arr[1])
                    elif len(arr) == 3:
                        sec = int(arr[0]) * 3600 + int(arr[1]) * 60 + int(arr[2])
                    else:
                        sec = int(float(s))
                else:
                    sec = int(float(s))
        except Exception:
            return str(dur)
        if sec <= 0:
            return ""
        if sec >= 3600:
            return "%d时%d分" % (sec // 3600, (sec % 3600) // 60)
        return "%d分%d秒" % (sec // 60, sec % 60)

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(k in u for k in (".m3u8", ".mp4", "bilivideo.com", "akamaized.net"))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("classes", [c["type_name"] for c in sp.homeContent(True)["class"]])
    cat = sp.categoryContent("电影", 1, False, {})
    print("cat", len(cat.get("list") or []))
    if cat.get("list"):
        vid = cat["list"][0]["vod_id"]
        d = sp.detailContent([vid])
        item = (d.get("list") or [{}])[0]
        print("detail", item.get("vod_name"), (item.get("vod_play_from") or ""))
        print("play_url sample", (item.get("vod_play_url") or "")[:120])
        ep = (item.get("vod_play_url") or "").split("$$$")[0].split("#")[0]
        if "$" in ep:
            pid = ep.split("$", 1)[1]
            p = sp.playerContent("dash", pid, [])
            print("play", p.get("parse"), str(p.get("url"))[:90])

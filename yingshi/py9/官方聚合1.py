# -*- coding: utf-8 -*-
"""
爱优腾芒哔哩聚合 —— 影视聚合 Python 源（OK影视 / 蜂蜜影视 / TVBox 通用）
=====================================================================
适配 OK影视、蜂蜜影视、TVBox 类壳子的标准 Python 源。
解析：优先分享者直链 API（huaqi / 12321），失败再走 WebView 解析站。
"""

import re
import json
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


def _log(*args):
    try:
        print("腾爱优聚合", *args)
    except Exception:
        pass


def _enc(value):
    return urllib.parse.quote(str(value), safe="!'()*-._~")


_CATEGORY = {
    "1": ("qq", "腾讯视频"),
    "2": ("qiyi", "爱奇艺"),
    "3": ("youku", "优酷视频"),
    "4": ("mgtv", "芒果TV"),
    "5": ("bilibili", "B站"),
}
_KEY_TO_NUM = {v[0]: k for k, v in _CATEGORY.items()}


class Spider(_BaseSpider):
    name = "腾爱优聚合"

    def init(self, extend=""):
        _log("init ->", extend)
        self.host = "http://cj.tianwe.cn"
        self.header = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        # 直链解析 API（返回 JSON.url = m3u8）
        # 每项: (api前缀, 可选专用 UA)；先试稳定源，再试分享者解析2
        self.parse_apis = [
            ("https://api.huaqi.pro/api/?key=5bd0db7c858ba9f999373450f3651af7&url=", None),
            ("https://test1.12321app.com/daoliansiquanjia.php?url=", None),
            ("http://mg.itufm.top/mg.php?url=", "okhttp/4.9.1"),
        ]
        # WebView 解析站兜底（壳子内置浏览器打开）
        self.parse_sites = [
            "https://jx.xmflv.com/?url=",
            "https://jx.playerjy.com/?url=",
            "https://jx.2s0.cn/?url=",
            "https://jx.m3u8.tv/jiexi/?url=",
            "https://www.daga.cc/vip1/?url=",
            "https://jx.xmflv.cc/?url=",
        ]
        self.custom_jx = self._parse_extend(extend)
        self.timeout = 12
        if _HAS_REQUESTS:
            self.session = _requests.Session()
            self.session.headers.update(self.header)

    @staticmethod
    def _parse_extend(extend):
        if not extend:
            return ""
        s = str(extend).strip()
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                # 支持 {"parse":"url="} 或 {"apis":["...","..."]}
                apis = d.get("apis") or d.get("parse_apis")
                if isinstance(apis, list) and apis:
                    return apis  # 特殊：返回 list
                return str(d.get("parse", "") or d.get("jx", "")).strip()
        except Exception:
            pass
        if "url=" in s or "?" in s:
            return s
        return ""

    def getName(self):
        return self.name

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv"))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def _http_get(self, url):
        try:
            if _HAS_REQUESTS:
                sess = getattr(self, "session", None) or _requests
                r = sess.get(url, timeout=getattr(self, "timeout", 15), verify=False)
                r.encoding = "utf-8"
                return r.text
            import urllib.request
            req = urllib.request.Request(url, headers=self.header)
            with urllib.request.urlopen(req, timeout=getattr(self, "timeout", 15)) as resp:
                data = resp.read()
                try:
                    return data.decode("utf-8")
                except Exception:
                    return data.decode("latin-1")
        except Exception as exc:
            _log("myfetch err ", exc)
            return ""

    def _get_json(self, url):
        try:
            return json.loads(self._http_get(url))
        except Exception:
            return None

    def homeContent(self, filter=False):
        try:
            classes = [
                {"type_id": "1", "type_pid": "0", "type_name": "腾讯视频"},
                {"type_id": "2", "type_pid": "0", "type_name": "爱奇艺"},
                {"type_id": "3", "type_pid": "0", "type_name": "优酷视频"},
                {"type_id": "4", "type_pid": "0", "type_name": "芒果TV"},
                {"type_id": "5", "type_pid": "0", "type_name": "B站"},
            ]
            type_filter = {
                "key": "class",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "电视剧", "v": "2"},
                    {"n": "电影", "v": "1"},
                    {"n": "动漫", "v": "4"},
                    {"n": "综艺", "v": "3"},
                    {"n": "少儿", "v": "5"},
                    {"n": "纪录片", "v": "6"},
                    {"n": "短剧", "v": "7"},
                ],
            }
            year_filter = {
                "key": "year",
                "name": "年份",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                ],
            }
            filters = {}
            for c in classes:
                filters[c["type_id"]] = [type_filter, year_filter]
            result = {"class": classes, "list": []}
            if filter:
                result["filters"] = filters
            return result
        except Exception as exc:
            _log("homeContent err", exc)
            return {"class": [], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        extend = extend or {}
        key = self._to_key(tid) or "qq"
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1

        params = ["from=" + key, "ac=detail", "limit=24", "pg=" + str(page)]
        t = extend.get("class") or "2"
        params.append("t=" + t)
        if extend.get("year"):
            params.append("year=" + _enc(extend["year"]))

        url = self.host + "/api.php/provide/vod/?" + "&".join(params)
        _log("api category url ->", url)

        data = self._get_json(url)
        if not data:
            return {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}

        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name", ""),
                    "vod_pic": v.get("vod_pic", ""),
                    "vod_remarks": v.get("vod_remarks", ""),
                }
                for v in data["list"]
            ]

        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1

        return {
            "list": vod_list,
            "page": page,
            "pagecount": pc,
            "limit": len(vod_list),
            "total": pc * len(vod_list) if vod_list else 0,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = str(ids)
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0])
        vid = vid.split("$")[-1].strip()

        url = self.host + "/api.php/provide/vod/?" + "&".join(["ac=detail", "ids=" + vid])
        _log("detailurl", url)

        data = self._get_json(url)
        if not data:
            return {"list": []}

        vod_list = []
        if isinstance(data.get("list"), list):
            for item in data["list"]:
                if not item.get("vod_id"):
                    continue
                vod_list.append({
                    "vod_id": str(item.get("vod_id", "")),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "vod_year": item.get("vod_year", ""),
                    "type_name": item.get("type_name", ""),
                    "vod_area": item.get("vod_area", ""),
                    "vod_lang": item.get("vod_lang", ""),
                    "vod_content": item.get("vod_content", ""),
                    "vod_play_from": item.get("vod_play_from", ""),
                    "vod_play_url": item.get("vod_play_url", ""),
                })
        return {"list": vod_list}

    def searchContent(self, key, quick, pg="1"):
        if not key:
            return {"list": []}
        url = (
            self.host
            + "/api.php/provide/vod/?ac=detail&wd="
            + _enc(key)
            + "&pg="
            + str(pg)
        )
        _log("api searchUrl:", url)

        data = self._get_json(url)
        if not data:
            return {"list": [], "page": str(pg), "pagecount": 1}

        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name") or v.get("name") or "",
                    "vod_pic": v.get("vod_pic") or v.get("pic") or "",
                    "vod_remarks": v.get("vod_remarks") or "",
                }
                for v in data["list"]
                if v.get("vod_id")
            ]

        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1
        return {"list": vod_list, "page": str(pg), "pagecount": pc}

    # ------------------------------------------------------------------
    # 播放
    # ------------------------------------------------------------------
    def playerContent(self, flag, id, vipFlags):
        _log("开始获取播放地址: ", id)
        try:
            if self._is_direct(id):
                ref = self._origin(id)
                hdr = dict(self.header)
                if ref:
                    hdr["Referer"] = ref
                return {"parse": 0, "url": id, "header": hdr, "playUrl": "", "jx": 0}

            # 1) 用户自定义解析站
            cjx = getattr(self, "custom_jx", "")
            if isinstance(cjx, list):
                # extend 传入 apis 列表时并入直链解析
                for api in cjx:
                    play = self._parse_with_api(api, id)
                    if play:
                        return self._direct_result(play)
            elif cjx:
                _log("使用自定义解析:", cjx + id)
                return {
                    "parse": 1,
                    "url": cjx + id,
                    "header": dict(self.header),
                    "playUrl": "",
                    "jx": 1,
                }

            # 2) 直链解析 API（分享者 huaqi / 12321）
            play_url = self._parse_video_url(id)
            if play_url:
                return self._direct_result(play_url)

            # 3) WebView 解析站兜底
            web_url = self._webview_jx(id)
            if web_url:
                return {
                    "parse": 1,
                    "url": web_url,
                    "header": dict(self.header),
                    "playUrl": "",
                    "jx": 1,
                }
        except Exception as exc:
            _log("play失败: ", exc)
        return {
            "parse": 1,
            "url": id,
            "header": dict(self.header),
            "playUrl": "",
            "jx": 1,
        }

    def _direct_result(self, play_url):
        ref = self._origin(play_url)
        hdr = dict(self.header)
        if ref:
            hdr["Referer"] = ref
            hdr["Origin"] = ref.rstrip("/")
        return {
            "parse": 0,
            "jx": 0,
            "url": play_url,
            "playUrl": "",
            "header": hdr,
        }

    @staticmethod
    def _origin(url):
        m = re.match(r"(https?://[^/]+)/", str(url or ""))
        return (m.group(1) + "/") if m else ""

    def _webview_jx(self, video_url):
        for site in getattr(self, "parse_sites", None) or []:
            if site:
                return site + video_url
        return ""

    def _is_direct(self, url):
        s = str(url).lower()
        return any(k in s for k in (".m3u8", ".mp4", ".flv", ".mkv"))

    def _parse_with_api(self, api, video_url, ua=None):
        if not api:
            return ""
        try:
            if api.endswith("url="):
                resolve = api + video_url
            else:
                resolve = api + _enc(video_url)
            # 临时 UA（如 okhttp）
            old_ua = None
            if ua and _HAS_REQUESTS and getattr(self, "session", None):
                old_ua = self.session.headers.get("User-Agent")
                self.session.headers["User-Agent"] = ua
            try:
                text = self._http_get(resolve)
            finally:
                if old_ua is not None:
                    self.session.headers["User-Agent"] = old_ua
            if not text:
                return ""
            # JSON
            try:
                data = json.loads(text)
            except Exception:
                data = None
            if isinstance(data, dict):
                code = data.get("code")
                if code is not None and int(code) not in (200, 0, 1):
                    # 继续尝试下一家
                    pass
                else:
                    for k in ("url", "Url", "play_url", "play", "m3u8", "data"):
                        v = data.get(k)
                        if isinstance(v, dict):
                            v = v.get("url") or v.get("play")
                        if v and isinstance(v, str) and v.startswith("http"):
                            u = self._format_url(v)
                            if self._is_direct(u) or u.startswith("http"):
                                _log("解析成功", api[:40], "->", u[:80])
                                return u
            # 裸链
            m = re.search(
                r"https?://[^\s\"'<>\\]+\.(?:m3u8|mp4)[^\s\"'<>\\]*",
                text.replace("\\/", "/"),
            )
            if m:
                return self._format_url(m.group(0))
        except Exception as exc:
            _log("api fail", api[:40], exc)
        return ""

    def _parse_video_url(self, video_url):
        for item in getattr(self, "parse_apis", []) or []:
            if isinstance(item, (list, tuple)):
                api, ua = item[0], (item[1] if len(item) > 1 else None)
            else:
                api, ua = item, None
            play = self._parse_with_api(api, video_url, ua=ua)
            if play:
                return play
        return ""

    @staticmethod
    def _format_url(url):
        if not url:
            return ""
        url = str(url).replace("\\/", "/").replace("\\", "")
        url = re.sub(r"^(https?:/)([^/])", r"\1/\2", url, flags=re.IGNORECASE)
        return url

    @staticmethod
    def _to_key(tid):
        if tid is None:
            return None
        s = str(tid).strip()
        if s in _CATEGORY:
            return _CATEGORY[s][0]
        if s in _KEY_TO_NUM:
            return s
        return s


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print(sp.homeContent(True).get("class"))
    cat = sp.categoryContent("1", 1, False, {"class": "2"})
    print("cat", len(cat.get("list") or []))
    if cat.get("list"):
        vid = cat["list"][0]["vod_id"]
        d = sp.detailContent([vid])
        item = (d.get("list") or [{}])[0]
        print("detail", item.get("vod_name"), (item.get("vod_play_from") or "")[:40])
        urls = item.get("vod_play_url") or ""
        ep = ""
        for seg in urls.split("#"):
            if "$" in seg:
                ep = seg.split("$", 1)[1]
                break
        if ep:
            p = sp.playerContent("qq", ep, [])
            print("play parse", p.get("parse"), "url", str(p.get("url"))[:100])

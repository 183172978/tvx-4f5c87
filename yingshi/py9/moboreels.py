from __future__ import annotations

import math
from urllib.parse import quote

import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            self.extend = ""


class Spider(BaseSpider):
    """MoboReels 简体中文公开内容 Spider。

    仅列出 langId=1 的简体中文内容，并只暴露服务端明确标记为公开免费的剧集。
    """

    WEB = "https://www.moboreels.com"
    VIDEO_API = "https://videoapi-hk.cdreader.com/video"
    BACKEND_API = "https://videoapi-hk.cdreader.com"
    LANG_ID = "1"
    PAGE_SIZE = 30

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Origin": self.WEB,
            "Referer": self.WEB + "/cn/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        })

    def getName(self):
        return "MoboReels简中"

    def init(self, extend=""):
        self.extend = extend or ""

    def getDependence(self):
        return []

    def destroy(self):
        return None

    def _post(self, base, path, body):
        response = self.session.post(base + path, json=body, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if int(payload.get("code", 0)) != 200:
            raise RuntimeError(payload.get("message") or "MoboReels API error")
        return payload.get("data") or {}

    def _home(self):
        return self._post(self.VIDEO_API, "/h5/series/home", {
            "langId": self.LANG_ID,
            "take": 50,
        })

    def _types(self):
        data = self._post(self.BACKEND_API, "/backend/series/typeList", {
            "langId": self.LANG_ID,
        })
        if isinstance(data, list):
            return data
        return data.get("list") or []

    def _type_page(self, type_id, page):
        return self._post(self.BACKEND_API, "/backend/series/typePage", {
            "langId": self.LANG_ID,
            "skip": (max(1, int(page)) - 1) * self.PAGE_SIZE,
            "take": self.PAGE_SIZE,
            "typeId": str(type_id or "0"),
        })

    def _detail(self, series_id, episode=1):
        return self._post(self.VIDEO_API, "/h5/series/homeSeriesDetail", {
            "langId": self.LANG_ID,
            "seriesId": str(series_id),
            "episNum": int(episode),
        })

    @staticmethod
    def _series_id(item):
        return str(item.get("seriesId") or "")

    @staticmethod
    def _cover(item):
        url = str(item.get("coverUrl") or "").strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://"):
            return "https://" + url[7:]
        return url

    def _vod(self, item):
        total = item.get("allEpis") or item.get("lastEpis") or ""
        types = item.get("types") or []
        remark = f"{total}集" if total else "/".join(str(x) for x in types[:2])
        return {
            "vod_id": self._series_id(item),
            "vod_name": str(item.get("seriesName") or "未知短剧"),
            "vod_pic": self._cover(item),
            "vod_remarks": remark,
            "vod_content": str(item.get("description") or item.get("summary") or ""),
        }

    def homeContent(self, filter=False):
        classes = [{"type_id": "0", "type_name": "全部"}]
        seen = {"0"}
        try:
            for item in self._types():
                name = str(item.get("typeName") or "").strip()
                type_id = str(item.get("typeIdStr") or item.get("typeId") or "0")
                if name and type_id not in seen:
                    classes.append({"type_id": type_id, "type_name": name})
                    seen.add(type_id)
        except Exception:
            pass
        return {"class": classes}

    def homeVideoContent(self):
        videos = []
        seen = set()
        try:
            data = self._home()
            for key in ("homeListVO1", "homeListVO2", "homeListVO3", "homeListVO4"):
                for item in (data.get(key) or {}).get("seriesList") or []:
                    if str(item.get("language")) != self.LANG_ID:
                        continue
                    series_id = self._series_id(item)
                    if series_id and series_id not in seen:
                        videos.append(self._vod(item))
                        seen.add(series_id)
        except Exception:
            pass
        return {"list": videos}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = max(1, int(pg or 1))
        try:
            data = self._type_page(tid, page)
            items = data.get("seriesList") or []
        except Exception:
            data, items = {}, []
        videos = [self._vod(item) for item in items if self._series_id(item)]
        has_next = len(items) >= self.PAGE_SIZE and int(data.get("skipSeries", -1)) > (page - 1) * self.PAGE_SIZE
        pagecount = page + 1 if has_next else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": self.PAGE_SIZE,
            "total": pagecount * self.PAGE_SIZE if has_next else (page - 1) * self.PAGE_SIZE + len(videos),
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        series_id = str(ids[0])
        try:
            data = self._detail(series_id, 1)
            series = data.get("seriesVO") or {}
            if str(series.get("language")) != self.LANG_ID:
                return {"list": []}
            all_episodes = max(1, int(series.get("allEpis") or series.get("lastEpis") or 1))
            pay_from = int(series.get("payEpisFrom") or (all_episodes + 1))
            # The anonymous web API only supplies media before payEpisFrom.
            free_end = min(all_episodes, max(0, pay_from - 1))
            if free_end <= 0:
                epis = data.get("episVO") or {}
                free_end = 1 if epis.get("isFree") is True and epis.get("isLock") is False else 0
            play_urls = [f"第{ep}集${series_id}_{ep}" for ep in range(1, free_end + 1)]
            vod = self._vod(series)
            vod.update({
                "vod_year": str(series.get("datePublished") or "")[:4],
                "vod_area": "简体中文",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": str(series.get("description") or ""),
                "vod_play_from": "MoboReels免费",
                "vod_play_url": "#".join(play_urls),
            })
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    @staticmethod
    def _episode_id(value):
        series_id, episode = str(value).rsplit("_", 1)
        return series_id, int(episode)

    @staticmethod
    def _select_media(epis):
        media = epis.get("episMedia") or []
        h264 = [x for x in media if str(x.get("codec") or "").lower() == "h264" and x.get("mediaUrl")]
        if h264:
            h264.sort(key=lambda x: int(x.get("resolution") or 0), reverse=True)
            return str(h264[0].get("mediaUrl"))
        for item in media:
            if item.get("mediaUrl"):
                return str(item.get("mediaUrl"))
        return str(epis.get("mediaUrl") or epis.get("m3u8Url") or "")

    def playerContent(self, flag, id, vipFlags=None):
        try:
            series_id, episode = self._episode_id(id)
            data = self._detail(series_id, episode)
            series = data.get("seriesVO") or {}
            epis = data.get("episVO") or {}
            if str(series.get("language")) != self.LANG_ID:
                raise RuntimeError("非简体中文内容")
            if int(epis.get("episNum") or 0) != episode:
                raise RuntimeError("集数不匹配")
            if epis.get("isFree") is not True or epis.get("isLock") is not False:
                raise RuntimeError("该集未向匿名网页公开媒体")
            url = self._select_media(epis)
            if not url:
                raise RuntimeError("无公开媒体地址")
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": {
                    "Referer": self.WEB + "/",
                    "User-Agent": self.session.headers["User-Agent"],
                },
            }
        except Exception:
            return {"parse": 1, "playUrl": "", "url": "", "header": {}}

    def searchContent(self, key, quick=False, pg="1"):
        page = max(1, int(pg or 1))
        try:
            data = self._post(self.BACKEND_API, "/backend/search/pageByEs", {
                "searchKey": str(key),
                "searchType": 1,
                "langId": self.LANG_ID,
                "mainReq": {"pageNo": page, "pageSize": self.PAGE_SIZE},
            })
            main = data.get("mainData") or {}
            rows = [x for x in main.get("rows") or [] if str(x.get("language")) == self.LANG_ID]
            total = int(main.get("total") or len(rows))
        except Exception:
            rows, total = [], 0
        return {
            "list": [self._vod(item) for item in rows],
            "page": page,
            "pagecount": max(1, math.ceil(total / self.PAGE_SIZE)) if total else 1,
            "limit": self.PAGE_SIZE,
            "total": total,
        }

    def localProxy(self, param):
        return [404, "text/plain", "not used"]

    def isVideoFormat(self, url):
        value = str(url or "").lower().split("?", 1)[0]
        return value.endswith((".mp4", ".m3u8", ".flv"))

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return ""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稀饭动漫 https://dm.xifanacg.com / https://anime.xifanacg.com
分类：连载新番 / 完结旧番 / 剧场版 / 美漫
播放：player_aaaa
修复：主线 xfxf1(apn.moedot.net) 需走 player.moedot.net 解析；
      线路重排，可用线路优先
"""
import json
import re
import gzip
import base64
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


HOST = "https://anime.xifanacg.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# from 字段 → 解析站（MacPlayerConfig.player_list，ps=1）
PARSE_MAP = {
    "xfxf1": "https://player.moedot.net/player/index.php?code=xfdm2&url=",
    "AL": "https://player.moedot.net/player/index.php?code=xfdm1&from=cf&url=",
    "xfy2": "https://player.moedot.net/player/index.php?code=xfdm1&from=cf&url=",
    "CS": "https://player.moedot.net/player/index.php?code=xfdm1&from=cf&url=",
}

CLASSES = [
    {"type_id": "1", "type_name": "连载新番"},
    {"type_id": "2", "type_name": "完结旧番"},
    {"type_id": "3", "type_name": "剧场版"},
    {"type_id": "21", "type_name": "美漫"},
]

FILTERS = {
    "1": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "搞笑", "v": "搞笑"}, {"n": "恋爱", "v": "恋爱"},
            {"n": "校园", "v": "校园"}, {"n": "战斗", "v": "战斗"}, {"n": "治愈", "v": "治愈"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "日常", "v": "日常"}, {"n": "热血", "v": "热血"},
            {"n": "异世界", "v": "异世界"}, {"n": "科幻", "v": "科幻"}, {"n": "冒险", "v": "冒险"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
            {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
        ]},
        {"key": "by", "name": "排序", "value": [
            {"n": "最新", "v": "time"}, {"n": "最热", "v": "hits"}, {"n": "评分", "v": "score"},
        ]},
    ],
}
FILTERS["2"] = FILTERS["1"]
FILTERS["3"] = FILTERS["1"]
FILTERS["21"] = FILTERS["1"]


class Spider(BaseSpider):
    def getName(self):
        return "稀饭动漫"

    def init(self, extend=""):
        pass

    def _headers(self, extra=None):
        h = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if extra:
            h.update(extra)
        return h

    def _get(self, url, headers=None, timeout=15):
        try:
            if requests is not None:
                r = requests.get(
                    url, headers=self._headers(headers),
                    timeout=timeout, verify=False, allow_redirects=True,
                )
                return r.text or ""
            req = urllib.request.Request(url, headers=self._headers(headers))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "ignore")
        except Exception as e:
            print("get err", url, e)
            return ""

    def _post(self, url, data, headers=None):
        try:
            h = self._headers(headers)
            h.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            if requests is not None:
                r = requests.post(url, data=data, headers=h, timeout=15, verify=False)
                return r.text or ""
            body = urllib.parse.urlencode(data).encode("utf-8") if isinstance(data, dict) else (
                data.encode("utf-8") if isinstance(data, str) else data
            )
            req = urllib.request.Request(url, data=body, headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("post err", e)
            return ""

    def _abs(self, u):
        if not u:
            return ""
        u = str(u).strip().replace("\\/", "/")
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("/"):
            return HOST + u
        return u

    def _clean(self, t):
        t = re.sub(r"<[^>]+>", " ", str(t or ""))
        t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
        return re.sub(r"\s+", " ", t).strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'class="public-list-exp"[^>]*href="([^"]+)"[^>]*title="([^"]+)"[\s\S]{0,600}?(?:data-src|src)="([^"]+)"',
            html, re.I,
        ):
            href, title, pic = m.group(1), self._clean(m.group(2)), m.group(3)
            if "data:image" in pic:
                near = html[m.start():m.start() + 800]
                pm = re.search(r'data-src="(https?://[^"]+)"', near)
                if pm:
                    pic = pm.group(1)
            vid = href
            mid = re.search(r"/bangumi/(\d+)", href)
            if mid:
                vid = mid.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            remarks = ""
            near = html[m.start():m.start() + 900]
            rm = re.search(r'class="public-list-prb[^"]*"[^>]*>([\s\S]*?)</span>', near)
            if rm:
                remarks = self._clean(rm.group(1))
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._abs(pic) if not str(pic).startswith("data:") else "",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 0.68},
            })
        if len(videos) < 4:
            for m in re.finditer(r'href="(/bangumi/(\d+)\.html)"[^>]*(?:title="([^"]*)")?', html):
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                title = self._clean(m.group(3) or "")
                if not title:
                    near = html[m.start():m.start() + 200]
                    tm = re.search(r">([^<]{2,60})</a>", near)
                    if tm:
                        title = self._clean(tm.group(1))
                videos.append({
                    "vod_id": vid,
                    "vod_name": title or ("番剧#" + vid),
                    "vod_pic": "",
                    "vod_remarks": "",
                    "style": {"type": "rect", "ratio": 0.68},
                })
        return videos

    def _list_from_api(self, tid, pg, extend=None):
        ext = extend or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}
        body = {
            "type": str(tid or "1"),
            "page": str(pg or 1),
            "by": str(ext.get("by") or "time"),
        }
        if ext.get("class"):
            body["class"] = str(ext["class"])
        if ext.get("area"):
            body["area"] = str(ext["area"])
        if ext.get("year"):
            body["year"] = str(ext["year"])
        txt = self._post(
            HOST + "/index.php/ds_api/vod",
            body,
            {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "%s/type/%s.html" % (HOST, tid),
            },
        )
        # API 有时返回纯文本提示而非 JSON
        if not txt or not txt.strip().startswith("{"):
            return [], 1, 0
        try:
            d = json.loads(txt)
        except Exception:
            return [], 1, 0
        if not isinstance(d, dict):
            return [], 1, 0
        lst = []
        for it in d.get("list") or []:
            vid = str(it.get("vod_id") or it.get("id") or "")
            name = it.get("vod_name") or it.get("name") or ""
            pic = str(it.get("vod_pic") or it.get("pic") or "").replace("\\/", "/")
            url = it.get("url") or ""
            if not vid and url:
                m = re.search(r"/bangumi/(\d+)", url)
                if m:
                    vid = m.group(1)
            if not vid or not name:
                continue
            lst.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._abs(pic),
                "vod_remarks": it.get("vod_remarks") or "",
                "style": {"type": "rect", "ratio": 0.68},
            })
        try:
            pc = int(d.get("pagecount") or 1)
        except Exception:
            pc = 1
        try:
            total = int(d.get("total") or len(lst))
        except Exception:
            total = len(lst)
        return lst, max(pc, 1), total

    def homeContent(self, filter=False):
        return {"class": CLASSES, "list": [], "filters": FILTERS}

    def homeVideoContent(self):
        html = self._get(HOST + "/")
        return {"list": self._parse_list(html)[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or "1")
        videos, pc, total = self._list_from_api(tid, pg, extend)
        if not videos:
            if pg <= 1:
                url = "%s/type/%s.html" % (HOST, tid)
            else:
                url = "%s/type/%s/page/%d.html" % (HOST, tid, pg)
            html = self._get(url)
            videos = self._parse_list(html)
            pc = pg + 1 if len(videos) >= 16 else max(pg, 1)
            total = 9999 if videos else 0
        return {
            "list": videos,
            "page": pg,
            "pagecount": pc,
            "limit": 40,
            "total": total,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        url = "%s/index.php/ajax/suggest?mid=1&wd=%s" % (HOST, urllib.parse.quote(str(key)))
        txt = self._get(url, {"X-Requested-With": "XMLHttpRequest", "Referer": HOST + "/"})
        try:
            d = json.loads(txt or "{}")
        except Exception:
            d = {}
        videos = []
        for it in d.get("list") or []:
            vid = str(it.get("id") or "")
            if not vid:
                continue
            videos.append({
                "vod_id": vid,
                "vod_name": it.get("name") or "",
                "vod_pic": self._abs(str(it.get("pic") or "").replace("\\/", "/")),
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 0.68},
            })
        return {
            "list": videos,
            "page": pg,
            "pagecount": int(d.get("pagecount") or 1),
            "limit": 20,
            "total": int(d.get("total") or len(videos)),
        }

    def _line_priority(self, name):
        """可用线路优先：备用 > 主线-2 > 主线-1"""
        n = (name or "").lower()
        if "备用" in n or "備份" in n or "cs" in n:
            return 0
        if "主线-2" in n or "主線-2" in n or "主线2" in n:
            return 1
        if "主线-1" in n or "主線-1" in n or "主线1" in n:
            return 3
        if "主线" in n or "主線" in n:
            return 2
        return 1

    def detailContent(self, ids):
        raw = str((ids or [""])[0]).strip()
        if raw.startswith("http"):
            url = raw
            m = re.search(r"/bangumi/(\d+)", raw)
            vid = m.group(1) if m else raw
        else:
            vid = re.sub(r"\D", "", raw) or raw
            url = "%s/bangumi/%s.html" % (HOST, vid)
        html = self._get(url)
        name = "番剧#" + str(vid)
        m = re.search(r"<h3>([\s\S]*?)</h3>", html or "", re.I)
        if m:
            name = self._clean(m.group(1))
        if not name or name.startswith("番剧"):
            m = re.search(r"<title>([^<]+)</title>", html or "", re.I)
            if m:
                name = self._clean(re.sub(r"\s*-\s*.*$", "", m.group(1)))
        pic = ""
        m = re.search(r'<div class="detail-pic">[\s\S]*?(?:data-src|src)="([^"]+)"', html or "", re.I)
        if m:
            pic = self._abs(m.group(1))
        remarks = ""
        m = re.search(r'class="slide-info-remarks cor5"[^>]*>([\s\S]*?)</span>', html or "", re.I)
        if m:
            remarks = self._clean(m.group(1))
        content = ""
        m = re.search(r'id="height_limit"[^>]*>([\s\S]*?)</div>', html or "", re.I)
        if m:
            content = self._clean(m.group(1))[:500]

        tab_names = []
        for m in re.finditer(r'<a class="swiper-slide">[\s\S]*?&nbsp;([^<]+)<span class="badge">', html or ""):
            tab_names.append(self._clean(m.group(1)))
        # data-form 备用
        if not tab_names:
            for m in re.finditer(r'data-form="([^"]+)"[^>]*>[\s\S]*?&nbsp;([^<]+)', html or ""):
                tab_names.append(self._clean(m.group(2)) or m.group(1))

        froms, urls = [], []
        boxes = re.findall(
            r'<ul class="anthology-list-play size">([\s\S]*?)</ul>',
            html or "",
            re.I,
        )
        pairs = []  # (priority, name, eps_str)
        if not boxes:
            groups = {}
            order = []
            for m in re.finditer(
                r'href="([^"]*/watch/(\d+)/(\d+)/(\d+)\.html)"[^>]*>\s*(?:<span>)?([^<]+)',
                html or "",
            ):
                sid = m.group(3)
                if sid not in groups:
                    groups[sid] = []
                    order.append(sid)
                groups[sid].append(
                    (self._clean(m.group(5)), self._abs(m.group(1)))
                )
            for i, sid in enumerate(order):
                tname = tab_names[i] if i < len(tab_names) else ("线路%d" % (i + 1))
                eps = "#".join("%s$%s" % (n, u) for n, u in groups[sid])
                pairs.append((self._line_priority(tname), tname, eps))
        else:
            for i, box in enumerate(boxes):
                eps = []
                for m in re.finditer(
                    r'href="([^"]*/watch/[^"]+)"[^>]*>\s*(?:<span>)?([^<]+)',
                    box,
                ):
                    eps.append("%s$%s" % (self._clean(m.group(2)), self._abs(m.group(1))))
                if eps:
                    tname = tab_names[i] if i < len(tab_names) else ("线路%d" % (i + 1))
                    pairs.append((self._line_priority(tname), tname, "#".join(eps)))

        pairs.sort(key=lambda x: x[0])
        for _, tname, eps in pairs:
            froms.append(tname)
            urls.append(eps)

        if not froms:
            froms = ["默认"]
            urls = ["正片$%s" % url]

        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_content": content or "稀饭动漫",
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
            "style": {"type": "rect", "ratio": 0.68},
        }]}

    def _decode_player_url(self, encoded, encrypt):
        u = str(encoded or "").replace("\\/", "/")
        try:
            enc = int(encrypt or 0)
        except Exception:
            enc = 0
        if enc == 1:
            try:
                u = urllib.parse.unquote(u)
            except Exception:
                pass
        elif enc == 2:
            try:
                u = urllib.parse.unquote(base64.b64decode(u).decode("utf-8", "ignore"))
            except Exception:
                pass
        if u and not u.startswith("http"):
            u = self._abs(u)
        return u

    def _need_parse(self, url, frm):
        """主线 xfxf1 / apn.moedot.net 直链不可播，需解析"""
        u = (url or "").lower()
        f = (frm or "").lower()
        if f in ("xfxf1",) or "apn.moedot.net" in u or "pan.wo.cn" in u:
            return True
        return False

    def _parse_via_moedot(self, raw_url, frm):
        """调用 player.moedot.net 取可播地址"""
        base = PARSE_MAP.get(frm) or PARSE_MAP.get("xfxf1")
        if not base or not raw_url:
            return ""
        api = base + urllib.parse.quote(raw_url, safe="")
        html = self._get(api, {"Referer": HOST + "/"}, timeout=12)
        if not html:
            return ""
        # JSON
        try:
            j = json.loads(html)
            for k in ("url", "Url", "src", "play", "video"):
                v = j.get(k) if isinstance(j, dict) else None
                if isinstance(v, str) and v.startswith("http"):
                    return v.replace("\\/", "/")
        except Exception:
            pass
        # HTML / 文本里找 m3u8 mp4
        m = re.search(r"https?://[^\"'\s<>]+?\.(?:m3u8|mp4)[^\"'\s<>]*", html.replace("\\/", "/"), re.I)
        if m:
            return m.group(0)
        m = re.search(r'["\']url["\']\s*[:=]\s*["\'](https?://[^"\']+)["\']', html)
        if m:
            return m.group(1).replace("\\/", "/")
        return ""

    def playerContent(self, flag, id, vipFlags=None):
        head = {"User-Agent": UA, "Referer": HOST + "/", "Origin": HOST}
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        if play.startswith("http") and re.search(r"\.(m3u8|mp4)(\?|$)", play, re.I):
            # 已是直链但可能是失效主线 CDN
            if self._need_parse(play, ""):
                real = self._parse_via_moedot(play, "xfxf1")
                if real:
                    return {
                        "parse": 0, "jx": 0, "url": real, "header": head,
                        "format": "application/x-mpegURL" if ".m3u8" in real.lower() else "video/mp4",
                    }
                # 解析站慢/挂：交给客户端打开解析页
                purl = PARSE_MAP["xfxf1"] + urllib.parse.quote(play, safe="")
                return {"parse": 1, "jx": 0, "url": purl, "header": head}
            return {
                "parse": 0, "jx": 0, "url": play, "header": head,
                "format": "application/x-mpegURL" if ".m3u8" in play.lower() else "video/mp4",
            }

        page = play if play.startswith("http") else self._abs(play)
        html = self._get(page, {"Referer": HOST + "/"})
        m = re.search(r"var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>", html or "", re.I)
        if m:
            try:
                player = json.loads(m.group(1))
            except Exception:
                player = {}
            url = self._decode_player_url(player.get("url"), player.get("encrypt"))
            frm = str(player.get("from") or "")
            if url:
                # 主线需解析
                if self._need_parse(url, frm):
                    real = self._parse_via_moedot(url, frm or "xfxf1")
                    if real:
                        return {
                            "parse": 0, "jx": 0, "url": real, "header": head,
                            "format": "application/x-mpegURL" if ".m3u8" in real.lower() else "video/mp4",
                        }
                    parse_base = PARSE_MAP.get(frm) or PARSE_MAP.get("xfxf1")
                    if parse_base:
                        return {
                            "parse": 1, "jx": 0,
                            "url": parse_base + urllib.parse.quote(url, safe=""),
                            "header": head,
                        }
                # 备用 / 主线-2 等可直出
                direct = bool(re.search(r"\.(m3u8|mp4)(\?|$)", url, re.I))
                if direct:
                    # mp4 CDN 用对应 Referer 更稳
                    if "xfvod.pro" in url or "playxf" in url or "moedot" in url:
                        head = {
                            "User-Agent": UA,
                            "Referer": HOST + "/",
                            "Origin": HOST,
                        }
                    return {
                        "parse": 0, "jx": 0, "url": url, "header": head,
                        "format": "application/x-mpegURL" if ".m3u8" in url.lower() else "video/mp4",
                    }
                # 非直链但有 from 解析配置
                parse_base = PARSE_MAP.get(frm)
                if parse_base:
                    return {
                        "parse": 1, "jx": 0,
                        "url": parse_base + urllib.parse.quote(url, safe=""),
                        "header": head,
                    }
                return {"parse": 1, "jx": 1, "url": url, "header": head}

        for mm in re.finditer(r"https?://[^\"'\s<>]+\.(?:m3u8|mp4)[^\"'\s<>]*", html or "", re.I):
            u = mm.group(0).replace("\\/", "/")
            if self._need_parse(u, ""):
                continue
            return {
                "parse": 0, "jx": 0, "url": u, "header": head,
                "format": "application/x-mpegURL" if ".m3u8" in u.lower() else "video/mp4",
            }
        return {"parse": 1, "jx": 1, "url": page, "header": head}

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(mp4|m3u8)(\?|$)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("home", [c["type_name"] for c in sp.homeContent(True)["class"]])
    hv = sp.homeVideoContent()
    print("homeVod", len(hv.get("list") or []))
    r = sp.categoryContent("1", 1, False, {})
    print("cat", len(r.get("list") or []), r["list"][0]["vod_name"] if r.get("list") else None)
    s = sp.searchContent("无职", False, 1)
    print("search", len(s.get("list") or []))
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        main = d["list"][0]
        print("detail", main.get("vod_name"), main.get("vod_play_from"))
        # test each line first ep
        froms = (main.get("vod_play_from") or "").split("$$$")
        url_groups = (main.get("vod_play_url") or "").split("$$$")
        for i, (fn, ug) in enumerate(zip(froms, url_groups)):
            pu = ug.split("#")[0]
            if "$" not in pu:
                continue
            p = sp.playerContent(fn, pu.split("$", 1)[1], [])
            print(" play", fn, "parse", p.get("parse"), str(p.get("url") or "")[:90])

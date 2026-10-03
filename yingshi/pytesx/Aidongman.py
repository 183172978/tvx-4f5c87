#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aidongman / girigiri愛動漫
站点: https://ani.girigirilove.com (bgm.girigirilove.com 跳转)
由 Aidongman.js 按 稀饭动漫.py 结构生成
播放: player_* encrypt=2 → base64 + urldecode → m3u8
"""
import json
import re
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


HOST = "https://ani.girigirilove.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

CLASSES = [
    {"type_id": "2", "type_name": "日番"},
    {"type_id": "3", "type_name": "美番"},
    {"type_id": "21", "type_name": "劇場版"},
    {"type_id": "20", "type_name": "真人番劇"},
    {"type_id": "24", "type_name": "BD副音軌"},
    {"type_id": "26", "type_name": "其他"},
]


def _years(from_y=2026, to_y=2000):
    v = [{"n": "全部", "v": ""}]
    for y in range(from_y, to_y - 1, -1):
        v.append({"n": str(y), "v": str(y)})
    return v


def _vals(arr):
    out = []
    for x in arr:
        if isinstance(x, dict):
            out.append(x)
        else:
            out.append({"n": x or "全部", "v": x})
    return out


BY = _vals([{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits"}, {"n": "评分", "v": "score"}])

FILTERS = {
    "2": [
        {"key": "class", "name": "类型", "value": _vals([
            "", "喜剧", "爱情", "恐怖", "动作", "科幻", "剧情", "战争", "奇幻", "冒险",
            "悬疑", "校园", "后宫", "热血", "运动", "百合", "乙女", "机甲", "日常",
            "魔法少女", "异世界", "爱抖露", "音乐", "萌",
        ])},
        {"key": "area", "name": "地区", "value": _vals(["", "一月", "四月", "七月", "十月"])},
        {"key": "year", "name": "年份", "value": _years()},
        {"key": "lang", "name": "语言", "value": _vals(["", "日语", "国语"])},
        {"key": "by", "name": "排序", "value": BY},
    ],
    "3": [
        {"key": "class", "name": "类型", "value": _vals([
            "", "搞笑", "爱情", "恐怖", "动作", "科幻", "剧情", "战争", "奇幻", "冒险",
            "悬疑", "校园", "后宫", "热血", "运动",
        ])},
        {"key": "area", "name": "地区", "value": _vals(["", "内地", "港台", "日韩", "欧美"])},
        {"key": "year", "name": "年份", "value": _years()},
        {"key": "lang", "name": "语言", "value": _vals(["", "国语", "英语"])},
        {"key": "by", "name": "排序", "value": BY},
    ],
    "21": [
        {"key": "class", "name": "类型", "value": _vals([
            "", "喜剧", "爱情", "恐怖", "动作", "科幻", "剧情", "战争", "奇幻", "冒险",
            "悬疑", "校园", "后宫", "热血", "运动", "百合", "耽美", "机甲", "日常",
            "魔法少女", "异世界", "爱抖露",
        ])},
        {"key": "year", "name": "年份", "value": _years()},
        {"key": "lang", "name": "语言", "value": _vals(["", "日语", "中文", "英语"])},
        {"key": "by", "name": "排序", "value": BY},
    ],
    "20": [
        {"key": "class", "name": "类型", "value": _vals([
            "", "爱情", "科幻", "经典", "冒险", "剧情", "动作", "同性", "喜剧", "奇幻",
            "恐怖", "悬疑.惊悚", "战争", "欧美", "歌舞", "灾难", "记录.泰剧", "体育", "烧脑",
        ])},
        {"key": "area", "name": "地区", "value": _vals(["", "日本", "欧美", "泰国"])},
        {"key": "year", "name": "年份", "value": _years()},
        {"key": "lang", "name": "语言", "value": _vals(["", "日语", "英语", "泰语"])},
        {"key": "by", "name": "排序", "value": BY},
    ],
    "24": [{"key": "by", "name": "排序", "value": BY}],
    "26": [{"key": "by", "name": "排序", "value": BY}],
}


class Spider(BaseSpider):
    def getName(self):
        return "Aidongman"

    def init(self, extend=""):
        pass

    def _headers(self, extra=None):
        h = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if extra:
            h.update(extra)
        return h

    def _get(self, url, headers=None):
        try:
            if requests is not None:
                r = requests.get(
                    url, headers=self._headers(headers),
                    timeout=18, verify=False, allow_redirects=True,
                )
                return r.text or ""
            req = urllib.request.Request(url, headers=self._headers(headers))
            with urllib.request.urlopen(req, timeout=18) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("get err", url, e)
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
        return HOST + "/" + u

    def _clean(self, t):
        t = re.sub(r"<[^>]+>", " ", str(t or ""))
        t = (
            t.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&#39;", "'")
            .replace("&quot;", '"')
            .replace("&#xe593;", "")
        )
        return re.sub(r"\s+", " ", t).strip()

    def _parse_cards(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        blocks = re.split(r'class="[^"]*public-list-box', html)
        for b in blocks[1:]:
            hm = re.search(r'href="(/GV\d+/[^"]*)"', b) or re.search(r'href="(/GV\d+/)"', b)
            if not hm:
                continue
            href = hm.group(1)
            vid = href
            m_id = re.search(r"/GV(\d+)", href)
            key = m_id.group(1) if m_id else href
            if key in seen:
                continue
            seen.add(key)
            tm = re.search(r'title="([^"]+)"', b)
            title = self._clean(tm.group(1) if tm else "")
            if not title:
                tm = re.search(r'time-title[^>]*>([^<]+)', b)
                title = self._clean(tm.group(1) if tm else "")
            if not title:
                continue
            pm = re.search(r'data-src="([^"]+)"', b) or re.search(
                r'(?:src|data-original)="((?:https?:)?//[^"]+/upload/[^"]+)"', b
            )
            pic = pm.group(1) if pm else ""
            if pic and not pic.startswith("http"):
                pic = self._abs(pic)
            remarks = ""
            rm = re.search(r'public-list-prb[^>]*>([\s\S]*?)<', b)
            if rm:
                remarks = self._clean(rm.group(1))
            videos.append({
                "vod_id": vid if vid.startswith("/") else "/GV%s/" % key,
                "vod_name": title,
                "vod_pic": self._abs(pic) if pic else "",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 0.75},
            })
        return videos

    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": FILTERS, "list": []}

    def homeVideoContent(self):
        html = self._get(HOST + "/")
        return {"list": self._parse_cards(html)[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or "2")
        ext = extend or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}
        area = str(ext.get("area") or "")
        by = str(ext.get("by") or "")
        cls = str(ext.get("class") or "")
        lang = str(ext.get("lang") or "")
        letter = str(ext.get("letter") or "")
        year = str(ext.get("year") or "")
        # /show/{tid}-{area}-{by}-{class}-{lang}-{letter}---{pg}---{year}/
        path = "/show/%s-%s-%s-%s-%s-%s---%d---%s/" % (
            tid, area, by, urllib.parse.quote(cls) if cls else "",
            urllib.parse.quote(lang) if lang else "", letter, pg, year,
        )
        html = self._get(HOST + path)
        videos = self._parse_cards(html)
        if not videos and pg == 1:
            # 兜底 type 页
            html2 = self._get("%s/type/%s.html" % (HOST, tid))
            videos = self._parse_cards(html2)
        pc = pg + 1 if len(videos) >= 12 else max(pg, 1)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pc,
            "limit": 24,
            "total": 9999 if videos else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        # ajax suggest 最稳
        url = "%s/index.php/ajax/suggest?mid=1&wd=%s&limit=30" % (
            HOST, urllib.parse.quote(str(key)),
        )
        txt = self._get(url, {"X-Requested-With": "XMLHttpRequest", "Referer": HOST + "/"})
        videos = []
        try:
            d = json.loads(txt or "{}")
        except Exception:
            d = {}
        for it in d.get("list") or []:
            vid = str(it.get("id") or "")
            if not vid:
                continue
            pic = str(it.get("pic") or "").replace("\\/", "/")
            videos.append({
                "vod_id": "/GV%s/" % vid,
                "vod_name": it.get("name") or "",
                "vod_pic": self._abs(pic),
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 0.75},
            })
        if not videos:
            # 页面搜索兜底
            page = "%s/search/-------------/?wd=%s" % (HOST, urllib.parse.quote(str(key)))
            html = self._get(page)
            videos = self._parse_cards(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": int(d.get("pagecount") or 1) if d else 1,
            "limit": 30,
            "total": int(d.get("total") or len(videos)),
        }

    def detailContent(self, ids):
        raw = str((ids or [""])[0]).strip()
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = HOST + raw
        elif re.match(r"^\d+$", raw):
            url = "%s/GV%s/" % (HOST, raw)
        else:
            url = self._abs(raw)
        html = self._get(url)
        m = re.search(r"/GV(\d+)", url)
        vid = m.group(1) if m else raw

        name = ""
        m = re.search(r"<title>([^<]+)</title>", html or "", re.I)
        if m:
            name = self._clean(re.sub(r"\s*[-_|].*$", "", m.group(1)))
        if not name:
            m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html or "", re.I)
            if m:
                name = self._clean(m.group(1))
        name = name or ("番剧#" + str(vid))

        pic = ""
        m = re.search(
            r'detail-pic[\s\S]{0,400}?(?:data-src|src)="([^"]+)"',
            html or "", re.I,
        ) or re.search(r'property="og:image"[^>]+content="([^"]+)"', html or "", re.I)
        if m:
            pic = self._abs(m.group(1))

        content = ""
        m = re.search(
            r'class="[^"]*(?:text|desc|content)[^"]*"[^>]*>([\s\S]*?)</div>',
            html or "", re.I,
        )
        if m:
            content = self._clean(m.group(1))[:500]

        # 线路名
        tab_names = []
        for m in re.finditer(
            r'anthology-tab[\s\S]*?<a[^>]*>([\s\S]*?)</a>',
            html or "", re.I,
        ):
            t = self._clean(m.group(1))
            if t:
                tab_names.append(t)

        # 分集 /playGV{id}-{sid}-{ep}/
        froms, urls = [], []
        boxes = re.findall(
            r'<ul class="anthology-list-play[^"]*">([\s\S]*?)</ul>',
            html or "", re.I,
        )
        if boxes:
            for i, box in enumerate(boxes):
                eps = []
                for m in re.finditer(
                    r'href="(/playGV\d+-\d+-\d+/)"[^>]*>\s*([^<]+)',
                    box,
                ):
                    eps.append("%s$%s" % (self._clean(m.group(2)), self._abs(m.group(1))))
                if eps:
                    froms.append(tab_names[i] if i < len(tab_names) else ("线路%d" % (i + 1)))
                    urls.append("#".join(eps))
        else:
            # 整页扫 playGV 链接，按 sid 分组
            groups = {}
            order = []
            for m in re.finditer(
                r'href="(/playGV(\d+)-(\d+)-(\d+)/)"[^>]*>\s*([^<]+)',
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
                eps = groups[sid]
                froms.append(tab_names[i] if i < len(tab_names) else ("线路%d" % (i + 1)))
                urls.append("#".join("%s$%s" % (n, u) for n, u in eps))

        if not froms:
            froms = ["默认"]
            urls = ["正片$%s" % url]

        return {"list": [{
            "vod_id": "/GV%s/" % vid if re.match(r"^\d+$", str(vid)) else raw,
            "vod_name": name,
            "vod_pic": pic,
            "vod_content": content or "girigiri愛動漫",
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
            "style": {"type": "rect", "ratio": 0.75},
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
                raw = base64.b64decode(u)
                u = urllib.parse.unquote(raw.decode("utf-8", "ignore"))
            except Exception:
                pass
        elif enc == 3:
            try:
                u = u[8:]
                u = base64.b64decode(u).decode("utf-8", "ignore")
                u = u[8:-8]
            except Exception:
                pass
        return u

    def playerContent(self, flag, id, vipFlags=None):
        head = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Origin": HOST,
        }
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        if play.startswith("http") and re.search(r"\.(m3u8|mp4)(\?|$)", play, re.I):
            return {
                "parse": 0, "jx": 0, "url": play, "header": head,
                "format": "application/x-mpegURL" if ".m3u8" in play.lower() else "video/mp4",
            }
        page = play if play.startswith("http") else self._abs(play)
        html = self._get(page, {"Referer": HOST + "/"})
        m = re.search(
            r"player_[a-zA-Z0-9_]*\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>",
            html or "", re.I,
        )
        if m:
            try:
                player = json.loads(m.group(1))
            except Exception:
                player = {}
            url = self._decode_player_url(player.get("url"), player.get("encrypt"))
            if url:
                # m3u8 主机可能是 akua.girigirilove.com，Referer 用主站即可
                direct = bool(re.search(r"\.(m3u8|mp4)(\?|$)", url, re.I))
                return {
                    "parse": 0 if direct else 1,
                    "jx": 0 if direct else 1,
                    "url": url,
                    "header": head,
                    "format": "application/x-mpegURL" if ".m3u8" in (url or "").lower() else "video/mp4",
                }
            frm = player.get("from") or ""
            nxt = player.get("link_next") or ""
            if frm:
                js = self._get("%s/static/player/%s.js" % (HOST, frm))
                pm = re.search(r'src=["\']([^"\']+)', js or "", re.I)
                if pm and re.search(r"https?:", pm.group(1)):
                    return {
                        "parse": 1, "jx": 0,
                        "url": pm.group(1) + (player.get("url") or "") + "&next=" + nxt + "&title=",
                        "header": head,
                    }
        for mm in re.finditer(
            r"https?://[^\"'\s<>]+\.(?:m3u8|mp4)[^\"'\s<>]*", html or "", re.I
        ):
            u = mm.group(0).replace("\\/", "/")
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
    r = sp.categoryContent("2", 1, False, {})
    print("cat", len(r.get("list") or []), r["list"][0]["vod_name"] if r.get("list") else None)
    s = sp.searchContent("无职", False, 1)
    print("search", len(s.get("list") or []))
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        main = d["list"][0]
        print("detail", main.get("vod_name"), main.get("vod_play_from"))
        print("eps", str(main.get("vod_play_url") or "")[:120])
        pu = (main.get("vod_play_url") or "").split("#")[0]
        if "$" in pu:
            p = sp.playerContent("线路", pu.split("$", 1)[1], [])
            print("play", p.get("parse"), str(p.get("url") or "")[:100])

# -*- coding: utf-8 -*-
"""
片库 / 裤佬影视  https://4k01.pianku.online
修复：列表标题/封面、自营线路、player_aaaa 播放
"""
import re
import json
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


HOST = "https://4k01.pianku.online"
HOSTS = [
    "https://4k01.pianku.online",
    "https://www.pianku.online",
]
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

CHANNELS = {
    "20": "电影",
    "37": "剧集",
    "43": "动漫",
    "45": "综艺",
    "47": "B站",
    "21": "动作片",
    "22": "喜剧片",
    "23": "爱情片",
}


class Spider(BaseSpider):
    def getName(self):
        return "片库"

    def init(self, extend=""):
        global HOST
        if extend:
            try:
                conf = (
                    json.loads(extend)
                    if isinstance(extend, str) and extend.strip().startswith("{")
                    else {}
                )
                if conf.get("host"):
                    HOST = str(conf["host"]).rstrip("/")
            except Exception:
                pass
        # 探测可用域名
        for h in HOSTS:
            try:
                html = self._get_raw(h + "/", h)
                if html and ("voddetail" in html or "片库" in html):
                    HOST = h
                    break
            except Exception:
                continue

    def _headers(self, extra=None, referer=None):
        h = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer or (HOST + "/"),
        }
        if extra:
            h.update(extra)
        return h

    def _get_raw(self, url, referer=None):
        try:
            if requests is not None:
                r = requests.get(
                    url,
                    headers=self._headers(referer=referer),
                    timeout=18,
                    verify=False,
                    allow_redirects=True,
                )
                return r.text or ""
            req = urllib.request.Request(url, headers=self._headers(referer=referer))
            with urllib.request.urlopen(req, timeout=18) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("get err", url, e)
            return ""

    def _get(self, url, extra=None):
        global HOST
        if not url.startswith("http"):
            url = HOST + (url if url.startswith("/") else "/" + url)
        html = self._get_raw(url, HOST + "/")
        if html:
            return html
        # 域名切换重试
        for h in HOSTS:
            if h == HOST:
                continue
            alt = url.replace(HOST, h) if HOST in url else (h + url.split(HOST)[-1] if HOST in url else h + "/")
            if not url.startswith("http"):
                alt = h + (url if str(url).startswith("/") else "/" + str(url))
            else:
                from urllib.parse import urlparse

                p = urlparse(url)
                alt = h + p.path + (("?" + p.query) if p.query else "")
            html = self._get_raw(alt, h + "/")
            if html and len(html) > 500:
                HOST = h
                return html
        return ""

    def _abs(self, u):
        if not u:
            return ""
        u = str(u).strip().replace("\\/", "/")
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        if u.startswith("/"):
            return HOST + u
        return HOST + "/" + u

    def _clean(self, t):
        t = re.sub(r"<[^>]+>", " ", str(t or ""))
        t = t.replace("&nbsp;", " ").replace("&amp;", "&")
        return re.sub(r"\s+", " ", t).strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        # 优先按 vod-item 切块
        blocks = re.findall(
            r'<div class="vod-item">([\s\S]*?)</div>\s*</div>', html, re.I
        )
        if not blocks:
            blocks = re.findall(
                r'(<a[^>]+href="[^"]*/voddetail/\d+\.html"[^>]*>[\s\S]*?</a>)',
                html,
                re.I,
            )
        for block in blocks:
            m = re.search(r'/voddetail/(\d+)\.html', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            name = ""
            tm = re.search(r'title="([^"]+)"', block)
            if tm:
                name = tm.group(1).strip()
            if not name:
                tm = re.search(r'class="title"[^>]*>([^<]+)', block)
                if tm:
                    name = self._clean(tm.group(1))
            if not name:
                tm = re.search(r"<h4[^>]*>([^<]+)", block)
                if tm:
                    name = self._clean(tm.group(1))
            pic = ""
            pm = re.search(
                r'(?:data-src|src)="(https?://[^"]+)"', block, re.I
            )
            if pm:
                pic = pm.group(1)
            remarks = ""
            rm = re.search(r'class="remarks"[^>]*>([^<]+)', block)
            if rm:
                remarks = self._clean(rm.group(1))
            if not remarks:
                rm = re.search(
                    r"(更新[^<\n]{0,20}|全\d+集|\d+集全|已完结|连载中|HD|完结)",
                    block,
                )
                if rm:
                    remarks = re.sub(r"\s+", "", rm.group(1))
            videos.append(
                {
                    "vod_id": vid,
                    "vod_name": (name or ("影片#" + vid))[:80],
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "style": {"type": "rect", "ratio": 0.7},
                }
            )
        # 兜底全局 href
        if len(videos) < 3:
            for m in re.finditer(
                r'href="(?:https?://[^"]+)?(/voddetail/(\d+)\.html)"[^>]*(?:title="([^"]*)")?',
                html,
                re.I,
            ):
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                name = (m.group(3) or "").strip()
                block = html[max(0, m.start() - 50) : m.start() + 800]
                if not name:
                    tm = re.search(r'class="title"[^>]*>([^<]+)', block)
                    if tm:
                        name = self._clean(tm.group(1))
                pic = ""
                pm = re.search(r'(?:data-src|src)="(https?://[^"]+)"', block)
                if pm:
                    pic = pm.group(1)
                videos.append(
                    {
                        "vod_id": vid,
                        "vod_name": (name or ("影片#" + vid))[:80],
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "style": {"type": "rect", "ratio": 0.7},
                    }
                )
        return videos

    def homeContent(self, filter=False):
        classes = [{"type_id": k, "type_name": v} for k, v in CHANNELS.items()]
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        html = self._get("/")
        return {"list": self._parse_list(html)[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        tid = str(tid or "20").strip()
        if pg <= 1:
            url = "/vodtype/%s.html" % tid
        else:
            url = "/vodtype/%s-%d.html" % (tid, pg)
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 20 else max(pg, 1),
            "limit": 30,
            "total": 9999,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        key = str(key or "").strip()
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        url = "/vodsearch/-------------.html?wd=%s" % urllib.parse.quote(key)
        if pg > 1:
            url = "/vodsearch/%s----------%d---.html" % (
                urllib.parse.quote(key),
                pg,
            )
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 20 else pg,
            "limit": 30,
            "total": len(videos),
        }

    def detailContent(self, ids):
        raw = str((ids or [""])[0]).strip()
        m = re.search(r"/voddetail/(\d+)", raw)
        vid = m.group(1) if m else re.sub(r"\D", "", raw)
        if not vid:
            return {"list": []}
        html = self._get("/voddetail/%s.html" % vid)
        if not html:
            return {"list": []}
        name = "影片#" + vid
        m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
        if m:
            name = self._clean(m.group(1))
        if not name or name.startswith("影片"):
            m = re.search(r"<title>([^<]+)</title>", html, re.I)
            if m:
                name = self._clean(re.sub(r"\s*[-|—].*$", "", m.group(1)))
        pic = ""
        m = re.search(
            r'class="[^"]*detail-pic[^"]*"[\s\S]{0,200}?(?:data-src|src)="([^"]+)"',
            html,
            re.I,
        )
        if not m:
            m = re.search(
                r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"',
                html,
                re.I,
            )
        if m:
            pic = self._abs(m.group(1))
        content = ""
        m = re.search(r"剧情简介[\s\S]*?<p>([\s\S]*?)</p>", html, re.I)
        if m:
            content = self._clean(m.group(1))[:500]

        # 线路名
        tab_map = {}
        for m in re.finditer(
            r'class="source-tab-item"[^>]*data-target="playlist-(\d+)"[^>]*>([^<]+)',
            html,
        ):
            tab_map[m.group(1)] = self._clean(m.group(2))
        for m in re.finditer(
            r'data-target="playlist-(\d+)"[^>]*class="source-tab-item"[^>]*>([^<]+)',
            html,
        ):
            tab_map.setdefault(m.group(1), self._clean(m.group(2)))
        for m in re.finditer(
            r'<span class="source-tab-item"[^>]*data-target="playlist-(\d+)"[^>]*>([^<]+)</span>',
            html,
        ):
            tab_map[m.group(1)] = self._clean(m.group(2))

        # 按 playlist-N 分组
        groups = {}
        order = []
        for m in re.finditer(
            r'id="playlist-(\d+)"([\s\S]*?)(?:id="playlist-|\Z)', html
        ):
            sid, body = m.group(1), m.group(2)
            eps = []
            for mm in re.finditer(
                r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*(?:title="([^"]*)")?[^>]*>([^<]*)',
                body,
            ):
                href, _, sid2, nid, title, text = mm.groups()
                label = self._clean(title or text) or ("第%s集" % nid)
                eps.append("%s$%s" % (label, self._abs(href)))
            if eps:
                groups[sid] = eps
                order.append(sid)

        # 全局兜底
        if not groups:
            for m in re.finditer(
                r'href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*(?:title="([^"]*)")?[^>]*>([^<]*)',
                html,
            ):
                href, _, sid, nid, title, text = m.groups()
                label = self._clean(title or text) or ("第%s集" % nid)
                if sid not in groups:
                    groups[sid] = []
                    order.append(sid)
                groups[sid].append("%s$%s" % (label, self._abs(href)))

        froms, urls = [], []
        # 只保留自营
        for sid in order:
            tname = tab_map.get(sid) or ("线路%s" % sid)
            if re.search(r"自营|jlm3u8|自建|专线", tname, re.I):
                froms.append(tname)
                urls.append("#".join(groups[sid]))
        # 未标注时探测
        if not froms:
            for sid in order:
                sample = groups[sid][0].split("$")[-1] if groups[sid] else ""
                if not sample:
                    continue
                ph = self._get(sample)
                mfrom = re.search(r'"from"\s*:\s*"([^"]+)"', ph or "")
                src = (mfrom.group(1) if mfrom else "").lower()
                has_m3u8 = bool(
                    re.search(r"https?://\S+\.m3u8", ph or "", re.I)
                )
                if "jlm3u8" in src or has_m3u8:
                    froms.append(tab_map.get(sid) or "自营")
                    urls.append("#".join(groups[sid]))
                    break
        if not froms:
            # 无自营时仍给出第一条线路（需解析）
            if order:
                sid = order[0]
                froms = [tab_map.get(sid) or "线路"]
                urls = ["#".join(groups[sid])]
            else:
                froms = ["自营"]
                urls = ["暂无$%s" % self._abs("/voddetail/%s.html" % vid)]

        return {
            "list": [
                {
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": "",
                    "vod_content": content or "片库",
                    "vod_play_from": "$$$".join(froms),
                    "vod_play_url": "$$$".join(urls),
                    "style": {"type": "rect", "ratio": 0.7},
                }
            ]
        }

    def _decode_player(self, encoded, encrypt):
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
                u = urllib.parse.unquote(
                    base64.b64decode(u).decode("utf-8", "ignore")
                )
            except Exception:
                pass
        return u

    def playerContent(self, flag, id, vipFlags=None):
        head = {"User-Agent": UA, "Referer": HOST + "/", "Origin": HOST}
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        if play.startswith("http") and re.search(
            r"\.(m3u8|mp4)(\?|$)", play, re.I
        ):
            return {
                "parse": 0,
                "jx": 0,
                "url": play,
                "header": head,
                "format": "application/x-mpegURL"
                if ".m3u8" in play.lower()
                else "video/mp4",
            }
        page = play if play.startswith("http") else self._abs(play)
        html = self._get(page)
        # player_aaaa
        m = re.search(
            r"var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>",
            html or "",
            re.I,
        )
        if not m:
            m = re.search(
                r"player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;", html or "", re.I
            )
        if m:
            raw = m.group(1)
            try:
                player = json.loads(raw)
            except Exception:
                # 容错：提取 url/from/encrypt
                player = {}
                um = re.search(r'"url"\s*:\s*"([^"]*)"', raw)
                if um:
                    player["url"] = um.group(1)
                em = re.search(r'"encrypt"\s*:\s*(\d+)', raw)
                if em:
                    player["encrypt"] = em.group(1)
                fm = re.search(r'"from"\s*:\s*"([^"]*)"', raw)
                if fm:
                    player["from"] = fm.group(1)
            url = self._decode_player(player.get("url"), player.get("encrypt"))
            if url:
                direct = bool(re.search(r"\.(m3u8|mp4)(\?|$)", url, re.I))
                if not direct and re.search(
                    r"(youku|iqiyi|v\.qq|mgtv|bilibili|sohu|le\.com|pptv)",
                    url,
                    re.I,
                ):
                    return {"parse": 1, "jx": 1, "url": url, "header": head}
                return {
                    "parse": 0 if direct else 1,
                    "jx": 0 if direct else 1,
                    "url": url,
                    "header": head,
                    "format": "application/x-mpegURL"
                    if ".m3u8" in url.lower()
                    else "video/mp4",
                }
        for mm in re.finditer(
            r"https?://[^\"'\s<>]+\.(?:m3u8|mp4)[^\"'\s<>]*", html or "", re.I
        ):
            u = mm.group(0).replace("\\/", "/")
            return {
                "parse": 0,
                "jx": 0,
                "url": u,
                "header": head,
                "format": "application/x-mpegURL"
                if ".m3u8" in u.lower()
                else "video/mp4",
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
    print("host", HOST)
    print("home", [c["type_name"] for c in sp.homeContent(True)["class"]])
    hv = sp.homeVideoContent()
    print("homeVod", len(hv.get("list") or []))
    r = sp.categoryContent("20", 1, False, {})
    print(
        "cat",
        len(r.get("list") or []),
        r["list"][0]["vod_name"] if r.get("list") else None,
    )
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        main = d["list"][0]
        print("detail", main.get("vod_name"), main.get("vod_play_from"))
        froms = (main.get("vod_play_from") or "").split("$$$")
        url_groups = (main.get("vod_play_url") or "").split("$$$")
        for fn, ug in zip(froms, url_groups):
            pu = ug.split("#")[0]
            if "$" not in pu:
                continue
            p = sp.playerContent(fn, pu.split("$", 1)[1], [])
            print(" play", fn, "parse", p.get("parse"), str(p.get("url"))[:90])
            break

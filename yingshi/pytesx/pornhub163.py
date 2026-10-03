#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub163  https://cn.pornhub163.net
修复：封面取 jpg、播放实时解析 m3u8/mp4
"""
import json
import re
import subprocess
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


HOST = "https://cn.pornhub163.net"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

CHANNELS = [
    ("video", "最新"),
    ("o_ht", "当前热门"),
    ("o_mv", "最多观看"),
    ("o_tr", "最高评分"),
    ("c_27", "少女"),
    ("c_29", "熟女"),
    ("c_35", "女同"),
    ("c_65", "素人"),
    ("c_28", "亚洲"),
    ("c_17", "日本AV"),
    ("c_111", "中文"),
    ("c_8", "按摩"),
    ("c_22", "口交"),
    ("c_24", "三人"),
    ("c_10", "角色扮演"),
    ("c_15", "颜射"),
    ("c_7", "肛交"),
    ("c_69", "自慰"),
    ("c_80", "群交"),
    ("c_1", "亚洲精选"),
    ("gayporn", "男同"),
    ("recommended", "推荐"),
]


class Spider(BaseSpider):
    def __init__(self):
        self.session = None

    def getName(self):
        return "Pornhub163"

    def init(self, extend=""):
        self.session = None

    def _sess(self):
        if self.session is not None:
            return self.session
        if requests is None:
            return None
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": UA,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": HOST + "/enter",
            }
        )
        s.cookies.set("x-index-auth", "authed", domain="cn.pornhub163.net", path="/")
        s.cookies.set("accessAgeDisclaimerPH", "1", domain="cn.pornhub163.net", path="/")
        s.cookies.set("accessAgeDisclaimerUA", "1", domain="cn.pornhub163.net", path="/")
        self.session = s
        return s

    def _headers(self, referer=None):
        return {
            "User-Agent": UA,
            "Referer": referer or (HOST + "/enter"),
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }

    def _solve_key(self, html):
        if not html or "leastFactor" not in html:
            return None
        m = re.search(r"<script[^>]*>([\s\S]*?leastFactor[\s\S]*?)</script>", html)
        if not m:
            return None
        js = m.group(1)
        js = js.replace("if (typeof phantom !== 'undefined') return 'phantom';", "")
        js = js.replace(
            "if (typeof module !== 'undefined' && module.exports) return 'node';", ""
        )
        js += (
            "\nvar cookieStore='';var document={set cookie(v){cookieStore=v;},"
            "get cookie(){return cookieStore;},location:{reload:function(){}}};"
            "go();console.log(cookieStore);"
        )
        try:
            out = subprocess.check_output(
                ["node", "-e", js], text=True, timeout=10
            ).strip()
            if "KEY=" in out:
                return out.split("KEY=")[-1].split(";")[0]
        except Exception as e:
            print("solve key err", e)
        return None

    def fetch_text(self, url, retry=2):
        if not url.startswith("http"):
            url = HOST + (url if url.startswith("/") else "/" + url)
        s = self._sess()
        for _ in range(retry + 1):
            try:
                if s is not None:
                    r = s.get(url, timeout=25, verify=False)
                    text = r.text or ""
                    if "leastFactor" in text and len(text) < 8000:
                        key = self._solve_key(text)
                        if key:
                            s.cookies.set(
                                "KEY", key, domain="cn.pornhub163.net", path="/"
                            )
                            continue
                    return text
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=25) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception as e:
                print("fetch err", url, e)
        return ""

    def _clean(self, t):
        t = re.sub(r"<[^>]+>", "", str(t or ""))
        t = (
            t.replace("&amp;", "&")
            .replace("&#039;", "'")
            .replace("&quot;", '"')
            .replace("&nbsp;", " ")
        )
        return re.sub(r"\s+", " ", t).strip()

    def _pick_cover(self, block):
        """优先真实图片；兼容换行 src"""
        cands = []
        # 允许属性换行：src\n="http..."
        for m in re.finditer(
            r'(?:data-image|data-thumb_url|data-mediumthumb|data-src|src)\s*=\s*"(https?://[^"]+)"',
            block,
            re.I,
        ):
            u = m.group(1).strip().replace("&amp;", "&")
            low = u.lower()
            if any(x in low for x in ("logo", "avatar", "icon", ".svg", "pixel.gif")):
                continue
            cands.append(u)
        for u in cands:
            path = u.split("?")[0].lower()
            if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                return u
            if ".jpg" in low or "(m=" in u or "/original/" in u:
                return u
        for u in cands:
            if ".mp4" not in u.lower():
                return u
        return cands[0] if cands else ""

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        # 按列表项切块，封面与标题更稳
        blocks = re.split(r'class="[^"]*pcVideoListItem', html)
        if len(blocks) < 2:
            blocks = re.split(r'class="[^"]*phimage', html)
        for block in blocks[1:]:
            vm = re.search(r'viewkey=([a-zA-Z0-9]+)', block)
            if not vm:
                continue
            vk = vm.group(1)
            if vk in seen:
                continue
            seen.add(vk)
            title = ""
            tm = re.search(r'title="([^"]{2,200})"', block)
            if tm:
                title = self._clean(tm.group(1))
            if not title:
                tm = re.search(r'alt="([^"]{2,200})"', block)
                if tm:
                    title = self._clean(tm.group(1))
            pic = self._pick_cover(block)
            videos.append(
                {
                    "vod_id": vk,
                    "vod_name": (title[:120] or vk),
                    "vod_pic": pic,
                    "vod_remarks": "HD",
                    "style": {"type": "rect", "ratio": 1.5},
                }
            )
        if len(videos) < 4:
            for m in re.finditer(
                r'href="(/view_video\.php\?viewkey=([a-zA-Z0-9]+))"[^>]*title="([^"]+)"',
                html,
                re.I,
            ):
                vk = m.group(2)
                if vk in seen:
                    continue
                seen.add(vk)
                block = html[max(0, m.start() - 200) : m.start() + 1200]
                videos.append(
                    {
                        "vod_id": vk,
                        "vod_name": self._clean(m.group(3))[:120] or vk,
                        "vod_pic": self._pick_cover(block),
                        "vod_remarks": "HD",
                        "style": {"type": "rect", "ratio": 1.5},
                    }
                )
        return videos

    def _list_url(self, tid, pg):
        pg = int(pg or 1)
        tid = str(tid or "video").strip()
        # 兼容旧 id 与 app 传参
        if tid in ("home", "latest", ""):
            tid = "video"
        if tid.startswith("video?c="):
            tid = "c_" + tid.split("=", 1)[-1]
        if tid.startswith("video?o="):
            tid = "o_" + tid.split("=", 1)[-1]
        if tid.startswith("c_"):
            base = HOST + "/video?c=" + tid[2:]
        elif tid.startswith("o_"):
            base = HOST + "/video?o=" + tid[2:]
        elif tid.startswith("http"):
            base = tid
        elif tid.startswith("/"):
            base = HOST + tid
        else:
            base = HOST + "/" + tid
        if pg <= 1:
            return base
        sep = "&" if "?" in base else "?"
        return base + sep + "page=%d" % pg

    def homeContent(self, filter=False):
        classes = [{"type_id": c[0], "type_name": c[1]} for c in CHANNELS]
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        html = self.fetch_text(HOST + "/video")
        if len(html) < 5000:
            html = self.fetch_text(HOST + "/enter")
        return {"list": self._parse_list(html)[:40]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg or 1)
        url = self._list_url(tid, pg)
        html = self.fetch_text(url)
        videos = self._parse_list(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 15 else max(pg, 1),
            "limit": 36,
            "total": 9999 if videos else 0,
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        pg = int(pg or 1)
        q = urllib.parse.quote(str(key or "").strip())
        if not q:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        url = HOST + "/video/search?search=%s" % q
        if pg > 1:
            url += "&page=%d" % pg
        html = self.fetch_text(url)
        videos = self._parse_list(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 15 else pg,
            "limit": 36,
            "total": 9999 if videos else 0,
        }

    def detailContent(self, ids):
        vk = str((ids or [""])[0]).strip()
        m = re.search(r"viewkey=([a-zA-Z0-9]+)", vk)
        if m:
            vk = m.group(1)
        if not vk:
            return {"list": []}
        html = self.fetch_text(HOST + "/embed/" + vk)
        if len(html) < 2000:
            html = self.fetch_text(HOST + "/view_video.php?viewkey=" + vk)
        name = vk
        pic = ""
        m = re.search(
            r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html or "", re.I
        )
        if m:
            name = self._clean(m.group(1))
        else:
            m = re.search(r"<title>([^<]+)</title>", html or "", re.I)
            if m:
                name = self._clean(re.sub(r"\s*[-|].*$", "", m.group(1)))
        if not name or name.lower() in ("embed player", "pornhub", "embed player - pornhub.com"):
            name = vk
        m = re.search(
            r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html or "", re.I
        )
        if m:
            pic = m.group(1)
        # 播放项：仅传 viewkey，播放时实时取流（避免签名过期）
        plays = self._probe_qualities(html, vk)
        if not plays:
            plays = ["播放$%s" % vk]
        return {
            "list": [
                {
                    "vod_id": vk,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": "HD",
                    "vod_content": "viewkey: " + vk,
                    "vod_play_from": "PH163",
                    "vod_play_url": "#".join(plays),
                    "style": {"type": "rect", "ratio": 1.5},
                }
            ]
        }

    def _probe_qualities(self, html, vk):
        """从页面探测可用清晰度标签，地址仍用 viewkey 实时解析"""
        labels = []
        seen = set()
        # get_media
        gm = re.search(
            r"(https://cn\.pornhub163\.net/video/get_media[^\"']+)",
            (html or "").replace("\\/", "/"),
        )
        if gm:
            ghtml = self.fetch_text(gm.group(1))
            if ghtml and ghtml.strip()[:1] in "[{":
                try:
                    data = json.loads(ghtml)
                    if isinstance(data, list):
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            u = (item.get("videoUrl") or "").replace("\\/", "/")
                            if not u:
                                continue
                            q = str(item.get("quality") or item.get("height") or "")
                            m = re.search(r"\d{3,4}", q)
                            lab = (m.group(0) + "P") if m else "HD"
                            fmt = str(item.get("format") or "")
                            if "hls" in u or ".m3u8" in u or fmt.lower() == "hls":
                                lab = lab + "·HLS"
                            if lab not in seen:
                                seen.add(lab)
                                labels.append("%s$%s" % (lab, vk))
                except Exception:
                    pass
        for mm in re.finditer(
            r'videoUrl["\']?\s*:\s*["\']([^"\']+)["\']', html or ""
        ):
            u = mm.group(1).replace("\\/", "/")
            if not u.startswith("http"):
                continue
            qm = re.search(r"/(\d{3,4})P_", u, re.I)
            lab = (qm.group(1) + "P") if qm else ("HLS" if ".m3u8" in u or "/hls/" in u else "HD")
            if lab not in seen:
                seen.add(lab)
                labels.append("%s$%s" % (lab, vk))
        if not labels:
            labels = ["1080P$%s" % vk, "720P$%s" % vk, "480P$%s" % vk]
        # 高清优先
        def sc(x):
            m = re.search(r"(\d{3,4})", x)
            return int(m.group(1)) if m else 0

        labels = sorted(labels, key=sc, reverse=True)
        return labels[:8]

    def _resolve_m3u8(self, url):
        from urllib.parse import urljoin

        u = str(url or "").strip()
        if not u or ".m3u8" not in u:
            return u
        if "index-v" in u or "chunk" in u:
            return u
        try:
            cdn_m = re.match(r"https?://([^/]+)", u)
            cdn = cdn_m.group(1) if cdn_m else ""
            headers = {
                "User-Agent": UA,
                "Referer": ("https://%s/" % cdn) if cdn else (HOST + "/"),
                "Accept": "*/*",
            }
            s = self._sess()
            body = ""
            if s is not None:
                r = s.get(u, headers=headers, timeout=15, verify=False)
                body = r.text or ""
            if body and "#EXT-X-STREAM-INF" in body:
                for ln in body.splitlines():
                    ln = ln.strip()
                    if ln and not ln.startswith("#"):
                        return urljoin(u, ln)
        except Exception as e:
            print("resolve m3u8 err", e)
        return u

    def _collect_streams(self, html):
        """返回 [(score, label, url), ...]"""
        cands = []
        # get_media JSON
        gm = re.search(
            r"(https://cn\.pornhub163\.net/video/get_media[^\"']+)",
            (html or "").replace("\\/", "/"),
        )
        if gm:
            ghtml = self.fetch_text(gm.group(1))
            if ghtml and ghtml.strip()[:1] in "[{":
                try:
                    data = json.loads(ghtml)
                    if isinstance(data, list):
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            u = (item.get("videoUrl") or "").replace("\\/", "/")
                            if not u.startswith("http"):
                                continue
                            q = str(item.get("quality") or item.get("height") or "0")
                            m = re.search(r"\d+", q)
                            qi = int(m.group()) if m else 0
                            fmt = str(item.get("format") or "").lower()
                            is_hls = (
                                ".m3u8" in u
                                or "/hls/" in u
                                or fmt in ("hls", "m3u8")
                            )
                            # HLS 优先（mp4 常绑定取流 IP）
                            sc = qi + (10000 if is_hls else 0)
                            lab = (str(qi) + "P") if qi else "HD"
                            if is_hls:
                                lab += "·HLS"
                            cands.append((sc, lab, u))
                except Exception as e:
                    print("get_media err", e)
        # videoUrl 字段
        for mm in re.finditer(
            r'videoUrl["\']?\s*:\s*["\']([^"\']+)["\']', html or ""
        ):
            u = mm.group(1).replace("\\/", "/")
            if not u.startswith("http"):
                continue
            if "get_media" in u:
                continue
            qm = re.search(r"/(\d{3,4})P_", u, re.I)
            qi = int(qm.group(1)) if qm else 480
            is_hls = ".m3u8" in u or "/hls/" in u
            sc = qi + (10000 if is_hls else 0)
            lab = str(qi) + "P" + ("·HLS" if is_hls else "")
            cands.append((sc, lab, u))
        # 裸 m3u8
        for mm in re.finditer(
            r"https?://[^\"'\s<>\\]+\.m3u8[^\"'\s<>\\]*", (html or "").replace("\\/", "/")
        ):
            u = mm.group(0)
            cands.append((15000, "HLS", u))
        return cands

    def playerContent(self, flag, id, vipFlags=None):
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        vk = play
        m = re.search(r"viewkey=([a-zA-Z0-9]+)", play)
        if m:
            vk = m.group(1)
        elif re.match(r"^[a-zA-Z0-9]+$", play) and "http" not in play:
            vk = play
        elif play.startswith("http") and re.search(
            r"\.(m3u8|mp4)(\?|$)", play, re.I
        ):
            u = play
            if ".m3u8" in u:
                u = self._resolve_m3u8(u)
            cdn_m = re.match(r"https?://([^/]+)", u)
            cdn = cdn_m.group(1) if cdn_m else ""
            return {
                "parse": 0,
                "jx": 0,
                "url": u,
                "header": {
                    "User-Agent": UA,
                    "Referer": ("https://%s/" % cdn) if cdn else (HOST + "/"),
                    "Accept": "*/*",
                },
                "format": "application/x-mpegURL"
                if ".m3u8" in u.lower()
                else "video/mp4",
            }
        else:
            vk = re.sub(r"[^a-zA-Z0-9]", "", play)

        html = self.fetch_text(HOST + "/embed/" + vk)
        if "站点维护" in (html or "") or len(html or "") < 1000:
            html = self.fetch_text(HOST + "/view_video.php?viewkey=" + vk)

        candidates = self._collect_streams(html)
        if not candidates:
            page = HOST + "/view_video.php?viewkey=" + vk
            return {
                "parse": 1,
                "jx": 0,
                "url": page,
                "header": {"User-Agent": UA, "Referer": HOST + "/"},
            }

        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen = candidates[0]
        if flag:
            fl = str(flag)
            for c in candidates:
                if fl.split("·")[0] in c[1] or fl in c[1]:
                    chosen = c
                    break
        u = chosen[2]
        # HLS 路径无扩展名时补 master
        if "/hls/" in u and ".m3u8" not in u and ".mp4" not in u:
            if not u.endswith("/"):
                # 常见形式 .../480P_2000K_xxxx  → 尝试加 .m3u8
                u2 = u + ".m3u8"
                u = u2
        if ".m3u8" in u:
            u = self._resolve_m3u8(u)
        cdn_m = re.match(r"https?://([^/]+)", u)
        cdn = cdn_m.group(1) if cdn_m else ""
        header = {
            "User-Agent": UA,
            "Referer": ("https://%s/" % cdn) if cdn else (HOST + "/embed/" + vk),
            "Accept": "*/*",
        }
        return {
            "parse": 0,
            "jx": 0,
            "url": u,
            "header": header,
            "format": "application/x-mpegURL"
            if ".m3u8" in u.lower() or "/hls/" in u
            else "video/mp4",
        }

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(mp4|m3u8)(\?|$)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

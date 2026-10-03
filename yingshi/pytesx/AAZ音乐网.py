#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AAZ音乐网 https://www.aaz.cx
修复：人机验证（csrf + human_check）/ 分类列表解析
"""
import json
import re
import gzip
import time
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


HOST = "https://www.aaz.cx"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
CLASSES = [
    {"type_id": "new", "type_name": "新歌榜"},
    {"type_id": "top", "type_name": "TOP榜单"},
    {"type_id": "singer", "type_name": "歌手"},
    {"type_id": "playtype", "type_name": "歌单"},
    {"type_id": "album", "type_name": "专辑"},
    {"type_id": "mv", "type_name": "高清MV"},
]
PATH_MAP = {
    "new": "/list/new.html",
    "top": "/list/top.html",
    "singer": "/singerlist/index/index/index/index.html",
    "playtype": "/playtype/index.html",
    "album": "/albumlist/index.html",
    "mv": "/mvlist/index.html",
}


class Spider(BaseSpider):
    def __init__(self):
        self._sess = None
        self._ok_ts = 0

    def getName(self):
        return "AAZ音乐网"

    def init(self, extend=""):
        self._ensure_pass()

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

    def _session(self):
        if requests is None:
            return None
        if self._sess is None:
            self._sess = requests.Session()
            self._sess.headers.update(self._headers())
        return self._sess

    def _is_verify(self, html):
        return bool(html and ("安全验证" in html or 'name="csrf_token"' in html) and len(html) < 8000)

    def _pass_verify(self, html, url):
        """提交人机验证，获取 PHPSESSID"""
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html or "")
        if not m:
            return False
        csrf = m.group(1)
        data = {"csrf_token": csrf, "human_check": "on"}
        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": HOST,
            "Referer": url,
        }
        try:
            sess = self._session()
            if sess is not None:
                r = sess.post(url, data=data, headers=post_headers, timeout=15, verify=False)
                ok = r.text and not self._is_verify(r.text)
                if ok:
                    self._ok_ts = time.time()
                return ok
            # urllib fallback
            body = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=self._headers(post_headers), method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                txt = resp.read().decode("utf-8", "ignore")
                # keep cookie from Set-Cookie if any - limited without session
                ok = txt and not self._is_verify(txt)
                if ok:
                    self._ok_ts = time.time()
                return ok
        except Exception as e:
            print("pass_verify err", e)
            return False

    def _ensure_pass(self):
        if self._ok_ts and time.time() - self._ok_ts < 1800:
            return True
        url = HOST + "/list/new.html"
        html = self._raw_get(url)
        if not self._is_verify(html):
            self._ok_ts = time.time()
            return True
        return self._pass_verify(html, url)

    def _raw_get(self, url, headers=None):
        try:
            sess = self._session()
            if sess is not None:
                r = sess.get(url, headers=self._headers(headers), timeout=15, verify=False)
                return r.text or ""
            req = urllib.request.Request(url, headers=self._headers(headers))
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "ignore")
        except Exception as e:
            print("raw_get", e)
            return ""

    def _get(self, url, headers=None):
        self._ensure_pass()
        html = self._raw_get(url, headers)
        if self._is_verify(html):
            self._pass_verify(html, url)
            html = self._raw_get(url, headers)
        return html or ""

    def _post(self, url, body, headers=None):
        self._ensure_pass()
        h = self._headers(headers)
        h.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        try:
            sess = self._session()
            if sess is not None:
                r = sess.post(url, data=body, headers=h, timeout=15, verify=False)
                return r.text or ""
            data = body.encode("utf-8") if isinstance(body, str) else body
            req = urllib.request.Request(url, data=data, headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("post err", e)
            return ""

    def _abs(self, u):
        if not u:
            return ""
        u = str(u).strip()
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return HOST + u
        return u

    def _clean(self, t):
        return re.sub(r"<[^>]+>", " ", str(t or "")).replace("&nbsp;", " ").strip()

    def _song_id(self, href):
        m = re.search(r"/m/([^.]+)\.html", href or "")
        return m.group(1) if m else ""

    def _parse_songs(self, html):
        songs, seen = [], set()
        if not html or self._is_verify(html):
            return songs
        # 主模式：name 链接
        for m in re.finditer(
            r'<div class="name">\s*<a href="(/m/[^"]+\.html)"[^>]*>([^<]+)</a>',
            html,
            re.I,
        ):
            sid = self._song_id(m.group(1))
            if not sid or sid in seen:
                continue
            seen.add(sid)
            title = self._clean(m.group(2))
            songs.append({
                "vod_id": "song@" + sid,
                "vod_name": title or sid,
                "vod_pic": "",
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 1.0},
            })
        # 兜底：任意 /m/ 链接
        if len(songs) < 3:
            for m in re.finditer(r'href="(/m/([a-f0-9]+)\.html)"[^>]*>([^<]{1,80})</a>', html, re.I):
                sid = m.group(2)
                if sid in seen:
                    continue
                seen.add(sid)
                songs.append({
                    "vod_id": "song@" + sid,
                    "vod_name": self._clean(m.group(3)) or sid,
                    "vod_pic": "",
                    "vod_remarks": "",
                    "style": {"type": "rect", "ratio": 1.0},
                })
        return songs

    def _parse_folders(self, html, prefix, remark):
        items, seen = [], set()
        if not html or self._is_verify(html):
            return items
        for m in re.finditer(
            r'<div class="name">\s*<a href="(%s[^"]+)"[^>]*(?:title="([^"]*)")?[^>]*>([^<]*)</a>'
            % re.escape(prefix),
            html,
            re.I,
        ):
            href = m.group(1)
            if href in seen:
                continue
            seen.add(href)
            title = self._clean(m.group(2) or m.group(3))
            # 附近图片
            start = max(0, m.start() - 400)
            near = html[start : m.end()]
            im = re.search(r'<img[^>]+src="([^"]+)"', near, re.I)
            items.append({
                "vod_id": "folder@" + self._abs(href),
                "vod_name": title or href,
                "vod_pic": self._abs(im.group(1)) if im else "",
                "vod_remarks": remark,
                "style": {"type": "rect", "ratio": 1.0},
            })
        # 兜底
        if len(items) < 2:
            for m in re.finditer(
                r'href="(%s[^"]+)"[^>]*>([^<]{1,60})</a>' % re.escape(prefix),
                html,
                re.I,
            ):
                href = m.group(1)
                if href in seen or "index" in href and href.count("/") > 3:
                    # still allow
                    pass
                if href in seen:
                    continue
                seen.add(href)
                items.append({
                    "vod_id": "folder@" + self._abs(href),
                    "vod_name": self._clean(m.group(2)),
                    "vod_pic": "",
                    "vod_remarks": remark,
                    "style": {"type": "rect", "ratio": 1.0},
                })
        return items

    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": {}, "list": []}

    def homeVideoContent(self):
        html = self._get(HOST + "/list/new.html")
        return {"list": self._parse_songs(html)[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        tid = str(tid or "new")
        path = PATH_MAP.get(tid, "/list/new.html")
        html = self._get(HOST + path)
        if tid in ("new", "top"):
            items = self._parse_songs(html)
        elif tid == "singer":
            items = self._parse_folders(html, "/s/", "歌手")
        elif tid == "playtype":
            items = self._parse_folders(html, "/p/", "歌单")
        elif tid == "album":
            items = self._parse_folders(html, "/a/", "专辑")
        elif tid == "mv":
            items = self._parse_folders(html, "/v/", "MV")
        else:
            items = self._parse_songs(html)
        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": 40,
            "total": len(items),
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        html = self._get(HOST + "/so/%s.html" % urllib.parse.quote(str(key)))
        songs = self._parse_songs(html)
        return {"list": songs, "page": 1, "pagecount": 1, "limit": 20, "total": len(songs)}

    def _play_info(self, song_id):
        body = "id=%s&type=music" % urllib.parse.quote(song_id)
        txt = self._post(
            HOST + "/js/play.php",
            body,
            {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "%s/m/%s.html" % (HOST, song_id),
            },
        )
        try:
            return json.loads(txt or "{}")
        except Exception:
            return {}

    def detailContent(self, ids):
        raw = str((ids or [""])[0]).strip()
        if raw.startswith("song@"):
            sid = raw[5:]
            html = self._get("%s/m/%s.html" % (HOST, sid))
            info = self._play_info(sid)
            name = sid
            m = re.search(r'<div class="djname"><h1>(.*?)<a', html or "", re.S | re.I)
            if m:
                name = self._clean(m.group(1))
            if not name or name == sid:
                name = (info.get("title") or sid).strip()
            pic = info.get("pic") or ""
            if not pic:
                m = re.search(r'id="mcover"\s+src="([^"]+)"', html or "")
                if m:
                    pic = self._abs(m.group(1))
            play_url = (info.get("url") or "").strip()
            return {"list": [{
                "vod_id": raw,
                "vod_name": name,
                "vod_pic": self._abs(pic),
                "vod_remarks": "音乐",
                "vod_content": "AAZ音乐网在线试听",
                "vod_play_from": "在线试听",
                "vod_play_url": "播放$%s" % (play_url or sid),
            }]}
        url = raw[7:] if raw.startswith("folder@") else raw
        if not url.startswith("http"):
            url = self._abs(url)
        html = self._get(url)
        title = url
        m = re.search(r'<div class="title">\s*<h1>(.*?)</h1>', html or "", re.I | re.S)
        if m:
            title = self._clean(m.group(1))
        pic = ""
        m = re.search(r'<div class="pic">\s*<img src="([^"]+)"', html or "", re.I | re.S)
        if m:
            pic = self._abs(m.group(1))
        eps = []
        for m in re.finditer(
            r'<div class="name">\s*<a href="(/m/[^"]+\.html)"[^>]*>([^<]+)</a>',
            html or "",
            re.I,
        ):
            sid = self._song_id(m.group(1))
            if sid:
                eps.append("%s$%s" % (self._clean(m.group(2)), sid))
        if not eps:
            eps = ["暂无$"]
        return {"list": [{
            "vod_id": raw,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": "列表",
            "vod_content": "歌曲列表",
            "vod_play_from": "歌曲列表",
            "vod_play_url": "#".join(eps),
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()
        head = {"User-Agent": UA, "Referer": HOST + "/"}
        if play.startswith("http"):
            return {"parse": 0, "jx": 0, "url": play, "header": head}
        info = self._play_info(play)
        url = (info.get("url") or "").strip()
        if url:
            return {"parse": 0, "jx": 0, "url": url, "header": head}
        return {"parse": 1, "jx": 1, "url": "%s/m/%s.html" % (HOST, play), "header": head}

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(mp3|m4a|mp4|m3u8)(\?|$)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("home", sp.homeContent())
    for tid in ["new", "top", "singer", "playtype", "album", "mv"]:
        r = sp.categoryContent(tid, 1, False, {})
        print(tid, len(r.get("list") or []), (r["list"][0]["vod_name"] if r.get("list") else None))
    r = sp.categoryContent("new", 1, False, {})
    if r.get("list"):
        d = sp.detailContent([r["list"][0]["vod_id"]])
        print("detail", d["list"][0].get("vod_name"), str(d["list"][0].get("vod_play_url"))[:80])
        p = sp.playerContent("在线试听", d["list"][0]["vod_play_url"].split("$")[-1], [])
        print("play", p.get("parse"), str(p.get("url"))[:80])

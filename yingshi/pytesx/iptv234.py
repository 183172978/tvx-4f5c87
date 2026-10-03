# -*- coding: utf-8 -*-
"""IPTV234  https://m.234iptv.com  密文: reverse + 双重b64 XOR"""
import re
import json
import sys

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    requests = None

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

HOST = "https://m.234iptv.com"
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.6 Mobile/15E148 Safari/604.1"
)
CHANNELS = [
    ("tv", "综合"),
    ("ty", "体育"),
    ("ys", "央视"),
    ("ws", "卫视"),
    ("gt", "港澳台"),
]


class Spider(BaseSpider):
    def init(self, extend=""):
        global HOST
        try:
            if extend and str(extend).strip().startswith("{"):
                conf = json.loads(extend)
                if conf.get("host"):
                    HOST = str(conf["host"]).rstrip("/")
        except Exception:
            pass
        self.session = None
        if requests is not None:
            self.session = requests.Session()
            self.session.headers.update({"User-Agent": UA, "Referer": HOST + "/"})
            self.session.verify = False

    def getName(self):
        return "IPTV234"

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv", ".mpd", "play.php"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass

    def _headers(self):
        return {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": HOST + "/",
        }

    def _get(self, path, timeout=12):
        if str(path).startswith("http"):
            url = path
        elif str(path).startswith("?"):
            url = HOST + "/" + path
        elif str(path).startswith("/"):
            url = HOST + path
        else:
            url = HOST + "/" + path
        try:
            if self.session is not None:
                r = self.session.get(url, headers=self._headers(), timeout=timeout)
                return r.text or ""
            import urllib.request
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("get err", e)
            return ""

    def _eval_concat(self, expr):
        out = []
        for text, rev in re.findall(
            r'"([^"]*)"(\.split\(""\)\.reverse\(\)\.join\(""\))?', expr or ""
        ):
            out.append(text[::-1] if rev else text)
        return "".join(out)

    def _b64(self, data):
        key_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        if not data:
            return ""
        data = str(data)
        i = 0
        tmp = []
        n = len(data)
        while i < n:
            def idx(j):
                if j >= n:
                    return 64
                try:
                    return key_str.index(data[j])
                except ValueError:
                    return 64
            h1, h2, h3, h4 = idx(i), idx(i + 1), idx(i + 2), idx(i + 3)
            i += 4
            bits = (h1 << 18) | (h2 << 12) | (h3 << 6) | h4
            a1, a2, a3 = (bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF
            if h3 == 64:
                tmp.append(chr(a1))
            elif h4 == 64:
                tmp.append(chr(a1) + chr(a2))
            else:
                tmp.append(chr(a1) + chr(a2) + chr(a3))
        return "".join(tmp)

    def _crypto(self, html):
        scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html or "", re.I)
        key_script = ""
        dec_script = ""
        for s in scripts:
            # 密钥脚本：含 var + reverse 拼接，且不含 keyStr（避免命中解码函数）
            if (
                'split("").reverse().join("")' in s
                and "var " in s
                and "keyStr" not in s
                and len(s) < 4000
            ):
                key_script = s
            if "keyStr" in s and "fromCharCode" in s:
                dec_script = s
        concats = []
        for e in re.findall(r"var\s+\w+\s*=\s*([^;]+);", key_script):
            e = e.strip()
            if e in ('""', "''"):
                continue
            if '"' in e and ("+" in e or "split" in e):
                concats.append(self._eval_concat(e))
        hx = re.findall(r'=\s*"([0-9a-f]{32})"', key_script)
        key = concats[0] if concats else ""
        new_tok = concats[1] if len(concats) > 1 else ""
        old_tok = hx[0] if hx else ""
        m = re.search(r'key\s*=\s*key\s*\+\s*"([0-9a-fA-F]+)"', dec_script or html or "")
        suffix = m.group(1) if m else "43aefdfa716367e6"
        return key, old_tok, new_tok, suffix

    def _decode_one(self, enc, key, old_tok, new_tok, suffix):
        if not enc:
            return ""
        enc = str(enc).strip()
        if enc.startswith("http"):
            return enc
        try:
            tix = enc[::-1]
            string = self._b64(tix)
            full = str(key) + str(suffix)
            if not full:
                return ""
            code = "".join(
                chr(ord(string[i]) ^ ord(full[i % len(full)]))
                for i in range(len(string))
            )
            tix = self._b64(code)
            if old_tok:
                tix = tix.replace("token=" + old_tok, "token=" + new_tok)
            if key:
                tix = tix.replace(key, "")
            tix = tix.strip()
            return tix if tix.startswith("http") else ""
        except Exception as e:
            print("dec err", e)
            return ""

    def _extract_play_urls(self, html):
        key, old_tok, new_tok, suffix = self._crypto(html)
        opts = re.findall(
            r'<option[^>]*value=["\']([^"\']+)["\'][^>]*>([^<]*)</option>',
            html or "",
            re.I,
        )
        out = []
        for enc, lab in opts:
            u = self._decode_one(enc, key, old_tok, new_tok, suffix)
            if u:
                out.append(((lab or "线路").strip() or "线路", u))
        return out

    def _parse_list(self, html):
        videos, seen = [], set()
        for m in re.finditer(
            r'href=["\']\?act=play&tid=([^&"\']+)&id=(\d+)["\'][^>]*>([^<]+)',
            html or "",
            re.I,
        ):
            t, cid, name = m.group(1), m.group(2), m.group(3).strip()
            if not name or name in ("返回", "首頁"):
                continue
            vid = "%s_%s" % (t, cid)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "🔴 LIVE",
                "style": {"type": "rect", "ratio": 1.5},
            })
        return videos

    def homeContent(self, filter=False):
        return {
            "class": [{"type_id": t, "type_name": n} for t, n in CHANNELS],
            "filters": {},
        }

    def homeVideoContent(self):
        return {"list": self._parse_list(self._get("/?tid=tv"))[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        tid = str(tid or "tv")
        videos = self._parse_list(self._get("/?tid=" + tid))
        return {
            "list": videos,
            "page": 1,
            "pagecount": 1,
            "limit": max(len(videos), 1),
            "total": len(videos),
        }

    def searchContent(self, key, quick=False, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick=False, pg=1):
        key = str(key or "").strip().lower()
        if not key:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        out = []
        for t, _ in CHANNELS:
            for v in self._parse_list(self._get("/?tid=" + t)):
                if key in str(v.get("vod_name") or "").lower():
                    out.append(v)
        return {"list": out, "page": 1, "pagecount": 1, "limit": 50, "total": len(out)}

    def detailContent(self, ids):
        raw = str((ids[0] if ids else "") or "").strip()
        m = re.match(r"([a-zA-Z0-9]+)_(\d+)", raw)
        if not m:
            return {"list": []}
        tid, cid = m.group(1), m.group(2)
        html = self._get("/?act=play&tid=%s&id=%s" % (tid, cid))
        title = raw
        tm = re.search(r"<h1[^>]*>([^<]+)</h1>", html or "", re.I)
        if tm:
            title = re.sub(r"\s*-\s*電視直播.*$", "", tm.group(1)).strip()
        plays = self._extract_play_urls(html)
        if not plays:
            # 再试一次
            html = self._get("/?act=play&tid=%s&id=%s" % (tid, cid))
            plays = self._extract_play_urls(html)
        if plays:
            play_url = "#".join("%s$%s" % (n, u) for n, u in plays)
        else:
            # 保底：把 vid 交给 playerContent 再解
            play_url = "直播$%s_%s" % (tid, cid)
        return {
            "list": [{
                "vod_id": "%s_%s" % (tid, cid),
                "vod_name": title,
                "vod_pic": "",
                "vod_remarks": "🔴 LIVE",
                "vod_content": title,
                "vod_play_from": "IPTV234",
                "vod_play_url": play_url,
                "style": {"type": "rect", "ratio": 1.5},
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        head = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Origin": HOST,
            "Accept": "*/*",
        }
        play = str(id or "").strip()
        if "$" in play:
            play = play.split("$")[-1].strip()

        # 直链 / play.php
        if play.startswith("http") and "act=play" not in play:
            return {"parse": 0, "jx": 0, "url": play, "header": head}

        tid = cid = ""
        m = re.match(r"([a-zA-Z0-9]+)_(\d+)$", play)
        if m:
            tid, cid = m.group(1), m.group(2)
        else:
            m = re.search(r"[?&]tid=([^&]+).*?[?&]id=(\d+)", play)
            if m:
                tid, cid = m.group(1), m.group(2)

        if tid and cid:
            html = self._get("/?act=play&tid=%s&id=%s" % (tid, cid))
            plays = self._extract_play_urls(html)
            if plays:
                return {"parse": 0, "jx": 0, "url": plays[0][1], "header": head}

        # 最后兜底：不要返回空字符串导致 Url: -
        # 用 sniff 模式打开播放页
        if tid and cid:
            return {
                "parse": 1,
                "jx": 0,
                "url": "%s/?act=play&tid=%s&id=%s" % (HOST, tid, cid),
                "header": head,
            }
        return {"parse": 1, "jx": 0, "url": HOST + "/", "header": head}


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    d = sp.detailContent(["tv_1"])
    print(d["list"][0]["vod_play_url"][:120])
    print(sp.playerContent("x", "tv_1", []))

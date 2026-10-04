#!/usr/bin/env python3
"""JAVDAY Type-3 Spider for fish2018/WebHTV.

The Spider lifecycle is Android/WebHTV compatible.  The CLI is a bounded,
read-only verifier for the exact same file.
"""

import argparse
import hashlib
import html as html_module
import inspect
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

try:
    from base.spider import Spider as BaseSpider
except ImportError:  # clean-room CLI outside WebHTV
    class BaseSpider:
        def __init__(self):
            self.extend = ""

        def getProxyUrl(self, local=True):
            return "http://127.0.0.1:9978/proxy?do=py"


BASE_URL = "https://javday.app/"
USER_AGENT = "Mozilla/5.0 (Linux; Android 13; WebHTV) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"
REQUEST_TIMEOUT = 15
PAGE_SIZE = 20
CATEGORIES = (
    ("/label/new/", "最近更新"),
    ("/label/hot/", "人氣系列"),
    ("/category/new-release/", "新作上市"),
    ("/category/censored/", "有碼"),
    ("/category/uncensored/", "無碼"),
    ("/category/chinese-av/", "國產AV"),
    ("/category/uncensored-leaked/", "無碼流出"),
    ("/category/sex8/", "杏吧"),
    ("/category/hongkongdoll/", "HongKongDoll"),
    ("/category/aiav/", "AI短劇"),
)


def _text(value):
    value = re.sub(r"<[^>]*>", "", value or "")
    return html_module.unescape(re.sub(r"\s+", " ", value)).strip()


def _safe_title(value):
    return (value or "").replace("#", " ").replace("$", " ").strip()


def _absolute(base_url, value):
    return urllib.parse.urljoin(base_url, html_module.unescape(value or ""))


def category_path(route, page):
    page = max(1, int(page))
    route = "/" + route.strip("/") + "/"
    return route if page == 1 else route + "page/{}/".format(page)


def search_path(keyword, page):
    page = max(1, int(page))
    encoded = urllib.parse.quote(str(keyword).strip(), safe="")
    root = "/search/wd/{}/".format(encoded)
    return root if page == 1 else root + "page/{}/".format(page)


def parse_video_cards(document, base_url=BASE_URL):
    rows = []
    seen = set()
    anchor_re = re.compile(
        r'<a\b[^>]*href=["\'](?P<href>/videos/[^"\']+/)["\'][^>]*class=["\'][^"\']*\bvideoBox\b[^"\']*["\'][^>]*>(?P<body>.*?)(?=</a>)',
        re.I | re.S,
    )
    for match in anchor_re.finditer(document or ""):
        href = match.group("href")
        vod_id = href.strip("/").split("/")[-1]
        if not vod_id or vod_id in seen:
            continue
        body = match.group("body")
        title_match = re.search(r'<span\b[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>(.*?)</span>', body, re.I | re.S)
        pic_match = re.search(r'background-image\s*:\s*url\(\s*["\']?([^\)"\']+)', body, re.I)
        remark_match = re.search(r'<span\b[^>]*class=["\'][^"\']*\bvideoBox-time\b[^"\']*["\'][^>]*>(.*?)</span>', body, re.I | re.S)
        title = _text(title_match.group(1) if title_match else vod_id)
        raw_pic = html_module.unescape(pic_match.group(1).strip() if pic_match else "").strip("\"'")
        pic = _absolute(base_url, raw_pic)
        remark = _text(remark_match.group(1) if remark_match else "")
        rows.append({
            "vod_id": vod_id,
            "vod_name": title or vod_id,
            "vod_pic": pic,
            "vod_remarks": remark,
        })
        seen.add(vod_id)
    return rows


def _first_group(document, pattern):
    match = re.search(pattern, document or "", re.I | re.S)
    return match.group(1).strip() if match else ""


def _all_text(document, pattern):
    return [_text(item) for item in re.findall(pattern, document or "", re.I | re.S) if _text(item)]


def extract_media_url(document):
    patterns = (
        r'new\s+Artplayer\s*\(\s*\{.*?\burl\s*:\s*["\'](https://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
        r'<source\b[^>]*src=["\'](https://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
        r'(https://[^"\'<>\s]+\.m3u8(?:\?[^"\'<>\s]*)?)',
    )
    for pattern in patterns:
        value = _first_group(document, pattern)
        if value:
            return html_module.unescape(value)
    return ""


def parse_detail(document, vod_id, base_url=BASE_URL):
    title = _text(_first_group(document, r'<h1\b[^>]*class=["\'][^"\']*\bvideo-title\b[^"\']*["\'][^>]*>(.*?)</h1>'))
    number = _text(_first_group(document, r'<span\b[^>]*class=["\'][^"\']*\bjpnum\b[^"\']*["\'][^>]*>(.*?)</span>'))
    actor_block = _first_group(document, r'<span\b[^>]*class=["\'][^"\']*\bvod_actor\b[^"\']*["\'][^>]*>(.*?)</span>')
    actors = _all_text(actor_block, r'<a\b[^>]*>(.*?)</a>')
    tag_block = _first_group(document, r'<span\b[^>]*class=["\'][^"\']*\btag\b[^"\']*["\'][^>]*>(.*?)</span>')
    tags = _all_text(tag_block, r'<a\b[^>]*>(.*?)</a>')
    poster = _first_group(document, r'<meta\b[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)')
    if not poster:
        poster = _first_group(document, r'\bposter\s*:\s*["\']([^"\']+)["\']')
    media_url = extract_media_url(document)
    detail = {
        "vod_id": str(vod_id),
        "vod_name": title or number or str(vod_id),
        "vod_pic": _absolute(base_url, poster),
        "vod_actor": ", ".join(actors),
        "vod_tag": ", ".join(tags),
        "vod_content": "番號：{}\n標籤：{}".format(number, ", ".join(tags)).strip(),
        "vod_play_from": "Javday" if media_url else "",
        "vod_play_url": "正片${}".format(vod_id) if media_url else "",
        "media_url": media_url,
    }
    return detail


def advertised_pagecount(document, current_page, item_count):
    numbers = [int(x) for x in re.findall(r'/page/(\d+)/', document or "", re.I)]
    if numbers:
        return max(max(numbers), int(current_page))
    return int(current_page) + (1 if item_count >= PAGE_SIZE else 0)


def playlist_summary(text):
    if not (text or "").lstrip().startswith("#EXTM3U"):
        raise ValueError("not an HLS playlist")
    durations = [float(x) for x in re.findall(r'#EXTINF:([0-9.]+)', text)]
    uris = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return {
        "kind": "master" if "#EXT-X-STREAM-INF" in text else "media",
        "object_count": len(uris),
        "duration_seconds": round(sum(durations), 3),
        "endlist": "#EXT-X-ENDLIST" in text,
        "first_uri": uris[0] if uris else "",
    }


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"})

    def init(self, extend=""):
        self.extend = extend or ""

    def getName(self):
        return "JAVDAY"

    def getDependence(self):
        return []

    def _get(self, path_or_url, timeout=REQUEST_TIMEOUT, headers=None, stream=False):
        url = path_or_url if str(path_or_url).startswith(("http://", "https://")) else _absolute(BASE_URL, path_or_url)
        merged = dict(self._session.headers)
        if headers:
            merged.update(headers)
        try:
            response = self._session.get(url, headers=merged, timeout=timeout, allow_redirects=True, stream=stream)
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            response = self._session.get(url, headers=merged, timeout=timeout, allow_redirects=True, stream=stream)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response

    def homeContent(self, filter):
        return {"class": [{"type_id": route, "type_name": name} for route, name in CATEGORIES], "filters": {}, "list": []}

    def homeVideoContent(self):
        try:
            rows = parse_video_cards(self._get("/").text, BASE_URL)
            return {"list": rows[:PAGE_SIZE]}
        except Exception as error:
            return {"list": [], "msg": "首頁請求失敗：{}".format(type(error).__name__)}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg))
        route = tid if any(tid == item[0] for item in CATEGORIES) else CATEGORIES[0][0]
        try:
            document = self._get(category_path(route, page)).text
            rows = parse_video_cards(document, BASE_URL)
            pagecount = advertised_pagecount(document, page, len(rows))
            return {"page": page, "pagecount": pagecount, "limit": PAGE_SIZE, "total": pagecount * PAGE_SIZE, "list": rows}
        except Exception as error:
            return {"page": page, "pagecount": page, "limit": PAGE_SIZE, "total": 0, "list": [], "msg": "分類請求失敗：{}".format(type(error).__name__)}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg))
        if not str(key).strip():
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}
        try:
            document = self._get(search_path(key, page)).text
            rows = parse_video_cards(document, BASE_URL)
            pagecount = advertised_pagecount(document, page, len(rows))
            return {"page": page, "pagecount": pagecount, "limit": PAGE_SIZE, "total": pagecount * PAGE_SIZE, "list": rows}
        except Exception as error:
            return {"page": page, "pagecount": page, "limit": PAGE_SIZE, "total": 0, "list": [], "msg": "搜尋請求失敗：{}".format(type(error).__name__)}

    def detailContent(self, ids):
        vod_id = str(ids[0] if isinstance(ids, (list, tuple)) else ids).strip()
        try:
            document = self._get("/videos/{}/".format(urllib.parse.quote(vod_id, safe=""))).text
            detail = parse_detail(document, vod_id, BASE_URL)
            detail.pop("media_url", None)
            return {"list": [detail]}
        except Exception as error:
            return {"list": [], "msg": "詳情請求失敗：{}".format(type(error).__name__)}

    def playerContent(self, flag, id, vipFlags):
        vod_id = str(id).split("$")[-1].strip()
        if flag and flag != "Javday":
            return {"parse": 0, "playUrl": "", "url": "", "header": {}, "msg": "未知播放線路"}
        try:
            document = self._get("/videos/{}/".format(urllib.parse.quote(vod_id, safe=""))).text
            media_url = extract_media_url(document)
            if not media_url:
                return {"parse": 0, "playUrl": "", "url": "", "header": {}, "msg": "詳情頁未發現已證實媒體源"}
            return {
                "parse": 0,
                "playUrl": "",
                "url": media_url,
                "header": {"User-Agent": USER_AGENT, "Referer": _absolute(BASE_URL, "/videos/{}/".format(vod_id))},
            }
        except Exception as error:
            return {"parse": 0, "playUrl": "", "url": "", "header": {}, "msg": "播放請求失敗：{}".format(type(error).__name__)}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"JAVDAY Spider does not require local proxy"]

    def liveContent(self, url):
        return ""

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(?:m3u8|mp4)(?:$|\?)", str(url), re.I))

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return {}

    def destroy(self):
        try:
            self._session.close()
        except Exception:
            pass


def _check(name, status, **details):
    item = {"status": status}
    item.update(details)
    return name, item


def self_test():
    checks = {}
    expected = {
        "init": 2,
        "homeContent": 2,
        "homeVideoContent": 1,
        "categoryContent": 5,
        "detailContent": 2,
        "searchContent": 4,
        "playerContent": 4,
        "localProxy": 2,
    }
    for name, count in expected.items():
        actual = len(inspect.signature(getattr(Spider, name)).parameters)
        checks[name] = {"status": "PASS" if actual == count else "FAIL", "parameters": actual}
    fixture = Path(__file__).resolve().parent / "fixtures" / "probe-5.html"
    if fixture.exists():
        detail = parse_detail(fixture.read_text(encoding="utf-8"), "IPZZ932", BASE_URL)
        checks["fixture_detail"] = {"status": "PASS" if detail.get("media_url", "").endswith(".m3u8") else "FAIL"}
    proxy = Spider().localProxy({})
    checks["local_proxy_contract"] = {"status": "PASS" if len(proxy) >= 3 and isinstance(proxy[0], int) else "FAIL"}
    success = all(value["status"] == "PASS" for value in checks.values())
    return {"success": success, "checks": checks}


def live_test(max_items=3):
    spider = Spider()
    checks = {}
    blocked = []
    try:
        home = spider.homeContent(True)
        checks["home"] = {"status": "PASS" if home.get("class") else "FAIL", "class_count": len(home.get("class", []))}
        cat1 = spider.categoryContent("/category/censored/", "1", False, {})
        cat2 = spider.categoryContent("/category/censored/", "2", False, {})
        ids1 = [x.get("vod_id") for x in cat1.get("list", [])]
        ids2 = [x.get("vod_id") for x in cat2.get("list", [])]
        checks["category_page_1"] = {"status": "PASS" if ids1 else "FAIL", "items": len(ids1), "unique_ids": len(set(ids1))}
        checks["category_page_2"] = {"status": "PASS" if ids2 and not (set(ids1) & set(ids2)) else "FAIL", "items": len(ids2), "overlap": len(set(ids1) & set(ids2))}
        search_a = spider.searchContent("JULIA", False, "1")
        search_b = spider.searchContent("JULIA", False, "2")
        a_ids = {x.get("vod_id") for x in search_a.get("list", [])}
        b_ids = {x.get("vod_id") for x in search_b.get("list", [])}
        search_ok = bool(a_ids and b_ids and a_ids != b_ids)
        checks["search"] = {"status": "PASS" if search_ok else "FAIL", "keyword": "JULIA", "page_1_items": len(a_ids), "page_2_items": len(b_ids), "overlap": len(a_ids & b_ids)}
        detail_id = "IPZZ932"
        detail = spider.detailContent([detail_id])
        vod = detail.get("list", [{}])[0] if detail.get("list") else {}
        checks["detail"] = {"status": "PASS" if vod.get("vod_id") == detail_id and vod.get("vod_play_url") else "FAIL", "source_groups": len(vod.get("vod_play_from", "").split("$$$")) if vod.get("vod_play_from") else 0}
        player = spider.playerContent("Javday", detail_id, [])
        media_url = player.get("url", "")
        checks["player"] = {"status": "PASS" if media_url.endswith(".m3u8") and player.get("parse") == 0 else "FAIL", "kind": "hls" if ".m3u8" in media_url else "unknown", "url_sha256_prefix": hashlib.sha256(media_url.encode()).hexdigest()[:12] if media_url else ""}
        if media_url:
            response = spider._get(media_url, headers=player.get("header", {}))
            summary = playlist_summary(response.text)
            checks["playlist"] = {"status": "PASS", "kind": summary["kind"], "objects": summary["object_count"], "duration_seconds": summary["duration_seconds"], "endlist": summary["endlist"]}
            object_url = urllib.parse.urljoin(response.url, summary["first_uri"])
            try:
                probe = spider._get(object_url, timeout=20, headers={**player.get("header", {}), "Range": "bytes=0-0"}, stream=True)
                one = next(probe.iter_content(1), b"")
                status = "PASS" if probe.status_code in (200, 206) and one else "FAIL"
                checks["media_object"] = {"status": status, "http": probe.status_code, "bytes": len(one), "content_type": probe.headers.get("Content-Type", "")}
                if status != "PASS":
                    blocked.append("BLOCKED:MEDIA_OBJECT_EMPTY")
            except Exception as error:
                checks["media_object"] = {"status": "BLOCKED", "error": type(error).__name__}
                blocked.append("BLOCKED:MEDIA_SEGMENT_RANGE_{}".format(type(error).__name__.upper()))
        else:
            checks["playlist"] = {"status": "BLOCKED"}
            checks["media_object"] = {"status": "BLOCKED"}
            blocked.append("BLOCKED:FULL_MEDIA_PROVENANCE_UNPROVEN")
        checks["device_playback"] = {"status": "PENDING_USER_DEVICE"}
    except Exception as error:
        blocked.append("BLOCKED:LIVE_TEST_{}".format(type(error).__name__.upper()))
        checks["fatal"] = {"status": "FAIL", "error": type(error).__name__}
    finally:
        spider.destroy()
    hard_fail = any(item.get("status") == "FAIL" for item in checks.values())
    return {
        "success": not hard_fail and not blocked,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks,
        "blocked": blocked,
        "redactions": ["full media URL", "cookies", "signed query"],
        "max_items": int(max_items),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="JAVDAY WebHTV Type-3 Spider verifier")
    parser.add_argument("--self-test", action="store_true", help="run offline ABI/parser checks")
    parser.add_argument("--live-test", action="store_true", help="run bounded read-only live checks")
    parser.add_argument("--max-items", type=int, default=3, help="maximum sample items reported")
    parser.add_argument("--json-output", help="write JSON result to this path")
    args = parser.parse_args(argv)
    if args.live_test:
        result = live_test(max(1, min(args.max_items, 10)))
    elif args.self_test:
        result = self_test()
    else:
        parser.print_help()
        return 0
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.json_output:
        Path(args.json_output).write_text(output + "\n", encoding="utf-8")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

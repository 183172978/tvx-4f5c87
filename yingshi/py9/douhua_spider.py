# -*- coding: utf-8 -*-
# //@name:豆花影视直播放
# //@id:douhua_direct
# //@version:2

import base64
import html as html_lib
import ipaddress
import json
import re
import time
from urllib.parse import parse_qs, quote, unquote_plus, urlencode, urljoin, urlsplit

import requests
from lxml import html

from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    name = "豆花影视直播放"
    host = "https://dhvideo.cc"
    discovery_host = "https://douhua.me"
    backend_parse = False
    category_mode = False
    categoryMode = False

    PLAY_PREFIX = "douhua-play:"
    MAGNET_PREFIX = "douhua-magnet:"
    ERROR_PREFIX = "douhua-error:"
    DEFAULT_PIC = "https://dhvideo.cc/template/douhua/douhua.me.png"

    CATEGORY_SPECS = (
        ("dianying", "电影", "/dianying.html"),
        ("dianshiju", "电视剧", "/dianshiju.html"),
        ("zongyi", "综艺", "/zongyi.html"),
        ("dongman", "动漫", "/dongman.html"),
        ("duanju", "短剧", "/duanju.html"),
    )
    CATEGORY_PATHS = dict((item[0], item[2]) for item in CATEGORY_SPECS)

    SORTS = (
        ("最新", ""),
        ("热门", "play_hot"),
        ("豆瓣评分", "group_douban"),
    )
    CLASSES = (
        "剧情", "喜剧", "动作", "爱情", "惊悚", "犯罪", "恐怖", "悬疑",
        "冒险", "奇幻", "科幻", "院线", "家庭", "历史", "战争", "纪录片",
        "古装", "音乐", "动画", "传记", "武侠", "运动", "西部", "短片",
    )
    AREAS = (
        "中国大陆", "美国", "日本", "英国", "中国香港", "法国", "韩国",
        "加拿大", "印度", "德国", "意大利", "中国台湾", "西班牙", "泰国",
        "俄罗斯", "澳大利亚",
    )
    YEARS = tuple(str(value) for value in range(2026, 1999, -1)) + (
        "2020年代", "2010年代", "2000年代", "90年代", "80年代", "70年代",
    )
    SOURCE_NAMES = {
        "vip": "超级线路",
        "modum3u8": "魔都",
        "jsm3u8": "极速",
        "mtm3u8": "茅台",
        "1080zyk": "1080资源",
        "lzm3u8": "量子",
        "bfzym3u8": "暴风",
        "dyttm3u8": "电影天堂",
        "ffm3u8": "非凡",
        "wztv": "网真",
    }
    SOURCE_PRIORITY = {
        "jsm3u8": 0,
        "wztv": 1,
        "lzm3u8": 2,
        "bfzym3u8": 3,
        "ffm3u8": 4,
        "dyttm3u8": 5,
        "1080zyk": 6,
        "modum3u8": 7,
        "vip": 8,
        "mtm3u8": 9,
    }

    DETAIL_PATH_RE = re.compile(
        r"^/(?:movie|tv)/[0-9a-f]{24}(?:[-/]\d+)\.html$", re.I
    )
    PLAYER_DATA_RE = re.compile(
        r"\baa\s*:\s*JSON\.parse\(\s*'((?:\\.|[^'])*)'\s*\)", re.I | re.S
    )
    PAGE_RE = re.compile(r"(?:\?|&)page=(\d+)", re.I)
    BTIH_RE = re.compile(r"btih:([A-F0-9]{40}|[A-Z2-7]{32})", re.I)
    CHALLENGE_MARKERS = (
        "just a moment",
        "/cdn-cgi/challenge-platform",
        "cf-turnstile",
        "attention required",
    )

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.timeout = 15
        self.cache_ttl = 60
        self.verify_tls = True
        self.trust_env = True
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        self._active_host = self.host
        self._session = None
        self._cache = {}
        self._discovery_checked = False
        self._reset_session()

    def getName(self):
        return self.name

    def init(self, extend=""):
        config = self._parse_dict(extend)
        configured_host = self._safe_origin(config.get("host"))
        configured_discovery = self._safe_origin(config.get("discovery_host"))
        if configured_host:
            self.host = configured_host
        if configured_discovery:
            self.discovery_host = configured_discovery
        self.timeout = self._bounded_int(config.get("timeout"), self.timeout, 5, 45)
        self.cache_ttl = self._bounded_int(
            config.get("cache_ttl"), self.cache_ttl, 0, 600
        )
        self.verify_tls = self._bool_value(config.get("verify_tls"), self.verify_tls)
        self.trust_env = self._bool_value(config.get("trust_env"), self.trust_env)
        user_agent = self._clean_text(config.get("user_agent"))
        if user_agent:
            self.user_agent = user_agent
        self._active_host = self.host
        self._cache.clear()
        self._discovery_checked = False
        self._reset_session()

    def destroy(self):
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        self._session = None
        self._cache.clear()

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|webm)(?:$|[?#])", str(url or ""), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"not found"]

    def homeContent(self, filter):
        classes = [
            {"type_id": type_id, "type_name": type_name}
            for type_id, type_name, _ in self.CATEGORY_SPECS
        ]
        common = [
            self._filter_row("sort_field", "排序", self.SORTS),
            self._filter_row("class", "类型", (("全部", ""),) + tuple((x, x) for x in self.CLASSES)),
            self._filter_row("area", "地区", (("全部", ""),) + tuple((x, x) for x in self.AREAS)),
            self._filter_row("year", "年份", (("全部", ""),) + tuple((x, x) for x in self.YEARS)),
        ]
        return {
            "class": classes,
            "filters": dict((item[0], common) for item in self.CATEGORY_SPECS),
        }

    def homeVideoContent(self):
        try:
            source, page_url = self._request_text(
                "/", markers=("/movie/", "/tv/")
            )
            result = self._parse_list_page(source, 1, page_url)
            return {"list": result.get("list", []), "msg": result.get("msg", "")}
        except Exception as exc:
            return {"list": [], "msg": "首页读取失败: %s" % exc}

    def categoryContent(self, tid, pg, filter, extend):
        page = self._page_number(pg)
        base_path = self.CATEGORY_PATHS.get(str(tid or ""))
        if not base_path:
            return self._empty_page(page, "未知分类")
        if page > 1:
            return self._empty_page(
                page, "站点 robots.txt 禁止 page 查询，已停止自动翻页"
            )
        values = self._parse_dict(extend)
        query = {}
        for key in ("sort_field", "class", "area", "year"):
            value = self._safe_filter_value(values.get(key))
            if value:
                query[key] = value
        path = base_path
        if query:
            path += "?" + urlencode(query)
        try:
            source, page_url = self._request_text(
                path, markers=("/movie/", "/tv/")
            )
            return self._parse_list_page(source, page, page_url)
        except Exception as exc:
            return self._empty_page(page, "分类读取失败: %s" % exc)

    def searchContent(self, key, quick, pg="1"):
        page = self._page_number(pg)
        return self._empty_page(
            page, "站点 robots.txt 禁止 name 查询，未发送搜索请求"
        )

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        path = self._normalize_detail_id(raw_id)
        if not path:
            return {"list": [self._detail_error(str(raw_id or ""), "无效详情 ID")]}
        try:
            source, page_url = self._request_text(
                path, markers=("episode-button", "<h1")
            )
            return {"list": [self._parse_detail_page(source, path, page_url)]}
        except Exception as exc:
            return {"list": [self._detail_error(path, "详情读取失败: %s" % exc)]}

    def playerContent(self, flag, id, vipFlags):
        value = str(id or "").strip()
        if value.startswith(self.ERROR_PREFIX):
            return self._player_error(value[len(self.ERROR_PREFIX) :])
        magnet = self._unpack_magnet(value)
        if magnet:
            return {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": "push://" + magnet,
                "header": {},
            }
        if value.startswith(("http://", "https://")):
            if self._is_allowed_media_url(value):
                return self._player_result(value, self._active_host + "/")
            return self._player_error("播放地址不安全")
        play_path = self._unpack_play_path(value)
        if not play_path:
            return self._player_error("无法识别播放 ID")
        try:
            source, page_url = self._request_text(
                play_path,
                markers=("xg_video_player_doc",),
                fresh=True,
            )
            payload = self._extract_player_payload(source)
            media_value = str(payload.get("url") or "").strip()
            media_url = urljoin(page_url, media_value)
            if not self._is_allowed_media_url(media_url):
                raise RuntimeError("页面未返回安全的媒体地址")
            return self._player_result(media_url, page_url)
        except Exception as exc:
            return self._player_error("播放解析失败: %s" % exc)

    def _reset_session(self):
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        session = requests.Session()
        session.trust_env = self.trust_env
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
            }
        )
        self._session = session

    def _request_text(self, path, markers=(), fresh=False):
        url = self._business_url(path)
        cache_key = url
        if not fresh and self.cache_ttl > 0:
            cached = self._cache.get(cache_key)
            if cached and time.time() - cached[0] <= self.cache_ttl:
                return cached[1], cached[2]
        first_error = None
        try:
            return self._fetch_business(url, markers, cache_key, fresh)
        except Exception as exc:
            first_error = exc
        previous = self._active_host
        discovered = self._discover_business_host()
        if discovered and discovered != previous:
            url = urljoin(discovered + "/", str(path or "").lstrip("/"))
            return self._fetch_business(url, markers, url, fresh)
        raise first_error

    def _fetch_business(self, url, markers, cache_key, fresh):
        response = self._session.get(
            url,
            timeout=(min(self.timeout, 10), self.timeout),
            allow_redirects=True,
            verify=self.verify_tls,
        )
        final_url = str(response.url or url)
        final_origin = self._safe_origin(final_url)
        if not final_origin or final_origin != self._active_host:
            raise RuntimeError("已阻止外域跳转")
        source = self._response_text(response)
        if self._looks_like_challenge(response.status_code, source):
            raise RuntimeError("站点返回了浏览器验证页")
        response.raise_for_status()
        if markers and not any(marker in source for marker in markers):
            raise RuntimeError("页面缺少业务标记")
        if not fresh and self.cache_ttl > 0:
            self._cache[cache_key] = (time.time(), source, final_url)
        return source, final_url

    def _discover_business_host(self):
        if self._discovery_checked:
            return self._active_host
        self._discovery_checked = True
        try:
            url = self.discovery_host + "/hosts.html?host=" + quote(
                urlsplit(self.discovery_host).hostname or "", safe=""
            )
            response = self._session.get(
                url,
                timeout=(min(self.timeout, 10), self.timeout),
                allow_redirects=True,
                verify=self.verify_tls,
            )
            final_origin = self._safe_origin(str(response.url or url))
            if final_origin != self.discovery_host:
                return self._active_host
            source = self._response_text(response)
            response.raise_for_status()
            for candidate in re.findall(r"https?://[A-Za-z0-9.-]+(?::\d+)?/?", source):
                origin = self._safe_origin(candidate)
                if origin and origin != self.discovery_host:
                    self._active_host = origin
                    self._cache.clear()
                    return origin
        except Exception:
            pass
        return self._active_host

    def _parse_list_page(self, source, page, page_url):
        tree = self._tree(source)
        cards = tree.xpath(
            '//a[(contains(@href,"/movie/") or contains(@href,"/tv/")) and .//img]'
            '/parent::div[contains(@class,"flex-col")]'
        )
        videos = []
        seen = set()
        for card in cards:
            href = card.xpath(
                'string(.//a[(contains(@href,"/movie/") or contains(@href,"/tv/")) and .//img][1]/@href)'
            ).strip()
            path = self._normalize_detail_id(href)
            if not path or path in seen:
                continue
            seen.add(path)
            title = self._clean_text(card.xpath("string(.//h3//a[1])"))
            image = card.xpath(
                'string(.//a[(contains(@href,"/movie/") or contains(@href,"/tv/")) and .//img][1]//img[1]/@data-src)'
            ).strip()
            if not image:
                image = card.xpath(
                    'string(.//a[(contains(@href,"/movie/") or contains(@href,"/tv/")) and .//img][1]//img[1]/@src)'
                ).strip()
            if not title:
                title = self._clean_text(card.xpath("string(.//img[1]/@alt)"))
            remark = self._clean_text(
                card.xpath(
                    'string(.//a[(contains(@href,"/movie/") or contains(@href,"/tv/")) and .//img][1]//span[1])'
                )
            )
            footer = [
                self._clean_text(value)
                for value in card.xpath('.//div[contains(@class,"mt-auto")]//*[self::div or self::span]/text()')
            ]
            footer = [value for value in footer if value]
            if footer:
                suffix = " ".join(footer[:2])
                remark = (remark + " " + suffix).strip()
            videos.append(
                {
                    "vod_id": path,
                    "vod_name": title or path,
                    "vod_pic": urljoin(page_url, image) if image else self.DEFAULT_PIC,
                    "vod_remarks": remark,
                }
            )
        page_indexes = [int(value) for value in self.PAGE_RE.findall(source)]
        pagecount = max(page_indexes) + 1 if page_indexes else page
        pagecount = max(pagecount, page)
        limit = len(videos) or 24
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": pagecount * limit,
        }

    def _parse_detail_page(self, source, path, page_url):
        tree = self._tree(source)
        name = self._clean_text(tree.xpath("string(//h1[1])")) or path
        pic = tree.xpath('string(//img[contains(@src,"/img/id/")][1]/@src)').strip()
        year_text = self._clean_text(tree.xpath("string(//h1[1]/parent::*)"))
        year_match = re.search(r"\((\d{4})\)", year_text)
        content = self._clean_text(
            tree.xpath(
                'string(//h3[normalize-space(.)="简介"]/following-sibling::div[1])'
            )
        )
        panel = tree.xpath('//h1[1]/ancestor::div[contains(@class,"flex-1")][1]')
        scope = panel[0] if panel else tree
        classes = self._unique_text(scope.xpath('.//a[contains(@href,"class=")]/text()'))
        areas = self._unique_text(scope.xpath('.//a[contains(@href,"area=")]/text()'))
        actors = self._unique_text(scope.xpath('.//a[contains(@href,"actor=")]/text()'))
        kind = self._clean_text(
            scope.xpath(
                'string(.//a[@href="/dianying.html" or @href="/dianshiju.html" or @href="/zongyi.html" or @href="/dongman.html" or @href="/duanju.html"][1])'
            )
        )
        remark = self._clean_text(
            tree.xpath(
                'string(//img[contains(@src,"/img/id/")][1]/following-sibling::div[1])'
            )
        )

        play_from = []
        play_urls = []
        source_groups = []
        for source_index, group in enumerate(
            tree.xpath('//div[starts-with(@id,"list-")]')
        ):
            origin = str(group.get("id") or "")[5:]
            if not origin:
                continue
            episodes = []
            for anchor in group.xpath('.//a[contains(@class,"episode-button")]'):
                label = self._safe_play_label(self._clean_text(anchor.text_content()))
                href = str(anchor.get("href") or "").strip()
                if not label or not self._valid_play_path(href):
                    continue
                episodes.append(label + "$" + self._pack_play_path(href))
            if not episodes:
                continue
            source_name = self.SOURCE_NAMES.get(origin, origin)
            source_groups.append(
                (
                    self.SOURCE_PRIORITY.get(origin, 100),
                    source_index,
                    source_name,
                    "#".join(episodes),
                )
            )
        for _, _, source_name, episodes in sorted(source_groups):
            play_from.append(source_name)
            play_urls.append(episodes)
        magnets = self._extract_magnets(source)
        if magnets:
            magnet_items = []
            for item in magnets:
                magnet_items.append(
                    self._safe_play_label(item["label"])
                    + "$"
                    + self._pack_magnet(item["magnet"])
                )
            play_from.append("磁力")
            play_urls.append("#".join(magnet_items))
        if not play_urls:
            play_from = ["提示"]
            play_urls = ["暂无可用线路$" + self.ERROR_PREFIX + quote("详情页没有选集", safe="")]

        return {
            "vod_id": path,
            "vod_name": name,
            "vod_pic": urljoin(page_url, pic) if pic else self.DEFAULT_PIC,
            "vod_remarks": remark,
            "vod_year": year_match.group(1) if year_match else "",
            "vod_area": ",".join(areas),
            "vod_actor": ",".join(actors),
            "vod_director": "",
            "vod_class": ",".join(([kind] if kind else []) + classes),
            "vod_content": content,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_urls),
        }

    def _extract_player_payload(self, source):
        match = self.PLAYER_DATA_RE.search(source)
        if match:
            escaped = match.group(1).replace('"', '\\"')
            decoded = json.loads('"' + escaped + '"')
            payload = json.loads(decoded)
            if isinstance(payload, dict):
                return payload
        normalized = source.replace("\\/", "/")
        match = re.search(
            r'["\']url["\']\s*:\s*["\'](https?://[^"\']+)["\']',
            normalized,
            re.I,
        )
        if match:
            return {"url": match.group(1)}
        raise RuntimeError("未找到播放器 aa 数据")

    def _pack_play_path(self, path):
        token = base64.urlsafe_b64encode(path.encode("utf-8")).decode("ascii")
        return self.PLAY_PREFIX + token.rstrip("=")

    def _pack_magnet(self, magnet):
        token = base64.urlsafe_b64encode(magnet.encode("utf-8")).decode("ascii")
        return self.MAGNET_PREFIX + token.rstrip("=")

    def _unpack_magnet(self, value):
        if not value.startswith(self.MAGNET_PREFIX):
            return ""
        token = value[len(self.MAGNET_PREFIX) :]
        try:
            token += "=" * ((4 - len(token) % 4) % 4)
            magnet = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        except Exception:
            return ""
        return self._normalize_magnet(magnet)

    def _unpack_play_path(self, value):
        if not value.startswith(self.PLAY_PREFIX):
            return ""
        token = value[len(self.PLAY_PREFIX) :]
        try:
            token += "=" * ((4 - len(token) % 4) % 4)
            path = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        except Exception:
            return ""
        return path if self._valid_play_path(path) else ""

    def _valid_play_path(self, value):
        parsed = urlsplit(str(value or ""))
        if parsed.scheme or parsed.netloc or not self.DETAIL_PATH_RE.match(parsed.path):
            return False
        query = parse_qs(parsed.query)
        origin = str((query.get("origin") or [""])[0])
        episode = str((query.get("p") or [""])[0])
        return bool(re.match(r"^[A-Za-z0-9]+$", origin) and episode.isdigit())

    def _extract_magnets(self, source):
        tree = self._tree(source)
        raw_items = []
        nodes = tree.xpath(
            '//a[starts-with(@href,"magnet:")]'
            ' | //*[@data-magnet]'
            ' | //*[@data-url and starts-with(@data-url,"magnet:")]'
            ' | //*[@data-href and starts-with(@data-href,"magnet:")]'
        )
        for node in nodes:
            magnet = (
                node.get("href")
                or node.get("data-magnet")
                or node.get("data-url")
                or node.get("data-href")
                or ""
            )
            raw_items.append((self._clean_text(node.text_content()), magnet))

        normalized_source = html_lib.unescape(str(source or ""))
        normalized_source = normalized_source.replace("\\/", "/")
        normalized_source = normalized_source.replace("\\u003f", "?")
        normalized_source = normalized_source.replace("\\u0026", "&")
        for magnet in re.findall(r"magnet:\?[^\"'<>\s]+", normalized_source, re.I):
            raw_items.append(("", magnet))

        items = []
        seen = set()
        for index, (label, raw_magnet) in enumerate(raw_items):
            magnet = self._normalize_magnet(raw_magnet)
            btih = self._extract_btih(magnet)
            if not magnet or not btih or btih in seen:
                continue
            seen.add(btih)
            clean_label = self._safe_play_label(label)
            if not clean_label or clean_label.lower().startswith("magnet:?"):
                query = parse_qs(urlsplit(magnet).query)
                clean_label = self._safe_play_label(
                    unquote_plus(str((query.get("dn") or [""])[0]))
                )
            if not clean_label:
                clean_label = "磁力资源 %d" % (len(items) + 1)
            items.append(
                {
                    "label": clean_label,
                    "magnet": magnet,
                    "quality": self._magnet_quality(clean_label),
                    "source_index": index,
                }
            )
        return sorted(
            items,
            key=lambda item: (-item["quality"], item["source_index"]),
        )

    def _normalize_magnet(self, value):
        text = html_lib.unescape(str(value or "")).strip().strip("\"'")
        match = re.search(r"magnet:\?[^\"'<>\s]+", text, re.I)
        if match:
            text = match.group(0)
        btih = self._extract_btih(text)
        if not btih:
            return ""
        if text.lower().startswith("magnet:?"):
            return text
        return "magnet:?xt=urn:btih:" + btih

    def _extract_btih(self, value):
        text = str(value or "")
        match = self.BTIH_RE.search(text)
        if match:
            return match.group(1).upper()
        stripped = text.strip()
        if re.match(r"^(?:[A-F0-9]{40}|[A-Z2-7]{32})$", stripped, re.I):
            return stripped.upper()
        return ""

    def _magnet_quality(self, label):
        text = str(label or "").upper()
        patterns = (
            (4320, r"(?:^|\D)(?:4320P|8K)(?:\D|$)"),
            (2160, r"(?:^|\D)(?:2160P|4K|UHD)(?:\D|$)"),
            (1440, r"(?:^|\D)(?:1440P|2K)(?:\D|$)"),
            (1080, r"(?:^|\D)(?:1080[PI]?|FHD)(?:\D|$)"),
            (720, r"(?:^|\D)(?:720[PI]?|HD)(?:\D|$)"),
            (480, r"(?:^|\D)480[PI]?(?:\D|$)"),
            (360, r"(?:^|\D)360[PI]?(?:\D|$)"),
        )
        for quality, pattern in patterns:
            if re.search(pattern, text):
                return quality
        return 0

    def _normalize_detail_id(self, value):
        text = str(value or "").strip()
        if text.startswith("atvp_detail:"):
            text = text[len("atvp_detail:") :]
        parsed = urlsplit(text)
        if parsed.scheme or parsed.netloc:
            if self._safe_origin(text) != self._active_host:
                return ""
            text = parsed.path
        else:
            text = parsed.path
        if not text.startswith("/"):
            text = "/" + text
        return text if self.DETAIL_PATH_RE.match(text) else ""

    def _business_url(self, path):
        text = str(path or "").strip()
        parsed = urlsplit(text)
        if parsed.scheme or parsed.netloc:
            if self._safe_origin(text) != self._active_host:
                raise RuntimeError("已阻止非业务域名")
            return text
        return urljoin(self._active_host + "/", text.lstrip("/"))

    def _response_text(self, response):
        body = bytes(response.content or b"")
        return body.decode("utf-8", errors="replace")

    def _tree(self, source):
        return html.fromstring(source or "<html></html>")

    def _looks_like_challenge(self, status, source):
        lowered = str(source or "").lower()
        return status in (403, 429, 503) and any(
            marker in lowered for marker in self.CHALLENGE_MARKERS
        )

    def _is_allowed_media_url(self, value):
        parsed = urlsplit(str(value or "").strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower()
        if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
        except ValueError:
            pass
        return True

    def _safe_origin(self, value):
        parsed = urlsplit(str(value or "").strip())
        if parsed.scheme != "https" or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith(".local"):
            return ""
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return ""
        except ValueError:
            pass
        port = (":" + str(parsed.port)) if parsed.port and parsed.port != 443 else ""
        return "https://" + host + port

    def _player_result(self, url, referer):
        header = {"User-Agent": self.user_agent}
        if referer:
            header["Referer"] = referer
        return {
            "parse": 0,
            "jx": 0,
            "playUrl": "",
            "url": url,
            "header": header,
        }

    def _player_error(self, message):
        text = self._clean_text(message) or "未知播放错误"
        return {
            "parse": 0,
            "jx": 0,
            "playUrl": "",
            "url": "",
            "header": {},
            "msg": text,
            "error": text,
            "content": text,
        }

    def _detail_error(self, vod_id, message):
        text = self._clean_text(message)
        return {
            "vod_id": vod_id or "douhua-error",
            "vod_name": "豆花影视解析提示",
            "vod_pic": self.DEFAULT_PIC,
            "vod_remarks": text,
            "vod_content": text,
            "vod_play_from": "提示",
            "vod_play_url": "查看提示$" + self.ERROR_PREFIX + quote(text, safe=""),
        }

    def _empty_page(self, page, message=""):
        result = {
            "list": [],
            "page": page,
            "pagecount": page,
            "limit": 24,
            "total": 0,
        }
        if message:
            result["msg"] = message
        return result

    def _filter_row(self, key, name, values):
        return {
            "key": key,
            "name": name,
            "value": [{"n": label, "v": value} for label, value in values],
        }

    def _parse_dict(self, value):
        if isinstance(value, dict):
            return dict(value)
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _page_number(self, value):
        try:
            return max(1, int(str(value or "1")))
        except Exception:
            return 1

    def _bounded_int(self, value, default, minimum, maximum):
        try:
            return max(minimum, min(maximum, int(value)))
        except Exception:
            return default

    def _bool_value(self, value, default):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
        return default

    def _safe_filter_value(self, value):
        text = self._clean_text(value)
        if not text or len(text) > 40 or any(char in text for char in "&#$\r\n"):
            return ""
        return text

    def _safe_play_label(self, value):
        return self._clean_text(value).replace("#", " ").replace("$", " ")

    def _clean_text(self, value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _unique_text(self, values):
        result = []
        for value in values:
            text = self._clean_text(value)
            if text and text not in result:
                result.append(text)
        return result

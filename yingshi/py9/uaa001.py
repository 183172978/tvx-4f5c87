#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════════
  UAA001 (UAA.COM) 爬虫源 —— 基于 API 接口
  站点: https://www.uaa001.com / https://www.uaa.com
  API: https://api.march24168.online
  CDN: https://cdn.uameta.ai/file/bucket-media
  类型: 视频 (m3u8/mp4)
  框架: dr_py / py-drpy
  生成: 2026-08-11
══════════════════════════════════════════════════════════════════
  【使用说明】
  1. 放入 TVBox/影视仓 的 spiders/ 目录
  2. index.json 添加: {"key":"uaa001","name":"UAA001","type":3,"api":"uaa001.py"}
  3. 依赖: pip install requests
  4. 账号: 内置测试账号，可通过 extend 参数覆盖
══════════════════════════════════════════════════════════════════
"""

import json
import sys
import time

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    requests = None

# ═════════════════════════════════════════════════════════════
# 常量配置
# ═════════════════════════════════════════════════════════════
_API_URL = "https://api.march24168.online"
_CDN_URL = "https://cdn.uameta.ai/file/bucket-media"
_UA = "Dart/3.11 (dart:io)"

# 内置授权账号（可通过 extend JSON 覆盖）
_DEFAULT_LOGIN = "285886751@qq.com"
_DEFAULT_PASSWORD = "qwer4321"

# 片商列表 (名称, API参数值)
_AUTHORS = (
    ("FC2", "FC2"),
    ("MOODYZ", "MOODYZ(Moody's)"),
    ("S1", "S1 No. 1 Style"),
    ("加勒比", "加勒比"),
    ("一本道", "一本道"),
    ("麻豆传媒", "麻豆传媒"),
)

# 来源分类 (名称, origin参数值, 对应HTML中的 origin 筛选)
_ORIGINS = (
    ("国产视频", "1"),
    ("日本AV", "2"),
    ("H动漫", "3"),
    ("正规", "4"),
    ("欧美", "5"),
)


class Spider(BaseSpider):
    """
    UAA001 视频站爬虫
    基于官方 App API，支持分类/片商/搜索/播放
    """

    name = "UAA001"
    base_url = _API_URL
    site_url = "https://www.uaa001.com"

    # 首页分类：来源 + 片商
    class_name = [n for n, _ in _ORIGINS] + [n for n, _ in _AUTHORS]
    class_url = ["origin:" + v for _, v in _ORIGINS] + ["author:" + str(i) for i in range(len(_AUTHORS))]

    def __init__(self):
        super().__init__()
        self.session = requests.Session() if requests else None
        if self.session:
            self.session.headers.update({"user-agent": _UA, "accept-encoding": "gzip"})
        self.token = ""
        self.items = {}          # categoryContent 缓存，供 detailContent 使用
        self._login_name = _DEFAULT_LOGIN
        self._password = _DEFAULT_PASSWORD

    def init(self, extend=""):
        """初始化，支持通过 extend JSON 覆盖账号"""
        if extend:
            try:
                cfg = json.loads(extend)
                self._login_name = cfg.get("loginName", self._login_name)
                self._password = cfg.get("password", self._password)
            except Exception:
                pass
        # 预登录
        self._login()

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    # ═════════════════════════════════════════════════════════════
    # 登录
    # ═════════════════════════════════════════════════════════════
    def _login(self):
        """获取 Token，失败返回 False"""
        if self.token:
            return True
        if not self.session:
            return False
        try:
            resp = self.session.post(
                f"{_API_URL}/console/app/login",
                params={
                    "loginName": self._login_name,
                    "password": self._password,
                    "platform": "app"
                },
                timeout=25,
            )
            data = resp.json()
            if data.get("code") == 0:
                model = data.get("model") or {}
                self.token = model.get("token", "")
                return bool(self.token)
        except Exception as exc:
            print(f"[UAA001] 登录失败: {exc}")
        return False

    # ═════════════════════════════════════════════════════════════
    # API 请求封装
    # ═════════════════════════════════════════════════════════════
    def _request(self, path, params=None, retries=2):
        """带 Token 的 GET 请求，自动处理 Token 过期"""
        if not self.session:
            return None
        for attempt in range(retries):
            if not self._login():
                return None
            try:
                resp = self.session.get(
                    f"{_API_URL}{path}",
                    params=params or {},
                    headers={"token": self.token},
                    timeout=25,
                )
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("model") or {}
                # Token 失效，清空重试
                if resp.status_code in (401, 403):
                    self.token = ""
                    continue
                return None
            except Exception as exc:
                print(f"[UAA001] 请求异常: {exc}")
                if attempt < retries - 1:
                    time.sleep(1)
        return None

    # ═════════════════════════════════════════════════════════════
    # 数据构造
    # ═════════════════════════════════════════════════════════════
    @staticmethod
    def _cover(item):
        """封面图URL处理"""
        cover = item.get("coverUrl") or item.get("cover") or ""
        if cover.startswith("http"):
            return cover
        if cover.startswith("/"):
            return f"{_CDN_URL}{cover}"
        return cover

    def _build_item(self, item):
        """构造列表/详情通用字段"""
        return {
            "vod_id": str(item.get("id", "")),
            "vod_name": item.get("title") or item.get("number") or "未命名",
            "vod_pic": self._cover(item),
            "vod_remarks": item.get("categories") or item.get("tags") or "",
            "vod_year": "",
            "vod_area": "",
            "vod_actor": item.get("actress") or item.get("authors") or "",
            "vod_director": "",
            "vod_type": item.get("categories") or "",
            "vod_score": "",
        }

    # ═════════════════════════════════════════════════════════════
    # 首页推荐
    # ═════════════════════════════════════════════════════════════
    def homeContent(self, filter=False):
        """返回分类列表"""
        classes = []
        # 来源分类
        for name, tid in zip(self.class_name, self.class_url):
            classes.append({"type_name": name, "type_id": tid})
        return {"class": classes}

    def homeVideoContent(self):
        """首页推荐视频（取默认列表第一页）"""
        return self.categoryContent("origin:1", 1)

    # ═════════════════════════════════════════════════════════════
    # 分类列表
    # ═════════════════════════════════════════════════════════════
    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        """
        tid 格式:
          - origin:N  → 按来源筛选 (1=国产, 2=日本AV, 3=H动漫, 4=正规, 5=欧美)
          - author:N  → 按片商筛选 (索引对应 _AUTHORS)
          - video     → 默认全部
        """
        page = max(1, int(pg) if pg else 1)
        params = {
            "orderType": 2,   # 默认排序
            "page": page,
            "size": 50,
        }

        tid_str = str(tid)
        if tid_str.startswith("author:"):
            try:
                idx = int(tid_str.split(":", 1)[1])
                author_val = _AUTHORS[idx][1]
            except (IndexError, ValueError):
                return {"list": [], "page": page, "pagecount": 1, "limit": 50, "total": 0}
            params.update({"searchType": 2, "author": author_val})

        elif tid_str.startswith("origin:"):
            origin_val = tid_str.split(":", 1)[1]
            params.update({"origin": origin_val})

        else:
            # 默认全部视频
            pass

        model = self._request("/video/app/video/search", params)
        if not model:
            return {"list": [], "page": page, "pagecount": 1, "limit": 50, "total": 0}

        data = model.get("data") or []
        # 缓存到 items，供 detailContent 使用
        for item in data:
            vid = str(item.get("id", ""))
            if vid:
                self.items[vid] = item

        return {
            "list": [self._build_item(item) for item in data],
            "page": model.get("currentPage", page),
            "pagecount": model.get("totalPage", 1),
            "limit": model.get("pageSize", 50),
            "total": model.get("totalCount", 0),
        }

    # ═════════════════════════════════════════════════════════════
    # 详情页
    # ═════════════════════════════════════════════════════════════
    def detailContent(self, ids):
        """
        优先从 categoryContent 缓存读取；
        缓存未命中时尝试通过搜索接口反查（兜底）
        """
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}

        item = self.items.get(vid)

        # 兜底：尝试通过搜索接口用 id 反查（部分 API 支持）
        if not item:
            try:
                fallback = self._request("/video/app/video/search", {
                    "keyword": vid,
                    "page": 1,
                    "size": 10,
                })
                if fallback:
                    for it in fallback.get("data", []):
                        if str(it.get("id", "")) == vid:
                            item = it
                            self.items[vid] = item
                            break
            except Exception:
                pass

        if not item:
            return {"list": []}

        url = item.get("url") or ""
        vod = self._build_item(item)
        vod.update({
            "vod_content": item.get("brief") or item.get("description") or "",
            "vod_actor": item.get("actress") or item.get("authors") or "",
            "vod_play_from": "官方线路",
            "vod_play_url": f"播放${url}" if url else "",
        })
        return {"list": [vod]}

    # ═════════════════════════════════════════════════════════════
    # 搜索
    # ═════════════════════════════════════════════════════════════
    def searchContent(self, key, quick=False, pg=1):
        """关键词搜索"""
        page = max(1, int(pg) if pg else 1)
        params = {
            "keyword": key,
            "page": page,
            "size": 50,
            "orderType": 2,
        }
        model = self._request("/video/app/video/search", params)
        if not model:
            return {"list": [], "page": page, "pagecount": 1, "limit": 50, "total": 0}

        data = model.get("data") or []
        for item in data:
            vid = str(item.get("id", ""))
            if vid:
                self.items[vid] = item

        return {
            "list": [self._build_item(item) for item in data],
            "page": model.get("currentPage", page),
            "pagecount": model.get("totalPage", 1),
            "limit": model.get("pageSize", 50),
            "total": model.get("totalCount", 0),
        }

    # ═════════════════════════════════════════════════════════════
    # 播放解析
    # ═════════════════════════════════════════════════════════════
    def playerContent(self, flag, id, vipFlags=None):
        """
        直接返回播放地址（API返回的已是直链或解析后地址）
        flag: 线路名（如"官方线路"）
        id: 播放地址（$分隔后的url部分）
        """
        if not id:
            return {"parse": 1, "url": "", "header": ""}

        # 如果是直链格式
        if self.isVideoFormat(id):
            return {
                "parse": 0,
                "url": id,
                "header": json.dumps({"user-agent": _UA, "referer": "https://www.uaa001.com/"}),
            }

        # 其他情况直接透传（可能为第三方解析页，需 TVBox 二次解析）
        return {
            "parse": 1,
            "url": id,
            "header": json.dumps({"user-agent": _UA}),
        }

    # ═════════════════════════════════════════════════════════════
    # 本地代理（图片防盗链等）
    # ═════════════════════════════════════════════════════════════
    def localProxy(self, param):
        """本地代理，用于图片/CDN资源"""
        EMPTY_GIF = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
            b"\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00"
            b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        if not param or not param.startswith("http"):
            return [200, "image/gif", EMPTY_GIF]
        try:
            r = self.session.get(param, headers={"user-agent": _UA}, timeout=15)
            return [
                200,
                r.headers.get("Content-Type", "application/octet-stream"),
                r.content,
            ]
        except Exception:
            return [200, "image/gif", EMPTY_GIF]


# TVBox 标准入口
class UAA001Spider(Spider):
    pass


if __name__ == "__main__":
    spider = Spider()
    print(f"[UAA001] {spider.getName()} 已加载")
    print(f"[UAA001] 分类数: {len(spider.class_name)}")
    print(f"[UAA001] 请运行 TVBox/影视仓 进行测试")

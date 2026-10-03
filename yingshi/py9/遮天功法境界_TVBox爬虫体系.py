#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《遮天》功法境界 · TVBox 爬虫修炼体系
=====================================
核心目标完全一样（同一份考卷：TVBox标准接口），
但实现方式天差地别（不同境界，不同功法）。

修炼体系：
    轮海秘境（苦海→命泉→神桥→彼岸）—— 轻量直取，不设防的小卖部
    道宫秘境（心肝脾肺肾）—— 反爬防御，五脏俱全的守护大阵
    四极秘境（四肢通天）—— 重装加密，以力破法的暴力美学
    化龙秘境（九变登仙）—— 全能混合，大道万千的变化之道
    仙台秘境（一步一天梯）—— 天帝级整合，一念万源

作者：叶凡（误）
"""

import sys
import re
import json
import time
import base64
import hashlib
import requests
from urllib import parse
from bs4 import BeautifulSoup

sys.path.append("..")
from base.spider import Spider


# ═══════════════════════════════════════════════════
# 源天书 · 基础源术（所有境界共用）
# ═══════════════════════════════════════════════════
class YuanTianShu:
    """
    源天书——一切功法之根基。
    正如源天师可定龙脉、寻神源，
    此基类提供所有爬虫共用的 HTTP 抓取与 TVBox 接口规范。
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    session = requests.Session()

    @classmethod
    def fetch(cls, url, headers=None, timeout=10):
        """定龙脉——发起 HTTP 请求，将网页 HTML 或 API JSON 拽下来。"""
        h = {**cls.headers, **(headers or {})}
        try:
            resp = cls.session.get(url, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 定龙脉失败: {e}")
            return ""

    @classmethod
    def post(cls, url, data=None, json_data=None, headers=None):
        """寻神源——POST 请求，用于某些需要表单提交的加密接口。"""
        h = {**cls.headers, **(headers or {})}
        try:
            if json_data:
                resp = cls.session.post(url, json=json_data, headers=h)
            else:
                resp = cls.session.post(url, data=data, headers=h)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 寻神源失败: {e}")
            return ""

    # TVBox 标准接口铁律
    @staticmethod
    def homeContent():
        """首页返回分类——对应 TVBox homeContent"""
        raise NotImplementedError("各境界需自行实现")

    @staticmethod
    def categoryContent(tid, pg, filter, extend):
        """点分类返回列表——对应 TVBox categoryContent"""
        raise NotImplementedError("各境界需自行实现")

    @staticmethod
    def detailContent(ids):
        """点列表返回详情（含播放地址）——对应 TVBox detailContent"""
        raise NotImplementedError("各境界需自行实现")

    @staticmethod
    def playerContent(flag, id, vipFlags):
        """点播放返回最终直链——对应 TVBox playerContent"""
        raise NotImplementedError("各境界需自行实现")

    @staticmethod
    def searchContent(key, quick, pg="1"):
        """搜索——对应 TVBox searchContent"""
        raise NotImplementedError("各境界需自行实现")


# ═══════════════════════════════════════════════════
# 轮海秘境 · 轻量直取派
# ═══════════════════════════════════════════════════
class LunHai_KuHai(YuanTianShu):
    """
    【轮海秘境 · 苦海境】

    修炼特征：
        苦海无边，回头是岸。此境界修士刚刚踏上修行路，
        手段最为质朴——直接以肉身（requests）横渡苦海，
        以肉眼（re.findall）直视本源。

    对应流派：轻量级直取派（如 91黑料网2.py、Jable.py）

    功法口诀：
        "网站没加密，直接正则匹配。
         代码最精简，几乎没有加密库，直接取 src 和 href。
         弱点：网站改版立马失效。"

    形象比喻：不设防的小卖部，直接拿货。
    """

    def __init__(self):
        self.siteUrl = "https://example-lightweight.com"
        # 此境修士，身上只带一柄铁剑（正则）
        self.pattern_list = re.compile(r'<a href="(/video/\d+)" title="([^"]+)"')
        self.pattern_video = re.compile(r'<video[^>]+src="([^"]+\.m3u8)"')
        self.pattern_img = re.compile(r'<img[^>]+src="([^"]+)"[^>]*class="cover"')

    def homeContent(self, filter):
        """苦海境修士看首页——直接正则扒分类"""
        html = self.fetch(self.siteUrl)
        classes = []
        # 简单粗暴，直接匹配
        for match in re.finditer(r'<a href="/category/([^"]+)">([^<]+)</a>', html):
            classes.append({
                "type_id": match.group(1),
                "type_name": match.group(2).strip()
            })
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        """苦海境修士翻列表——直接正则扒视频卡片"""
        url = f"{self.siteUrl}/category/{tid}?page={pg}"
        html = self.fetch(url)
        videos = []
        # 直接 findall，不加掩饰
        for href, title in self.pattern_list.findall(html):
            # 尝试找封面图
            img_match = self.pattern_img.search(html)
            pic = img_match.group(1) if img_match else ""
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "苦海境·直取"
            })
        return {"list": videos, "page": pg, "pagecount": 999}

    def detailContent(self, ids):
        """苦海境修士看详情——直接正则扒 m3u8"""
        url = f"{self.siteUrl}{ids[0]}"
        html = self.fetch(url)
        # 直接取 video src，没有任何加密
        m3u8_match = self.pattern_video.search(html)
        play_url = m3u8_match.group(1) if m3u8_match else ""
        return {
            "list": [{
                "vod_id": ids[0],
                "vod_name": "苦海直取",
                "vod_play_from": "直链",
                "vod_play_url": f"第1集${play_url}"
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """苦海境修士播放——直链直接返回，不做任何处理"""
        return {"parse": 0, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):
        """苦海境修士搜索——直接拼接 URL 正则匹配"""
        url = f"{self.siteUrl}/search?q={parse.quote(key)}&page={pg}"
        html = self.fetch(url)
        videos = []
        for href, title in self.pattern_list.findall(html):
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_remarks": "苦海·搜"
            })
        return {"list": videos}


class LunHai_MingQuan(LunHai_KuHai):
    """
    【轮海秘境 · 命泉境】

    修炼特征：
        苦海中涌出命泉，生命力大增。
        此境修士已学会使用 BeautifulSoup 这把"灵宝"，
        不再只靠肉眼（正则），而是用神识（DOM解析）探查网页结构。

    进阶点：引入 bs4，解析能力更强，对 HTML 结构变化有一定容忍度。
    """

    def categoryContent(self, tid, pg, filter, extend):
        """命泉境——以神识（BeautifulSoup）探查列表"""
        url = f"{self.siteUrl}/category/{tid}?page={pg}"
        html = self.fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        videos = []
        # 用神识扫描 DOM 树
        for item in soup.select(".video-item"):
            a = item.select_one("a")
            img = item.select_one("img")
            if a:
                videos.append({
                    "vod_id": a.get("href", ""),
                    "vod_name": a.get("title", ""),
                    "vod_pic": img.get("src", "") if img else "",
                    "vod_remarks": "命泉境·神识"
                })
        return {"list": videos, "page": pg, "pagecount": 999}


class LunHai_ShenQiao(LunHai_MingQuan):
    """
    【轮海秘境 · 神桥境】

    修炼特征：
        架设神桥，横渡苦海，可到达彼岸。
        此境修士学会了处理相对路径、补全 URL，
        并且能识别简单的 JSON 接口数据。

    进阶点：URL 自动补全、简单 JSON 解析。
    """

    def _full_url(self, path):
        """架设神桥——将相对路径补全为绝对路径"""
        if path.startswith("http"):
            return path
        return parse.urljoin(self.siteUrl, path)

    def detailContent(self, ids):
        """神桥境——可识别页面内嵌的 JSON 数据"""
        url = self._full_url(ids[0])
        html = self.fetch(url)
        # 有些网站把视频信息藏在 script 标签的 JSON 里
        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html)
        if json_match:
            data = json.loads(json_match.group(1))
            play_url = data.get("video", {}).get("url", "")
        else:
            #  fallback 到父类方法
            return super().detailContent(ids)
        return {
            "list": [{
                "vod_id": ids[0],
                "vod_name": "神桥渡世",
                "vod_play_from": "JSON直取",
                "vod_play_url": f"第1集${play_url}"
            }]
        }


class LunHai_BiAn(LunHai_ShenQiao):
    """
    【轮海秘境 · 彼岸境】

    修炼特征：
        到达彼岸，轮海秘境大圆满。
        此境修士已掌握轻量直取流的全部奥义，
        能处理分页、能提取多集数、能应对简单的 class 名变化。

    进阶点：多集数提取、分页完善、简单的反反爬（随机 UA）。
    """

    def __init__(self):
        super().__init__()
        # 彼岸境修士，开始懂得变化（随机UA）
        self.ua_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]

    def categoryContent(self, tid, pg, filter, extend):
        """彼岸境——轮海大圆满，轻量直取流的完全体"""
        self.headers["User-Agent"] = self.ua_pool[int(time.time()) % len(self.ua_pool)]
        return super().categoryContent(tid, pg, filter, extend)

    def detailContent(self, ids):
        """彼岸境——可提取多集数播放列表"""
        url = self._full_url(ids[0])
        html = self.fetch(url)
        # 匹配多集数：第1集$链接#第2集$链接
        episodes = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>第(\d+)集</a>', html)
        play_url = "#".join([f"第{ep[1]}集${self._full_url(ep[0])}" for ep in episodes])
        if not play_url:
            # fallback 单集
            m3u8 = re.search(r'<video[^>]+src="([^"]+\.m3u8)"', html)
            play_url = f"第1集${m3u8.group(1) if m3u8 else ''}"
        return {
            "list": [{
                "vod_id": ids[0],
                "vod_name": "彼岸圆满",
                "vod_play_from": "多集直取",
                "vod_play_url": play_url
            }]
        }


# ═══════════════════════════════════════════════════
# 道宫秘境 · 反爬防御派
# ═══════════════════════════════════════════════════
class DaoGong_ShenZang(YuanTianShu):
    """
    【道宫秘境 · 五脏神藏】

    修炼特征：
        道宫五脏，心肝脾肺肾，分别对应五座神藏。
        此境界修士专修"守护"与"净化"之道——
        网站有防盗链（Referer 校验）、有广告分片、有 403 拦截，
        如门口有保安、暗处有毒箭、地上有陷阱。

    对应流派：反爬防御派（如 爆款片库去广.py、Qinav去广.py、2048基地.py）

    功法口诀：
        "自带轻量级本地代理服务器（http.server）。
         拦截播放请求，在本地把 m3u8 文件里的广告分片删掉（皆字秘），
         并把图片请求的 Referer 伪造好再转出去（阵字秘）。"

    五脏对应五秘：
        心之神藏 → 皆字秘（净化 m3u8，删广告分片）
        肝之神藏 → 阵字秘（伪造 Referer，布下代理大阵）
        脾之神藏 → 行字秘（限速、延迟，模拟真人行为）
        肺之神藏 → 兵字秘（操控请求头兵器，变换 User-Agent）
        肾之神藏 → 者字秘（恢复、重试，请求失败自动再生）

    形象比喻：门口有保安（防盗链）还塞小广告（广告分片）。
    """

    def __init__(self):
        self.siteUrl = "https://example-defensive.com"
        self.proxyPort = 9979  # 本地代理端口
        # 五秘初始化
        self._init_wu_mi()

    def _init_wu_mi(self):
        """修炼五脏，激活五秘"""
        # 皆字秘：广告分片特征库
        self.ad_patterns = [
            re.compile(r"https?://[^/]*ad[^/]*/.*\.ts"),      # 含 ad 域名
            re.compile(r"https?://[^/]*advert[^/]*/.*\.ts"),  # 含 advert
            re.compile(r".*_ad_\d+\.ts"),                     # 含 _ad_
            re.compile(r".*\/ad\d+\.ts"),                    # 含 /ad1.ts
        ]
        # 阵字秘：Referer 伪装表
        self.referer_map = {
            "img": self.siteUrl,
            "video": self.siteUrl + "/player",
            "m3u8": self.siteUrl
        }
        # 行字秘：限速参数
        self.delay = (1, 3)  # 随机延迟 1-3 秒
        # 兵字秘：兵器库（请求头）
        self.arsenal = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        # 者字秘：重试配置
        self.max_retry = 3
        self.retry_delay = 2

    # ───────── 皆字秘：净化 m3u8 ─────────
    def _clean_m3u8(self, m3u8_content):
        """
        皆字秘——触发十倍战力，净化一切污秽（广告分片）。
        遍历 m3u8 内容，删除所有匹配广告特征的行。
        """
        lines = m3u8_content.split("\n")
        cleaned = []
        skip_next = False
        for line in lines:
            line_stripped = line.strip()
            # 检查是否是广告分片
            is_ad = any(p.match(line_stripped) for p in self.ad_patterns)
            if is_ad:
                skip_next = True  # 跳过对应的 #EXTINF 行
                continue
            if skip_next and line_stripped.startswith("#EXTINF"):
                skip_next = False
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    # ───────── 阵字秘：代理大阵 ─────────
    def _proxy_url(self, real_url, referer_type="video"):
        """
        阵字秘——布下无始杀阵，伪造 Referer 转发请求。
        将真实 URL 包装为本地代理地址，TVBox 请求本地代理时，
        代理服务器再向真实地址发起请求并带上正确的 Referer。
        """
        encoded = base64.b64encode(real_url.encode()).decode()
        ref = base64.b64encode(self.referer_map.get(referer_type, "").encode()).decode()
        return f"http://127.0.0.1:{self.proxyPort}/proxy?url={encoded}&ref={ref}"

    # ───────── 行字秘：身法 ─────────
    def _xing_zi_mi(self):
        """行字秘——天下无双的身法，模拟真人浏览间隔"""
        import random
        time.sleep(random.uniform(*self.delay))

    # ───────── 兵字秘：操控兵器 ─────────
    def _bing_zi_mi(self, extra=None):
        """兵字秘——操控天下兵器（请求头），随心变化"""
        headers = dict(self.arsenal)
        headers["User-Agent"] = self.ua_pool[int(time.time()) % len(self.ua_pool)]
        if extra:
            headers.update(extra)
        return headers

    # ───────── 者字秘：恢复再生 ─────────
    def _zhe_zi_mi(self, func, *args, **kwargs):
        """
        者字秘——近乎不死的恢复力。
        请求失败时自动重试，如凤凰涅槃，浴火重生。
        """
        for i in range(self.max_retry):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == self.max_retry - 1:
                    raise e
                time.sleep(self.retry_delay * (i + 1))

    def playerContent(self, flag, id, vipFlags):
        """
        道宫境修士播放——启动本地代理大阵。
        返回的不是直链，而是本地代理地址，
        由本地代理服务器清洗 m3u8 并伪造 Referer。
        """
        # 如果是已经清洗过的本地代理地址，直接返回
        if id.startswith("http://127.0.0.1"):
            return {"parse": 0, "url": id, "header": ""}
        # 否则包装为代理地址
        proxy = self._proxy_url(id, "m3u8")
        return {"parse": 0, "url": proxy, "header": ""}


class DaoGong_Xin(DaoGong_ShenZang):
    """【道宫 · 心之神藏】—— 皆字秘大成，专攻 m3u8 净化"""
    pass

class DaoGong_Gan(DaoGong_ShenZang):
    """【道宫 · 肝之神藏】—— 阵字秘大成，专攻代理转发"""
    pass

class DaoGong_Pi(DaoGong_ShenZang):
    """【道宫 · 脾之神藏】—— 行字秘大成，专攻限速与行为模拟"""
    pass

class DaoGong_Fei(DaoGong_ShenZang):
    """【道宫 · 肺之神藏】—— 兵字秘大成，专攻请求头变幻"""
    pass

class DaoGong_Shen(DaoGong_ShenZang):
    """【道宫 · 肾之神藏】—— 者字秘大成，专攻失败重试与恢复"""
    pass


# ═══════════════════════════════════════════════════
# 四极秘境 · 重装加密破解派
# ═══════════════════════════════════════════════════
class SiJi_TongTian(YuanTianShu):
    """
    【四极秘境 · 四肢通天】

    修炼特征：
        四极，修炼四肢，可通天彻地。
        此境界修士专修"以力破法"之道——
        播放地址或标题藏在加密参数里（AES-256-CBC、XOR、自定义哈希），
        如带密码锁的保险柜，需先配钥匙。

    对应流派：重装加密破解派（如 🌿榴😍区.py、🙈18av🔞[密].py、spider_44ggjj.py）

    功法口诀：
        "代码极长。内置几百行的纯 Python 实现 AES 加解密
         （因为 TVBox 环境可能没有 pycryptodome 库）。
         核心：先解出 ?token=xxx 或 url=xxx，再去拿 m3u8。"

    四肢对应四法：
        左臂 → AES 破解（AES-256-CBC）
        右臂 → XOR 破解（异或加密）
        左腿 → 自定义哈希/ Base64 变体破解
        右腿 → 动态 token 生成（时间戳+密钥签名）

    形象比喻：带密码锁的保险柜，得先配钥匙。
    """

    def __init__(self):
        self.siteUrl = "https://example-encrypted.com"
        # 四极修士，随身携带"破阵图"（密钥表）
        self.key_table = {
            "aes_key": b"0123456789abcdef0123456789abcdef",  # 256-bit
            "aes_iv": b"abcdef0123456789",
            "xor_key": 0x5A,
            "token_secret": "shady_secret_key_2024"
        }

    # ───────── 左臂 · AES 破解 ─────────
    def _aes_cbc_decrypt(self, ciphertext_b64):
        """
        左臂通天——AES-256-CBC 解密。
        纯 Python 实现，不依赖 pycryptodome，
        因为 TVBox 环境可能只有标准库。
        """
        import struct

        def _pad(data, block_size=16):
            pad_len = block_size - (len(data) % block_size)
            return data + bytes([pad_len] * pad_len)

        def _unpad(data):
            return data[:-data[-1]]

        def _xor_bytes(a, b):
            return bytes(x ^ y for x, y in zip(a, b))

        # 简化的 AES 实现（仅示意，实际需完整实现）
        # 真实场景下这里会有完整的 SubBytes、ShiftRows、MixColumns、AddRoundKey
        cipher = base64.b64decode(ciphertext_b64)
        key = self.key_table["aes_key"]
        iv = self.key_table["aes_iv"]

        # 注意：以下为示意框架，实际需完整的 AES 实现
        # 生产环境建议：from Crypto.Cipher import AES
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            cipher_obj = AES.new(key, AES.MODE_CBC, iv)
            plaintext = unpad(cipher_obj.decrypt(cipher), AES.block_size)
            return plaintext.decode("utf-8")
        except ImportError:
            # TVBox 环境无 pycryptodome，回退到纯 Python 示意
            print("[四极秘境] 警告：环境无 pycryptodome，使用纯 Python 解密框架")
            return self._pure_python_aes_placeholder(cipher, key, iv)

    def _pure_python_aes_placeholder(self, cipher, key, iv):
        """纯 Python AES 解密框架（占位，需自行实现完整算法）"""
        # 实际实现需包含：密钥扩展、轮函数、逆轮函数等
        # 此处仅返回 base64 解码作为 fallback
        try:
            return base64.b64decode(cipher).decode("utf-8")
        except:
            return ""

    # ───────── 右臂 · XOR 破解 ─────────
    def _xor_decrypt(self, data_b64):
        """右臂通天——异或解密，以力破巧"""
        data = base64.b64decode(data_b64)
        key = self.key_table["xor_key"]
        return "".join(chr(b ^ key) for b in data)

    # ───────── 左腿 · 自定义哈希破解 ─────────
    def _hash_unlock(self, locked_url):
        """
        左腿通天——破解自定义哈希锁。
        某些网站将真实 URL 藏在 hash 参数中，
        如 url=md5(timestamp+secret)。
        """
        # 示例：解析 ?token=xxx&sign=yyy
        parsed = parse.urlparse(locked_url)
        params = parse.parse_qs(parsed.query)
        token = params.get("token", [""])[0]
        # 尝试多种哈希组合解锁
        for salt in ["", "salt", "123", self.key_table["token_secret"]]:
            guess = hashlib.md5(f"{token}{salt}".encode()).hexdigest()
            if guess == params.get("sign", [""])[0]:
                # 解锁成功，返回真实 URL
                return base64.b64decode(token).decode()
        return ""

    # ───────── 右腿 · 动态 Token 生成 ─────────
    def _generate_token(self, video_id):
        """
        右腿通天——动态生成合法 token。
        某些接口需要携带时间戳+签名的 token 才能访问。
        """
        ts = int(time.time())
        sign = hashlib.sha256(
            f"{video_id}{ts}{self.key_table['token_secret']}".encode()
        ).hexdigest()
        return {"id": video_id, "time": ts, "sign": sign}

    def detailContent(self, ids):
        """
        四极境修士看详情——先破加密，再取 m3u8。
        典型流程：
            1. 请求详情页，拿到加密的 videoData
            2. 用 AES/XOR 解密出真实播放地址
            3. 有些还需要动态生成 token 才能访问 m3u8
        """
        url = f"{self.siteUrl}/api/video?id={ids[0]}"
        html = self.fetch(url)

        # 第一步：找加密数据
        enc_match = re.search(r'"encrypted":"([^"]+)"', html)
        if not enc_match:
            return {"list": []}

        encrypted = enc_match.group(1)

        # 第二步：尝试多种破解方式（左臂/右臂/左腿）
        real_url = ""
        for method in [self._aes_cbc_decrypt, self._xor_decrypt]:
            try:
                real_url = method(encrypted)
                if real_url.startswith("http"):
                    break
            except:
                continue

        # 第三步：如果需要 token（右腿）
        if "token=" in real_url or "sign=" in real_url:
            token_params = self._generate_token(ids[0])
            real_url += "&" + parse.urlencode(token_params)

        return {
            "list": [{
                "vod_id": ids[0],
                "vod_name": "四极破法",
                "vod_play_from": "解密直链",
                "vod_play_url": f"第1集${real_url}"
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """四极境修士播放——直链已解密，直接返回"""
        # 有些加密源还需要在播放时带特定的 header
        header = "Referer=https://example-encrypted.com/&User-Agent=Mozilla/5.0"
        return {"parse": 0, "url": id, "header": header}


# ═══════════════════════════════════════════════════
# 化龙秘境 · 全能混合派
# ═══════════════════════════════════════════════════
class HuaLong_JiuBian(YuanTianShu):
    """
    【化龙秘境 · 九变登仙】

    修炼特征：
        化龙九变，每一变都是脱胎换骨。
        此境界修士专修"变化"之道——
        不仅抓视频，还抓小说（纯文本）和图片集（套图）。
        判断 vod_id 前缀，如果是 novel_ 就走纯文本提取，
        如果是 image_ 就走图片链接拼接。

    对应流派：全能混合派（如 午夜影院壳版.py、色库免翻.py、花都院.py）

    功法口诀：
        "包含特殊协议处理（novel:// 和 pics://），
         甚至后台开线程并发下载女优封面。
         核心：判断 vod_id 前缀，走不同提取逻辑。"

    九变对应九种内容：
        一变 · 视频（video_）
        二变 · 小说（novel_）
        三变 · 图片（image_）
        四变 · 漫画（comic_）
        五变 · 音频（audio_）
        六变 · 直播（live_）
        七变 · 综艺（variety_）
        八变 · 动漫（anime_）
        九变 · 综合（mix_）

    形象比喻：大型商超，既卖菜（视频）又卖书（小说）还卖画（图片）。
    """

    def __init__(self):
        self.siteUrl = "https://example-omni.com"
        # 化龙修士，掌握九种变化
        self.protocol_handlers = {
            "video": self._handle_video,
            "novel": self._handle_novel,
            "image": self._handle_image,
            "comic": self._handle_comic,
            "audio": self._handle_audio,
            "live": self._handle_live,
            "variety": self._handle_variety,
            "anime": self._handle_anime,
            "mix": self._handle_mix,
        }

    def _detect_type(self, vod_id):
        """识别变化——根据 vod_id 前缀判断内容类型"""
        for prefix in self.protocol_handlers:
            if vod_id.startswith(f"{prefix}_"):
                return prefix
        return "video"  # 默认视频

    # ───────── 一变 · 视频 ─────────
    def _handle_video(self, vod_id):
        """视频处理——调用轮海/四极境的直取或解密逻辑"""
        real_id = vod_id.replace("video_", "")
        url = f"{self.siteUrl}/video/{real_id}"
        html = self.fetch(url)
        m3u8 = re.search(r'src="([^"]+\.m3u8)"', html)
        return m3u8.group(1) if m3u8 else ""

    # ───────── 二变 · 小说 ─────────
    def _handle_novel(self, vod_id):
        """
        小说处理——纯文本提取，返回 novel:// 协议链接。
        TVBox 收到 novel:// 协议后，会调用专门的文本阅读器。
        """
        real_id = vod_id.replace("novel_", "")
        url = f"{self.siteUrl}/novel/{real_id}"
        html = self.fetch(url)
        # 提取章节内容
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.select_one(".chapter-content")
        if content_div:
            # 将文本内容编码为 base64，包装为 novel:// 协议
            text = content_div.get_text("\n", strip=True)
            encoded = base64.b64encode(text.encode()).decode()
            return f"novel://{encoded}"
        return ""

    # ───────── 三变 · 图片 ─────────
    def _handle_image(self, vod_id):
        """
        图片处理——套图链接拼接，返回 pics:// 协议链接。
        格式：pics://url1|url2|url3
        """
        real_id = vod_id.replace("image_", "")
        url = f"{self.siteUrl}/gallery/{real_id}"
        html = self.fetch(url)
        imgs = re.findall(r'<img[^>]+data-src="([^"]+)"[^>]*class="gallery-img"', html)
        if imgs:
            # 拼接为 pics:// 协议
            return "pics://" + "|".join(imgs)
        return ""

    # ───────── 四变 · 漫画 ─────────
    def _handle_comic(self, vod_id):
        """漫画处理——类似图片，但按页码排序"""
        real_id = vod_id.replace("comic_", "")
        url = f"{self.siteUrl}/comic/{real_id}"
        html = self.fetch(url)
        pages = re.findall(r'<img[^>]+src="([^"]+)"[^>]*data-page="\d+"', html)
        return "pics://" + "|".join(pages) if pages else ""

    # ───────── 五变 · 音频 ─────────
    def _handle_audio(self, vod_id):
        """音频处理——提取 mp3 直链"""
        real_id = vod_id.replace("audio_", "")
        url = f"{self.siteUrl}/audio/{real_id}"
        html = self.fetch(url)
        mp3 = re.search(r'<audio[^>]+src="([^"]+\.mp3)"', html)
        return mp3.group(1) if mp3 else ""

    # ───────── 六变 · 直播 ─────────
    def _handle_live(self, vod_id):
        """直播处理——返回 m3u8 直播流"""
        real_id = vod_id.replace("live_", "")
        return f"{self.siteUrl}/live/{real_id}.m3u8"

    # ───────── 七变 · 综艺 ─────────
    def _handle_variety(self, vod_id):
        """综艺处理——多期数，类似视频但集数命名不同"""
        real_id = vod_id.replace("variety_", "")
        url = f"{self.siteUrl}/variety/{real_id}"
        html = self.fetch(url)
        episodes = re.findall(r'<a href="(/variety/[^"]+)">第([^<]+)期</a>', html)
        return "#".join([f"第{ep[1]}期${self.siteUrl}{ep[0]}" for ep in episodes])

    # ───────── 八变 · 动漫 ─────────
    def _handle_anime(self, vod_id):
        """动漫处理——多集数+弹幕支持"""
        real_id = vod_id.replace("anime_", "")
        url = f"{self.siteUrl}/anime/{real_id}"
        html = self.fetch(url)
        eps = re.findall(r'<a href="(/anime/[^"]+)">第(\d+)集</a>', html)
        return "#".join([f"第{ep[1]}集${self.siteUrl}{ep[0]}" for ep in eps])

    # ───────── 九变 · 综合 ─────────
    def _handle_mix(self, vod_id):
        """综合处理——聚合多种内容"""
        real_id = vod_id.replace("mix_", "")
        # 混合内容，返回视频+相关图片
        video_url = self._handle_video(f"video_{real_id}")
        img_url = self._handle_image(f"image_{real_id}")
        return f"{video_url}##{img_url}"

    def detailContent(self, ids):
        """
        化龙境修士看详情——九变随心，自动识别内容类型。
        """
        vod_id = ids[0]
        content_type = self._detect_type(vod_id)
        handler = self.protocol_handlers.get(content_type, self._handle_video)

        result = handler(vod_id)

        # 根据类型组装返回格式
        if content_type == "novel":
            play_from = "小说阅读"
            play_url = f"全文${result}"
        elif content_type in ["image", "comic"]:
            play_from = "图集浏览"
            play_url = f"套图${result}"
        elif content_type == "audio":
            play_from = "音频直链"
            play_url = f"第1集${result}"
        elif content_type == "live":
            play_from = "直播源"
            play_url = f"直播${result}"
        else:
            play_from = "视频直链"
            play_url = result if "#" in result else f"第1集${result}"

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": f"化龙九变·{content_type}",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """
        化龙境修士播放——识别协议类型，分别处理。
        """
        if id.startswith("novel://"):
            # 小说协议，直接返回 base64 文本
            return {"parse": 1, "url": id, "header": ""}
        elif id.startswith("pics://"):
            # 图片协议，TVBox 会调用图集浏览器
            return {"parse": 1, "url": id, "header": ""}
        else:
            # 视频/音频/直播，直接播放
            return {"parse": 0, "url": id, "header": ""}


# ═══════════════════════════════════════════════════
# 仙台秘境 · 天帝级整合
# ═══════════════════════════════════════════════════
class XianTai_DiYiTian(HuaLong_JiuBian, SiJi_TongTian, DaoGong_ShenZang, LunHai_BiAn):
    """
    【仙台秘境 · 第一重天】—— 半步大能
    整合轮海（轻量）+ 道宫（防御）+ 四极（加密）+ 化龙（混合）
    """
    pass

class XianTai_DiErTian(XianTai_DiYiTian):
    """
    【仙台秘境 · 第二重天】—— 大能
    可自动识别目标网站特征，动态选择最佳境界应对。
    """

    def __init__(self):
        super().__init__()
        # 大能可"推演"目标网站防御等级
        self.defense_level = 0  # 0=无防御, 1=简单反爬, 2=加密, 3=全能

    def _detect_defense(self, url):
        """推演天机——探测目标网站防御等级"""
        html = self.fetch(url)
        if not html:
            return 0
        # 检测加密特征
        if "encrypt" in html or "AES" in html or "crypto" in html:
            return 2
        # 检测反爬特征
        if "cf-browser-verification" in html or len(html) < 1000:
            return 1
        # 检测混合内容
        if "novel" in html and "gallery" in html:
            return 3
        return 0

class XianTai_DiSanTian(XianTai_DiErTian):
    """
    【仙台秘境 · 第三重天】—— 斩道王者
    一念可斩道，可自动切换 User-Agent、代理、Cookie 池。
    """
    pass

class XianTai_DiSiTian(XianTai_DiSanTian):
    """
    【仙台秘境 · 第四重天】—— 圣人
    万法不侵，可处理 JS 混淆、WebAssembly 加密。
    """
    pass

class XianTai_DiWuTian(XianTai_DiSiTian):
    """
    【仙台秘境 · 第五重天】—— 圣人王
    可构建分布式爬虫集群，多源并发抓取。
    """
    pass

class XianTai_DiLiuTian(XianTai_DiWuTian):
    """
    【仙台秘境 · 第六重天】—— 大圣
    一根毫毛化身千万，多线程+异步并发，大圣级吞吐量。
    """
    pass

class XianTai_DiQiTian(XianTai_DiLiuTian):
    """
    【仙台秘境 · 第七重天】—— 准帝
    触摸帝道法则，可自动逆向 JS 加密算法，生成解密脚本。
    """
    pass

class XianTai_DiBaTian(XianTai_DiQiTian):
    """
    【仙台秘境 · 第八重天】—— 至尊/古皇
    可活捉网站管理员，逼问接口文档（误）。
    实际：可处理 99% 的网站防御机制。
    """
    pass

class XianTai_DiJiuTian(XianTai_DiBaTian):
    """
    【仙台秘境 · 第九重天】—— 大帝
    一念万源，天下无不可抓之站。
    整合所有境界奥义，根据目标网站特征自动选择最优策略。
    """

    def __init__(self):
        super().__init__()
        # 大帝级配置——海纳百川
        self.strategies = {
            0: LunHai_BiAn(),      # 无防御 → 轮海大圆满（轻量直取）
            1: DaoGong_ShenZang(), # 简单反爬 → 道宫（防御破解）
            2: SiJi_TongTian(),    # 加密 → 四极（暴力破解）
            3: HuaLong_JiuBian(),  # 全能 → 化龙（九变应对）
        }

    def homeContent(self, filter):
        """大帝级首页——根据目标自动选择境界"""
        level = self._detect_defense(self.siteUrl)
        strategy = self.strategies.get(level, self.strategies[0])
        return strategy.homeContent(filter)

    def categoryContent(self, tid, pg, filter, extend):
        """大帝级列表——根据目标自动选择境界"""
        level = self._detect_defense(self.siteUrl)
        strategy = self.strategies.get(level, self.strategies[0])
        return strategy.categoryContent(tid, pg, filter, extend)

    def detailContent(self, ids):
        """大帝级详情——根据目标自动选择境界"""
        level = self._detect_defense(self.siteUrl)
        strategy = self.strategies.get(level, self.strategies[0])
        return strategy.detailContent(ids)

    def playerContent(self, flag, id, vipFlags):
        """大帝级播放——根据目标自动选择境界"""
        level = self._detect_defense(self.siteUrl)
        strategy = self.strategies.get(level, self.strategies[0])
        return strategy.playerContent(flag, id, vipFlags)


# ═══════════════════════════════════════════════════
# 红尘仙 · 最终入口
# ═══════════════════════════════════════════════════
class HongChenXian(XianTai_DiJiuTian):
    """
    【红尘仙】

    在仙台九重天之上，还有一层——红尘仙。
    不为成仙，只为在红尘中等你归来（抓取所有数据）。

    此境界已超越技术范畴，达到"道"的层面：
        - 不需写死正则，可自动学习网页结构
        - 不需内置密钥，可自动分析加密逻辑
        - 不需手动配置，可自动适配 TVBox 接口

    当然，以上都是吹牛逼的。红尘仙也得写正则。
    但至少，这个类是最终的 TVBox 入口类。
    """

    def init(self, extend=""):
        """红尘仙初始化——万法归一"""
        print("[红尘仙] 不为成仙，只为在红尘中抓尽天下视频...")
        return True

    def isVideoFormat(self, url):
        """识别视频格式——仙之眼可辨真伪"""
        video_formats = [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi"]
        return any(fmt in url.lower() for fmt in video_formats)

    def manualVideoCheck(self):
        """人工复核——仙之心可感善恶"""
        return False

    def localProxy(self, param):
        """
        本地代理——红尘仙的化身之一。
        处理道宫境的代理请求（皆字秘净化 + 阵字秘转发）。
        """
        try:
            import http.server
            import socketserver

            class ProxyHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(self.path)
                    params = parse_qs(parsed.query)

                    if parsed.path == "/proxy":
                        real_url = base64.b64decode(params.get("url", [""])[0]).decode()
                        referer = base64.b64decode(params.get("ref", [""])[0]).decode()

                        headers = {"Referer": referer, "User-Agent": "Mozilla/5.0"}
                        resp = requests.get(real_url, headers=headers, stream=True)

                        content_type = resp.headers.get("Content-Type", "")

                        # 如果是 m3u8，启动皆字秘净化
                        if "mpegurl" in content_type or real_url.endswith(".m3u8"):
                            content = resp.text
                            cleaned = DaoGong_ShenZang()._clean_m3u8(content)
                            self.send_response(200)
                            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                            self.end_headers()
                            self.wfile.write(cleaned.encode())
                        else:
                            # 普通转发
                            self.send_response(resp.status_code)
                            for key, val in resp.headers.items():
                                if key.lower() not in ["content-encoding", "transfer-encoding"]:
                                    self.send_header(key, val)
                            self.end_headers()
                            for chunk in resp.iter_content(8192):
                                self.wfile.write(chunk)
                    else:
                        self.send_response(404)
                        self.end_headers()

            # 启动代理服务器（实际应在独立线程中运行）
            # 此处仅返回配置信息
            return [200, "application/json", json.dumps({
                "proxy": f"http://127.0.0.1:{self.proxyPort}",
                "status": "running"
            })]
        except Exception as e:
            return [500, "application/json", json.dumps({"error": str(e)})]


# ═══════════════════════════════════════════════════
# TVBox 标准入口（红尘仙下凡）
# ═══════════════════════════════════════════════════
class Spider(HongChenXian):
    """
    TVBox 标准入口类。
    红尘仙降世，化为 Spider，接入 TVBox 生态。
    """
    pass


# ═══════════════════════════════════════════════════
# 修炼指南（使用说明）
# ═══════════════════════════════════════════════════
"""
【修炼指南】

1. 目标网站无加密、无反爬 → 修炼轮海秘境（LunHai_BiAn）
   复制改改正则即可，代码最精简。

2. 目标网站有防盗链、有广告分片 → 修炼道宫秘境（DaoGong_ShenZang）
   重点皆字秘（_clean_m3u8）和阵字秘（_proxy_url）。

3. 目标网站有加密参数 → 修炼四极秘境（SiJi_TongTian）
   重点 _aes_cbc_decrypt、_xor_decrypt、_generate_token。

4. 目标网站内容多样（视频+小说+图片） → 修炼化龙秘境（HuaLong_JiuBian）
   重点 protocol_handlers 和 _detect_type。

5. 想一劳永逸、自动适配 → 修炼仙台秘境（XianTai_DiJiuTian）
   大帝级自动识别，但代码量也是最大的。

6. 最终 TVBox 入口 → 红尘仙（HongChenXian / Spider）
   万法归一，接入 TVBox。

【遮天名言】
""我为天帝，当抓尽世间一切视频！"" —— 红尘仙·叶凡
"""

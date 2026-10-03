# -*- coding: utf-8 -*-
# ============ 88测试结构模板（派生自71us v7.5·测试版；原母版未动） ============
# ★88测试版新增: ①_log诊断日志 ②_pid防御解析+header/user_agent双键 ③_safe选集断链保护 ④多级TTL缓存(home3600/详情1800/播放900) ⑤容错取值三件套_dig/_card/_plist(共和国动漫A级)⑥请求串行锁SERIAL(开关)⑦满页判定_pgc ⑧CFGuard过盾引擎(WebView真内核·CF站可选外衣)⑨翻页续读族(单飞去重+游标+补读簿+判死+去重环; 多页源防跳空丢页; 出处cuct v13攻坚)⑩三段续读族(详情/搜索/播放容错续读: 续读梯_rty+列表记忆li+最小结构兜底+预算收件_gather+源黑名单)
# ★88测试版修正: localProxy入参dict崩溃修复(三形态+key=/url=/img:b64) 失败分支统一[404,'text/plain',''](内核兼容口径)；查错修整(2026-09-15)：未用导入清理3处 + 重复导入合并3处 + 裸except加固10处→Exception，零功能变更
# ★88-8 过盾引擎: CF_GUARD=1开(CF盾站); _get_raw盾页自动兜底(WebView真内核), cookie自动注入, _gget强通道, cf_verify()手动入口; 引擎段可整段替换(cf_guard.py 2026-09-13)
# ★88-8b 引擎修正(2026-09-16·同步zzoc实战·均站点无关): ①CF_WVUA='__native__'原生UA铁律(面具UA=挑战内死循环, 原生UA=8.1s过盾) ②过盾成功即CookieManager收cookie自动落盘(修'每请求必走WebView') ③过盾后UA回写(cf_clearance与UA绑定) ④盾页兜底timeout=40s
# ★88-9 翻页续读族: CONT=1开(多页分类源防跳空丢页); 单飞去重+游标+补读簿+判死+去重环+余光预取; 键 cur:/seen:/hold:/pf:/bf:; 站点仅需实现 _cat_fetch(t,cls,ex2,ex,pn)->(items,pagecount); 回填位置 BF_POS(0尾/1头)
# ★88-10 三段续读: 详情=续读梯+负缓存+最小结构兜底(li:); 搜索=续读梯+去重环+预算收件_gather+源黑名单(sb:); 播放=续读梯+负缓存; 复用⑨单飞; 负缓存键 mm:
# ★88-11 搜索开关自开(2026-09-16·fantuan实证): 影视仓聚合搜索只调用 registry.json 里 searchable=1 的源(添加本地源默认全0→源内搜索正常但实机搜索永远空); 本源init时自动把匹配条目 searchable/quickSearch 置1(顶层+site内4处; 改前原文存 .src_bak), App重启后生效; REG_FIX=1 开, REG_MATCH 空=全开/非空=按name或api匹配
# 定版: 71us模板v7.4(555骨架+能力层) + 勃士13接口四壳协议 | 2026-09-07
# 13接口=init/homeContent/categoryContent/detailContent/searchContent/playerContent/localProxy/isVideoFormat/manualVideoCheck/getDependence/destroy/progressVideo/setVideoFlags
# 四壳通用: TVBox/T4(只认555五接口) / 海阔/影视仓1.x(额外调扩展钩子) / 独立加载(无base.spider走兜底)
# ★自动调用协议(套本模板写源/修复/重构/逆向=自动触发, 先过清单再动手, 缺一不可):
# ①记忆库检索: query_memory『知识库/影视源开发』→《py源开发技能清单v18》(v18>v17>v16), 开工即查
# ②技能包13包分层调度(技能库全量13包=目录16个−红果系3资产[fq_crypto_lib/fq_cenc_stream/hongguo_main]; 写源核心调度11包=13−peekpro−ikguard; /sdcard/Download/Operit/skills/):
#   L0骨架 tvbox-py-v73(本模板母版) | L1入口 pySkill(spider-create全类型7内容) | L2攻坚 gpt56全家桶(eni/INDEX.md路由90项+kit冷咖啡+five_blade五刃)+reverse-skill(87技能逆向路由)+遮天九秘_破甲版(zhetian.py/cf-bypass/aes-decrypt) | L3质量 adaptive四工作台(播放契约/响应边界/图片资源/清洗规范化)并行套用 | L4交付 wei-ai-xiao-ge(影视仓加载契约/测试矩阵)+jk-lingyu-spider(MacCMS/Txmojia样本)
#   ★包内 references 症状索引(2026-09-19新增·写源遇对应症状即阅): 图片白图/中转慢→adaptive-image-resource-workbench/references/local-relay-hardening.md; 分类空白/首页转圈→adaptive-video-response-workbench/references/api-budget-cache-traps.md; 真机报错但沙箱正常→wei-ai-xiao-ge/references/device-log-first-triage.md; 分类与官网不一致→jk-lingyu-spider/references/taxonomy-sync.md; VIP墙硬锁→遮天九秘_破甲版/技能包/spider-craft/no-auth-cdn-bypass.md
# r3.1.4 口径修正(2026-09-19·零功能变更): ①技能包口径统一13包(原11=写源核心调度子集,易误读为技能库总数) ②补包内 references 症状索引五章 ③71us v7.5母版保持冻结不动, 本派生版承载口径与索引更新
# ★站点级实测纠偏(bestjavporn·browser实机DOM取证): ①CATEGORIES改真实slug+CAT_PATH(v37/category/censored/实证) ②_nav_map()于init解析nav得真实 /vNN/category/{slug}/ 覆盖静态表 ③_items_card()锚定 article.thumb-block + a[href*="/video/"] + img[src] ④_dcands 收敛为 /video/{slug}/ ⑤详情无明文直链时必出 "线路1$详情页URL"(否则影视仓无线路可点) ⑥playerContent: 媒体正则放宽(.m3u8/.mp4/.flv)+parse:1回退 —— 该站播放源为 data-mpu / span.srv[data-link] / #video-infos[data-blk] 三处同族 Base64 AES 密文(496B=16×31块), 而页面不下发任何解密器(11个外链脚本+全部内联+主题JS均无 mpu/blk/srv 关键字, 15个候选播放器脚本全404, 无原生iframe) → 播放交宿主 WebView 解析嗅探, 宿主内 jQuery/主题JS正常时由主题解密后注入iframe

# ③交付铁律: py_compile → 555契约字段(coding/sys.path/class Spider(Spider)/init(extend)/homeContent/homeVideoContent/searchContent/categoryContent/playerContent) → 模拟T4全调用链 → 播放链验证 → 双份md5一致
# 用法: 只改 ★ 区(CONFIG/init), 其余通用; 站点无某项能力直接省略对应方法调用
# 加载契约: 首行coding/sys.path.append('..')/from base.spider import Spider(带兜底)/class Spider(Spider)
# ★版本兼容铁律: 全文件禁3.9+API(random.randbytes/removeprefix/removesuffix等; OK影视内置Python≤3.8教训2026-09), 随机字节用bytes([random.randrange(1,256)]), 交付前grep -n 'randbytes'自查
# ★分隔符铁律: $=名称/地址 | #=选集 | $$$=线路; 严禁$$或$连选集; 线路名与地址$$$段数必须相等
# ★链路策略v4: 资源默认直连输出, 仅403/防盗链/KEY404/需特殊头才走 localProxy 兜底
import sys, re, json, time, base64, hashlib, threading
from urllib.parse import urljoin, quote, unquote, urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import requests
import urllib.request, urllib.parse

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

# ============ ★ CONFIG ============
HOSTS = ['https://www.bestjavporn.com']  # ★ 多域名轮询(主在前), 防封容灾
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
CATEGORIES = {'censored': '日本有碼', 'uncensored': '無碼', 'amateur': '素人', 'decensored': '去碼', 'english-subtitle': '英文字幕', 'chinese-subtitle': '中文字幕', 'subtitle-indonesia': '字幕印尼', '10musume': '10Musume', '1pondo': '1Pondo', 'caribbeancom': 'Caribbeancom', 'fc2-ppv': 'FC2 PPV', 'heyzo': 'Heyzo', 'hitozuma': '人妻', 'pacopacomama': 'PacoPacomama', 'subthai': '字幕泰文', 'tokyo-hot': 'Tokyo Hot', 'uncensored-leaked': '無碼流出', 'pornstars': '女優', 'studios': '片商'}  # ★ 一级; type=真实分类slug(实测: nav菜单)
CAT_PATH = {'censored': '/category/censored/', 'uncensored': '/category/uncensored/', 'amateur': '/category/amateur/', 'decensored': '/category/decensored/', 'english-subtitle': '/category/censored/english-subtitle/', 'chinese-subtitle': '/category/chinese-subtitle/', 'subtitle-indonesia': '/category/subtitle-indonesia/', '10musume': '/category/uncensored/10musume/', '1pondo': '/category/uncensored/1pondo/', 'caribbeancom': '/category/uncensored/caribbeancom/', 'fc2-ppv': '/category/uncensored/fc2-ppv/', 'heyzo': '/category/uncensored/heyzo/', 'hitozuma': '/category/hitozuma/', 'pacopacomama': '/category/uncensored/pacopacomama/', 'subthai': '/category/subthai/', 'tokyo-hot': '/category/uncensored/tokyo-hot/', 'uncensored-leaked': '/category/decensored/uncensored-leaked/', 'pornstars': '/pornstars/', 'studios': '/studios/'}  # ★ 实测路径前缀(v37/censored已实机验证; 运行时 _nav_map 覆盖优先)
PK = ''  # ★ 接口密钥(签名/AES key/解密用)
REFERER = 'https://www.bestjavporn.com/'  # ★ 播放/资源防盗链Referer(空=用self.base)
PIC_REFERER = 'https://www.bestjavporn.com/'  # ★ 图片防盗链Referer(空=无)
FD_ZONE = 0  # ★ 分片区段(71us .fd 协议用, 无则0)
PROBE = 1  # ★ 详情多线路实测排序开关 1/0
SITE_KEY = 'bestjavporn'  # ★ 壳源标识(海阔setVideoFlags回调时上报, 调试多源用)
VIDEO_EXTS = 'm3u8|mp4|flv|mkv|avi|ts'  # ★ isVideoFormat判定扩展名(竖线分隔)
DEBUG = 1  # ★88-1 诊断日志开关(1开/0关)
LOG_PATH = '/sdcard/bestjavporn_debug.log'  # ★88-1 诊断日志固定路径(单条截断300字)
TTL_HOME = 3600  # ★88-4 首页缓存(秒)
TTL_DETAIL = 1800  # ★88-4 详情缓存(秒)
TTL_PLAY = 900  # ★88-4 播放缓存(秒)
SERIAL = 0  # ★88-6 请求串行锁(1开/0关; 防风控站开启, 请求排队串行)
PAGE_SIZE = 24  # ★88-7 每页条数(满页判定基准; 站点源按需改)
REG_FIX = 1  # ★88-11 搜索开关自开(1开/0关; init时把registry条目searchable/quickSearch置1, App重启后生效)
REG_MATCH = ''  # ★88-11 匹配串(空=全开registry全部源; 非空=只开name/api含此串的条目, 如 'fantuan')
CF_GUARD = 1  # ★88-8 过盾引擎开关(1开/0关; CF盾站开启, WebView真内核+cf_clearance持久化)
CF_WVUA = '__native__'  # ★88-8b 过盾WebView UA('__native__'=原生UA铁律·默认; zzoc实证: 面具UA=挑战内死循环, 原生UA=8.1s过盾; ''=引擎自选缓存UA; 或字面UA串)
CF_HOST = 'https://www.bestjavporn.com'  # ★88-8 过盾目标站(留空=用HOSTS[0])
CF_COOKIE_DIR = '/storage/emulated/0/tmp/123'  # ★88-8 CF cookie缓存目录(按域名分文件, 多站共用)
CONT = 1  # ★88-9 翻页续读族开关(1开/0关; 多页分类源防跳空丢页, 简单站可关)
CURSOR_TTL = 7200  # ★88-9 游标/去重环存活(秒)
HOLD_TTL = 21600  # ★88-9 补读簿存活(秒)
HOLD_MAX = 8  # ★88-9 补读簿容量(页/分类)
HOLD_FAILS = 3  # ★88-9 判死门槛:失败次数
HOLD_SPAN = 300  # ★88-9 判死门槛:时间跨度(秒; 次数×跨度双门槛同满足才判真洞)
SEEN_CAP = 400  # ★88-9 去重环容量(条)
PROBE_MAX = 1
WARM = 0
GCACHE = 1
GC_TTL = 1800
GC_MAX = 800  # ★88-9 空页跳探测上限(+N页)
LADDER_SLEEP = 0.35  # ★88-9 递进重试间隔(秒)
BF_POS = 0  # ★88-9 补读回填位置(0=下一轮尾部/1=头部)
MISS_TTL = 60  # ★88-10 负缓存时长(详情/播放/搜索失败记忆, 秒)
LI_CAP = 600  # ★88-10 列表记忆容量(条; 详情失败最小结构兜底用)
GATHER_BUDGET = 8.0  # ★88-10 搜索预算收件(秒; 聚合源多源收集用)

def _log(msg):
    if not DEBUG:
        return
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%m-%d %H:%M:%S'), str(msg)[:300]))
    except Exception:
        pass

# ============ AES 纯Python引擎(Crypto不可用时降级) ============
SBOX = [99, 124, 119, 123, 242, 107, 111, 197, 48, 1, 103, 43, 254, 215, 171, 118, 202, 130, 201, 125, 250, 89, 71, 240, 173, 212, 162, 175, 156, 164, 114, 192, 183, 253, 147, 38, 54, 63, 247, 204, 52, 165, 229, 241, 113, 216, 49, 21, 4, 199, 35, 195, 24, 150, 5, 154, 7, 18, 128, 226, 235, 39, 178, 117, 9, 131, 44, 26, 27, 110, 90, 160, 82, 59, 214, 179, 41, 227, 47, 132, 83, 209, 0, 237, 32, 252, 177, 91, 106, 203, 190, 57, 74, 76, 88, 207, 208, 239, 170, 251, 67, 77, 51, 133, 69, 249, 2, 127, 80, 60, 159, 168, 81, 163, 64, 143, 146, 157, 56, 245, 188, 182, 218, 33, 16, 255, 243, 210, 205, 12, 19, 236, 95, 151, 68, 23, 196, 167, 126, 61, 100, 93, 25, 115, 96, 129, 79, 220, 34, 42, 144, 136, 70, 238, 184, 20, 222, 94, 11, 219, 224, 50, 58, 10, 73, 6, 36, 92, 194, 211, 172, 98, 145, 149, 228, 121, 231, 200, 55, 109, 141, 213, 78, 169, 108, 86, 244, 234, 101, 122, 174, 8, 186, 120, 37, 46, 28, 166, 180, 198, 232, 221, 116, 31, 75, 189, 139, 138, 112, 62, 181, 102, 72, 3, 246, 14, 97, 53, 87, 185, 134, 193, 29, 158, 225, 248, 152, 17, 105, 217, 142, 148, 155, 30, 135, 233, 206, 85, 40, 223, 140, 161, 137, 13, 191, 230, 66, 104, 65, 153, 45, 15, 176, 84, 187, 22]
IS = [0] * 256
for _i, _v in enumerate(SBOX):
    IS[_v] = _i
RCON = [1, 2, 4, 8, 16, 32, 64, 128, 27, 54, 108, 216, 171, 77]
G2 = [0] * 256
G3 = [0] * 256
for _i in range(256):
    _t = _i << 1
    if _i & 128:
        _t ^= 0x11b
    G2[_i] = _t
    G3[_i] = G2[_i] ^ _i


def _ke(k):
    nk = len(k) // 4
    nr = nk + 6
    w = [list(k[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = w[i - 1][:]
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return w


def _enc(b, w):
    s = [[b[r + 4 * c] for c in range(4)] for r in range(4)]
    def add(r):
        for i in range(4):
            for j in range(4):
                s[i][j] ^= w[r * 4 + j][i]
    def sub():
        for i in range(4):
            for j in range(4):
                s[i][j] = SBOX[s[i][j]]
    def sh():
        for r in range(1, 4):
            s[r] = s[r][r:] + s[r][:r]
    def mx():
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = G2[a[0]] ^ G3[a[1]] ^ a[2] ^ a[3]
            s[1][c] = a[0] ^ G2[a[1]] ^ G3[a[2]] ^ a[3]
            s[2][c] = a[0] ^ a[1] ^ G2[a[2]] ^ G3[a[3]]
            s[3][c] = G3[a[0]] ^ a[1] ^ a[2] ^ G2[a[3]]
    add(0)
    nr = len(w) // 4 - 1
    for rnd in range(1, nr):
        sub()
        sh()
        mx()
        add(rnd)
    sub()
    sh()
    add(nr)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def _gm(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        a = (a << 1) ^ 0x11b if a & 0x80 else a << 1
        b >>= 1
    return p & 0xff


def _dec(b, w):
    s = [[b[r + 4 * c] for c in range(4)] for r in range(4)]
    def add(r):
        for i in range(4):
            for j in range(4):
                s[i][j] ^= w[r * 4 + j][i]
    def isub():
        for i in range(4):
            for j in range(4):
                s[i][j] = IS[s[i][j]]
    def ish():
        for r in range(1, 4):
            s[r] = s[r][-r:] + s[r][:-r]
    def imx():
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = _gm(a[0], 14) ^ _gm(a[1], 11) ^ _gm(a[2], 13) ^ _gm(a[3], 9)
            s[1][c] = _gm(a[0], 9) ^ _gm(a[1], 14) ^ _gm(a[2], 11) ^ _gm(a[3], 13)
            s[2][c] = _gm(a[0], 13) ^ _gm(a[1], 9) ^ _gm(a[2], 14) ^ _gm(a[3], 11)
            s[3][c] = _gm(a[0], 11) ^ _gm(a[1], 13) ^ _gm(a[2], 9) ^ _gm(a[3], 14)
    nr = len(w) // 4 - 1
    add(nr)
    for rnd in range(nr - 1, 0, -1):
        ish()
        isub()
        add(rnd)
        imx()
    ish()
    isub()
    add(0)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def aes_ecb(data, key, mode=1):
    w = _ke(key)
    out = b''
    if mode:
        pad = 16 - len(data) % 16
        data += bytes([pad]) * pad
        for i in range(0, len(data), 16):
            out += _enc(data[i:i + 16], w)
    else:
        for i in range(0, len(data), 16):
            out += _dec(data[i:i + 16], w)
        if out and 0 < out[-1] <= 16:
            out = out[:-out[-1]]
    return out


def aes_cbc(data, key, iv, enc=1):
    w = _ke(key)
    out = b''
    prev = iv
    if enc:
        pad = 16 - len(data) % 16
        data += bytes([pad]) * pad
        for i in range(0, len(data), 16):
            blk = bytes(data[i + j] ^ prev[j] for j in range(16))
            ct = _enc(blk, w)
            out += ct
            prev = ct
    else:
        for i in range(0, len(data), 16):
            blk = _dec(data[i:i + 16], w)
            out += bytes(blk[j] ^ prev[j] for j in range(16))
            prev = data[i:i + 16]
        if out and 0 < out[-1] <= 16:
            out = out[:-out[-1]]
    return out


# ============ ★BJP解密引擎(WP-Script RetroTube cast.js dex + video子域 main.js) ============
DEX_C1 = "_0x58fe15"
DEX_C2 = "_0x59a0e4"


def _dx(k, c, const=DEX_C1, nested=True):
    k = str(k or '')
    raw = str(c or '').strip()
    if not k or not raw:
        return ''
    try:
        d = base64.b64decode(raw + '=' * (-len(raw) % 4))
    except Exception:
        return ''
    seed = base64.b64encode((k + const).encode()).decode()[::-1]
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(seed[i % len(seed)])) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for ch in d:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(ch ^ s[(s[i] + s[j]) % 256])
    if not nested:
        return bytes(out).decode('utf-8', 'ignore')
    try:
        return base64.b64decode(bytes(out) + b'=' * (-len(out) % 4)).decode('utf-8', 'ignore')
    except Exception:
        return ''


# ============ ★88-8 CFGuard过盾引擎（站点无关·整段可替换；来源 cf_guard.py 2026-09-13） ============
import os, urllib.parse

try:
    from java import jclass, dynamic_proxy
except ImportError:
    jclass = None
    dynamic_proxy = None


class CFGuard(object):

    UA_DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    CF_MARKS = ('just a moment', 'checking your browser', 'cf-mitigated', 'challenge-platform',
                'enable javascript and cookies to continue', 'attention required! | cloudflare',
                'verify you are human')
    COOKIE_DIR = '/storage/emulated/0/tmp/123'
    POLL_GAP = 1.5
    POLL_START = 2.0
    MAX_REFS = 60
    _cls_cache = {}

    def __init__(self, host='', cookie_dir=None, log=None, images=False):
        h = str(host or '').strip().rstrip('/')
        if h and '://' not in h:
            h = 'https://' + h
        self.host = h
        self.domain = urllib.parse.urlparse(h).netloc or h or 'default'
        self.cookie_dir = cookie_dir or self.COOKIE_DIR
        self.on_log = log
        self.images = images
        self.last_wv_ua = ''
        self.cf_marks = tuple(self.CF_MARKS)
        self._refs = []

    def available(self):
        return not (jclass is None or dynamic_proxy is None)

    def set_log(self, fn):
        self.on_log = fn

    def _log(self, msg):
        try:
            if self.on_log:
                self.on_log(msg)
                return
        except Exception:
            pass
        print('[CFGuard] ' + str(msg))

    def _keep(self, *objs):
        for o in objs:
            if o is not None:
                self._refs.append(o)
        if len(self._refs) > self.MAX_REFS:
            del self._refs[:len(self._refs) - self.MAX_REFS]

    def _cls_vc(self):
        c = CFGuard._cls_cache.get('vc')
        if c is None:
            base = dynamic_proxy(jclass('android.webkit.ValueCallback'))

            class _VC(base):
                def onReceiveValue(self, value):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn(value)
            c = CFGuard._cls_cache['vc'] = _VC
        return c

    def _cls_run(self):
        c = CFGuard._cls_cache.get('run')
        if c is None:
            base = dynamic_proxy(jclass('java.lang.Runnable'))

            class _Run(base):
                def run(self):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn()
            c = CFGuard._cls_cache['run'] = _Run
        return c

    def _cls_click(self):
        c = CFGuard._cls_cache.get('click')
        if c is None:
            base = dynamic_proxy(jclass('android.content.DialogInterface').OnClickListener)

            class _Click(base):
                def onClick(self, dialog, which):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn(dialog, which)
            c = CFGuard._cls_cache['click'] = _Click
        return c

    def _activity(self):
        try:
            AT = jclass("java.lang.Class").forName("android.app.ActivityThread")
            cur = AT.getMethod("currentActivityThread").invoke(None)
            f = AT.getDeclaredField("mActivities")
            f.setAccessible(True)
            map_obj = f.get(cur)
            values = map_obj.values().toArray() if hasattr(map_obj, "values") else map_obj.toArray()
            for r in values:
                rc = r.getClass()
                pf = rc.getDeclaredField("paused")
                pf.setAccessible(True)
                if not pf.getBoolean(r):
                    af = rc.getDeclaredField("activity")
                    af.setAccessible(True)
                    a = af.get(r)
                    if a:
                        return a
        except Exception:
            pass
        return None

    def _ui(self, fn):
        if not self.available():
            return False
        act = self._activity()
        if not act:
            return False
        try:
            r = self._cls_run()()
            r._fn = lambda: fn(act)
            self._keep(r)
            act.getWindow().getDecorView().post(r)
        except Exception:
            try:
                r2 = self._cls_run()()
                r2._fn = lambda: fn(act)
                self._keep(r2)
                jclass('android.os.Handler')(jclass('android.os.Looper').getMainLooper()).post(r2)
            except Exception:
                return False
        return True

    def _click(self, fn):
        c = self._cls_click()()
        c._fn = fn
        self._keep(c)
        return c

    def is_cf(self, text):
        if not text:
            return True
        low = str(text).lower()
        return any(m in low for m in self.cf_marks)

    def _domain(self, url):
        return urllib.parse.urlparse(str(url or '')).netloc or self.domain

    def _cookie_path(self, domain):
        return os.path.join(self.cookie_dir, str(domain or self.domain) + '.json')

    def cookies_data(self, domain=None):
        domain = str(domain or self.domain)
        p = self._cookie_path(domain)
        if not os.path.exists(p) and domain != self.domain:
            p = self._cookie_path(self.domain)
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if d.get('cookies'):
                    return d
        except Exception as e:
            self._log('读取CF cookie缓存失败: ' + str(e))
        return None

    def cookies(self, domain=None):
        d = self.cookies_data(domain)
        return dict(d.get('cookies') or {}) if d else {}

    def cookie_header(self, domain=None):
        return '; '.join('%s=%s' % (k, v) for k, v in self.cookies(domain).items())

    def ua(self, domain=None, fallback=None):
        d = self.cookies_data(domain)
        return str((d.get('ua') if d else '') or self.last_wv_ua or fallback or self.UA_DESKTOP)

    def save(self, domain, cookies, ua=''):
        try:
            os.makedirs(self.cookie_dir, exist_ok=True)
            with open(self._cookie_path(domain), 'w', encoding='utf-8') as f:
                json.dump({'cookies': cookies, 'ua': ua, 'ts': int(time.time())}, f,
                          ensure_ascii=False, indent=2)
            self._log('已保存CF cookie -> ' + self._cookie_path(domain))
        except Exception as e:
            self._log('保存CF cookie失败: ' + str(e))

    def restore(self):
        try:
            d = self.cookies_data(self.domain)
            if not (d and d.get('cookies')) or jclass is None:
                return False
            cm = jclass('android.webkit.CookieManager').getInstance()
            cm.setAcceptCookie(True)
            site = self.host or ('https://' + self.domain)
            for k, v in d['cookies'].items():
                cm.setCookie(site, '%s=%s' % (k, v))
            cm.flush()
            self._log('[恢复] CookieManager写入完成')
            return True
        except Exception as e:
            self._log('[恢复] 写回CookieManager失败: ' + str(e))
            return False

    def wv_html(self, url, timeout=15, ua=None, js=None):
        if not self.available():
            return None
        cached = self.cookies_data(self._domain(url))
        target_ua = ua or (cached or {}).get('ua') or self.last_wv_ua or self.UA_MOBILE
        evt = threading.Event()
        store = {'html': None}

        def on_ui(act):
            try:
                WebView = jclass('android.webkit.WebView')
                WebViewClient = jclass('android.webkit.WebViewClient')
                wv = WebView(act)
                st = wv.getSettings()
                st.setJavaScriptEnabled(True)
                st.setDomStorageEnabled(True)
                if str(target_ua) == '__native__':
                    try:
                        self._log('[wv] engine-ua: ' + str(st.getUserAgentString())[-90:])
                    except Exception:
                        pass
                else:
                    st.setUserAgentString(str(target_ua))
                try:
                    self.last_wv_ua = str(st.getUserAgentString())
                except Exception:
                    self.last_wv_ua = ''
                try:
                    self._log('[wv] set-ua: ' + str(self.last_wv_ua)[-70:])
                except Exception:
                    pass
                if not self.images:
                    try:
                        st.setLoadsImagesAutomatically(False)
                    except Exception:
                        pass
                wv.setWebViewClient(WebViewClient())
                try:
                    _cm = jclass('android.webkit.CookieManager').getInstance()
                    _cm.setAcceptCookie(True)
                    _cm.setAcceptThirdPartyCookies(wv, True)
                except Exception:
                    pass
                wv.loadUrl(url)
                def cleanup():
                    try:
                        wv.stopLoading()
                        wv.loadUrl('about:blank')
                        wv.clearHistory()
                        wv.removeAllViews()
                        wv.destroy()
                    except Exception:
                        pass

                vc = self._cls_vc()()

                def _on_val(value):
                    try:
                        html = json.loads(value) if isinstance(value, str) else str(value)
                    except Exception:
                        html = str(value) if value is not None else ''
                    if html and not self.is_cf(html):
                        store['html'] = html
                        try:
                            _cm2 = jclass('android.webkit.CookieManager').getInstance()
                            _raw = _cm2.getCookie(url) or ''
                            _cks = {}
                            for _p in _raw.split(';'):
                                _p = _p.strip()
                                if '=' in _p:
                                    _k, _v = _p.split('=', 1)
                                    _cks[_k.strip()] = _v
                            if _cks:
                                self.save(self._domain(url), _cks, self.last_wv_ua or target_ua)
                                _sig8 = ','.join(sorted(_cks.keys()))
                                if _sig8 != getattr(self, '_ck_sig', ''):
                                    self._ck_sig = _sig8
                                    self._log('[wv] cookie落盘: ' + _sig8[:100])
                        except Exception as _ce:
                            self._log('[wv] cookie收集失败: ' + str(_ce))
                        evt.set()
                        cleanup()

                vc._fn = _on_val
                self._keep(vc)
                handler = jclass('android.os.Handler')(jclass('android.os.Looper').getMainLooper())
                start = time.time()

                def loop():
                    if evt.is_set():
                        return
                    if time.time() - start > timeout:
                        evt.set()
                        cleanup()
                        return
                    try:
                        wv.evaluateJavascript(js or 'document.documentElement.outerHTML', vc)
                    except Exception:
                        evt.set()
                        cleanup()
                        return
                    r = self._cls_run()()
                    r._fn = loop
                    self._keep(r)
                    handler.postDelayed(r, int(self.POLL_GAP * 1000))

                r0 = self._cls_run()()
                r0._fn = loop
                self._keep(r0)
                handler.postDelayed(r0, int(self.POLL_START * 1000))
            except Exception as e:
                self._log('[wv] 初始化失败: ' + str(e))
                evt.set()

        if not self._ui(on_ui):
            return None
        evt.wait(timeout=timeout + 2)
        return store['html']

    def verify(self, url=None):
        url = url or ((self.host or '') + '/')
        ua = self.ua()
        headers = {'User-Agent': ua, 'Referer': (self.host or '') + '/'}

        def on_cookies(cks):
            self._log('验证完成: ' + (', '.join(cks.keys()) if cks else '无cookie'))
            if cks:
                self.save(self._domain(url), cks, self.last_wv_ua or ua)
                self.restore()
                self.toast('Cookie 验证成功并保存！')

        self._verify_dialog(url, headers, on_cookies)

    def _verify_dialog(self, url, base_headers, on_cookies):
        if not self.available():
            on_cookies({})
            return

        def on_ui(act):
            try:
                WebView = jclass('android.webkit.WebView')
                WebViewClient = jclass('android.webkit.WebViewClient')
                LinearLayout = jclass('android.widget.LinearLayout')
                TextView = jclass('android.widget.TextView')
                Builder = jclass('android.app.AlertDialog$Builder')
                CookieManager = jclass('android.webkit.CookieManager')
                TypedValue = jclass('android.util.TypedValue')
                pad = int(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 8.0,
                                                    act.getResources().getDisplayMetrics()))
                container = LinearLayout(act)
                container.setOrientation(LinearLayout.VERTICAL)
                tip = TextView(act)
                tip.setText('请完成验证（勾选/点击/输入验证码），成功后点「完成」')
                tip.setPadding(pad, pad, pad, pad)
                wv = WebView(act)
                wv.getSettings().setJavaScriptEnabled(True)
                wv.getSettings().setDomStorageEnabled(True)
                hm = jclass('java.util.HashMap')()
                for k, v in base_headers.items():
                    hm.put(str(k), str(v))
                wv.setWebViewClient(WebViewClient())
                wv.loadUrl(url, hm)
                container.addView(tip)
                container.addView(wv)
                try:
                    self.last_wv_ua = str(wv.getSettings().getUserAgentString())
                except Exception:
                    self.last_wv_ua = ''
                result = {'cookies': {}}

                def _collect():
                    raw = CookieManager.getInstance().getCookie(url) or ''
                    out = {}
                    for part in raw.split(';'):
                        part = part.strip()
                        if '=' in part:
                            k, v = part.split('=', 1)
                            out[k.strip()] = v
                    result['cookies'] = out

                def _finish(d, w):
                    _collect()
                    try:
                        if dialog is not None:
                            dialog.dismiss()
                    except Exception:
                        pass
                    on_cookies(result['cookies'])

                builder = Builder(act)
                builder.setTitle('手动过验证')
                builder.setView(container)
                builder.setPositiveButton('完成', self._click(_finish))
                builder.setNegativeButton('取消', self._click(lambda d, w: on_cookies({})))
                dialog = builder.create()
                dialog.show()
            except Exception as e:
                self._log('[verify] 弹窗失败: ' + str(e))
                on_cookies({})

        self._ui(on_ui)

    def show_log(self, lines=None, title='信息', text=''):
        body = text or ''
        if lines:
            body = (body + '\n' if body else '') + '\n'.join(str(x) for x in lines)

        def on_ui(act):
            try:
                Builder = jclass('android.app.AlertDialog$Builder')
                TextView = jclass('android.widget.TextView')
                ScrollView = jclass('android.widget.ScrollView')
                Color = jclass('android.graphics.Color')
                TypedValue = jclass('android.util.TypedValue')
                tv = TextView(act)
                tv.setText(body or '(空)')
                tv.setTextIsSelectable(True)
                tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13.0)
                tv.setTextColor(Color.parseColor('#334155'))
                pad = int(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 12.0,
                                                    act.getResources().getDisplayMetrics()))
                tv.setPadding(pad, pad, pad, pad)
                scroll = ScrollView(act)
                scroll.addView(tv)
                builder = Builder(act)
                builder.setTitle(str(title))
                builder.setView(scroll)
                builder.setPositiveButton('关闭', self._click(lambda d, w: d.dismiss() if d else None))
                dialog = builder.create()
                self._keep(dialog, tv, scroll)
                dialog.show()
            except Exception as e:
                self._log('[show_log] 失败: ' + str(e))

        return self._ui(on_ui)

    def toast(self, msg, duration=1):
        def on_ui(act):
            try:
                jclass('android.widget.Toast').makeText(act, str(msg), int(duration)).show()
            except Exception:
                pass
        return self._ui(on_ui)


class Spider(Spider):
    def init(self, extend=''):
        self.base = HOSTS[0].rstrip('/')  # ★ 主域(init内可被重定向更新)
        self.ua = UA
        self.pk = PK
        self.ref = REFERER or self.base
        self.types = dict(CATEGORIES)
        self.filters = {}  # ★ {'1':[{'key':'class','name':'类型','value':[{'n':'剧情','v':'剧情'}]}]}
        self._pc = {}  # 线路probe缓存 {md5:[ts,froms,urls]}
        self._catmap = {}  # ★实测纠偏: 运行时nav解析 {slug:'/v37/category/censored/'}
        self._tok = []  # ★实测纠偏: data-mpu/data-link/data-blk 加密token(WP-Script RetroTube主题JS解密后注入iframe)
        self._tok2 = []  # ★v7 播放线路token列表(mpu>link, blk仅兜底)
        self._srv = None  # 本地代理线程(延迟启动)
        self._c = {}
        self._gc = {}  # ★88-4 兼容槽(destroy清理用)
        self._ttl = {}  # ★88-4 多级TTL缓存 {key:[ts,val]}
        self._lock = threading.RLock()  # ★88-6 请求串行锁(SERIAL=1时启用)
        self._inflight = {}  # ★88-9 单飞去重表{键:Future}
        self.cf = None  # ★88-8 过盾引擎(CF_GUARD=1时启用)
        self._cf_skip = None  # ★提速: requests不可用时直接走WebView
        if CF_GUARD:
            self.cf = CFGuard(CF_HOST or HOSTS[0], cookie_dir=CF_COOKIE_DIR, log=_log)
            self.cf.restore()
            self.ua = self.cf.ua(fallback=self.ua)
        _h0 = ''
        try:
            r = self.fetch(self.base, headers={'User-Agent': self.ua}, timeout=10000)
            if hasattr(r, 'url') and r.url and r.url != self.base:
                self.base = r.url.rstrip('/')
            _h0 = r.text if hasattr(r, 'text') else ''
        except Exception:
            pass
        if _h0:
            try:
                self._nav_map(_h0)
            except Exception:
                pass
        if REG_FIX:
            self._reg_fix()
    # ========== ★实测纠偏: nav菜单解析(真实分类路径 /vNN/category/slug/) ==========
    def _nav_map(self, h=''):
        if not h:
            h = self._get(self.base, timeout=15000)
        if not h:
            return {}
        m = {}
        for mm in re.finditer(r'<a[^>]+href="([^"]*?/v\d+/category/[a-z0-9\-]+(?:/[a-z0-9\-]+)?/?)"[^>]*>([\s\S]{0,200}?)</a>', h, re.I):
            u = urljoin(self.base, mm.group(1))
            pth = re.sub(r'^https?://[^/]+', '', u)
            seg = [x for x in pth.strip('/').split('/') if x]
            if not seg or 'category' not in seg:
                continue
            slug = seg[-1]
            if slug in ('category', 'page'):
                continue
            if slug not in m:
                m[slug] = '/' + '/'.join(seg) + '/'
                txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', mm.group(2))).strip()[:20]
                if slug not in self.types and txt:
                    self.types[slug] = txt
        if m:
            self._catmap = m
            _log('nav_map %d %s' % (len(m), '|'.join(list(m.keys())[:10])))
        return m

    # ========== 容灾: 多HOST轮询 + requests双保险 ==========
    def _get(self, url, headers=None, timeout=15000):
        if SERIAL:
            with self._lock:
                return self._get_raw(url, headers, timeout)
        return self._get_raw(url, headers, timeout)

    def _get_raw(self, url, headers=None, timeout=15000):
        if GCACHE:
            _cv = self._gc.get(url)
            if _cv and time.time() - _cv[0] < GC_TTL:
                return _cv[1]
        if self.cf and self._cf_skip is None:
            _t0 = ''
            try:
                _r0 = self.fetch(self.base, headers={'User-Agent': self.ua}, timeout=8000)
                _t0 = _r0.text if hasattr(_r0, 'text') else str(_r0)
            except Exception:
                _t0 = ''
            self._cf_skip = 1 if (not _t0 or self.cf.is_cf(_t0)) else 0
            _log('cf-skip %d' % self._cf_skip)
        if self.cf and self._cf_skip:
            h2 = self.cf.wv_html(url, timeout=22, ua=(CF_WVUA or self.ua))
            if h2:
                try:
                    self.ua = self.cf.last_wv_ua or self.ua
                except Exception:
                    pass
                self._gput(url, h2)
                return h2
            return ''
        hd = headers or {'User-Agent': self.ua, 'Referer': self.ref}
        if self.cf:
            ckh = self.cf.cookie_header()
            if ckh and not any(str(k).lower() == 'cookie' for k in hd):
                hd = dict(hd)
                hd['Cookie'] = ckh
        try:
            r = self.fetch(url, headers=hd, timeout=timeout)
        except TypeError:
            try:
                r = self.fetch(url, headers=hd)
            except Exception:
                return ''
        except Exception:
            return ''
        try:
            text = r.text if hasattr(r, 'text') else str(r)
        except Exception:
            text = ''
        if self.cf and self.cf.is_cf(text):
            _t0 = time.time()
            h2 = self.cf.wv_html(url, timeout=22, ua=(CF_WVUA or self.ua))
            try:
                self._log('[wv] %s %.1fs ua=%s' % ('ok' if h2 else 'NONE', time.time() - _t0, (self.cf.last_wv_ua or '')[-28:]))
            except Exception:
                pass
            if h2:
                self.ua = self.cf.last_wv_ua or self.ua
                self._gput(url, h2)
                return h2
        if text and not (self.cf and self.cf.is_cf(text)):
            self._gput(url, text)
        return text
    def _gget(self, url, timeout=15):
        if self.cf and self.cf.available():
            h = self.cf.wv_html(url, timeout=timeout, ua=(CF_WVUA or self.ua))
            if h:
                return h
        return self._get(url)

    def cf_verify(self, url=None):
        if self.cf:
            self.cf.verify(url or self.base)
            return True
        return False

    def _pic(self, u):
        if not u:
            return ''
        if u.startswith('data:'):
            return ''
        if u.startswith('//'):
            u = 'https:' + u
        return u  # 直连优先; 403时 playerContent/localProxy 兜底

    def _pagecount(self, h, cur=1):
        mx = cur
        for rx in (r'changePage\((\d+)\)', r'[?&]paged[=/](\d+)', r'[?&]page=(\d+)', r'/page/(\d+)/', r'[?&]p=(\d+)'):
            for m in re.finditer(rx, h):
                try:
                    n = int(m.group(1))
                    if n > mx:
                        mx = n
                except Exception:
                    pass
        if re.search(r'下一页|next page|class="[^"]*next[^"]*"|rel="next"', h, re.I):
            mx = max(mx, cur + 1)
        return mx

    # ========== 88测试版通用工具(_tget/_tset/_pid/_pres/_safe/_dig/_card/_plist/_pgc) ==========

    def _tget(self, key, ttl):
        v = self._ttl.get(key)
        if v and time.time() - v[0] < ttl:
            return v[1]
        return None

    def _tset(self, key, val):
        self._ttl[key] = [time.time(), val]
        return val
    def _reg_fix(self):
        """88-11搜索开关自开: registry里匹配条目 searchable/quickSearch 置1(App重启后生效)"""
        kw = (REG_MATCH or '').strip().lower()
        p = '/sdcard/TV/CustomCsp/registry.json'
        try:
            raw = open(p).read()
            d = json.loads(raw)
        except Exception:
            _log('88-11 registry读取失败 %s' % p)
            return 0
        n = 0
        for it in d.get('items', []):
            if kw and kw not in ('%s %s' % (it.get('name') or '', it.get('api') or '')).lower():
                continue
            st = it.get('site') if isinstance(it.get('site'), dict) else {}
            if it.get('searchable') == 1 and it.get('quickSearch') == 1 and (not st or (st.get('searchable') == 1 and st.get('quickSearch') == 1)):
                continue
            it['searchable'] = 1
            it['quickSearch'] = 1
            if st:
                st['searchable'] = 1
                st['quickSearch'] = 1
            n += 1
        if not n:
            return 0
        try:
            json.dump(d, open(p, 'w'), ensure_ascii=False, indent=1)
            open(p + '.src_bak', 'w').write(raw)
            _log('88-11 registry搜索开关自开: 匹配[%s] 共%d条' % (kw or 'ALL', n))
        except Exception:
            _log('88-11 registry写入失败')
        return n
    def _pid(self, sid):
        s = str(sid or '').strip()
        if '$$$' in s:
            s = s.split('$$$', 1)[0]
        if '$' in s:
            a, b = s.split('$', 1)[1], s.rsplit('$', 1)[-1]
            s = b if ('://' in b or b.startswith('/')) else a
        if '#' in s and '://' not in s.split('#', 1)[0] and not s.split('#', 1)[1].startswith('/'):
            s = s.split('#', 1)[0]
        return s

    def _pres(self, url, ref=None):
        hd = {'Referer': ref if ref is not None else self.ref}
        return {'parse': 0, 'url': url or '', 'header': hd, 'user_agent': self.ua}

    def _pres_parse(self, url):
        return {'parse': 1, 'url': url or '', 'header': {'Referer': self.ref, 'User-Agent': self.ua},
                'user_agent': self.ua, 'playUrl': ''}

    def _safe(self, s):
        return str(s or '').replace('#', '-').replace('$', '|')

    def _dig(self, obj, *keys):
        cur = obj
        for k in keys:
            if isinstance(cur, dict):
                cur = cur.get(k)
            elif isinstance(cur, list) and isinstance(k, int) and 0 <= k < len(cur):
                cur = cur[k]
            else:
                return None
        return cur

    def _card(self, it):
        if not isinstance(it, dict):
            return None
        vid = it.get('id') or it.get('videoId') or it.get('vid') or it.get('video_id')
        name = it.get('name') or it.get('title') or it.get('videoName') or it.get('showName')
        if vid is None and name is None:
            return None
        return {
            'vod_id': str(vid if vid is not None else name),
            'vod_name': str(name or ''),
            'vod_pic': str(it.get('cover') or it.get('pic') or it.get('image') or it.get('poster') or ''),
            'vod_remarks': str(it.get('remark') or it.get('status') or it.get('updateInfo') or it.get('subTitle') or '')
        }

    def _plist(self, d):
        for path in (('data', 'list'), ('data', 'records'), ('data', 'items'), ('data', 'rows'),
                     ('data',), ('list',), ('records',), ('items',)):
            v = self._dig(d, *path)
            if isinstance(v, list):
                return v
        return []

    def _pgc(self, n, pn, total=None, size=None):
        size = size or PAGE_SIZE
        try:
            t = int(total)
        except Exception:
            t = 0
        if t > 0:
            return max((t + size - 1) // size, pn)
        return (pn + 1) if n >= size else pn

    # ========== ★88-9 翻页续读族(单飞去重+游标+补读簿+判死+去重环; 出处cuct v13攻坚·2026-09-15) ==========
    def _single(self, key, fn, timeout=20):
        with self._lock:
            f = self._inflight.get(key)
            own = f is None
            if own:
                f = self._inflight[key] = Future()
        if not own:
            try:
                return f.result(timeout=timeout)
            except Exception:
                return None
        v = None
        try:
            v = fn()
        except Exception:
            pass
        try:
            f.set_result(v)
        except Exception:
            pass
        with self._lock:
            if self._inflight.get(key) is f:
                del self._inflight[key]
        return v

    def _nextpg(self, key, dflt=1):
        v = self._tget('cur:' + key, CURSOR_TTL)
        try:
            return int(v)
        except Exception:
            return dflt

    def _advc(self, key, used):
        try:
            used = int(used) + 1
        except Exception:
            return
        with self._lock:
            try:
                old = self._tget('cur:' + key, CURSOR_TTL)
                if old is not None and int(old) >= used:
                    return
            except Exception:
                pass
            self._tset('cur:' + key, used)

    def _hold_add(self, kc, pg):
        try:
            pg = int(pg)
        except Exception:
            return
        if pg <= 0:
            return
        with self._lock:
            hk = 'hold:' + kc
            h = self._tget(hk, HOLD_TTL)
            if not isinstance(h, dict):
                h = {}
            if pg in h or len(h) >= HOLD_MAX:
                return
            h[pg] = [0, time.time(), time.time()]
            self._tset(hk, h)

    def _hold_try(self, kc, ff, budget=1):
        hk = 'hold:' + kc
        h = self._tget(hk, HOLD_TTL)
        if not isinstance(h, dict) or not h:
            return None
        try:
            budget = max(int(budget or 1), 1)
        except Exception:
            budget = 1
        for pg in sorted(h.keys())[:budget]:
            r = self._single('pg:%s:%s' % (kc, pg), lambda p=pg: ff(p), timeout=12)
            items, pc = (r[0], r[1]) if isinstance(r, (list, tuple)) and len(r) == 2 else (r, 0)
            try:
                pc = int(pc or 0)
            except Exception:
                pc = 0
            if items:
                with self._lock:
                    h = self._tget(hk, HOLD_TTL) or {}
                    h.pop(pg, None)
                    self._tset(hk, h)
                _log('88-9补读回来 %s pg=%s' % (kc, pg))
                return items, pg
            with self._lock:
                h = self._tget(hk, HOLD_TTL) or {}
                ent = h.get(pg) or [0, time.time(), time.time()]
                ent[0] = int(ent[0]) + 1
                ent[2] = time.time()
                if 0 < pc <= pg:
                    h.pop(pg, None)
                elif ent[0] >= HOLD_FAILS and (time.time() - ent[1]) >= HOLD_SPAN:
                    h.pop(pg, None)
                    _log('88-9判死(真洞) %s pg=%s' % (kc, pg))
                else:
                    h[pg] = ent
                self._tset(hk, h)
        return None

    def _rcget(self, kc, start, ff, probe=None):
        try:
            start = int(start)
        except Exception:
            start = 1
        if start <= 0:
            start = 1
        try:
            probe = PROBE_MAX if probe is None else int(probe)
        except Exception:
            probe = PROBE_MAX
        c = self._tget('pf:%s:%s' % (kc, start), 300)
        if isinstance(c, list) and c:
            return list(c), start
        items, pc, served, used = None, 0, 0, start
        for off in (0,) + tuple(range(1, probe + 1)):
            pg = start + off
            used = pg
            r = self._single('pg:%s:%s' % (kc, pg), lambda p=pg: ff(p), timeout=12)
            items, pc = (r[0], r[1]) if isinstance(r, (list, tuple)) and len(r) == 2 else (r, 0)
            try:
                pc = int(pc or 0)
            except Exception:
                pc = 0
            if items:
                served = pg
                break
            if 0 < pc <= pg:
                return None, pg
            time.sleep(LADDER_SLEEP)
        if served:
            for pg in range(start, served):
                self._hold_add(kc, pg)
            return list(items), served
        for pg in range(start, used + 1):
            self._hold_add(kc, pg)
        return None, used

    def _seen_merge(self, kc, items):
        if not items:
            return []
        sk = 'seen:' + kc
        with self._lock:
            s = list(self._tget(sk, CURSOR_TTL) or [])
            out = []
            for it in items:
                try:
                    vid = str(it.get('vod_id')) if isinstance(it, dict) else str(it)
                except Exception:
                    vid = str(it)
                if vid in s:
                    continue
                s.append(vid)
                out.append(it)
            if len(s) > SEEN_CAP:
                s = s[-SEEN_CAP:]
            self._tset(sk, s)
        return out

    def _warm_next(self, kc, ff, delay=0.6):
        if not WARM:
            return

        def run():
            try:
                time.sleep(delay)
                r = self._hold_try(kc, ff, budget=1)
                if r:
                    self._tset('bf:' + kc, r)
                np = self._nextpg(kc, 0)
                try:
                    np = int(np)
                except Exception:
                    np = 0
                if np > 0 and not self._tget('pf:%s:%s' % (kc, np), 240):
                    rr = self._single('pg:%s:%s' % (kc, np), lambda p=np: ff(p), timeout=20)
                    it2 = rr[0] if isinstance(rr, (list, tuple)) and len(rr) == 2 else rr
                    if it2:
                        self._tset('pf:%s:%s' % (kc, np), list(it2))
            except Exception:
                pass
        try:
            threading.Thread(target=run, daemon=True).start()
        except Exception:
            pass




    # ========== ★88-10 三段续读(详情/搜索/播放容错续读; 复用⑨单飞+负缓存基建) ==========
    def _rty(self, key, fn, waits=(0, 0.45, 1.2), ttl=None):
        try:
            ttl = MISS_TTL if ttl is None else int(ttl)
        except Exception:
            ttl = 60
        if self._tget('mm:' + key, ttl):
            return None
        r = None
        for w in waits:
            try:
                if w:
                    time.sleep(w)
            except Exception:
                pass
            r = self._single(key, fn, timeout=25)
            if r:
                break
        if r:
            self._tset('mm:' + key, None)
            return r
        self._tset('mm:' + key, 1)
        _log('88-10续读梯尽 %s' % key[:80])
        return None

    def _li_mem(self, items):
        if not items:
            return items
        try:
            with self._lock:
                db = self._tget('li:db', CURSOR_TTL) or {}
                for it in items:
                    try:
                        vid = str(it.get('vod_id') or '')
                    except Exception:
                        continue
                    if not vid:
                        continue
                    db[vid] = {'vod_name': str(it.get('vod_name') or ''), 'vod_pic': str(it.get('vod_pic') or ''), 'vod_remarks': str(it.get('vod_remarks') or '')}
                if len(db) > LI_CAP:
                    for k in list(db.keys())[:len(db) - LI_CAP]:
                        db.pop(k, None)
                self._tset('li:db', db)
        except Exception:
            pass
        return items

    def _li_get(self, vid):
        db = self._tget('li:db', CURSOR_TTL) or {}
        try:
            return db.get(str(vid))
        except Exception:
            return None

    def _minstruct(self, vid):
        li = self._li_get(vid)
        if not isinstance(li, dict) or not li.get('vod_name'):
            return None
        return {'vod_id': str(vid), 'vod_name': li.get('vod_name') or '', 'vod_pic': li.get('vod_pic') or '',
                'vod_content': '', 'vod_remarks': li.get('vod_remarks') or '', 'vod_play_from': '', 'vod_play_url': ''}

    def _sbl_on(self, k):
        self._tset('sb:' + str(k), 1)

    def _sbl_bad(self, k):
        return bool(self._tget('sb:' + str(k), 600))

    def _gather(self, gkey, tasks, workers=8, budget=None):
        out = {}
        if not tasks:
            return out
        try:
            budget = GATHER_BUDGET if budget is None else float(budget)
        except Exception:
            budget = 8.0
        ex, fmap = None, {}
        try:
            ex = ThreadPoolExecutor(max_workers=max(1, min(workers, len(tasks))))
            for tag, fn in tasks:
                fmap[ex.submit(self._rty, 'gt:%s:%s' % (gkey, tag), fn, (0, 0.45))] = tag
        except Exception:
            pass
        try:
            for fut in as_completed(list(fmap.keys()), timeout=budget):
                try:
                    r = fut.result()
                except Exception:
                    r = None
                if r:
                    out[fmap.get(fut)] = r
        except Exception:
            pass
        for fut, tag in list(fmap.items()):
            if tag in out:
                continue
            def _late(ff, _t=tag):
                try:
                    r = ff.result()
                except Exception:
                    r = None
                if not r:
                    return
                try:
                    with self._lock:
                        d = self._tget('late:' + gkey, 600) or {}
                        d[_t] = r
                        self._tset('late:' + gkey, d)
                except Exception:
                    pass
            if fut.done():
                _late(fut)
            else:
                fut.add_done_callback(_late)
        try:
            if ex:
                ex.shutdown(wait=False)
        except Exception:
            pass
        return out


    # ========== 首页 ==========
    def homeContent(self, filter=False):
        ck = 'home:%d' % (1 if filter else 0)
        c = self._tget(ck, TTL_HOME)
        if c:
            return c
        r = {'class': [{'type_id': k, 'type_name': v} for k, v in self.types.items()]}
        if filter and self.filters:
            r['filters'] = self.filters
        r['list'] = self.homeVideoContent().get('list', [])
        if r.get('list'):
            return self._tset(ck, r)
        return r

    def homeVideoContent(self):
        c = self._tget('home:list', TTL_HOME)
        if c is not None:
            return c
        h, _u = self._first('home', self._cands('home', 'latest', 1), ttl=TTL_HOME)
        items = self._items(h) if h else []
        self._li_mem(items)
        _log('home %s items=%d' % (_u or 'NONE', len(items)))
        r = {'list': items[:PAGE_SIZE]}
        if items:
            return self._tset('home:list', r)
        return r

    # ========== 分类(1/2/3级展平+筛选+动态翻页) ==========
    def categoryContent(self, tid, pg=1, filter=False, extend=''):
        try:
            pn = max(int(str(pg)), 1)
        except Exception:
            pn = 1
        t, cls, ex2 = str(tid), '', ''
        if '|' in t:
            p = t.split('|')
            t, cls = p[0], p[1] if len(p) > 1 else ''
            ex2 = p[2] if len(p) > 2 else ''
        ex = {}
        if extend:
            try:
                ex = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ex = {}
        if not CONT:
            h = self._get(self._cat_url(t, pn, cls, ex2, ex))
            if not h:
                return {'page': pn, 'pagecount': 1, 'limit': 42, 'total': 0, 'list': []}
            items = self._items(h)
            self._li_mem(items)
            return {'page': pn, 'pagecount': self._pagecount(h, pn), 'limit': 42, 'total': len(items), 'list': items}
        kc = '%s:%s' % (t, cls)
        if pn <= 1:
            self._tset('seen:' + kc, [])
            self._tset('cur:' + kc, 1)
            self._tset('pf:%s:1' % kc, None)
        elif self._tget('cur:' + kc, CURSOR_TTL) is None:
            self._tset('seen:' + kc, [])
        ff = lambda p: self._cat_fetch(t, cls, ex2, ex, p)
        start = pn if pn > 1 else 1
        it2, used = self._rcget(kc, start, ff)
        self._advc(kc, used)
        if pn > 1:
            _m9 = self._seen_merge(kc, it2 or [])
            items = _m9 if (_m9 or not it2) else (it2 or [])
        else:
            items = self._seen_merge(kc, it2 or [])
        rb = self._tget('bf:' + kc, 1800)
        if rb:
            self._tset('bf:' + kc, None)
        bf = self._seen_merge(kc, rb[0] if isinstance(rb, tuple) and rb[0] else [])
        if bf:
            items = (bf + items) if BF_POS else (items + bf)
        if items:
            self._li_mem(items)
            self._warm_next(kc, ff)
        try:
            pcv = int(self._tget('pcm:' + kc, 3600) or 0)
        except Exception:
            pcv = 0
        pcout = max(pn + 1, pcv) if items else ((pn + 1) if pcv > pn else pn)
        return {'page': pn, 'pagecount': pcout, 'limit': PAGE_SIZE, 'total': len(items), 'list': items}

    def _cat_fetch(self, t, cls, ex2, ex, pn):
        # ★88-9 站点级单页取数(派生源按站实现); 约定返回 (items, pagecount)
        h, _u = self._first('c:' + str(t), self._cands('cat', t, pn)[:1], ttl=1800)
        kc = '%s:%s' % (t, cls)
        if not h:
            self._tset('pcm:' + kc, 0)
            return [], 0
        pc = self._pagecount(h, pn)
        self._tset('pcm:' + kc, pc)
        items = self._items(h)
        if not items:
            return [], pc
        return items, pc


    def _cat_url(self, t, pn, cls='', ex2='', ex=None):
        u = self._cands('cat', t, pn)
        return u[0] if u else self.base

    def _cands(self, kind, t, pn=1):
        b, s = self.base, str(t or '')
        try:
            p = max(1, int(pn or 1))
        except Exception:
            p = 1
        if kind == 'home':
            return [b + '/latest-updates/', b + '/', b + '/videos/', b + '/new/']
        if kind == 'search':
            q = quote(s)
            if p <= 1:
                return [b + '/?s=' + q, b + '/search/' + q + '/', b + '/?s=' + q + '&paged=1',
                        b + '/search?text=' + q + '&p=1']
            return [b + '/search/' + q + '/page/%d/' % p, b + '/?s=' + q + '&paged=%d' % p,
                    b + '/?s=' + q + '&page=%d' % p, b + '/search/' + q + '/page/%d' % p]
        pg2 = '' if p <= 1 else 'page/%d/' % p
        if s in ('', 'latest', 'new', 'home'):
            return [b + '/', b + '/v37/category/censored/' + pg2, b + '/page/%d/' % p]
        out = []

        def _add(u):
            if u and u not in out:
                out.append(u)
        if s.startswith('/'):
            _add(b + s.rstrip('/') + '/' + pg2)
        else:
            pth = (self._catmap or {}).get(s, '') or CAT_PATH.get(s, '')
            if pth:
                _add(b + pth.rstrip('/') + '/' + pg2)
            _add(b + '/v37/category/%s/' % s + pg2)
            _add(b + '/category/%s/' % s + pg2)
            _add(b + '/%s/' % s + pg2)
            _add(b + '/v37/category/%s/page/%d/' % (s, p))
        return out or [b + '/']

    def _first(self, key, urls, ttl=86400):
        c = self._tget('sh:' + key, ttl)
        if c is not None:
            try:
                i = int(c)
            except Exception:
                i = -1
            if 0 <= i < len(urls):
                h = self._get(urls[i])
                if h and self._items(h):
                    return h, urls[i]
        if self._tget('shf:' + key, 3600) and len(urls) > 1:
            urls = urls[:1]
        last = ''
        for i, u in enumerate(urls):
            h = self._get(u)
            if h:
                last = h
            if h and self._items(h):
                self._tset('sh:' + key, i)
                self._tset('shf:' + key, None)
                return h, u
        self._tset('shf:' + key, 1)
        if last:
            return last, (urls[0] if urls else '')
        return '', ''

    # ========== 详情(多线路 + probe实测排序) ==========
    def detailContent(self, ids, quick='1'):
        vid = str(ids[0] if isinstance(ids, list) else ids or '').strip()
        if not vid:
            return {'list': []}
        c = self._tget('d:' + vid, TTL_DETAIL)
        if c:
            return c
        h, _u = self._first('d:' + vid, self._dcands(vid), ttl=TTL_DETAIL)
        if not h:
            _log('detail miss %s' % vid)
            v = self._minstruct(vid) or {'vod_id': vid, 'vod_name': vid, 'vod_pic': '', 'vod_year': '', 'vod_area': '',
                                         'vod_class': '', 'vod_director': '', 'vod_actor': '', 'vod_content': '', 'vod_remarks': ''}
            v['vod_play_from'] = v.get('vod_play_from') or '线路1'
            v['vod_play_url'] = v.get('vod_play_url') or ('1$' + vid)
            return {'list': [v]}
        _idx = ('video-id="' not in h) and (('/pornstar/' in vid) or ('/studio/' in vid) or (len(re.findall(r'/video/', h)) >= 8))
        if _idx:
            _eps, _es = [], set()
            for _m in re.finditer(r'<a[^>]+href="(https?://[^"]+?/video/[^"]+)"', h, re.I):
                _u2 = _m.group(1)
                if _u2 in _es:
                    continue
                _es.add(_u2)
                _eps.append('%02d$%s' % (len(_eps) + 1, _u2))
                if len(_eps) >= 80:
                    break
            if len(_eps) >= 2:
                _t2 = re.search(r'<title>(.*?)</title>', h, re.I)
                _p2 = re.search(r'og:image"[^>]+content="([^"]+)"', h, re.I) or re.search(r'<img[^>]+data-lazy-src="([^"]+)"', h, re.I)
                _d2 = {'vod_id': vid, 'vod_name': (re.sub(r'<[^>]+>', '', _t2.group(1)).strip()[:140] if _t2 else vid),
                       'vod_pic': self._pic(_p2.group(1) if _p2 else ''), 'vod_year': '', 'vod_area': '', 'vod_class': '',
                       'vod_director': '', 'vod_actor': '', 'vod_content': '', 'vod_remarks': '%d部' % len(_eps),
                       'vod_play_from': '作品', 'vod_play_url': '#'.join(_eps)}
                _log('detail idx %s eps=%d' % (vid, len(_eps)))
                return self._tset('d:' + vid, {'list': [_d2]})
        d = {'vod_id': vid, 'vod_name': '', 'vod_pic': '', 'vod_year': '', 'vod_area': '',
             'vod_class': '', 'vod_director': '', 'vod_actor': '', 'vod_content': '',
             'vod_remarks': '', 'vod_play_from': '', 'vod_play_url': ''}
        tn = re.search(r'og:title"[^>]+content="([^"]*)"', h, re.I) or \
            re.search(r'<h1[^>]*>([\s\S]{0,200}?)</h1>', h, re.I) or \
            re.search(r'<title>(.*?)</title>', h, re.I)
        if tn:
            d['vod_name'] = re.sub(r'<[^>]+>', '', tn.group(1)).strip()[:140]
        p = re.search(r'og:image"[^>]+content="(https?://[^"]+)"', h, re.I) or \
            re.search(r'<video[^>]+poster="([^"]+)"', h, re.I) or \
            re.search(r'<img[^>]+(?:data-src|data-original|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I)
        if p:
            d['vod_pic'] = self._pic(p.group(1))
        dm = re.search(r'og:description"[^>]+content="([^"]*)"', h, re.I) or \
            re.search(r'name="description"[^>]+content="([^"]*)"', h, re.I)
        if dm:
            d['vod_content'] = re.sub(r'\s+', ' ', dm.group(1)).strip()[:500]
        cl = re.findall(r'/(?:categories|category|tags?)/([a-z0-9\-]+)/?["\']', h, re.I) or re.findall(r'/v\d+/category/([a-z0-9\-]+)', h, re.I)
        if cl:
            d['vod_class'] = ','.join(list(dict.fromkeys(cl))[:6])
        _du = re.search(r'itemprop="duration"[^>]+content="P(?:\d+D)?T?(?:\d+H)?(\d+)M', h)
        if _du:
            d['vod_remarks'] = '%s:%s' % (_du.group(1), '00')
        _s0 = self._sources(h)
        _bu = _u or (self._dcands(vid) or [''])[0]
        srcs = [_bu] if 'video-id="' in h else (_s0 or [_bu])
        if srcs and srcs[0]:
            fs, us = [], []
            for i, s2 in enumerate(srcs[:6]):
                if '.m3u8' in s2:
                    lab = 'HLS' if i == 0 else 'HLS%d' % (i + 1)
                elif '.mp4' in s2:
                    lab = 'MP4' if i == 0 else 'MP4%d' % (i + 1)
                else:
                    lab = '线路%d' % (i + 1)
                fs.append(lab)
                us.append('1$' + s2)
            if PROBE and len(fs) > 1 and not any('|' in x for x in us):
                f2, u2 = self._sort_lines(fs, us)
                fs, us = f2, u2
            d['vod_play_from'] = '$$$'.join(fs)
            d['vod_play_url'] = '$$$'.join(us)
        return self._tset('d:' + vid, {'list': [d]})

    def _dcands(self, vid):
        if vid.startswith('http'):
            out = [vid]
            v2 = re.sub(r'^(https?://[^/]+)/v\d+/', r'\1/', vid)
            if v2 != vid:
                out.append(v2)
            return out
        if vid.startswith('/'):
            out = [urljoin(self.base, vid)]
            v2 = re.sub(r'^(https?://[^/]+)/v\d+/', r'\1/', out[0])
            if v2 != out[0]:
                out.append(v2)
            return out
        b, s = self.base, vid.strip('/')
        if '/' in s:
            return [b + '/' + s + '/', b + '/' + s]
        return [b + '/video/%s/' % s, b + '/%s/' % s, b + '/%s.html' % s, b + '/?p=%s' % s]

    def _sources(self, h):
        out, seen = [], set()
        try:
            _mk = re.findall(r'data-(mpu|link)="([A-Za-z0-9+/=]{32,})"', h or '')
            _kk = [v for n, v in sorted(_mk, key=lambda x: 0 if x[0] == 'mpu' else 1)]
            if not _kk:
                _kk = re.findall(r'data-blk="([A-Za-z0-9+/=]{32,})"', h or '')
            _see, _out = set(), []
            for _v in _kk:
                if _v not in _see:
                    _see.add(_v)
                    _out.append(_v)
            self._tok = _out
            self._tok2 = _out
        except Exception:
            self._tok = []
            self._tok2 = []
        bad = ('ads', 'doubleclick', 'googlesyndication', 'analytics', '.gif', 'preview.mp4',
               'trailer', 'sample.mp4', '/static/', 'poster.', 'exoclick',
               'exosrv', 'exdynsrv', 'juicyads', 'adspy', 'trafficjunky', 'adtng', 'pemsrv',
               'tsyndicate', 'recreativ', 'adsterra', 'propellerads', 'clickadu', 'popads', 'onclickads')
        pats = (r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                r'["\'](?:videoUrl|video_url|videoSrc|contentUrl|hls|source|src|url)["\']\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                r'<source[^>]+src="([^"]+\.(?:m3u8|mp4)[^"]*)"',
                r'<video[^>]+src="([^"]+\.(?:m3u8|mp4)[^"]*)"',
                r'data-(?:src|video|url)="([^"]+\.(?:m3u8|mp4)[^"]*)"')
        for rx in pats:
            for m in re.finditer(rx, h, re.I):
                u = m.group(1)
                if u.startswith('//'):
                    u = 'https:' + u
                if not u.startswith('http'):
                    continue
                if u not in seen and not any(b in u.lower() for b in bad):
                    seen.add(u)
                    out.append(u)
        if not out:
            for m in re.finditer(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4))', h, re.I):
                u = m.group(1)
                if u not in seen and not any(b in u.lower() for b in bad):
                    seen.add(u)
                    out.append(u)
        if not out:
            for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', h, re.I):
                u = m.group(1)
                if u.startswith('//'):
                    u = 'https:' + u
                elif u.startswith('/'):
                    u = urljoin(self.base, u)
                if u.startswith('http') and u not in seen and not any(_b in u.lower() for _b in ('ads', 'exoclick', 'exosrv', 'juicyads', 'doubleclick', 'googlesyndication', 'adsterra', 'onclickads', 'trafficjunky')):
                    seen.add(u)
                    out.append(u)
        return out

    def _play_sources(self, h):
        pf, pu = [], []
        pp = h.find('id="playlist"')
        head = h[max(0, pp - 3000):pp] if pp > 0 else h
        names = []
        for t in re.findall(r'<(?:li|span|a|div)[^>]*class="[^"]*(?:module-tab-item|tab-item|swiper-slide|nav-tabs)[^"]*"[^>]*>([\s\S]*?)</(?:li|span|a|div)>', head):
            c = re.sub(r'<[^>]+>', '', t).strip()
            if c and '排序' not in c and '报错' not in c and '选集' not in c and len(c) < 20:
                names.append(c)
        uls = re.findall(r'<ul[^>]*>([\s\S]*?)</ul>', h[pp:] if pp > 0 else '')
        for i, ul in enumerate(uls):
            links = re.findall(r'href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>', ul)
            if links:
                pf.append(names[i] if i < len(names) else ('正片' if i == 0 else f'线路{i + 1}'))
                pu.append('#'.join(f'{self._safe(ep.strip())}${urljoin(self.base, href)}' for href, ep in links))
        if not pf:  # 兜底: 全局按线路分组
            routes = {}
            for href, route, ep in re.findall(r'href="(/vodplay/\d+-(\d+)-\d+\.html)"[^>]*>([^<]+)</a>', h):
                routes.setdefault(route, []).append(f'{self._safe(ep.strip())}${urljoin(self.base, href)}')
            for i, route in enumerate(sorted(routes.keys(), key=lambda x: int(x) if x.isdigit() else 999)):
                pf.append(names[i] if i < len(names) else f'线路{i + 1}')
                pu.append('#'.join(routes[route]))
        return pf, pu

    def _sort_lines(self, froms, urls):
        key = hashlib.md5('|'.join(froms).encode()).hexdigest()
        c = self._pc.get(key)
        if c and time.time() - c[0] < 300:
            return c[1], c[2]
        def probe(i):
            u = urls[i].split('#')[0].rsplit('$', 1)[-1]
            try:
                r = requests.head(urljoin(self.base, u), headers={'User-Agent': self.ua}, timeout=5)
                return 0 if r.status_code < 400 else 1
            except Exception:
                return 1
        with ThreadPoolExecutor(max_workers=min(len(froms), 8)) as ex:
            res = list(ex.map(probe, range(len(froms))))
        pairs = sorted(zip(froms, urls, res), key=lambda x: x[2])
        out = ([p[0] for p in pairs], [p[1] for p in pairs])
        self._pc[key] = [time.time()] + list(out)
        return out

    # ========== 搜索 ==========
    def searchContent(self, key, quick=False, pg='1'):
        try:
            pn = max(int(str(pg)), 1)
        except Exception:
            pn = 1
        kw = str(key or '').strip()
        if not kw:
            return {'list': [], 'page': pn, 'pagecount': 1}
        ck = 'sq:%s:%s' % (kw, pn)
        c = self._tget(ck, 300)
        if c:
            return c
        h, _u = self._first('s:' + kw, self._cands('search', kw, pn), ttl=600)
        if not h:
            return {'list': [], 'page': pn, 'pagecount': 1}
        if pn <= 1:
            self._tset('seen:sq:' + kw, [])
        items = self._seen_merge('sq:' + kw, self._items(h))
        self._li_mem(items)
        _log('search %s p%d %s n=%d' % (kw, pn, _u or 'NONE', len(items)))
        r = {'list': items, 'page': pn, 'pagecount': self._pagecount(h, pn)}
        if items:
            return self._tset(ck, r)
        return r

    # ========== 播放: 直连优先 → 解密 → VIP插槽 ==========
    def playerContent(self, flag, id, vipFlags=None):
        raw = str(id) if id else str(flag)
        ck = 'p:' + raw
        c = self._tget(ck, TTL_PLAY)
        if c:
            return c
        _ti = None
        if '|' in raw:
            _rp = raw.rsplit('|', 1)
            if _rp[1].isdigit():
                _ti = int(_rp[1])
                raw = _rp[0]
        url = self._pid(raw)
        _pv = self._tget('pm:' + str(url), TTL_PLAY) if url else None
        if _pv:
            return self._tset(ck, self._pres(_pv))
        if '://' in url and re.search(r'\.(m3u8|mp4|flv|mp3)(\?|$)', url, re.I):
            _log('play direct %s' % url[:90])
            return self._tset(ck, self._pres(url))  # 直连
        full = url if url.startswith('http') else urljoin(self.base, url)
        _w8 = (0,) if self._cf_skip else (0, 0.4, 1.0)
        h = self._rty('pl:%s' % raw, lambda: (self._get(full) or ((self._gget(full) if self.cf else '') if not self._cf_skip else '')), _w8)
        if h and not re.search(r'video-id', h):
            _h2 = self._uget(full, self.ref)
            if _h2 and re.search(r'video-id', _h2):
                _log('urllib page ok %d' % len(_h2))
                h = _h2
        if not h:
            _log('play miss %s' % raw[:90])
            return self._pres('')
        _gi = bool(re.search(r'video-id|data-(?:mpu|link|blk)="[A-Za-z0-9+/=_-]{32,}"|videoId|video_id', h))
        if not _gi:
            self._dump_html(h, full, 'nogate')
        u = self._bjp_play(h, full, ti=_ti) if _gi else ''
        if not u:
            u = self._parse_play(h, full)
        if not u:
            u = self._wv_play(full)
        if not u:
            u = self._vip_try(full, h, vipFlags)  # 会员: 能破则破, 服务端硬锁放弃
        if u and u.startswith('http') and re.search(r'\.(m3u8|mp4|flv|txt)(\?|$)', u, re.I):
            _log('play ok %s' % u[:90])
            return self._tset(ck, self._pres(u))
        _log('play parse %s toc=%d' % (raw[:80], len(self._tok or [])))
        return self._tset(ck, self._pres_parse(u if str(u or '').startswith('http') else full))

    def _parse_play(self, h, page_url, _dep=0):
        s = [] if re.search(r'video-id', h or '') else self._sources(h)
        if s:
            return s[0]
        m = re.search(r'var\s*(?:now|url|videoSrc|video_url|videoUrl)\s*=\s*["\']([^"\']+)["\']', h)
        if m:
            u2 = self._dec(m.group(1), page_url)
            if u2:
                return u2
        if _dep < 2:
            for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', h, re.I):
                u = m.group(1)
                if u.startswith('//'):
                    u = 'https:' + u
                elif u.startswith('/'):
                    u = urljoin(self.base, u)
                if not u.startswith('http') or any(_b in u.lower() for _b in ('ads', 'exoclick', 'exosrv', 'juicyads', 'doubleclick', 'googlesyndication', 'adsterra', 'onclickads', 'trafficjunky')):
                    continue
                h2 = self._gget(u) if self.cf else self._get(u)
                if h2:
                    r = self._parse_play(h2, u, _dep + 1)
                    if r:
                        return r
        return ''

    def _dec(self, u, page_url):
        u = u.strip()
        if re.search(r'\.(m3u8|mp4|flv)(\?|$)', u, re.I):
            return u
        try:  # base64
            s = u.encode()
            s2 = base64.b64decode(s + b'=' * (-len(s) % 4)).decode('utf-8', 'ignore')
            if re.search(r'\.(m3u8|mp4|flv)(\?|$)', s2, re.I):
                return s2
        except Exception:
            pass
        # ★ AES-CBC 解密插槽: aes_cbc(base64.b64decode(s2), key, iv, 0)
        return u if u.startswith('http') else ''

    def _uget(self, url, ref=None, timeout=12):
        try:
            hd = {'User-Agent': self.ua, 'Referer': ref or self.ref,
                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                  'Accept-Language': 'en-US,en;q=0.9', 'Upgrade-Insecure-Requests': '1',
                  'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none'}
            if self.cf:
                try:
                    ckh = self.cf.cookie_header()
                    if ckh:
                        hd['Cookie'] = ckh
                except Exception:
                    pass
            return urllib.request.urlopen(urllib.request.Request(url, headers=hd), timeout=timeout).read().decode('utf-8', 'ignore') or ''
        except Exception:
            return ''

    def _wv_play(self, page_url, timeout=20):
        if not (self.cf and not self._cf_skip):
            return ''
        js = ("(function(){var v=document.querySelector('video');"
              "var u=(v&&(v.currentSrc||v.src))||'';"
              "if(!u){var s=document.querySelector('source');u=(s&&s.src)||'';}"
              "if(!u){var f=document.querySelector('iframe');u=(f&&f.src)||'';}"
              "return u||'';})()")
        try:
            r = self.cf.wv_html(page_url, timeout=timeout, ua=(CF_WVUA or self.ua), js=js)
        except Exception:
            r = ''
        if not r:
            return ''
        r = str(r).strip().strip('"')
        if r.startswith('//'):
            r = 'https:' + r
        if not r.startswith('http') or any(_b in r.lower() for _b in ('ads', 'exoclick', 'doubleclick', 'googlesyndication', 'Top_Banner', '/static/')):
            return ''
        _log('wv-play %s' % r[:90])
        return r

    def _dump_html(self, h, url, tag):
        if not DEBUG:
            return
        try:
            p = '/sdcard/bjp_html_%s.txt' % tag
            open(p, 'w').write('URL=%s LEN=%d NVID=%s\n' % (url, len(h or ''), 'video-id' in (h or '')) + (h or '')[:80000])
            _log('dump %s %s' % (tag, p))
        except Exception:
            pass

    def _cfish(self, t):
        return bool(t) and ('Just a moment' in t or 'cf-chl' in t or 'challenge-platform' in t or '_cf_chl' in t)

    def _post(self, url, data, headers=None, timeout=20):
        hd = dict(headers) if headers else {}
        hd.setdefault('User-Agent', self.ua)
        hd.setdefault('Referer', self.ref)
        hd.setdefault('Origin', self.base)
        hd.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
        hd.setdefault('X-Requested-With', 'XMLHttpRequest')
        hd.setdefault('Accept', 'application/json, text/javascript, */*; q=0.01')
        hd.setdefault('Accept-Language', 'en-US,en;q=0.9')
        hd.setdefault('Sec-Fetch-Site', 'same-origin')
        hd.setdefault('Sec-Fetch-Mode', 'cors')
        hd.setdefault('Sec-Fetch-Dest', 'empty')
        if self.cf:
            try:
                ckh = self.cf.cookie_header()
                if ckh and not any(str(k).lower() == 'cookie' for k in hd):
                    hd['Cookie'] = ckh
            except Exception:
                pass
        _bd = urllib.parse.urlencode(data).encode()
        try:
            rq = urllib.request.Request(url, data=_bd, headers=hd)
            _t0 = urllib.request.urlopen(rq, timeout=timeout).read().decode('utf-8', 'ignore') or ''
            if _t0 and not self._cfish(_t0):
                return _t0
            if _t0 and self.cf and not self._cf_skip:
                self._gget(self.base)
                try:
                    _ck = self.cf.cookie_header() or ''
                except Exception:
                    _ck = ''
                if _ck:
                    hd['Cookie'] = _ck
                    rq = urllib.request.Request(url, data=_bd, headers=hd)
                    try:
                        _t1 = urllib.request.urlopen(rq, timeout=timeout).read().decode('utf-8', 'ignore') or ''
                    except Exception:
                        _t1 = ''
                    if _t1 and not self._cfish(_t1):
                        return _t1
                    _t0 = _t1 or _t0
            return _t0
        except Exception:
            pass
        try:
            r = requests.post(url, data=data, headers=hd, timeout=timeout)
            r.encoding = 'utf-8'
            return r.text or ''
        except Exception:
            return ''

    def _bjp_play(self, h, page_url, ti=None):
        h = h or ''
        vid = ''
        m = re.search(r'video-id="(\d+)"', h)
        if m:
            vid = m.group(1)
        if not vid:
            m = re.search(r'video-id[\'"]?\s*[:=]\s*[\'"]?(\d+)', h)
            vid = m.group(1) if m else ''
        if not vid:
            for _rx in (r'data-video-id[\'"]?\s*[:=]\s*[\'"]?(\d+)', r'data-id[\'"]?\s*[:=]\s*[\'"]?(\d+)',
                        r'video_id[\'"]?\s*[:=]\s*[\'"]?(\d+)', r'videoId[\'"]?\s*[:=]\s*[\'"]?(\d+)',
                        r'/api/play/[\'"]?\s*[\'"]?(\d{3,})', r'itemprop="identifier"[^>]*content="(\d+)"'):
                m = re.search(_rx, h)
                if m:
                    vid = m.group(1)
                    break
        if not vid:
            self._dump_html(h, page_url, 'novid')
            return ''
        _tl = []
        for _rx in (r'data-mpu="([A-Za-z0-9+/=_-]{32,})"', r'data-link="([A-Za-z0-9+/=_-]{32,})"'):
            for _m in re.finditer(_rx, h):
                _v0 = _m.group(1)
                if _v0 not in _tl:
                    _tl.append(_v0)
        if not _tl:
            _tl = list(dict.fromkeys(re.findall(r'data-blk="([A-Za-z0-9+/=_-]{32,})"', h)))
        if not _tl:
            return ''
        _pm = self._tget('pm:' + page_url, TTL_PLAY)
        if _pm:
            return _pm
        _pt = self._tget('pt:' + page_url, TTL_PLAY)
        try:
            _i = int(ti) % len(_tl) if ti is not None else (int(_pt) % len(_tl) if _pt is not None else 0)
        except Exception:
            _i = 0
        tok = _tl[_i]
        ver = '2'
        m = re.search(r'video_ver="(\d+)"', h)
        if m:
            ver = m.group(1)
        srcs = _dx(vid, tok)
        txt = self._post(urljoin(self.base, '/api/play/'), {'sources': srcs, 'ver': ver}) if srcs else ''
        if not txt:
            return self._bjp_next(h, page_url, _i, _tl)
        try:
            j = json.loads(txt)
        except Exception:
            j = None
            m = re.search(r'\{.*\}', txt, re.S)
            if m:
                try:
                    j = json.loads(m.group(0))
                except Exception:
                    j = None
        if not j or not j.get('status') or not j.get('data'):
            return self._bjp_next(h, page_url, _i, _tl)
        _rl, _nm = [j.get('data')], [j.get('lo') or 'main']
        try:
            for _it in json.loads(_dx(vid, j.get('reserve')) or '[]'):
                if isinstance(_it, dict) and _it.get('data'):
                    _rl.append(_it.get('data'))
                    _nm.append(_it.get('lo') or '')
        except Exception:
            pass
        _lp = getattr(self, '_bjp_last', '')
        if _lp and _lp in _nm:
            _lx = _nm.index(_lp)
            if _lx > 0:
                _rl.insert(0, _rl.pop(_lx))
                _nm.insert(0, _nm.pop(_lx))
        _t0, _hit, _m8, _soft, _hitlo = time.time(), '', [], [], ''
        for _k, _c in enumerate(_rl[:8]):
            if time.time() - _t0 > 25:
                break
            _lo9 = _nm[_k] if _k < len(_nm) else ''
            _pl = _dx(vid, _c)
            if not _pl:
                continue
            _purl = ('https:' + _pl) if _pl.startswith('//') else _pl
            if not _purl.startswith('http'):
                _purl = urljoin(self.base, _purl)
            for _u in self._bjp_srcs(_purl, page_url):
                if re.search(r'\.(m3u8|txt)(\?|$)', _u, re.I) or '.urlset' in _u:
                    if _u not in [_m[1] for _m in _m8]:
                        _m8.append((_lo9, _u))
                elif self._alive(_u, page_url):
                    _hit = _u
                    _hitlo = _lo9
                    break
            if _hit:
                break
        if not _hit:
            for _lo9, _u in sorted(_m8, key=lambda x: 1 if 'pianopic' in x[1] else 0):
                if time.time() - _t0 > 40:
                    break
                _pk = self._hls_pick(_u, page_url)
                if _pk:
                    _hit = _pk
                    _hitlo = _lo9
                    break
                if re.search(r'\.m3u8(\?|$)', _u, re.I) and self._rng(_u, page_url).lstrip().startswith(b'#EXTM3U'):
                    _soft.append(_u)
        if not _hit and _soft:
            for _u in _soft:
                if 'pianopic' not in _u:
                    _hit = _u
                    break
            if not _hit:
                _hit = _soft[0]
        if _hit:
            self._tset('pm:' + page_url, _hit)
            self._tset('pt:' + page_url, _i)
            if _hitlo:
                self._bjp_last = _hitlo
            _log('bjp play %s' % _hit[:90])
            return _hit
        return self._bjp_next(h, page_url, _i, _tl)

    def _rng(self, u, ref):
        _hn = urlsplit(u).netloc
        if _hn in getattr(self, '_badh', ()):
            return b''
        hd = {'User-Agent': self.ua, 'Referer': ref, 'Accept': '*/*',
              'Accept-Language': 'en-US,en;q=0.9', 'Range': 'bytes=0-4095'}
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=hd), timeout=7)
            return r.read(4096) or b''
        except Exception:
            if not hasattr(self, '_badh'):
                self._badh = set()
            self._badh.add(_hn)
            return b''

    def _alive(self, u, ref):
        return bool(self._rng(u, ref))

    def _hls_ok(self, u, ref):
        _t = self._rng(u, ref)
        if not _t.lstrip().startswith(b'#EXTM3U'):
            return False
        _tx = _t.decode('utf-8', 'ignore')
        _ls = [x.strip() for x in _tx.splitlines() if x.strip() and not x.strip().startswith('#')]
        if not _ls:
            return False
        if '#EXTINF' in _tx:
            return bool(self._rng(urljoin(u, _ls[0]), ref))
        return self._hls_ok(urljoin(u, _ls[0]), ref)

    def _hls_pick(self, u, ref):
        t = self._rng(u, ref)
        if not t.lstrip().startswith(b'#EXTM3U'):
            return ''
        if self._hls_ok(u, ref):
            return u
        _tx = t.decode('utf-8', 'ignore')
        if '#EXTINF' in _tx:
            return ''
        cands, bw = [], 0
        for ln in _tx.splitlines():
            ln = ln.strip()
            if ln.upper().startswith('#EXT-X-STREAM-INF'):
                m = re.search(r'BANDWIDTH=(\d+)', ln)
                bw = int(m.group(1)) if m else 0
            elif ln and not ln.startswith('#'):
                cands.append((bw, urljoin(u, ln)))
                bw = 0
        if not cands:
            return ''
        for _bw, v in sorted(cands, key=lambda x: -x[0]):
            if self._hls_ok(v, ref):
                return v
        return ''

    def _bjp_srcs(self, purl, page_url):
        hd = {'User-Agent': self.ua, 'Referer': page_url,
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept-Language': 'en-US,en;q=0.9', 'Upgrade-Insecure-Requests': '1',
              'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none'}
        ph = self._get(purl, headers=hd, timeout=8000) or ''
        m = re.search(r'data-config="([^"]+)"', ph)
        if not m:
            return []
        sp = urlsplit(purl)
        pq = sp.path + (('?' + sp.query) if sp.query else '')
        pid = sp.path.rsplit('/', 1)[-1]
        bb = base64.b64encode(pq.encode()).decode()
        raw = ''
        for kk in (base64.b64encode(pid.encode()).decode().rstrip('='), (bb[4:20] if len(bb) >= 20 else bb), pid, bb):
            raw = _dx(kk, m.group(1), DEX_C2)
            if raw and ('{' in raw[:4] or '"' in raw[:40]):
                break
        if not raw:
            return []
        _raw = raw.replace('\\/', '/')
        out = []
        for _mm in re.finditer(r'"src"\s*:\s*"([^"]+)"', _raw):
            try:
                _d = base64.b64decode(_mm.group(1) + '=' * (-len(_mm.group(1)) % 4)).decode('utf-8', 'ignore').replace('\\/', '/')
            except Exception:
                continue
            out += re.findall(r'(https?://[^\s"\'<>]+)', _d)
        for _mm in re.finditer(r'"(?:file|src|url|link)"\s*:\s*"(https?://[^"]+)"', _raw, re.I):
            out.append(_mm.group(1))
        return [x for x in dict.fromkeys(out) if re.search(r'\.(m3u8|mp4|flv|webm|txt)(\?|$)', x, re.I) or '.urlset' in x]


    def _bjp_next(self, h, page_url, i, tl):
        if i + 1 < min(len(tl), 3):
            return self._bjp_play(h, page_url, ti=i + 1)
        return ''

    def _vip_try(self, page_url, h, vipFlags):
        # ★ 模板插槽: 会员能破则破(拼token/签名/老接口); 服务端硬锁返回''
        return ''

    # ========== 四壳13接口扩展钩子(v7.5): isVideoFormat/manualVideoCheck/getDependence/destroy/progressVideo/setVideoFlags ==========
    def isVideoFormat(self, url):
        if not url:
            return False
        if '.m3u8' in url:
            return True
        return bool(re.search(r'\.(?:%s)(?:\?|$)' % (VIDEO_EXTS or 'm3u8|mp4|flv'), url, re.I))

    def manualVideoCheck(self):
        return False

    def getDependence(self):
        return ''

    def destroy(self):
        try:
            self._c.clear()
            self._pc.clear()
            self._ttl.clear()
            self._srv = None
        except Exception:
            pass

    def progressVideo(self, speed, time, end):
        return False

    def setVideoFlags(self, siteKey, flags):
        try:
            self._siteKey = siteKey or SITE_KEY
            self._vflags = flags or {}
        except Exception:
            pass

    # ========== 本地代理(9979-9988): dict/JSON/裸串三形态入参 + key=/url=/img:b64 + m3u8重写/图片转码 ==========
    def localProxy(self, param):
        if isinstance(param, dict):
            q, s = param, ''
        else:
            q, s = {}, str(param or '').strip()
            if s.startswith('{'):
                try:
                    d = json.loads(s)
                    q = d if isinstance(d, dict) else {}
                except Exception:
                    q = {}
        p = str(q.get('key') or q.get('url') or s or '')
        if 'key=' in p:
            p = p.split('key=', 1)[-1].split('&', 1)[0]
        elif 'url=' in p:
            p = p.split('url=', 1)[-1]
        p = unquote(p) if '%' in p else p
        if p.startswith('img:'):
            try:
                b = p[4:]
                p = base64.b64decode(b + '=' * (-len(b) % 4)).decode('utf-8', 'replace')
            except Exception:
                return [404, 'text/plain', '']
        if not p.startswith('http'):
            return [404, 'text/plain', '']
        if re.search(r'\.(jpe?g|png|webp|gif)(\?|$)', p, re.I):
            return self._img(p)
        if '.m3u8' in p:
            return self._rewrite_m3u8(p)
        try:
            r = self.fetch(p, headers={'User-Agent': self.ua, 'Referer': self.ref}, timeout=20000)
            if hasattr(r, 'status_code') and r.status_code != 200:
                return [r.status_code, 'text/plain', '']
            return {'code': 200, 'content': r.content, 'headers': {'Content-Type': r.headers.get('Content-Type', 'application/octet-stream')}}
        except Exception:
            return [404, 'text/plain', '']

    def _rewrite_m3u8(self, url):
        try:
            r = self.fetch(url, headers={'User-Agent': self.ua, 'Referer': self.ref}, timeout=20000)
            if hasattr(r, 'status_code') and r.status_code != 200:
                return [r.status_code, 'text/plain', '']
            body = r.text if hasattr(r, 'text') else str(r)
        except Exception:
            return [404, 'text/plain', '']
        base = url.rsplit('/', 1)[0] + '/'
        origin = re.match(r'https?://[^/]+', url)
        origin = origin.group(0) if origin else ''
        out = []
        for ln in body.splitlines():
            if ln.startswith('#EXT-X-KEY'):
                m = re.search(r'URI="([^"]+)"', ln)
                if m:
                    ku = m.group(1)
                    if ku.startswith('/'):
                        ku = origin + ku  # 根相对路径拼origin
                    elif not ku.startswith('http'):
                        ku = base + ku
                    ln = ln.replace('URI="%s"' % m.group(1), 'URI="%s"' % ('proxy?url=' + quote(ku, safe='')))
            elif ln.startswith('http'):
                ln = 'proxy?url=' + quote(ln, safe='')
            elif ln.startswith('/') and not ln.startswith('//'):
                ln = 'proxy?url=' + quote(origin + ln, safe='')
            out.append(ln)
        return {'code': 200, 'content': '\n'.join(out), 'headers': {'Content-Type': 'application/vnd.apple.mpegurl'}}

    def _img(self, u):
        try:
            r = requests.get(u, headers={'User-Agent': self.ua, 'Referer': PIC_REFERER or self.ref}, timeout=15)
            data, ct = r.content, r.headers.get('Content-Type', 'image/jpeg')
            if data[:4] == b'RIFF' or 'webp' in ct:
                try:
                    from PIL import Image
                    import io
                    buf = io.BytesIO()
                    Image.open(io.BytesIO(data)).convert('RGB').save(buf, 'JPEG', quality=85)
                    data, ct = buf.getvalue(), 'image/jpeg'
                except Exception:
                    ct = 'image/webp'
            return {'code': 200, 'content': data, 'headers': {'Content-Type': ct}}
        except Exception:
            return [404, 'text/plain', '']

    # ========== 列表解析(通用多形态: WP-Script/KVS/自建卡片, 3级兜底) ==========
    def _imgof(self, seg):
        for rx in (r'data-lazy-src="([^"]+)"', r'data-wpsrc="([^"]+)"', r'data-src="([^"]+)"', r'data-original="([^"]+)"', r'\bsrc="([^"]+)"'):
            m = re.search(rx, seg or '', re.I)
            if not m:
                continue
            u = m.group(1).strip()
            if not u or u.startswith('data:'):
                continue
            if u.startswith('//'):
                u = 'https:' + u
            return u
        return ''

    def _gput(self, url, h):
        if not GCACHE or not url or not h:
            return
        if len(self._gc) >= GC_MAX:
            self._gc.clear()
        self._gc[url] = [time.time(), h]

    def _items(self, h):
        if not h:
            return []
        _c = self._items_card(h)
        if _c:
            return _c
        items, seen = [], set()
        host = re.sub(r'^https?://', '', self.base).split('/')[0].replace('www.', '')
        for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>([\s\S]{0,1200}?)</a>', h, re.I):
            u = urljoin(self.base, m.group(1))
            if not self._is_item(u, host):
                continue
            inner = m.group(2)
            i = self._imgof(inner)
            if not i:
                continue
            if u in seen:
                continue
            seen.add(u)
            pic = i
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = urljoin(self.base, pic)
            nm = re.search(r'<img[^>]+alt="([^"]{2,150})"', inner, re.I) or \
                re.search(r'title="([^"]{2,150})"', inner, re.I)
            name = nm.group(1) if nm else re.sub(r'<[^>]+>', ' ', inner)
            name = re.sub(r'\s+', ' ', name).strip()
            if not name or name.lower() in ('logo', 'banner', 'preview'):
                name = unquote(u.rstrip('/').rsplit('/', 1)[-1]).replace('-', ' ')[:120]
            rm = re.search(r'(\d{1,3}:\d{2}(?::\d{2})?)', inner)
            items.append({'vod_id': u, 'vod_name': name[:140], 'vod_pic': self._pic(pic),
                          'vod_remarks': rm.group(1) if rm else '', 'vod_year': '', 'vod_area': '',
                          'vod_actor': '', 'vod_director': '', 'vod_content': ''})
            if len(items) >= 120:
                break
        if items:
            return items
        return self._items_json(h)

    def _items_card(self, h):
        out, seen = [], set()
        for m in re.finditer(r'<article[^>]*class="[^"]*thumb-block[^"]*"[\s\S]{0,2500}?</article>', h, re.I):
            blk = m.group(0)
            a = re.search(r'<a[^>]+href="([^"]*?/video/[^"]+)"', blk, re.I)
            if not a:
                continue
            u = urljoin(self.base, a.group(1))
            if u in seen:
                continue
            seen.add(u)
            pic = self._imgof(blk)
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = urljoin(self.base, pic)
            nm = re.search(r'<img[^>]+alt="([^"]{2,150})"', blk, re.I) or re.search(r'title="([^"]{2,150})"', blk, re.I)
            name = nm.group(1) if nm else unquote(u.rstrip('/').rsplit('/', 1)[-1]).replace('-', ' ')
            name = re.sub(r'\s+', ' ', name).strip()
            rm = re.search(r'(\d{1,3}:\d{2}(?::\d{2})?)', blk)
            out.append({'vod_id': u, 'vod_name': name[:140], 'vod_pic': self._pic(pic),
                        'vod_remarks': rm.group(1) if rm else '', 'vod_year': '', 'vod_area': '',
                        'vod_actor': '', 'vod_director': '', 'vod_content': ''})
            if len(out) >= 120:
                break
        return out

    def _is_item(self, u, host):
        if not u.startswith('http') or host not in u:
            return False
        low = u.lower()
        if re.search(r'\.(?:jpe?g|png|webp|gif|css|js|svg|ico|woff2?)(\?|$)', low):
            return False
        for bad in ('/page/', '/tag/', '/tags/', '/category', '/categories', '/login', '/signup',
                    '/register', '/dmca', '/contact', '/privacy', '/terms', '/?s=', '/search',
                    'javascript:', 'mailto:', '/feed', '/wp-json', '/comments'):
            if bad in low:
                return False
        return True

    def _items_json(self, h):
        try:
            d = json.loads(h)
        except Exception:
            return []
        out = []
        for it in (self._plist(d) or []):
            c = self._card(it) if isinstance(it, dict) else None
            if c:
                c['vod_pic'] = self._pic(c.get('vod_pic', ''))
                out.append(c)
        return out
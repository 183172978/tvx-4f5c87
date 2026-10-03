# -*- coding: utf-8 -*-
# 玩偶聚合 - 基于 https://fgblh.github.io/uhuj.github.io/玩偶聚合.html
# 多站网盘聚合（AppleCMS 模板），详情提取百度/夸克/阿里等网盘链接
# 播放返回网盘直链（需配合网盘播放器 / Token），parse=0
import re
import sys
from urllib.parse import quote, urljoin

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=''):
            pass


class Spider(Spider):

    def init(self, extend=""):
        self._alive = {}  # site_id -> working domain

    def getName(self):
        return '玩偶聚合'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv', 'pan.baidu', 'quark', 'aliyundrive', 'alipan', '115.com', 'xunlei', 'magnet:'))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    # 与页面 SITES 保持一致，支持多域名故障转移
    SITES = [
        {
            'id': 'wanou', 'name': '玩偶',
            'domains': ['https://wogg.xxooo.cf', 'https://www.wogg.net'],
            'listSelector': '.module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'categoryUrl': '/vodshow/{categoryId}--------{page}---.html',
            'searchUrl': '/vodsearch/-------------.html?wd={keyword}&page={page}',
            'cats': [['44', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['4', '综艺'], ['5', '音乐'], ['6', '短剧'], ['46', '纪录片']],
        },
        {
            'id': 'muou', 'name': '木偶',
            'domains': ['https://www.muou.site', 'https://www.muou.asia', 'https://666.666291.xyz'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['25', '臻选'], ['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['4', '纪录片'], ['29', '综艺'], ['30', '原盘']],
        },
        {
            'id': 'labi', 'name': '蜡笔',
            'domains': ['http://xiaocgege.shop'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['29', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['4', '综艺'], ['5', '短剧'], ['24', '蜡笔4K']],
        },
        {
            'id': 'zhizhen', 'name': '至臻',
            'domains': ['https://www.mihdr.top', 'https://mihdr.top'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['26', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['4', '综艺'], ['5', '短剧'], ['24', '老剧']],
        },
        {
            'id': 'erxiao', 'name': '二小',
            'domains': ['https://www.2xiaopan.top'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['4', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['21', '综艺']],
        },
        {
            'id': 'huban', 'name': '虎斑',
            'domains': ['http://38.76.197.172:16969', 'http://103.45.162.207:20720', 'http://xhban.xyz:20720'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['6', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '综艺'], ['4', '动漫'], ['5', '短剧'], ['30', '115网盘']],
        },
        {
            'id': 'kuaiying', 'name': '快映',
            'domains': ['http://103.45.162.207:12512', 'http://38.76.197.172:12521'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['5', '臻彩'], ['1', '电影'], ['2', '电视剧'], ['3', '综艺'], ['4', '动漫'], ['6', '短剧'], ['30', '115'], ['35', '123'], ['36', '天移迅']],
        },
        {
            'id': 'shandian', 'name': '闪电',
            'domains': ['http://shandian.blog', 'http://sd.sduc.site'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['1', '电影'], ['2', '电视剧'], ['3', '综艺'], ['4', '动漫'], ['30', '短剧']],
        },
        {
            'id': 'ouge', 'name': '欧哥',
            'domains': ['https://woog.nxog.eu.org'],
            'listSelector': '#main .module-item',
            'searchListSelector': '.module-search-item',
            'detailPanSelector': '.module-row-info p',
            'cats': [['1', '电影'], ['2', '电视剧'], ['3', '动漫'], ['4', '综艺'], ['5', '短剧'], ['21', '综合']],
        },
    ]

    DEFAULT_CAT_URL = '/vodshow/{categoryId}--------{page}---.html'
    DEFAULT_SEARCH_URL = '/vodsearch/-------------.html?wd={keyword}&page={page}'

    def fetch(self, url, headers=None):
        import requests
        h = dict(self.headers)
        if headers:
            h.update(headers)
        r = requests.get(url, headers=h, timeout=18, verify=False)
        return r

    def _get_site(self, site_id):
        for s in self.SITES:
            if s['id'] == site_id:
                return s
        return self.SITES[0]

    def _fetch_site(self, site, path):
        """多域名故障转移，缓存可用域名"""
        last_err = ''
        domains = list(site['domains'])
        # 优先使用已存活域名
        alive = self._alive.get(site['id'])
        if alive and alive in domains:
            domains = [alive] + [d for d in domains if d != alive]
        for d in domains:
            base = d.rstrip('/')
            url = path if path.startswith('http') else base + path
            try:
                r = self.fetch(url, {'Referer': base + '/'})
                text = r.text or ''
                if not text or len(text) < 200:
                    last_err = 'empty'
                    continue
                low = text.lower()
                if 'just a moment' in low or 'cf-browser' in low or 'access denied' in low or 'challenge' in low:
                    last_err = 'cf/challenge'
                    continue
                if r.status_code >= 400:
                    last_err = f'http{r.status_code}'
                    continue
                self._alive[site['id']] = base
                return {'html': text, 'base': base}
            except Exception as e:
                last_err = str(e)[:80]
                continue
        raise Exception(last_err or '全部域名失败')

    def _abs(self, base, u):
        if not u:
            return ''
        u = u.strip()
        if u.startswith('//'):
            return 'https:' + u
        return urljoin(base + '/', u)

    def _clean(self, t):
        return re.sub(r'\s+', ' ', (t or '')).strip()

    def _pan_type(self, u):
        u = (u or '').lower()
        if 'pan.baidu' in u:
            return '百度'
        if 'quark' in u:
            return '夸克'
        if 'aliyun' in u or 'alipan' in u:
            return '阿里'
        if 'xunlei' in u:
            return '迅雷'
        if '115.com' in u:
            return '115'
        if '123' in u and ('pan' in u or 'www.123' in u):
            return '123'
        if 'cloud.189' in u:
            return '天翼'
        if 'caiyun' in u or '139' in u:
            return '移动'
        if u.startswith('magnet:'):
            return '磁力'
        return '网盘'

    def homeContent(self, filter):
        classes = []
        for s in self.SITES:
            for cid, cname in s['cats']:
                classes.append({
                    'type_name': f"{s['name']}·{cname}",
                    'type_id': f"{s['id']}|{cid}",
                })
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        # 用第一个站点的第一分类试拉
        try:
            s = self.SITES[0]
            cid = s['cats'][0][0]
            path = (s.get('categoryUrl') or self.DEFAULT_CAT_URL).replace('{categoryId}', cid).replace('{page}', '1')
            r = self._fetch_site(s, path)
            return {'list': self._parse_list(r['html'], r['base'], s)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        site_id, cat_id = (tid.split('|', 1) + ['1'])[:2]
        s = self._get_site(site_id)
        path_tpl = s.get('categoryUrl') or self.DEFAULT_CAT_URL
        path = path_tpl.replace('{categoryId}', str(cat_id)).replace('{page}', str(pg))
        try:
            r = self._fetch_site(s, path)
            videos = self._parse_list(r['html'], r['base'], s)
        except Exception as e:
            videos = []
        pagecount = pg + 1 if len(videos) >= 18 else pg
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': 999999,
        }

    def _parse_list(self, html, base, site):
        videos = []
        seen = set()
        if not html:
            return videos
        # 通用 module-item / 搜索项
        # 匹配含 href 的卡片块
        blocks = re.split(r'(?=<div[^>]*class="[^"]*module-(?:item|search-item)[^"]*")', html)
        for blk in blocks:
            if 'module-item' not in blk and 'module-search-item' not in blk:
                continue
            m_href = re.search(r'href="([^"]+)"', blk)
            if not m_href:
                continue
            href = m_href.group(1)
            if '/voddetail/' not in href and '/detail/' not in href and not re.search(r'/\d+\.html', href):
                # 仍尝试接受
                if 'vod' not in href and 'detail' not in href:
                    continue
            m_img = re.search(r'<img[^>]+(?:data-src|data-original|src)="([^"]+)"', blk, re.I)
            pic = m_img.group(1) if m_img else ''
            m_title = re.search(r'(?:title|alt)="([^"]+)"', blk)
            title = self._clean(m_title.group(1) if m_title else '')
            if not title:
                m_t2 = re.search(r'class="[^"]*(?:module-item-title|module-search-item-title|video-title|title)[^"]*"[^>]*>([^<]+)', blk)
                title = self._clean(m_t2.group(1) if m_t2 else '')
            m_note = re.search(r'class="[^"]*(?:module-item-note|module-search-item-note|note)[^"]*"[^>]*>([^<]+)', blk)
            remark = self._clean(m_note.group(1) if m_note else site['name'])
            if not title or len(title) < 1:
                continue
            full_href = self._abs(base, href)
            # vod_id 编码: siteId|相对路径或绝对路径
            rel = href if href.startswith('/') else href
            vid = f"{site['id']}|{rel}"
            if vid in seen:
                continue
            seen.add(vid)
            # 过滤百度图床包装
            if 'image.baidu.com/search/down' in pic:
                mm = re.search(r'url=([^&]+)', pic)
                if mm:
                    from urllib.parse import unquote
                    pic = unquote(mm.group(1))
            videos.append({
                'vod_id': vid,
                'vod_name': title[:60],
                'vod_pic': self._abs(base, pic),
                'vod_remarks': remark,
            })
            if len(videos) >= 60:
                break
        return videos

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        raw = ids[0]
        site_id, path = (raw.split('|', 1) + [''])[:2]
        if not path:
            return {'list': []}
        s = self._get_site(site_id)
        try:
            r = self._fetch_site(s, path if path.startswith('/') else '/' + path)
            html, base = r['html'], r['base']
        except Exception as e:
            return {'list': [{'vod_id': raw, 'vod_name': '加载失败', 'vod_play_from': '错误', 'vod_play_url': f'失败${e}'}]}

        # 标题 / 封面 / 简介
        title = ''
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or re.search(r'class="[^"]*module-info-heading[^"]*"[^>]*>[\s\S]*?<h1[^>]*>([^<]+)', html)
        if m:
            title = self._clean(m.group(1))
        pic = ''
        m = re.search(r'class="[^"]*module-item-pic[^"]*"[^>]*>[\s\S]*?<img[^>]+(?:data-src|src)="([^"]+)"', html) or \
            re.search(r'<img[^>]+class="[^"]*(?:lazyload|module)[^"]*"[^>]+(?:data-src|src)="([^"]+)"', html)
        if m:
            pic = self._abs(base, m.group(1))
        desc = ''
        m = re.search(r'class="[^"]*(?:module-info-introduction|vod_content|content)[^"]*"[^>]*>([\s\S]*?)</div>', html)
        if m:
            desc = self._clean(re.sub(r'<[^>]+>', '', m.group(1)))[:500]

        # 提取网盘链接
        pans = []
        seen = set()
        # 1) selector 文本中的纯 URL
        for m in re.finditer(r'(https?://[^\s<>"\']+)', html):
            u = m.group(1).rstrip('.,;)"\'')
            if re.search(r'pan\.baidu|quark|aliyun|alipan|xunlei|115\.com|123|cloud\.189|caiyun|magnet:', u, re.I):
                if u not in seen:
                    seen.add(u)
                    pans.append((self._pan_type(u), u))
        # 2) a[href]
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', html, re.I):
            u = m.group(1)
            if re.search(r'pan\.baidu|quark|aliyun|alipan|xunlei|115\.com|123|cloud\.189|caiyun|magnet:', u, re.I):
                full = self._abs(base, u)
                if full not in seen:
                    seen.add(full)
                    name = self._clean(re.sub(r'<[^>]+>', '', m.group(2))) or self._pan_type(full)
                    pans.append((name[:40] if name else self._pan_type(full), full))

        if not pans:
            # 兜底：module-row-info
            for m in re.finditer(r'class="[^"]*module-row-info[^"]*"[^>]*>([\s\S]*?)</div>', html):
                for um in re.finditer(r'(https?://[^\s<>"\']+)', m.group(1)):
                    u = um.group(1).rstrip('.,;)"\'')
                    if u not in seen and re.search(r'http', u):
                        seen.add(u)
                        pans.append((self._pan_type(u), u))

        play_from = []
        play_url = []
        if pans:
            # 按类型分组
            groups = {}
            for name, url in pans:
                t = self._pan_type(url)
                groups.setdefault(t, []).append(f'{name}${url}')
            for t, items in groups.items():
                play_from.append(t)
                play_url.append('#'.join(items))
        else:
            play_from = ['无资源']
            play_url = ['未提取到网盘链接$']

        return {
            'list': [{
                'vod_id': raw,
                'vod_name': title or '未知',
                'vod_pic': pic,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]
        }

    def searchContent(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': []}
        results = []
        seen = set()
        # 聚合搜索：依次尝试各站（限制时间）
        for s in self.SITES:
            if len(results) >= 40:
                break
            try:
                path_tpl = s.get('searchUrl') or self.DEFAULT_SEARCH_URL
                path = path_tpl.replace('{keyword}', quote(key)).replace('{page}', str(pg))
                r = self._fetch_site(s, path)
                items = self._parse_list(r['html'], r['base'], s)
                for v in items:
                    if v['vod_id'] in seen:
                        continue
                    seen.add(v['vod_id'])
                    v['vod_remarks'] = f"{s['name']} · {v.get('vod_remarks', '')}"
                    results.append(v)
            except Exception:
                continue
        return {'list': results[:48]}

    def playerContent(self, flag, id, vipFlags):
        # 网盘链接直接返回，客户端需支持 push 或网盘解析
        url = id or ''
        return {
            'parse': 0,
            'url': url,
            'header': self.headers,
        }

    def localProxy(self, param):
        return None

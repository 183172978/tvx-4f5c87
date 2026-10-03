# -*- coding: utf-8 -*-
"""
漫蛙动漫 TVBox Spider
站点: https://manwaza.cc/ (漫蛙 MANWA)
形态: API 站 · 首页/分类/搜索走 JSON 接口, 详情/播放页服务端渲染
接口:
  分类 POST /api/cate/  body{page{page,pageSize:36},category:"video",sort,
        video{typeId,year,status,tag,area,lang}} -> data{list[{title,pic,url,tags,status}],total}
  搜索 GET  /api/search?keyword=&page=&pageSize=20 -> data{list[{id,title,cover,tags,status}],total}
  详情 /video/{vid} HTML: .comic-title / img.comic-cover / .comic-meta / .comic-desc /
        #lineSelect 线路 / #grid-N 每线路选集 <a class="episode-item" href="/video/{vid}/{eid}">
  播放 /video/{vid}/{eid} HTML 内联 var currentUrl = '...m3u8', 直链交播放器
二级分类(filters): 分类(typeId 1国产/2日韩/3欧美/4港台/5动漫/6里番) ×
  剧情tag / 状态status(-1全部 0连载 1完结) / 年份year / 排序sort(0更新 1播放 3收藏)
加密处理: 部分播放 m3u8 为 HLS AES-128 加密(EXT-X-KEY:METHOD=AES-128, IV=0, key 公开可拉),
  已实测解密出标准 TS(h264+aac)。属标准 HLS 加密, 播放器(Exo)凭 KEY 行原生解密。
广告清洗: 多家 CDN 在正片 m3u8 中混插广告分片(异目录 + METHOD=NONE + DISCONTINUITY 隔离)。
  playerContent 返回 [净化, 直连] 双地址: 净化经 localProxy 拉取列表→主列表跟随 variant→
  多数目录表决剔广告→保留 AES KEY(绝对化)交播放器解密→分片绝对地址直连 CDN;
  净化不可用时可在播放器内切「直连」原样播放。
契约: class Spider 无继承 · 14 壳方法全实现 · 位置参数契约 · $/#/$$$ 分隔
      playerContent header 为 dict · Python 层不调用 setCache/getCache
生成: 2026-10-02 · 结构经实站接口与页面逐项核对
"""
import re
import json
import base64
import html as _html
import urllib.request
import urllib.parse
import urllib.error
from collections import Counter


class Spider:
    def __init__(self):
        self.host = 'https://manwaza.cc'
        self.ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        self.headers = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.classes = [
            ('国产', '1'), ('日韩', '2'), ('欧美', '3'),
            ('港台', '4'), ('动漫', '5'), ('里番', '6'),
        ]
        self.page_size = 36

    # ================= 内部工具 =================
    def _fetch_bytes(self, url, timeout=20, data=None):
        headers = dict(self.headers)
        if data is not None:
            headers['Content-Type'] = 'application/json'
        last = None
        for _ in range(2):
            try:
                req = urllib.request.Request(url, headers=headers, data=data)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except Exception as e:
                last = e
        raise last

    def _fetch(self, url, timeout=20):
        data = self._fetch_bytes(url, timeout=timeout)
        for enc in ('utf-8', 'gbk', 'gb18030'):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode('utf-8', 'ignore')

    def _get_json(self, url, timeout=20):
        return json.loads(self._fetch(url, timeout=timeout))

    def _post_json(self, url, obj, timeout=25):
        body = json.dumps(obj).encode('utf-8')
        raw = self._fetch_bytes(url, timeout=timeout, data=body)
        return json.loads(raw.decode('utf-8', 'ignore'))

    def _clean(self, s):
        if not s:
            return ''
        s = _html.unescape(s)
        s = re.sub(r'<[^>]+>', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    def _to_int(self, v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    def _cate_body(self, page, type_id=0, tag='', status=-1, year=0, sort=0):
        return {
            'page': {'page': page, 'pageSize': self.page_size},
            'category': 'video',
            'sort': sort,
            'comic': {'status': -1, 'day': 0, 'year': 0, 'tag': ''},
            'video': {
                'year': year, 'typeId': type_id, 'area': '', 'lang': '',
                'status': status, 'tag': tag,
            },
            'novel': {'status': -1, 'day': 0, 'sortId': 0},
        }

    def _list_item(self, it):
        url = it.get('url') or ''
        m = re.search(r'/video/(\d+)', url)
        vid = m.group(1) if m else str(it.get('id') or '')
        if not vid:
            return None
        pic = it.get('pic') or it.get('cover') or ''
        if pic.startswith('data:'):
            pic = ''
        remark = ''
        tags = (it.get('tags') or '').replace(',', ' ')
        if tags:
            remark = tags
        st = it.get('status')
        if st == 0:
            remark = (remark + ' 连载').strip()
        elif st == 1:
            remark = (remark + ' 完结').strip()
        return {
            'vod_id': vid,
            'vod_name': self._clean(it.get('title') or ''),
            'vod_pic': pic,
            'vod_remarks': remark[:24],
        }

    def _filters(self):
        tag_vals = [{'n': '全部', 'v': ''}] + [
            {'n': t, 'v': t} for t in
            ('动画', '喜剧', '奇幻', '剧情', '冒险', '动作', '科幻',
             '爱情', '儿童', '短片', '家庭', '悬疑', '运动')
        ]
        return [
            {'key': 'tag', 'name': '剧情', 'value': tag_vals},
            {'key': 'status', 'name': '状态', 'value': [
                {'n': '全部', 'v': '-1'}, {'n': '连载', 'v': '0'}, {'n': '完结', 'v': '1'}]},
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': '0'}, {'n': '2026', 'v': '2026'}, {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'}, {'n': '2023', 'v': '2023'}, {'n': '2022', 'v': '2022'}]},
            {'key': 'sort', 'name': '排序', 'value': [
                {'n': '最近更新', 'v': '0'}, {'n': '最多播放', 'v': '1'}, {'n': '最多收藏', 'v': '3'}]},
        ]

    # ================= 壳接口(位置参数契约) =================
    def getName(self):
        return '漫蛙动漫'

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        u = (url or '').lower()
        if u.endswith('.m3u8') or u.endswith('.mp4') or '.m3u8?' in u or '.mp4?' in u:
            return True
        return '/proxy' in u and 'hls' in u

    def manualVideoCheck(self):
        return False

    def init(self, extend):
        return None

    def destroy(self):
        return None

    def homeContent(self, filter):
        classes = [{'type_id': tid, 'type_name': name} for name, tid in self.classes]
        filters = {tid: self._filters() for _, tid in self.classes}
        items = []
        try:
            d = self._post_json(self.host + '/api/cate/', self._cate_body(1))
            for it in (d.get('data') or {}).get('list') or []:
                one = self._list_item(it)
                if one:
                    items.append(one)
        except Exception:
            items = []
        return {'class': classes, 'list': items, 'filters': filters}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = self._to_int(pg, 1)
        if pg < 1:
            pg = 1
        ext = extend if isinstance(extend, dict) else {}
        tag = str(ext.get('tag') or '')
        status = self._to_int(ext.get('status'), -1)
        year = self._to_int(ext.get('year'), 0)
        sort = self._to_int(ext.get('sort'), 0)
        body = self._cate_body(pg, type_id=self._to_int(tid, 0),
                               tag=tag, status=status, year=year, sort=sort)
        d = self._post_json(self.host + '/api/cate/', body)
        data = d.get('data') or {}
        items = []
        for it in data.get('list') or []:
            one = self._list_item(it)
            if one:
                items.append(one)
        total = self._to_int(data.get('total'), 0)
        pagecount = (total + self.page_size - 1) // self.page_size if total else pg
        if pagecount < pg:
            pagecount = pg
        return {
            'list': items,
            'page': str(pg),
            'pagecount': str(pagecount),
            'limit': self.page_size,
            'total': total if total else 999999,
        }

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ''
        elif isinstance(ids, dict):
            vid = str(ids.get('id') or ids.get('vod_id') or '')
        else:
            vid = str(ids or '')
        m_vid = re.search(r'(\d+)', vid)
        vid = m_vid.group(1) if m_vid else vid
        url = '{0}/video/{1}'.format(self.host, vid)
        html = self._fetch(url)
        title = ''
        m = re.search(r'class="comic-title"[^>]*>([^<]+)<', html)
        if m:
            title = self._clean(m.group(1))
        if not title:
            m2 = re.search(r'<title>《([^》]+)》', html)
            title = self._clean(m2.group(1)) if m2 else vid
        pic = ''
        pm = re.search(r'<img class="comic-cover"[^>]*src="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        # 元信息: 类型/导演/主演/更新/状态/年份
        meta = {}
        mm = re.search(r'class="comic-meta">(.*?)</div>\s*</div>', html, re.S)
        if mm:
            for k, v in re.findall(r'<div>([^<：:]+)[：:]\s*<span[^>]*>(.*?)</span>', mm.group(1), re.S):
                meta[self._clean(k)] = self._clean(v)
        desc = ''
        dm = re.search(r'class="comic-desc">(.*?)</div>', html, re.S)
        if dm:
            desc = self._clean(dm.group(1))
        tags = []
        for t in re.findall(r'<span class="tag">([^<]+)</span>', html):
            t = self._clean(t)
            if t and t != '更多':
                tags.append(t)
        # 线路名
        line_names = []
        for v, name in re.findall(r'<option value="(\d+)">\s*([^<]+?)\s*</option>', html):
            name = self._clean(name)
            if name:
                line_names.append(name)
        # 按 grid 分组解析选集
        grids = {}
        parts = re.split(r'id="grid-(\d+)"', html)
        for k in range(1, len(parts) - 1, 2):
            gid = parts[k]
            body = parts[k + 1]
            eps = []
            for href, name in re.findall(
                    r'<a href="(/video/\d+/\d+)"[^>]*class="episode-item"[^>]*>\s*([^<]+?)\s*</a>', body):
                name = self._clean(name) or '正片'
                eps.append('{0}${1}'.format(name, href))
            if eps:
                grids[gid] = eps
        play_from, play_url = [], []
        for idx in sorted(grids, key=lambda x: self._to_int(x, 0)):
            gi = self._to_int(idx, 0)
            name = line_names[gi] if gi < len(line_names) else ''
            if not name:
                name = '漫蛙资源{0}'.format(gi + 1)
            play_from.append(name)
            play_url.append('#'.join(grids[idx]))
        if not play_from:
            play_from = ['漫蛙资源']
            play_url = ['']
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'type_name': meta.get('类型', ''),
            'vod_year': meta.get('年份', ''),
            'vod_actor': meta.get('主演', ''),
            'vod_director': meta.get('导演', ''),
            'vod_remarks': meta.get('状态', ''),
            'vod_tag': ','.join(tags),
            'vod_content': desc,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = self._to_int(pg, 1)
        if pg < 1:
            pg = 1
        q = urllib.parse.quote(key)
        url = '{0}/api/search?keyword={1}&page={2}&pageSize=20'.format(self.host, q, pg)
        d = self._get_json(url)
        data = d.get('data') or {}
        items = []
        for it in data.get('list') or []:
            one = self._list_item(it)
            if one:
                items.append(one)
        total = self._to_int(data.get('total'), 0)
        pagecount = (total + 19) // 20 if total else pg
        if pagecount < pg:
            pagecount = pg
        return {
            'list': items,
            'page': str(pg),
            'pagecount': str(pagecount),
            'limit': 20,
            'total': total if total else 999999,
        }

    # ================= HLS 广告清洗(本地代理) =================
    def _proxy_url(self, target):
        b64 = base64.urlsafe_b64encode(target.encode('utf-8')).decode('ascii')
        base = ''
        try:
            fn = globals().get('getProxyUrl')
            if callable(fn):
                base = fn() or ''
        except Exception:
            base = ''
        if not base:
            base = 'http://127.0.0.1:9978/proxy?do=py'
        sep = '&' if '?' in base else '?'
        return '{0}{1}type=hls&url={2}'.format(base, sep, b64)

    def _proxy_target(self, param):
        p = param
        if isinstance(p, bytes):
            p = p.decode('utf-8', 'ignore')
        if isinstance(p, str):
            s = p.strip()
            d = None
            try:
                d = json.loads(s)
            except Exception:
                d = None
            if isinstance(d, dict):
                p = d
            else:
                if '?' in s:
                    s = s.split('?', 1)[1]
                p = dict(urllib.parse.parse_qsl(s))
        if not isinstance(p, dict):
            return ''
        raw = ''
        if p.get('url'):
            raw = str(p['url'])
        elif p.get('key'):
            k = str(p['key'])
            if k.startswith('hls/'):
                raw = k[4:]
        if not raw:
            return ''
        try:
            return base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8')
        except Exception:
            return ''

    def _abs_uri(self, line, base):
        return re.sub(r'URI="([^"]+)"',
                      lambda m: 'URI="{0}"'.format(urllib.parse.urljoin(base, m.group(1))),
                      line)

    def _hls_absolutize(self, text, base):
        out = []
        for l in text.splitlines():
            s = l.strip()
            if not s:
                continue
            if s.startswith('#'):
                if 'URI="' in s:
                    s = self._abs_uri(s, base)
                out.append(s)
            else:
                out.append(urllib.parse.urljoin(base, s))
        return '\n'.join(out) + '\n'

    def _hls_clean(self, text, base, depth=0):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # 主列表 -> 取码率最高的 variant 继续清洗
        if depth < 3 and any(l.startswith('#EXT-X-STREAM-INF') for l in lines):
            best_bw, variant = -1, ''
            for i, l in enumerate(lines):
                if l.startswith('#EXT-X-STREAM-INF'):
                    m = re.search(r'BANDWIDTH=(\d+)', l)
                    bw = int(m.group(1)) if m else 0
                    nxt = lines[i + 1] if i + 1 < len(lines) else ''
                    if nxt and not nxt.startswith('#') and bw >= best_bw:
                        best_bw, variant = bw, nxt
            if variant:
                vurl = urllib.parse.urljoin(base, variant)
                return self._hls_clean(self._fetch(vurl), vurl, depth + 1)
        # 多数目录表决: 分片最多的目录为正片, 其余视为混插广告
        absu, dirs = {}, Counter()
        for i, l in enumerate(lines):
            if not l.startswith('#'):
                a = urllib.parse.urljoin(base, l)
                absu[i] = a
                dirs[a.rsplit('/', 1)[0] + '/'] += 1
        if not dirs:
            return self._hls_absolutize(text, base)
        main_dir = dirs.most_common(1)[0][0]
        out = []
        cur_key = None      # 当前正片 KEY 行(绝对化后), None 表示不加密
        last_key = '__init__'
        pending_inf = None
        for i, l in enumerate(lines):
            if l.startswith('#EXT-X-DISCONTINUITY'):
                pending_inf = None
                continue
            if l.startswith('#EXT-X-KEY'):
                if 'METHOD=NONE' in l:
                    cur_key = None
                else:
                    cur_key = self._abs_uri(l, base)
                continue
            if l.startswith('#EXTINF'):
                pending_inf = l
                continue
            if l.startswith('#EXT-X-MEDIA-SEQUENCE'):
                out.append('#EXT-X-MEDIA-SEQUENCE:0')
                continue
            if l.startswith('#'):
                if 'URI="' in l:  # EXT-X-MAP 等
                    l = self._abs_uri(l, base)
                out.append(l)
                continue
            a = absu.get(i, '')
            if a.rsplit('/', 1)[0] + '/' != main_dir:
                pending_inf = None
                continue
            if cur_key != last_key:
                out.append(cur_key if cur_key else '#EXT-X-KEY:METHOD=NONE')
                last_key = cur_key
            out.append(pending_inf or '#EXTINF:4,')
            pending_inf = None
            out.append(a)
        if not any(l == '#EXT-X-ENDLIST' for l in out) and '#EXT-X-ENDLIST' in lines:
            out.append('#EXT-X-ENDLIST')
        return '\n'.join(out) + '\n'

    def _serve_hls(self, target):
        text = self._fetch(target)
        try:
            body = self._hls_clean(text, target)
        except Exception:
            body = self._hls_absolutize(text, target)
        return [200, 'application/vnd.apple.mpegurl', body.encode('utf-8'), {}]

    def playerContent(self, flag, id, vipFlags):
        # 播放页内联 currentUrl 即 m3u8; 返回 [净化, 直连] 双地址
        # 净化: localProxy 清洗混插广告分片; AES-128 加密保留 KEY 行由播放器原生解密
        _header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
        }
        play_id = str(id or '')
        page_url = play_id if play_id.startswith('http') else self.host + play_id
        m3u8 = ''
        try:
            html = self._fetch(page_url)
            m = re.search(r"var currentUrl = '([^']+)'", html)
            if m:
                m3u8 = m.group(1).strip()
            if not m3u8:
                m2 = re.search(r'(https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?)', html)
                if m2:
                    m3u8 = m2.group(1).strip()
        except Exception:
            m3u8 = ''
        if not m3u8:
            return {'parse': 1, 'url': page_url, 'header': _header}
        clean = self._proxy_url(m3u8)
        return {'parse': 0, 'url': ['净化', clean, '直连', m3u8], 'header': _header}

    def localProxy(self, param):
        try:
            target = self._proxy_target(param)
            if target.startswith('http'):
                return self._serve_hls(target)
        except Exception:
            pass
        return [404, 'text/plain', b'', {}]

    def action(self, action):
        return None

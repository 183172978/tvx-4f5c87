#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vimeo 爬虫 — 修复无播放地址 + 多清晰度选择
优先从 player embed 页提取 playerConfig（/config 常 403）
"""
import json
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://vimeo.com'
        self.api = 'https://api.vimeo.com'
        self.player = 'https://player.vimeo.com/video/'
        self.viewer = 'https://vimeo.com/_next/viewer'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        self.jwt = ''
        self.jwt_ts = 0
        self.bearer = ''
        self.channels = {
            'staffpicks': {'name': 'Staff Picks'},
            'animation': {'name': 'Animation'},
            'documentary': {'name': 'Documentary'},
            'narrative': {'name': 'Narrative'},
            'music': {'name': 'Music'},
            'comedy': {'name': 'Comedy'},
            'experimental': {'name': 'Experimental'},
            'sports': {'name': 'Sports'},
            'travel': {'name': 'Travel'},
            'adsandcommercials': {'name': 'Ads'},
            'brandedcontent': {'name': 'Branded'},
        }

    def getName(self):
        return 'Vimeo'

    def init(self, extend=""):
        try:
            if isinstance(extend, str) and extend.strip().startswith(('eyJ', 'jwt ', 'bearer ', 'Bearer ')):
                raw = extend.strip()
                if raw.lower().startswith('bearer '):
                    self.bearer = raw.split(' ', 1)[1].strip()
                elif raw.lower().startswith('jwt '):
                    self.jwt = raw.split(' ', 1)[1].strip()
                    self.jwt_ts = time.time()
                else:
                    self.jwt = raw
                    self.jwt_ts = time.time()
            elif extend:
                ext = json.loads(extend) if isinstance(extend, str) else (extend or {})
                self.bearer = str(ext.get('bearer') or ext.get('token') or '')
                if ext.get('jwt'):
                    self.jwt = str(ext.get('jwt'))
                    self.jwt_ts = time.time()
        except Exception:
            pass
        self._ensure_jwt()

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'application/json, text/plain, */*',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=20, verify=False)
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params, doseq=True)
            from urllib.request import Request, urlopen
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            raw = urlopen(Request(full, headers=headers), timeout=20, context=ctx).read()

            class R:
                def __init__(self, raw):
                    self.content = raw
                    self.text = raw.decode('utf-8', 'ignore')
                    self.status_code = 200

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_json(self, url, headers=None, params=None):
        resp = self.fetch(url, headers=headers, params=params)
        if not resp:
            return {}
        try:
            if hasattr(resp, 'status_code') and resp.status_code != 200:
                return {}
            return resp.json()
        except Exception:
            return {}

    def fetch_text(self, url, headers=None):
        resp = self.fetch(url, headers=headers)
        if not resp:
            return ''
        return getattr(resp, 'text', '') or ''

    def _ensure_jwt(self):
        if self.bearer:
            return ''
        if self.jwt and (time.time() - self.jwt_ts) < 240:
            return self.jwt
        self.jwt = ''
        try:
            js = self.fetch_json(self.viewer, headers={
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'application/json',
            })
            if js.get('jwt'):
                self.jwt = js.get('jwt')
                self.jwt_ts = time.time()
                return self.jwt
        except Exception:
            pass
        html = self.fetch_text(self.siteUrl + '/channels/staffpicks')
        if not html:
            html = self.fetch_text(self.siteUrl + '/')
        m = re.search(r'"jwt"\s*:\s*"([^"]+)"', html or '')
        if m:
            self.jwt = m.group(1)
            self.jwt_ts = time.time()
        return self.jwt

    def _auth_headers(self):
        headers = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'application/vnd.vimeo.*+json;version=3.4',
            'Origin': self.siteUrl,
        }
        if self.bearer:
            headers['Authorization'] = 'bearer ' + self.bearer
        else:
            token = self._ensure_jwt()
            if token:
                headers['Authorization'] = 'jwt ' + token
        return headers

    def api_get(self, path, params=None):
        js = self.fetch_json(self.api + path, headers=self._auth_headers(), params=params)
        if not js or js.get('error') or js.get('error_code'):
            self.jwt = ''
            self.jwt_ts = 0
            js = self.fetch_json(self.api + path, headers=self._auth_headers(), params=params)
        return js or {}

    def _fmt_dur(self, sec):
        try:
            n = int(sec or 0)
        except Exception:
            return ''
        if n <= 0:
            return ''
        return '%d:%02d' % (n // 60, n % 60)

    def _pic(self, item):
        p = (item or {}).get('pictures') or {}
        if p.get('base_link'):
            return p.get('base_link')
        sizes = p.get('sizes') or []
        if sizes:
            return sizes[-1].get('link') or ''
        return ''

    def _vid(self, item):
        uri = str((item or {}).get('uri') or '')
        m = re.search(r'/videos/(\d+)', uri)
        if m:
            return m.group(1)
        link = str((item or {}).get('link') or '')
        m2 = re.search(r'vimeo\.com/(\d+)', link)
        return m2.group(1) if m2 else ''

    def _map(self, item):
        vid = self._vid(item)
        if not vid:
            return None
        return {
            'vod_id': vid,
            'vod_name': item.get('name') or vid,
            'vod_pic': self._pic(item),
            'vod_remarks': self._fmt_dur(item.get('duration')),
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            js = self.api_get('/channels/staffpicks/videos', {'per_page': 20, 'page': 1, 'sort': 'date'})
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        cate = str(tid or 'staffpicks')
        videos = []
        total = 0
        try:
            if cate == 'staffpicks':
                path = '/channels/staffpicks/videos'
                params = {'per_page': 20, 'page': pg, 'sort': 'date'}
            else:
                path = '/categories/%s/videos' % urllib.parse.quote(cate)
                params = {'per_page': 20, 'page': pg, 'sort': 'likes'}
            js = self.api_get(path, params)
            total = int(js.get('total') or 0)
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        pagecount = min((total + 19) // 20, 200) if total else (pg + 1 if len(videos) >= 20 else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 20,
            'total': total or len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        total = 0
        try:
            m = re.search(r'(\d{6,})', str(key or ''))
            if m and pg == 1:
                js = self.api_get('/videos/' + m.group(1))
                v = self._map(js) if js else None
                if v:
                    return {'list': [v], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 1}
            js = self.api_get('/videos', {
                'query': key,
                'per_page': 20,
                'page': pg,
                'filter': 'content_rating',
                'filter_content_rating': 'safe',
            })
            total = int(js.get('total') or 0)
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('搜索失败: %s' % e)
        pagecount = min((total + 19) // 20, 200) if total else (pg + 1 if videos else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 20,
            'total': total or len(videos),
        }

    # ---------- playerConfig 提取 ----------
    def _extract_json_object(self, html, needle):
        text = html or ''
        i = text.find(needle)
        if i < 0:
            return {}
        start = text.find('{', i)
        if start < 0:
            return {}
        depth = 0
        in_str = False
        esc = False
        for p in range(start, len(text)):
            c = text[p]
            if in_str:
                if esc:
                    esc = False
                elif c == '\\':
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:p + 1])
                    except Exception:
                        return {}
        return {}

    def _load_player_cfg(self, vid):
        """优先 embed HTML 的 playerConfig（/config 常 403）"""
        # 1) embed 页
        html = self.fetch_text(self.player + vid, headers={
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/' + vid,
            'Accept': 'text/html,application/xhtml+xml',
        })
        cfg = self._extract_json_object(html, 'window.playerConfig')
        if not cfg:
            cfg = self._extract_json_object(html, 'playerConfig')
        if cfg.get('request'):
            return cfg

        # 2) /config API
        cfg = self.fetch_json(self.player + vid + '/config', headers={
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/' + vid,
            'Origin': 'https://player.vimeo.com',
            'Accept': 'application/json',
        })
        if cfg.get('request'):
            return cfg

        # 3) api config_url / embed h=
        info = self.api_get('/videos/' + vid, {'fields': 'config_url,player_embed_url'})
        if info.get('config_url'):
            cfg = self.fetch_json(info['config_url'], headers={
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/' + vid,
            })
            if cfg.get('request'):
                return cfg
        embed = info.get('player_embed_url') or ''
        hm = re.search(r'[?&]h=([a-f0-9]+)', embed)
        if hm:
            cfg = self.fetch_json(self.player + vid + '/config?h=' + hm.group(1), headers={
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/' + vid,
                'Accept': 'application/json',
            })
            if cfg.get('request'):
                return cfg
        return {}

    def _resolve_url(self, base, rel):
        if not rel:
            return ''
        if re.match(r'^https?://', rel, re.I):
            return rel
        return urllib.parse.urljoin(base, rel)

    def _parse_hls_master(self, master_url):
        text = self.fetch_text(master_url, headers={
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': '*/*',
        })
        if not text or text[:1] == '<':
            return []
        lines = text.splitlines()
        out = []
        seen_h = set()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXT-X-STREAM-INF:'):
                hm = re.search(r'RESOLUTION=\d+x(\d+)', line)
                h = int(hm.group(1)) if hm else 0
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    uri = lines[j].strip()
                    if uri and not uri.startswith('#'):
                        if h not in seen_h:
                            seen_h.add(h)
                            out.append({'height': h, 'url': self._resolve_url(master_url, uri)})
                        i = j
            i += 1
        out.sort(key=lambda x: x.get('height') or 0, reverse=True)
        return out

    def _collect_qualities(self, cfg):
        """返回 [(label, url), ...] — 优先 HLS（播放器兼容更好），再 progressive"""
        result = []
        seen = set()
        files = ((cfg or {}).get('request') or {}).get('files') or {}

        # 1) HLS master + 分档（优先）
        hls = files.get('hls') or {}
        cdns = hls.get('cdns') or {}
        preferred = hls.get('default_cdn') or ''
        order = ([preferred] if preferred else []) + list(cdns.keys())
        master = ''
        for name in order:
            node = cdns.get(name) or {}
            master = node.get('url') or node.get('avc_url') or node.get('av1_url') or ''
            if master:
                break
        if not master:
            master = hls.get('url') or ''

        if master:
            variants = self._parse_hls_master(master)
            for v in variants:
                u = v.get('url')
                if not u or u in seen:
                    continue
                seen.add(u)
                h = int(v.get('height') or 0)
                result.append(('%dp' % h if h else 'HLS', u))
            if master not in seen:
                seen.add(master)
                result.append(('自适应', master))

        # 2) progressive MP4 兜底
        prog = [p for p in (files.get('progressive') or []) if p and p.get('url')]
        prog.sort(key=lambda x: int(x.get('height') or 0), reverse=True)
        for p in prog:
            u = p.get('url')
            if not u or u in seen:
                continue
            seen.add(u)
            h = int(p.get('height') or 0)
            label = '%dp-MP4' % h if h else 'MP4'
            result.append((label, u))

        # 3) DASH
        if not result:
            dash = files.get('dash') or {}
            for node in (dash.get('cdns') or {}).values():
                u = (node or {}).get('url') or (node or {}).get('avc_url') or ''
                if u:
                    result.append(('DASH', u))
                    break
        return result

    def detailContent(self, ids):
        vid = str((ids or [''])[0]).split(':')[0]
        vid = re.sub(r'\D', '', vid) or vid
        try:
            js = self.api_get('/videos/' + vid)
            if not js.get('name') and not js.get('uri'):
                js = {}
            user = (js.get('user') or {}).get('name') or ''
            desc = js.get('description') or ''
            if isinstance(desc, str):
                desc = re.sub(r'<[^>]+>', '', desc)[:600]

            cfg = self._load_player_cfg(vid)
            qualities = self._collect_qualities(cfg)
            if qualities:
                # 存 label$vid@@label，播放时重新取流（避免 progressive/HLS 签名过期）
                play_url = '#'.join(['%s$%s@@%s' % (n, vid, n) for n, u in qualities])
            else:
                play_url = '正片$%s@@auto' % vid

            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': js.get('name') or vid,
                    'vod_pic': self._pic(js),
                    'vod_remarks': self._fmt_dur(js.get('duration')),
                    'vod_year': str(js.get('created_time') or '')[:10],
                    'vod_actor': user,
                    'vod_content': desc,
                    'vod_play_from': 'Vimeo',
                    'vod_play_url': play_url,
                }]
            }
        except Exception as e:
            print('获取详情失败: %s' % e)
            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': vid,
                    'vod_play_from': 'Vimeo',
                    'vod_play_url': '正片$%s' % vid,
                }]
            }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play_id = str(id or '').strip()
        want = ''
        # id 形如 133697756@@1080p 或旧直链
        if '@@' in play_id:
            left, want = play_id.split('@@', 1)
            play_id = left
        if play_id.startswith('http') and ('vimeocdn.com' in play_id or self.isVideoFormat(play_id)):
            # 旧缓存直链可能过期，尽量从 URL 反推 vid 再刷新
            m = re.search(r'/(\d{6,})/', play_id)
            if m:
                play_id = m.group(1)
            else:
                return {'parse': 0, 'jx': 0, 'url': play_id, 'header': header}

        vid = re.sub(r'\D', '', play_id.split('|')[0].split(':')[0].split('$')[-1]) or play_id
        fl = str(want or flag or '')
        try:
            cfg = self._load_player_cfg(vid)
            qualities = self._collect_qualities(cfg)
            if qualities:
                chosen = qualities[0][1]
                for name, url in qualities:
                    if not fl or fl in ('auto', '正片', '默认'):
                        chosen = url
                        break
                    if fl == name or fl in name or name.replace('-MP4', '') == fl.replace('-MP4', ''):
                        chosen = url
                        break
                # HLS 用标准头；progressive 去掉 Origin 更稳
                h = dict(header)
                if '.mp4' in chosen and 'vimeocdn.com' in chosen:
                    h.pop('Origin', None)
                return {'parse': 0, 'jx': 0, 'url': chosen, 'header': h}
        except Exception as e:
            print('获取播放内容失败: %s' % e)
        return {
            'parse': 1,
            'jx': 1,
            'url': self.siteUrl + '/' + str(vid),
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.m3u8', '.mp4', '.mpd', '.m4s', 'vimeocdn.com'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False)[:200])
    cat = spider.categoryContent('staffpicks', 1, False, {})
    print('cat', len(cat.get('list') or []))
    if cat.get('list'):
        vid = cat['list'][0]['vod_id']
        d = spider.detailContent([vid])
        item = (d.get('list') or [{}])[0]
        print('name', item.get('vod_name'))
        print('play_url', (item.get('vod_play_url') or '')[:200])
        first = (item.get('vod_play_url') or '').split('#')[0].split('$')[-1]
        p = spider.playerContent('1080p', first, [])
        print('play', p.get('parse'), str(p.get('url'))[:90])

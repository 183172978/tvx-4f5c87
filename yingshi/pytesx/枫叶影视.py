# -*- coding: utf-8 -*-
# 枫叶影视 https://www.fyeys.com
# 播放：/api/mw-movie/anonymous/v2/video/episode/url
# 签名：sign = SHA1(MD5(sortedParams + &key=SIGN_KEY&t=timestamp_ms))
import sys, re, json, time, hashlib, uuid
import urllib.request
import urllib.parse
import ssl

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass

class Spider(BaseSpider):
    host = 'https://www.fyeys.com'
    api_prefix = '/api/mw-movie'
    SIGN_KEY = 'cb808529bae6b6be45ecfab29a4889bc'
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    device_id = ''

    CLASSES = [
        {'type_id': '1', 'type_name': '电影'},
        {'type_id': '2', 'type_name': '电视剧'},
        {'type_id': '3', 'type_name': '综艺'},
        {'type_id': '4', 'type_name': '动漫'},
        {'type_id': '88', 'type_name': '短剧'},
    ]

    def init(self, extend=''):
        self.device_id = str(uuid.uuid4())
        if isinstance(extend, str) and extend.strip():
            try:
                if extend.strip().startswith('{'):
                    cfg = json.loads(extend)
                    if cfg.get('host'):
                        self.host = str(cfg['host']).rstrip('/')
                    if cfg.get('signKey'):
                        self.SIGN_KEY = str(cfg['signKey'])
                elif extend.startswith('http'):
                    self.host = extend.rstrip('/')
            except Exception:
                pass
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.headers = {
            'User-Agent': self.UA,
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def getName(self):
        return '枫叶影视'

    def _get(self, url, extra_headers=None):
        headers = dict(self.headers)
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=self.ctx) as resp:
            data = resp.read()
            try:
                return data.decode('utf-8')
            except Exception:
                return data.decode('latin1', errors='ignore')

    def _md5(self, s):
        return hashlib.md5(s.encode('utf-8')).hexdigest()

    def _sha1(self, s):
        return hashlib.sha1(s.encode('utf-8')).hexdigest()

    def _sign(self, params, t):
        items = []
        for k in sorted(params.keys()):
            v = params[k]
            if v is None or v == '' or str(v) in ('undefined', 'null'):
                continue
            items.append('%s=%s' % (k, v))
        g = '&'.join(items)
        h = 'key=%s&t=%s' % (self.SIGN_KEY, t)
        if g:
            h = '%s&%s' % (g, h)
        # 站点算法：SHA1(MD5(h).toString()).toString()
        return self._sha1(self._md5(h))

    def _api_get(self, path, params):
        t = str(int(time.time() * 1000))
        sign = self._sign(params, t)
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None and v != ''})
        url = '%s%s%s?%s' % (self.host, self.api_prefix, path, qs)
        headers = dict(self.headers)
        headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Origin': self.host,
            'client-type': '1',
            'authorization': '',
            'deviceId': self.device_id or str(uuid.uuid4()),
            'sign': sign,
            't': t,
        })
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15, context=self.ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print('api_get error', path, e)
            return None

    def homeContent(self, filter):
        result = {'class': list(self.CLASSES)}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        try:
            html = self._get(self.host + '/')
            return {'list': self._parse_list(html)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        url = '%s/vod/show/id/%s/page/%s' % (self.host, tid, page)
        html = self._get(url)
        items = self._parse_list(html)
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if len(items) >= 20 else page,
            'limit': 40,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg='1'):
        page = max(1, int(pg or 1))
        url = '%s/vod/search/%s' % (self.host, urllib.parse.quote(str(key)))
        if page > 1:
            url += '?page=%s' % page
        html = self._get(url)
        items = self._parse_list(html)
        return {'list': items, 'page': page, 'pagecount': page + 1 if items else page}

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(r'href="(/detail/(\d+))"', html):
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            start = max(0, m.start() - 50)
            end = min(len(html), m.end() + 900)
            block = html[start:end]
            name = ''
            nm = re.search(r'(?:card-name|CardName|title)[^>]*>([\s\S]*?)<', block, re.I)
            if nm:
                name = re.sub(r'<[^>]+>', '', nm.group(1)).strip()
            if not name:
                nm = re.search(r'alt="([^"]+)"', block)
                if nm:
                    name = nm.group(1).strip()
            if not name:
                name = '影片' + vid
            pic = ''
            pm = re.search(r'(https://[^"\'\s)]+\.(?:jpg|jpeg|png|webp))', block, re.I)
            if pm:
                pic = pm.group(1)
            else:
                pm = re.search(r'url\(([^)]+)\)', block)
                if pm:
                    pic = pm.group(1).strip('\'"')
            remarks = ''
            rm = re.search(r'(?:remarks|tag|score|episode)[^>]*>([\s\S]*?)<', block, re.I)
            if rm:
                remarks = re.sub(r'<[^>]+>', '', rm.group(1)).strip()
            items.append({
                'vod_id': path,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        return items

    def _extract_detail_json(self, html):
        m = re.search(r'\\"vodId\\":(\d+)', html)
        if not m:
            m = re.search(r'"vodId":(\d+)', html)
        if not m:
            return None
        idx = m.start()
        chunk = html[idx:idx + 80000]
        unesc = chunk.replace('\\"', '"').replace('\\n', '\n')
        if not unesc.startswith('{'):
            unesc = '{' + unesc
        episode_list = []
        em = re.search(r'"episodeList"\s*:\s*(\[[\s\S]*?\])', unesc)
        if em:
            try:
                episode_list = json.loads(em.group(1))
            except Exception:
                episode_list = []

        def field(name):
            mm = re.search(r'"%s"\s*:\s*"((?:\\.|[^"\\])*)"' % name, unesc)
            if mm:
                try:
                    return json.loads('"' + mm.group(1) + '"')
                except Exception:
                    return mm.group(1)
            mm = re.search(r'"%s"\s*:\s*([^,}\]]+)' % name, unesc)
            if mm:
                return mm.group(1).strip().strip('"')
            return ''

        return {
            'vodId': m.group(1),
            'vodName': field('vodName'),
            'vodPic': field('vodPic'),
            'vodContent': field('vodContent') or field('vodBlurb'),
            'vodActor': field('vodActor'),
            'vodDirector': field('vodDirector'),
            'vodYear': field('vodYear'),
            'vodArea': field('vodArea'),
            'vodRemarks': field('vodRemarks'),
            'typeName': field('typeName'),
            'episodeList': episode_list,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        path = raw if str(raw).startswith('/') else '/detail/' + str(raw).replace('detail/', '')
        html = self._get(self.host + path)
        data = self._extract_detail_json(html)
        if not data:
            # API 兜底
            vid = re.search(r'(\d+)', path)
            if vid:
                api = self._api_get('/anonymous/video/detail', {'id': vid.group(1)})
                if api and api.get('code') == 200 and api.get('data'):
                    d = api['data']
                    data = {
                        'vodId': str(d.get('vodId') or vid.group(1)),
                        'vodName': d.get('vodName') or '',
                        'vodPic': d.get('vodPic') or '',
                        'vodContent': d.get('vodContent') or d.get('vodBlurb') or '',
                        'vodActor': d.get('vodActor') or '',
                        'vodDirector': d.get('vodDirector') or '',
                        'vodYear': d.get('vodYear') or '',
                        'vodArea': d.get('vodArea') or '',
                        'vodRemarks': d.get('vodRemarks') or '',
                        'typeName': d.get('typeName') or '',
                        'episodeList': d.get('episodeList') or [],
                    }
        if not data:
            return {'list': []}
        vod_id = str(data.get('vodId') or '')
        play_urls = []
        for ep in data.get('episodeList') or []:
            nid = ep.get('nid')
            name = str(ep.get('name') or '')
            if not nid:
                continue
            play_urls.append('%s$%s@%s' % (name or str(nid), vod_id, nid))
        if not play_urls:
            for m in re.finditer(r'href="(/vod/play/%s/sid/(\d+))"[^>]*>([\s\S]*?)</a>' % re.escape(vod_id), html):
                name = re.sub(r'<[^>]+>', '', m.group(3)).strip() or m.group(2)
                play_urls.append('%s$%s@%s' % (name, vod_id, m.group(2)))
        return {'list': [{
            'vod_id': '/detail/' + vod_id,
            'vod_name': data.get('vodName') or '',
            'vod_pic': data.get('vodPic') or '',
            'vod_content': data.get('vodContent') or '',
            'vod_actor': data.get('vodActor') or '',
            'vod_director': data.get('vodDirector') or '',
            'vod_year': data.get('vodYear') or '',
            'vod_area': data.get('vodArea') or '',
            'vod_remarks': data.get('vodRemarks') or '',
            'type_name': data.get('typeName') or '',
            'vod_play_from': '枫叶影视',
            'vod_play_url': '#'.join(play_urls),
        }]}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id)
        vod_id, nid = '', ''
        if '@' in raw:
            vod_id, nid = raw.split('@', 1)
        else:
            mm = re.search(r'/vod/play/(\d+)/.*?(\d+)$', raw)
            if mm:
                vod_id, nid = mm.group(1), mm.group(2)
            else:
                vod_id = raw
        headers = {
            'User-Agent': self.UA,
            'Referer': self.host + '/',
        }
        play_url = ''
        # 多清晰度：优先免登录(flag=true / needLogin=false)，否则取最高分辨率
        if nid and vod_id:
            data = self._api_get('/anonymous/v2/video/episode/url', {
                'id': str(vod_id),
                'nid': str(nid),
            })
            if data and data.get('code') == 200:
                d = data.get('data') or {}
                lst = d.get('list') if isinstance(d, dict) else None
                if isinstance(lst, list) and lst:
                    free = [x for x in lst if x.get('flag') is True or x.get('needLogin') is False]
                    pick = None
                    if free:
                        pick = sorted(free, key=lambda x: int(x.get('resolution') or 0), reverse=True)[0]
                    else:
                        pick = sorted(lst, key=lambda x: int(x.get('resolution') or 0), reverse=True)[0]
                    play_url = (pick or {}).get('url') or ''
                elif isinstance(d, str) and d.startswith('http'):
                    play_url = d
                elif isinstance(d, dict):
                    play_url = d.get('url') or d.get('playUrl') or ''
        if play_url:
            return {
                'parse': 0,
                'jx': 0,
                'url': play_url,
                'header': headers,
            }
        page = '%s/vod/play/%s/sid/%s' % (self.host, vod_id, nid) if nid else '%s/detail/%s' % (self.host, vod_id)
        return {'parse': 1, 'jx': 0, 'url': page, 'header': headers}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

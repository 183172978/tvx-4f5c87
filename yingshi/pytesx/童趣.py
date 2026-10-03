# -*- coding: utf-8 -*-
"""
童趣 (boosj.com)
- 列表: /search_res_3362_{cate}_{page}_{by}.html{area}
- 播放: gslb.boosj.com/ipv2.json → gslb 拼参
参考 爱看机器人.py 结构
"""
import sys
import re
import json
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


HOST = 'https://www.boosj.com'
SEARCH_API = 'https://search.boosj.com/m_ajax'
GSLB_JSON = 'https://gslb.boosj.com/ipv2.json'
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
HEADERS = {
    'User-Agent': UA,
    'Referer': HOST + '/',
    'Accept': 'text/html,application/json,application/xhtml+xml,*/*',
}

CLASS_NAMES = '全部&辅食&动画&儿童舞蹈&少儿英语&儿童歌曲&才艺&播视自制&故事&亲子教育&美术&其他&儿童游戏&识物&绘本&古诗&科普&儿童玩具&播视童趣儿童玩具'.split('&')
CLASS_URLS = '_&_28&_582&_3364&_3366&_3367&_3622&_3782&_3822&_3842&_4402&_4583&_4762&_4842&_4843&_4844&_4845&_5102&_5142'.split('&')


class Spider(Spider):

    def init(self, extend=''):
        self.headers = dict(HEADERS)

    def getName(self):
        return '童趣'

    def isVideoFormat(self, url):
        return any(x in str(url) for x in ['.m3u8', '.mp4', '.flv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _get(self, url):
        r = self.fetch(url, headers=self.headers)
        return r.text if hasattr(r, 'text') else str(r)

    def _get_json(self, url):
        try:
            return json.loads(self._get(url))
        except Exception:
            return {}

    def homeContent(self, filter=False):
        classes = []
        filters = {}
        age = [
            {'n': '全部', 'v': ''},
            {'n': '6岁以上', 'v': '?p367=370'},
            {'n': '3~6岁', 'v': '?p367=369'},
            {'n': '0~3岁', 'v': '?p367=368'},
        ]
        sort = [
            {'n': '全部', 'v': ''},
            {'n': '最新发布', 'v': 'lately'},
            {'n': '最多播放', 'v': 'pop'},
            {'n': '最多评论', 'v': 'view'},
        ]
        for name, tid in zip(CLASS_NAMES, CLASS_URLS):
            classes.append({'type_id': tid, 'type_name': name})
            filters[tid] = [
                {'name': '年龄段', 'key': 'area', 'value': age},
                {'name': '排序', 'key': 'by', 'value': sort},
            ]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        try:
            html = self._get(HOST + '/baby/')
            return {'list': self._parse_recommend(html)[:24]}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        pg = max(int(str(pg) or 1), 1)
        extend = extend or {}
        try:
            url = self._build_list_url(tid, pg, extend)
            html = self._get(url)
            items = self._parse_list(html)
            return {
                'list': items, 'page': pg,
                'pagecount': pg + 1 if len(items) >= 6 else pg,
                'limit': 12, 'total': 9999,
            }
        except Exception as e:
            print('category', e)
            return {'list': [], 'page': pg, 'pagecount': 0}

    def detailContent(self, ids):
        vid = re.sub(r'\.html$', '', str(ids[0] if ids else ''))
        vid = re.sub(r'^.*/', '', vid)
        try:
            html = self._get(f'{HOST}/{vid}.html')
            name = ''
            m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                name = re.split(r'[-_|]', m.group(1))[0].strip()
            if not name:
                m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
                if m:
                    name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            pic = ''
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
            if m:
                pic = self._abs(m.group(1))
            content = ''
            m = re.search(r'class="[^"]*intro[^"]*"[^>]*>([\s\S]*?)</div>', html, re.I)
            if m:
                content = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            return {'list': [{
                'vod_id': vid,
                'vod_name': name or f'视频{vid}',
                'vod_pic': pic,
                'vod_content': content,
                'vod_remarks': '童趣',
                'vod_play_from': '童趣',
                'vod_play_url': f'播放${vid}',
            }]}
        except Exception as e:
            print('detail', e)
            return {'list': []}

    def searchContent(self, key, quick=False, pg=1):
        pg = max(int(str(pg) or 1), 1)
        try:
            url = f'{SEARCH_API}?q={quote(key)}&p={pg}&typeId=3362'
            data = self._get_json(url)
            result = ((data.get('body') or {}).get('result')) or data.get('result') or []
            items = []
            for it in result if isinstance(result, list) else []:
                vid = it.get('id') or it.get('resourceId')
                if not vid:
                    continue
                items.append({
                    'vod_id': str(vid),
                    'vod_name': it.get('resourceName') or it.get('name') or '',
                    'vod_pic': it.get('imageUrl') or it.get('pic') or '',
                    'vod_remarks': it.get('clickNumStr') or it.get('intro') or '',
                })
            return {'list': items, 'page': pg}
        except Exception as e:
            print('search', e)
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            m = re.search(r'\d+', str(id or ''))
            vid = m.group(0) if m else str(id or '')
            body = self._get_json(GSLB_JSON)
            if not body or not body.get('gslb'):
                return {'parse': 1, 'url': f'{HOST}/{vid}.html', 'header': self.headers}
            body['_id'] = vid
            base = body['gslb']
            params = []
            for k, v in body.items():
                if k == 'gslb':
                    continue
                params.append(f'{quote(str(k))}={quote("" if v is None else str(v))}')
            sep = '&' if '?' in base else '?'
            play_json = self._get_json(base + sep + '&'.join(params))
            if not play_json or not play_json.get('url'):
                return {'parse': 1, 'url': f'{HOST}/{vid}.html', 'header': self.headers}
            # 原规则: json.url + '?' + json.t
            t = play_json.get('t')
            if t is not None and t != '':
                play_url = f"{play_json['url']}?{t}"
            else:
                play_url = str(play_json['url'])
            return {
                'parse': 0, 'jx': 0, 'url': play_url,
                'header': {'User-Agent': UA, 'Referer': HOST + '/'},
            }
        except Exception as e:
            print('play', e)
            return {'parse': 1, 'url': str(id), 'header': self.headers}

    def _build_list_url(self, tid, pg, extend):
        cate = str(tid or '_')
        by = str(extend.get('by') or '')
        area = str(extend.get('area') or '')
        cate_part = cate if cate.startswith('_') else '_' + cate
        return f'{HOST}/search_res_3362{cate_part}_{pg}_{by}.html{area}'

    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        for block in re.split(r'class="[^"]*bj-col4[^"]*"', html, flags=re.I)[1:]:
            block = block[:2000]
            hm = re.search(r'href\s*=\s*["\']([^"\']+(\d+)\.html)["\']', block, re.I)
            if not hm:
                continue
            vid_m = re.search(r'(\d+)\.html', hm.group(1))
            vid = vid_m.group(1) if vid_m else ''
            if not vid or vid in seen:
                continue
            seen.add(vid)
            name = ''
            tm = re.search(r'title\s*=\s*["\']([^"\']+)["\']', block, re.I)
            if tm:
                name = tm.group(1).strip()
            if not name:
                continue
            pic = ''
            pm = re.search(r'data-original\s*=\s*["\']([^"\']+)["\']', block, re.I) or \
                 re.search(r'src\s*=\s*["\']([^"\']+)["\']', block, re.I)
            if pm:
                pic = self._abs(pm.group(1))
            remarks = ''
            rm = re.search(r'class="[^"]*played[^"]*"[^>]*>([\s\S]*?)</', block, re.I)
            if rm:
                remarks = re.sub(r'<[^>]+>', '', rm.group(1)).strip()
            items.append({'vod_id': vid, 'vod_name': name, 'vod_pic': pic, 'vod_remarks': remarks})
        return items

    def _parse_recommend(self, html):
        items, seen = [], set()
        for m in re.finditer(r'<div[^>]+class="[^"]*pubpic[^"]*"[^>]*>([\s\S]*?)</div>', html or '', re.I):
            block = m.group(1)
            hm = re.search(r'href\s*=\s*["\']([^"\']+(\d+)\.html)["\']', block, re.I)
            if not hm:
                continue
            vid_m = re.search(r'(\d+)\.html', hm.group(1))
            vid = vid_m.group(1) if vid_m else ''
            if not vid or vid in seen:
                continue
            seen.add(vid)
            tm = re.search(r'title\s*=\s*["\']([^"\']+)["\']', block, re.I)
            if not tm:
                continue
            pic = ''
            pm = re.search(r'src\s*=\s*["\']([^"\']+)["\']', block, re.I)
            if pm:
                pic = self._abs(pm.group(1))
            items.append({'vod_id': vid, 'vod_name': tm.group(1).strip(), 'vod_pic': pic, 'vod_remarks': ''})
        return items or self._parse_list(html)

    def _abs(self, u):
        u = str(u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if re.match(r'^https?:', u, re.I):
            return u
        if u.startswith('/'):
            return HOST + u
        return HOST + '/' + u

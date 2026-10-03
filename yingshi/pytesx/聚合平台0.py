# -*- coding: utf-8 -*-
# 聚合平台0 - 成人资源 API 聚合
# 对应 聚合平台0.js；结构参考 ppnix.py
import json
import re
import sys
from urllib.parse import quote, urlencode

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):
    def init(self, extend=""):
        pass

    def getName(self):
        return '聚合平台0'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv'))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    UA = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    headers = {'User-Agent': UA}

    # type: 1 = 标准 provide/vod JSON（默认）
    # type: 3 = 大地 feifei2（data/vod_url/vod_play/list分类）
    SOURCES = {
        's1': {'name': '🎬香蕉', 'api': 'https://www.xiangjiaozyw.com/api.php/provide/vod/'},
        's2': {'name': '💧番茄', 'api': 'http://fhapi9.com/api.php/provide/vod/'},
        's3': {'name': '🧸嘿嘿', 'api': 'https://api.heiapi.cc/api.php/provide/vod/'},
        's4': {'name': '📺鲨鱼', 'api': 'https://shayuzy5.com/api.php/provide/vod/'},
        's5': {'name': '🔥麻花', 'api': 'https://19q.cc/api.php/provide/vod/'},
        's6': {'name': '📺搜AV', 'api': 'https://souavzy.net/api.php/provide/vod/'},
        's7': {'name': '📺精品', 'api': 'https://www.jingpinx.com/api.php/provide/vod/'},
        's8': {'name': '⚡极品', 'api': 'https://jipinvip1.com/api.php/provide/vod/'},
        's9': {'name': '📺美少女', 'api': 'https://www.msnii.com/api/json.php'},
        's10': {'name': '📺饮水机', 'api': 'https://www.xrbsp.com/api/json.php'},
        's11': {'name': '📺香奶儿', 'api': 'https://www.gdlsp.com/api/json.php'},
        's12': {'name': '🐯白嫖', 'api': 'https://www.kxgav.com/api/json.php'},
        's13': {'name': '📺小师妹', 'api': 'https://www.afasu.com/api/json.php'},
        's14': {'name': '📺潢AV', 'api': 'https://www.pgxdy.com/api/json.php'},
        's15': {'name': '📺杏吧', 'api': 'https://api.xgbbk8.com/api.php/provide/vod/'},
        's16': {'name': '📺CK资源', 'api': 'https://ckzy.me/api.php/provide/vod'},
        's17': {'name': '📺越南', 'api': 'https://vnzyz.com/api.php/provide/vod'},
        's18': {'name': '📺15', 'api': 'https://155api.com/api.php/provide/vod/'},
        's19': {'name': '📺91AV', 'api': 'https://91av.cyou/api.php/provide/vod/'},
        's20': {'name': '🌕红楼', 'api': 'https://www.hlzyapi.vip/api.php/provide/vod/'},
        's21': {'name': '📺小鸡', 'api': 'https://api.xiaojizy.live/provide/vod/'},
        's22': {'name': '📺大奶', 'api': 'https://apidanaizi.com/api.php/provide/vod/'},
        's23': {'name': '📺豆豆', 'api': 'https://api.douapi.cc/api.php/provide/vod/'},
        's24': {'name': '📺黑料', 'api': 'https://heiliaozyapi.com/api.php/provide/vod/'},
        's25': {'name': '🌸仓库', 'api': 'https://hsckzy888.com/api.php/provide/vod/'},
        's26': {'name': '🐮玉兔', 'api': 'https://apiyutu.com/api.php/provide/vod'},
        's27': {'name': '☁️精东', 'api': 'http://chujia.cc/api.php/provide/vod/'},
        's28': {'name': '🏎奶香', 'api': 'https://naixxzy.com/api.php/provide/vod'},
        's29': {'name': '🦅乐播', 'api': 'https://lbapi9.com/api.php/provide/vod'},
        's30': {'name': '⚡JKUN', 'api': 'https://jkunzyapi.com/api.php/provide/vod'},
        's31': {'name': '👑桃花', 'api': 'https://thzy1.me/api.php/provide/vod/'},
        's32': {'name': '🍃百花', 'api': 'https://bhziyuan.com/api.php/provide/vod/'},
        's33': {'name': '🐾老色', 'api': 'https://apilsbzy1.com/api.php/provide/vod/'},
        's34': {'name': '🐾辣椒', 'api': 'https://apilj.com/api.php/provide/vod'},
        's35': {'name': '🐾javbus', 'api': 'https://javbus.sbs/api.php/provide/vod/'},
        's36': {'name': '🐾奥斯卡', 'api': 'https://aosikazy8.com/api.php/provide/vod'},
        's37': {'name': '🐾火速', 'api': 'https://api.huosuapi.cc/api.php/provide/vod/'},
        's38': {'name': '🐾聚合2', 'api': 'http://150.109.94.44:1112/api.php/provide/vod/'},
        's39': {'name': '🐾CK百货', 'api': 'https://ckbh1.xyz/api.php/provide/vod/'},
        's40': {'name': '🐾番茄', 'api': 'https://fqzy.me/api.php/provide/vod/'},
        's41': {'name': '🐾98', 'api': 'https://jp98.vip/api.php/provide/vod/'},
        's42': {'name': '🐾森林', 'api': 'https://slapibf.com/api.php/provide/vod/'},
        's43': {'name': '🐾大地', 'api': 'https://dadiapi.com/feifei2/', 'type': 3},
        's44': {'name': '🐾色猫', 'api': 'https://caiji.semaozy.net/inc/apijson_vod.php'},
        's45': {'name': '🐾滴滴', 'api': 'https://api.ddapi.cc/api.php/provide/vod/'},
        's46': {'name': '🐾91', 'api': 'https://91md.me/api.php/provide/vod/'},
        's47': {'name': '🐾免费', 'api': 'https://yuanlib.com/api.php/provide/vod/'},
        's48': {'name': '🐾细胞', 'api': 'https://www.xxibaozyw.com/api.php/provide/vod/'},
        's49': {'name': '📺湿园', 'api': 'https://xxavs.com/api.php/provide/vod'},
    }

    def _text(self, v):
        return str(v if v is not None else '').strip()

    def _build_url(self, base, params=None):
        url = self._text(base).strip(' "\'')
        params = params or {}
        keys = [k for k, v in params.items() if v is not None and str(v) != '']
        if not keys:
            return url
        qs = urlencode({k: str(params[k]) for k in keys})
        return url + ('&' if '?' in url else '?') + qs

    def _request(self, url):
        try:
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.headers, timeout=6, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _safe_json(self, s):
        try:
            if not s:
                return None
            return json.loads(s)
        except Exception:
            return None

    def _fix_pic(self, url):
        url = self._text(url)
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return ''

    def _normalize_vod(self, item):
        if not item or not isinstance(item, dict):
            return item
        o = dict(item)
        if not o.get('vod_play_from') and o.get('vod_play'):
            o['vod_play_from'] = o['vod_play']
        if not o.get('vod_play_url') and o.get('vod_url'):
            o['vod_play_url'] = o['vod_url']
        if not o.get('vod_id') and o.get('id'):
            o['vod_id'] = o['id']
        if not o.get('vod_name') and o.get('name'):
            o['vod_name'] = o['name']
        if not o.get('vod_name') and o.get('title'):
            o['vod_name'] = o['title']
        if not o.get('vod_pic') and o.get('pic'):
            o['vod_pic'] = o['pic']
        if not o.get('vod_remarks') and o.get('remarks'):
            o['vod_remarks'] = o['remarks']
        if not o.get('vod_remarks') and o.get('note'):
            o['vod_remarks'] = o['note']
        if not o.get('vod_remarks') and o.get('vod_continu'):
            o['vod_remarks'] = o['vod_continu']
        if not o.get('vod_content') and o.get('content'):
            o['vod_content'] = o['content']
        if not o.get('vod_year') and o.get('d_year'):
            o['vod_year'] = o['d_year']
        if not o.get('type_name') and o.get('list_name'):
            o['type_name'] = o['list_name']
        o['vod_pic'] = self._fix_pic(o.get('vod_pic'))
        return o

    def _parse_response(self, html):
        empty = {'list': [], 'page': 1, 'pagecount': 1, 'pagesize': 20, 'total': 0, 'class': []}
        if not html:
            return empty
        j = self._safe_json(html)
        if not j:
            return empty
        # 大地 feifei2
        if j.get('status') is not None and (isinstance(j.get('data'), list) or j.get('page')):
            page_obj = j.get('page') or {}
            classes = []
            if isinstance(j.get('list'), list) and j['list']:
                first = j['list'][0]
                if first and (first.get('list_id') is not None or first.get('list_name')):
                    classes = [{
                        'type_id': self._text(c.get('list_id') or c.get('type_id') or c.get('id')),
                        'type_name': self._text(c.get('list_name') or c.get('type_name') or c.get('name')),
                    } for c in j['list']]
            raw = j['data'] if isinstance(j.get('data'), list) else []
            return {
                'list': [self._normalize_vod(x) for x in raw],
                'page': int(page_obj.get('pageindex') or page_obj.get('page') or 1),
                'pagecount': int(page_obj.get('pagecount') or 1),
                'pagesize': int(page_obj.get('pagesize') or 20),
                'total': int(page_obj.get('recordcount') or page_obj.get('total') or len(raw)),
                'class': classes,
            }
        # 标准 provide
        classes = j.get('class') if isinstance(j.get('class'), list) else []
        classes = [{
            'type_id': self._text(c.get('type_id') or c.get('list_id') or c.get('id')),
            'type_name': self._text(c.get('type_name') or c.get('list_name') or c.get('name')),
        } for c in classes]
        raw = j.get('list') if isinstance(j.get('list'), list) else []
        if raw and raw[0] and raw[0].get('list_id') is not None and not raw[0].get('vod_id') and not raw[0].get('vod_name'):
            classes = [{
                'type_id': self._text(c.get('list_id') or c.get('type_id')),
                'type_name': self._text(c.get('list_name') or c.get('type_name')),
            } for c in raw]
            raw = []
        return {
            'list': [self._normalize_vod(x) for x in raw],
            'page': int(j.get('page') or 1),
            'pagecount': int(j.get('pagecount') or 1),
            'pagesize': int(j.get('limit') or j.get('pagesize') or 20),
            'total': int(j.get('total') or 0),
            'class': classes,
        }

    def _clean_item(self, item, source_key, source_name, is_detail=False):
        o = self._normalize_vod(dict(item))
        if not is_detail:
            o['vod_id'] = '%s@@%s' % (source_key, self._text(o.get('vod_id')))
        rem = self._text(o.get('vod_remarks'))
        o['vod_remarks'] = '%s | %s' % (source_name, rem)
        from_arr = [s.strip() for s in self._text(o.get('vod_play_from')).split('$$$') if s.strip()]
        url_arr = [s.strip() for s in self._text(o.get('vod_play_url')).split('$$$')]
        if from_arr:
            from_arr = [x if x.startswith(source_name) else '%s-%s' % (source_name, x) for x in from_arr]
        if not from_arr and any(url_arr):
            from_arr = ['%s-线路%d' % (source_name, i + 1) for i in range(len(url_arr))]
        if from_arr and url_arr:
            while len(url_arr) < len(from_arr):
                url_arr.append('')
            while len(from_arr) < len(url_arr):
                from_arr.append('%s-线路%d' % (source_name, len(from_arr) + 1))
        o['vod_play_from'] = '$$$'.join(from_arr)
        o['vod_play_url'] = '$$$'.join(url_arr)
        o.pop('vod_down_from', None)
        o.pop('vod_down_url', None)
        return o

    def _load_filter(self, source_key, source_obj):
        url = self._build_url(source_obj['api'], {'ac': 'list'})
        data = self._parse_response(self._request(url))
        vals = [{'n': '全部(最新)', 'v': ''}]
        for c in (data.get('class') or []):
            cid = self._text(c.get('type_id'))
            name = self._text(c.get('type_name'))
            if cid or name:
                vals.append({'n': name or cid, 'v': cid})
        return vals

    def homeContent(self, filter):
        # 只返回源列表，不逐个请求分类（否则 40+ 源会卡死加载）
        classes = []
        filters = {}
        default_vals = [{'n': '全部(最新)', 'v': ''}]
        for sk, so in self.SOURCES.items():
            classes.append({'type_id': sk, 'type_name': so['name']})
            filters[sk] = [{'key': 'cateId', 'name': '分类', 'value': list(default_vals)}]
        return {'class': classes, 'filters': filters if filter else {}}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        source = self.SOURCES.get(str(tid))
        if not source:
            return {'list': [], 'page': pg, 'pagecount': 0}
        cate_id = ''
        if isinstance(extend, dict):
            cate_id = self._text(extend.get('cateId'))
        elif isinstance(filter, dict):
            cate_id = self._text(filter.get('cateId'))
        stype = source.get('type') or 1
        if stype == 3:
            params = {'ac': 'videolist', 'pg': pg}
            if cate_id:
                params['t'] = cate_id
            url = self._build_url(source['api'], params)
        else:
            params = {'ac': 'detail', 'pg': pg}
            if cate_id:
                params['t'] = cate_id
            url = self._build_url(source['api'], params)
        data = self._parse_response(self._request(url))
        if stype != 3 and not data.get('list'):
            params2 = {'ac': 'videolist', 'pg': pg}
            if cate_id:
                params2['t'] = cate_id
            data2 = self._parse_response(self._request(self._build_url(source['api'], params2)))
            if data2.get('list'):
                data = data2
        out = []
        for it in (data.get('list') or []):
            cleaned = self._clean_item(it, tid, source['name'], False)
            cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
            out.append(cleaned)
        return {
            'list': out,
            'page': int(data.get('page') or pg),
            'pagecount': int(data.get('pagecount') or 1),
            'limit': int(data.get('pagesize') or 20),
            'total': int(data.get('total') or len(out)),
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        if '@@' not in str(raw):
            return {'list': []}
        source_key, real_id = str(raw).split('@@', 1)
        source = self.SOURCES.get(source_key)
        if not source:
            return {'list': []}
        stype = source.get('type') or 1
        if stype == 3:
            html = self._request(self._build_url(source['api'], {'ac': 'videolist', 'ids': real_id}))
            tmp = self._parse_response(html)
            first = (tmp.get('list') or [None])[0]
            if not first or not self._text(first.get('vod_play_url') or first.get('vod_url')):
                html2 = self._request(self._build_url(source['api'], {'ac': 'detail', 'ids': real_id}))
                if html2:
                    html = html2
        else:
            html = self._request(self._build_url(source['api'], {'ac': 'detail', 'ids': real_id}))
            tmp = self._parse_response(html)
            first = (tmp.get('list') or [None])[0]
            if not first or not self._text(first.get('vod_play_url')):
                html2 = self._request(self._build_url(source['api'], {'ac': 'videolist', 'ids': real_id}))
                d2 = self._parse_response(html2)
                if (d2.get('list') or [None])[0] and self._text((d2['list'][0].get('vod_play_url') or '')):
                    html = html2
        data = self._parse_response(html)
        out = []
        for it in (data.get('list') or []):
            cleaned = self._clean_item(it, source_key, source['name'], True)
            cleaned['vod_id'] = str(raw)
            cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
            if not self._text(cleaned.get('vod_play_from')) and self._text(cleaned.get('vod_play_url')):
                segs = self._text(cleaned.get('vod_play_url')).split('$$$')
                cleaned['vod_play_from'] = '$$$'.join(
                    ['%s-线路%d' % (source['name'], i + 1) for i in range(len(segs))]
                )
            out.append(cleaned)
        return {'list': out}

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = self._text(key)
        if not key:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 40, 'total': 0}
        result = []
        max_page = 1
        items = list(self.SOURCES.items())

        def _one(sk_so):
            sk, so = sk_so
            try:
                stype = so.get('type') or 1
                if stype in (0, 3):
                    url = self._build_url(so['api'], {'ac': 'videolist', 'wd': key, 'pg': pg})
                elif stype == 2:
                    url = self._build_url(so['api'], {'wd': key, 'pg': pg})
                else:
                    url = self._build_url(so['api'], {'ac': 'detail', 'wd': key, 'pg': pg})
                data = self._parse_response(self._request(url))
                if stype not in (0, 2, 3) and not data.get('list'):
                    data2 = self._parse_response(
                        self._request(self._build_url(so['api'], {'ac': 'videolist', 'wd': key, 'pg': pg}))
                    )
                    if data2.get('list'):
                        data = data2
                lst = []
                for it in (data.get('list') or []):
                    cleaned = self._clean_item(it, sk, so['name'], False)
                    cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
                    lst.append(cleaned)
                return lst, int(data.get('pagecount') or 1)
            except Exception as e:
                print('search skip', sk, e)
                return [], 1

        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = [pool.submit(_one, it) for it in items]
                for fut in as_completed(futs, timeout=25):
                    try:
                        lst, pc = fut.result()
                        result.extend(lst)
                        if pc > max_page:
                            max_page = pc
                    except Exception:
                        pass
        except Exception:
            for it in items[:15]:
                lst, pc = _one(it)
                result.extend(lst)
                if pc > max_page:
                    max_page = pc
        return {
            'list': result,
            'page': pg,
            'pagecount': max_page,
            'limit': 40,
            'total': 9999,
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = self._text(id)
        need_parse = not self.isVideoFormat(play_url)
        return {
            'parse': 1 if need_parse else 0,
            'url': play_url,
            'header': {'User-Agent': self.UA},
        }

    def localProxy(self, param):
        return None

# -*- coding: utf-8 -*-
# 豆瓣导航搜索版 - 仅分类/推荐/搜索
# 使用 movie.douban.com / m.douban.com 公开接口
# 壳契约: class Spider 无继承 · 位置参数
import json
import re
import urllib.parse
import urllib.request

class Spider:
    def __init__(self):
        self.jhost = 'https://movie.douban.com'
        self.mhost = 'https://m.douban.com/rexxar/api/v2'
        self.ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.ua_m = ('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')

    def init(self, extend=''):
        return None

    def getName(self):
        return '豆瓣导航'

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return None

    def localProxy(self, param):
        return None

    def action(self, action):
        return None

    # type_id, 名称, 接口类型 j/c, 参数
    CATS = [
        ('movie_hot', '电影热门', 'j', {'type': 'movie', 'tag': '热门'}),
        ('tv_hot', '剧集热门', 'j', {'type': 'tv', 'tag': '热门'}),
        ('show_hot', '综艺热门', 'j', {'type': 'tv', 'tag': '综艺'}),
        ('movie_top', '电影高分', 'j', {'type': 'movie', 'tag': '豆瓣高分'}),
        ('tv_top', '剧集高分', 'j', {'type': 'tv', 'tag': '豆瓣高分'}),
        ('movie_new', '最新电影', 'j', {'type': 'movie', 'tag': '最新'}),
        ('tv_new', '最新剧集', 'j', {'type': 'tv', 'tag': '最新'}),
        ('movie_cn', '华语电影', 'j', {'type': 'movie', 'tag': '华语'}),
        ('movie_west', '欧美电影', 'j', {'type': 'movie', 'tag': '欧美'}),
        ('movie_jp', '日本电影', 'j', {'type': 'movie', 'tag': '日本'}),
        ('movie_kr', '韩国电影', 'j', {'type': 'movie', 'tag': '韩国'}),
        ('tv_cn', '国产剧', 'j', {'type': 'tv', 'tag': '国产剧'}),
        ('tv_us', '美剧', 'j', {'type': 'tv', 'tag': '美剧'}),
        ('tv_kr', '韩剧', 'j', {'type': 'tv', 'tag': '韩剧'}),
        ('tv_jp', '日剧', 'j', {'type': 'tv', 'tag': '日剧'}),
        ('movie_coming', '即将上映', 'c', 'movie_coming_soon'),
        ('movie_showing', '正在热映', 'c', 'movie_showing'),
        ('tv_domestic', '国产剧榜', 'c', 'tv_domestic'),
        ('tv_american', '美剧榜', 'c', 'tv_american'),
        ('movie_top250', 'Top250', 'c', 'movie_top250'),
    ]

    def _open(self, url, headers=None, timeout=12):
        h = {'User-Agent': self.ua, 'Accept': 'application/json, text/plain, */*'}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', 'ignore')

    def _json(self, url, mobile=False):
        try:
            if mobile:
                headers = {
                    'User-Agent': self.ua_m,
                    'Referer': 'https://m.douban.com/movie/',
                    'Origin': 'https://m.douban.com',
                }
            else:
                headers = {
                    'User-Agent': self.ua,
                    'Referer': 'https://movie.douban.com/',
                }
            text = self._open(url, headers=headers)
            return json.loads(text) if text else {}
        except Exception as e:
            print('req fail', url, e)
            return {}

    def _j_subjects(self, typ, tag, start, count, sort='recommend'):
        url = ('%s/j/search_subjects?type=%s&tag=%s&sort=%s&page_limit=%d&page_start=%d' % (
            self.jhost,
            urllib.parse.quote(str(typ)),
            urllib.parse.quote(str(tag)),
            urllib.parse.quote(str(sort or 'recommend')),
            count, start,
        ))
        data = self._json(url, mobile=False)
        return (data or {}).get('subjects') or []

    def _collection(self, cid, start, count):
        url = ('%s/subject_collection/%s/items?start=%d&count=%d&items_only=1&for_mobile=1' % (
            self.mhost, cid, start, count))
        data = self._json(url, mobile=True)
        return (data or {}).get('subject_collection_items') or (data or {}).get('items') or []

    def _to_vod(self, item):
        if not isinstance(item, dict):
            return None
        vid = item.get('id') or item.get('target_id') or ''
        if not vid:
            return None
        title = item.get('title') or item.get('name') or ''
        pic = item.get('cover') or item.get('pic') or item.get('img') or ''
        if isinstance(pic, dict):
            pic = pic.get('url') or pic.get('normal') or pic.get('large') or ''
        rate = item.get('rate') or ''
        if not rate:
            rating = item.get('rating') or {}
            if isinstance(rating, dict):
                rate = rating.get('value') or ''
        year = str(item.get('year') or '')[:4]
        remarks = ('%s分' % rate) if rate else year
        return {
            'vod_id': str(vid),
            'vod_name': str(title),
            'vod_pic': str(pic),
            'vod_remarks': str(remarks),
            'vod_year': year,
        }

    def homeContent(self, filter):
        classes = [{'type_id': c[0], 'type_name': c[1]} for c in self.CATS]
        sort_filter = {
            'key': 'sort',
            'name': '排序',
            'value': [
                {'n': '热度', 'v': 'recommend'},
                {'n': '时间', 'v': 'time'},
                {'n': '评价', 'v': 'rank'},
            ],
        }
        filters = {}
        for c in self.CATS:
            if c[2] == 'j':
                filters[c[0]] = [sort_filter]
        # 首页同时带一批热门，避免部分壳只读 list
        try:
            items = self._j_subjects('movie', '热门', 0, 20, 'recommend')
            lst = [self._to_vod(x) for x in items if x]
            lst = [x for x in lst if x]
        except Exception:
            lst = []
        return {'class': classes, 'filters': filters, 'list': lst}

    def homeVideoContent(self):
        try:
            items = self._j_subjects('movie', '热门', 0, 20, 'recommend')
            lst = [self._to_vod(x) for x in items if x]
            return {'list': [x for x in lst if x]}
        except Exception as e:
            print('homeVideo', e)
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        start = (pg - 1) * 20
        sort = 'recommend'
        if isinstance(extend, dict):
            sort = str(extend.get('sort') or 'recommend')
        elif isinstance(extend, str) and extend.strip().startswith('{'):
            try:
                sort = str(json.loads(extend).get('sort') or 'recommend')
            except Exception:
                pass
        meta = None
        for c in self.CATS:
            if c[0] == str(tid):
                meta = c
                break
        items = []
        try:
            if meta is None:
                items = self._j_subjects('movie', '热门', start, 20, sort)
            elif meta[2] == 'j':
                p = meta[3]
                items = self._j_subjects(p['type'], p['tag'], start, 20, sort)
            else:
                items = self._collection(meta[3], start, 20)
        except Exception as e:
            print('category', e)
            items = []
        vods = [self._to_vod(x) for x in items if x]
        vods = [x for x in vods if x]
        return {
            'list': vods,
            'page': pg,
            'pagecount': 50,
            'limit': 20,
            'total': 1000,
        }

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ''
        else:
            vid = str(ids or '')
        m = re.search(r'\d+', vid)
        if m:
            vid = m.group(0)
        if not vid:
            return {'list': []}
        data = self._json('%s/movie/%s' % (self.mhost, vid), mobile=True)
        if not data or data.get('code') or not data.get('title'):
            data = self._json('%s/tv/%s' % (self.mhost, vid), mobile=True)
        if not data or not data.get('title'):
            return {'list': []}
        title = data.get('title') or ''
        pic_obj = data.get('pic') or data.get('cover') or {}
        if isinstance(pic_obj, dict):
            pic = pic_obj.get('normal') or pic_obj.get('large') or pic_obj.get('url') or ''
        else:
            pic = str(pic_obj or '')
        year = str(data.get('year') or '')[:4]
        rating = data.get('rating') or {}
        score = rating.get('value') if isinstance(rating, dict) else ''
        genres = '/'.join(data.get('genres') or [])
        countries = '/'.join(data.get('countries') or [])
        directors = '/'.join([x.get('name', '') for x in (data.get('directors') or [])[:5]])
        actors = '/'.join([x.get('name', '') for x in (data.get('actors') or [])[:8]])
        intro = data.get('intro') or data.get('card_subtitle') or ''
        remarks = ('%s分' % score) if score else ''
        content = '%s · %s\n%s\n导演: %s\n主演: %s\n\n%s' % (
            year, genres, countries, directors, actors, intro)
        return {'list': [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_year': year,
            'vod_remarks': remarks,
            'vod_content': content,
            'vod_actor': actors,
            'vod_director': directors,
            'type_name': genres,
            'vod_area': countries,
            'vod_play_from': '豆瓣导航',
            'vod_play_url': '请用其他源搜索同名影片播放$https://movie.douban.com/subject/%s/' % vid,
        }]}

    def searchContent(self, key, quick=False, pg='1', *args, **kwargs):
        pg = int(pg) if str(pg).isdigit() else 1
        start = (pg - 1) * 20
        key = str(key or '').strip()
        if not key:
            return {'list': []}
        vods = []
        try:
            url = '%s/j/subject_suggest?q=%s' % (self.jhost, urllib.parse.quote(key))
            data = self._json(url, mobile=False)
            items = data if isinstance(data, list) else []
            page_items = items[start:start + 20]
            for it in page_items:
                if not isinstance(it, dict):
                    continue
                t = it.get('type')
                if t and t not in ('movie', 'tv'):
                    continue
                v = self._to_vod({
                    'id': it.get('id'),
                    'title': it.get('title') or it.get('name'),
                    'cover': it.get('img') or it.get('cover'),
                    'rate': '',
                    'year': it.get('year') or '',
                })
                if v:
                    vods.append(v)
        except Exception as e:
            print('search', e)
        return {
            'list': vods,
            'page': pg,
            'pagecount': 10,
            'limit': 20,
            'total': 200,
        }

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 0, 'jx': 0, 'url': '', 'header': {}}

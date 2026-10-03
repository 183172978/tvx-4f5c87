#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网易公版影像典藏 https://public.163.com
站点已停更，数据仍可通过 active.163.com 表单接口获取。
分类: movie=电影, doc=纪录片, ani=动画片, his=珍贵史料
"""
import json
import re
import sys
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
    """网易公版影像典藏"""

    def __init__(self):
        self.siteUrl = 'https://public.163.com'
        self.hallUrl = 'https://wp.m.163.com/163/html/newsapp/time-hall/index.html'
        self.openUrl = 'https://open.163.com'
        self.apiHost = 'https://active.163.com'
        self.videoApi = 'https://so.v.163.com/mobile/getBatchOnlineVideo.do'
        self.userAgent = (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        )
        # 与前端 listTypeName 一致
        self.channels = {
            'movie': {'name': '电影', 'kinds': 'movie'},
            'doc': {'name': '纪录片', 'kinds': 'doc'},
            'ani': {'name': '动画片', 'kinds': 'ani'},
            'his': {'name': '珍贵史料', 'kinds': 'his'},
            'daily': {'name': '每日精读', 'kinds': 'daily'},
        }
        # 列表 / 详情 / 搜索 / 每日精读
        self.listApi = self.apiHost + '/service/form/v1/9347/view/1618.jsonp'
        self.entryApi = self.apiHost + '/service/form/v1/9347/{id}.jsonp'
        self.searchApi = self.apiHost + '/service/form/v1/9347/view/1619.jsonp'
        self.readApi = self.apiHost + '/service/form/v1/9344/view/1624.jsonp'
        self.countApi = self.apiHost + '/service/form/v1/9347/view/1619/count.jsonp'

    def getName(self):
        return '网易公版'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=12)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=12).read()

            class R:
                def __init__(self, raw):
                    self.text = raw.decode('utf-8', 'ignore')

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_text(self, url, params=None):
        resp = self.fetch(url, params=params)
        return getattr(resp, 'text', '') if resp else ''

    def fetch_jsonp(self, url, params=None):
        """解析 jsonp 或纯 JSON"""
        if params is None:
            params = {}
        params = dict(params)
        params.setdefault('callback', 'cb')
        text = self.fetch_text(url, params=params)
        if not text:
            return {}
        text = text.strip()
        # cb({...}); 或 cb([...]);
        m = re.search(r'^[a-zA-Z0-9_]+\s*\(\s*([\s\S]*)\s*\)\s*;?\s*$', text)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        try:
            return json.loads(text)
        except Exception:
            m2 = re.search(r'(\{[\s\S]+\}|\[[\s\S]+\])', text)
            if m2:
                try:
                    return json.loads(m2.group(1))
                except Exception:
                    pass
        return {}

    def _abs(self, u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u.replace('http://', 'https://')

    def _clean(self, s):
        return re.sub(r'<[^>]+>', '', str(s or '')).replace('&nbsp;', ' ').strip()

    def _map_item(self, it):
        if not isinstance(it, dict):
            return None
        vid = str(it.get('id') or it.get('vid') or '')
        name = it.get('title') or it.get('media_name') or it.get('name') or ''
        pic = it.get('cover_pic') or it.get('cover') or it.get('img') or it.get('imgpath') or ''
        remarks = ''
        year = (it.get('release_date') or '')[:4]
        length = it.get('film_length') or ''
        area = it.get('made_area') or ''
        parts = [p for p in (year, area, length) if p]
        remarks = ' / '.join(parts) if parts else (it.get('meida_type') or it.get('entry_kinds') or '公版')
        if not vid and not name:
            return None
        return {
            'vod_id': vid or name,
            'vod_name': self._clean(name) or vid,
            'vod_pic': self._abs(pic),
            'vod_remarks': str(remarks).strip(),
        }

    def _map_daily(self, it):
        if not isinstance(it, dict):
            return None
        mid = it.get('media_id') or ''
        tid = str(it.get('id') or mid or '')
        text = self._clean(it.get('text') or '')
        name = text[:40] + ('…' if len(text) > 40 else '') if text else tid
        date = it.get('date') or ''
        return {
            'vod_id': 'daily_' + tid + (('_' + mid) if mid else ''),
            'vod_name': name or date or tid,
            'vod_pic': '',
            'vod_remarks': date or '每日精读',
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            data = self.fetch_jsonp(self.listApi, {
                'param_entry_kinds': 'movie',
                'page': 1,
                'pageSize': 24,
            })
            for it in (data.get('list') or []):
                v = self._map_item(it)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        page_size = 20
        videos = []
        pagecount = pg
        total = 0
        try:
            tid = str(tid or 'movie')
            if tid == 'daily':
                data = self.fetch_jsonp(self.readApi, {
                    'page': pg,
                    'pageSize': page_size,
                })
                for it in (data.get('list') or []):
                    v = self._map_daily(it)
                    if v:
                        videos.append(v)
                paging = data.get('paging') or {}
                total = int(paging.get('total') or len(videos))
                next_p = paging.get('nextPage')
                pagecount = int(next_p or pg) if next_p else pg
            else:
                ch = self.channels.get(tid) or self.channels['movie']
                kinds = ch.get('kinds') or tid
                data = self.fetch_jsonp(self.listApi, {
                    'param_entry_kinds': kinds,
                    'page': pg,
                    'pageSize': page_size,
                })
                for it in (data.get('list') or []):
                    v = self._map_item(it)
                    if v:
                        videos.append(v)
                paging = data.get('paging') or {}
                total = int(paging.get('total') or len(videos))
                next_p = paging.get('nextPage')
                if next_p:
                    pagecount = max(pg, int(next_p))
                elif total > 0:
                    pagecount = max(1, (total + page_size - 1) // page_size)
                else:
                    pagecount = pg
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': page_size,
            'total': total or len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        page_size = 20
        videos = []
        pagecount = pg
        total = 0
        try:
            data = self.fetch_jsonp(self.searchApi, {
                'param_title': key,
                'page': pg,
                'pageSize': page_size,
                '_charset': 'UTF-8',
                '_decode': 'UTF-8',
            })
            for it in (data.get('list') or []):
                v = self._map_item(it)
                if v:
                    videos.append(v)
            paging = data.get('paging') or {}
            total = int(paging.get('total') or len(videos))
            next_p = paging.get('nextPage')
            if next_p:
                pagecount = max(pg, int(next_p))
            elif total > 0:
                pagecount = max(1, (total + page_size - 1) // page_size)
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': page_size,
            'total': total or len(videos),
        }

    def _get_video_url(self, vid):
        """通过 vid 拉取 m3u8 / mp4 播放地址"""
        if not vid:
            return ''
        try:
            # 接口返回纯 JSON
            text = self.fetch_text(self.videoApi, params={'vidstr': vid})
            if not text:
                return ''
            data = json.loads(text)
            if str(data.get('errString') or '') != 'success' and data.get('retCode') not in (0, '0'):
                return ''
            vlist = (data.get('data') or {}).get('video_list') or []
            if not vlist:
                return ''
            item = vlist[0]
            for key in (
                'm3u8SdUrl', 'm3u8HdUrl', 'm3u8ShdUrl',
                'mp4SdUrl', 'mp4HdUrl', 'mp4ShdUrl',
                'hdUrl', 'sdUrl',
            ):
                u = item.get(key) or ''
                if u and u.startswith('http'):
                    return u.replace('http://', 'https://')
            # video_data 内嵌
            vd = item.get('video_data') or {}
            for key in ('sd_url', 'hd_url'):
                u = vd.get(key) or ''
                if u and u.startswith('http'):
                    return u.replace('http://', 'https://')
        except Exception as e:
            print('获取播放地址失败: %s' % e)
        return ''

    def detailContent(self, ids):
        raw = str((ids or [''])[0])
        name, pic, desc, remarks, director, actor = raw, '', '', '公版影像', '', ''
        play_url = '播放$%s' % self.hallUrl
        vid_media = ''

        try:
            # 每日精读: daily_{id}_{media_id}
            if raw.startswith('daily_'):
                parts = raw.split('_')
                media_id = parts[-1] if len(parts) >= 3 else ''
                entry_id = parts[1] if len(parts) >= 2 else ''
                name = '每日精读'
                if media_id and media_id.startswith('V'):
                    play = self._get_video_url(media_id)
                    if play:
                        play_url = '播放$%s' % play
                return {'list': [{
                    'vod_id': raw,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': remarks,
                    'vod_actor': '',
                    'vod_director': '',
                    'vod_content': '网易公版每日精读。站点已停更，完整片可尝试时光放映厅。',
                    'vod_play_from': '网易公版',
                    'vod_play_url': play_url,
                }]}

            # 数字 id -> 词条详情
            if raw.isdigit():
                data = self.fetch_jsonp(self.entryApi.format(id=raw))
                it = data.get('value') or data
                if isinstance(it, dict) and it.get('title'):
                    name = self._clean(it.get('title') or name)
                    pic = self._abs(it.get('cover_pic') or '')
                    desc = self._clean(it.get('desc') or '')
                    director = self._clean(it.get('director') or '')
                    actor = self._clean(it.get('protagonist') or '')
                    year = (it.get('release_date') or '')[:4]
                    length = it.get('film_length') or ''
                    area = it.get('made_area') or ''
                    mtype = it.get('meida_type') or ''
                    remarks = ' / '.join([p for p in (year, area, length, mtype) if p]) or remarks
                    vid_media = it.get('vid') or ''
                    page_url = it.get('url') or ''
                    if vid_media:
                        play = self._get_video_url(vid_media)
                        if play:
                            play_url = '播放$%s' % play
                        elif page_url:
                            play_url = '播放$%s' % page_url
                    elif page_url:
                        play_url = '播放$%s' % page_url
            else:
                # 兼容旧版：直接把 url 当 id
                page = raw if raw.startswith('http') else self.siteUrl + '/'
                html = self.fetch_text(page)
                tm = re.search(r'<title>([^<]+)</title>', html or '')
                if tm:
                    name = re.sub(r'\s*[-_|].*$', '', tm.group(1)).strip() or name
                m3 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html or '')
                mp4 = re.search(r'https?://[^\s"\']+\.mp4[^\s"\']*', html or '')
                if m3:
                    play_url = '播放$%s' % m3.group(0).replace('\\/', '/')
                elif mp4:
                    play_url = '播放$%s' % mp4.group(0).replace('\\/', '/')
        except Exception as e:
            print('获取详情失败: %s' % e)

        return {'list': [{
            'vod_id': raw,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': remarks,
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': (desc or '网易公版影像典藏，站点已停更，完整片可尝试时光放映厅。').strip(),
            'vod_play_from': '网易公版',
            'vod_play_url': play_url,
        }]}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': 'https://public.163.com',
        }
        play = str(id or '')
        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        # 可能是 vid
        if re.match(r'^V[A-Z0-9]+$', play):
            u = self._get_video_url(play)
            if u:
                return {'parse': 0, 'jx': '0', 'url': u, 'header': header}

        if play.startswith('/'):
            play = self.siteUrl + play

        if play.startswith('http') and '163.com' in play:
            html = self.fetch_text(play)
            m3 = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4|flv)[^\s"\']*', html or '')
            if m3:
                return {
                    'parse': 0, 'jx': '0',
                    'url': m3.group(0).replace('\\/', '/').replace('http://', 'https://'),
                    'header': header,
                }

        if not play.startswith('http'):
            play = self.hallUrl
        return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mpd'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print('=== homeContent ===')
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    print('=== category movie ===')
    print(json.dumps(spider.categoryContent('movie', 1, {}, {}), ensure_ascii=False, indent=2)[:800])
    print('=== category doc ===')
    print(json.dumps(spider.categoryContent('doc', 1, {}, {}), ensure_ascii=False, indent=2)[:500])

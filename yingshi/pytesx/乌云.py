#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乌云影视 Spider  (wooyun.tv)
接口：/api/proxy?url=/movie/media/search 与 video/list
风格对齐爱奇艺.py
"""
import json
import re
import sys
import urllib.parse
import urllib.request

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
        self.siteUrl = 'https://wooyun.tv'
        self.proxyApi = 'https://wooyun.tv/api/proxy'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        )
        self.channels = {
            '1': {'name': '电影', 'topCode': 'movie'},
            '2': {'name': '电视剧', 'topCode': 'tv_series'},
            '3': {'name': '综艺', 'topCode': 'variety'},
            '4': {'name': '动漫', 'topCode': 'animation'},
            '72': {'name': '短剧', 'topCode': 'short_drama'},
            '5': {'name': '演唱会', 'topCode': 'concert'},
            '53': {'name': '纪录片', 'topCode': 'documentary'},
        }
        self.filters = self._build_filters()

    def _build_filters(self):
        item = [
            {
                'key': 'genre',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '动作', 'v': 'action'},
                    {'n': '喜剧', 'v': 'comedy'},
                    {'n': '剧情', 'v': 'drama'},
                    {'n': '爱情', 'v': 'romance'},
                    {'n': '惊悚', 'v': 'thriller'},
                    {'n': '恐怖', 'v': 'horror'},
                    {'n': '科幻', 'v': 'sci_fi'},
                    {'n': '奇幻', 'v': 'fantasy'},
                    {'n': '战争', 'v': 'war'},
                    {'n': '历史', 'v': 'history'},
                    {'n': '冒险', 'v': 'adventure'},
                    {'n': '犯罪', 'v': 'crime'},
                ],
            },
            {
                'key': 'region',
                'name': '地区',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '大陆', 'v': 'china'},
                    {'n': '香港', 'v': 'hongkong'},
                    {'n': '台湾', 'v': 'taiwan'},
                    {'n': '美国', 'v': 'usa'},
                    {'n': '英国', 'v': 'uk'},
                    {'n': '日本', 'v': 'japan'},
                    {'n': '韩国', 'v': 'korea'},
                ],
            },
            {
                'key': 'language',
                'name': '语言',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '中文', 'v': 'chinese'},
                    {'n': '英语', 'v': 'english'},
                    {'n': '日语', 'v': 'japanese'},
                    {'n': '韩语', 'v': 'korean'},
                    {'n': '法语', 'v': 'french'},
                    {'n': '德语', 'v': 'german'},
                    {'n': '泰语', 'v': 'thai'},
                    {'n': '俄语', 'v': 'russian'},
                ],
            },
            {
                'key': 'year',
                'name': '年份',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '今年', 'v': 'THIS_YEAR'},
                    {'n': '去年', 'v': 'LAST_YEAR'},
                    {'n': '更早', 'v': 'EARLIER'},
                    {'n': '2026', 'v': '2026'},
                    {'n': '2025', 'v': '2025'},
                    {'n': '2024', 'v': '2024'},
                    {'n': '2023', 'v': '2023'},
                    {'n': '2022', 'v': '2022'},
                    {'n': '2021', 'v': '2021'},
                    {'n': '2020', 'v': '2020'},
                ],
            },
            {
                'key': 'sort',
                'name': '排序',
                'value': [
                    {'n': '最新排序', 'v': 'newest'},
                    {'n': '默认排序', 'v': 'default'},
                    {'n': '人气排序', 'v': 'hits'},
                    {'n': '评分排序', 'v': 'score'},
                ],
            },
        ]
        return {k: item for k in self.channels}

    def getName(self):
        return '乌云影视'

    def init(self, extend=""):
        pass

    def _headers(self, json_body=False):
        h = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        if json_body:
            h['Content-Type'] = 'application/json'
        return h

    def fetch(self, url, headers=None, params=None, data=None, method=None):
        if headers is None:
            headers = self._headers(json_body=bool(data))
        try:
            if requests:
                if data is not None:
                    resp = requests.post(url, headers=headers, data=data, timeout=15)
                elif params:
                    resp = requests.get(url, headers=headers, params=params, timeout=15)
                else:
                    resp = requests.get(url, headers=headers, timeout=15)
                return resp
            full = url
            if params and data is None:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            body = data if isinstance(data, (bytes, bytearray)) else (data.encode() if data else None)
            req = urllib.request.Request(
                full,
                data=body,
                headers=headers,
                method=method or ('POST' if body else 'GET'),
            )
            raw = urllib.request.urlopen(req, timeout=15).read()

            class R:
                def __init__(self, raw):
                    self.text = raw.decode('utf-8', 'ignore')
                    self.status_code = 200

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def _proxy_url(self, path):
        return self.proxyApi + '?url=' + urllib.parse.quote(path, safe='')

    def _post_search(self, payload):
        url = self._proxy_url('/movie/media/search')
        body = json.dumps(payload, ensure_ascii=False)
        resp = self.fetch(url, headers=self._headers(True), data=body, method='POST')
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _get_video_list(self, media_id):
        path = '/movie/media/video/list?mediaId=%s&lineName=&resolutionCode=' % urllib.parse.quote(str(media_id))
        url = self._proxy_url(path)
        resp = self.fetch(url, headers=self._headers(False))
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _map_top_code(self, tid):
        info = self.channels.get(str(tid))
        if info:
            return info['topCode']
        return 'movie'

    def _parse_item(self, item, top_code=''):
        media_id = str(item.get('id') or '')
        mt = item.get('mediaType') or {}
        code = top_code or (mt.get('code') if isinstance(mt, dict) else '') or 'movie'
        pic = item.get('posterUrlS3') or item.get('posterUrl') or ''
        return {
            'vod_id': '%s|%s' % (code, media_id),
            'vod_name': item.get('title') or '',
            'vod_pic': pic,
            'vod_remarks': item.get('episodeStatus') or '',
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        result = {'class': classes}
        if filter:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        videos = []
        try:
            for tid in ('2', '1', '4', '3'):
                top = self._map_top_code(tid)
                data = self._post_search({
                    'menuCodeList': [],
                    'pageIndex': '1',
                    'pageSize': 8,
                    'searchKey': '',
                    'sortCode': 'newest',
                    'topCode': top,
                })
                records = (data.get('data') or {}).get('records') or []
                for item in records[:6]:
                    videos.append(self._parse_item(item, top))
                if len(videos) >= 24:
                    break
        except Exception as e:
            print('首页失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        pagecount = pg
        total = 0
        try:
            extend = extend or {}
            top = self._map_top_code(tid)
            menu = []
            for k in ('genre', 'region', 'language', 'year'):
                v = extend.get(k) if isinstance(extend, dict) else ''
                if v:
                    menu.append(v)
            sort_code = (extend.get('sort') if isinstance(extend, dict) else None) or 'default'
            data = self._post_search({
                'menuCodeList': menu,
                'pageIndex': str(pg),
                'pageSize': 24,
                'searchKey': '',
                'sortCode': sort_code,
                'topCode': top,
            })
            body = data.get('data') or {}
            records = body.get('records') or []
            total = int(body.get('total') or len(records) or 0)
            for item in records:
                videos.append(self._parse_item(item, top))
            pagecount = max(1, (total + 23) // 24) if total else (pg + 1 if len(videos) >= 20 else pg)
        except Exception as e:
            print('分类失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': total or len(videos),
        }

    def _get_media_detail(self, media_id):
        path = '/movie/media/detail?mediaId=%s' % urllib.parse.quote(str(media_id))
        url = self._proxy_url(path)
        resp = self.fetch(url, headers=self._headers(False))
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def detailContent(self, ids):
        result = {'list': []}
        try:
            raw = str((ids or [''])[0])
            parts = raw.split('|')
            media_id = parts[1] if len(parts) > 1 else parts[0]

            name = ''
            pic = ''
            remarks = ''
            actors = ''
            directors = ''
            content = ''
            year = ''
            area = ''

            detail = self._get_media_detail(media_id)
            info = detail.get('data') or {}
            if info:
                name = info.get('title') or info.get('originalTitle') or ''
                pic = info.get('posterUrlS3') or info.get('posterUrl') or info.get('thumbUrl') or ''
                remarks = info.get('episodeStatus') or ''
                content = info.get('overview') or info.get('description') or ''
                year = str(info.get('releaseYear') or '')[:4]
                area = info.get('region') or ''
                if isinstance(info.get('actors'), list):
                    actors = ' '.join([str(a) for a in info['actors'][:10]])
                if isinstance(info.get('directors'), list):
                    directors = ' '.join([str(d) for d in info['directors'][:5]])

            vdata = self._get_video_list(media_id)
            seasons = vdata.get('data') or []
            play_urls = []
            for s in seasons:
                for ep in (s.get('videoList') or []):
                    ep_name = ep.get('remark') or ('第%s集' % (ep.get('epNo') or 1))
                    play_url = ep.get('playUrl') or ''
                    if play_url:
                        play_urls.append('%s$%s' % (ep_name, play_url))
                    else:
                        token = 'wooyun://play?mediaId=%s&videoId=%s' % (
                            urllib.parse.quote(str(media_id)),
                            urllib.parse.quote(str(ep.get('id') or '')),
                        )
                        play_urls.append('%s$%s' % (ep_name, token))

            if not play_urls:
                play_urls.append(
                    '正片$wooyun://play?mediaId=%s&videoId=' % urllib.parse.quote(str(media_id))
                )

            if not name:
                name = '作品 %s' % media_id
            if not remarks and len(play_urls) > 1:
                remarks = '共%d集' % len(play_urls)

            result['list'] = [{
                'vod_id': raw,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_year': year,
                'vod_area': area,
                'vod_actor': actors,
                'vod_director': directors,
                'vod_content': content,
                'vod_play_from': '乌云',
                'vod_play_url': '#'.join(play_urls),
            }]
        except Exception as e:
            print('详情失败: %s' % e)
            result['list'] = []
        return result

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        total = 0
        try:
            data = self._post_search({
                'menuCodeList': [],
                'pageIndex': str(pg),
                'pageSize': 20,
                'searchKey': key or '',
                'sortCode': 'default',
                'topCode': '',
            })
            body = data.get('data') or {}
            records = body.get('records') or []
            total = int(body.get('total') or len(records) or 0)
            for item in records:
                videos.append(self._parse_item(item))
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': max(1, (total + 19) // 20) if total else pg,
            'limit': 20,
            'total': total or len(videos),
        }

    def _resolve_play_url(self, play_url):
        """处理 gen_overseas 前缀与跳转"""
        if not play_url:
            return ''
        u = play_url.strip()
        # https://wooyun.tv/gen_overseas/https://xxx.m3u8
        m = re.match(r'https?://[^/]+/gen_overseas/(https?://.+)', u, re.I)
        if m:
            return m.group(1)
        if re.search(r'\.(m3u8|mp4)(\?|$)', u, re.I):
            return u
        # 跟随一次跳转
        try:
            if requests:
                r = requests.get(u, headers=self._headers(), timeout=12, allow_redirects=True)
                final = r.url or u
                if re.search(r'\.(m3u8|mp4)(\?|$)', final, re.I):
                    return final
                # 响应体里再找
                mm = re.search(r'https?://[^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*', r.text or '', re.I)
                if mm:
                    return mm.group(0)
            else:
                req = urllib.request.Request(u, headers=self._headers())
                resp = urllib.request.urlopen(req, timeout=12)
                final = resp.geturl() or u
                if re.search(r'\.(m3u8|mp4)(\?|$)', final, re.I):
                    return final
        except Exception as e:
            print('resolve play error:', e)
        return u

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
        }
        play = str(id or '').strip()
        try:
            # 自定义协议
            if play.startswith('wooyun://play?'):
                qs = play.split('?', 1)[-1]
                media_id = ''
                video_id = ''
                for pair in qs.split('&'):
                    if '=' not in pair:
                        continue
                    k, v = pair.split('=', 1)
                    v = urllib.parse.unquote(v)
                    if k == 'mediaId':
                        media_id = v
                    elif k == 'videoId':
                        video_id = v
                raw_url = ''
                if media_id:
                    vdata = self._get_video_list(media_id)
                    for s in (vdata.get('data') or []):
                        for ep in (s.get('videoList') or []):
                            if not video_id or str(ep.get('id')) == str(video_id):
                                raw_url = ep.get('playUrl') or ''
                                if raw_url:
                                    break
                        if raw_url:
                            break
                final = self._resolve_play_url(raw_url) if raw_url else ''
                if final:
                    return {'parse': 0, 'url': final, 'header': header}
                return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

            # 已是 gen_overseas 或直链
            if play.startswith('http'):
                final = self._resolve_play_url(play)
                if self.isVideoFormat(final):
                    return {'parse': 0, 'url': final, 'header': header}
                return {'parse': 1, 'jx': '1', 'url': final or play, 'header': header}

            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}
        except Exception as e:
            print('播放失败: %s' % e)
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv|webm)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2)[:500])
    r = spider.categoryContent('1', 1, False, {})
    print('movie list', len(r.get('list') or []), (r.get('list') or [{}])[0].get('vod_name'))
    r2 = spider.searchContentPage('流浪地球', False, 1)
    print('search', [x.get('vod_name') for x in (r2.get('list') or [])[:3]])
    if r.get('list'):
        d = spider.detailContent([r['list'][0]['vod_id']])
        print('detail play', (d.get('list') or [{}])[0].get('vod_play_url', '')[:120])

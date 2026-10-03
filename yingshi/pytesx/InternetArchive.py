#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internet Archive 蜘蛛
修复：.ia.mp4 被误过滤导致无播放地址；下载链使用官方 /download/ 与 CDN 双保险
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
    def __init__(self):
        self.siteUrl = 'https://archive.org'
        self.searchApi = 'https://archive.org/advancedsearch.php'
        self.metaApi = 'https://archive.org/metadata/'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        self.channels = {
            'feature_films': {'name': '故事片', 'media': 'movies'},
            'moviesandfilms': {'name': '电影合集', 'media': 'movies'},
            'Film_Noir': {'name': '黑色电影', 'media': 'movies'},
            'SciFi_Horror': {'name': '科幻恐怖', 'media': 'movies'},
            'silent_films': {'name': '默片', 'media': 'movies'},
            'animationandcartoons': {'name': '动画', 'media': 'movies'},
            'classic_tv': {'name': '经典电视', 'media': 'movies'},
            'prelinger': {'name': 'Prelinger', 'media': 'movies'},
            'opensource_movies': {'name': '开源电影', 'media': 'movies'},
            'movie_trailers': {'name': '预告片', 'media': 'movies'},
            'TVNews': {'name': '电视新闻', 'media': 'movies'},
            'etree': {'name': '现场音乐', 'media': 'audio'},
            'audio_music': {'name': '音乐音频', 'media': 'audio'},
        }

    def getName(self):
        return 'Internet Archive'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'application/json, text/plain, */*',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=25)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                q = params if isinstance(params, str) else urllib.parse.urlencode(params, doseq=True)
                full += ('&' if '?' in url else '?') + q
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=25).read()

            class R:
                def __init__(self, raw):
                    self.content = raw
                    self.text = raw.decode('utf-8', 'ignore')

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_json(self, url, params=None):
        resp = self.fetch(url, params=params)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _as_text(self, v):
        if v is None:
            return ''
        if isinstance(v, list):
            return ', '.join(str(x) for x in v if x)
        return str(v)

    def _thumb(self, ident):
        return '%s/services/img/%s' % (self.siteUrl, urllib.parse.quote(ident, safe=''))

    def _map_doc(self, doc):
        ident = str(doc.get('identifier') or '')
        if not ident:
            return None
        return {
            'vod_id': ident,
            'vod_name': self._as_text(doc.get('title')) or ident,
            'vod_pic': self._thumb(ident),
            'vod_remarks': self._as_text(doc.get('year')) or self._as_text(doc.get('mediatype')),
        }

    def _ia_search(self, q, pg=1, rows=20):
        pg = int(pg or 1)
        params = [
            ('q', q),
            ('output', 'json'),
            ('rows', str(rows)),
            ('page', str(pg)),
            ('sort[]', 'downloads desc'),
        ]
        for f in ('identifier', 'title', 'year', 'creator', 'mediatype', 'downloads'):
            params.append(('fl[]', f))
        js = self.fetch_json(self.searchApi, params=params)
        resp = js.get('response') or {}
        return resp.get('docs') or [], int(resp.get('numFound') or 0)

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            docs, _ = self._ia_search('collection:(feature_films) AND mediatype:movies', 1, 20)
            for doc in docs:
                v = self._map_doc(doc)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        col = str(tid or 'feature_films')
        media = self.channels.get(col, {}).get('media', 'movies')
        videos = []
        total = 0
        try:
            q = 'collection:(%s) AND mediatype:%s' % (col, media)
            docs, total = self._ia_search(q, pg, 20)
            for doc in docs:
                v = self._map_doc(doc)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        pagecount = (total + 19) // 20 if total else (pg + 1 if videos else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': min(pagecount, 500),
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
            q = '(%s) AND (mediatype:movies OR mediatype:audio)' % key
            docs, total = self._ia_search(q, pg, 20)
            for doc in docs:
                v = self._map_doc(doc)
                if v:
                    videos.append(v)
        except Exception as e:
            print('搜索失败: %s' % e)
        pagecount = (total + 19) // 20 if total else pg
        return {
            'list': videos,
            'page': pg,
            'pagecount': min(pagecount, 500),
            'limit': 20,
            'total': total or len(videos),
        }

    def _rank_file(self, f):
        """
        给可播放文件打分。注意：IA 的 h.264 衍生文件名常带 .ia.mp4，不可过滤。
        """
        name = str(f.get('name') or '')
        low = name.lower()
        fmt = str(f.get('format') or '').lower()
        source = str(f.get('source') or '').lower()

        # 明确排除
        if low.endswith(('_files.xml', '.xml', '.sqlite', '.gz', '.zip', '.torrent', '.txt', '.vtt', '.srt')):
            return -1
        if low.endswith(('.gif', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.svg')):
            return -1
        if low.endswith(('.epub', '.pdf', '.djvu', '.cbz')):
            return -1
        # 原始超大 archive 包
        if fmt in ('archive bittorrent', 'metadata', 'json', 'unknown') and not low.endswith(('.mp4', '.mp3', '.m3u8', '.webm', '.ogv', '.ogg')):
            return -1

        score = -1
        height = 0
        try:
            height = int(f.get('height') or 0)
        except Exception:
            height = 0

        # HLS
        if low.endswith('.m3u8') or 'hls' in fmt:
            score = 100
        # 官方衍生 h.264 / MPEG4（含 .ia.mp4）
        elif fmt in ('h.264', 'mpeg4', '512kb mpeg4', 'h.264 ia'):
            score = 95
        elif low.endswith('.mp4'):
            score = 90
        elif low.endswith('.webm') or 'webm' in fmt:
            score = 70
        elif low.endswith('.ogv') or 'ogg video' in fmt:
            score = 55
        elif low.endswith('.mp3') or 'mp3' in fmt:
            score = 45
        elif low.endswith('.ogg') or 'vorbis' in fmt:
            score = 35
        elif low.endswith(('.mkv', '.avi', '.mov', '.mpg', '.mpeg', '.wmv', '.flv')):
            # 原始片源，能播但体积大，分数略低
            score = 50
        else:
            return -1

        # 分辨率加分
        if height >= 1080:
            score += 8
        elif height >= 720:
            score += 5
        elif height >= 480:
            score += 2

        # 衍生转码优先于 original 原盘
        if source == 'derivative':
            score += 3
        elif source == 'original' and score >= 50:
            score -= 5

        return score

    def _build_download_url(self, ident, fname, d1=None, directory=None):
        """构造可播放直链：优先官方 /download/，备选 CDN"""
        # 按路径分段编码，保留斜杠
        parts = [urllib.parse.quote(p, safe='') for p in str(fname).split('/')]
        enc_name = '/'.join(parts)
        enc_id = urllib.parse.quote(ident, safe='')
        primary = '%s/download/%s/%s' % (self.siteUrl, enc_id, enc_name)
        if d1 and directory:
            # d1 如 dn801201.us.archive.org，dir 如 /0/items/xxx
            cdn = 'https://%s%s/%s' % (d1, directory.rstrip('/'), enc_name)
            return primary, cdn
        return primary, None

    def detailContent(self, ids):
        ident = str((ids or [''])[0]).strip('/')
        try:
            js = self.fetch_json(self.metaApi + urllib.parse.quote(ident, safe=''))
            meta = js.get('metadata') or {}
            files = js.get('files') or []
            d1 = js.get('d1') or ''
            directory = js.get('dir') or ''

            cands = []
            for f in files:
                sc = self._rank_file(f)
                if sc > 0:
                    cands.append((sc, f))
            cands.sort(key=lambda x: (x[0], int(x[1].get('height') or 0)), reverse=True)

            urls = []
            seen = set()
            for sc, f in cands:
                name = f.get('name')
                if not name or name in seen:
                    continue
                seen.add(name)

                fmt = f.get('format') or name
                height = f.get('height')
                if height:
                    label = '%s %sp' % (fmt, height)
                else:
                    label = str(fmt)
                # 去掉过长文件名噪音
                if len(label) > 40:
                    label = label[:37] + '...'

                # play id: ident||filename  （双竖线避免与文件名中的 | 冲突）
                play_id = '%s||%s' % (ident, urllib.parse.quote(name, safe=''))
                urls.append('%s$%s' % (label, play_id))
                if len(urls) >= 15:
                    break

            if not urls:
                # 仍无文件时给详情页兜底
                urls.append('详情页$%s' % ident)

            return {
                'list': [{
                    'vod_id': ident,
                    'vod_name': self._as_text(meta.get('title')) or ident,
                    'vod_pic': self._thumb(ident),
                    'vod_year': self._as_text(meta.get('year') or meta.get('date')),
                    'vod_actor': self._as_text(meta.get('creator')),
                    'vod_director': self._as_text(meta.get('producer')),
                    'vod_content': self._as_text(meta.get('description'))[:600],
                    'vod_remarks': self._as_text(meta.get('mediatype')),
                    'vod_play_from': 'Internet Archive',
                    'vod_play_url': '#'.join(urls),
                }]
            }
        except Exception as e:
            print('获取详情失败: %s' % e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': '*/*',
            'Connection': 'keep-alive',
        }
        play_id = str(id or '').strip()

        # 已是直链
        if play_id.startswith('http'):
            return {
                'parse': 0 if self.isVideoFormat(play_id) else 1,
                'jx': 0,
                'url': play_id,
                'header': header,
            }

        # 新格式 ident||filename ；兼容旧格式 ident|filename
        if '||' in play_id:
            ident, enc_name = play_id.split('||', 1)
        elif '|' in play_id:
            ident, enc_name = play_id.split('|', 1)
        else:
            ident, enc_name = play_id, ''

        fname = urllib.parse.unquote(enc_name) if enc_name else ''

        try:
            # 有文件名：直接拼下载地址
            if fname:
                url, _ = self._build_download_url(ident, fname)
                return {'parse': 0, 'jx': 0, 'url': url, 'header': header}

            # 无文件名：重新选最优文件
            js = self.fetch_json(self.metaApi + urllib.parse.quote(ident, safe=''))
            d1 = js.get('d1') or ''
            directory = js.get('dir') or ''
            best, best_sc = None, -1
            for f in js.get('files') or []:
                sc = self._rank_file(f)
                if sc > best_sc:
                    best_sc, best = sc, f
            if best and best.get('name'):
                url, cdn = self._build_download_url(ident, best['name'], d1, directory)
                return {'parse': 0, 'jx': 0, 'url': url, 'header': header}
        except Exception as e:
            print('获取播放内容失败: %s' % e)

        # 最后兜底：详情页（需嗅探）
        return {
            'parse': 1,
            'jx': 0,
            'url': '%s/details/%s' % (self.siteUrl, urllib.parse.quote(ident, safe='')),
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        for fmt in ('.m3u8', '.mp4', '.mp3', '.ogv', '.webm', '.ogg', '.mkv', '.avi'):
            if fmt in u:
                return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    # 简易自测
    home = spider.homeVideoContent()
    print('home videos', len(home.get('list') or []))
    if home.get('list'):
        vid = home['list'][0]['vod_id']
        detail = spider.detailContent([vid])
        lst = detail.get('list') or []
        if lst:
            print('play_from', lst[0].get('vod_play_from'))
            print('play_url sample', (lst[0].get('vod_play_url') or '')[:200])
            first = (lst[0].get('vod_play_url') or '').split('#')[0]
            if '$' in first:
                pid = first.split('$', 1)[1]
                play = spider.playerContent('', pid, None)
                print('play result', play.get('parse'), play.get('url', '')[:120])

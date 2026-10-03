#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJ耶耶耶网 www.djyyy.com
舞曲试听 / 视频列表
列表: /{分类}/x_{页}.html
详情: /play/{id}.html → script /t/TOKEN → playurl (m4a)
搜索: /search.php?ac=dj|dy&key=
"""
import re
import sys
import json
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
        self.siteUrl = 'https://www.djyyy.com'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # type_id → (名称, 列表路径模板 {pg})
        self.channels = {
            'chuanshao': {'name': '串烧舞曲', 'path': '/chuanshao/x_{pg}.html', 'kind': 'dj'},
            'manyao': {'name': '慢摇串烧', 'path': '/manyao/x_{pg}.html', 'kind': 'dj'},
            'jinbao': {'name': '劲爆串烧', 'path': '/jinbao/x_{pg}.html', 'kind': 'dj'},
            'mange': {'name': '慢歌连版', 'path': '/mange/x_{pg}.html', 'kind': 'dj'},
            'zhongwen': {'name': '中文舞曲', 'path': '/zhongwen/x_{pg}.html', 'kind': 'dj'},
            'waiyu': {'name': '外文舞曲', 'path': '/waiyu/x_{pg}.html', 'kind': 'dj'},
            'jiaoyi': {'name': '交谊舞曲', 'path': '/jiaoyi/x_{pg}.html', 'kind': 'dj'},
            'hanmai': {'name': '喊麦舞曲', 'path': '/hanmai/x_{pg}.html', 'kind': 'dj'},
            'zuixin': {'name': '最新发布', 'path': '/wuqu/zuixin/', 'kind': 'dj'},
            'chezai': {'name': '车载视频', 'path': '/shipin/chezai/x_{pg}.html', 'kind': 'sp'},
            'yedian': {'name': '夜店视频', 'path': '/sp/yedian/x_{pg}.html', 'kind': 'sp'},
            'rewu': {'name': '热舞视频', 'path': '/sp/rewu/x_{pg}.html', 'kind': 'sp'},
            'wuqusp': {'name': '舞曲视频', 'path': '/sp/wuqu/x_{pg}.html', 'kind': 'sp'},
            'dadie': {'name': '打碟视频', 'path': '/sp/dadie/x_{pg}.html', 'kind': 'sp'},
        }
        self.filters = {}

    def getName(self):
        return 'DJ耶耶耶'

    def init(self, extend=""):
        pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        try:
            if requests:
                if params:
                    response = requests.get(url, headers=headers, params=params, timeout=12)
                else:
                    response = requests.get(url, headers=headers, timeout=12)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return response
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=12).read()

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

    def homeContent(self, filter):
        classes = [
            {'type_id': k, 'type_name': v['name']}
            for k, v in self.channels.items()
        ]
        result = {'class': classes}
        if filter:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        videos = []
        try:
            # 首页最新 + 中文
            for path in ('/wuqu/zuixin/', '/zhongwen/x_1.html', '/manyao/x_1.html'):
                resp = self.fetch(self.siteUrl + path)
                if not resp:
                    continue
                videos.extend(self._parseList(resp.text, limit=10))
                if len(videos) >= 24:
                    break
        except Exception as e:
            print('获取首页失败: %s' % e)
        # 去重
        seen, out = set(), []
        for v in videos:
            if v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            out.append(v)
        return {'list': out[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        pagecount = pg
        try:
            ch = self.channels.get(str(tid), {})
            path = ch.get('path') or '/zhongwen/x_{pg}.html'
            if '{pg}' in path:
                url = self.siteUrl + path.format(pg=pg)
            else:
                url = self.siteUrl + path
                if pg > 1 and path.endswith('/'):
                    # 最新发布可能无分页，仍请求原页
                    pass
            resp = self.fetch(url)
            if resp:
                videos = self._parseList(resp.text)
                pages = re.findall(r'/%s/x_(\d+)\.html' % re.escape(str(tid)), resp.text)
                if not pages:
                    pages = re.findall(r'x_(\d+)\.html', resp.text)
                if pages:
                    pagecount = max(int(p) for p in pages)
                else:
                    pagecount = pg + 1 if videos else pg
        except Exception as e:
            print('获取分类失败: %s' % e)
            pagecount = pg

        return {
            'list': videos,
            'page': pg,
            'pagecount': min(pagecount, 500),
            'limit': 25,
            'total': len(videos) * pagecount,
        }

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            # dj 或 视频
            if vid.startswith('sp_'):
                return self._detailVideo(vid[3:])
            return self._detailDj(vid)
        except Exception as e:
            print('获取详情失败: %s' % e)
            return {'list': []}

    def _detailDj(self, vid):
        url = self.siteUrl + '/play/%s.html' % vid
        resp = self.fetch(url)
        if not resp:
            return {'list': []}
        html = resp.text
        name = ''
        m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        if m:
            name = re.sub(r'\s*dj舞曲.*', '', m.group(1), flags=re.I)
            name = re.sub(r'\s*[,，].*', '', name).strip()
        if not name:
            m = re.search(r'<font[^>]*>([^<]+)</font>', html)
            name = m.group(1).strip() if m else vid

        # 分类 / 编号
        remarks = ''
        m = re.search(r'舞曲编号[:：\s]*<span>(\d+)</span>', html)
        if m:
            remarks = '编号%s' % m.group(1)
        m = re.search(r'收录于分类[（(]([^)）]+)[)）]', html)
        cate = m.group(1).strip() if m else ''

        play_url = self._extractPlayUrl(html, url)
        if not play_url:
            # 仍给出页面供解析
            play_url = url
            parse_hint = url
        else:
            parse_hint = play_url

        vod = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
            'vod_remarks': remarks or cate or 'DJ',
            'vod_content': cate,
            'vod_play_from': 'DJ耶耶耶',
            'vod_play_url': '试听$%s' % parse_hint,
        }
        return {'list': [vod]}

    def _detailVideo(self, vid):
        url = self.siteUrl + '/shipin/%s.html' % vid
        resp = self.fetch(url)
        if not resp:
            return {'list': []}
        html = resp.text
        name = ''
        m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        if m:
            name = re.sub(r'\s*[-–].*www\.djyyy.*', '', m.group(1), flags=re.I).strip()
        play_url = self._extractPlayUrl(html, url)
        vod = {
            'vod_id': 'sp_' + vid,
            'vod_name': name or vid,
            'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
            'vod_remarks': '视频',
            'vod_content': '',
            'vod_play_from': 'DJ耶耶耶',
            'vod_play_url': '播放$%s' % (play_url or url),
        }
        return {'list': [vod]}

    def _extractPlayUrl(self, html, page_url):
        """从详情页取 playurl：舞曲 /t/TOKEN，视频 /tt/TOKEN/"""
        # 1) 页面内直接写死的地址
        m = re.search(r"playurl\s*=\s*['\"](https?://[^'\"]+)['\"]", html)
        if m:
            return m.group(1)

        # 2) 舞曲 /t/TOKEN 或 视频 /tt/TOKEN/
        for m in re.finditer(r'src=["\'](/t{1,2}/[A-Za-z0-9]+/?)["\']', html):
            token_url = self.siteUrl + m.group(1)
            resp = self.fetch(
                token_url,
                headers={
                    'User-Agent': self.userAgent,
                    'Referer': page_url,
                    'Accept': '*/*',
                },
            )
            if not resp:
                continue
            m2 = re.search(
                r"playurl\s*=\s*['\"](https?://[^'\"]+)['\"]",
                resp.text,
            )
            if m2:
                return m2.group(1)
            m2 = re.search(
                r'(https?://[^\s\'"]+\.(?:m4a|mp3|mp4|m3u8)[^\s\'"]*)',
                resp.text,
                re.I,
            )
            if m2:
                return m2.group(1)

        # 3) 其它直链
        for pat in (
            r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)',
            r'(https?://[^"\'\s]+\.m4a[^"\'\s]*)',
            r'(https?://[^"\'\s]+\.mp3[^"\'\s]*)',
            r'(https?://[^"\'\s]+\.mp4[^"\'\s]*)',
        ):
            ms = re.findall(pat, html, re.I)
            if ms:
                return ms[0]
        return ''

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            # 舞曲
            resp = self.fetch(
                self.siteUrl + '/search.php',
                params={'ac': 'dj', 'key': key},
            )
            if resp:
                videos.extend(self._parseSearch(resp.text, kind='dj'))
            # 视频
            resp2 = self.fetch(
                self.siteUrl + '/search.php',
                params={'ac': 'dy', 'key': key},
            )
            if resp2:
                videos.extend(self._parseSearch(resp2.text, kind='sp'))
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if videos else pg,
            'limit': 50,
            'total': len(videos),
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '').strip()
        try:
            # 已是媒体直链
            if self.isVideoFormat(play):
                return {
                    'parse': 0,
                    'jx': '0',
                    'url': play,
                    'header': header,
                }

            # 详情页 → 再解 playurl
            if play.startswith('http') and 'djyyy.com' in play:
                resp = self.fetch(play)
                if resp:
                    real = self._extractPlayUrl(resp.text, play)
                    if real and self.isVideoFormat(real):
                        return {
                            'parse': 0,
                            'jx': '0',
                            'url': real,
                            'header': header,
                        }
                return {
                    'parse': 1,
                    'jx': '1',
                    'url': play,
                    'header': header,
                }

            # 纯 id
            if play.isdigit():
                real = ''
                page = self.siteUrl + '/play/%s.html' % play
                resp = self.fetch(page)
                if resp:
                    real = self._extractPlayUrl(resp.text, page)
                if real:
                    return {
                        'parse': 0,
                        'jx': '0',
                        'url': real,
                        'header': header,
                    }
                return {
                    'parse': 1,
                    'jx': '1',
                    'url': page,
                    'header': header,
                }

            return {
                'parse': 1,
                'jx': '1',
                'url': play if play.startswith('http') else self.siteUrl + '/',
                'header': header,
            }
        except Exception as e:
            print('获取播放失败: %s' % e)
            return {'parse': 1, 'url': play, 'header': header}

    def isVideoFormat(self, url):
        if not url or not str(url).startswith('http'):
            return False
        u = url.lower()
        for fmt in ('.mp3', '.m4a', '.mp4', '.m3u8', '.flv', '.aac', '.wav'):
            if fmt in u:
                return True
        if 'haiqu.vip' in u or 'ct.' in u:
            return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def _parseList(self, html, limit=0):
        videos = []
        seen = set()
        # 舞曲 /play/id.html + font 标题
        for m in re.finditer(
            r'href="(/play/(\d+)\.html)"[^>]*>[\s\S]*?<font[^>]*>([^<]+)</font>',
            html,
        ):
            vid, title = m.group(2), m.group(3).strip()
            if not title or vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                'vod_remarks': 'DJ',
            })
            if limit and len(videos) >= limit:
                return videos

        # 搜索页可能无 font
        if not videos:
            for m in re.finditer(
                r'href="(/play/(\d+)\.html)"[^>]*>\s*<span>\s*<font[^>]*>([^<]+)</font>',
                html,
            ):
                vid, title = m.group(2), m.group(3).strip()
                if vid in seen or not title:
                    continue
                seen.add(vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                    'vod_remarks': 'DJ',
                })

        # 视频 /shipin/id.html
        for m in re.finditer(
            r'href="(/shipin/(\d+)\.html)"[^>]*>\s*<img[^>]+alt="([^"]+)"',
            html,
        ):
            vid, title = m.group(2), m.group(3).strip()
            key = 'sp_' + vid
            if key in seen or not title:
                continue
            seen.add(key)
            pic = ''
            # 尝试同块 img src
            videos.append({
                'vod_id': key,
                'vod_name': title,
                'vod_pic': pic or self.siteUrl + '/static/assets/images/logo.png',
                'vod_remarks': '视频',
            })
            if limit and len(videos) >= limit:
                break

        # 视频无 alt 时
        if not any(v['vod_id'].startswith('sp_') for v in videos):
            for m in re.finditer(r'href="(/shipin/(\d+)\.html)"', html):
                vid = m.group(2)
                key = 'sp_' + vid
                if key in seen:
                    continue
                seen.add(key)
                videos.append({
                    'vod_id': key,
                    'vod_name': '视频' + vid,
                    'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                    'vod_remarks': '视频',
                })
        return videos

    def _parseSearch(self, html, kind='dj'):
        videos = []
        seen = set()
        if kind == 'dj':
            for m in re.finditer(
                r'href="(/play/(\d+)\.html)"[^>]*>[\s\S]{0,120}?<font[^>]*>([^<]+)</font>',
                html,
            ):
                vid, title = m.group(2), m.group(3).strip()
                if not title or vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                    'vod_remarks': 'DJ',
                })
            # 备选 span 结构
            if not videos:
                for m in re.finditer(
                    r'href="(/play/(\d+)\.html)"[^>]*>([\s\S]*?)</a>',
                    html,
                ):
                    vid = m.group(2)
                    title = re.sub(r'<[^>]+>', '', m.group(3)).strip()
                    title = re.sub(r'\s+', ' ', title)
                    if not title or len(title) < 2 or vid in seen:
                        continue
                    seen.add(vid)
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title[:80],
                        'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                        'vod_remarks': 'DJ',
                    })
        else:
            for m in re.finditer(
                r'href="(/shipin/(\d+)\.html)"[^>]*>\s*<img[^>]+alt="([^"]+)"',
                html,
            ):
                vid, title = m.group(2), m.group(3).strip()
                key = 'sp_' + vid
                if key in seen:
                    continue
                seen.add(key)
                videos.append({
                    'vod_id': key,
                    'vod_name': title,
                    'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                    'vod_remarks': '视频',
                })
            if not videos:
                for m in re.finditer(r'href="(/shipin/(\d+)\.html)"', html):
                    vid = m.group(2)
                    key = 'sp_' + vid
                    if key in seen:
                        continue
                    seen.add(key)
                    videos.append({
                        'vod_id': key,
                        'vod_name': '视频' + vid,
                        'vod_pic': self.siteUrl + '/static/assets/images/logo.png',
                        'vod_remarks': '视频',
                    })
        return videos


if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2)[:500])
    hv = spider.homeVideoContent()
    print('home', len(hv.get('list') or []))
    if hv.get('list'):
        print(' sample', hv['list'][0])
    cat = spider.categoryContent('zhongwen', 1, {}, {})
    print('cat', len(cat.get('list') or []), 'pagecount', cat.get('pagecount'))
    if cat.get('list'):
        d = spider.detailContent([cat['list'][0]['vod_id']])
        vod = (d.get('list') or [{}])[0]
        print('detail', vod.get('vod_name'), vod.get('vod_play_url', '')[:80])
        token = (vod.get('vod_play_url') or '').split('$')[-1]
        p = spider.playerContent('DJ耶耶耶', token, [])
        print('play', p.get('parse'), str(p.get('url') or '')[:100])
    s = spider.searchContent('dj', False, 1)
    print('search dj', len(s.get('list') or []))
    if s.get('list'):
        print(' ', s['list'][0].get('vod_name'))

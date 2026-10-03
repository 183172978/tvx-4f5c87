#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新片场 Spider  (xinpianchang.com)
列表：/_next/data/{buildId}/discover/article-{cate}-0.json
详情：/_next/data/{buildId}/a{id}.json
播放：mod-api.xinpianchang.com/mod/api/v2/media/{vid}?appKey=
支持多分辨率（1080p/720p/360p 等）
风格对齐爱奇艺.py
"""
import json
import re
import sys
import time
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
    APP_KEY = '61a2f329348b3bf77'
    MOD_API = 'https://mod-api.xinpianchang.com/mod/api/v2/media'

    def __init__(self):
        self.siteUrl = 'https://www.xinpianchang.com'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        )
        self.mobileUA = (
            'Mozilla/5.0 (Linux; Android 13; Mobile) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Mobile Safari/537.36'
        )
        self._build_id = ''
        self._build_ts = 0
        # cate1Id from /recommend/editor navigation
        self.channels = {
            '9999': {'name': '全球精选', 'cate': '9999'},
            '1': {'name': '广告片', 'cate': '1'},
            '16': {'name': '宣传片', 'cate': '16'},
            '332': {'name': '竖屏广告', 'cate': '332'},
            '329': {'name': 'AIGC', 'cate': '329'},
            '61': {'name': '摄影', 'cate': '61'},
            '142': {'name': '剪辑二创', 'cate': '142'},
            '31': {'name': '剧情短片', 'cate': '31'},
            '49': {'name': '纪录片', 'cate': '49'},
            '347': {'name': '三维CG', 'cate': '347'},
            '69': {'name': '二维动画', 'cate': '69'},
            '27': {'name': '音乐声音', 'cate': '27'},
            '76': {'name': '视觉探索', 'cate': '76'},
            '144': {'name': '学习分享', 'cate': '144'},
            '315': {'name': '校园作品', 'cate': '315'},
            '29': {'name': '短视频', 'cate': '29'},
            'editor': {'name': '编辑精选', 'cate': 'editor'},
        }

    def getName(self):
        return '新片场'

    def init(self, extend=""):
        try:
            self._ensure_build_id()
        except Exception as e:
            print('init buildId:', e)

    def _headers(self, mobile=False):
        return {
            'User-Agent': self.mobileUA if mobile else self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def fetch(self, url, headers=None):
        headers = headers or self._headers()
        try:
            if requests is not None:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code >= 400:
                    print('请求失败:', url, r.status_code)
                    return None
                return r
            req = urllib.request.Request(url, headers=headers)
            raw = urllib.request.urlopen(req, timeout=15).read()

            class R:
                def __init__(self, raw, url):
                    self.url = url
                    self.text = raw.decode('utf-8', 'ignore') if isinstance(raw, (bytes, bytearray)) else str(raw)
                    self.status_code = 200

                def json(self):
                    return json.loads(self.text)

            return R(raw, url)
        except Exception as e:
            print('请求失败:', url, e)
            return None

    def _ensure_build_id(self, force=False):
        if not force and self._build_id and (time.time() - self._build_ts) < 3600:
            return self._build_id
        resp = self.fetch(self.siteUrl + '/recommend/editor')
        if not resp:
            return self._build_id
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
        if m:
            try:
                data = json.loads(m.group(1))
                self._build_id = data.get('buildId') or self._build_id
                self._build_ts = time.time()
            except Exception as e:
                print('parse buildId:', e)
        return self._build_id

    def _next_json(self, path):
        """path like /discover/article-1-0.json or /a123.json"""
        bid = self._ensure_build_id()
        if not bid:
            return {}
        if not path.startswith('/'):
            path = '/' + path
        url = '%s/_next/data/%s%s' % (self.siteUrl, bid, path)
        if '?' in path:
            # already has query
            pass
        resp = self.fetch(url)
        if not resp:
            # refresh buildId once
            self._ensure_build_id(force=True)
            bid = self._build_id
            url = '%s/_next/data/%s%s' % (self.siteUrl, bid, path)
            resp = self.fetch(url)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _fmt_duration(self, sec):
        try:
            sec = int(sec or 0)
        except Exception:
            return ''
        if sec <= 0:
            return ''
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h:
            return '%d:%02d:%02d' % (h, m, s)
        return '%d:%02d' % (m, s)

    def _cover(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            url = 'https:' + url
        # 新片场封面常无后缀，可原样使用
        return url

    def _parse_item(self, item):
        if not item or not isinstance(item, dict):
            return None
        vid = str(item.get('id') or '')
        if not vid:
            return None
        title = item.get('title') or ''
        cover = self._cover(item.get('cover') or '')
        remarks = self._fmt_duration(item.get('duration'))
        badge = ''
        try:
            badge = (item.get('display_badge') or {}).get('badge_name') or ''
        except Exception:
            pass
        if badge and remarks:
            remarks = '%s · %s' % (badge, remarks)
        elif badge:
            remarks = badge
        author = ''
        try:
            author = ((item.get('author') or {}).get('userinfo') or {}).get('username') or ''
        except Exception:
            pass
        if author and not remarks:
            remarks = author
        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': cover,
            'vod_remarks': remarks,
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        result = {'class': classes}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos = []
        try:
            data = self._next_json('/recommend/editor.json')
            pp = data.get('pageProps') or {}
            sections = ((pp.get('editorRecommendData') or {}).get('section')) or []
            for sec in sections:
                for item in (sec.get('articles') or []):
                    v = self._parse_item(item)
                    if v:
                        videos.append(v)
                    if len(videos) >= 24:
                        break
                if len(videos) >= 24:
                    break
        except Exception as e:
            print('首页失败:', e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        total = 0
        try:
            info = self.channels.get(str(tid), {})
            cate = info.get('cate') or str(tid)
            if cate == 'editor':
                data = self._next_json('/recommend/editor.json')
                pp = data.get('pageProps') or {}
                sections = ((pp.get('editorRecommendData') or {}).get('section')) or []
                for sec in sections:
                    for item in (sec.get('articles') or []):
                        v = self._parse_item(item)
                        if v:
                            videos.append(v)
                total = len(videos)
            else:
                # 首页列表；分页接口常被 WAF 拦截，pg>1 仍尝试 next 参数
                path = '/discover/article-%s-0.json' % cate
                if pg > 1:
                    path += '?page=%d' % pg
                data = self._next_json(path)
                pp = data.get('pageProps') or {}
                dad = pp.get('discoverArticleData') or {}
                for item in (dad.get('list') or []):
                    v = self._parse_item(item)
                    if v:
                        videos.append(v)
                total = int(dad.get('total') or len(videos) or 0)
        except Exception as e:
            print('分类失败:', e)
        pagecount = max(1, (total + 59) // 60) if total else (pg + 1 if len(videos) >= 40 else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 60,
            'total': total or len(videos),
        }

    def _search_api(self, key, pg=1):
        params = {
            'keyword': key or '',
            'page': str(pg),
            'per_page': '60',
            'type': 'article',
            'result_profile': 'discover_card',
        }
        url = self.siteUrl + '/v2/search?' + urllib.parse.urlencode(params)
        resp = self.fetch(url)
        if not resp:
            return [], 0
        text = getattr(resp, 'text', '') or ''
        if not text.strip().startswith('{'):
            return [], 0
        try:
            data = resp.json()
        except Exception:
            return [], 0
        body = data.get('data') or data
        records = body.get('list') or body.get('articles') or []
        if not records and isinstance(body, list):
            records = body
        total = body.get('total') if isinstance(body, dict) else len(records)
        if isinstance(total, dict):
            total = total.get('article') or total.get('total') or len(records)
        videos = []
        for item in records:
            v = self._parse_item(item)
            if v:
                videos.append(v)
        return videos, int(total or len(videos) or 0)

    def _hydrate_ids(self, ids):
        videos = []
        seen = set()
        for aid in ids:
            aid = str(aid)
            if not aid or aid in seen:
                continue
            seen.add(aid)
            try:
                data = self._next_json('/a%s.json' % aid)
                detail = (data.get('pageProps') or {}).get('detail') or {}
                if not detail or not detail.get('title'):
                    continue
                item = {
                    'id': aid,
                    'title': detail.get('title'),
                    'cover': detail.get('cover'),
                    'duration': detail.get('duration'),
                }
                v = self._parse_item(item)
                if v:
                    videos.append(v)
            except Exception as e:
                print('hydrate', aid, e)
        return videos

    def _search_haosou(self, key, pg=1):
        """外站搜索兜底：多页抓取文章 id，再回源详情"""
        try:
            q = urllib.parse.quote('%s site:www.xinpianchang.com' % key)
            pn = int(pg or 1)
            ids = []
            # 一次多取几页，提高数量
            pages = [pn, pn + 1, pn + 2] if pn == 1 else [pn]
            candidates_tpl = [
                ('https://m.so.com/s?q=%s&pn=%d', True),
                ('https://www.so.com/s?q=%s&pn=%d', False),
                ('https://m.baidu.com/s?word=%s&pn=%d', True),
            ]
            for page in pages:
                for tpl, mobile in candidates_tpl:
                    if 'baidu' in tpl:
                        # 百度 pn 从 0 起，每页约 10
                        url = tpl % (q, max(0, (page - 1) * 10))
                    else:
                        url = tpl % (q, page)
                    resp = self.fetch(url, headers=self._headers(mobile=mobile))
                    if not resp:
                        continue
                    html = resp.text or ''
                    if '访问异常' in html or 'qcaptcha' in html.lower():
                        continue
                    found = re.findall(r'xinpianchang\.com/a(\d+)', html)
                    found += re.findall(r'xinpianchang\.com%2Fa(\d+)', html)
                    found += re.findall(r'xinpianchang\.com%252Fa(\d+)', html)
                    for i in found:
                        if i not in ids:
                            ids.append(i)
                if len(ids) >= 30:
                    break
            if not ids:
                return [], 0
            # 多取一些再回源
            videos = self._hydrate_ids(ids[:40])
            # 软过滤：标题含关键词优先，其余相关也保留
            kl = key.lower()
            primary = [v for v in videos if kl in (v.get('vod_name') or '').lower()]
            if len(primary) >= 5:
                videos = primary
            # 若 primary 太少，保留全部回源结果
            return videos, len(videos)
        except Exception as e:
            print('external search:', e)
            return [], 0

            videos = self._hydrate_ids(ids[:20])
            kl = key.lower()
            filtered = [v for v in videos if kl in (v.get('vod_name') or '').lower()]
            if filtered:
                videos = filtered
            return videos, len(videos)
        except Exception as e:
            print('external search:', e)
            return [], 0

            html = resp.text or ''
            ids = re.findall(r'xinpianchang\.com/a(\d+)', html)
            ids += re.findall(r'xinpianchang\.com%2Fa(\d+)', html)
            ids = list(dict.fromkeys(ids))
            if not ids:
                return [], 0
            videos = self._hydrate_ids(ids)
            kl = key.lower()
            filtered = [v for v in videos if kl in (v.get('vod_name') or '').lower()]
            if filtered:
                videos = filtered
            return videos, len(videos)
        except Exception as e:
            print('haosou search:', e)
            return [], 0

    def _search_fallback_cate(self, key, pg=1):
        key_l = (key or '').strip().lower()
        if not key_l:
            return [], 0
        cate_ids = ['1', '31', '49', '329', '27', '29', '16', '9999', 'editor']
        matched = []
        seen = set()
        for cid in cate_ids:
            try:
                if cid == 'editor':
                    data = self._next_json('/recommend/editor.json')
                    sections = (((data.get('pageProps') or {}).get('editorRecommendData') or {}).get('section')) or []
                    items = []
                    for sec in sections:
                        items.extend(sec.get('articles') or [])
                else:
                    data = self._next_json('/discover/article-%s-0.json' % cid)
                    items = (((data.get('pageProps') or {}).get('discoverArticleData') or {}).get('list')) or []
                for item in items:
                    title = (item.get('title') or '').lower()
                    content = (item.get('content') or '').lower()
                    author = ''
                    try:
                        author = (((item.get('author') or {}).get('userinfo') or {}).get('username') or '').lower()
                    except Exception:
                        pass
                    if key_l in title or key_l in content or key_l in author:
                        vid = str(item.get('id') or '')
                        if not vid or vid in seen:
                            continue
                        seen.add(vid)
                        v = self._parse_item(item)
                        if v:
                            matched.append(v)
            except Exception as e:
                print('search fallback cate', cid, e)
        page_size = 24
        start = (int(pg or 1) - 1) * page_size
        return matched[start:start + page_size], len(matched)

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        key = (key or '').strip()
        if not key:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 40, 'total': 0}
        videos = []
        seen = set()
        total = 0
        kl = key.lower()
        try:
            # 1) 官方搜索
            api_list, api_total = self._search_api(key, pg)
            related = [v for v in api_list if kl in (v.get('vod_name') or '').lower()]
            # 官方结果若多数相关则采用，否则仍合并进列表
            use_api = related if related else ([] if api_list else [])
            if not related and api_list:
                # 可能官方未按关键词过滤，标题不含则丢弃热门脏数据
                use_api = []
            for v in use_api:
                vid = str(v.get('vod_id') or '')
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append(v)
            total = max(total, api_total if related else 0)

            # 2) 外站全库（补量）
            if len(videos) < 20:
                ext_list, ext_total = self._search_haosou(key, pg)
                for v in ext_list:
                    vid = str(v.get('vod_id') or '')
                    if vid and vid not in seen:
                        seen.add(vid)
                        videos.append(v)
                total = max(total, len(videos), ext_total)

            # 3) 分类过滤再补
            if len(videos) < 12:
                fb_list, fb_total = self._search_fallback_cate(key, pg)
                for v in fb_list:
                    vid = str(v.get('vod_id') or '')
                    if vid and vid not in seen:
                        seen.add(vid)
                        videos.append(v)
                total = max(total, len(videos), fb_total)
            if not total:
                total = len(videos)
        except Exception as e:
            print('搜索失败:', e)
            try:
                videos, total = self._search_haosou(key, pg)
            except Exception as e2:
                print('搜索兜底失败:', e2)
        return {
            'list': videos,
            'page': pg,
            'pagecount': max(1, (total + 39) // 40) if total else pg,
            'limit': 40,
            'total': total or len(videos),
        }

    def _media_progressive(self, vid, app_key=None):
        app_key = app_key or self.APP_KEY
        url = '%s/%s?appKey=%s' % (self.MOD_API, urllib.parse.quote(str(vid)), app_key)
        resp = self.fetch(url)
        if not resp:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        if data.get('status') not in (0, '0', None) and data.get('message') not in ('OK', None):
            # status 0 = OK
            if data.get('status') != 0:
                print('media api:', data.get('message'))
        progressive = ((data.get('data') or {}).get('resource') or {}).get('progressive') or []
        return progressive if isinstance(progressive, list) else []

    def detailContent(self, ids):
        result = {'list': []}
        try:
            aid = re.sub(r'\D', '', str((ids or [''])[0])) or str((ids or [''])[0])
            data = self._next_json('/a%s.json' % aid)
            detail = (data.get('pageProps') or {}).get('detail') or {}
            if not detail:
                return result
            name = detail.get('title') or ('作品 %s' % aid)
            pic = self._cover(detail.get('cover') or '')
            desc = detail.get('content') or detail.get('description') or ''
            duration = self._fmt_duration(detail.get('duration'))
            cats = detail.get('categories') or []
            if isinstance(cats, list):
                area = ' / '.join([c if isinstance(c, str) else str(c.get('name') or '') for c in cats[:6]])
            else:
                area = ''
            author = ''
            try:
                author = ((detail.get('author') or {}).get('userinfo') or {}).get('username') or ''
            except Exception:
                pass

            video_meta = detail.get('video') or {}
            media_id = video_meta.get('vid') or detail.get('media_id') or detail.get('video_library_id') or ''
            app_key = video_meta.get('appKey') or self.APP_KEY

            play_parts = []
            if media_id:
                progressive = self._media_progressive(media_id, app_key)
                # 按分辨率从高到低
                def sort_key(p):
                    return int(p.get('height') or p.get('codedHeight') or 0)

                progressive = sorted(progressive, key=sort_key, reverse=True)
                for p in progressive:
                    u = (p.get('url') or p.get('backupUrl') or '').strip()
                    if not u:
                        continue
                    label = p.get('profile') or p.get('quality') or ('%sp' % (p.get('height') or ''))
                    play_parts.append('%s$%s' % (label, u))
                # 若全无 url（如 1080 需登录），仍列出可用的
            if not play_parts:
                # 回退网页
                play_parts.append('网页$%s/a%s' % (self.siteUrl, aid))

            # 多分辨率作为同一线路多个清晰度
            result['list'] = [{
                'vod_id': aid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': duration,
                'vod_year': '',
                'vod_area': area,
                'vod_actor': author,
                'vod_director': '',
                'vod_content': (desc or '').replace('\n\n', '\n').strip()[:500],
                'vod_play_from': '新片场',
                'vod_play_url': '#'.join(play_parts),
            }]
        except Exception as e:
            print('详情失败:', e)
            result['list'] = []
        return result

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(mp4|m3u8)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}
        if play.startswith('http'):
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}
        # 可能是 article id，重新取最高清
        aid = re.sub(r'\D', '', play) or play
        try:
            data = self._next_json('/a%s.json' % aid)
            detail = (data.get('pageProps') or {}).get('detail') or {}
            video_meta = detail.get('video') or {}
            media_id = video_meta.get('vid') or detail.get('media_id') or ''
            app_key = video_meta.get('appKey') or self.APP_KEY
            progressive = self._media_progressive(media_id, app_key) if media_id else []
            progressive = sorted(
                progressive,
                key=lambda p: int(p.get('height') or 0),
                reverse=True,
            )
            for p in progressive:
                u = (p.get('url') or '').strip()
                if u:
                    return {'parse': 0, 'url': u, 'header': header}
        except Exception as e:
            print('播放失败:', e)
        return {
            'parse': 1,
            'jx': '1',
            'url': '%s/a%s' % (self.siteUrl, aid),
            'header': header,
        }

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(mp4|m3u8|webm)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print(json.dumps(spider.homeContent(False), ensure_ascii=False)[:200])
    hv = spider.homeVideoContent()
    print('homeVod', len(hv.get('list') or []))
    r = spider.categoryContent('1', 1, False, {})
    print('cate', len(r.get('list') or []), (r.get('list') or [{}])[0].get('vod_name'))
    if r.get('list'):
        d = spider.detailContent([r['list'][0]['vod_id']])
        vod = (d.get('list') or [{}])[0]
        print('detail', vod.get('vod_name'))
        print('play', vod.get('vod_play_url', '')[:180])
    s = spider.searchContentPage('剧情', False, 1)
    print('search', len(s.get('list') or []))

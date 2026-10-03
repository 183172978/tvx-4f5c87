#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光厂 VJshi Spider v1.1
修复：WAF acw_sc__v2 导致分类无数据
"""
import json
import re
import sys
import time
import gzip
import subprocess
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

NODE_PRELUDE = r"""
global.location = { host: 'www.vjshi.com', hostname: 'www.vjshi.com', reload: function(){} };
global.window = global;
global.document = { location: global.location };
Object.defineProperty(global.document, 'cookie', {
  set: function(v){ console.log(v); },
  get: function(){ return ''; }
});
const _Function = Function;
global.Function = function(...args){
  const s = String(args[args.length-1]||'');
  if (s.includes('return this')) return function(){ return global; };
  return _Function.apply(this, args);
};
"""


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://www.vjshi.com'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        )
        self._cookie = ''
        self._cookie_ts = 0
        self.channels = {
            'shipinsucai': {'name': '视频素材', 'path': '/so/shipinsucai.html'},
            'aemuban': {'name': 'AE模板', 'path': '/so/aemuban.html'},
            'prmuban': {'name': 'PR模板', 'path': '/so/prmuban.html'},
            'fcpmuban': {'name': 'FCP模板', 'path': '/so/fcpmuban.html'},
            '3d': {'name': '3D模型', 'path': '/so/3dmaxmoxing.html'},
            'c4d': {'name': 'C4D模型', 'path': '/so/c4dmoxing.html'},
            'nature': {'name': '自然风景', 'query': '自然'},
            'city': {'name': '城市建筑', 'query': '城市'},
            'people': {'name': '人物生活', 'query': '人物'},
            'tech': {'name': '科技数据', 'query': '科技'},
            'business': {'name': '商务企业', 'query': '商务'},
            'medical': {'name': '医疗健康', 'query': '医疗'},
            'food': {'name': '美食餐饮', 'query': '美食'},
            'sport': {'name': '运动健身', 'query': '运动'},
            '4k': {'name': '4K素材', 'query': '4K'},
        }

    def getName(self):
        return '光厂视频'

    def init(self, extend=""):
        try:
            self._ensure_cookie()
        except Exception as e:
            print('init cookie:', e)

    def _headers(self, with_cookie=True):
        h = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        if with_cookie and self._cookie:
            h['Cookie'] = 'acw_sc__v2=' + self._cookie
        return h

    def _decode_body(self, raw):
        if not raw:
            return ''
        if raw[:2] == b'\x1f\x8b':
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw.decode('utf-8', 'ignore')

    def _raw_get(self, url, with_cookie=True):
        try:
            req = urllib.request.Request(url, headers=self._headers(with_cookie))
            resp = urllib.request.urlopen(req, timeout=18)
            return self._decode_body(resp.read())
        except Exception as e:
            print('raw_get error:', url, e)
            return ''

    def _solve_cookie_node(self, challenge_html):
        m = re.search(r'<script>([\s\S]+?)</script>', challenge_html)
        if not m:
            return ''
        path = '/tmp/vjshi_chal_%d.js' % int(time.time() * 1000)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(NODE_PRELUDE + '\n' + m.group(1))
        try:
            out = subprocess.check_output(['node', path], stderr=subprocess.STDOUT, timeout=12)
            out = out.decode('utf-8', 'ignore')
            cm = re.search(r'acw_sc__v2=([0-9a-fA-F]+)', out)
            return cm.group(1) if cm else ''
        except Exception as e:
            print('node solve error:', e)
            return ''

    def _ensure_cookie(self, force=False):
        if not force and self._cookie and (time.time() - self._cookie_ts) < 3000:
            return self._cookie
        html = self._raw_get(self.siteUrl + '/', with_cookie=False)
        if 'var arg1=' not in html:
            self._cookie_ts = time.time()
            return self._cookie
        val = self._solve_cookie_node(html)
        if val:
            self._cookie = val
            self._cookie_ts = time.time()
            print('acw_sc__v2 ok')
        return self._cookie

    def fetch_text(self, url):
        self._ensure_cookie()
        html = self._raw_get(url, with_cookie=True)
        if 'var arg1=' in html and len(html) < 20000:
            self._ensure_cookie(force=True)
            html = self._raw_get(url, with_cookie=True)
        return html or ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _parse_list(self, html):
        videos = []
        if not html or ('var arg1=' in html and len(html) < 20000):
            return videos
        seen = set()
        re_card = re.compile(
            r'href="(/watch/(\d+)\.html)[^"]*"[\s\S]{0,1500}?'
            r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"',
            re.I
        )
        for m in re_card.finditer(html):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = (m.group(4) or '').strip() or ('素材 #%s' % vid)
            videos.append({
                'vod_id': vid,
                'vod_name': title[:100],
                'vod_pic': self._abs(m.group(3)),
                'vod_remarks': '',
            })
        if len(videos) < 6:
            for m in re.finditer(r'href="(/watch/(\d+)\.html)[^"]*"', html):
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': '素材 #%s' % vid,
                    'vod_pic': '',
                    'vod_remarks': '',
                })
        return videos

    def _list_url(self, tid, pg):
        pg = int(pg or 1)
        info = self.channels.get(str(tid), {})
        path = info.get('path')
        q = info.get('query')
        if path:
            if pg <= 1:
                return self.siteUrl + path
            return self.siteUrl + path + '?page=' + str(pg)
        if q:
            params = {'wd': q}
            if pg > 1:
                params['page'] = pg
            return self.siteUrl + '/so?' + urllib.parse.urlencode(params)
        return self.siteUrl + '/'

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        result = {'class': classes}
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos = []
        try:
            html = self.fetch_text(self.siteUrl + '/')
            videos = self._parse_list(html)
        except Exception as e:
            print('首页失败:', e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            url = self._list_url(tid, pg)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
        except Exception as e:
            print('分类失败:', e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            params = {'wd': key or ''}
            if pg > 1:
                params['page'] = pg
            url = self.siteUrl + '/so?' + urllib.parse.urlencode(params)
            html = self.fetch_text(url)
            videos = self._parse_list(html)
        except Exception as e:
            print('搜索失败:', e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 24,
            'total': 9999 if videos else 0,
        }

    def detailContent(self, ids):
        vid = re.sub(r'\D', '', str((ids or [''])[0])) or str((ids or [''])[0])
        try:
            url = '%s/watch/%s.html' % (self.siteUrl, vid)
            html = self.fetch_text(url)
            name = '素材 #%s' % vid
            pic = ''
            desc = ''
            m = re.search(r'<title>([^<]+)</title>', html or '', re.I)
            if m:
                name = re.sub(r'\s*[-|_].*$', '', m.group(1)).strip() or name
            m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html or '', re.I)
            if m:
                name = m.group(1).strip()
            m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html or '', re.I)
            if m:
                pic = self._abs(m.group(1))
            m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html or '', re.I)
            if m:
                desc = m.group(1).strip()[:400]

            play_parts = []
            seen = set()
            for m in re.finditer(r'https?://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html or '', re.I):
                u = m.group(0).replace('\\/', '/')
                if u in seen:
                    continue
                seen.add(u)
                label = '预览'
                if 'lmp4' in u:
                    label = '低清预览'
                elif 'mp4.vjshi' in u:
                    label = '高清预览'
                play_parts.append('%s$%s' % (label, u))
            if not play_parts:
                play_parts.append('网页$%s' % url)

            return {'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': '',
                'vod_content': desc or '光厂（VJshi）正版素材，完整下载需授权，此处为在线预览。',
                'vod_play_from': '光厂',
                'vod_play_url': '#'.join(play_parts[:6]),
            }]}
        except Exception as e:
            print('详情失败:', e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and re.search(r'\.(mp4|m3u8)(\?|$)', play, re.I):
            return {'parse': 0, 'url': play, 'header': header}
        if play.startswith('http'):
            html = self.fetch_text(play)
            m = re.search(r'https?://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html or '', re.I)
            if m:
                return {'parse': 0, 'url': m.group(0).replace('\\/', '/'), 'header': header}
            return {'parse': 1, 'jx': '1', 'url': play, 'header': header}
        page = '%s/watch/%s.html' % (self.siteUrl, re.sub(r'\D', '', play) or play)
        html = self.fetch_text(page)
        m = re.search(r'https?://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html or '', re.I)
        if m:
            return {'parse': 0, 'url': m.group(0).replace('\\/', '/'), 'header': header}
        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(mp4|m3u8|webm)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print(json.dumps(spider.homeContent(False), ensure_ascii=False)[:200])
    r = spider.categoryContent('shipinsucai', 1, False, {})
    print('list', len(r.get('list') or []), (r.get('list') or [{}])[0].get('vod_name'))
    r2 = spider.searchContentPage('自然', False, 1)
    print('search', len(r2.get('list') or []))

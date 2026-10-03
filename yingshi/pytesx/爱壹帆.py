#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱壹帆（镜像 www.yfsp.lv）
分类: /t/{1电影 2剧集 3综艺 4动漫}/
详情: /iyftv/{id}/
播放: /iyfplay/{id}-{sid}-{nid}/ → player_aaaa.url (m3u8)
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
        # 主站 yifan.tv / iyf.tv 常 403/521，用可用镜像
        self.siteUrl = 'https://www.yfsp.lv'
        self.hosts = [
            'https://www.yfsp.lv',
            'https://www.iyf.lv',
        ]
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        )
        self.channels = {
            '1': {'name': '电影', 'path': '/t/1/'},
            '2': {'name': '剧集', 'path': '/t/2/'},
            '3': {'name': '综艺', 'path': '/t/3/'},
            '4': {'name': '动漫', 'path': '/t/4/'},
            'new': {'name': '最新', 'path': '/label/new/'},
            'hot': {'name': '热榜', 'path': '/label/hot/'},
        }

    def getName(self):
        return '爱壹帆'

    def init(self, extend=""):
        if not extend:
            return
        try:
            if isinstance(extend, str) and extend.strip().startswith('{'):
                ext = json.loads(extend)
                if ext.get('host'):
                    self.siteUrl = str(ext['host']).rstrip('/')
                    if self.siteUrl not in self.hosts:
                        self.hosts.insert(0, self.siteUrl)
            elif isinstance(extend, str) and extend.startswith('http'):
                self.siteUrl = extend.rstrip('/')
                if self.siteUrl not in self.hosts:
                    self.hosts.insert(0, self.siteUrl)
        except Exception:
            pass

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=15).read()

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
        # 多域名回退
        urls = [url]
        for h in self.hosts:
            if url.startswith(self.siteUrl):
                urls.append(url.replace(self.siteUrl, h, 1))
        seen = set()
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            resp = self.fetch(u, params=params)
            text = getattr(resp, 'text', '') if resp else ''
            if text and len(text) > 500:
                return text
        return ''

    def _abs(self, u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.siteUrl + u
        return u

    def _clean(self, s):
        return re.sub(r'<[^>]+>', '', str(s or '')).strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        # 标准海报卡片
        for m in re.finditer(
            r'href="(/iyftv/(\d+)/?)"\s+title="([^"]+)"[\s\S]{0,600}?'
            r'data-original="([^"]+)"[\s\S]{0,200}?module-item-note">([^<]*)',
            html or '',
        ):
            vid, name, pic, note = m.group(2), self._clean(m.group(3)), m.group(4), self._clean(m.group(5))
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': name or vid,
                'vod_pic': self._abs(pic),
                'vod_remarks': note or '',
            })
        if videos:
            return videos
        # 宽松匹配
        for m in re.finditer(
            r'href="(/iyftv/(\d+)/?)"[^>]*title="([^"]+)"',
            html or '',
        ):
            vid, name = m.group(2), self._clean(m.group(3))
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': name or vid,
                'vod_pic': '',
                'vod_remarks': '',
            })
        for m in re.finditer(
            r'/iyftv/(\d+)/[\s\S]{0,400}?data-original="([^"]+)"',
            html or '',
        ):
            for v in videos:
                if v['vod_id'] == m.group(1) and not v['vod_pic']:
                    v['vod_pic'] = self._abs(m.group(2))
                    break
        return videos

    def _list_page(self, path, pg=1):
        pg = int(pg or 1)
        paths = []
        base = path if path.startswith('/') else '/' + path
        if pg <= 1:
            paths.append(base)
            paths.append(base.rstrip('/') + '/')
        else:
            # 分页常见格式
            paths.append(base.rstrip('/') + '/page/%s/' % pg)
            paths.append(base.rstrip('/') + '-%s/' % pg)
            paths.append(base + (('&' if '?' in base else '?') + 'page=' + str(pg)))
        videos = []
        for p in paths:
            html = self.fetch_text(self.siteUrl + p)
            videos = self._parse_list(html)
            if videos:
                break
        return videos

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            videos = self._list_page('/label/hot/', 1)
            if len(videos) < 8:
                videos = self._list_page('/t/1/', 1) or self._list_page('/', 1)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        videos = []
        try:
            path = self.channels.get(str(tid), {}).get('path', '/t/1/')
            videos = self._list_page(path, pg)
            if not videos and pg == 1:
                videos = self._list_page('/label/new/', 1)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        try:
            q = urllib.parse.quote(key)
            for path in (
                '/s/%s-------------/' % q,
                '/vodsearch/-------------.html?wd=%s' % q,
                '/index.php/vod/search.html?wd=%s' % q,
            ):
                html = self.fetch_text(self.siteUrl + path)
                videos = self._parse_list(html)
                if videos:
                    break
        except Exception as e:
            print('搜索失败: %s' % e)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 12 else pg,
            'limit': 24,
            'total': len(videos),
        }

    def detailContent(self, ids):
        vid = str((ids or [''])[0])
        name, pic, desc, remarks = vid, '', '', ''
        actor, director = '', ''
        parts = []
        try:
            html = self.fetch_text(self.siteUrl + '/iyftv/%s/' % vid)
            tm = re.search(r'<title>([^<]+)</title>', html or '')
            if tm:
                name = re.sub(r'[-_|].*(详情|免费|在线|爱壹帆).*$', '', tm.group(1)).strip() or name
            hm = re.search(r'class="module-info-heading"[^>]*>[\s\S]*?<h1[^>]*>([^<]+)</h1>', html or '')
            if hm:
                name = self._clean(hm.group(1)) or name
            pm = re.search(r'og:image["\']\s+content=["\']([^"\']+)', html or '')
            if pm:
                pic = self._abs(pm.group(1))
            if not pic:
                im = re.search(r'data-original="([^"]+)"', html or '')
                if im:
                    pic = self._abs(im.group(1))
            dm = re.search(r'og:description["\']\s+content=["\']([^"\']+)', html or '')
            if dm:
                desc = dm.group(1)
            am = re.search(r'主演[:：</]+[^>]*>([^<]+)', html or '')
            if am:
                actor = self._clean(am.group(1))
            # 线路选集 /iyfplay/{id}-{sid}-{nid}/
            seen = set()
            for m in re.finditer(
                r'href="(/iyfplay/(\d+)-(\d+)-(\d+)/?)"[^>]*(?:title="([^"]*)")?[^>]*>\s*([^<]*)',
                html or '',
            ):
                href, sid, nid = m.group(1), m.group(3), m.group(4)
                label = self._clean(m.group(5) or m.group(6) or '')
                if not label or label in ('播放',):
                    label = '线路%s-%s' % (sid, nid)
                key = href
                if key in seen:
                    continue
                seen.add(key)
                # token: id|sid|nid 便于 playerContent
                token = '%s|%s|%s' % (vid, sid, nid)
                parts.append('%s$%s' % (label, token))
            if not parts:
                parts.append('播放$%s|1|1' % vid)
            remarks = '%s线路' % len(parts) if len(parts) > 1 else remarks
        except Exception as e:
            print('获取详情失败: %s' % e)
            parts = ['播放$%s|1|1' % vid]
        return {
            'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': (desc or '').replace('\n\n', '\n').strip(),
                'vod_play_from': '爱壹帆',
                'vod_play_url': '#'.join(parts),
            }]
        }

    def _player_url(self, vid, sid='1', nid='1'):
        """从 /iyfplay/ 页提取 player_aaaa.url"""
        path = '/iyfplay/%s-%s-%s/' % (vid, sid, nid)
        html = self.fetch_text(self.siteUrl + path)
        m = re.search(r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>', html or '')
        if not m:
            m = re.search(r'var\s+player_[a-z]+\s*=\s*(\{[\s\S]*?\})\s*</script>', html or '')
        if m:
            try:
                obj = json.loads(m.group(1))
                url = obj.get('url') or ''
                if url and not url.startswith('http') and obj.get('encrypt') in (1, '1', 2, '2'):
                    # 可能 base64
                    try:
                        import base64
                        url = base64.b64decode(url).decode('utf-8', 'ignore')
                    except Exception:
                        pass
                if url.startswith('http'):
                    return url
            except Exception as e:
                print('解析 player_aaaa 失败: %s' % e)
        m3 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html or '')
        if m3:
            return m3.group(0).replace('\\/', '/')
        return ''

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play = str(id or '')
        if self.isVideoFormat(play) and play.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play, 'header': header}

        vid, sid, nid = play, '1', '1'
        if '|' in play:
            parts = play.split('|')
            vid = parts[0]
            if len(parts) > 1:
                sid = parts[1]
            if len(parts) > 2:
                nid = parts[2]
        else:
            m = re.search(r'(\d+)', play)
            if m:
                vid = m.group(1)

        url = self._player_url(vid, sid, nid)
        if url:
            return {'parse': 0, 'jx': '0', 'url': url, 'header': header}

        page = self.siteUrl + '/iyfplay/%s-%s-%s/' % (vid, sid, nid)
        return {'parse': 1, 'jx': '1', 'url': page, 'header': header}

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
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    print('--- category ---')
    r = spider.categoryContent('1', 1, {}, {})
    print(json.dumps(r, ensure_ascii=False)[:600])
    if r.get('list'):
        vid = r['list'][0]['vod_id']
        d = spider.detailContent([vid])
        print('--- detail ---')
        print(json.dumps(d, ensure_ascii=False)[:500])
        token = (d.get('list') or [{}])[0].get('vod_play_url', '').split('#')[0].split('$')[-1]
        print('--- play ---')
        print(json.dumps(spider.playerContent('爱壹帆', token, []), ensure_ascii=False)[:400])

import json, re, sys, requests, hashlib, base64
from urllib.parse import quote, unquote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.host = "https://t.me"
        self.pan_api = "http://127.0.0.1:6080"
        self.cache = {}
        self.channels = []
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}
        
    def init(self, extend=""):
        if not extend: return
        
        data = self.session.get(extend).json()
        if isinstance(data, dict):
            self.pan_api = data.get('pan_api', self.pan_api)
            if proxy := data.get('proxy'):
                self.session.proxies = {'http': proxy, 'https': proxy}
            self.channels = data.get('channels', data.get('class', []))
        elif isinstance(data, list):
            self.channels = data
    
    def getName(self):
        return "TG精准推送(缓存翻页版)"
    
    def homeContent(self, _):
        return {
            'class': [{
                "type_name": ch.get('type_name', ch.get('name', '')),
                "type_id": ch.get('type_id', ch.get('id', ''))
            } for ch in self.channels if isinstance(ch, dict)],
            'filters': {}
        }
    
    def _get_link_type(self, url):
        patterns = {
            '百度': r'pan\.baidu\.com',
            '夸克': r'pan\.quark\.cn',
            '阿里': r'www\.aliyundrive\.com|www\.alipan\.com',
            '移动': r'yun\.139\.com|caiyun\.139\.com',
            '天翼': r'cloud\.189\.cn',
            '115': r'www\.115\.com|115cdn\.com',
            'UC': r'pan\.uc\.cn|drive\.uc\.cn',
            '123': r'123pan\.(?:com|cn)|123(?:684|865|912|592)\.com',
            '磁力': r'^magnet:\?xt=urn:btih:'
        }
        for name, pattern in patterns.items():
            if re.search(pattern, url, re.I):
                return name
    
    def _check_links(self, links):
        if not links: return set()
        
        magnets = [l for l in links if self._get_link_type(l) == '磁力']
        others = [l for l in links if self._get_link_type(l) != '磁力']
        
        valid = set(magnets)
        if others:
            try:
                res = self.session.post(
                    f"{self.pan_api}/api/v1/links/check",
                    json={"links": list(set(others))},
                    timeout=5
                )
                data = res.json()
                valid.update(data.get('valid_links', []))
                valid.update(data.get('pending_links', []))
            except:
                valid.update(others)
        return valid
    
    def _image_to_base64(self, url):
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                content_type = res.headers.get('Content-Type', 'image/jpeg')
                pic_data = base64.b64encode(res.content).decode('utf-8')
                return f"data:{content_type};base64,{pic_data}"
        except:
            pass
        return url
    
    def _parse_tg_html(self, html):
        vod_list = []
        blocks = html.split('tgme_widget_message_bubble')[1:]
        
        for block in blocks:
            vids = re.findall(r'<video[^>]*?src=["\']([^"\']+\.mp4[^"\']*)["\']', block, re.S)
            hrefs = re.findall(r'href=["\']?(https?://[^"\'\s>]+)', block)
            magnets = re.findall(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,40}', block, re.I)
            
            links = list(set([u for u in hrefs + magnets if self._get_link_type(u)]))
            if not vids and not links:
                continue

            text_match = re.search(r'js-message_?text[^>]*?>(.*?)</div>', block, re.S)
            if text_match:
                text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                title = lines[0] if lines else "TG资源"
            else:
                bolds = re.findall(r'<b[^>]*?>(.*?)</b>', block, re.S)
                title = "".join([re.sub(r'<[^>]+>', '', b).strip() for b in bolds])
                title = title if len(title) >= 2 else "TG资源"

            title = re.sub(r'^(名称：|资源标题：)', '', title)
            title = re.sub(r'(全\s*\d+\s*集|共\s*\d+\s*集|\d+\s*集\s*全|(?:更新至|更新到|更至|更新)\s*(?:第)?\s*\d+\s*(?:集)?|剧情|加更|更新).*$', '', title)
            title = title.strip()
            title = title[:100] + "..." if len(title) > 100 else title
            pic_match = re.search(r'background-image:url\([\'"]?(.*?)[\'"]?\)', block)
            pic = pic_match.group(1) if pic_match else "https://api.xinac.net/icon/?url=https://t.me"
            
            vod_list.append({
                'title': title,
                'pic': self._image_to_base64(pic) if pic.startswith('http') else pic,
                'vids': vids[:3],
                'links': links
            })
        
        # 批量检查链接有效性
        all_links = [l for v in vod_list for l in v['links']]
        valid_links = self._check_links(all_links)
        
        result = []
        for vod in vod_list:
            play_froms, play_urls = [], []
            
            if vod['vids']:
                play_froms.append("直连")
                play_urls.append("#".join([f"视频{i+1}${u}" for i, u in enumerate(vod['vids'])]))
            
            active_links = [l for l in vod['links'][:5] if l in valid_links]
            for link in active_links:
                if (link_type := self._get_link_type(link)) == '磁力':
                    play_urls.append(link)
                else:
                    play_urls.append(f"一键推送$push://{quote(link, safe='')}")
                play_froms.append(link_type)
            
            if not play_urls:
                continue
            
            unique_id = hashlib.md5((vod['title'] + str(vod['vids']) + str(vod['links'])).encode()).hexdigest()
            result.append({
                "vod_name": vod['title'],
                "vod_id": json.dumps({
                    "id": unique_id,
                    "n": vod['title'],
                    "p": vod['pic'],
                    "f": "$$$".join(play_froms),
                    "u": "$$$".join(play_urls)
                }),
                "vod_pic": vod['pic'],
                "vod_remarks": " | ".join(play_froms[:3])
            })
        
        return result
    
    def categoryContent(self, tid, pg, _filter, _extend):
        pg = int(pg)
        if pg == 1:
            url = f"{self.host}/s/{tid}"
        else:
            cache_key = f"{tid}_{pg}"
            if cache_key not in self.cache:
                return {'list': []}
            url = f"{self.host}/s/{tid}?before={self.cache[cache_key]}"
        
        html = self.session.get(url).text
        if match := re.search(r'before=(\d+)', html):
            self.cache[f"{tid}_{pg+1}"] = match.group(1)
        
        return {'list': self._parse_tg_html(html)[::-1], 'page': pg, 'pagecount': pg + 1}
    
    def detailContent(self, ids):
        data = json.loads(ids[0])
        pic = self._image_to_base64(data['p']) if data['p'].startswith('http') else data['p']
        
        return {'list': [{
            "vod_name": data['n'],
            "vod_pic": pic,
            "vod_play_from": data['f'],
            "vod_play_url": data['u'],
            "vod_content": data['n']
        }]}
    
    def playerContent(self, _flag, id, _vipFlags):
        if id.startswith('一键推送$push://'):
            url = unquote(id.split('一键推送$push://')[1])
        elif '$' in id:
            url = id.split('$')[-1]
        else:
            url = id
        
        header = {'User-Agent': 'Mozilla/5.0'}
        parse = 0
        
        return {
            'parse': parse,
            'url': url,
            'header': header,
            'proxy': self.session.proxies.get('http') if url.startswith('http') and ('video' in url.lower() or url.endswith('.mp4')) else None
        }
    
    def searchContent(self, key, _quick, _pg="1"):
        results = []
        for channel in self.channels:
            if chan_id := channel.get('id', channel.get('type_id')):
                url = f"{self.host}/s/{chan_id}?q={quote(key)}"
                results.extend(self._parse_tg_html(self.session.get(url).text))
                if len(results) > 20:
                    break
        return {'list': results}
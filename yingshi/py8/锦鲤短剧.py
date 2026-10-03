from base.spider import Spider
import re,sys,json
sys.path.append('..')
class Spider(Spider):
    api_host = 'https://api.jinlidj.com'
    origin = 'https://www.jinlidj.com'
    api_path = '/api/search'
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        'Content-Type': "application/json",
        'accept-language': "zh-CN,zh;q=0.9",
        'cache-control': "no-cache",
        'origin': origin,
        'pragma': "no-cache",
        'priority': "u=1, i",
        'referer': origin+'/',
        'sec-ch-ua': "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
        'sec-ch-ua-mobile': "?0",
        'sec-ch-ua-platform': "\"Windows\"",
        'sec-fetch-dest': "empty",
        'sec-fetch-mode': "cors",
        'sec-fetch-site': "same-site"
    }
    def homeContent(self, filter):
        return {'class': [{'type_id': 1, 'type_name': '情感关系'}, {'type_id': 2, 'type_name': '成长逆袭'}, {'type_id': 3, 'type_name': '奇幻异能'}, {'type_id': 4, 'type_name': '战斗热血'}, {'type_id': 5, 'type_name': '伦理现实'}, {'type_id': 6, 'type_name': '时空穿越'}, {'type_id': 7, 'type_name': '权谋身份'}]}
    
    def homeVideoContent(self):
        payload = {
            "page": 1,
            "limit": 24,
            "type_id": "",
            "year": "",
            "keyword": ""
        }
        try:
            response = self.post(f"{self.api_host}{self.api_path}", data=json.dumps(payload), headers=self.headers).json()
            data = response.get('data', {})
            videos = []
            for i in data.get('list', []):
                # 修复：int转str，避免拼接报错，加默认值防空
                vod_total = i.get('vod_total', 0)
                videos.append({
                        'vod_id': i.get('vod_id', ''),
                        'vod_name': i.get('vod_name', ''),
                        'vod_class': i.get('vod_class', ''),
                        'vod_pic': i.get('vod_pic', ''),
                        'vod_year': i.get('vod_year', ''),
                        'vod_remarks': str(vod_total)+'集',
                        'vod_score': i.get('vod_score', '')
                        })
            return {'list': videos}
        except:
            return {'list': []}
    
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        try:
            response = self.post(f'{self.api_host}/api/detail/{ids[0]}', data=json.dumps({}), headers=self.headers).json()
            data = response.get('data', {})
            videos = []
            vod_play_url = ''
            # 修复：加判空，避免player非字典报错
            player = data.get('player', {})
            if isinstance(player, dict):
                for name,url in player.items():
                    if url:
                        vod_play_url += f'{name}${url}#'
            # 修复：rstrip赋值，真正去掉末尾#
            vod_play_url = vod_play_url.rstrip('#') if vod_play_url else ''
            # 修复：int转str，加默认值
            vod_total = data.get('vod_total', 0)
            videos.append({
                'vod_id': data.get('vod_id', ''),
                'vod_name': data.get('vod_name', ''),
                'vod_content': data.get('vod_blurb', ''),
                'vod_remarks': '集数：' + str(vod_total),
                "vod_director": data.get('vod_director', ''),
                "vod_actor": data.get('vod_actor', ''),
                'vod_year': data.get('vod_year', ''),
                'vod_area': data.get('vod_area', ''),
                'vod_play_from': '锦鲤短剧',
                'vod_play_url': vod_play_url,
                # 修复：加playUrl字段，兼容羊壳强制要求，避免KeyError
                'playUrl': vod_play_url.split('#')[0].split('$')[-1] if vod_play_url else ''
            })
            return {'list': videos}
        except:
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        payload = {
            "page": pg,
            "limit": 24,
            "type_id": "",
            "keyword": key
        }
        try:
            response = self.post(f'{self.api_host}{self.api_path}', data=json.dumps(payload), headers=self.headers).json()
            data = response.get('data', {})
            videos = []
            for i in data.get('list', []):
                    # 修复：int转str，加默认值
                    vod_total = i.get('vod_total', 0)
                    videos.append({
                        "vod_id": i.get('vod_id', ''),
                        "vod_name": i.get('vod_name', ''),
                        "vod_class": i.get('vod_class', ''),
                        "vod_pic": i.get('vod_pic', ''),
                        'vod_year': i.get('vod_year', ''),
                        "vod_remarks": str(vod_total) + '集'
                    })
            return {'list': videos, 'page': pg, 'total': data.get('total', 0), 'limit': 24}
        except:
            return {'list': [], 'page': pg, 'total': 0, 'limit': 24}
    
    def categoryContent(self, tid, pg, filter, extend):
        payload = {
            "page": pg,
            "limit": 24,
            "type_id": tid,
            "year": "",
            "keyword": ""
        }
        try:
            response = self.post(f'{self.api_host}{self.api_path}', data=json.dumps(payload), headers=self.headers).json()
            data = response.get('data', {})
            videos = []
            for i in data.get('list', []):
                # 修复：int转str，加默认值防空
                vod_total = i.get('vod_total', 0)
                videos.append({
                        'vod_id': i.get('vod_id', ''),
                        'vod_name': i.get('vod_name', ''),
                        'vod_class': i.get('vod_class', ''),
                        'vod_pic': i.get('vod_pic', ''),
                        'vod_remarks': str(vod_total)+'集',
                        'vod_year': i.get('vod_year', ''),
                        'vod_score': i.get('vod_score', '')
                        })
            return {'list': videos}
        except:
            return {'list': []}
    
    def playerContent(self, flag, id, vipflags):
        parse = 0
        header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}
        try:
            response = self.fetch(id, headers=self.headers).text
            # 修复：放宽正则匹配，兼容网页源代码不同写法，加非贪婪匹配
            match = re.search(r'let\s+data\s*=\s*(\{[\s\S]*?http[\s\S]*?\});', response, re.IGNORECASE)
            if match:
                data = match.group(1)
                data2 = json.loads(data)
                url = data2.get('url', id)
            else:
                url = id
        except Exception:
            # 解析失败直接用原地址，羊壳自动二次解析
            url, parse, header = id, 1, self.headers
        return {'parse': parse, 'url': url,'header': header}
    
    def init(self, extend=''):
        pass
    def getName(self):
        pass
    def isVideoFormat(self, url):
        pass
    def manualVideoCheck(self):
        pass
    def destroy(self):
        pass
    def localProxy(self, param):
        pass

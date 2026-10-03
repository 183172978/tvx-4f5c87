#coding=utf-8
#!/usr/bin/python
import re
import sys
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import quote, unquote, urlencode

import requests

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "B站视频"

    # 固定有效Cookie
    MY_COOKIE = "DedeUserID=546666766;DedeUserID__ckMd5=8abadf385c8cbcee;Expires=1794468426;SESSDATA=e8759cbd,1794468426,bd62d*51CjAAcPu-7QmaJSz88y29Z5qpZ6K0Bx1bEJ-jsZMSWI_6SUwqv8BCnsrQ5a7ApVY-PL0SVlY0RkJuRWhCSlVISEV6QVN0ZDhxNnlqeVd5ZXZuX1JkYThENi16MDBBVzdKeGdQUkpzMUh5N2d2cFJjM0xOYmswdnBxdzNXREpRT0xJVk5LZTdzbWdBIIEC;bili_jct=b57504835a9a3a69f42947f1dbb125ae;gourl=https://www.bilibili.com;first_domain=.bilibili.com;"

    def init(self, extend):
        try:
            self.extendDict = json.loads(extend)
        except:
            self.extendDict = {}

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # 标准请求头
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    # 补全缺失清洗方法
    def cleanText(self, text):
        return text.strip().replace('\r','').replace('\n','')

    def homeContent(self, filter):
        result = {}
        result['filters'] = {}
        result['class'] = [
            {"type_name":"沙雕虾仁","type_id":"虾仁"},{"type_name":"沙雕仙逆","type_id":"沙雕仙逆"},
            {"type_name":"沙雕动画","type_id":"沙雕动画"},{"type_name":"纪录片","type_id":"纪录片超清"},
            {"type_name":"演唱会","type_id":"演唱会超清"},{"type_name":"流行音乐","type_id":"音乐超清"},
            {"type_name":"美食","type_id":"美食超清"},{"type_name":"食谱","type_id":"食谱"},
            {"type_name":"体育","type_id":"体育超清"},{"type_name":"球星","type_id":"球星"},
            {"type_name":"教育","type_id":"中小学教育"},{"type_name":"幼儿教育","type_id":"幼儿教育"},
            {"type_name":"旅游","type_id":"旅游"},{"type_name":"风景","type_id":"风景4K"},
            {"type_name":"说案","type_id":"说案"},{"type_name":"知名UP主","type_id":"知名UP主"},
            {"type_name":"探索发现","type_id":"探索发现超清"},{"type_name":"鬼畜","type_id":"鬼畜"},
            {"type_name":"搞笑","type_id":"搞笑超清"},{"type_name":"儿童","type_id":"儿童超清"},
            {"type_name":"动物世界","type_id":"动物世界超清"},{"type_name":"相声小品","type_id":"相声小品超清"},
            {"type_name":"戏曲","type_id":"戏曲"},{"type_name":"解说","type_id":"解说"},
            {"type_name":"演讲","type_id":"演讲"},{"type_name":"小姐姐","type_id":"小姐姐超清"},
            {"type_name":"荒野求生","type_id":"荒野求生超清"},{"type_name":"健身","type_id":"健身"},
            {"type_name":"帕梅拉","type_id":"帕梅拉"},{"type_name":"太极拳","type_id":"太极拳"},
            {"type_name":"广场舞","type_id":"广场舞"},{"type_name":"舞蹈","type_id":"舞蹈"},
            {"type_name":"音乐","type_id":"音乐"},{"type_name":"歌曲","type_id":"歌曲"},
            {"type_name":"MV","type_id":"MV4K"},{"type_name":"舞曲","type_id":"舞曲超清"},
            {"type_name":"4K","type_id":"4K"},{"type_name":"电影","type_id":"电影"},
            {"type_name":"电视剧","type_id":"电视剧"},{"type_name":"白噪音","type_id":"白噪音超清"},
            {"type_name":"考公考证","type_id":"考公考证"},{"type_name":"平面设计教学","type_id":"平面设计教学"},
            {"type_name":"软件教程","type_id":"软件教程"},{"type_name":"Windows","type_id":"Windows"}
        ]
        return result

    def homeVideoContent(self):
        result = {}
        cookie, imgKey, subKey = self.getCookie(self.MY_COOKIE)
        try:
            params = {"version": "v2", "ps": 20}
            params = self.encWbi(params, imgKey, subKey)
            url = "https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd"
            r = requests.get(url, params=params, cookies=cookie, headers=self.header, timeout=10)
            data = json.loads(self.cleanText(r.text))
            result['list'] = []
            vodList = data['data']['item']
            for vod in vodList:
                aid = str(vod['id']).strip()
                title = self.removeHtmlTags(vod['title']).strip()
                img = vod['pic'].strip()
                remark = time.strftime('%H:%M:%S', time.gmtime(vod['duration']))
                if remark.startswith('00:'):
                    remark = remark[3:]
                result['list'].append({
                    'vod_id': aid,
                    'vod_name': title,
                    'vod_pic': img,
                    'vod_remarks': remark
                })
        except Exception as e:
            pass
        return result

    def categoryContent(self, cid, page, filter, ext):
        page = int(page)
        result = {}
        videos = []
        pagecount = page
        cookie, imgKey, subKey = self.getCookie(self.MY_COOKIE)
        try:
            params = {
                "keyword": cid,
                "search_type": "video",
                "page": page,
                "page_size": 20
            }
            params = self.encWbi(params, imgKey, subKey)
            url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
            r = requests.get(url, params=params, cookies=cookie, headers=self.header, timeout=10)
            data = json.loads(self.cleanText(r.text))
            if data.get('data') and data['data'].get('result'):
                pagecount = data['data'].get('numPages', page)
                for vod in data['data']['result']:
                    if vod.get('type') != 'video':continue
                    vid = str(vod['aid']).strip()
                    title = self.removeHtmlTags(vod['title'])
                    img = 'https:' + vod['pic'].strip()
                    remark = vod['duration']
                    videos.append({"vod_id":vid,"vod_name":title,"vod_pic":img,"vod_remarks":remark})
        except Exception as e:pass
        result['list']=videos;result['page']=page;result['pagecount']=pagecount
        result['limit']=len(videos);result['total']=len(videos)*pagecount if pagecount>1 else len(videos)
        return result

    def detailContent(self, did):
        aid = did[0]
        if aid.startswith('UP主&&&'):
            bizId = aid[6:]
            url = f'https://api.bilibili.com/x/v2/medialist/resource/list?mobi_app=web&type=1&oid=&biz_id={bizId}&otype=1&ps=100'
            r = self.fetch(url, headers=self.header, timeout=10)
            videoList = r.json()['data']['media_list']
            vod = {"vod_id":aid,"vod_name":'播放列表','vod_play_from':'B站视频'}
            playUrl = ''
            for video in videoList:
                remark = time.strftime('%H:%M:%S', time.gmtime(video['duration']))
                name = self.removeHtmlTags(video['title']).strip().replace("#", "-")
                if remark.startswith('00:'):remark=remark[3:]
                playUrl += f"[{remark}]/{name}$bvid&&&{video['bv_id']}#"
            vod['vod_play_url']=playUrl.strip('#')
            return {'list':[vod]}
        cookie,imgKey,subKey=self.getCookie(self.MY_COOKIE)
        params=self.encWbi({"aid":aid},imgKey,subKey)
        url="https://api.bilibili.com/x/web-interface/wbi/view"
        r=requests.get(url,params=params,cookies=cookie,headers=self.header,timeout=10)
        data=json.loads(self.cleanText(r.text))
        if data.get('code')!=0:return {'list':[]}
        data=data['data']
        director=f'[a=cr:{{"id":"UP主&&&{data["owner"]["mid"]}","name":"{data["owner"]["name"]}"}}/]{data["owner"]["name"]}[/a]'
        vod={
            "vod_id":aid,"vod_name":self.removeHtmlTags(data['title']),"vod_pic":data['pic'],
            "type_name":data['tname'],"vod_year":datetime.fromtimestamp(data['pubdate']).strftime('%Y-%m-%d %H:%M:%S'),
            "vod_content":data.get('desc','无简介').replace('\xa0',' ').strip(),"vod_director":director
        }
        playUrl=''
        for video in data['pages']:
            remark=time.strftime('%H:%M:%S',time.gmtime(video['duration']))
            name=self.removeHtmlTags(video['part']).strip().replace("#","-")
            if remark.startswith('00:'):remark=remark[3:]
            playUrl+=f"[{remark}]/{name}${aid}_{video['cid']}#"
        vod['vod_play_from']='B站视频'
        vod['vod_play_url']=playUrl.strip('#')
        return {'list':[vod]}

    def searchContent(self,key,quick):
        return self.searchContentPage(key,quick,'1')

    def searchContentPage(self,key,quick,page):
        videos=[]
        if quick:return {'list':videos}
        cookie,imgKey,subKey=self.getCookie(self.MY_COOKIE)
        try:
            params={"keyword":key,"search_type":"video","page":page,"page_size":20}
            params=self.encWbi(params,imgKey,subKey)
            url="https://api.bilibili.com/x/web-interface/wbi/search/type"
            r=requests.get(url,params=params,cookies=cookie,headers=self.header,timeout=10)
            jo=json.loads(self.cleanText(r.text))
            if jo.get('data') and jo['data'].get('result'):
                for vod in jo['data']['result']:
                    aid=str(vod['aid']).strip()
                    title=self.removeHtmlTags(vod['title'])
                    img='https:'+vod['pic'].strip()
                    remark=vod['duration']
                    videos.append({"vod_id":aid,"vod_name":title,"vod_pic":img,"vod_remarks":remark})
        except:pass
        return {'list':videos}

    # 播放核心修复：改参数+兼容直连+优先普通流兜底
    def playerContent(self, flag, pid, vipFlags):
        result = {}
        if pid.startswith('bvid&&&'):
            bvid = pid[7:]
            url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            r = requests.get(url, headers=self.header, timeout=10)
            data = r.json()['data']
            aid = data['aid']
            cid = data['cid']
        else:
            idList = pid.split("_")
            aid = idList[0]
            cid = idList[1]

        # 下调清晰度参数，兼容非大会员，同时保留高清
        play_api = f'https://api.bilibili.com/x/player/playurl?aid={aid}&cid={cid}&qn=80&fnval=16&fourk=0'
        cookiesDict, _, _ = self.getCookie(self.MY_COOKIE)
        # 优先尝试直链播放，失败再走代理
        try:
            res = requests.get(play_api, cookies=cookiesDict, headers=self.header, timeout=6)
            play_data = res.json()
            if play_data.get("code") == 0 and play_data["data"].get("durl"):
                result["parse"] = 1
                result["playUrl"] = play_data["data"]["durl"][0]["url"]
                result["header"] = self.header
                result['danmaku'] = f'https://api.bilibili.com/x/v1/dm/list.so?oid={cid}'
                return result
        except:
            pass

        # 直链失败再走本地代理MPD
        cookies = quote(json.dumps(cookiesDict))
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = f'http://127.0.0.1:9978/proxy?do=py&type=mpd&cookies={cookies}&url={quote(play_api)}&aid={aid}&cid={cid}'
        result["header"] = self.header
        result['danmaku'] = f'https://api.bilibili.com/x/v1/dm/list.so?oid={cid}'
        result["format"] = 'application/dash+xml'
        return result

    def localProxy(self, params):
        if params['type'] == "mpd":
            return self.proxyMpd(params)
        if params['type'] == "media":
            return self.proxyMedia(params)
        return None

    def destroy(self):
        pass

    def proxyMpd(self, params):
        content, durlinfos, mediaType = self.getDash(params)
        if mediaType == 'mpd':
            return [200, "application/dash+xml", content]
        else:
            url = content
            header = self.header.copy()
            if 'range' in params:header['Range']=params['range']
            r=requests.get(url,headers=header,stream=True,timeout=10)
            return [206,"application/octet-stream",r.content]

    def proxyMedia(self, params, forceRefresh=False):
        _, dashinfos, _ = self.getDash(params)
        try:
            if 'videoid' in params:
                dashinfo = dashinfos['video'][int(params['videoid'])]
            elif 'audioid' in params:
                dashinfo = dashinfos['audio'][int(params['audioid'])]
            else:
                return [404, "text/plain", ""]
            url = dashinfo['baseUrl']
            header = self.header.copy()
            if 'range' in params:header['Range']=params['range']
            r=requests.get(url,headers=header,stream=True,timeout=10)
            return [206,"application/octet-stream",r.content]
        except:
            return [404,"text/plain",""]

    def getDash(self, params, forceRefresh=False):
        aid=params['aid'];cid=params['cid'];url=unquote(params['url'])
        key=f'bilivdmpdcache_{aid}_{cid}'
        if not forceRefresh:
            data=self.getCache(key)
            if data:return data['content'],data['dashinfos'],data['type']
        cookieDict=json.loads(params['cookies'])
        r=self.fetch(url,cookies=cookieDict,headers=self.header,timeout=8)
        data=json.loads(self.cleanText(r.text))
        if data.get('code')!=0 or not data.get('data'):return '',{},''
        data=data['data']
        if 'dash' not in data:
            purl=data['durl'][0]['url']
            self.setCache(key,{'content':purl,'type':'mp4','dashinfos':data,'expiresAt':int(time.time())+1800})
            return purl,data,'mp4'
        dashinfos=data['dash'];duration=dashinfos['duration']
        videoinfo='';audioinfo=''
        for idx,video in enumerate(dashinfos['video']):
            baseUrl=f'http://127.0.0.1:9978/proxy?do=py&type=media&cookies={params["cookies"]}&aid={aid}&cid={cid}&videoid={idx}'
            videoinfo += f'''      <Representation bandwidth="{video['bandwidth']}" codecs="{video['codecs']}" height="{video['height']}" width="{video['width']}">
        <BaseURL>{baseUrl}</BaseURL>
        <SegmentBase indexRange="{video['SegmentBase']['indexRange']}">
        <Initialization range="{video['SegmentBase']['Initialization']}"/>
        </SegmentBase>
      </Representation>
'''
        for idx,audio in enumerate(dashinfos['audio']):
            baseUrl=f'http://127.0.0.1:9978/proxy?do=py&type=media&cookies={params["cookies"]}&aid={aid}&cid={cid}&audioid={idx}'
            audioinfo += f'''      <Representation bandwidth="{audio['bandwidth']}" codecs="{audio['codecs']}">
        <BaseURL>{baseUrl}</BaseURL>
        <SegmentBase indexRange="{audio['SegmentBase']['indexRange']}">
        <Initialization range="{audio['SegmentBase']['Initialization']}"/>
        </SegmentBase>
      </Representation>
'''
        mpd=f'''<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static" mediaPresentationDuration="PT{duration}S">
  <Period>
    <AdaptationSet mimeType="video/mp4" segmentAlignment="true">{videoinfo.strip()}</AdaptationSet>
    <AdaptationSet mimeType="audio/mp4" segmentAlignment="true">{audioinfo.strip()}</AdaptationSet>
  </Period>
</MPD>'''
        self.setCache(key,{'type':'mpd','content':mpd.replace('&','&amp;'),'dashinfos':dashinfos,'expiresAt':int(time.time())+1800})
        return mpd.replace('&','&amp;'),dashinfos,'mpd'

    def getCookie(self, cookie_str):
        cookies = {}
        try:
            for item in cookie_str.split(';'):
                item=item.strip()
                if not item or '=' not in item:continue
                k,v=item.split('=',1)
                cookies[k]=v
        except:pass
        cache=self.getCache('bblogin')
        if cache:return cookies,cache['imgKey'],cache['subKey']
        try:
            r=requests.get("https://api.bilibili.com/x/web-interface/nav",cookies=cookies,headers=self.header,timeout=10)
            data=r.json()
            if data.get('code')==0 and data.get('data',{}).get('wbi_img'):
                img_url=data['data']['wbi_img']['img_url']
                sub_url=data['data']['wbi_img']['sub_url']
                imgKey=img_url.split('/')[-1].split('.')[0]
                subKey=sub_url.split('/')[-1].split('.')[0]
                self.setCache('bblogin',{'imgKey':imgKey,'subKey':subKey,'expiresAt':int(time.time())+3600})
                return cookies,imgKey,subKey
        except:pass
        return cookies,"7777","7777"

    def getUserid(self,cookie):
        try:
            url='https://api.bilibili.com/x/space/myinfo'
            r=self.fetch(url,cookies=cookie,headers=self.header,timeout=8)
            return r.json()['data']['mid']
        except:return None

    def removeHtmlTags(self,src):
        return re.sub(r'<.*?>','',src)

    def encWbi(self,params,img_key,sub_key):
        mixinKeyEncTab=[46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
        def get_mixin_key(orig):
            n=[orig[i] for i in mixinKeyEncTab]
            return ''.join(n)[:32]
        s=img_key+sub_key
        mixin_key=get_mixin_key(s)
        params.update({'wts':int(time.time())})
        params=dict(sorted(params.items()))
        query=urlencode(params)
        w_rid=hashlib.md5((query+mixin_key).encode()).hexdigest()
        params['w_rid']=w_rid
        return params
import re,urllib.request,urllib.parse,html as htmllib,json,sys
try:
    from base.spider import Spider
except Exception:
    class Spider: pass

class Spider(Spider):
    def getName(self): return '粉嫩女友'
    def init(self,extend=''): pass
    def isVideoFormat(self,url): return url.endswith(('.m3u8','.mp4','.flv','.avi','.mkv'))
    def manualVideoCheck(self): return False
    def destroy(self): pass
    def __init__(self):
        self.host='https://xn--0523tt29-fr4s583p.fnnvtv0b.xyz'
        self.headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36','Accept-Language':'zh-CN,zh;q=0.9','Referer':self.host+'/'}
        self.cms_type='unknown'
        self.classes=[
            ('精品导航','精品导航'),
            ('顶级推荐','顶级推荐'),
            ('更多 >','更多 >'),
        ]

    def fetch(self,url,headers=None,timeout=20):
        req=urllib.request.Request(url,headers=headers or self.headers)
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.read().decode('utf-8','ignore')
    def clean(self,s): return re.sub(r'\s+',' ',htmllib.unescape(re.sub(r'<.*?>','',s or ''))).strip()
    def abs(self,u): return u if u.startswith('http') else self.host+u
    def field(self,html,label):
        m=re.search(r'<span>\s*'+re.escape(label)+r':\s*</span>\s*(?:<time[^>]*datetime="([^"]*)"[^>]*>.*?</time>|<span[^>]*>(.*?)</span>|<a[^>]*>(.*?)</a>)',html,re.S)
        return self.clean((m.group(1) or m.group(2) or m.group(3)) if m else '')
    def pic_proxy(self,u):
        u=htmllib.unescape(u or '').replace('&#x2F;','/').replace('&#x3D;','=')
        q=urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get('url',[''])[0] if 'api/proxy' in u and 'url=' in u else u
        if q.startswith('//'): q='https:'+q
        return 'https://ig2.pppppppp.top/api/proxy?url='+q if q.startswith('http') else u

    def homeContent(self,filter):
        return {'class':[{'type_name':n,'type_id':i} for n,i in self.classes]}

    def categoryContent(self,tid,pg,filter,extend):
        result={}
        try:
            url=self.host+'/'+tid+(('?page='+str(pg)) if str(pg)!='1' else '')
            html=self.fetch(url)
            result['list']=self.parse_list(html)
            result['page']=int(pg)
            result['pagecount']=999
            result['limit']=len(result.get('list',[]))
            result['total']=999*24
        except Exception as e:
            result['list']=[]
        return result

    def parse_list(self,html):
        arr=[];seen=set()
        # 容器选择器: div#app > div.page:nth-of-type(1)...
        # 优先正则提取，兜底选择器
        for m in re.finditer(r'<a\s+href="([^"]+)"[^>]*>.*?<img[^>]+(?:data-src|src)="([^"]*)"[^>]*>.*?</a>',html,re.S|re.I):
            vid=m.group(1);pic=m.group(2)
            if vid in seen or not vid or vid.startswith('http'): continue
            seen.add(vid)
            title='';tm=re.search(r'<a[^>]*href="'+re.escape(vid)+r'"[^>]*>(.*?)</a>',html[m.start():m.start()+800],re.S)
            if tm: title=self.clean(tm.group(1))
            if len(title)<2: continue
            pic=self.pic_proxy(pic)
            dur='';dm=re.search(r'<span[^>]*>(\s*\d{1,2}:\d{2}(?::\d{2})?\s*)</span>',html[m.start():m.start()+600],re.S)
            if dm: dur=dm.group(1).strip()
            arr.append({'vod_id':vid,'vod_name':title,'vod_pic':pic,'vod_remarks':dur})
        return arr

    def detailContent(self,ids):
        result={}
        try:
            vid=ids[0] if isinstance(ids,list) else ids
            url=vid if vid.startswith('http') else self.host+vid
            html=self.fetch(url)
            title=self.clean((re.search(r'<meta property="og:title" content="([^"]*)"',html) or re.search(r'<title>(.*?)</title>',html,re.S) or ['',''])[1])
            pic='';pm=re.search(r'<meta property="og:image" content="([^"]*)"',html)
            pic=htmllib.unescape(pm.group(1)).replace('&#x2F;','/').replace('&#x3D;','=') if pm else ''
            desc=self.clean((re.search(r'<meta property="og:description"\s*content="([^"]*)"',html,re.S) or ['',''])[1])
            year=self.field(html,'发行日期') or self.field(html,'年份') or self.field(html,'上映时间')
            code=self.field(html,'番号') or self.field(html,'编号')
            actresses=self.field(html,'女优') or self.field(html,'演员') or self.field(html,'主演')
            series=self.field(html,'系列') or self.field(html,'剧集')
            maker=self.field(html,'发行商') or self.field(html,'制作') or self.field(html,'厂商')
            director=self.field(html,'导演')
            tags=','.join([self.clean(x) for x in re.findall(r'href="/[^"]*(?:genres|labels|tags)/[^"]+"[^>]*>(.*?)</a>',html,re.S) if self.clean(x)][:12])
            sources=self.unpack_sources(html)
            play=[]
            if sources:
                for k,u in sources: play.append(k+'$'+u)
            else:
                play.append('播放$'+self.host+'/'+vid)
            content='\n'.join([x for x in [desc,('番号：'+code) if code else '',('演员：'+actresses) if actresses else '',('系列：'+series) if series else '',('发行商：'+maker) if maker else '',('导演：'+director) if director else ''] if x])
            vod={'vod_id':vid,'vod_name':title or vid.upper(),'vod_pic':pic,'type_name':tags,'vod_year':year,'vod_area':maker,'vod_director':director,'vod_actor':actresses,'vod_content':content,'vod_play_from':'$$$'.join([x.split('$')[0] for x in play]),'vod_play_url':'$$$'.join(play)}
            result['list']=[vod]
        except Exception as e:
            result['list']=[]
        return result

    def unpack_sources(self,html):
        out=[]
        p=re.search(r"eval\(function\(p,a,c,k,e,d\).*?\('(.*?)',\s*(\d+),\s*(\d+),\s*'([^']*)'\.split\('\|'\)",html,re.S)
        if not p: return out
        s,base,count,keys=p.group(1).replace("\\'","'"),int(p.group(2)),int(p.group(3)),p.group(4).split('|')
        def b36(n):
            chars='0123456789abcdefghijklmnopqrstuvwxyz';n=int(n);r=''
            if n==0: return '0'
            while n: r=chars[n%36]+r;n//=36
            return r
        for c in range(count-1,-1,-1):
            k=keys[c] if c<len(keys) else ''
            if k: s=re.sub(r'\b'+b36(c)+r'\b',k,s)
        for name,url in re.findall(r"(source(?:842|1280)?)='(https?://[^']+?\.m3u8)'",s):
            label={'source':'原画','source842':'842x480','source1280':'1280x720'}.get(name,name)
            out.append((label,'https://pl3.vvvvvvvv.top/api/play?url='+url))
        return out

    def searchContent(self,key,quick,pg='1'):
        try:
            url=self.host+'/search/'+urllib.parse.quote(key)
            html=self.fetch(url)
            return {'list':self.parse_list(html)}
        except:
            return {'list':[]}

    def playerContent(self,flag,id,vipFlags):
        if id.startswith('http') and '.m3u8' in id:
            return {'parse':0,'url':id,'header':self.headers}
        did=id.split('/')[-1]
        d=self.detailContent([did])['list'][0]
        u=d['vod_play_url'].split('$')[-1].split('$$$')[0]
        return {'parse':0,'url':u,'header':self.headers}

    def localProxy(self,param): return None

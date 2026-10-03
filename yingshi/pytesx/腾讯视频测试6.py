# coding=utf-8
# !/usr/bin/python
import json
import sys
import uuid
import copy
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.dbody = {
            "page_params": {
                "channel_id": "",
                "filter_params": "sort=75",
                "page_type": "channel_operation",
                "page_id": "channel_list_second_page"
            }
        }
        self.body = self.dbody
        pass
    def getName(self):
        return "腾讯视频"
    def isVideoFormat(self, url):
        pass
    def manualVideoCheck(self):
        pass
    def destroy(self):
        pass

    host = 'https://v.qq.com'
    apihost = 'https://pbaccess.video.qq.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
        'origin': host,
        'referer': f'{host}/'
    }

    def safe_get(self, obj, *keys, default=None):
        """安全多层取值，替代硬编码 [-1]"""
        o = obj
        for k in keys:
            if isinstance(o, dict) and k in o:
                o = o[k]
            elif isinstance(o, list) and isinstance(k,int) and 0<=k<len(o):
                o = o[k]
            else:
                return default
        return o

    def get_filter_data(self, cid):
        """串行获取单个分类筛选条件，移除线程池"""
        try:
            hbody = copy.deepcopy(self.dbody)
            hbody['page_params']['channel_id'] = cid
            rsp = self.post(
                f'{self.apihost}/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?video_appid=1000005&vplatform=2&vversion_name=8.9.10&new_mark_label_enabled=1',
                json=hbody, headers=self.headers, timeout=12
            )
            if rsp is None:
                return cid, {}
            data = rsp.json()
            return cid, data
        except Exception as e:
            print(f"get_filter_data fail cid={cid}, err={e}")
            return cid, {}

    def homeContent(self, filter):
        cdata = {
            "电视剧": "100113",
            "电影": "100173",
            "综艺": "100109",
            "纪录片": "100105",
            "动漫": "110755",
            "少儿": "100150",
            "短剧": "110755"
        }
        result = {}
        classes = []
        filters = {}
        for k in cdata:
            classes.append({
                'type_name': k,
                'type_id': cdata[k]
            })

        # 【修复】去掉ThreadPoolExecutor，串行逐个请求，防止同步函数卡死
        for item in classes:
            cid = item['type_id']
            _, data = self.get_filter_data(cid)
            mod_list = self.safe_get(data, "data", "module_list_datas", default=[])
            if not isinstance(mod_list, list) or len(mod_list) == 0:
                continue
            filter_dict = {}
            try:
                # 安全取嵌套，不写死 [-1]
                for mod_data in mod_list:
                    md_list = self.safe_get(mod_data, "module_datas", default=[])
                    if not isinstance(md_list, list):
                        continue
                    for md in md_list:
                        item_datas = self.safe_get(md, "item_data_lists", "item_datas", default=[])
                        if not isinstance(item_datas, list):
                            continue
                        for it in item_datas:
                            params = self.safe_get(it, "item_params", default={})
                            fkey = params.get("index_item_key")
                            if not fkey:
                                continue
                            if fkey not in filter_dict:
                                filter_dict[fkey] = {
                                    'key': fkey,
                                    'name': params.get("index_name", ""),
                                    'value': []
                                }
                            filter_dict[fkey]['value'].append({
                                'n': params.get("option_name",""),
                                'v': params.get("option_value","")
                            })
                if filter_dict:
                    filters[cid] = list(filter_dict.values())
            except Exception as e:
                print(f"parse filter cid={cid} error {e}")
                continue

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        vlist = []
        rsp = self.fetch(self.host, headers=self.headers, timeout=12)
        if rsp is None:
            return {'list': vlist}
        data = self.cleanText(rsp.text)
        import pyquery
        pq = pyquery.PyQuery(data)
        its = pq('script')
        s = None
        for it in its.items():
            txt = it.text()
            if 'window.__INITIAL_STATE__' in txt:
                s = txt
                break
        if s:
            index = s.find('=')
            if index != -1:
                try:
                    sd = json.loads(s[index + 1:])
                    choice = self.safe_get(sd, 'storeModulesData', 'channelsModulesMap', 'choice', default={})
                    cardListData = self.safe_get(choice, 'cardListData', default=[])
                    for its in cardListData:
                        clist = self.safe_get(its, 'children_list','list','cards', default=[])
                        for it in clist:
                            p = self.safe_get(it, 'params', default={})
                            tagRaw = p.get('uni_imgtag') or p.get('imgtag') or '{}'
                            try:
                                tag = json.loads(tagRaw)
                            except:
                                tag = {}
                            id = it.get('id') or p.get('cid')
                            name = p.get('mz_title') or p.get('title')
                            if name and id and 'http' not in str(id):
                                vlist.append({
                                    'vod_id': id,
                                    'vod_name': name,
                                    'vod_pic': p.get('image_url'),
                                    'vod_year': self.safe_get(tag, 'tag_2','text', default=""),
                                    'vod_remarks': self.safe_get(tag, 'tag_4','text', default="")
                                })
                except Exception as e:
                    print(f"homeVideoContent parse error {e}")
        return {'list': vlist}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        params = {
            "sort": extend.get('sort', '75'),
            "attr": extend.get('attr', '-1'),
            "itype": extend.get('itype', '-1'),
            "ipay": extend.get('ipay', '-1'),
            "iarea": extend.get('iarea', '-1'),
            "iyear": extend.get('iyear', '-1'),
            "theater": extend.get('theater', '-1'),
            "award": extend.get('award', '-1'),
            "recommend": extend.get('recommend', '-1')
        }
        if pg == '1':
            self.body = copy.deepcopy(self.dbody)
        self.body['page_params']['channel_id'] = tid
        self.body['page_params']['filter_params'] = self.josn_to_params(params)
        try:
            rsp = self.post(
                f'{self.apihost}/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?video_appid=1000005&vplatform=2&vversion_name=8.9.10&new_mark_label_enabled=1',
                json=self.body, headers=self.headers, timeout=12
            )
            if rsp is None:
                return {'list':[],'page':pg,'pagecount':0}
            data = rsp.json()
            ndata = data.get('data',{})
            has_next_page = bool(ndata.get('has_next_page',False))
            if has_next_page:
                result['pagecount'] = 9999
                self.body['page_context'] = ndata.get('next_page_context','')
            else:
                result['pagecount'] = int(pg)
            vlist = []
            mod_list = self.safe_get(ndata, "module_list_datas", default=[])
            item_datas = []
            for mod in mod_list:
                mds = self.safe_get(mod,"module_datas", default=[])
                for md in mds:
                    ids = self.safe_get(md,"item_data_lists","item_datas", default=[])
                    if isinstance(ids,list):
                        item_datas.extend(ids)
            for its in item_datas:
                p = self.safe_get(its, 'item_params', default={})
                cid = p.get('cid')
                if not cid:
                    continue
                tagRaw = p.get('uni_imgtag') or p.get('imgtag') or '{}'
                try:
                    tag = json.loads(tagRaw)
                except:
                    tag = {}
                name = p.get('mz_title') or p.get('title')
                pic = p.get('new_pic_hz') or p.get('new_pic_vt')
                vlist.append({
                    'vod_id': cid,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_year': self.safe_get(tag,'tag_2','text', default=""),
                    'vod_remarks': self.safe_get(tag,'tag_4','text', default="")
                })
            result['list'] = vlist
            result['page'] = pg
            result['limit'] = 90
            result['total'] = 999999
            return result
        except Exception as e:
            print(f"categoryContent error {e}")
            return {'list':[],'page':pg,'pagecount':0}

    def detailContent(self, ids):
        vbody = {
            "page_params": {
                "req_from": "web",
                "cid": ids[0],
                "vid": "",
                "lid": "",
                "page_type": "detail_operation",
                "page_id": "detail_page_introduction"
            },
            "has_cache": 1
        }
        body = {
            "page_params": {
                "req_from": "web_vsite",
                "page_id": "vsite_episode_list",
                "page_type": "detail_operation",
                "id_type": "1",
                "page_size": "",
                "cid": ids[0],
                "vid": "",
                "lid": "",
                "page_num": "",
                "page_context": "",
                "detail_page_type": "1"
            },
            "has_cache": 1
        }
        try:
            vdata = self.get_vdata(vbody)
            data = self.get_vdata(body)
            pdata = self.process_tabs(data, body, ids)
            if not pdata:
                return self.handle_exception(None, "No pdata available")
            star_list = self.safe_get(vdata, 'data','module_list_datas',0,'module_datas',0,'item_data_lists','item_datas',0,'sub_items','star_list','item_datas', default=[])
            actors = []
            for star in star_list:
                sp = self.safe_get(star, "item_params","name")
                if sp:
                    actors.append(sp)
            names = ['腾讯视频', '预告片']
            plist, ylist = self.process_pdata(pdata, ids)
            if not plist:
                del names[0]
            if not ylist:
                del names[1]
            vod = self.build_vod(vdata, actors, plist, ylist, names)
            return {'list': [vod]}
        except Exception as e:
            return self.handle_exception(e, "Error processing detail")

    def searchContent(self, key, quick, pg="1"):
        body = {
            "version": "24072901",
            "clientType": 1,
            "filterValue": "",
            "uuid": str(uuid.uuid4()),
            "retry": 0,
            "query": key,
            "pagenum": int(pg) - 1,
            "pagesize": 30,
            "queryFrom": 0,
            "searchDatakey": "",
            "transInfo": "",
            "isneedQc": True,
            "preQid": "",
            "adClientInfo": "",
            "extraInfo": {"isNewMarkLabel": "1", "multi_terminal_pc": "1"}
        }
        try:
            rsp = self.post(f'{self.apihost}/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vplatform=2',
                         json=body, headers=self.headers, timeout=12)
            if rsp is None:
                return {'list': [], 'page': pg}
            data = rsp.json()
            boxList = self.safe_get(data,'data','areaBoxList', default=[])
            vlist = []
            for k in boxList:
                doc = self.safe_get(k, 'doc', default={})
                docid = doc.get('id')
                if not docid:
                    continue
                img_tag_str = self.safe_get(k,'videoInfo','imgTag', default="{}")
                try:
                    tag = json.loads(img_tag_str)
                except:
                    tag = {}
                pic = self.safe_get(k,'videoInfo','imgUrl', default="")
                vlist.append({
                    'vod_id': docid,
                    'vod_name': self.safe_get(k,'videoInfo','title', default=""),
                    'vod_pic': pic,
                    'vod_year': self.safe_get(tag,'tag_2','text', default=""),
                    'vod_remarks': self.safe_get(tag,'tag_4','text', default="")
                })
            return {'list': vlist, 'page': pg}
        except Exception as e:
            print(f"searchContent error {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        ids = id.split('@')
        url = f"{self.host}/x/cover/{ids[0]}/{ids[1]}.html"
        parse_url = f"https://jx.xmflv.com/?url={url}"
        return {'parse': 1, 'url': parse_url, 'header': ''}

    def localProxy(self, param):
        pass

    def get_vdata(self, body):
        try:
            rsp = self.post(
                f'{self.apihost}/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?video_appid=3000010&vplatform=2&vversion_name=8.2.96',
                json=body, headers=self.headers, timeout=12
            )
            if rsp is None:
                return {'data': {'module_list_datas': []}}
            return rsp.json()
        except Exception as e:
            print(f"Error in get_vdata: {str(e)}")
            return {'data': {'module_list_datas': []}}

    def process_pdata(self, pdata, ids):
        plist = []
        ylist = []
        for k in pdata:
            if k.get('item_id'):
                union_title = self.safe_get(k, 'item_params','union_title', default="")
                pid = f"{union_title}${ids[0]}@{k['item_id']}"
                if '预告' in union_title:
                    ylist.append(pid)
                else:
                    plist.append(pid)
        return plist, ylist

    def build_vod(self, vdata, actors, plist, ylist, names):
        d = self.safe_get(vdata, 'data','module_list_datas',0,'module_datas',0,'item_data_lists',0,'item_datas',0,'item_params', default={})
        urls = []
        if plist:
            urls.append('#'.join(plist))
        if ylist:
            urls.append('#'.join(ylist))
        vod = {
            'type_name': d.get('sub_genre', ''),
            'vod_name': d.get('title', ''),
            'vod_year': d.get('year', ''),
            'vod_area': d.get('area_name', ''),
            'vod_remarks': d.get('holly_online_time', '') or d.get('hotval', ''),
            'vod_actor': ','.join(actors),
            'vod_content': d.get('cover_description', ''),
            'vod_play_from': '$$$'.join(names),
            'vod_play_url': '$$$'.join(urls)
        }
        return vod

    def handle_exception(self, e, message):
        print(f"{message}: {str(e)}")
        return {'list': [{'vod_play_from': '哎呀翻车啦', 'vod_play_url': '翻车啦#555'}]}

    def process_tabs(self, data, body, ids):
        try:
            pdata = []
            mod_list = self.safe_get(data, "data","module_list_datas", default=[])
            for mod in mod_list:
                mds = self.safe_get(mod,"module_datas", default=[])
                for md in mds:
                    ids_list = self.safe_get(md,"item_data_lists","item_datas", default=[])
                    if isinstance(ids_list,list):
                        pdata.extend(ids_list)
                    tabs_str = self.safe_get(md,"module_params","tabs", default="")
                    if tabs_str:
                        tabs = json.loads(tabs_str)
                        if isinstance(tabs,list):
                            for tab in tabs[1:]:
                                nbody = copy.deepcopy(body)
                                nbody['page_params']['page_context'] = tab.get('page_context','')
                                res_data = self.get_vdata(nbody)
                                sub_mods = self.safe_get(res_data,"data","module_list_datas", default=[])
                                for smod in sub_mods:
                                    smds = self.safe_get(smod,"module_datas", default=[])
                                    for smd in smds:
                                        sub_ids = self.safe_get(smd,"item_data_lists","item_datas", default=[])
                                        if isinstance(sub_ids,list):
                                            pdata.extend(sub_ids)
            return pdata
        except Exception as e:
            print(f"Error processing episodes: {str(e)}")
            return []

    def josn_to_params(self, params, skip_empty=False):
        query = []
        for k, v in params.items():
            if skip_empty and not v:
                continue
            query.append(f"{k}={v}")
        return "&".join(query)
#（注：内容由AI生成）

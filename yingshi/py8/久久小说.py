# -*- coding: utf-8 -*-
import sys
import json
import requests
from lxml import etree
import re
sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        pass

class Spider(BaseSpider):
    def getName(self):
        return "久久小说网"

    def init(self, extend=""):
        self.vod = Vod()

    def homeContent(self, filter):
        classes = [
            {'type_id': 'xuanhuan', 'type_name': '玄幻小说'},
            {'type_id': 'dushi', 'type_name': '都市小说'},
            {'type_id': 'young', 'type_name': '现言小说'},
            {'type_id': 'qinggan', 'type_name': '总裁言情'},
            {'type_id': 'chuanyue', 'type_name': '穿越小说'},
            {'type_id': 'chongshengxiaoshuo', 'type_name': '重生小说'},
            {'type_id': 'lsjs', 'type_name': '架空历史'},
            {'type_id': 'wuxia', 'type_name': '仙侠武侠'},
            {'type_id': 'dmtr', 'type_name': '耽美纯美'},
            {'type_id': 'kongbu', 'type_name': '惊悚恐怖'},
            {'type_id': '', 'type_name': '全部小说'}
        ]
        
        filterObj = {
            "": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "xuanhuan": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "dushi": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "young": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "qinggan": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "chuanyue": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "chongshengxiaoshuo": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "lsjs": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "wuxia": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "dmtr": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ],
            "kongbu": [
                {"key": "orderby", "name": "排序", "value": [{"v": "1", "n": "时间先后"}, {"v": "2", "n": "人气高低"}, {"v": "3", "n": "收藏次数"}]},
                {"key": "qujian", "name": "大小", "value": [{"v": "", "n": "不限"}, {"v": "1", "n": "中短篇"}, {"v": "2", "n": "中长篇"}, {"v": "3", "n": "较长篇"}, {"v": "4", "n": "超长篇"}]},
                {"key": "lastday", "name": "更新", "value": [{"v": "", "n": "不限"}, {"v": "3", "n": "三天内"}, {"v": "7", "n": "一周内"}, {"v": "30", "n": "一月内"}, {"v": "180", "n": "半年内"}]}
            ]
        }
        return {'class': classes, 'filters': filterObj}

    def homeVideoContent(self):
        return self.categoryContent('', '1', None, {})

    def categoryContent(self, cid, page, filter, ext):
        return self.vod.categoryContent(cid, page, filter, ext)

    def detailContent(self, did):
        return self.vod.detailContent(did)

    def searchContent(self, key, quick, page='1'):
        return self.vod.searchContent(key, page)

    def playerContent(self, flag, pid, vipFlags=None):
        return self.vod.playerContent(flag, pid)

class Vod:
    def __init__(self):
        self.home_url = 'https://m.ijjjjxsw.com'
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.home_url + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def categoryContent(self, cid, page, filter, ext):
        if not cid:
            base_url = f'{self.home_url}/txt/'
        else:
            base_url = f'{self.home_url}/txt/{cid}/'
        
        try:
            r = self.session.get(base_url.rstrip('/'), headers=self.headers, timeout=10)
            r.encoding = 'utf-8'
            root = etree.HTML(r.text)
            classid_match = re.search(r'classid=(\d+)', ''.join(root.xpath('//a[contains(@href,"ListInfo.php")]/@href')))
            classid = classid_match.group(1) if classid_match else "14"
        except:
            classid = "14"
        page_num = int(page) if page and page.isdigit() else 1
        url = f"{self.home_url}/e/action/ListInfo.php?page={page_num}&classid={classid}&tempid=3&ph={page_num}"
        if ext and isinstance(ext, dict):
            if ext.get('lastday'): url += f'&lastday={ext["lastday"]}'
            if ext.get('qujian'): url += f'&qujian={ext["qujian"]}'
            if ext.get('orderby'): url += f'&orderby={ext["orderby"]}'
        try:
            r = self.session.get(url, headers=self.headers, timeout=12)
            r.encoding = 'utf-8'
            return {'list': self.parse_common(r.text), 'pagecount': 200}
        except Exception as e:
            print(f"分类请求失败: {url} → {e}")
            return {'list': []}

    # 【终极优化搜索】完全适配网站真实搜索源码
    def searchContent(self, key, page='1'):
        # 1. 关键词预处理（保留原始语义，仅去首尾空格，适配网站模糊匹配）
        key = key.strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}
        
        page_num = int(page) if page and page.isdigit() else 1
        # 2. 完全匹配网站搜索表单：action地址+参数名（与源码<form>标签一致）
        search_url = f"{self.home_url}/e/search/index.php"
        post_data = {
            "keyboard": key,          # 关键词输入框name属性
            "show": "writer,title",   # 搜索范围（书名/作者，与源码select默认值一致）
            "Submit22": "搜索",       # 提交按钮name属性
            "tempid": "3"             # 模板ID（网站固定参数）
        }
        
        # 3. 分页参数处理（网站分页通过URL参数page传递）
        if page_num > 1:
            search_url += f"?page={page_num}"
        
        try:
            # 4. 模拟真实访问流程：先访问首页获取Cookie
            self.session.get(self.home_url, headers=self.headers, timeout=8)
            # 5. 提交表单（与网站表单method="post"一致）
            r = self.session.post(
                search_url,
                data=post_data,
                headers=self.headers,
                timeout=15,
                allow_redirects=True
            )
            r.encoding = 'utf-8'
            
            # 6. 解析搜索结果（完全适配网站页面结构）
            search_list = self.parse_search_result(r.text)
            # 7. 从页面提取总记录数（更精准）
            total = self.extract_total_count(r.text)
            pagecount = (total + 19) // 20  # 每页20条，计算总页数
            
            return {
                'list': search_list,
                'page': page_num,
                'pagecount': pagecount if pagecount > 0 else 1,
                'limit': 20,
                'total': total
            }
        except Exception as e:
            print(f"搜索异常: {e}")
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

    # 【新增】专门解析搜索结果（适配网站真实DOM结构）
    def parse_search_result(self, html):
        root = etree.HTML(html)
        vods = []
        # 完全匹配网站搜索结果容器：div.booklist_a > ul > li > div.list_a（与源码一致）
        items = root.xpath('//div[@class="booklist_a"]/ul/li/div[@class="list_a"]')
        
        for item in items:
            try:
                # 解析标题（适配源码strong标签包裹的标题）
                title = ''.join(item.xpath('.//div[@class="main"]/a/strong//text()')).strip()
                if not title:
                    title = ''.join(item.xpath('.//div[@class="main"]/a//text()')).strip()
                # 解析链接
                link = ''.join(item.xpath('.//div[@class="main"]/a/@href')).strip()
                if not title or not link:
                    continue
                # 解析图片（适配源码//开头的图片URL）
                pic = ''.join(item.xpath('.//div[@class="img"]/a/img/@src')).strip()
                if pic:
                    pic = 'https:' + pic if pic.startswith('//') else self.home_url + '/' + pic.lstrip('/') if not pic.startswith('http') else pic
                else:
                    pic = 'https://image.ijjjjxsw.com/skin/images/nopic.jpg'
                # 解析作者（适配源码<span>作者:xxx</span>格式）
                author = ''.join(item.xpath('.//span[contains(text(),"作者:")]/text()')).replace('作者:', '').strip()
                # 解析分类和大小（适配源码[分类] 大小:xxx格式）
                category = ''.join(item.xpath('.//span/a[contains(@href,"/txt/")]/text()')).strip()
                size = ''.join(item.xpath('.//span[contains(text(),"大小:")]/text()')).replace('大小:', '').strip()
                meta = f"[{category}] {size}" if category or size else ""
                remarks = f"{author} | {meta}" if author or meta else "TXT小说"
                
                vods.append({
                    "vod_id": link,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            except Exception as e:
                print(f"解析搜索结果异常: {e}")
                continue
        
        return vods

    # 【新增】从搜索页面提取总记录数（与网站显示一致）
    def extract_total_count(self, html):
        root = etree.HTML(html)
        # 匹配源码"搜索xxx，有x条记录"格式
        total_text = ''.join(root.xpath('//div[@class="header"]/div[@class="left"]/text()')).strip()
        match = re.search(r'有(\d+)条记录', total_text)
        return int(match.group(1)) if match else 0

    # 通用解析逻辑（分类列表专用）
    def parse_common(self, html):
        root = etree.HTML(html)
        vods = []
        items = root.xpath('//div[@class="booklist_a"]/ul/li/div[@class="list_a"]')
        
        for item in items:
            try:
                title = ''.join(item.xpath('.//div[@class="main"]/a/strong//text()')).strip()
                if not title:
                    title = ''.join(item.xpath('.//div[@class="main"]/a//text()')).strip()
                link = ''.join(item.xpath('.//div[@class="main"]/a/@href')).strip()
                if not title or not link: continue
                pic = ''.join(item.xpath('.//div[@class="img"]/a/img/@src')).strip()
                if pic:
                    if pic.startswith('//'):
                        pic = 'https:' + pic
                    elif not pic.startswith('http'):
                        pic = self.home_url + '/' + pic.lstrip('/')
                else:
                    pic = 'https://image.ijjjjxsw.com/skin/images/nopic.jpg'
                author = ''.join(item.xpath('.//span[contains(text(),"作者:")]/following-sibling::text() | .//span[contains(text(),"作者:")]/a/text()')).replace('作者:', '').strip()
                meta = ' '.join(item.xpath('.//span[contains(@class,"oldDate") or contains(text(),"大小:")]/text()')).strip()
                remarks = f"{author} | {meta}" if author or meta else "TXT小说"
                vods.append({
                    "vod_id": link,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            except Exception as e:
                print(f"解析分类数据异常: {e}")
                continue
        return vods

    def detailContent(self, did):
        url = did if isinstance(did, str) else did[0]
        if not url.startswith('http'):
            url = self.home_url + (url if url.startswith('/') else '/' + url)
        
        try:
            r = self.session.get(url, headers=self.headers, timeout=15)
            r.encoding = 'utf-8'
            root = etree.HTML(r.text)
            name = ''.join(root.xpath('//h1/text() | //div[@class="jie"]/h1/text()')).strip() or "未知书名"
            pic = ''.join(root.xpath('//div[@class="pic"]/img/@src')).strip()
            if pic:
                if pic.startswith('//'):
                    pic = 'https:' + pic
                elif not pic.startswith('http'):
                    pic = self.home_url + '/' + pic.lstrip('/')
            else:
                pic = 'https://image.ijjjjxsw.com/skin/images/nopic.jpg'
            
            intro = ''.join(root.xpath('//div[@class="novelinfo"]//text()')).strip().replace('\xa0', ' ')
            
            script_text = ''.join(root.xpath('//script[contains(text(),"bookinfo")]/text()'))
            cid = re.search(r'"cid":(\d+)', script_text)
            aid = re.search(r'"aid":(\d+)', script_text)
            cid = cid.group(1) if cid else '11'
            aid = aid.group(1) if aid else url.split('/')[-1].replace('.html', '')
            
            catalog_url = f"{self.home_url}/read/{cid}/{aid}/"
            r_cat = self.session.get(catalog_url, headers=self.headers, timeout=15)
            r_cat.encoding = 'utf-8'
            root_cat = etree.HTML(r_cat.text)
            
            chapters = root_cat.xpath('//a[contains(@href,"/read/") and contains(@href,".html")]')
            play_urls = []
            seen = set()
            for c in chapters:
                cname = ''.join(c.xpath('.//text()')).strip()
                if not cname or cname in seen or len(cname) < 2 or any(x in cname for x in ['上一页','下一页','目录','返回']):
                    continue
                seen.add(cname)
                curl = c.xpath('./@href')[0].strip()
                if not curl.startswith('http'):
                    curl = self.home_url + (curl if curl.startswith('/') else '/' + curl)
                play_urls.append(f"{cname}${curl}")
            
            vod_play_url = "#".join(play_urls) if play_urls else "暂无章节$javascript:;"
            
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_content": intro or "暂无简介",
                    "vod_play_from": "久久小说",
                    "vod_play_url": vod_play_url
                }]
            }
        except Exception as e:
            print(f"详情解析异常: {e}")
            return {'list': []}

    def playerContent(self, flag, pid):
        try:
            url = pid if pid.startswith('http') else self.home_url + (pid if pid.startswith('/') else '/' + pid)
            r = self.session.get(url, headers=self.headers, timeout=15)
            r.encoding = 'utf-8'
            root = etree.HTML(r.text)
            title = ''.join(root.xpath('//h1[@id="BookName"]/text() | //h1/text()')).strip() or "正文"
            content_nodes = root.xpath('//span[@id="Content"]//text() | //div[@class="chapter_content"]//text() | //div[@id="content"]//text()')
            lines = []
            junk = ['上一页', '下一页', '回顶部', '报错', '久久小说网', 'TXT下载', '白天', '黑夜', '护眼', '第\\d+页']
            for text in content_nodes:
                line = text.strip().replace('\xa0', ' ').replace('&nbsp;', ' ')
                if not line: continue
                if any(re.search(p, line, re.I) for p in junk): continue
                if re.match(r'^第\d+章', line) and len(line) < 40: continue
                lines.append(line)
            content = '\n\n'.join(lines).strip() or "正文提取失败"
            data = {"title": title, "content": content}
            return {
                "parse": 0,
                "playUrl": "",
                "url": "novel://" + json.dumps(data, ensure_ascii=False),
                "header": ""
            }
        except Exception as e:
            return {
                "parse": 0,
                "playUrl": "",
                "url": "novel://" + json.dumps({"title": "读取失败", "content": str(e)}, ensure_ascii=False),
                "header": ""
            }

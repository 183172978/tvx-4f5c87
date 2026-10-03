#coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json, base64
from urllib.parse import urlencode, quote, unquote, urlsplit

host_url = 'https://frodo.douban.com/api/v2'
apikey = "?apiKey=0ac44ae016490db2204ce0a042db2916"

# 豆瓣 APP UA：带这个 UA 请求 img1/img2/img3 可以绕过 Referer 校验（无需Referer就能返回真图）
douban_app_ua = "com.douban.frodo/7.85.0(235) DoubanApp OS:Android API33 Device:Pixel7"
# 桌面 UA（当 APP UA 失败时作为回退，配合 Referer 使用）
desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

# ================= 兜底开关（影视仓无封面时默认打开） =================
# 说明：直接把封面图片下载并内联为 data:image/jpeg;base64,...
#       100% 不经过本地代理，不依赖 APP 的 getProxyUrl/localProxy 路由
#       代价：列表加载稍慢（串行请求封面），长列表最多内联 BASE64_MAX_ITEM 条
USE_BASE64_INLINE = True
BASE64_MAX_ITEM = 60
BASE64_TIMEOUT = 5
# ====================================================================

class Spider(Spider):
	def getName(self):
		return "豆瓣"
	def init(self,extend=""):
		print("============{0}============".format(extend))
		pass
	def isVideoFormat(self,url):
		pass
	def manualVideoCheck(self):
		pass
	def homeContent(self,filter):
		result = {}
		cateManual = {
			"热门电影": "hot_gaia",
			"热播剧集": "tv_hot",
			"热播综艺": "show_hot",
			"电影筛选": "movie",
			"电视筛选": "tv",
			"电影榜单": "rank_list_movie",
			"电视榜单": "rank_list_tv"
		}
		classes = []
		for k in cateManual:
			classes.append({
				'type_name':k,
				'type_id':cateManual[k]
			})
		result['class'] = classes
		if(filter):
			result['filters'] = self.config['filter']
		return result

	# ================ 封面处理：URL 清洗 + 兜底内联 =================
	def _douban_img_url_clean(self, url):
		if not url:
			return ""
		# img9 即使带 Referer 也只返回验证页/占位HTML，统一换成 img1
		for old in ("img9.doubanio.com", "img2.doubanio.com", "img3.doubanio.com"):
			url = url.replace(old, "img1.doubanio.com")
		return url

	def _b64_inline(self, url):
		"""兜底：直接把封面拉下来并以 data:image/jpeg;base64 内联。性能差但不依赖本地代理。"""
		if not url:
			return ""
		url = self._douban_img_url_clean(url)
		try:
			headers = {"User-Agent": douban_app_ua, "Referer": "https://movie.douban.com/"}
			r = self.fetch(url, headers=headers, timeout=BASE64_TIMEOUT)
			if r is None:
				return ""
			ct = 'image/jpeg'
			if hasattr(r, 'headers') and r.headers.get('content-type'):
				ct = r.headers.get('content-type').split(';')[0].strip() or 'image/jpeg'
			if hasattr(r, 'content'):
				body = r.content
			elif isinstance(getattr(r, 'text', ''), bytes):
				body = r.text
			else:
				body = (getattr(r, 'text', '') or '').encode('utf-8', errors='ignore')
			if len(body) < 5000:
				return ""
			b64 = base64.b64encode(body).decode('ascii')
			return "data:{0};base64,{1}".format(ct, b64)
		except Exception:
			return ""

	def fixCover(self, url):
		"""生成 vod_pic：
		1) 若开关打开，直接内联 base64（不依赖本地代理，影视仓最兼容方案）；
		2) 否则走本地9978代理，附带 name/extend/if/spider/src 多组路由参数，
		   同时强制 path=/proxy，适配 OK影视 / TVBox / 影视仓(PyramidStore) 各种路由规则。
		"""
		if not url:
			return ""
		url = self._douban_img_url_clean(url)
		if USE_BASE64_INLINE:
			d = self._b64_inline(url)
			if d:
				return d
		spider_name = self.getName()
		# ============================================================
		# 多路由参数：覆盖 OK影视 (do=py&if=) / 影视仓 (name= / extend= / spider= / src=)
		# 同时附带 url= 明文 和 quote 过的兼容字段
		# ============================================================
		q_url = quote(url, safe='')
		params = [
			("do", "py"),
			("name",   spider_name),
			("extend", spider_name),
			("if",     spider_name),
			("spider", spider_name),
			("src",    spider_name),
			("url",    url),          # 明文：部分 APP 不做 unquote
			("u",      q_url),        # 简写：兼容特殊版本取值
			("pic",    q_url),        # 影视仓部分分支把图当 pic 字段
		]
		qs = urlencode(params)
		proxy_base = None
		if hasattr(self, 'getProxyUrl'):
			try:
				proxy_base = self.getProxyUrl()
			except Exception:
				proxy_base = None
		if proxy_base:
			try:
				p = urlsplit(proxy_base)
				new_scheme = p.scheme or "http"
				new_netloc = p.netloc or "127.0.0.1:9978"
				# 强制 path=/proxy（OK影视 proven 可用格式，影视仓也识别该路径）
				base = "{0}://{1}/proxy".format(new_scheme, new_netloc)
				return "{0}?{1}".format(base, qs)
			except Exception:
				pass
		return "http://127.0.0.1:9978/proxy?{0}".format(qs)

	def homeVideoContent(self):
		url = host_url + '/subject_collection/subject_real_time_hotest/items' + apikey
		rsp = self.fetch(url, headers=self.header)
		jo = json.loads(rsp.text)
		joList = jo.get("subject_collection_items") or []
		lists = []
		b64_count = 0
		for item in joList:
			rating = item.get('rating', {}).get('value', '') if item.get('rating') else ""
			year = item.get('year', '')
			pic = item.get('cover_url') or item.get('pic', {}).get('large', '') or item.get('pic', {}).get('normal', '')
			# 超过内联阈值后强制跳过 b64 走代理（防止超时）
			if USE_BASE64_INLINE and b64_count >= BASE64_MAX_ITEM:
				# 临时关闭内联仅本条：用自定义走代理分支
				saved = self.__dict__.pop('_b64_tmp_off', None)
				cover = self._fallback_proxy_cover(pic)
			else:
				cover = self.fixCover(pic)
				if cover.startswith("data:"):
					b64_count += 1
			lists.append({
				"vod_id": f'msearch:{item.get("type", "")}__{item.get("id", "")}',
				"vod_name": item.get('title', ''),
				"vod_pic": cover,
				"vod_remarks": f'{year} {rating}'.strip()
			})
		result = {
			'list':lists
		}
		return result

	def _fallback_proxy_cover(self, url):
		"""仅走代理的封面版本（不做 base64）。"""
		if not url:
			return ""
		url = self._douban_img_url_clean(url)
		spider_name = self.getName()
		q_url = quote(url, safe='')
		params = [
			("do","py"),
			("name",spider_name),("extend",spider_name),("if",spider_name),
			("spider",spider_name),("src",spider_name),
			("url",url),("u",q_url),("pic",q_url),
		]
		qs = urlencode(params)
		proxy_base = None
		if hasattr(self, 'getProxyUrl'):
			try:
				proxy_base = self.getProxyUrl()
			except Exception:
				proxy_base = None
		if proxy_base:
			try:
				p = urlsplit(proxy_base)
				base = "{0}://{1}/proxy".format(p.scheme or "http", p.netloc or "127.0.0.1:9978")
				return "{0}?{1}".format(base, qs)
			except Exception:
				pass
		return "http://127.0.0.1:9978/proxy?{0}".format(qs)

	def categoryContent(self,tid,pg,filter,extend):
		result = {}
		params = {'start': str((int(pg) - 1) * 30)}
		if tid == "hot_gaia":
			urlpath = f"/movie/{tid}"
			params['sort'] = extend.get("sort", "recommend")
			area = extend.get("area", "全部")
			if area and area != "全部":
				params['area'] = area
			year = extend.get("year", "")
			if year:
				params['year'] = year
			tags = extend.get("type", "")
			if tags:
				params['tags'] = tags
			getdata = "items"
		elif tid == "tv_hot" or tid == "show_hot":
			s_type = extend.get("type", tid)
			urlpath = f"/subject_collection/{s_type}/items"
			getdata = "subject_collection_items"
		elif tid.startswith("rank_list"):
			id = "movie_real_time_hotest" if tid == "rank_list_movie" else "tv_real_time_hotest"
			urlpath = f"/subject_collection/{id}/items"
			getdata = "subject_collection_items"
		else:
			urlpath = f"/{tid}/recommend"
			params['sort'] = extend.pop('sort') if "sort" in extend else "T"
			params['tags'] = ",".join(item for item in extend.values())
			getdata = "items"
		query = apikey + "&" + urlencode(params)
		url = host_url + urlpath + query
		rsp = self.fetch(url, headers=self.header)
		jo = json.loads(rsp.text)
		jolist = jo.get(getdata) or []
		videos = []
		b64_count = 0
		for vod in jolist:
			if vod.get("type", "") == "movie" or vod.get("type", "") == "tv":
				rating = vod.get("rating", {}).get("value", '') if vod.get("rating") else ""
				pic = vod.get('cover_url') or vod.get("pic", {}).get("large", "") or vod.get("pic", {}).get("normal", "")
				title = vod.get("title", "")
				year = vod.get('year', '')
				if USE_BASE64_INLINE and b64_count >= BASE64_MAX_ITEM:
					cover = self._fallback_proxy_cover(pic)
				else:
					cover = self.fixCover(pic)
					if cover.startswith("data:"):
						b64_count += 1
				videos.append({
					"vod_id": f'msearch:{vod.get("type", "")}__{vod.get("id", "")}',
					"vod_name": title,
					"vod_pic": cover,
					"vod_remarks": f'{year} {rating}'.strip()
				})
		result['list'] = videos
		result['page'] = pg
		result['pagecount'] = 9999
		result['limit'] = 90
		result['total'] = 999999
		return result

	def detailContent(self,array):
		pass
	def searchContent(self,key,quick):
		pass
	def playerContent(self,flag,id,vipFlags):
		pass

	# ================ localProxy：最大兼容 + 双通道 UA + 真图校验 ================
	def _extract_proxy_url(self, param):
		"""最大兼容：从 localProxy 入参中尽力取出目标 url"""
		url = ""
		if param is None:
			return ""
		if isinstance(param, str):
			url = param
		elif isinstance(param, dict):
			candidates = ['url','pic','img','target','src','image','href','link','path','uri','raw','u']
			for k in candidates:
				v = param.get(k)
				if v:
					if isinstance(v, list) and len(v) > 0:
						v = v[0]
					if isinstance(v, (bytes, bytearray)):
						try:
							url = v.decode('utf-8', errors='ignore')
						except Exception:
							url = ""
					else:
						url = str(v)
					if url:
						break
			if not url:
				for vv in param.values():
					if isinstance(vv, str) and vv.startswith("http"):
						url = vv
						break
		elif isinstance(param, (list, tuple)) and len(param) > 0:
			first = param[0]
			if isinstance(first, dict):
				return self._extract_proxy_url(first)
			elif isinstance(first, str):
				url = first
			else:
				try:
					url = str(first)
				except Exception:
					url = ""
		else:
			try:
				url = str(param)
			except Exception:
				url = ""
		if not url:
			return ""
		url = url.strip().strip("\"'").strip()
		if not url:
			return ""
		# 可能双重 urlencode
		try:
			for _ in range(2):
				if "%" in url and "doubanio.com" not in url:
					url = unquote(url)
				elif "%25" in url:
					url = unquote(url)
				else:
					break
		except Exception:
			pass
		return url

	def localProxy(self, param):
		try:
			url = self._extract_proxy_url(param)
			if not url:
				return [404, "text/plain", "", "no url"]
			if "doubanio.com" not in url and "douban.com" not in url:
				return [404, "text/plain", "", "not douban url"]
			url = self._douban_img_url_clean(url)
			rsp = None
			got_image = False
			# 1) 豆瓣APP UA：本地代理也用它，不依赖 Referer
			try:
				rsp = self.fetch(url, headers={
					"User-Agent": douban_app_ua,
					"Referer": "https://movie.douban.com/"
				}, timeout=8)
			except Exception:
				rsp = None
			# 判定是否拿到真图（content-type=image 且 size>5k）
			if rsp is not None:
				try:
					body0 = getattr(rsp, 'content', b'')
					sz = len(body0) if isinstance(body0, (bytes, bytearray)) else 0
					if sz < 100:
						t = getattr(rsp, 'text', '') or ''
						if isinstance(t, str):
							sz = len(t.encode('utf-8', errors='ignore'))
						else:
							sz = len(bytes(t))
					ct = ''
					if hasattr(rsp, 'headers') and rsp.headers:
						ct = (rsp.headers.get('content-type') or '').lower()
					if 'image' in ct and sz > 5000:
						got_image = True
				except Exception:
					pass
			# 2) 若APP UA没拿到真图，回退桌面 UA + Referer
			if not got_image:
				try:
					rsp = self.fetch(url, headers={
						"User-Agent": desktop_ua,
						"Referer": "https://movie.douban.com/",
						"Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
					}, timeout=10)
				except Exception:
					rsp = None
			if rsp is None:
				return [502, "text/plain", "", "fetch failed"]
			ctype = 'image/jpeg'
			if hasattr(rsp, 'headers') and rsp.headers.get('content-type'):
				ctype = rsp.headers.get('content-type')
			if hasattr(rsp, 'content'):
				body = rsp.content
			else:
				text_body = getattr(rsp, 'text', '') or ''
				if isinstance(text_body, (bytes, bytearray)):
					body = bytes(text_body)
				else:
					body = text_body.encode('utf-8', errors='ignore')
			extra_headers = (
				"Content-Type: {0}\r\n"
				"Cache-Control: public, max-age=86400\r\n"
				"Content-Length: {1}\r\n"
			).format(ctype, len(body))
			return [200, ctype, body, extra_headers]
		except Exception as e:
			return [500, "text/plain", "", str(e)]

	config = {
		"player": {},
		"filter": {"hot_gaia":[{"key":"sort","name":"排序","value":[{"n":"热度","v":"recommend"},{"n":"最新","v":"time"},{"n":"评分","v":"rank"}]},{"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"动作","v":"动作"},{"n":"科幻","v":"科幻"},{"n":"动画","v":"动画"},{"n":"悬疑","v":"悬疑"},{"n":"犯罪","v":"犯罪"},{"n":"惊悚","v":"惊悚"},{"n":"冒险","v":"冒险"},{"n":"音乐","v":"音乐"},{"n":"历史","v":"历史"},{"n":"奇幻","v":"奇幻"},{"n":"恐怖","v":"恐怖"},{"n":"战争","v":"战争"},{"n":"传记","v":"传记"},{"n":"歌舞","v":"歌舞"},{"n":"武侠","v":"武侠"},{"n":"情色","v":"情色"},{"n":"灾难","v":"灾难"},{"n":"西部","v":"西部"},{"n":"纪录片","v":"纪录片"},{"n":"短片","v":"短片"}]},{"key":"area","name":"地区","value":[{"n":"全部","v":"全部"},{"n":"华语","v":"华语"},{"n":"欧美","v":"欧美"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"}]},{"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2010年代","v":"2010年代"},{"n":"2000年代","v":"2000年代"},{"n":"90年代","v":"90年代"},{"n":"80年代","v":"80年代"},{"n":"70年代","v":"70年代"},{"n":"60年代","v":"60年代"},{"n":"更早","v":"更早"}]}],"tv_hot":[{"key":"type","name":"分类","value":[{"n":"综合","v":"tv_hot"},{"n":"国产剧","v":"tv_domestic"},{"n":"欧美剧","v":"tv_american"},{"n":"日剧","v":"tv_japanese"},{"n":"韩剧","v":"tv_korean"},{"n":"动画","v":"tv_animation"}]}],"show_hot":[{"key":"type","name":"分类","value":[{"n":"综合","v":"show_hot"},{"n":"国内","v":"show_domestic"},{"n":"国外","v":"show_foreign"}]}],"movie":[{"key":"类型","name":"类型","value":[{"n":"全部类型","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"动作","v":"动作"},{"n":"科幻","v":"科幻"},{"n":"动画","v":"动画"},{"n":"悬疑","v":"悬疑"},{"n":"犯罪","v":"犯罪"},{"n":"惊悚","v":"惊悚"},{"n":"冒险","v":"冒险"},{"n":"音乐","v":"音乐"},{"n":"历史","v":"历史"},{"n":"奇幻","v":"奇幻"},{"n":"恐怖","v":"恐怖"},{"n":"战争","v":"战争"},{"n":"传记","v":"传记"},{"n":"歌舞","v":"歌舞"},{"n":"武侠","v":"武侠"},{"n":"情色","v":"情色"},{"n":"灾难","v":"灾难"},{"n":"西部","v":"西部"},{"n":"纪录片","v":"纪录片"},{"n":"短片","v":"短片"}]},{"key":"地区","name":"地区","value":[{"n":"全部地区","v":""},{"n":"华语","v":"华语"},{"n":"欧美","v":"欧美"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"},{"n":"中国大陆","v":"中国大陆"},{"n":"美国","v":"美国"},{"n":"中国香港","v":"中国香港"},{"n":"中国台湾","v":"中国台湾"},{"n":"英国","v":"英国"},{"n":"法国","v":"法国"},{"n":"德国","v":"德国"},{"n":"意大利","v":"意大利"},{"n":"西班牙","v":"西班牙"},{"n":"印度","v":"印度"},{"n":"泰国","v":"泰国"},{"n":"俄罗斯","v":"俄罗斯"},{"n":"加拿大","v":"加拿大"},{"n":"澳大利亚","v":"澳大利亚"},{"n":"爱尔兰","v":"爱尔兰"},{"n":"瑞典","v":"瑞典"},{"n":"巴西","v":"巴西"},{"n":"丹麦","v":"丹麦"}]},{"key":"sort","name":"排序","value":[{"n":"近期热度","v":"T"},{"n":"首映时间","v":"R"},{"n":"高分优先","v":"S"}]},{"key":"年代","name":"年代","value":[{"n":"全部年代","v":""},  {"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2010年代","v":"2010年代"},{"n":"2000年代","v":"2000年代"},{"n":"90年代","v":"90年代"},{"n":"80年代","v":"80年代"},{"n":"70年代","v":"70年代"},{"n":"60年代","v":"60年代"},{"n":"更早","v":"更早"}]}],"tv":[{"key":"类型","name":"类型","value":[{"n":"不限","v":""},{"n":"电视剧","v":"电视剧"},{"n":"综艺","v":"综艺"}]},{"key":"电视剧形式","name":"电视剧形式","value":[{"n":"不限","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"悬疑","v":"悬疑"},{"n":"动画","v":"动画"},{"n":"武侠","v":"武侠"},{"n":"古装","v":"古装"},{"n":"家庭","v":"家庭"},{"n":"犯罪","v":"犯罪"},{"n":"科幻","v":"科幻"},{"n":"恐怖","v":"恐怖"},{"n":"历史","v":"历史"},{"n":"战争","v":"战争"},{"n":"动作","v":"动作"},{"n":"冒险","v":"冒险"},{"n":"传记","v":"传记"},{"n":"剧情","v":"剧情"},{"n":"奇幻","v":"奇幻"},{"n":"惊悚","v":"惊悚"},{"n":"灾难","v":"灾难"},{"n":"歌舞","v":"歌舞"},{"n":"音乐","v":"音乐"}]},{"key":"综艺形式","name":"综艺形式","value":[{"n":"不限","v":""},{"n":"真人秀","v":"真人秀"},{"n":"脱口秀","v":"脱口秀"},{"n":"音乐","v":"音乐"},{"n":"歌舞","v":"歌舞"}]},{"key":"地区","name":"地区","value":[{"n":"全部地区","v":""},{"n":"华语","v":"华语"},{"n":"欧美","v":"欧美"},{"n":"国外","v":"国外"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"},{"n":"中国大陆","v":"中国大陆"},{"n":"中国香港","v":"中国香港"},{"n":"美国","v":"美国"},{"n":"英国","v":"英国"},{"n":"泰国","v":"泰国"},{"n":"中国台湾","v":"中国台湾"},{"n":"意大利","v":"意大利"},{"n":"法国","v":"法国"},{"n":"德国","v":"德国"},{"n":"西班牙","v":"西班牙"},{"n":"俄罗斯","v":"俄罗斯"},{"n":"瑞典","v":"瑞典"},{"n":"巴西","v":"巴西"},{"n":"丹麦","v":"丹麦"},{"n":"印度","v":"印度"},{"n":"加拿大","v":"加拿大"},{"n":"爱尔兰","v":"爱尔兰"},{"n":"澳大利亚","v":"澳大利亚"}]},{"key":"sort","name":"排序","value":[{"n":"近期热度","v":"T"},{"n":"首播时间","v":"R"},{"n":"高分优先","v":"S"}]},{"key":"年代","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2010年代","v":"2010年代"},{"n":"2000年代","v":"2000年代"},{"n":"90年代","v":"90年代"},{"n":"80年代","v":"80年代"},{"n":"70年代","v":"70年代"},{"n":"60年代","v":"60年代"},{"n":"更早","v":"更早"}]},{"key":"平台","name":"平台","value":[{"n":"全部","v":""},{"n":"腾讯视频","v":"腾讯视频"},{"n":"爱奇艺","v":"爱奇艺"},{"n":"优酷","v":"优酷"},{"n":"湖南卫视","v":"湖南卫视"},{"n":"Netflix","v":"Netflix"},{"n":"HBO","v":"HBO"},{"n":"BBC","v":"BBC"},{"n":"NHK","v":"NHK"},{"n":"CBS","v":"CBS"},{"n":"NBC","v":"NBC"},{"n":"tvN","v":"tvN"}]}],"rank_list_movie":[{"key":"榜单","name":"榜单","value":[{"n":"实时热门电影","v":"movie_real_time_hotest"},{"n":"一周口碑电影榜","v":"movie_weekly_best"},{"n":"豆瓣电影Top250","v":"movie_top250"}]}],"rank_list_tv":[{"key":"榜单","name":"榜单","value":[{"n":"实时热门电视","v":"tv_real_time_hotest"},{"n":"华语口碑剧集榜","v":"tv_chinese_best_weekly"},{"n":"全球口碑剧集榜","v":"tv_global_best_weekly"},{"n":"国内口碑综艺榜","v":"show_chinese_best_weekly"},{"n":"国外口碑综艺榜","v":"show_global_best_weekly"}]}]}
	}
	header = {
		"Host": "frodo.douban.com",
		"Connection": "Keep-Alive",
		"Referer": "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html",
		"content-type": "application/json",
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat"
	}

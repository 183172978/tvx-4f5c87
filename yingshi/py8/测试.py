# -*- coding: utf-8 -*-
# ==========================================================================
# 📌 版本记录：LocalTitan_v223_Unified_Shield (三位一体过滤版)
#    综合读取
# ==========================================================================

import os, json, time, gc, re, base64

class Spider():
    # ==========================================================================
    # 💎 【1. 核心导航配置区】       #综合读取
    # ==========================================================================
    CHANNEL_PAGE_SIZE = 1000  

    SCAN_DIR_LIST = [
                "bh"#, "tvbox",  "bhh",         #👈电视📺专用文件夹，把db文件放在这里# 👈 u盘也用这个文件夹                                          
             #   "lz", "纯福利", "私藏视频",  "江湖",          # 👈 前面加#关闭   这里可以修改任意大佬包名 
         #       "VodPlus", "peekpili/php-scripts"                       #同上
          ]       
    # ==========================================================================
      # 🚫 [门阀 文件夹：深度文件夹拦截] 
    DIR_BLACK_LIST = [
        "PQ类", "YQ类", "真心", "JS类", "百合[搜]", "漫画类[画]", 
         "XYQHike", "php", "音乐", "天微", "南风", "OK杰克", "xbpq", 
          "scripts", "db", "bt", "py", "jar"
    ]
#①    
    # ==========================================================================

    def __init__(self):
        self.inited = False
        self.cache = {"categories": [], "file_index": {}}
        # 🛡️ 档位初始化
        self.config = self._get_adaptive_config()
        # 🏷️ 【新增】：将内存档位转换为中文标签，方便显示在简介里
        level_map = {"Eco": "低功耗(省电)", "Balance": "平衡模式", "Turbo": "极速模式"}
        self.running_mode = level_map.get(self.config['tag'], "通用模式")
        
        self.JSON_ICON = "https://img.icons8.com/color/200/json--v1.png"
    # ==========================================================================

        # 🚫 [门阀 A：路径/文件名硬拦截] - 统一黑名单
        # 只要路径 or 文件名里包含这些词，直接从物理层面无视该文件
        self.BLACK_LIST = [
            "实验影视", "教程", "drpy2.min",  "cj.txt", "py64.txt", "py32.txt", "aa.json",
             "FongMi.json", "本地仓.txt", "说明文档.txt", "使用须知txt", "youtube.txt",
               "cj"
        ]
    
        # 🚫 [门阀 B：深度内容指纹拦截] - 针对文件内部文本
        # 无论是 JSON、TXT 还是 M3U，只要内容里扫描到这些，直接拒之门外
        self.BLACK_FINGERPRINTS = [
            "serv00", "termux", "readme", "192.168.", "static IP", "logo", "User-Agent",
            "压缩包", "解压", "说明", "使用方法", "扫码", "规则名", "数据列表", "请求头参数", 
            '{"urls"', "clan://", '{"rule"', '{"sites"', '{"key"' , "key" ,"Jsoup", "spider", "houzhui", 
            "主題", "筛选"
            # 🎯 上面.拦截JSON配置类文件
        ]
    # ==========================================================================

    def getName(self):
        return f"LocalTitan_v223_Precision_{self.config['tag']}"

    def _format_size(self, size_bytes):
        if size_bytes < 1024: return f"{int(size_bytes)}B"
        if size_bytes < 1048576: return f"{int(size_bytes/1024)}K"  
        return f"{size_bytes/1048576:.1f}M"

    def _get_adaptive_config(self):
        total_kb = 2048 * 1024 
        try:
            if os.path.exists('/proc/meminfo'):
                with open('/proc/meminfo', 'r') as f:
                    m = re.search(r'MemTotal:\s+(\d+)', f.read())
                    if m: total_kb = int(m.group(1))
        except: pass
        if total_kb <= 1572864: return {"limit": 500, "chunk": 1024 * 1024, "tag": "Eco"}
        elif total_kb <= 3145728: return {"limit": 1000, "chunk": 2 * 1024 * 1024, "tag": "Balance"}
        else: return {"limit": 2000, "chunk": 4 * 1024 * 1024, "tag": "Turbo"}
#② 
    # ==========================================================================
    # 📂 【2. 引擎初始化】 - 稳健扫描逻辑
    # ==========================================================================
    def _is_black_dir(self, name):
        name_low = name.lower()
        return any(word.lower() in name_low for word in self.DIR_BLACK_LIST) or \
               any(word.lower() in name_low for word in self.BLACK_LIST)

    def _is_illegal_source(self, path, head):
        # 针对 JSON 的合法性简单检查
        return any(bf in head for bf in self.BLACK_FINGERPRINTS)

    def init(self, extend=""):
        if self.inited: return
        gc.disable() 
        
        internal_paths = ["/storage/emulated/0", "/sdcard"]
        scan_tasks = []
        seen_real_paths = set()
        
        for ip in internal_paths:
            if os.path.exists(ip):
                real_p = os.path.realpath(ip)
                if real_p not in seen_real_paths:
                    scan_tasks.append({"root": ip, "is_ext": False})
                    seen_real_paths.add(real_p)

        try:
            if os.path.exists("/storage"):
                for folder in os.listdir("/storage"):
                    if folder not in ["emulated", "self", "knox", "sdcard0", "runtime"]:
                        ext_path = os.path.join("/storage", folder)
                        if os.path.isdir(ext_path):
                            real_p = os.path.realpath(ext_path)
                            if real_p not in seen_real_paths:
                                scan_tasks.append({"root": ext_path, "is_ext": True})
                                seen_real_paths.add(real_p)
        except: pass
        if extend: scan_tasks.insert(0, {"root": extend.strip(), "is_ext": True})

        all_raw_cats, final_index, unique_paths = [], {}, set()
        sort_w = {"JSON": 1, "M3U": 2, "TXT": 3, "MEDIA": 4}
        folder_groups = {} 
        p_size = self.CHANNEL_PAGE_SIZE if self.CHANNEL_PAGE_SIZE > 0 else 1000

        for task in scan_tasks:
            for target_dir in self.SCAN_DIR_LIST:
                if self._is_black_dir(target_dir): continue
                bh_p = os.path.join(task['root'], target_dir)
                if not os.path.isdir(bh_p): continue
                star = "☆" if task['is_ext'] else "" 
                
                # 优先级排序逻辑
                zone_weight = 0
                if target_dir == "lz": zone_weight = 1
                elif target_dir == "江湖": zone_weight = 2
                
                for root, dirs, files in os.walk(bh_p):
                    full_root_low = root.lower()
                    if any(word.lower() in full_root_low for word in ['android', 'data', '.thumbnails']):
                        dirs[:] = []
                        continue

                    dirs[:] = [d for d in dirs if not self._is_black_dir(d)]

                    temp_valid_list = []
                    for f in files:
                        if self._is_black_dir(f): continue
                        f_path = os.path.join(root, f)
                        f_low = f.lower()

                        if f_low.endswith('.json'):
                            try:
                                with open(f_path, 'r', encoding='utf-8', errors='ignore') as jf:
                                    head = jf.read(1024)
                                    if self._is_illegal_source(f_path, head): continue 
                                    temp_valid_list.append(f_path)
                            except: continue
                        elif f_low.endswith(('.m3u', '.m3u8', '.txt', '.mp4', '.mkv', '.avi', '.flv')):
                            temp_valid_list.append(f_path)

                    valid_files = temp_valid_list
                    if not valid_files: continue                    
                    real_root = os.path.realpath(root)
                    if real_root in unique_paths: continue
                    unique_paths.add(real_root)
                    
                    rel_name = os.path.relpath(root, bh_p)
                    folder_display = target_dir if rel_name == "." else f"{target_dir}/{rel_name.replace(os.sep, '/')}"

                    for suffix_type in [".json", ".m3u", ".txt", ".media"]:
                        if suffix_type == ".media":
                            sub_files = sorted([f for f in valid_files if f.lower().endswith(('.mp4', '.mkv', '.avi', '.flv'))])
                            c_tag = "MEDIA"
                        else:
                            sub_files = sorted([f for f in valid_files if f.lower().endswith(suffix_type) or (suffix_type == ".m3u" and f.lower().endswith(".m3u8"))])
                            c_tag = suffix_type[1:].upper().replace("M38", "M3U")
                        if not sub_files: continue

                        for f_path in sub_files:
                            try:
                                sz_raw = os.path.getsize(f_path)
                                is_ext_val = 1 if task['is_ext'] else 0
                                type_w = sort_w.get(c_tag, 99)
                                final_zone = zone_weight
                                if "json0" in f_path.lower(): type_w = 0; final_zone = -1 

                                if sz_raw >= 5 * 1048576: 
                                    f_base = os.path.basename(f_path).rsplit('.', 1)[0]
                                    u_key = f"📄[{c_tag}]{folder_display}/{f_base} ({self._format_size(sz_raw)}){star}"
                                    tid = base64.b64encode(f"SINGLE|{f_path}|{u_key}".encode()).decode()
                                    final_index[tid] = [f_path]
                                    all_raw_cats.append({"type_id": tid, "type_name": u_key, "sk": (final_zone, type_w, 1, sz_raw, is_ext_val, folder_display, 0)})
                                else: 
                                    group_key = f"📁[{c_tag}]{folder_display}"
                                    if group_key not in folder_groups: 
                                        folder_groups[group_key] = {"files": [], "total_size": 0, "star": star, "tag": c_tag, "sk_base": (final_zone, type_w, 0, is_ext_val, folder_display)}
                                    folder_groups[group_key]["files"].append(f_path)
                                    folder_groups[group_key]["total_size"] += sz_raw
                            except: continue

        for g_name, g_data in folder_groups.items():
            g_data["files"].sort()
            formatted_total = self._format_size(g_data["total_size"])
            final_t_name = f"{g_name} ({formatted_total}){g_data['star']}"
            tid = base64.b64encode(f"GROUP|{final_t_name}".encode()).decode()
            final_index[tid] = g_data["files"]
            all_raw_cats.append({"type_id": tid, "type_name": final_t_name, "sk": g_data["sk_base"] + (0,)})
        
        sorted_cats = sorted(all_raw_cats, key=lambda x: x['sk'])
        self.cache["categories"] = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in sorted_cats]
        self.cache["file_index"] = final_index
        self.inited = True
        gc.collect()
#④
        for g_name, g_data in folder_groups.items():
            g_data["files"].sort()
            g_files = g_data["files"]
            formatted_total = self._format_size(g_data["total_size"])
            g_star = g_data["star"]
            for i in range(0, len(g_files), p_size):
                chunk = g_files[i : i + p_size]
                page_num = (i // p_size) + 1
                suffix = f"[{page_num}]" if len(g_files) > p_size else ""
                # 💎 修正：文件夹组星号☆统一放在大小后面
                final_t_name = f"{g_name} ({formatted_total}){g_star}{suffix}"
                tid = base64.b64encode(f"GROUP|{final_t_name}".encode()).decode()
                final_index[tid] = chunk
                all_raw_cats.append({"type_id": tid, "type_name": final_t_name, "sk": g_data["sk_base"][:3] + (g_data["total_size"],) + g_data["sk_base"][3:] + (page_num,)})
        
        sorted_cats = sorted(all_raw_cats, key=lambda x: x['sk'])
        self.cache["categories"] = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in sorted_cats]
        self.cache["file_index"] = final_index
        self.inited = True
        gc.collect()

    def homeContent(self, filter):
        res = {"class": self.cache["categories"], "list": []}
        if self.cache["categories"]:
            for i in range(min(3, len(self.cache["categories"]))):
                tid = self.cache["categories"][i]["type_id"]
                res["list"].extend(self.categoryContent(tid, "1", False, {}).get("list", []))
        return res

    def categoryContent(self, tid, pg, filter, ext):
        page = int(pg) if pg.isdigit() else 1
        limit = self.config['limit']
        files = self.cache["file_index"].get(tid, [])
        all_channels = []
        for fp in files:
            f_low = fp.lower()
            f_tag = os.path.basename(fp).rsplit('.', 1)[0]
            if f_low.endswith(('.m3u', '.m3u8')): all_channels.extend(self._parse_m3u_stream(fp))
            elif f_low.endswith('.txt'): all_channels.extend(self._parse_txt_stream(fp))
            elif f_low.endswith(('.mp4', '.mkv', '.avi', '.flv')): all_channels.append(self._parse_media(fp))
            elif f_low.endswith('.json'):
                try:
                    with open(fp, "r", encoding="utf-8", errors='ignore') as f:
                        items = self._extract_items(json.load(f))
                        for it in items:
                            std = self._to_standard(it, f_tag, fp)
                            if std:
                                play_url = it.get("vod_play_url", it.get("url", ""))
                                if "#" in play_url and "$" in play_url and "$$$" not in play_url:
                                    parts = play_url.split("#")
                                    for p in parts:
                                        if "$" in p:
                                            p_name, p_url = p.split("$", 1)
                                            v_id = f"VIRT|{base64.b64encode(fp.encode()).decode()}|{base64.b64encode(p_url.encode()).decode()}|{base64.b64encode(p_name.encode()).decode()}"
                                            all_channels.append({
                                                "vod_id": v_id, "vod_name": p_name, 
                                                "vod_pic": "https://tutu1.space/images/2025/07/08/9bae40344904f8920f00a5926635f4b8.jpg",
                                                "vod_remarks": f"拆解-{f_tag}", "vod_play_from": "虚拟拆解"
                                            })
                                else:
                                    all_channels.append(std)
                except: continue
        total_count = len(all_channels)
        start_idx = (page - 1) * limit
        return {"page": page, "pagecount": (total_count + limit - 1) // limit, "limit": limit, "total": total_count, "list": all_channels[start_idx : start_idx + limit]}
#⑨
    def detailContent(self, array):
        if not array: return {"list": []}
        v_id_raw = str(array[0])
        try:
            parts = v_id_raw.split("|")
            prefix = parts[0]
            f_path = base64.b64decode(parts[1]).decode()
            f_name = os.path.basename(f_path)
            if prefix == "VIRT":
                real_url = base64.b64decode(parts[2]).decode()
                real_name = base64.b64decode(parts[3]).decode()
                return {"list": [{"vod_name": real_name, "vod_play_from": "json虚拟源", "vod_play_url": f"放大播放${real_url}", "vod_content": f"{real_name} | 【文件名】: {f_name}\n【路径】: {f_path}\n【档位】:{self.config['tag']}"}]}
            if prefix == "MEDIA_URL":
                v_name = base64.b64decode(parts[2]).decode() if len(parts) > 2 else f_name
                return {"list": [{"vod_id": v_id_raw, "vod_name": v_name, "vod_remarks": "本地媒体", "vod_play_from": "媒体", "vod_play_url": f"放大播放${f_path}", "vod_content": f"{v_name} | 【文件名】: {f_name}\n【路径】: {f_path}\n【档位】:{self.config['tag']}"}]}
            if prefix == "RAW": 
                real_url = base64.b64decode(parts[2]).decode()
                v_name = base64.b64decode(parts[3]).decode() if len(parts) > 3 else "直播频道"
                return {"list": [{"vod_id": v_id_raw, "vod_name": v_name, "vod_remarks": "本地源", "vod_play_from": "本地源", "vod_play_url": f"放大播放${real_url}", "vod_content": f"{v_name} | 【文件名】: {f_name}\n【路径】: {f_path}\n【链接】: {real_url}\n【档位】:{self.config['tag']}"}]}

            if prefix == "JS": 
                target_id = parts[2]
                with open(f_path, "r", encoding="utf-8") as f:
                    items = self._extract_items(json.load(f))
                    for it in items:
                        if str(it.get("vod_id", it.get("title", ""))) == target_id:
                            # 调用优化后的 standard 方法
                            std = self._to_standard(it, "JSON", f_path)
                            if std:
                                # 详情页播放地址必须包含“播放$”标记，否则播放器无法识别
                                urls = std["vod_play_url"].split("$$$")
                                std["vod_play_url"] = "$$$".join([f"播放${u}" for u in urls])
                                return {"list": [std]}
                                
        except: pass
        return {"list": []}

    def _extract_items(self, data):
        if isinstance(data, list): return data
        if not isinstance(data, dict): return []
        for key in ["vod", "videos", "list", "data", "items", "results", "objects"]:
            if key in data and isinstance(data[key], list): return data[key]
        for val in data.values():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict): return val
        return []
#⑩
    def _to_standard(self, item, file_tag, fp):
        if not isinstance(item, dict): return None
        url_raw = item.get("vod_play_url", item.get("play_url", item.get("url", "")))
        if not url_raw: return None
        name = item.get("vod_name", item.get("title", "未命名"))
#⑤
        # 🖼️ 【去反代核心】：自动截断图片前缀
        pic = item.get("vod_pic", item.get("cover", ""))
        if pic:
            pic_match = re.search(r'/(https?://|vip\.|dytt-|cdn\.|img\.)', pic)
            if pic_match:
                pic = pic[pic_match.start()+1:]
                if not pic.startswith("http"): pic = "https://" + pic
        if not pic or not pic.startswith("http"): pic = self.JSON_ICON

        # 🔗 【线路重组】：智能对齐 From 和 URL
        play_from_raw = item.get("vod_play_from", "本地JSON")
        url_groups = url_raw.split("$$$")
        from_parts = [p.strip() for p in play_from_raw.split("$$$") if p.strip()]
        while len(from_parts) < len(url_groups):
            from_parts.append(f"线路{len(from_parts)+1}")

        # 🎯 【m3u8 置顶】：让第一个按钮最有效
        if len(url_groups) > 1:
            m3u8_idx = next((i for i, g in enumerate(url_groups) if ".m3u8" in g.lower()), -1)
            if m3u8_idx > 0:
                url_groups[0], url_groups[m3u8_idx] = url_groups[m3u8_idx], url_groups[0]
        
        v_id = f"JS|{base64.b64encode(fp.encode()).decode()}|{str(item.get('vod_id', name))}"
        
        # 📝 【优化】：重新拼接简介内容
        # 获取原有简介，如果没有则显示“暂无详情”
        raw_content = item.get('vod_content', '暂无详情').strip()
        
        # 组合成新的简介：原简介 + 档位信息 + 物理路径
        new_content = (
            f"{raw_content}\n"           
            f"🚀 运行档位：{self.running_mode} (Limit:{self.config['limit']})\n"
            f"📂 文件路径：{fp}"
        )

        return {
            "vod_id": v_id, 
            "vod_name": name, 
            "vod_pic": pic, 
            "vod_remarks": item.get("vod_remarks", file_tag), 
            "vod_play_from": "$$$".join(from_parts), 
            "vod_play_url": "$$$".join(url_groups),
            "vod_content": new_content  # 👈 这里使用了缝合后的新简介
        }
#⑥
    def _parse_m3u_stream(self, file_path):
        items = []
        try:
            with open(file_path, 'rb') as f:
                temp_item = {}
                for line_bytes in f:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                    if line.startswith("#EXTINF:"):
                        logo_match = re.search(r'tvg-logo=["\'](.*?)["\']', line, re.I)
                        logo_url = logo_match.group(1) if logo_match else "https://img.icons8.com/color/200/tv.png"
                        name = line.split(',')[-1].strip()
                        temp_item = {"n": name, "pic": logo_url}
                    elif line.startswith("http"):
                        if temp_item:
                            v_id = f"RAW|{base64.b64encode(file_path.encode()).decode()}|{base64.b64encode(line.encode()).decode()}|{base64.b64encode(temp_item['n'].encode()).decode()}"
                            items.append({"vod_id": v_id, "vod_name": temp_item["n"], "vod_pic": temp_item["pic"], "vod_remarks": "M3U"})
                            temp_item = {}
        except: pass
        return items
#⑦
    def _parse_txt_stream(self, file_path):
        items = []
        try:
            with open(file_path, 'rb') as f:
                for line in f:
                    line = line.decode('utf-8', errors='ignore').strip()
                    if "," in line and "://" in line:
                        parts = line.split(',')
                        n, u = parts[0].strip(), parts[1].strip()
                        v_id = f"RAW|{base64.b64encode(file_path.encode()).decode()}|{base64.b64encode(u.encode()).decode()}|{base64.b64encode(n.encode()).decode()}"
                        items.append({"vod_id": v_id, "vod_name": n, "vod_pic": "https://img.icons8.com/color/200/txt.png", "vod_remarks": "TXT"})
        except: pass
        return items

    def _parse_media(self, fp):
        name = os.path.basename(fp)
        v_id = f"MEDIA_URL|{base64.b64encode(fp.encode()).decode()}|{base64.b64encode(name.encode()).decode()}"
        return {"vod_id": v_id, "vod_name": name, "vod_pic": "https://img.icons8.com/color/200/video-file.png", "vod_remarks": "MEDIA"}

    def playerContent(self, flag, id, vipFlags):
        # 1. 基础 URL 提取
        url = id.split('$')[-1] if '$' in id else id
        url = url.strip()

        # 🔪 【强效去反代】：识别多种特征词并强制截取
        # 解决类似于 down.nigx.cn/https://... 的问题
        match = re.search(r'/(https?://|vip\.|dytt-|cdn\.|img\.)', url)
        if match:
            url = url[match.start()+1:]
            if not url.startswith("http"):
                url = "https://" + url

        # 2. 伪装 UA 和 Referer 绕过防盗链
        domain_match = re.search(r'https?://[^/]+/', url)
        base_url = domain_match.group(0) if domain_match else url
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 okhttp/3.15.0",
            "Referer": base_url,
            "Origin": base_url.rstrip('/'),
            "Connection": "keep-alive"
        }
        
        return {"url": url, "header": headers, "parse": 0}
#⑧

    def destroy(self):
        gc.collect(); gc.enable(); return "destroy"
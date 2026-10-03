# -*- coding: utf-8 -*-
import os, json, time, gc, re, base64
from base.spider import Spider

class Spider(Spider):
    # ==========================================================================
    # 💎 【1. 核心导航配置区】
    # ==========================================================================
    # ⚙️ [门阀1.2：频道分页开关]：控制首页频道列表每页显示的条数
    CHANNEL_PAGE_SIZE = 1000  # 👈 修改这个数值，即可控制频道分页的大小 (默认1000条一页)
    
    # --------------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self.inited = False
        # 核心缓存系统：categories 存放分类频道，file_index 存放频道ID到物理文件的映射
        self.cache = {"categories": [], "file_index": {}}
        # 【关键部位：自适应配置加载】根据设备内存决定加载性能
        self.config = self._get_adaptive_config()
        # 【关键部位：调试日志保留】用于排查 JSON 文件解析异常
        self.debug_file = "/storage/emulated/0/json_reader_debug.txt"

    def getName(self):
        """ 返回插件名称及当前运行的性能档位标签 """
        return f"流式归类_v68_{self.config['tag']}"

    def _format_size(self, size_bytes):
        """ 工具：将字节数值转化为人类可读的 K/M 字符串，用于首页显示文件体积 """
        if size_bytes < 1024: return f"{int(size_bytes)}B"
        if size_bytes < 1048576: return f"{int(size_bytes/1024)}K"  
        return f"{size_bytes/1048576:.1f}M"

    def _debug(self, message):
        """ 故障排查日志记录函数 """
        try:
            with open(self.debug_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")
        except: pass

    def _get_adaptive_config(self):
        """ 【性能自适应系统】通过读取 /proc/meminfo 动态调整 limit（单页条数）和采样阈值 """
        total_kb = 2048 * 1024 
        try:
            if os.path.exists('/proc/meminfo'):
                with open('/proc/meminfo', 'r') as f:
                    m = re.search(r'MemTotal:\s+(\d+)', f.read())
                    if m: total_kb = int(m.group(1))
        except: pass
        # 🎯 分档逻辑：1.5G以下Eco，3G以下Balance，3G以上Turbo
        if total_kb <= 1572864: return {"limit": 500, "chunk": 1024 * 1024, "tag": "Eco"}
        elif total_kb <= 3145728: return {"limit": 1000, "chunk": 2 * 1024 * 1024, "tag": "Balance"}
        else: return {"limit": 2000, "chunk": 4 * 1024 * 1024, "tag": "Turbo"}

    # ==========================================================================
    # 🕵️ 【新版本万能适配核心逻辑 - 用于兼容各种异构 JSON 格式】
    # ==========================================================================
    def _extract_items(self, data):
        """ 【缝合点：万能列表提取器】自动寻找 JSON 中存放视频列表的键名（如 vod, videos, list 等） """
        if isinstance(data, list): return data
        if not isinstance(data, dict): return []
        # 优先级探测常用键名
        for key in ["vod", "videos", "list", "data", "items", "results"]:
            if key in data and isinstance(data[key], list): return data[key]
        # 自动扫描逻辑：寻找第一个非空且元素为字典的列表
        for val in data.values():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict): return val
        return []

    def _to_standard(self, item, file_tag, fp):
        """ 【缝合点：万能字段映射器】将不同 JSON 的字段统一映射为标准格式，并强制恢复纯净副标题 """
        if not isinstance(item, dict): return None
        # 1. 自动寻找播放链接键名
        url = item.get("vod_play_url", item.get("play_url", item.get("playUrl", item.get("url", ""))))
        if not url: return None
        # 2. 自动寻找标题键名
        name = item.get("vod_name", item.get("title", item.get("name", "未命名视频")))
        # 3. 提取 ID 并注入文件标记，方便详情页反查
        raw_id = str(item.get("vod_id", item.get("id", item.get("uuid", url))))
        v_id = f"JS|{base64.b64encode(fp.encode()).decode()}|{raw_id}"
        
        return {
            "vod_id": v_id,
            "vod_name": name,
            "vod_pic": item.get("vod_pic", item.get("cover", item.get("img", "https://img.icons8.com/color/200/json--v1.png"))),
            "vod_remarks": "JSON", # 🎯 【关键动作：恢复纯净副标题】
            "vod_play_from": "本地JSON",
            "vod_play_url": url,
            "vod_content": item.get("vod_content", item.get("description", item.get("desc", "暂无详情")))
        }

    def init(self, extend):
        """ 【核心扫描引擎】支持递归探测 bh 目录，支持大小文件分流，支持外置 U 盘星号标记 """
        if self.inited: return
        gc.disable() 
        # 1. 设置扫描任务：内部存储 + 自动探测 /storage 下的所有外置挂载点
        scan_tasks = [{"root": "/storage/emulated/0", "is_ext": False}]
        try:
            if os.path.exists("/storage"):
                for folder in os.listdir("/storage"):
                    if folder not in ["emulated", "self", "knox", "sdcard0", "runtime"]:
                        ext_path = os.path.join("/storage", folder)
                        if os.path.isdir(ext_path): scan_tasks.append({"root": ext_path, "is_ext": True})
        except: pass
        if extend: scan_tasks.insert(0, {"root": extend.strip(), "is_ext": True})

        all_raw_cats, final_index, unique_paths = [], {}, set()
        sort_w = {"JSON": 0, "M3U": 1, "TXT": 2, "MEDIA": 3}
        folder_groups = {} 

        # 🎯 获取分页开关数值
        p_size = self.CHANNEL_PAGE_SIZE if self.CHANNEL_PAGE_SIZE > 0 else 1000

        for task in scan_tasks:
            bh_p = os.path.join(task['root'], "bh")
            if not os.path.isdir(bh_p): continue
            
            # 🎯 【关键动作：补全外存星号标识】
            star = "☆" if task['is_ext'] else "" 
            
            for root, dirs, files in os.walk(bh_p):
                # 过滤并识别支持的文件格式
                valid_files = [os.path.join(root, f) for f in files if f.lower().endswith(('.json', '.m3u', '.m3u8', '.txt', '.mp4', '.mkv', '.avi', '.flv'))]
                if not valid_files: continue
                real_root = os.path.realpath(root)
                if real_root in unique_paths: continue
                unique_paths.add(real_root)
                
                # 计算相对路径，美化文件夹显示名称
                rel_name = os.path.relpath(root, bh_p)
                folder_display = "根目录" if rel_name == "." else rel_name.replace("/", " > ")

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
                            f_size_mb = sz_raw / 1048576
                            
                            # 🎯 【关键动作：恢复预估条数采样逻辑】
                            count = 0
                            if c_tag != "MEDIA":
                                try:
                                    with open(f_path, 'rb') as f_cnt:
                                        sample = f_cnt.read(1024*512)
                                        c_sample = sample.count(b'"play_url"') + sample.count(b'"vod_play_url"') + sample.count(b'://')
                                        count = int((c_sample / len(sample)) * sz_raw) if len(sample) > 0 else 0
                                        if count == 0 and sz_raw > 0: count = 1
                                except: count = 1
                            
                            f_info = f"({self._format_size(sz_raw)}|{count}条)" if c_tag != "MEDIA" else f"({self._format_size(sz_raw)})"
                            
                            # 🚀 策略：5M 以上大文件作为独立频道
                            if f_size_mb >= 5:
                                f_base = os.path.basename(f_path).rsplit('.', 1)[0]
                                u_key = f"【{c_tag}】{f_base} {f_info}{star}"
                                tid = base64.b64encode(f"SINGLE|{f_path}|{u_key}".encode()).decode()
                                final_index[tid] = [f_path]
                                all_raw_cats.append({"type_id": tid, "type_name": u_key, "sk": (1 if task['is_ext'] else 0, sort_w.get(c_tag, 9), folder_display, 0)})
                            # 🚀 策略：小文件按文件夹聚合展示
                            else:
                                group_key = f"【{c_tag}】📁{folder_display}{star}"
                                if group_key not in folder_groups: 
                                    folder_groups[group_key] = {"files": [], "sk_base": (1 if task['is_ext'] else 0, sort_w.get(c_tag, 9), folder_display)}
                                folder_groups[group_key]["files"].append(f_path)
                        except: continue

        # 处理文件夹聚合频道的分页（应用 CHANNEL_PAGE_SIZE 变量）
        for g_name, g_data in folder_groups.items():
            g_files = g_data["files"]
            # 🎯 此处应用门阀开关：控制文件夹内文件展示的分页
            for i in range(0, len(g_files), p_size):
                chunk = g_files[i : i + p_size]
                page_num = (i // p_size) + 1
                suffix = f"[{page_num}]" if len(g_files) > p_size else ""
                final_t_name = f"{g_name}{suffix}"
                tid = base64.b64encode(f"GROUP|{final_t_name}".encode()).decode()
                final_index[tid] = chunk
                all_raw_cats.append({"type_id": tid, "type_name": final_t_name, "sk": g_data["sk_base"] + (page_num,)})
        
        # 按照“内外置、格式权重、文件夹名、页码”进行全局排序
        sorted_cats = sorted(all_raw_cats, key=lambda x: x['sk'])
        self.cache["categories"] = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in sorted_cats]
        self.cache["file_index"] = final_index
        self.inited = True
        gc.collect()

    def _parse_media(self, fp):
        """ 解析本地视频文件，统一副标题为“本地媒体” """
        name = os.path.basename(fp)
        v_id = f"MEDIA_URL|{base64.b64encode(fp.encode()).decode()}|{base64.b64encode(name.encode()).decode()}"
        return {"vod_id": v_id, "vod_name": name, "vod_pic": "https://img.icons8.com/color/200/video-file.png", "vod_remarks": "本地媒体", "vod_play_from": "媒体", "vod_content": f"文件路径：{fp} | 档位:{self.config['tag']}"}

    def _parse_m3u_stream(self, file_path):
        """ 流式读取 M3U 直播源，统一副标题为“M3U” """
        items = []
        try:
            with open(file_path, 'rb') as f:
                temp_item = {}
                for line_bytes in f:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    if line.startswith("#EXTINF:"):
                        name = line.split(',')[-1].strip()
                        logo_match = re.search(r'tvg-logo=["\'](.*?)["\']', line)
                        temp_item = {"n": name, "l": logo_match.group(1) if logo_match else ""}
                    elif line.startswith("http"):
                        if temp_item:
                            v_id = f"RAW|{base64.b64encode(file_path.encode()).decode()}|{base64.b64encode(line.encode()).decode()}|{base64.b64encode(temp_item['n'].encode()).decode()}"
                            items.append({"vod_id": v_id, "vod_name": temp_item["n"], "vod_pic": temp_item["l"] if temp_item["l"].startswith('http') else "https://img.icons8.com/color/200/tv.png", "vod_remarks": "M3U", "vod_play_from": "M3U", "vod_content": f"⚡{temp_item['n']} | 路径:{file_path} | 档位:{self.config['tag']}"})
                            temp_item = {}
        except: pass
        return items

    def _parse_txt_stream(self, file_path):
        """ 解析 TXT 逗号直播源，统一副标题为“TXT” """
        items = []
        try:
            with open(file_path, 'rb') as f:
                for line_bytes in f:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                    if not line or "#genre#" in line or "," not in line: continue
                    parts = line.split(',')
                    if len(parts) >= 2 and "://" in parts[1]:
                        name, url = parts[0].strip(), parts[1].strip()
                        v_id = f"RAW|{base64.b64encode(file_path.encode()).decode()}|{base64.b64encode(url.encode()).decode()}|{base64.b64encode(name.encode()).decode()}"
                        pic = "https://img.icons8.com/color/200/txt.png"
                        remark = "网络mkv"
                        if url.lower().endswith(('.mkv', '.mp4')): pic = "https://img.icons8.com/color/200/video-file.png"
                        items.append({"vod_id": v_id, "vod_name": name, "vod_pic": pic, "vod_remarks": remark, "vod_play_from": "TXT", "vod_content": f"⚡{name} | 路径:{file_path} | 档位:{self.config['tag']}"})
        except: pass
        return items

    def homeContent(self, filter):
        """ 返回首页频道列表 """
        return {"class": self.cache["categories"]}

    def categoryContent(self, tid, pg, filter, ext):
        """ 【列表加载核心】调度不同格式的解析引擎，实现分页逻辑 """
        page = int(pg) if pg.isdigit() else 1
        limit = self.config['limit']
        files = self.cache["file_index"].get(tid, [])
        all_channels = []
        for fp in files:
            f_low = fp.lower()
            if f_low.endswith(('.m3u', '.m3u8')): all_channels.extend(self._parse_m3u_stream(fp))
            elif f_low.endswith('.txt'): all_channels.extend(self._parse_txt_stream(fp))
            elif f_low.endswith(('.mp4', '.mkv', '.avi', '.flv')): all_channels.append(self._parse_media(fp))
            elif f_low.endswith('.json'):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                        # 【缝合点：使用新版列表提取引擎】
                        items = self._extract_items(raw_data)
                        file_tag = os.path.basename(fp).replace('.json', '')
                        for it in items:
                            # 【缝合点：使用新版字段映射器】
                            std = self._to_standard(it, file_tag, fp)
                            if std:
                                std["vod_content"] = str(std["vod_content"]) + f" | 档位:{self.config['tag']}"
                                all_channels.append(std)
                except: continue
        total_count = len(all_channels)
        start_idx = (page - 1) * limit
        return {"page": page, "pagecount": (total_count + limit - 1) // limit, "limit": limit, "total": total_count, "list": all_channels[start_idx : start_idx + limit]}

    def detailContent(self, array):
        """ 【详情页反查引擎】通过 ID 中携带的信息回溯到物理文件，提取完整详情与播放链接 """
        if not array: return {"list": []}
        v_id_raw = str(array[0])
        try:
            parts = v_id_raw.split("|")
            prefix, f_path = parts[0], base64.b64decode(parts[1]).decode()
            f_name = os.path.basename(f_path)
            f_size = "未知"
            if os.path.exists(f_path): f_size = f"{os.path.getsize(f_path) / (1024*1024):.2f}MB"
            
            # 本地视频文件反查
            if prefix == "MEDIA_URL":
                m_name = base64.b64decode(parts[2]).decode() if len(parts) > 2 else f_name
                return {"list": [{"vod_id": v_id_raw, "vod_name": m_name, "vod_remarks": "本地媒体", "vod_play_from": "媒体", "vod_play_url": f"播放${f_path}", "type_name": "本地媒体", "vod_content": f"【片名】：{f_name} | 【路径】：{f_path} | 档位:{self.config['tag']}"}]}
            # M3U/TXT 直播源反查
            if prefix == "RAW": 
                real_url = base64.b64decode(parts[2]).decode()
                v_name = base64.b64decode(parts[3]).decode() if len(parts) > 3 else "未知频道"
                return {"list": [{"vod_id": v_id_raw, "vod_name": v_name, "vod_remarks": "TXT" if f_path.endswith('.txt') else "M3U", "vod_play_from": "本地直播源", "vod_play_url": f"全屏播放${real_url}", "type_name": "直播源", "vod_content": f"【片名】: {v_name}  【路径】: {f_path} | 【链接】：{real_url} | 【来源】：{f_name} | 档位:{self.config['tag']}\n"}]}
            # JSON 文件反查（使用新版回溯逻辑）
            elif prefix == "JS": 
                target_id = parts[2]
                if not os.path.exists(f_path): return {"list": []}
                with open(f_path, "r", encoding="utf-8") as f:
                    # 【缝合点：详情页同样使用万能提取引擎】
                    items = self._extract_items(json.load(f))
                    file_tag = os.path.basename(f_path).replace('.json', '')
                    for p_idx, it in enumerate(items):
                        curr_id = str(it.get("vod_id", it.get("id", it.get("uuid", ""))))
                        if curr_id == target_id:
                            std = self._to_standard(it, file_tag, f_path)
                            if std:
                                std["vod_remarks"] = "JSON" # 🎯 详情页再次确认副标题纯净
                                std["vod_play_url"] = f"立即播放${std['vod_play_url']}"
                                std["vod_content"] = f"{std['vod_name']}\n⚡总量:{f_size} | 本段:{p_idx+1}集 | 路径:{f_path} | 档位:{self.config['tag']}"
                                return {"list": [std]}
        except Exception as e: self._debug(f"详情解析失败: {e}")
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        """ 播放器最终入口：清洗 $ 符号后的播放链接 """
        url = id.split('$')[-1] if '$' in id else id
        return {"url": url.strip(), "header": {"User-Agent": "okhttp/3.12.0"}, "parse": 0}

    def destroy(self):
        """ 插件退出时强制回收内存 """
        gc.collect(); gc.enable(); return "destroy"
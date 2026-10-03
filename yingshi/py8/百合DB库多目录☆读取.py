import sys
import sqlite3
import json
import os
import base64
import re  # 保留基础正则模块，用于自然排序与分片路由逻辑
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "Universal_DB_Spider"

    # ==========================================================================   
    # 💎 【1. 配置与物理路径】 db数据库 路径自适应
    # ==========================================================================
    SCAN_DIR_LIST = [
                "bh", "tvbox",  "bhh",         #👈电视📺专用文件夹，把db文件放在这里# 👈 u盘也用这个文件夹                                          
                "lz", "纯福利", "私藏视频",  "江湖",          # 👈 前面加#关闭   这里可以修改任意大佬包名 
                "VodPlus", "peekpili/php-scripts"                       #同上
          ]   
   
    MIN_DB_SIZE = 0.5 * 1024 * 1024   # 门限小于0.5M不显示
    FP_LOGO = "https://img.icons8.com/color/200/video-file.png"
    DB_LOGO = "https://img.icons8.com/color/96/opened-folder.png"
    
    def init(self, extend=""):
        self.inited = True
        self.databases = {}
        self.scan_roots = ["/storage/emulated/0"]
        # 🚀 建立运行时高频查询轻量动态缓冲区，防止全量清单读取时重复摩擦硬盘
        self._query_cache = {}
        
        # 增强型多挂载点路径扫描 源文件可放在SD卡和U盘
        try:
            if os.path.exists("/storage"):
                for s in os.listdir("/storage"):
                    if s not in ["self", "emulated", "knox", "sdcard0", "runtime"]:
                        full_s = os.path.join("/storage", s)
                        if os.path.isdir(full_s):
                            self.scan_roots.append(full_s)
        except: pass
        self._differential_scan()

    def _format_size(self, sz):
        if sz >= 1024**3: return f"{sz/1024**3:.1f}G"
        if sz >= 1024**2: return f"{sz/1024**2:.1f}M"
        return f"{sz/1024:.1f}K"

    def _differential_scan(self):
        temp_list = []
        for root_p in self.scan_roots:
            is_ext = not root_p.startswith("/storage/emulated/0")
            star = "☆" if is_ext else ""
            for target in self.SCAN_DIR_LIST:
                base_p = os.path.join(root_p, target)
                if not os.path.isdir(base_p): continue
                for root, dirs, files in os.walk(base_p):
                    for file in files:
                        if not file.lower().endswith(".db"): continue
                        f_path = os.path.join(root, file)
                        try:
                            sz_raw = os.path.getsize(f_path)
                            if sz_raw < self.MIN_DB_SIZE: continue
                            
                            # 📺 物理路径层级显示逻辑
                            rel_path = f_path.replace("/storage/emulated/0/", "").replace(root_p, "")
                            display_name = f"{os.path.basename(f_path)}({self._format_size(sz_raw)}){star}"                            

                            db_key = base64.b64encode(f_path.encode()).decode()
                            temp_list.append({
                                "key": db_key, "name": display_name, "path": f_path,
                                "is_ext": is_ext, "size_bytes": sz_raw
                            })
                        except: continue
        temp_list.sort(key=lambda x: (x["is_ext"], x["size_bytes"]))
  
        for item in temp_list:
            self.databases[item["key"]] = {
                "name": item["name"], 
                "path": item["path"], 
                "size_str": self._format_size(item["size_bytes"]),
                "valid": 1
            }

    # ==========================================================================
    # ⚡ 【硬件级加速调优连接池】
    # ==========================================================================
    def _get_connection(self, db_path):
        if not db_path or not os.path.exists(db_path): return None
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # 🚀🔴 [核心提速补丁] 通过 PRAGMA 指令直接下达硬件级内存加速
            cursor = conn.cursor()
            cursor.execute("PRAGMA cache_size = -8000;")       # 强制分配约8MB的纯内存高速页缓存
            cursor.execute("PRAGMA mmap_size = 268435456;")     # 开启内存映射（MMap），允许直读256MB数据内核
            cursor.execute("PRAGMA temp_store = MEMORY;")       # 强制将临时表、排序操作全部丢进内存运行
            cursor.execute("PRAGMA journal_mode = WAL;")        # 启用高性能预写日志模式，降低磁盘I/O阻塞
            cursor.execute("PRAGMA synchronous = OFF;")        # 解除严重的硬盘同步锁，提速全量扫描
            
            return conn
        except: return None

    # ==========================================================================
    # 🧠 【2. 核心智能探测系统 】
    # ==========================================================================
    def _get_auto_mapping(self, conn):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            priority_tables = ["videos", "vod_unified_data", "cj", "vod", "data", "video_detail"]
            target_table = next((t for t in priority_tables if t in tables), tables[0] if tables else None)
            if not target_table: return None
            
            cat_tables = ["categories", "type", "vod_type", "classes"]
            target_cat_table = next((t for t in cat_tables if t in tables), None)
            
            cursor.execute(f"PRAGMA table_info(`{target_table}`)")
            cols = [str(r[1]) for r in cursor.fetchall()]
            
            mapping = {}
            field_candidates = {
                "vod_id": ["id", "vod_id", "uuid", "aid", "rowid"],
                "vod_name": ["name", "vod_name", "title", "subject"],
                "vod_pic": ["image", "vod_pic", "pic", "thumbnail", "cover"],
                "vod_play_url": ["play_url", "vod_play_url", "url", "link"],
                "vod_remarks": ["remarks", "vod_remarks", "quality", "note"],
                "vod_content": ["content", "vod_content", "description", "summary"],
                "category_field": ["type_id", "category_id", "type_name", "class_id", "actress_id"]
            }
            
            for k, candidates in field_candidates.items():
                matches = [c for c in candidates if c in cols]
                if not matches:
                    mapping[k] = None
                    continue
                
                best_match = matches[0]
                max_score = -1
                for match in matches:
                    score = 0
                    cursor.execute(f'SELECT `{match}` FROM `{target_table}` WHERE `{match}` IS NOT NULL AND `{match}` != "" LIMIT 10')
                    results = cursor.fetchall()
                    if not results: continue
                    
                    if k == "category_field":
                        distinct_vals = set([str(r[0]) for r in results])
                        if len(distinct_vals) <= 1 and len(results) > 1: score -= 50
                        if target_cat_table: score += 30
                    
                    score += (20 if match == candidates[0] else 5)
                    if score > max_score:
                        max_score = score
                        best_match = match
                mapping[k] = best_match
            
            return {"table_name": target_table, "cat_table_name": target_cat_table, "field_mapping": mapping}
        except: return None

    # ==========================================================================
    # 📺 【3. 渲染逻辑 - 首页秒开】 屏蔽隐藏后缀.db
    # ==========================================================================
    def homeContent(self, filter):
        classes = []
        for key, info in self.databases.items():
            display_name = info["name"].replace(".db", "").replace(".DB", "")            
            classes.append({"type_id": key, "type_name": display_name})
            
        return {"class": classes}
        
    # ==========================================================================
    # ⚡ 【全量多层套娃路由探测过滤引擎】
    # ==========================================================================
    def categoryContent(self, tid, pg, filter, extend):
        parts = tid.split('$')
        db_key = parts[0]
        category_val = parts[1] if len(parts) > 1 else None
        
        # 🛡️ 多重路由物理路径解析守护
        db_path = None
        if db_key in self.databases:
            db_path = self.databases[db_key].get("path")
        if not db_path:
            try: db_path = base64.b64decode(db_key).decode() if len(db_key) > 32 else db_key
            except: db_path = db_key
        if db_path in self.databases:
            db_path = self.databases[db_path].get("path", db_path)

        conn = self._get_connection(db_path)
        if not conn: return {"list": []}
        
        auto = self._get_auto_mapping(conn)
        if not auto: 
            conn.close()
            return {"list": []}
        
        table, cat_table, m = auto["table_name"], auto["cat_table_name"], auto["field_mapping"]
        cursor = conn.cursor()
        vod_list = []

        # 🎯 【自然排序提取核心】：将文本切分为“文字”与“数字”，使数字按大小排序
        def _natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

        # 🚀🔴 【第一层：首次点击数据库，拉出全量一级大类】
        if category_val is None:
            has_valid_categories = False  # 🔓 建立分类检测锚点锁
            if m.get("category_field"):
                try:
                    sql_select_all = f"SELECT DISTINCT CAST(`{m['category_field']}` AS TEXT) FROM `{table}` WHERE `{m['category_field']}` IS NOT NULL AND `{m['category_field']}` != ''"
                    cursor.execute(sql_select_all)
                    rows = cursor.fetchall()
                    
                    unique_clean_check = set()
                    level1_set = set()
                    
                    for r in rows:
                        if not r[0]: continue
                        s_cat = str(r[0]).strip()
                        if not s_cat: continue
                        
                        unique_clean_check.add(s_cat.split("/")[0].strip() if '/' in s_cat else s_cat)
                        
                        l1_name = s_cat.split("/")[0].strip() if '/' in s_cat else s_cat
                        if l1_name: 
                            level1_set.add(l1_name)
                  
                    # 🔓 分类直出锁激活：只要盘点出不同的类目数大于1，直接判定为有分类文件
                    if len(unique_clean_check) > 1:
                        has_valid_categories = True
                    
                    if has_valid_categories and level1_set:
                        # 🚀🔴 通过自然排序算法排序
                        sorted_level1 = sorted(list(level1_set), key=_natural_sort_key)
                        for r_dir in sorted_level1:
                            safe_route = base64.b64encode(r_dir.encode('utf-8', 'ignore')).decode()
                            
                            # 💡 [针对数字名定向深度美化补丁]
                            final_show_name = r_dir
                            if final_show_name.isdigit():
                                final_show_name = f"第{int(final_show_name):02d}分类"

                            vod_list.append({
                                "vod_id": f"{db_key}$LEVEL1_{safe_route}",
                                "vod_name": final_show_name,  # 应用数字美化包装
                                "vod_pic": self.DB_LOGO,
                                "vod_tag": "folder",
                                "vod_remarks": "进入查看"
                            })
                except: pass

            # ⚙️ 虚拟分片兜底锁（只有当无有效分类名时，才会用来保底）
            if not has_valid_categories or not vod_list:
                vod_list = []
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    total = cursor.fetchone()[0]
                except: total = 0
                for i in range(0, total, 500):
                    end_idx = min(i + 500, total)
                    current_chunk_pg = (i // 500) + 1
                    vod_list.append({
                        "vod_id": f"{db_key}$CHUNK_{i}",
                        "vod_name": f"本页 第{i+1}-{end_idx}条", 
                        "vod_pic": self.FP_LOGO,
                        "vod_tag": "folder",
                        "vod_remarks": f"第{current_chunk_pg}页/共{total}条" 
                    })
            conn.close()
            return {"page": 1, "pagecount": 1, "limit": 999, "list": vod_list}
         
        # 🚀🔴 【第二层：点击一级文件夹 -> 渲染二级文件夹 OR 直接渲染视频列表】
        if category_val.startswith("LEVEL1_"):
            raw_b64 = category_val.replace("LEVEL1_", "").strip()
            try: target_level1 = base64.b64decode(raw_b64).decode('utf-8', 'ignore').strip()
            except: target_level1 = raw_b64
            
            try:
                sql_scan = f"SELECT DISTINCT CAST(`{m['category_field']}` AS TEXT) FROM `{table}` WHERE CAST(`{m['category_field']}` AS TEXT) LIKE ?"
                cursor.execute(sql_scan, (f"%{target_level1}%",))
                matched_rows = cursor.fetchall()
                
                sub_folders = set()
                has_pure_list = False
                
                for r in matched_rows:
                    if not r[0]: continue
                    s_cat = str(r[0]).strip()
                    if not s_cat: continue
                    
                    if '/' in s_cat:
                        parts_path = [p.strip() for p in s_cat.split('/') if p.strip()]
                        if target_level1 in parts_path:
                            idx = parts_path.index(target_level1)
                            if idx + 1 < len(parts_path):
                                sub_folders.add(parts_path[idx + 1])
                            else:
                                has_pure_list = True
                    else:
                        if s_cat == target_level1:
                            has_pure_list = True

                if sub_folders:
                    sorted_sub = sorted(list(sub_folders), key=_natural_sort_key)
                    for sub_f in sorted_sub:
                        combine_str = f"{target_level1}##SUB##{sub_f}"
                        safe_route = base64.b64encode(combine_str.encode('utf-8', 'ignore')).decode()
                        
                        # 💡 [针对二级子目录数字名定向深度美化补丁]
                        final_sub_name = sub_f
                        if final_sub_name.isdigit():
                            final_sub_name = f"第{int(final_sub_name):02d}分类"
                        
                        display_parent = f"第{int(target_level1):02d}栏" if target_level1.isdigit() else target_level1
                        vod_list.append({
                            "vod_id": f"{db_key}$LEVEL2_{safe_route}",
                            "vod_name": final_sub_name,  # 应用二级数字美化包装
                            "vod_pic": self.DB_LOGO,
                            "vod_tag": "folder",
                            "vod_remarks": f"[{display_parent}] 子栏目"
                        })
                    
                    conn.close()
                    return {"page": 1, "pagecount": 1, "limit": 999, "list": vod_list}
            except: pass

            limit = 60
            offset = (int(pg) - 1) * limit
            f_id, f_name = m.get("vod_id") or "rowid", m.get("vod_name") or "rowid"
            f_pic, f_rem = m.get("vod_pic") or "''", m.get("vod_remarks") or "''"
            f_cnt = m.get("vod_content") or "''"

            try:
                sql = f"""
                    SELECT {f_id}, {f_name}, {f_pic}, {f_rem}, {f_cnt} 
                    FROM `{table}` 
                    WHERE CAST(`{m['category_field']}` AS TEXT) LIKE ? 
                    ORDER BY rowid ASC LIMIT ? OFFSET ?
                """
                cursor.execute(sql, (f"%{target_level1}%", limit, offset))
                for row in cursor.fetchall():
                    vod_list.append({
                        "vod_id": f"{db_key}#ID#{row[0]}",
                        "vod_name": str(row[1]), 
                        "vod_pic": str(row[2]) if str(row[2]).startswith('http') else "",
                        "vod_remarks": str(row[3]) if row[3] else "视频",
                        "vod_content": str(row[4])
                    })
            except: pass
            finally: conn.close()
            return {"page": int(pg), "pagecount": int(pg)+1, "limit": limit, "list": vod_list}

        # 🚀🔴 【第三层：点击二级文件夹 -> 精准渲染最底层终极视频清单】
        if category_val.startswith("LEVEL2_"):
            raw_b64 = category_val.replace("LEVEL2_", "").strip()
            try: combine_de = base64.b64decode(raw_b64).decode('utf-8', 'ignore').strip()
            except: combine_de = raw_b64
            
            target_level1, _, target_level2 = combine_de.partition("##SUB##")
            
            limit = 60
            offset = (int(pg) - 1) * limit
            f_id, f_name = m.get("vod_id") or "rowid", m.get("vod_name") or "rowid"
            f_pic, f_rem = m.get("vod_pic") or "''", m.get("vod_remarks") or "''"
            f_cnt = m.get("vod_content") or "''"

            try:
                sql = f"""
                    SELECT {f_id}, {f_name}, {f_pic}, {f_rem}, {f_cnt} 
                    FROM `{table}` 
                    WHERE CAST(`{m['category_field']}` AS TEXT) LIKE ? 
                      AND CAST(`{m['category_field']}` AS TEXT) LIKE ?
                    ORDER BY rowid ASC LIMIT ? OFFSET ?
                """
                cursor.execute(sql, (f"%{target_level1}%", f"%{target_level2}%", limit, offset))
                for row in cursor.fetchall():
                    vod_list.append({
                        "vod_id": f"{db_key}#ID#{row[0]}",
                        "vod_name": str(row[1]), 
                        "vod_pic": str(row[2]) if str(row[2]).startswith('http') else "",
                        "vod_remarks": str(row[3]) if row[3] else "视频",
                        "vod_content": str(row[4])
                    })
            except: pass
            finally: conn.close()
            return {"page": int(pg), "pagecount": int(pg)+1, "limit": limit, "list": vod_list}

        # 🚀🔴 【第四层：无分类时的 Chunk 虚拟分片渲染】
        if category_val.startswith("CHUNK_"):
            limit = 60
            offset = (int(pg) - 1) * limit
            start_i = int(category_val.replace("CHUNK_", ""))
            f_id, f_name = m.get("vod_id") or "rowid", m.get("vod_name") or "rowid"
            f_pic, f_rem = m.get("vod_pic") or "''", m.get("vod_remarks") or "''"
            f_cnt = m.get("vod_content") or "''"
            try:
                sql = f"SELECT {f_id}, {f_name}, {f_pic}, {f_rem}, {f_cnt} FROM `{table}` ORDER BY rowid ASC LIMIT ? OFFSET ?"
                cursor.execute(sql, (limit, start_i + offset))
                for row in cursor.fetchall():
                    vod_list.append({
                        "vod_id": f"{db_key}#ID#{row[0]}",
                        "vod_name": str(row[1]), 
                        "vod_pic": str(row[2]) if str(row[2]).startswith('http') else "",
                        "vod_remarks": str(row[3]) if row[3] else "视频",
                        "vod_content": str(row[4])
                    })
            except: pass
            finally: conn.close()
            return {"page": int(pg), "pagecount": int(pg)+1, "limit": limit, "list": vod_list}

        conn.close()
        return {"list": []}

    def clean_vod_url(self, raw_url):
        if not raw_url or not isinstance(raw_url, str):
            return ""
        clean_url = raw_url.split("$")[-1].split("|")[0]
        for ext in [".m3u8", ".mp4", ".mkv", ".m4v"]:
            pos = clean_url.lower().find(ext)
            if pos != -1:
                clean_url = clean_url[:pos + len(ext)]
                break
        if "&" in clean_url and ".m3u" not in clean_url.lower():
             clean_url = clean_url.split("&")[0]
        return clean_url.strip()


    # ==========================================================================
    # 【4. 详情页渲染】 增量无损加速版
    # ==========================================================================
    def detailContent(self, ids):
        mid_full = ids[0]
        
        # 1. 外部网络直链绿色通道 - 瞬间秒开
        if mid_full.startswith("http"):
            return {
                "list": [{
                    "vod_id": mid_full, "vod_name": "网络视频预览", "vod_remarks": "直链播放",
                    "vod_content": f"📍 外部链接: {mid_full}", "vod_play_from": "直链", "vod_play_url": mid_full
                }]
            }

        # 2. 高频内存高阶缓存拦截 - 0毫秒返回
        if mid_full in self._query_cache:
            return {"list": [self._query_cache[mid_full]]}

        db_key, _, real_id = mid_full.partition("#ID#")
        try: db_path = base64.b64decode(db_key).decode('utf-8', 'ignore') if len(db_key) > 32 else db_key
        except: db_path = db_key
        
        db_info = self.databases.get(db_key, {})
        if not db_info and db_path in self.databases:
             db_info = self.databases[db_path]
        
        actual_path = db_info.get("path", db_path)
        conn = self._get_connection(actual_path)
        if not conn: return {"list": [{"vod_name": "数据库连接失败"}]}
        
        try:
            # 🚀🔴 [增量常驻加速锚点] 初始化映射与总数常驻内存，防止老硬件单次点击高频摩擦硬盘
            if not hasattr(self, '_table_meta_cache'):
                self._table_meta_cache = {}
            if not hasattr(self, '_db_total_cache'):
                self._db_total_cache = {}

            # 🧠 智能提取常驻映射，如果这一个db已经跑过一次探测，直接从内存拿，免去全表扫描跑分
            if actual_path in self._table_meta_cache:
                auto_info = self._table_meta_cache[actual_path]
            else:
                auto_info = self._get_auto_mapping(conn)
                if auto_info:
                    self._table_meta_cache[actual_path] = auto_info

            main_cfg = db_info.get("tables", {}).get("main", {})
            table_name = main_cfg.get("table_name") or auto_info["table_name"]
            mapping = main_cfg.get("field_mapping") or auto_info["field_mapping"]

            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            id_col = mapping.get("vod_id") or "rowid"
            
            # 执行核心主键/ROWID精确单行索引扫描
            cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{id_col}` = ?", (real_id,))
            row = cursor.fetchone()
            if not row: return {"list": []}

            def get_raw_field(m_key):
                col = mapping.get(m_key)
                if col and col in row.keys() and row[col] is not None:
                    return str(row[col]).strip()
                return ""

            raw_play_url = get_raw_field("vod_play_url").replace(r'\/', '/')
            
            final_from_list = []
            final_url_list = []
            
            sources = raw_play_url.split('$$$')
            for idx, s_content in enumerate(sources):
                s_strip = s_content.strip()
                if not s_strip or s_strip.lower() == 'no': continue
                
                episodes = s_strip.split('#')
                clean_episodes = []
                for ep in episodes:
                    if not ep.strip(): continue
                    if '$' in ep:
                        parts = ep.split('$')
                        e_name = parts[0].strip()
                        e_url = parts[1].strip()
                        # 对大批量剧集进行高阶快速清洗
                        if '%' in e_url or '\\' in e_url:
                            e_url = re.sub(r'[^a-zA-Z0-9\.\:\/\-\_\=\&\?\%\#]', '', e_url)
                        if e_url: clean_episodes.append(f"{e_name}${e_url}")
                    else:
                        found_url = re.search(r'https?://[a-zA-Z0-9\.\:\/\-\_\=\&\?\%\#]+', ep)
                        if found_url: clean_episodes.append(f"播放${found_url.group().strip()}")
                
                if clean_episodes:
                    final_from_list.append(f"线路{idx + 1}")
                    final_url_list.append("#".join(clean_episodes))

            # 📊 优化大表计数：同样增加内存常驻锁，单数据库只查一次全表总数，后续直接复用
            if actual_path in self._db_total_cache:
                db_total = self._db_total_cache[actual_path]
            else:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    db_total = cursor.fetchone()[0]
                    self._db_total_cache[actual_path] = db_total
                except: 
                    db_total = "N/A"

            vod = {
                "vod_id": mid_full, 
                "vod_name": get_raw_field("vod_name") or "未知",
                "vod_pic": get_raw_field("vod_pic"),
                "vod_actor": get_raw_field("vod_actor") or "主演暂无",
                "vod_director": get_raw_field("vod_director") or "导演暂无",
                "vod_remarks": get_raw_field("vod_remarks") or "详情",
                "vod_area": get_raw_field("vod_area") or "其他", 
                "vod_year": get_raw_field("vod_year") or "",
                "vod_content": f"【详情】: {get_raw_field('vod_content')}\n\n📊 库内数量: {db_total}\n📍 存储路径: {actual_path}",
                "vod_play_from": "$$$".join(final_from_list) if final_from_list else "无线路",
                "vod_play_url": "$$$".join(final_url_list) if final_url_list else "无链接"
            }
            if len(self._query_cache) > 30: self._query_cache.clear()
            self._query_cache[mid_full] = vod
            return {"list": [vod]}
        except: return {"list": [{"vod_name": "解析失败"}]}
        finally: conn.close()
                
    # ==================== 播放内容 ====================
    def playerContent(self, flag, id, vipFlags):
        # 1. 拦截清理：剔除不必要的轨道切片符号并做终极清洗
        playurl = id.split("|")[0]
        if hasattr(self, 'clean_vod_url'):
            playurl = self.clean_vod_url(playurl)

        # 2. 基础请求头配置
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; MIbox PRO Build/PI)"
        }

        # 3. 针对M3U8的动态防盗链逆向伪装
        if playurl.strip().lower().endswith('.m3u8'):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(playurl)
                referer = f"{parsed.scheme}://{parsed.netloc}/"
                headers["Referer"] = referer
            except:
                pass

        return {
            "parse": 0, 
            "url": playurl, 
            "header": headers
        }
        
# ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        search_list = []
        limit = 30  
        for db_key, db_info in self.databases.items():
            if db_info.get("valid") == 0: continue
            conn = self._get_connection(db_info.get("path"))
            if not conn: continue
            try:
                auto_info = self._get_auto_mapping(conn)
                if not auto_info: continue
                table_name = auto_info["table_name"]
                mapping = auto_info["field_mapping"]
                
                title_field = mapping.get("vod_name")
                if not title_field: continue

                cursor = conn.cursor()
                sql = f"SELECT {mapping.get('vod_id') or 'rowid'}, {title_field}, {mapping.get('vod_pic') or '---'}, {mapping.get('vod_remarks') or '---'} FROM `{table_name}` WHERE `{title_field}` LIKE ? LIMIT {limit}"
                cursor.execute(sql, (f"%{key}%",))
                
                clean_db_name = db_info.get('name', db_key).replace(".db", "").replace(".DB", "")
                for row in cursor.fetchall():
                    search_list.append({
                        "vod_id": f"{db_key}#ID#{row[0]}", "vod_name": f"[{clean_db_name}] {row[1]}", 
                        "vod_pic": str(row[2]) if str(row[2]).startswith('http') else "", "vod_remarks": str(row[3])
                    })
            except: pass
            finally: conn.close()
        return {"list": search_list, "page": pg}
# coding: utf-8
import json
import sqlite3
import sys
import os
import re
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append('..')
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    """智能本地数据库爬虫 - 自动适配数据库结构（支持超时跳过与并行扫描）"""

    def init(self, extend=""):
        """初始化"""
        self.db_folder = "/storage/emulated/0/lz/db"
        self.page_size = 20
        self.databases = []
        self.db_cache = {}
        
        # 单个数据库读取超时（秒），可通过extend参数覆盖
        self.db_read_timeout = 20
        # 总扫描超时（秒），超过此时间不再等待未完成的数据库扫描，直接返回已完成的
        self.total_scan_timeout = 60
        # 缓存有效期（秒），在此时间内重复调用scan_databases直接返回缓存
        self.cache_ttl = 60
        
        # ===== 可配置项：顶级分类列表的封面图片 =====
        self.default_category_pic = "https://www.252035.xyz/imgs?t=1335527662"
        # ===============================================================
        
        if extend and extend.strip():
            try:
                if "=" in extend:
                    pairs = extend.split(",")
                    for pair in pairs:
                        if "timeout" in pair:
                            val = pair.split("=")[1].strip()
                            self.db_read_timeout = float(val)
                        elif "total" in pair:
                            val = pair.split("=")[1].strip()
                            self.total_scan_timeout = float(val)
                        elif "cache_ttl" in pair:
                            val = pair.split("=")[1].strip()
                            self.cache_ttl = float(val)
                else:
                    self.db_read_timeout = float(extend)
            except:
                pass
        
        self.last_scan_time = 0
        self.cached_databases = None
        
        # ===== 优化1: 线程本地连接池，避免重复打开/关闭数据库 =====
        self._local = threading.local()
        
        print(f"数据库读取超时: {self.db_read_timeout}秒 | 总扫描超时: {self.total_scan_timeout}秒 | 缓存有效期: {self.cache_ttl}秒")

    def scan_databases(self, force=False, max_total_wait=None):
        """
        扫描文件夹中的所有数据库文件（带并行 + 总超时控制）
        :param force: 是否强制重新扫描（忽略缓存）
        :param max_total_wait: 最大总等待时间（秒），默认使用 self.total_scan_timeout
        :return: 数据库列表
        """
        now = time.time()
        if not force and self.cached_databases is not None and (now - self.last_scan_time) < self.cache_ttl:
            print(f"使用缓存数据库列表（{len(self.cached_databases)}个数据库）")
            return self.cached_databases
        
        if not os.path.exists(self.db_folder):
            print(f"数据库文件夹不存在: {self.db_folder}")
            self.cached_databases = []
            self.last_scan_time = now
            return []
        
        db_files = []
        for file_name in os.listdir(self.db_folder):
            if file_name.endswith('.db'):
                db_path = os.path.join(self.db_folder, file_name)
                db_name = file_name.replace('.db', '')
                db_files.append((db_name, db_path))
        
        if not db_files:
            print("未找到任何.db数据库文件")
            self.cached_databases = []
            self.last_scan_time = now
            return []
        
        print(f"开始并行扫描 {len(db_files)} 个数据库，单个超时={self.db_read_timeout}秒，总超时={max_total_wait or self.total_scan_timeout}秒")
        
        # ===== 优化2: 提高最大并发线程数，加快扫描速度 =====
        databases = []
        with ThreadPoolExecutor(max_workers=min(len(db_files), 10)) as executor:
            future_to_db = {}
            for db_name, db_path in db_files:
                # 直接提交 worker，不再使用多余的 _analyze_db_with_timeout
                future = executor.submit(self._analyze_db_worker, db_path, db_name)
                future_to_db[future] = (db_name, db_path)
            
            total_wait = max_total_wait if max_total_wait is not None else self.total_scan_timeout
            start_time = time.time()
            
            for future in as_completed(future_to_db, timeout=total_wait):
                elapsed = time.time() - start_time
                if elapsed >= total_wait:
                    print(f"总扫描超时（{total_wait}秒），剩余未完成的数据库将跳过")
                    break
                
                db_name, db_path = future_to_db[future]
                try:
                    # ===== 优化3: future 已完成，直接获取结果 =====
                    result = future.result()
                except Exception as e:
                    print(f"数据库 {db_name} 扫描异常: {e}")
                    result = None
                
                if result and result.get('has_video_table'):
                    video_count = result.get('video_count', 0)
                    databases.append({
                        'id': db_name,
                        'name': result.get('db_display_name', db_name),
                        'path': db_path,
                        'structure': result,
                        'video_count': video_count
                    })
                    print(f"✓ 数据库 [{db_name}] 加载成功: {result.get('db_display_name', db_name)} ({video_count}个视频)")
                elif result is None:
                    print(f"✗ 数据库 [{db_name}] 读取超时或失败，已跳过")
                else:
                    print(f"✗ 数据库 [{db_name}] 无视频表，已跳过")
        
        self.cached_databases = databases
        self.last_scan_time = time.time()
        print(f"扫描完成，共加载 {len(databases)} 个数据库（总耗时 {time.time()-start_time:.2f}秒）")
        return databases
    
    # ===== 优化4: 删除 _analyze_db_with_timeout 方法，逻辑合并至 worker =====
    def _analyze_db_worker(self, db_path, db_name):
        """实际执行数据库结构分析（在线程中运行，包含超时逻辑）"""
        conn = None
        try:
            conn = self.get_db_connection(db_path)
            if not conn:
                return None
            # 设置查询超时（SQLite 不支持查询超时，但可以设置 busy_timeout）
            conn.execute(f"PRAGMA busy_timeout = {int(self.db_read_timeout * 1000)}")
            return self.analyze_db_structure(conn, db_path)
        except Exception as e:
            print(f"分析数据库结构失败 {db_path}: {e}")
            return None
        # ===== 优化5: 不关闭连接，保持复用 =====
    
    def analyze_db_structure(self, conn, db_path):
        """分析数据库结构，自动识别视频表"""
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            video_table = None
            priority_tables = ['vod_unified_data', 'video', 'videos', 'movie', 'movies', 'vod', 'media']
            
            for pt in priority_tables:
                if pt in tables:
                    video_table = pt
                    break
            
            if not video_table:
                for table in tables:
                    cursor = conn.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    if any(f in columns for f in ['vod_name', 'name', 'title', 'video_name']):
                        video_table = table
                        break
            
            if not video_table:
                return None
            
            cursor = conn.execute(f"PRAGMA table_info({video_table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            field_mapping = self.smart_field_mapping(columns)
            
            cursor = conn.execute(f"SELECT COUNT(*) FROM {video_table}")
            video_count = cursor.fetchone()[0]
            
            category_field = field_mapping.get('type_name', 'type_name')
            category_mapping_table = self.find_category_mapping_table(conn, tables)
            
            categories = []
            category_is_id = False
            
            if category_mapping_table:
                category_is_id = True
                categories = self.get_categories_from_mapping_table(conn, video_table, category_field, category_mapping_table)
                if categories:
                    print(f"  从映射表获取到 {len(categories)} 个分类")
            
            if not categories and category_field in columns:
                categories = self.get_categories_from_video_table(conn, video_table, category_field)
                if categories:
                    print(f"  从视频表获取到 {len(categories)} 个分类")
            
            if not categories and video_count > 0:
                categories = [{
                    'id': 'all',
                    'name': '全部视频',
                    'count': video_count
                }]
                print(f"  创建默认分类: 全部视频 ({video_count}个)")
            
            db_display_name = os.path.basename(db_path).replace('.db', '')
            if 'db_info' in tables:
                try:
                    cursor = conn.execute("SELECT name FROM db_info LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        db_display_name = row[0]
                except:
                    pass
            
            return {
                'table_name': video_table,
                'columns': columns,
                'field_mapping': field_mapping,
                'video_count': video_count,
                'categories': categories,
                'category_field': category_field,
                'category_is_id': category_is_id,
                'category_mapping_table': category_mapping_table,
                'db_display_name': db_display_name,
                'has_video_table': True
            }
            
        except Exception as e:
            print(f"分析数据库结构失败: {e}")
            return None
    
    def find_category_mapping_table(self, conn, tables):
        """查找分类映射表"""
        mapping_table_names = ['category', 'categories', 'type', 'types', 'cate', 'cates', 'class', 'classes']
        
        for table in tables:
            table_lower = table.lower()
            for mt in mapping_table_names:
                if mt == table_lower or mt in table_lower:
                    try:
                        cursor = conn.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        columns_lower = [c.lower() for c in columns]
                        
                        has_id = any('id' in c or 'type_id' in c or 'cate_id' in c for c in columns_lower)
                        has_name = any('name' in c or 'type_name' in c or 'cate_name' in c for c in columns_lower)
                        
                        if has_id and has_name:
                            id_field = None
                            name_field = None
                            for col in columns:
                                col_lower = col.lower()
                                if col_lower == 'id' or col_lower == 'type_id' or col_lower == 'cate_id':
                                    id_field = col
                                elif col_lower == 'name' or col_lower == 'type_name' or col_lower == 'cate_name':
                                    name_field = col
                            
                            if not id_field:
                                for col in columns:
                                    if 'id' in col.lower():
                                        id_field = col
                                        break
                            if not name_field:
                                for col in columns:
                                    if 'name' in col.lower():
                                        name_field = col
                                        break
                            
                            if id_field and name_field:
                                print(f"  找到分类映射表: {table} (id: {id_field}, name: {name_field})")
                                return {
                                    'table': table,
                                    'id_field': id_field,
                                    'name_field': name_field
                                }
                    except:
                        pass
        return None
    
    def get_categories_from_mapping_table(self, conn, video_table, category_field, mapping_table):
        """从映射表获取分类列表"""
        categories = []
        try:
            cursor = conn.execute(f"""
                SELECT DISTINCT {category_field} 
                FROM {video_table} 
                WHERE {category_field} IS NOT NULL AND {category_field} != ''
            """)
            used_ids = [str(row[0]) for row in cursor.fetchall()]
            
            if not used_ids:
                return categories
            
            id_field = mapping_table['id_field']
            name_field = mapping_table['name_field']
            
            placeholders = ','.join(['?'] * len(used_ids))
            sql = f"""
                SELECT {id_field}, {name_field} 
                FROM {mapping_table['table']} 
                WHERE CAST({id_field} AS TEXT) IN ({placeholders})
                ORDER BY {name_field}
            """
            cursor = conn.execute(sql, used_ids)
            
            for row in cursor:
                cat_id = str(row[0])
                cat_name = str(row[1])
                count_cursor = conn.execute(
                    f"SELECT COUNT(*) FROM {video_table} WHERE {category_field} = ?",
                    [cat_id]
                )
                count = count_cursor.fetchone()[0]
                categories.append({
                    'id': cat_id,
                    'name': cat_name,
                    'count': count
                })
        except Exception as e:
            print(f"从映射表获取分类失败: {e}")
        return categories
    
    def get_categories_from_video_table(self, conn, video_table, category_field):
        """从视频表直接获取分类"""
        categories = []
        try:
            cursor = conn.execute(f"""
                SELECT {category_field}, COUNT(*) as cnt 
                FROM {video_table} 
                WHERE {category_field} IS NOT NULL AND {category_field} != ''
                GROUP BY {category_field}
                ORDER BY cnt DESC
            """)
            
            for row in cursor:
                cat_value = str(row[0])
                cat_count = row[1]
                categories.append({
                    'id': cat_value,
                    'name': cat_value,
                    'count': cat_count
                })
        except Exception as e:
            print(f"从视频表获取分类失败: {e}")
        return categories
    
    def smart_field_mapping(self, columns):
        """智能映射字段名称"""
        mapping = {}
        
        field_rules = {
            'vod_id': ['vod_id', 'id', 'video_id', 'vid', '_id'],
            'vod_name': ['vod_name', 'title', 'video_name', 'movie_name', 'media_name'],
            'vod_pic': ['vod_pic', 'pic', 'cover', 'image', 'thumbnail', 'poster', 'img'],
            'vod_play_url': ['vod_play_url','m3u8_url', 'play_url', 'video_url', 'vod_url', 'playurl', 'url'],
            'vod_play_from': ['vod_play_from', 'play_from', 'source_name', 'platform', 'source', 'from'],
            'vod_remarks': ['vod_remarks', 'remarks', 'remark', 'note', 'desc_short'],
            'vod_year': ['vod_year', 'year', 'release_year', 'pubdate'],
            'vod_area': ['vod_area', 'area', 'region', 'country'],
            'vod_actor': ['vod_actor', 'actor', 'actors', 'starring', 'cast'],
            'vod_director': ['vod_director', 'director', 'directors'],
            'vod_content': ['vod_content', 'content', 'description', 'intro', 'introduction', 'plot'],
            'type_name': ['type_name', 'type', 'category', 'cate', 'class', 'genre', 'kind']
        }
        
        for target_field, possible_names in field_rules.items():
            for col in columns:
                col_lower = col.lower()
                for pn in possible_names:
                    if pn == col_lower or (pn in col_lower and len(pn) > 3):
                        mapping[target_field] = col
                        break
                if target_field in mapping:
                    break
        
        if 'vod_name' not in mapping and columns:
            mapping['vod_name'] = columns[0]
        
        return mapping
    
    # ===== 优化6: 线程本地连接池，避免反复开关 =====
    def get_db_connection(self, db_path):
        """获取数据库连接（线程本地复用）"""
        if not hasattr(self._local, 'conn_pool'):
            self._local.conn_pool = {}
        conn = self._local.conn_pool.get(db_path)
        if conn is None:
            try:
                if not os.path.exists(db_path):
                    return None
                # 允许在同一线程内复用，不检查 same_thread
                conn = sqlite3.connect(db_path, timeout=self.db_read_timeout, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute(f"PRAGMA busy_timeout = {int(self.db_read_timeout * 1000)}")
                self._local.conn_pool[db_path] = conn
            except Exception as e:
                print(f"连接数据库失败 {db_path}: {e}")
                return None
        return conn

    def getName(self):
        return "📚 智能数据库"

    def homeContent(self, filter):
        """首页内容（使用缓存，快速返回）"""
        self.databases = self.scan_databases(force=False, max_total_wait=self.total_scan_timeout)
        
        types = []
        for db in self.databases:
            types.append({
                "type_id": f"db_{db['id']}",
                "type_name": f"{db['name']} ({db.get('video_count', 0)})"
            })
        
        if not types:
            types = [{"type_id": "db_empty", "type_name": "暂无数据库 (0)"}]
        
        return {"class": types, "filters": {}}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        pg = int(pg) if pg else 1
        limit = self.page_size
        offset = (pg - 1) * limit
        
        parts = tid.split("_sub_")
        
        if len(parts) == 2:
            db_id = parts[0].replace("db_", "")
            category_value = parts[1]
            return self.get_videos_by_category(db_id, category_value, pg, limit, offset)
        else:
            db_id = tid.replace("db_", "")
            
            db_info = None
            for db in self.databases:
                if db['id'] == db_id:
                    db_info = db
                    break
            
            if db_info:
                categories = db_info['structure'].get('categories', [])
                if len(categories) == 1:
                    category_value = categories[0]['id']
                    return self.get_videos_by_category(db_id, category_value, pg, limit, offset)
            
            return self.get_categories_list(db_id, pg, limit, offset)

    # ===== 优化7: 批量获取分类封面，解决 N+1 问题 =====
    def get_categories_list(self, db_id, pg, limit, offset):
        """获取数据库下的分类列表 - 已优化为批量获取封面"""
        db_info = None
        for db in self.databases:
            if db['id'] == db_id:
                db_info = db
                break
        
        if not db_info:
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        
        structure = db_info['structure']
        categories = structure.get('categories', [])
        
        if not categories:
            conn = self.get_db_connection(db_info['path'])
            if conn:
                categories = self.refresh_categories(conn, db_info)
                if categories:
                    structure['categories'] = categories
        
        if not categories:
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        
        # ===== 批量获取每个分类的首张图片 =====
        vod_pic_map = {}
        conn = self.get_db_connection(db_info['path'])
        if conn and categories:
            table_name = structure['table_name']
            category_field = structure.get('category_field')
            pic_field = structure['field_mapping'].get('vod_pic', 'vod_pic')
            
            # 获取每个分类的第一张图片（通过最小 rowid）
            if category_field:
                try:
                    sql = f"""
                        SELECT {category_field}, {pic_field}
                        FROM {table_name}
                        WHERE rowid IN (
                            SELECT MIN(rowid)
                            FROM {table_name}
                            WHERE {category_field} IS NOT NULL AND {category_field} != ''
                            GROUP BY {category_field}
                        )
                        AND {pic_field} IS NOT NULL AND {pic_field} != ''
                    """
                    cursor = conn.execute(sql)
                    for row in cursor:
                        cat_key = str(row[0])
                        if row[1] and str(row[1]).startswith('http'):
                            vod_pic_map[cat_key] = str(row[1])
                except Exception as e:
                    print(f"批量获取分类封面失败: {e}")
            
            # 补充 'all' 分类的封面
            if 'all' not in vod_pic_map:
                try:
                    all_pic = conn.execute(
                        f"SELECT {pic_field} FROM {table_name} WHERE {pic_field} IS NOT NULL AND {pic_field} != '' LIMIT 1"
                    ).fetchone()
                    if all_pic and all_pic[0] and str(all_pic[0]).startswith('http'):
                        vod_pic_map['all'] = str(all_pic[0])
                except:
                    pass
        
        start = (pg - 1) * limit
        end = start + limit
        page_categories = categories[start:end]
        
        category_list = []
        for cat in page_categories:
            cat_id = cat['id']
            cat_name = cat['name']
            cat_count = cat.get('count', 0)
            
            # 直接从批量查询的映射中获取封面
            vod_pic = vod_pic_map.get(cat_id, self.default_category_pic)
            
            # ===== 优化8: 不再调用 get_category_video_count，直接使用已有的 count =====
            if cat_count == 0:
                # 如果确实为0，从数据库总计数推算（极少情况），但保留原结构
                cat_count = cat.get('count', 0)
            
            category_list.append({
                "vod_id": f"db_{db_id}_sub_{cat_id}",
                "vod_name": cat_name,
                "vod_pic": vod_pic,
                "vod_remarks": f"{cat_count} 个视频",
                "vod_tag": "folder",
                "style": {"type": "rect", "ratio": 1.0}
            })

        total = len(categories)
        pagecount = (total + limit - 1) // limit if total > 0 else 1
        
        return {
            "list": category_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": limit,
            "total": total
        }

    
    def refresh_categories(self, conn, db_info):
        """刷新分类列表"""
        structure = db_info['structure']
        video_table = structure['table_name']
        category_field = structure.get('category_field')
        
        if not category_field:
            return []
        
        category_mapping_table = structure.get('category_mapping_table')
        if category_mapping_table:
            categories = self.get_categories_from_mapping_table(conn, video_table, category_field, category_mapping_table)
            if categories:
                return categories
        
        categories = self.get_categories_from_video_table(conn, video_table, category_field)
        return categories
    
    # ===== 优化9: 构建分类ID到名称的映射表，避免逐条查询 =====
    def _build_id_name_map(self, db_info, conn):
        """建立分类ID -> 分类名称的快速查找字典"""
        id_to_name = {}
        structure = db_info['structure']
        # 从已有的分类列表获取
        for cat in structure.get('categories', []):
            id_to_name[cat['id']] = cat['name']
        
        # 如果映射表存在，补全可能缺失的ID
        cat_map = structure.get('category_mapping_table')
        if cat_map:
            try:
                sql = f"SELECT {cat_map['id_field']}, {cat_map['name_field']} FROM {cat_map['table']}"
                for row in conn.execute(sql):
                    key = str(row[0])
                    if key not in id_to_name:
                        id_to_name[key] = str(row[1])
            except:
                pass
        return id_to_name
    
    def get_all_videos(self, db_info, pg, limit, offset):
        """获取所有视频（已优化分类名称映射）"""
        structure = db_info['structure']
        table_name = structure['table_name']
        field_mapping = structure['field_mapping']
        
        conn = self.get_db_connection(db_info['path'])
        if not conn:
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        
        try:
            # 预先建立分类名称映射
            id_to_name = self._build_id_name_map(db_info, conn) if structure.get('category_is_id') else {}
            
            sql = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
            cursor = conn.execute(sql, [limit, offset])
            
            count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            
            videos = []
            for row in cursor:
                video = self.map_video_data(row, field_mapping, db_info, conn, id_to_name)
                if video:
                    videos.append(video)
            
            count_row = count_cursor.fetchone()
            total = count_row[0] if count_row else 0
            pagecount = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
                "limit": limit,
                "total": total,
                "parse": 0,
                "jx": 0
            }
            
        except Exception as e:
            print(f"get_all_videos 错误: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        # ===== 优化10: 不再关闭连接 =====

    def get_videos_by_category(self, db_id, category_value, pg, limit, offset):
        """获取指定分类下的视频列表（已优化分类名称映射）"""
        db_info = None
        for db in self.databases:
            if db['id'] == db_id:
                db_info = db
                break
        
        if not db_info:
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        
        if category_value == 'all':
            return self.get_all_videos(db_info, pg, limit, offset)
        
        structure = db_info['structure']
        table_name = structure['table_name']
        field_mapping = structure['field_mapping']
        category_field = structure.get('category_field')
        
        if not category_field:
            return self.get_all_videos(db_info, pg, limit, offset)
        
        conn = self.get_db_connection(db_info['path'])
        if not conn:
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        
        try:
            # 预先建立分类名称映射
            id_to_name = self._build_id_name_map(db_info, conn) if structure.get('category_is_id') else {}
            
            sql = f"""
                SELECT * FROM {table_name}
                WHERE {category_field} = ?
                ORDER BY rowid
                LIMIT ? OFFSET ?
            """
            cursor = conn.execute(sql, [category_value, limit, offset])
            
            count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {category_field} = ?", [category_value])
            
            videos = []
            for row in cursor:
                video = self.map_video_data(row, field_mapping, db_info, conn, id_to_name)
                if video:
                    videos.append(video)
            
            count_row = count_cursor.fetchone()
            total = count_row[0] if count_row else 0
            pagecount = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
                "limit": limit,
                "total": total,
                "parse": 0,
                "jx": 0
            }
            
        except Exception as e:
            print(f"get_videos_by_category 错误: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": limit, "total": 0}
        # ===== 优化11: 不再关闭连接 =====
    
    def sort_sources_by_m3u8(self, play_from_str, play_url_str):
        """对播放来源进行排序，m3u8线路优先"""
        if not play_from_str or not play_url_str:
            return play_from_str, play_url_str
        
        if '#' in play_from_str:
            sources = play_from_str.split('#')
        elif '$$$' in play_from_str:
            sources = play_from_str.split('$$$')
        else:
            sources = [play_from_str]
        
        if '#' in play_url_str:
            urls = play_url_str.split('#')
        elif '$$$' in play_url_str:
            urls = play_url_str.split('$$$')
        else:
            urls = [play_url_str]
        
        min_len = min(len(sources), len(urls))
        sources = sources[:min_len]
        urls = urls[:min_len]
        
        pairs = []
        for i in range(min_len):
            is_m3u8 = False
            if '.m3u8' in urls[i].lower():
                is_m3u8 = True
            elif 'm3u8' in sources[i].lower() or 'hls' in sources[i].lower():
                is_m3u8 = True
            
            pairs.append({
                'source': sources[i].strip(),
                'url': urls[i].strip(),
                'is_m3u8': is_m3u8
            })
        
        m3u8_pairs = [p for p in pairs if p['is_m3u8']]
        other_pairs = [p for p in pairs if not p['is_m3u8']]
        sorted_pairs = m3u8_pairs + other_pairs
        
        if m3u8_pairs:
            print(f"线路排序: {len(m3u8_pairs)} 条m3u8线路已优先")
        
        new_sources = [p['source'] for p in sorted_pairs]
        new_urls = [p['url'] for p in sorted_pairs]
        
        return '#'.join(new_sources), '#'.join(new_urls)
    
    def parse_episodes(self, play_url_str):
        """解析多集数据，返回集数列表和对应的URL列表"""
        if not play_url_str:
            return [], []
        
        episode_names = []
        episode_urls = []
        
        if '#' in play_url_str and '$' in play_url_str:
            parts = play_url_str.split('#')
            for part in parts:
                if '$' in part:
                    name, url = part.split('$', 1)
                    episode_names.append(name.strip())
                    episode_urls.append(url.strip())
            if episode_names:
                print(f"解析到 {len(episode_names)} 集")
                return episode_names, episode_urls
        
        if '$$$' in play_url_str and '$' in play_url_str:
            parts = play_url_str.split('$$$')
            for part in parts:
                if '$' in part:
                    name, url = part.split('$', 1)
                    episode_names.append(name.strip())
                    episode_urls.append(url.strip())
            if episode_names:
                print(f"解析到 {len(episode_names)} 集")
                return episode_names, episode_urls
        
        return [], []
    
    def format_episodes(self, episode_names, episode_urls):
        """格式化多集数据为标准格式"""
        if not episode_names or not episode_urls:
            return ""
        parts = []
        for name, url in zip(episode_names, episode_urls):
            parts.append(f"{name}${url}")
        return '#'.join(parts)
    
    # ===== 优化12: map_video_data 支持 id_to_name 参数，避免重复查询 =====
    def map_video_data(self, row, field_mapping, db_info, conn=None, id_to_name=None):
        """将数据库行映射为视频数据格式（优化分类名查找）"""
        def get_field_value(field_name, default_value=''):
            mapped_field = field_mapping.get(field_name)
            if mapped_field and mapped_field in row.keys() and row[mapped_field] is not None:
                value = row[mapped_field]
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                return str(value)
            return default_value
        
        vod_id = get_field_value('vod_id')
        vod_name = get_field_value('vod_name')
        
        if not vod_name:
            return None
        
        if not vod_id:
            if 'rowid' in row.keys():
                vod_id = str(row['rowid'])
            else:
                vod_id = vod_name
        
        default_pic = "https://storage.7x24cc.com/storage-server/presigned/ss1/a6-online-fileupload/newMediaImage/103D11B_773_db2025121201_20251212200052607newMediaImage.png"
        vod_pic = get_field_value('vod_pic')
        if not vod_pic or vod_pic.strip() == '':
            vod_pic = default_pic
        
        vod_play_from_raw = get_field_value('vod_play_from')
        vod_play_url_raw = get_field_value('vod_play_url')
        
        vod_play_from, vod_play_url = self.sort_sources_by_m3u8(vod_play_from_raw, vod_play_url_raw)
        
        if not vod_play_from or vod_play_from.strip() == '':
            vod_play_from = "直接播放"
        
        vod_remarks = get_field_value('vod_remarks')
        vod_year = get_field_value('vod_year')
        vod_area = get_field_value('vod_area')
        vod_actor = get_field_value('vod_actor')
        vod_director = get_field_value('vod_director')
        vod_content = get_field_value('vod_content')
        
        type_name = get_field_value('type_name')
        # 使用预构建的映射表快速查找
        if id_to_name and (db_info['structure'].get('category_is_id', False) or (type_name and type_name.isdigit())):
            type_name = id_to_name.get(type_name, type_name)
        
        temp_id = f"db_video__{db_info['id']}__{vod_id}"
        
        if not vod_play_url or vod_play_url.strip() == '':
            vod_play_url = f"播放${temp_id}"
        
        return {
            "vod_id": temp_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_remarks": vod_remarks or vod_year or "",
            "vod_actor": vod_actor or "",
            "vod_director": vod_director or "",
            "type_name": type_name,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url,
            "vod_content": vod_content or "",
            "vod_year": vod_year,
            "vod_area": vod_area,
            "style": {"type": "rect", "ratio": 0.75}
        }

    def detailContent(self, ids):
        """详情内容"""
        if not ids:
            return {"list": []}
        
        vid = ids[0]
        parts = vid.split("__")
        
        if len(parts) >= 3 and parts[0] == "db_video":
            db_id = parts[1]
            original_id = parts[2]
            
            db_info = None
            for db in self.databases:
                if db['id'] == db_id:
                    db_info = db
                    break
            
            if db_info:
                return self.get_video_detail(db_info, original_id, vid)
        
        return {"list": []}
    
    def get_video_detail(self, db_info, original_id, vid):
        """获取视频详情"""
        structure = db_info['structure']
        table_name = structure['table_name']
        field_mapping = structure['field_mapping']
        
        id_field = field_mapping.get('vod_id')
        
        conn = self.get_db_connection(db_info['path'])
        if not conn:
            return {"list": []}
        
        try:
            if id_field:
                sql = f"SELECT * FROM {table_name} WHERE {id_field} = ?"
                params = [original_id]
            else:
                sql = f"SELECT *, rowid FROM {table_name} WHERE rowid = ? OR {field_mapping.get('vod_name', 'name')} = ?"
                params = [original_id, original_id]
            
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            
            if row:
                def get_field_value(field_name):
                    mapped_field = field_mapping.get(field_name)
                    if mapped_field and mapped_field in row.keys() and row[mapped_field] is not None:
                        value = row[mapped_field]
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        return str(value)
                    return ''
                
                vod_name = get_field_value('vod_name')
                vod_pic = get_field_value('vod_pic')
                vod_play_from_raw = get_field_value('vod_play_from')
                vod_play_url_raw = get_field_value('vod_play_url')
                vod_remarks = get_field_value('vod_remarks')
                vod_year = get_field_value('vod_year')
                vod_area = get_field_value('vod_area')
                vod_actor = get_field_value('vod_actor')
                vod_director = get_field_value('vod_director')
                vod_content = get_field_value('vod_content')
                type_name = get_field_value('type_name')
                
                if not vod_name:
                    return {"list": []}
                
                default_pic = "https://storage.7x24cc.com/storage-server/presigned/ss1/a6-online-fileupload/newMediaImage/103D11B_773_db2025121201_20251212200052607newMediaImage.png"
                if not vod_pic or vod_pic.strip() == '':
                    vod_pic = default_pic
                
                episode_names, episode_urls = self.parse_episodes(vod_play_url_raw)
                sorted_from, sorted_url = self.sort_sources_by_m3u8(vod_play_from_raw, vod_play_url_raw)
                
                if episode_names and len(episode_names) > 1:
                    if '$' in sorted_url and '#' in sorted_url:
                        vod_play_url = sorted_url
                    else:
                        vod_play_url = self.format_episodes(episode_names, episode_urls)
                    vod_play_from = sorted_from
                    print(f"✓ 多集视频: 共 {len(episode_names)} 集")
                else:
                    vod_play_from = sorted_from
                    vod_play_url = sorted_url
                
                if not vod_play_from or vod_play_from.strip() == '':
                    vod_play_from = "直接播放"
                
                temp_id = f"db_video__{db_info['id']}__{original_id}"
                
                video = {
                    "vod_id": temp_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks or vod_year or "",
                    "vod_actor": vod_actor or "",
                    "vod_director": vod_director or "",
                    "type_name": type_name,
                    "vod_play_from": vod_play_from,
                    "vod_play_url": vod_play_url,
                    "vod_content": vod_content or "",
                    "vod_year": vod_year,
                    "vod_area": vod_area,
                    "style": {"type": "rect", "ratio": 0.75}
                }
                
                return {"list": [video]}
            
        except Exception as e:
            print(f"detailContent error: {e}")
            import traceback
            traceback.print_exc()
        # ===== 优化13: 不再关闭连接 =====
        
        return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """搜索内容"""
        if not key:
            return {"list": []}
        
        pg = int(pg) if pg else 1
        limit = self.page_size
        offset = (pg - 1) * limit
        videos = []
        
        if not self.databases:
            self.databases = self.scan_databases()
        
        # ===== 优化14: 搜索时也使用 id_to_name 映射 =====
        for db_info in self.databases:
            structure = db_info['structure']
            table_name = structure['table_name']
            field_mapping = structure['field_mapping']
            
            name_field = field_mapping.get('vod_name', 'name')
            
            conn = self.get_db_connection(db_info['path'])
            if conn:
                try:
                    id_to_name = self._build_id_name_map(db_info, conn) if structure.get('category_is_id') else {}
                    sql = f"""
                        SELECT * FROM {table_name}
                        WHERE {name_field} LIKE ?
                        LIMIT ? OFFSET ?
                    """
                    cursor = conn.execute(sql, [f"%{key}%", limit, offset])
                    
                    for row in cursor:
                        video = self.map_video_data(row, field_mapping, db_info, conn, id_to_name)
                        if video:
                            videos.append(video)
                except Exception as e:
                    print(f"searchContent error in {db_info['name']}: {e}")
                # 不再关闭连接
        
        total = len(videos)
        pagecount = (total + limit - 1) // limit if total > 0 else 1
        
        return {
            "list": videos[:limit],
            "page": pg,
            "pagecount": pagecount,
            "limit": limit,
            "total": total
        }

    def playerContent(self, flag, id, vipFlags):
        """播放器内容"""
        if id.startswith("播放$"):
            id = id[3:]
        
        if id.startswith('http://') or id.startswith('https://'):
            return {"parse": 0, "url": id}
        
        parts = id.split("__")
        
        if len(parts) >= 3 and parts[0] == "db_video":
            db_id = parts[1]
            original_id = parts[2]
            
            db_info = None
            for db in self.databases:
                if db['id'] == db_id:
                    db_info = db
                    break
            
            if db_info:
                video_url = self.get_play_url_from_db(db_info, original_id, flag)
                if video_url:
                    return {"parse": 0, "url": video_url}
        
        return {"parse": 0, "url": ""}
    
    def get_play_url_from_db(self, db_info, original_id, episode_flag=None):
        """从数据库获取播放地址"""
        structure = db_info['structure']
        table_name = structure['table_name']
        field_mapping = structure['field_mapping']
        
        id_field = field_mapping.get('vod_id')
        play_url_field = field_mapping.get('vod_play_url', 'vod_play_url')
        
        conn = self.get_db_connection(db_info['path'])
        if conn:
            try:
                if id_field:
                    sql = f"SELECT {play_url_field} FROM {table_name} WHERE {id_field} = ?"
                    params = [original_id]
                else:
                    name_field = field_mapping.get('vod_name', 'name')
                    sql = f"SELECT {play_url_field} FROM {table_name} WHERE {name_field} = ?"
                    params = [original_id]
                
                cursor = conn.execute(sql, params)
                row = cursor.fetchone()
                
                if row and row[0]:
                    play_url = str(row[0])
                    
                    episode_names, episode_urls = self.parse_episodes(play_url)
                    
                    if episode_names and len(episode_names) > 1:
                        if episode_flag:
                            for i, name in enumerate(episode_names):
                                if episode_flag == name:
                                    return episode_urls[i]
                                clean_flag = episode_flag.replace('第', '').replace('集', '')
                                clean_name = name.replace('第', '').replace('集', '')
                                if clean_flag == clean_name:
                                    return episode_urls[i]
                                if episode_flag.isdigit() and clean_name == episode_flag:
                                    return episode_urls[i]
                                if episode_flag.isdigit() and clean_name == f"{int(episode_flag):02d}":
                                    return episode_urls[i]
                        return episode_urls[0]
                    
                    if play_url.startswith('http://') or play_url.startswith('https://'):
                        return play_url
                    
                    if '$' in play_url and '#' not in play_url:
                        _, url = play_url.split('$', 1)
                        return url
                    
                    return play_url
                    
            except Exception as e:
                print(f"获取播放地址失败: {e}")
            # 不再关闭连接
        
        return None

    def destroy(self):
        """销毁时清理"""
        self.databases = []
        self.db_cache = {}
        self.cached_databases = None
        # 线程本地连接池由系统自动回收，无需手动关闭
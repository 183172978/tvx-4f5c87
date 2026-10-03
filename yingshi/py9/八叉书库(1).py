# -*- coding: utf-8 -*-
# 八叉书库 - TVBox小说爬虫（精选+搜索修复版）
# 目标: https://bcshuku.com

import sys
import re
import json
import urllib.parse
import time
from base.spider import Spider
from bs4 import BeautifulSoup
import requests

class Spider(Spider):
    def getName(self):
        return "八叉书库"

    def init(self, extend=""):
        self.host = "https://bcshuku.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

        self.class_map = {
            "1": "长篇", "2": "综合", "3": "武侠",
            "4": "历史", "5": "都市", "6": "玄幻",
            "7": "女生", "8": "其他", "9": "现代",
        }

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _fetch(self, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[Fetch Error] {url} -> {e}")
            return ""

    def _post(self, url, data, headers=None, timeout=15):
        try:
            h = self.session.headers.copy()
            if headers:
                h.update(headers)
            resp = self.session.post(url, data=data, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[Post Error] {url} -> {e}")
            return ""

    def homeContent(self, filter=False):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.class_map.items()]
        return {"class": classes}

    # ==================== 精选：从首页提取推荐书籍（来自旧版） ====================
    def homeVideoContent(self):
        try:
            html = self._fetch(self.host)
            if not html:
                return {"list": []}
            books = self._extract_home_books(html)
            return {"list": books[:30]}
        except Exception as e:
            print(f"首页异常: {e}")
            return {"list": []}

    def _extract_home_books(self, html):
        """从首页提取推荐书籍 - 旧版逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        books = []
        seen = set()

        # 从 .de-cu 区域提取推荐书籍
        for item in soup.select(".de-cu .normal-image1"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            id_match = re.search(r"/novel(\d+)/", href)
            vod_id = id_match.group(1) if id_match else ""
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)

            title = a_tag.get("title", "")
            if not title:
                title_tag = item.find("h3")
                if title_tag:
                    title = title_tag.get_text(strip=True)

            img = item.find("img")
            pic = img.get("src", "") if img else ""
            pic = self._fix_url(pic)

            # 分类
            cate = ""
            cate_tag = item.select_one(".chuyen-muc")
            if cate_tag:
                cate = cate_tag.get_text(strip=True).replace("分类", "").strip()

            books.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": cate
            })

        # 从 .truyenhot_li_customcol 提取最近更新
        for li in soup.select(".truyenhot_li_customcol"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            id_match = re.search(r"/novel(\d+)/", href)
            vod_id = id_match.group(1) if id_match else ""
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)
            title = a_tag.get_text(strip=True)

            # 提取最新章节
            chap_tag = li.select_one(".update_chap a")
            chap = chap_tag.get_text(strip=True) if chap_tag else ""

            books.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": "",
                "vod_remarks": chap if chap else "更新"
            })

        return books

    def _parse_book_block(self, item):
        a_tag = item.find("a", href=True)
        if not a_tag:
            return None
        href = a_tag.get("href", "")
        id_match = re.search(r"/novel(\d+)/", href)
        vod_id = id_match.group(1) if id_match else ""
        if not vod_id:
            return None

        title = a_tag.get("title", "")
        if not title:
            title_tag = item.find("h3")
            if title_tag:
                title = title_tag.get_text(strip=True)

        img = item.find("img")
        pic = img.get("src", "") if img else ""
        pic = self._fix_url(pic)

        cate = ""
        cate_tag = item.select_one(".chuyen-muc")
        if cate_tag:
            cate = cate_tag.get_text(strip=True).replace("分类", "").strip()

        last_chapter = ""
        label = item.select_one(".label-primary a")
        if label:
            last_chapter = label.get_text(strip=True)

        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": f"{cate} | {last_chapter}" if last_chapter else cate
        }

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        if pg <= 1:
            url = f"{self.host}/booklist{tid}/"
        else:
            url = f"{self.host}/booklist{tid}/index_{pg}.html"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

        books = self._extract_category_books(html)
        pagecount = self._extract_pagecount(html)

        if pagecount <= 1 and len(books) >= 20:
            pagecount = pg + 1
        if pagecount < pg:
            pagecount = pg

        return {
            "list": books,
            "page": pg,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20
        }

    def _extract_category_books(self, html):
        """从分类页提取书籍列表"""
        soup = BeautifulSoup(html, "html.parser")
        books = []
        seen = set()

        for item in soup.select(".col-md-3.col-sm-6.col-xs-6.home-truyendecu"):
            book = self._parse_book_item(item)
            if book and book["vod_id"] not in seen:
                seen.add(book["vod_id"])
                books.append(book)

        if not books:
            for item in soup.select(".one-row .home-truyendecu"):
                book = self._parse_book_item(item)
                if book and book["vod_id"] not in seen:
                    seen.add(book["vod_id"])
                    books.append(book)

        if not books:
            for a in soup.find_all("a", href=re.compile(r"/novel\d+/")):
                href = a.get("href", "")
                id_match = re.search(r"/novel(\d+)/", href)
                vod_id = id_match.group(1) if id_match else ""
                if not vod_id or vod_id in seen:
                    continue
                seen.add(vod_id)
                title = a.get("title", "") or a.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                books.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_remarks": ""
                })

        return books

    def _parse_book_item(self, item):
        a_tag = item.find("a", href=True)
        if not a_tag:
            return None
        href = a_tag.get("href", "")
        id_match = re.search(r"/novel(\d+)/", href)
        vod_id = id_match.group(1) if id_match else ""
        if not vod_id:
            return None

        caption = item.select_one(".caption")
        if not caption:
            caption = item

        title = a_tag.get("title", "")
        if not title:
            title_tag = caption.find("h3") or caption.find("a")
            if title_tag:
                title = title_tag.get_text(strip=True)

        img = item.find("img")
        pic = img.get("src", "") if img else ""
        pic = self._fix_url(pic)

        cate = ""
        cate_tag = caption.select_one(".chuyen-muc")
        if cate_tag:
            cate = cate_tag.get_text(strip=True).replace("分类", "").strip()

        last_chapter = ""
        label = caption.select_one(".label-primary a")
        if label:
            last_chapter = label.get_text(strip=True)

        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": f"{cate} | {last_chapter}" if last_chapter else cate
        }

    def _extract_pagecount(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for span in soup.select(".page span, .pagination span, .pages span"):
            text = span.get_text(strip=True)
            if "/" in text:
                parts = text.split("/")
                if len(parts) == 2:
                    try:
                        return int(parts[1].strip())
                    except:
                        pass
        max_page = 1
        for a in soup.select(".page a, .pagination a, .pages a"):
            href = a.get("href", "")
            m = re.search(r"index_(\d+)\.html", href)
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_page:
                        max_page = num
                except:
                    pass
        return max_page

    # ==================== 无上限抓取所有章节 ====================
    def _get_total_pages(self, html):
        soup = BeautifulSoup(html, "html.parser")
        pagination = soup.select_one("#pagination")
        if not pagination:
            return 1

        max_page = 1
        for a in pagination.find_all("a"):
            href = a.get("href", "")
            m = re.search(r"[?&]p=(\d+)", href)
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_page:
                        max_page = num
                except:
                    pass
            if "Last" in a.get_text():
                m = re.search(r"[?&]p=(\d+)", href)
                if m:
                    try:
                        num = int(m.group(1))
                        if num > max_page:
                            max_page = num
                    except:
                        pass

        text = pagination.get_text()
        m = re.search(r"共\s*(\d+)\s*页", text)
        if m:
            try:
                max_page = int(m.group(1))
            except:
                pass

        return max_page if max_page >= 1 else 1

    def _extract_chapters_from_page(self, html):
        soup = BeautifulSoup(html, "html.parser")
        chapters = []

        list_chapter = soup.select_one("#list-chapter")
        if list_chapter:
            for a in list_chapter.select("ul.list-chapter li a"):
                href = a.get("href", "")
                name = a.get_text(strip=True)
                if not name:
                    name = href.split("/")[-1].replace(".html", "")
                if href:
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")
            return chapters

        for a in soup.select(".list-chapter li a"):
            href = a.get("href", "")
            name = a.get_text(strip=True)
            if href and name:
                if href.startswith("/"):
                    href = self._fix_url(href)
                chapters.append(f"{name}${href}")

        if not chapters:
            for a in soup.select("#chaplist .list-chapter li a"):
                href = a.get("href", "")
                name = a.get_text(strip=True)
                if href and name:
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")

        return chapters

    def _fetch_all_chapters(self, base_url):
        all_chapters = []
        seen = set()
        page_num = 1

        print(f"[八叉书库] 开始抓取章节，无上限...")

        while True:
            if page_num == 1:
                page_url = base_url
            else:
                page_url = f"{base_url}?p={page_num}"

            print(f"[八叉书库] 抓取第 {page_num} 页: {page_url}")
            html = self._fetch(page_url)

            if not html:
                print(f"[八叉书库] 第 {page_num} 页为空，停止抓取")
                break

            chapters = self._extract_chapters_from_page(html)

            if not chapters:
                print(f"[八叉书库] 第 {page_num} 页没有章节，停止抓取")
                break

            new_count = 0
            for ch in chapters:
                if ch not in seen:
                    seen.add(ch)
                    all_chapters.append(ch)
                    new_count += 1

            print(f"[八叉书库] 第 {page_num} 页获取 {len(chapters)} 章，新增 {new_count} 章，累计 {len(all_chapters)} 章")

            if new_count == 0 and len(chapters) > 0:
                print(f"[八叉书库] 已无新章节，停止抓取")
                break

            soup = BeautifulSoup(html, "html.parser")
            pagination = soup.select_one("#pagination")
            has_next = False

            if pagination:
                for a in pagination.find_all("a"):
                    text = a.get_text()
                    if "Next" in text or "下一页" in text or ">" in text:
                        has_next = True
                        break
                    if "Last" in text:
                        has_next = True
                        break

                max_page = self._get_total_pages(html)
                if page_num < max_page:
                    has_next = True

            if not has_next:
                print(f"[八叉书库] 没有下一页，停止抓取，共 {len(all_chapters)} 章")
                break

            page_num += 1
            time.sleep(0.3)

        print(f"[八叉书库] 抓取完成，共 {len(all_chapters)} 章")
        return all_chapters

    def detailContent(self, ids):
        vod_id = ids[0]
        base_url = f"{self.host}/novel{vod_id}/"
        html = self._fetch(base_url)

        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_tag = soup.select_one(".desc h3, .info-chitiet h3")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            title_match = re.search(r"<title>(.*?)</title>", html)
            if title_match:
                title = title_match.group(1).strip()

        pic = ""
        img_tag = soup.select_one(".book img, .books-detail-img img")
        if img_tag:
            pic = img_tag.get("src", "")
            pic = self._fix_url(pic)

        author = ""
        author_tag = soup.select_one('a[itemprop="author"]')
        if author_tag:
            author = author_tag.get_text(strip=True)

        intro = ""
        intro_tag = soup.select_one('div[itemprop="description"]')
        if intro_tag:
            intro = intro_tag.get_text(strip=True)

        cate = ""
        cate_tag = soup.select_one('a[itemprop="genre"]')
        if cate_tag:
            cate = cate_tag.get_text(strip=True)

        all_chapters = self._fetch_all_chapters(base_url)

        seen = set()
        unique_chapters = []
        for ch in all_chapters:
            if ch not in seen:
                seen.add(ch)
                unique_chapters.append(ch)

        play_url = "#".join(unique_chapters) if unique_chapters else f"第1章${self.host}/novel{vod_id}/chapter1.html"

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title or f"小说{vod_id}",
                "vod_pic": pic,
                "vod_content": intro,
                "vod_author": author,
                "vod_remarks": f"{cate} | 共{len(unique_chapters)}章",
                "vod_play_from": "八叉书库",
                "vod_play_url": play_url
            }]
        }

    # ==================== 正文获取 ====================
    def playerContent(self, flag, id, vipFlags=None):
        try:
            chapter_url = id if id.startswith("http") else self._fix_url(id)
            if not chapter_url:
                return self._error_result("无效的章节URL")

            html = self._fetch(chapter_url)
            if not html:
                return self._error_result("获取章节页面失败")

            json_match = re.search(r'{"url"\s*:\s*"[^"]+"\s*,\s*"mobile"\s*:\s*"\d+"\s*,\s*"isk"\s*:\s*"\d+"\s*,\s*"novel"\s*:\s*"\d+"\s*,\s*"chapter"\s*:\s*"\d+"}', html)
            if not json_match:
                return self._error_result("未找到章节配置")

            try:
                config = json.loads(json_match.group(0))
            except Exception as e:
                return self._error_result(f"解析配置失败: {e}")

            api_url = "https://bcshuku.com/conapi.php"
            data = {
                "url": config.get("url", ""),
                "mobile": config.get("mobile", "0"),
                "isk": config.get("isk", "0"),
                "novel": config.get("novel", ""),
                "chapter": config.get("chapter", "")
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; U; Android 10; zh-CN; MI 9 Build/QKQ1.190828.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/100.0.4896.58 Quark/10.5.1.1026 Mobile Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "x-requested-with": "XMLHttpRequest",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "origin": "https://www.bcshuku.com",
                "referer": chapter_url,
                "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
            }

            resp_text = self._post(api_url, data, headers=headers)
            if not resp_text:
                return self._error_result("获取正文失败")

            try:
                resp_json = json.loads(resp_text)
                content = resp_json.get("content", "")
                if not content:
                    return self._error_result("正文内容为空")
            except Exception as e:
                return self._error_result(f"解析正文失败: {e}")

            soup = BeautifulSoup(html, "html.parser")
            title = ""
            title_tag = soup.find("h1") or soup.find("h2") or soup.find("h3")
            if title_tag:
                title = title_tag.get_text(strip=True)
            if not title:
                title_match = re.search(r"<title>(.*?)</title>", html)
                if title_match:
                    title = title_match.group(1).strip().replace("八叉书库 - ", "")

            result_data = {
                "title": title or "章节",
                "content": content
            }
            return {
                "parse": 0,
                "playUrl": "",
                "url": f"novel://{json.dumps(result_data, ensure_ascii=False)}",
                "header": ""
            }

        except Exception as e:
            print(f"playerContent error: {e}")
            return self._error_result(f"获取正文异常: {str(e)}")

    def _error_result(self, msg):
        result_data = {"title": "加载失败", "content": msg}
        return {
            "parse": 0,
            "playUrl": "",
            "url": f"novel://{json.dumps(result_data, ensure_ascii=False)}",
            "header": ""
        }

    # ==================== 搜索修复 ====================
    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = urllib.parse.quote(key)

        search_url = f"{self.host}/e/search/index.php?keyboard={enc_key}&show=title,writer,byr&searchget=1"
        try:
            resp = self.session.get(search_url, timeout=15, allow_redirects=False)
            location = resp.headers.get("location", "")
            searchid_match = re.search(r"searchid=(\d+)", location)
            if not searchid_match:
                html = resp.text
                if html:
                    # 搜索结果可能在当前页面，用搜索专用解析
                    books = self._extract_search_books(html)
                    if books:
                        return {"list": books, "page": pg, "pagecount": 1, "limit": 20, "total": len(books)}
                return {"list": [], "page": pg, "pagecount": 1}
            searchid = searchid_match.group(1)
        except Exception as e:
            print(f"搜索请求失败: {e}")
            return {"list": [], "page": pg, "pagecount": 1}

        if pg <= 1:
            result_url = f"{self.host}/e/search/result/?searchid={searchid}"
        else:
            result_url = f"{self.host}/e/search/result/index.php?page={pg-1}&searchid={searchid}"

        html = self._fetch(result_url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1}

        # 使用搜索专用解析
        books = self._extract_search_books(html)
        pagecount = self._extract_pagecount(html)

        if pagecount <= 1 and len(books) >= 20:
            pagecount = pg + 1
        if pagecount < pg:
            pagecount = pg

        return {
            "list": books,
            "page": pg,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20
        }

    def _extract_search_books(self, html):
        """专门解析搜索结果的书籍列表（搜索页结构和分类页不同）"""
        soup = BeautifulSoup(html, "html.parser")
        books = []
        seen = set()

        # 搜索页结果通常放在 .one-row 下的 .home-truyendecu
        for item in soup.select(".one-row .home-truyendecu"):
            book = self._parse_search_item(item)
            if book and book["vod_id"] not in seen:
                seen.add(book["vod_id"])
                books.append(book)

        # 如果没有，尝试 .col-md-3.col-sm-6.col-xs-6.home-truyendecu
        if not books:
            for item in soup.select(".col-md-3.col-sm-6.col-xs-6.home-truyendecu"):
                book = self._parse_search_item(item)
                if book and book["vod_id"] not in seen:
                    seen.add(book["vod_id"])
                    books.append(book)

        # 再兜底：直接匹配 /novel数字/ 链接
        if not books:
            for a in soup.find_all("a", href=re.compile(r"/novel\d+/")):
                href = a.get("href", "")
                id_match = re.search(r"/novel(\d+)/", href)
                vod_id = id_match.group(1) if id_match else ""
                if not vod_id or vod_id in seen:
                    continue
                seen.add(vod_id)
                title = a.get("title", "") or a.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                # 过滤导航链接
                if title in ["首页", "分类", "排行", "原创", "最新", "更多+", "搜索"]:
                    continue
                books.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_remarks": "搜索结果"
                })

        return books

    def _parse_search_item(self, item):
        """解析搜索列表项"""
        a_tag = item.find("a", href=True)
        if not a_tag:
            return None
        href = a_tag.get("href", "")
        id_match = re.search(r"/novel(\d+)/", href)
        vod_id = id_match.group(1) if id_match else ""
        if not vod_id:
            return None

        # 从 .caption 或直接取
        caption = item.select_one(".caption")
        if not caption:
            caption = item

        title = a_tag.get("title", "")
        if not title:
            title_tag = caption.find("h3") or caption.find("a")
            if title_tag:
                title = title_tag.get_text(strip=True)

        # 封面
        img = item.find("img")
        pic = img.get("src", "") if img else ""
        pic = self._fix_url(pic)

        # 分类
        cate = ""
        cate_tag = caption.select_one(".chuyen-muc")
        if cate_tag:
            cate = cate_tag.get_text(strip=True).replace("分类", "").strip()

        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": cate
        }

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None
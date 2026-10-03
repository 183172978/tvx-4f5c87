import requests
from bs4 import BeautifulSoup
import re
import subprocess
import platform
import os
import sys

# ==================== 播放器配置 ====================
# 这里配置你的 PotPlayer 所在目录
POTPLAYER_DIR = r"E:\potplayer"


def get_potplayer_path():
    """自动在指定目录下寻找 PotPlayer 的可执行文件"""
    if platform.system() != "Windows":
        return "open -a IINA"  # Mac 默认使用 IINA

    paths_to_try = [
        os.path.join(POTPLAYER_DIR, "PotPlayer64.exe"),
        os.path.join(POTPLAYER_DIR, "PotPlayerMini64.exe"),
        os.path.join(POTPLAYER_DIR, "PotPlayer.exe"),
        os.path.join(POTPLAYER_DIR, "PotPlayerMini.exe"),
    ]
    for p in paths_to_try:
        if os.path.exists(p):
            return p
    return None


class HanxiaoquanPlayer:
    def __init__(self):
        self.base_url = 'https://www.jennyhow.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.base_url
        }
        self.target_categories = [
            "今日推荐", "最新韩剧", "韩国电影", "韩国综艺", "韩国动漫",
            "最新韩剧•月榜", "韩国电影•月榜", "韩国综艺•月榜", "韩国动漫•月榜"
        ]
        self.menu_data = {}  # 存放首页菜单数据
        self.player_exe = get_potplayer_path()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def fetch_html(self, url):
        """通用网络请求"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            print(f"[-] 网络请求失败: {e}")
            return None

    def load_index(self):
        """1. 爬取首页，加载所有分类和片单（轻量级，秒出）"""
        print("[*] 正在连接韩小圈服务器，获取最新片单...")
        html = self.fetch_html(self.base_url)
        if not html:
            sys.exit(1)

        soup = BeautifulSoup(html, 'lxml')
        titles = soup.find_all(class_='module-title')

        for title_tag in titles:
            category_name = title_tag.get_text(strip=True)
            if category_name not in self.target_categories: continue

            videos = []
            if "月榜" not in category_name:
                # 左侧图文卡片
                heading_div = title_tag.find_parent('div', class_='module-heading')
                list_div = heading_div.find_next_sibling('div', class_='module-list')
                if list_div:
                    for item in list_div.find_all('div', class_='module-item'):
                        a_tag = item.find('a', class_='module-item-title')
                        if a_tag:
                            name = a_tag.get_text(strip=True)
                            href = a_tag.get('href', '')
                            videos.append({"名称": name, "链接": self.base_url + href if href else ""})
            else:
                # 右侧月榜纯文字
                heading_div = title_tag.find_parent('div', class_='module-heading')
                list_div = heading_div.find_next_sibling('div', class_='module-side-list')
                if list_div:
                    for item in list_div.find_all('a', class_='text-list-item'):
                        name = item.get('title', '未知')
                        href = item.get('href', '')
                        videos.append({"名称": name, "链接": self.base_url + href if href else ""})

            if videos:
                self.menu_data[category_name] = videos

    def load_detail(self, detail_url):
        """2. 用户点进某部剧后，实时抓取详情页解析集数"""
        print("\n[*] 正在获取播放线路...")
        html = self.fetch_html(detail_url)
        if not html: return {}

        soup = BeautifulSoup(html, 'lxml')
        lines_data = {}

        # 寻找选项卡
        tabs_ul = soup.find('ul', class_='nav-tabs')
        if tabs_ul:
            for li in tabs_ul.find_all('li'):
                a_tag = li.find('a')
                if not a_tag: continue

                line_name = a_tag.get_text(strip=True)
                target_id = a_tag.get('href', '').replace('#', '')

                playlist_div = soup.find('div', id=target_id)
                if playlist_div:
                    episodes = []
                    for ep in playlist_div.find_all('a'):
                        ep_name = ep.get('title') or ep.get_text(strip=True)
                        ep_href = ep.get('href', '')
                        episodes.append({"剧集": ep_name, "链接": self.base_url + ep_href if ep_href else ""})
                    lines_data[line_name] = episodes
        return lines_data

    def get_m3u8(self, play_url):
        """3. 用户选择集数后，实时去播放页提取 m3u8 直链"""
        print("\n[*] 正在破解高速视频流直链...")
        html = self.fetch_html(play_url)
        if not html: return None

        # 使用正则提取 var now="..."; 里的内容，兼容单双引号
        match = re.search(r'var now=[\'"](.*?)[\'"];', html)
        if match:
            return match.group(1)
        return None

    def play_video(self, m3u8_url):
        """4. 唤起 PotPlayer"""
        print(f"[+] 获取直链成功！\n -> {m3u8_url}")
        print("\n🚀 正在呼叫本地播放器...")

        if platform.system() == "Windows":
            if not self.player_exe:
                print(f"[-] 未在 {POTPLAYER_DIR} 找到 PotPlayer！请检查路径配置！")
                print("你可以手动复制上面的链接，用任何播放器打开。")
                return

            try:
                # 隐藏控制台黑框调用 PotPlayer
                subprocess.Popen([self.player_exe, m3u8_url], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f"[-] 播放器启动失败: {e}")
        else:
            os.system(f'{self.player_exe} "{m3u8_url}"')

    def start(self):
        """主交互循环"""
        self.clear_screen()
        self.load_index()

        while True:
            self.clear_screen()
            print("=" * 45)
            print("      🍿 韩小圈 VIP免广专属点播器 🍿")
            print("=" * 45)

            categories = list(self.menu_data.keys())
            for i, cat in enumerate(categories):
                print(f"  [{i:02d}] {cat}")
            print("-" * 45)

            cat_idx = input("👉 请选择分类编号 (输入 q 退出): ")
            if cat_idx.lower() == 'q': break
            if not cat_idx.isdigit() or int(cat_idx) >= len(categories):
                input("[-] 输入有误，按回车重试...")
                continue

            selected_cat = categories[int(cat_idx)]
            videos = self.menu_data[selected_cat]

            # --- 选剧 ---
            self.clear_screen()
            print(f"=== 当前板块: {selected_cat} ===")
            for i, v in enumerate(videos):
                print(f"  [{i:02d}] {v['名称']}")

            vid_idx = input("\n👉 请选择影片编号 (输入 b 返回): ")
            if vid_idx.lower() == 'b': continue
            if not vid_idx.isdigit() or int(vid_idx) >= len(videos):
                input("[-] 输入有误，按回车重试...")
                continue

            selected_video = videos[int(vid_idx)]

            # --- 加载并选线路 ---
            lines = self.load_detail(selected_video['链接'])
            if not lines:
                input("[-] 抱歉，该影片暂无可播放的资源，按回车返回...")
                continue

            line_names = list(lines.keys())
            print("\n" + "-" * 30)
            for i, line in enumerate(line_names):
                print(f"  [{i}] {line} (共 {len(lines[line])} 集)")

            line_idx = input("\n👉 请选择线路编号 (默认0, b返回): ")
            if line_idx.lower() == 'b': continue
            line_idx = 0 if line_idx == "" else int(line_idx)
            if line_idx >= len(line_names): continue

            selected_line = line_names[line_idx]
            episodes = lines[selected_line]

            # --- 选集并播放 ---
            print("\n" + "-" * 30)
            for i, ep in enumerate(episodes):
                # 每排打印多个集数，看着更整齐
                print(f"[{i:02d}] {ep['剧集'][:8]:<8}", end="\t")
                if (i + 1) % 4 == 0: print()

            print()  # 换行
            ep_idx = input("\n👉 请输入要播放的集数编号 (默认0, b返回): ")
            if ep_idx.lower() == 'b': continue
            ep_idx = 0 if ep_idx == "" else int(ep_idx)
            if ep_idx >= len(episodes): continue

            selected_ep = episodes[ep_idx]

            # 获取 m3u8 并播放
            m3u8_url = self.get_m3u8(selected_ep['链接'])
            if m3u8_url:
                self.play_video(m3u8_url)
            else:
                print("[-] 提取视频流失败，可能是网站修改了规则。")

            input("\n[ 观影愉快！看完按回车键返回主菜单... ]")


if __name__ == '__main__':
    app = HanxiaoquanPlayer()
    app.start()
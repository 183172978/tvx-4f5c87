# coding=utf-8
"""
全球广播 - 分类精选电台爬虫
数据来自全球广播 HTML 源站列表；播放直出 m3u8/mp3
风格对齐 凤梨音乐.py
"""
import sys
import re

sys.path.append('..')
try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        def init(self, extend=""):
            pass


class Spider(Spider):
    # (id, name, url, category)
    STATIONS = [
        (0, '华语环球', 'https://sk.cri.cn/hyhq.m3u8', '国际'),
        (1, '环球资讯', 'https://sk.cri.cn/905.m3u8', '新闻'),
        (2, '轻松调频', 'https://sk.cri.cn/915.m3u8', '综合'),
        (3, '世界华声', 'https://sk.cri.cn/hxfh.m3u8', '国际'),
        (4, 'China Plus Radio', 'https://sk.cri.cn/am846.m3u8', '国际'),
        (5, '流行音乐', 'https://sk.cri.cn/887.m3u8', '音乐'),
        (6, '网络电台', 'https://live.ximalaya.com/radio-first-page-app/live/1006/64.m3u8', '综合'),
        (7, '香港电台', 'https://rthkradio1-live.akamaized.net/hls/live/2035313/radio1/master.m3u8?sd=10&rebase=on', '国际'),
        (8, '澳门电台', 'https://fm995.ddns.net/hls1/fm995.m3u8', '国际'),
        (9, '亚洲经典台', 'https://lhttp.qingting.fm/live/5021912/64k.mp3', '经典'),
        (10, 'HD音乐', 'https://lhttp.qingting.fm/live/15318341/64k.mp3', '音乐'),
        (11, '亚洲粤语', 'https://lhttp.qingting.fm/live/15318569/64k.mp3', '综合'),
        (12, '亚洲天空', 'https://lhttp.qingting.fm/live/20071/64k.mp3', '综合'),
        (13, '亚洲音乐', 'https://lhttp.qingting.fm/live/5022405/64k.mp3', '音乐'),
        (14, '老歌音乐台', 'http://live.xmcdn.com:80/live/2628/64.m3u8', '音乐'),
        (15, '怀集音乐台', 'http://live.xmcdn.com:80/live/966/64.m3u8', '音乐'),
        (16, 'Asia FM', 'https://lhttp.qingting.fm/live/5022405/64k.mp3', '综合'),
        (17, '亚洲音乐台', 'https://lhttp.qingting.fm/live/4581/64k.mp3', '音乐'),
        (18, 'Love Radio FM103.7', 'http://live.xmcdn.com/live/55/64.m3u8', '综合'),
        (19, '清晨音乐台', 'http://lhttp.qingting.fm/live/4915/64k.mp3', '音乐'),
        (20, '华语经典', 'http://ls.qingting.fm/live/3412131.m3u8?bitrate=64', '国际'),
        (21, '经典FM', 'http://stream3.hndt.com/now/C5NvUpwy/playlist.m3u8', '经典'),
        (22, '格莱美音乐', 'http://stream3.hndt.com/now/yorSd1X2/playlist.m3u8', '音乐'),
        (23, '有声文摘', 'http://stream3.hndt.com/now/WNoVfBcQ/playlist.m3u8', '综合'),
        (24, '民谣音乐', 'http://stream3.hndt.com/now/DTK5qc83/playlist.m3u8', '音乐'),
        (25, '天籁古典', 'http://stream3.hndt.com/now/MdOpB4zP/playlist.m3u8', '综合'),
        (26, '摇滚天空', 'http://stream3.hndt.com/now/SXJtR4M4/playlist.m3u8', '综合'),
        (27, '国乐悠扬', 'http://stream3.hndt.com/now/8bplFuwp/playlist.m3u8', '综合'),
        (28, '80后音乐台', 'http://stream3.hndt.com/now/SFZeH2cb/playlist.m3u8', '音乐'),
        (29, '动感音乐', 'http://stream3.hndt.com/now/ufjjbZxV/playlist.m3u8', '音乐'),
        (30, '安全百科', 'http://stream3.hndt.com/now/4pcovD2L/playlist.m3u8', '综合'),
        (31, '心灵音乐', 'http://play-radio-stream3.hndt.com/now/AFqvb0VX/playlist.m3u8', '音乐'),
        (32, '经典流行', 'http://play-radio-stream3.hndt.com/now/WUBA5hW2/playlist.m3u8', '音乐'),
        (33, '民谣蓝调', 'http://play-radio-stream3.hndt.com/now/XWfN89gh/playlist.m3u8', '综合'),
        (34, '潮流音乐', 'http://play-radio-stream3.hndt.com/now/Or5au0KN/playlist.m3u8', '音乐'),
        (35, '舞迷心窍', 'http://play-radio-stream3.hndt.com/now/WBhgSD3A/playlist.m3u8', '综合'),
        (36, '警广之声', 'http://play-radio-stream3.hndt.com/now/prIgXGFo/playlist.m3u8', '综合'),
        (37, '北京音乐广播', 'https://brtv-radiolive.rbc.cn/alive/fm974.m3u8', '音乐'),
        (38, '北京好音乐', 'http://live.xmcdn.com/live/964/64.m3u8', '音乐'),
        (39, '北京经典调频', 'http://live.funhillrm.com/4/sd/live.m3u8', '经典'),
        (40, '安徽音乐广播', 'https://satellitepull.cnr.cn/live/wxahyygb/playlist.m3u8', '音乐'),
        (41, '重庆音乐广播', 'https://satellitepull.cnr.cn/live/wxcqyygb/playlist.m3u8', '音乐'),
        (42, '福建汽车音乐', 'https://satellitepull.cnr.cn/live/wx32fjdnyygb/playlist.m3u8', '音乐'),
        (43, '广东音乐之声', 'https://satellitepull.cnr.cn/live/wxgdyyzs/playlist.m3u8', '音乐'),
        (44, '深圳飞扬971', 'https://satellitepull.cnr.cn/live/wxszfy971/playlist.m3u8', '音乐'),
        (45, '广西文艺广播', 'https://satellitepull.cnr.cn/live/wx32gxwygb/playlist.m3u8', '音乐'),
        (46, '贵州音乐广播', 'https://satellitepull.cnr.cn/live/wx32gzyygb/playlist.m3u8', '音乐'),
        (47, '海南音乐广播', 'https://satellitepull.cnr.cn/live/wxhainyygb/playlist.m3u8', '音乐'),
        (48, '河北音乐广播', 'https://satellitepull.cnr.cn/live/wxhebyygb/playlist.m3u8', '音乐'),
        (49, '黑龙江音乐广播', 'https://satellitepull.cnr.cn/live/wx32hljyygb/playlist.m3u8', '音乐'),
        (50, '楚天音乐广播', 'https://satellitepull.cnr.cn/live/wx32hubctyygb/playlist.m3u8', '音乐'),
        (51, '湖北经典音乐', 'https://satellitepull.cnr.cn/live/wx32hubyygb/playlist.m3u8', '音乐'),
        (52, '湖南年代音乐台', 'https://satellitepull.cnr.cn/live/wx32hunlygb/playlist.m3u8', '音乐'),
        (53, '江苏经典流行音乐', 'https://satellitepull.cnr.cn/live/wx32jsjdlxyy/playlist.m3u8', '音乐'),
        (54, '江苏音乐广播', 'https://satellitepull.cnr.cn/live/wx32jsyygb/playlist.m3u8', '音乐'),
        (55, '内蒙古音乐之声', 'https://satellitepull.cnr.cn/live/wx32nmgyygb/playlist.m3u8', '音乐'),
        (56, '宁夏音乐广播', 'https://satellitepull.cnr.cn/live/wxnxyygb/playlist.m3u8', '音乐'),
        (57, '青海交通音乐', 'https://satellitepull.cnr.cn/live/wx32qhjtyygb/playlist.m3u8', '音乐'),
        (58, '山东经典音乐', 'https://audiolive302.iqilu.com/sdradioShenghuo/sdradio04/playlist.m3u8', '音乐'),
        (59, '山东音乐广播', 'https://audiolive302.iqilu.com/sdradioYinyue/sdradio07/playlist.m3u8', '音乐'),
        (60, '陕西音乐广播', 'https://satellitepull.cnr.cn/live/wxsxxyygb/playlist.m3u8', '音乐'),
        (61, '四川城市之音', 'https://satellitepull.cnr.cn/live/wxsccszs/playlist.m3u8', '生活'),
        (62, '四川岷江音乐', 'https://satellitepull.cnr.cn/live/wxscmjyyt/playlist.m3u8', '音乐'),
        (63, '四川文艺广播', 'https://satellitepull.cnr.cn/live/wxscwygb/playlist.m3u8', '音乐'),
        (64, '云南音乐广播', 'https://satellitepull.cnr.cn/live/wxynyygb/playlist.m3u8', '音乐'),
        (65, '浙江女主播电台', 'https://satellitepull.cnr.cn/live/wxzj1045/playlist.m3u8', '生活'),
        (66, '浙江悦动之音', 'https://satellitepull.cnr.cn/live/wxzj968/playlist.m3u8', '综合'),
        (67, '江西音乐广播', 'https://satellitepull.cnr.cn/live/wx32jiangxyygb/playlist.m3u8', '音乐'),
        (68, '楚天交通广播', 'http://ls.qingting.fm/live/1291.m3u8', '新闻'),
        (69, '荆门交通音乐', 'http://ls.qingting.fm/live/60808.m3u8', '音乐'),
        (70, '襄阳交通广播', 'http://ls.qingting.fm/live/1307.m3u8', '新闻'),
        (71, '襄阳音乐广播', 'http://ls.qingting.fm/live/5057.m3u8', '音乐'),
        (72, '北京房山经典音乐', 'http://ls.qingting.fm/live/68746.m3u8', '音乐'),
        (73, '重庆新闻广播', 'http://live.xmcdn.com/live/128/64.m3u8', '新闻'),
        (74, '重庆经济广播', 'http://ls.qingting.fm/live/1499.m3u8', '新闻'),
        (75, '500首华语经典', 'http://ls.qingting.fm/live/3412131.m3u8?bitrate=64', '国际'),
        (76, '楚天音乐广播 FM105.8', 'http://ls.qingting.fm/live/1289.m3u8', '音乐'),
        (77, '楚天交通广播 FM92.7', 'http://ls.qingting.fm/live/1291.m3u8', '新闻'),
        (78, '荆门交通音乐 FM99.3', 'http://ls.qingting.fm/live/60808.m3u8', '音乐'),
        (79, '襄阳交通广播 FM89.0', 'http://ls.qingting.fm/live/1307.m3u8', '新闻'),
        (80, '重庆新闻广播 FM96.8', 'http://live.xmcdn.com/live/128/64.m3u8', '新闻'),
        (81, '重庆经济广播 FM101.5', 'http://ls.qingting.fm/live/1499.m3u8', '新闻'),
        (82, '重庆交通广播 FM95.5', 'http://live.xmcdn.com/live/130/64.m3u8', '新闻'),
        (83, '重庆音乐广播 FM88.1', 'http://live.xmcdn.com/live/131/64.m3u8', '音乐'),
        (84, '重庆都市广播 FM93.8', 'http://live.xmcdn.com/live/132/64.m3u8', '生活'),
        (85, '巴渝之声 FM104.5', 'http://ls.qingting.fm/live/3545693.m3u8', '综合'),
        (86, '万州交通广播', 'http://live.xmcdn.com/live/1679/64.m3u8', '新闻'),
        (87, '厦门音乐广播', 'http://ls.qingting.fm/live/1739.m3u8', '音乐'),
        (88, '厦门新闻广播', 'http://ls.qingting.fm/live/1737.m3u8', '新闻'),
        (89, '兰州新闻综合广播 FM97.3', 'http://ls.qingting.fm/live/1712.m3u8', '音乐'),
        (90, '兰州交通音乐广播 FM99.5', 'http://ls.qingting.fm/live/1711.m3u8', '音乐'),
        (91, '兰州生活文艺广播 FM100.8', 'http://ls.qingting.fm/live/1713.m3u8', '音乐'),
        (92, '广州综合', 'http://php.jdshipin.com:8880/gztv.php?id=zhonghe', '新闻'),
        (93, '广州新闻电台 FM96.2', 'http://live.xmcdn.com/live/256/64.m3u8', '新闻'),
        (94, '广州汽车音乐电台 FM102.7', 'http://live.xmcdn.com/live/257/64.m3u8', '音乐'),
        (95, '广州交通电台 FM106.1', 'http://ls.qingting.fm/live/4955.m3u8', '新闻'),
        (96, '广州 MYFM 88.0', 'http://ls.qingting.fm/live/52712.m3u8', '综合'),
        (97, '东广新闻台 FM90.9', 'http://ls.qingting.fm/live/275.m3u8', '新闻'),
        (98, '东莞FM104音乐广播', 'http://ls.qingting.fm/live/93619.m3u8', '音乐'),
        (99, '东莞畅享1075交通广播', 'http://ls.qingting.fm/live/1288.m3u8', '新闻'),
        (100, '九江交通广播 FM88.4', 'http://ls.qingting.fm/live/2785094.m3u8', '音乐'),
        (101, '云南交通广播 FM91.8', 'http://ls.qingting.fm/live/1928.m3u8', '音乐'),
        (102, '云南教育广播 FM100', 'http://ls.qingting.fm/live/1930.m3u8', '新闻'),
        (103, '云南新闻广播 FM105.8', 'http://ls.qingting.fm/live/1926.m3u8', '新闻'),
        (104, '云南民族广播', 'http://ls.qingting.fm/live/1933.m3u8', '综合'),
        (105, '云南经济广播 FM88.7', 'http://ls.qingting.fm/live/1927.m3u8', '音乐'),
        (106, '云南音乐广播 FM97', 'http://ls.qingting.fm/live/1929.m3u8', '音乐'),
        (107, '保定交通广播 FM104.8', 'http://ls.qingting.fm/live/28140.m3u8', '新闻'),
        (108, '保定城市服务广播', 'http://ls.qingting.fm/live/62628.m3u8', '生活'),
        (109, '保定新闻广播 FM93.7', 'http://ls.qingting.fm/live/3701149.m3u8', '新闻'),
        (110, '保定经典964汽车音乐广播', 'http://ls.qingting.fm/live/2227017.m3u8', '音乐'),
        (111, '南宁交通音乐广播 FM107.4', 'http://ls.qingting.fm/live/80793.m3u8', '音乐'),
        (112, '南通交通广播 FM92.9', 'http://ls.qingting.fm/live/2216385.m3u8', '新闻'),
        (113, '呼和浩特城市生活广播 FM90.1', 'http://ls.qingting.fm/live/2218717.m3u8', '生活'),
        (114, '呼和浩特文艺广播 FM99.8', 'http://ls.qingting.fm/live/3099076.m3u8', '音乐'),
        (115, '呼和浩特新闻综合广播 FM92.9', 'http://ls.qingting.fm/live/2218711.m3u8', '新闻'),
        (116, '咸阳城市之声 FM100.7', 'http://ls.qingting.fm/live/3559664.m3u8', '新闻'),
        (117, '四川文艺广播 FM90.0', 'http://ls.qingting.fm/live/4887.m3u8', '音乐'),
        (118, '四川新闻综合广播 FM98.1', 'http://ls.qingting.fm/live/4906.m3u8', '新闻'),
        (119, '四川民族广播 AM954', 'http://ls.qingting.fm/live/1115.m3u8', '综合'),
        (120, '四川私家车广播 FM92.5', 'http://ls.qingting.fm/live/4939.m3u8', '新闻'),
        (121, '四川财富广播 FM94.0', 'http://ls.qingting.fm/live/4927.m3u8', '新闻'),
        (122, '太原交通广播 FM107', 'http://ls.qingting.fm/live/4900.m3u8', '新闻'),
        (123, '太原新闻广播 FM91.2', 'http://ls.qingting.fm/live/23873.m3u8', '音乐'),
        (124, '太原私家车RADIO FM104.4', 'http://ls.qingting.fm/live/4018.m3u8', '新闻'),
        (125, '太原音乐广播 FM102.6', 'http://ls.qingting.fm/live/1185.m3u8', '音乐'),
        (126, '宁夏交通广播 FM98.4', 'http://ls.qingting.fm/live/1840.m3u8', '新闻'),
        (127, '宁夏都市广播 FM103.7', 'http://ls.qingting.fm/live/1842.m3u8', '生活'),
        (128, '山东体育广播 FM102.1', 'http://ls.qingting.fm/live/60266.m3u8', '综合'),
        (129, '山东女主播电台 FM97.5', 'http://ls.qingting.fm/live/60258.m3u8', '音乐'),
        (130, '山东新闻广播 FM95', 'http://ls.qingting.fm/live/60180.m3u8', '新闻'),
        (131, '山东生活广播 FM105', 'http://ls.qingting.fm/live/60260.m3u8', '生活'),
        (132, '山东音乐广播 FM99.1', 'http://ls.qingting.fm/live/1665.m3u8', '音乐'),
        (133, '岳阳交通广播 FM106.1', 'http://ls.qingting.fm/live/88931.m3u8', '新闻'),
        (134, '岳阳新闻综合广播', 'http://ls.qingting.fm/live/88933.m3u8', '新闻'),
        (135, '常州交通广播 FM90', 'http://ls.qingting.fm/live/2796.m3u8', '新闻'),
        (136, '广西女主播电台 FM97.0', 'http://ls.qingting.fm/live/1754.m3u8', '音乐'),
        (137, '广西新闻910 FM91.0', 'http://ls.qingting.fm/live/1753.m3u8', '音乐'),
        (138, '广西私家车930 FM93.0', 'http://ls.qingting.fm/live/1756.m3u8', '新闻'),
        (139, '广西音乐台 FM95.0', 'http://ls.qingting.fm/live/4875.m3u8', '音乐'),
        (140, '惠州新闻综合广播 FM100', 'http://ls.qingting.fm/live/5016.m3u8', '新闻'),
        (141, '惠州环保交通广播 FM98.8', 'http://ls.qingting.fm/live/5017.m3u8', '新闻'),
        (142, '惠州音乐广播 FM90.7', 'http://ls.qingting.fm/live/2212959.m3u8', '音乐'),
        (143, '新疆交通广播 FM94.9', 'http://ls.qingting.fm/live/1910.m3u8', '新闻'),
        (144, '新疆新闻广播 FM96.1', 'http://ls.qingting.fm/live/1902.m3u8', '新闻'),
        (145, '新疆民生广播 FM92.4', 'http://ls.qingting.fm/live/76186.m3u8', '新闻'),
        (146, '新疆维吾尔语交通文艺广播', 'http://ls.qingting.fm/live/78923.m3u8', '音乐'),
        (147, '新疆蒙古语广播', 'http://ls.qingting.fm/live/1903.m3u8', '综合'),
        (148, '无锡新闻广播 FM93.7', 'http://ls.qingting.fm/live/2777.m3u8', '新闻'),
        (149, '昆明汽车广播 FM95.4', 'http://ls.qingting.fm/live/1936.m3u8', '综合'),
        (150, '昆明资讯频率', 'http://ls.qingting.fm/live/1937.m3u8', '新闻'),
        (151, '昆明都市调频 FM102.8', 'http://ls.qingting.fm/live/1935.m3u8', '生活'),
        (152, '昆明阳光广播', 'http://ls.qingting.fm/live/1934.m3u8', '综合'),
        (153, '梅州交通广播 FM105.8', 'http://ls.qingting.fm/live/24195.m3u8', '新闻'),
        (154, '梅州新闻广播 FM94.8', 'http://ls.qingting.fm/live/24173.m3u8', '新闻'),
        (155, '江苏新闻广播 FM93.7', 'http://ls.qingting.fm/live/4944.m3u8', '新闻'),
        (156, '沈阳新闻广播 FM104.5', 'http://ls.qingting.fm/live/23891.m3u8', '新闻'),
        (157, '河北 MY FM 102.9', 'http://ls.qingting.fm/live/2508757.m3u8', '综合'),
        (158, '河北交通广播 FM99.2', 'http://ls.qingting.fm/live/1646.m3u8', '音乐'),
        (159, '河北农民广播 AM558', 'http://ls.qingting.fm/live/1650.m3u8', '综合'),
        (160, '河北故事广播 FM107.9', 'http://ls.qingting.fm/live/1645.m3u8', '经典'),
        (161, '河北新闻广播 FM104.3', 'http://ls.qingting.fm/live/1644.m3u8', '新闻'),
        (162, '河北旅游广播 AM603', 'http://ls.qingting.fm/live/1651.m3u8', '生活'),
        (163, '河北生活广播 FM88.8', 'http://ls.qingting.fm/live/4867.m3u8', '音乐'),
        (164, '河北私家车广播 FM90.7', 'http://ls.qingting.fm/live/4868.m3u8', '新闻'),
        (165, '河北音乐广播 FM102.4', 'http://ls.qingting.fm/live/1649.m3u8', '音乐'),
        (166, '河南乐龄广播 FM105.6', 'http://ls.qingting.fm/live/59896.m3u8', '综合'),
        (167, '河南交通广播 FM104.1', 'http://ls.qingting.fm/live/1209.m3u8', '新闻'),
        (168, '河南娱乐广播 FM97.6', 'http://ls.qingting.fm/live/1719795.m3u8', '音乐'),
        (169, '河南影院广播 FM90.0', 'http://ls.qingting.fm/live/1206.m3u8', '综合'),
        (170, '河南音乐广播 FM88.1', 'http://ls.qingting.fm/live/1208.m3u8', '音乐'),
        (171, '河南驾车1066 FM106.6', 'http://ls.qingting.fm/live/1207.m3u8', '新闻'),
        (172, '济南故事广播 FM104.3', 'http://ls.qingting.fm/live/1672.m3u8', '经典'),
        (173, '济南私家车广播 FM93.6', 'http://ls.qingting.fm/live/1670.m3u8', '新闻'),
        (174, '济南经济广播 FM90.9', 'http://ls.qingting.fm/live/1668.m3u8', '新闻'),
        (175, '济南音乐广播', 'http://ls.qingting.fm/live/1671.m3u8', '音乐'),
        (176, '浙江之声 FM88', 'http://ls.qingting.fm/live/4518.m3u8', '音乐'),
        (177, '浙江交通之声 FM93', 'http://ls.qingting.fm/live/4522.m3u8', '新闻'),
        (178, '浙江动听音乐调频 FM96.8', 'http://ls.qingting.fm/live/4866.m3u8', '音乐'),
        (179, '浙江女主播电台 FM104.5', 'http://ls.qingting.fm/live/4524.m3u8', '生活'),
        (180, '浙江财富广播 FM95', 'http://ls.qingting.fm/live/4519.m3u8', '新闻'),
        (181, '海南交通广播 FM100', 'http://ls.qingting.fm/live/4911.m3u8', '新闻'),
        (182, '海南国际旅游之声 FM103.8', 'http://ls.qingting.fm/live/1862.m3u8', '国际'),
        (183, '海南新闻广播 FM88.6', 'http://ls.qingting.fm/live/1861.m3u8', '音乐'),
        (184, '海南民生广播 FM101', 'http://ls.qingting.fm/live/1511803.m3u8', '新闻'),
        (185, '深圳快乐1062交通广播', 'http://ls.qingting.fm/live/1272.m3u8', '新闻'),
        (186, '深圳私家车广播 FM94.2', 'http://ls.qingting.fm/live/1273.m3u8', '新闻'),
        (187, '深圳飞扬音乐971', 'http://ls.qingting.fm/live/1271.m3u8', '音乐'),
        (188, '温州交通广播 FM103.9', 'http://ls.qingting.fm/live/23863.m3u8', '新闻'),
        (189, '温州新闻广播 FM94.9', 'http://ls.qingting.fm/live/23861.m3u8', '新闻'),
        (190, '温州私家车音乐广播 FM100.3', 'http://ls.qingting.fm/live/23865.m3u8', '音乐'),
        (191, '温州经济生活广播 FM88.8', 'http://ls.qingting.fm/live/23867.m3u8', '音乐'),
        (192, '温州绿色之声 FM93.8', 'http://ls.qingting.fm/live/1158.m3u8', '综合'),
        (193, '珠海电台交通音乐875', 'http://ls.qingting.fm/live/1275.m3u8', '音乐'),
        (194, '西宁交通频率', 'http://ls.qingting.fm/live/3400408.m3u8', '新闻'),
        (195, '西宁新闻频率', 'http://ls.qingting.fm/live/3400403.m3u8', '新闻'),
        (196, '西安交通广播 FM104.3', 'http://ls.qingting.fm/live/1611.m3u8', '新闻'),
        (197, '西安新闻广播 FM95.0', 'http://ls.qingting.fm/live/1610.m3u8', '新闻'),
        (198, '西安音乐广播 FM93.1', 'http://ls.qingting.fm/live/1612.m3u8', '音乐'),
        (199, '贵州新闻综合广播 FM94.6', 'http://ls.qingting.fm/live/23933.m3u8', '新闻'),
        (200, '贵州交通广播 FM95.2', 'http://ls.qingting.fm/live/23927.m3u8', '新闻'),
        (201, '贵州旅游广播 FM97.2', 'http://ls.qingting.fm/live/23929.m3u8', '音乐'),
        (202, '贵州经济广播 FM98.9', 'http://ls.qingting.fm/live/23935.m3u8', '新闻'),
        (203, '贵州音乐广播 FM91.6', 'http://ls.qingting.fm/live/23937.m3u8', '音乐'),
        (204, '辽宁交通广播 FM97.5', 'http://ls.qingting.fm/live/23801.m3u8', '音乐'),
        (205, '郑州新闻广播 FM98.6', 'http://ls.qingting.fm/live/1220.m3u8', '新闻'),
        (206, '郑州汽车广播 FM91.2', 'http://ls.qingting.fm/live/1211.m3u8', '音乐'),
        (207, '郑州活力944', 'http://ls.qingting.fm/live/4921.m3u8', '综合'),
        (208, '郑州车道931', 'http://ls.qingting.fm/live/1221.m3u8', '综合'),
        (209, '郴州综合广播 FM99.2', 'http://ls.qingting.fm/live/76765.m3u8', '音乐'),
        (210, '郴州音乐交通广播 FM102.8', 'http://ls.qingting.fm/live/86747.m3u8', '音乐'),
        (211, '金鹰955电台', 'http://ls.qingting.fm/live/4937.m3u8', '综合'),
        (212, '长春生活故事广播 FM90.0', 'http://ls.qingting.fm/live/5014.m3u8', '经典'),
        (213, '长沙城市之声 FM101.7', 'http://ls.qingting.fm/live/4237.m3u8', '生活'),
        (214, '长沙新闻广播 FM105.0', 'http://ls.qingting.fm/live/4877.m3u8', '新闻'),
        (215, '长治交通文艺广播 FM94.9', 'http://ls.qingting.fm/live/2669405.m3u8', '音乐'),
        (216, '长治新闻综合广播 FM94.3', 'http://ls.qingting.fm/live/2702863.m3u8', '新闻'),
        (217, '阳信人民广播电台 FM103.4', 'http://ls.qingting.fm/live/2915753.m3u8', '新闻'),
        (218, '阳泉交通广播', 'http://ls.qingting.fm/live/4592896.m3u8', '新闻'),
        (219, '阳泉新闻综合广播', 'http://ls.qingting.fm/live/5876899.m3u8', '新闻'),
        (220, '陕西交通广播 FM91.6', 'http://ls.qingting.fm/live/1601.m3u8', '音乐'),
        (221, '陕西故事广播 AM603', 'http://ls.qingting.fm/live/1608.m3u8', '经典'),
        (222, '陕西秦腔广播 FM101.1', 'http://ls.qingting.fm/live/1604.m3u8', '综合'),
        (223, '陕西都市广播 FM101.8', 'http://ls.qingting.fm/live/1609.m3u8', '生活'),
        (224, '陕西音乐广播 FM98.8', 'http://ls.qingting.fm/live/4873.m3u8', '音乐'),
        (225, '青岛交通广播 FM89.7', 'http://ls.qingting.fm/live/1676.m3u8', '新闻'),
        (226, '青岛故事广播 FM95.2', 'http://ls.qingting.fm/live/4956.m3u8', '经典'),
        (227, '青岛新闻广播 FM107.6', 'http://ls.qingting.fm/live/1673.m3u8', '新闻'),
        (228, '青岛西海岸城市生活广播 FM92.6', 'http://ls.qingting.fm/live/33446.m3u8', '新闻'),
        (229, '青海交通音乐广播 FM97.2', 'http://ls.qingting.fm/live/5009.m3u8', '音乐'),
        (230, '青海生活广播 FM90.3', 'http://ls.qingting.fm/live/2163891.m3u8', '生活'),
        (231, '青海经济广播 FM07.5', 'http://ls.qingting.fm/live/5008.m3u8', '新闻'),
        (232, '鹤壁交通音乐广播 FM93.5', 'http://ls.qingting.fm/live/3032681.m3u8', '音乐'),
        (233, '龙广交通广播 FM99.8', 'http://ls.qingting.fm/live/4973.m3u8', '音乐'),
        (234, '龙广新闻广播 FM94.6', 'http://ls.qingting.fm/live/4974.m3u8', '新闻'),
        (235, '龙广音乐广播 FM95.8', 'http://ls.qingting.fm/live/4969.m3u8', '音乐'),
    ]

    CATS = [
        {"type_id": "全部", "type_name": "全部"},
        {"type_id": "音乐", "type_name": "🎵 音乐"},
        {"type_id": "新闻", "type_name": "📰 新闻"},
        {"type_id": "国际", "type_name": "🌍 国际"},
        {"type_id": "经典", "type_name": "🎶 经典"},
        {"type_id": "生活", "type_name": "🏙️ 生活"},
        {"type_id": "综合", "type_name": "📻 综合"},
    ]

    def getName(self):
        return "全球广播"

    def init(self, extend=""):
        self.header = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.qingting.fm/",
        }

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in (".m3u8", ".mp3", ".mp4", ".aac", ".flv"))

    def homeContent(self, filter):
        return {"class": self.CATS, "filters": {}}

    def homeVideoContent(self):
        return {"list": self._to_list(self.STATIONS[:40])}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or "全部")
        if tid in ("", "全部", "all"):
            items = list(self.STATIONS)
        else:
            items = [s for s in self.STATIONS if s[3] == tid]
        # 简单分页，每页 40
        page_size = 40
        start = (pg - 1) * page_size
        chunk = items[start:start + page_size]
        pagecount = max(1, (len(items) + page_size - 1) // page_size)
        return {
            "list": self._to_list(chunk),
            "page": pg,
            "pagecount": pagecount,
            "limit": page_size,
            "total": len(items),
        }

    def _to_list(self, items):
        out = []
        for sid, name, url, cat in items:
            typ = "HLS" if (".m3u8" in url or "hls" in url.lower()) else "MP3"
            out.append({
                "vod_id": str(sid),
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "%s · %s" % (cat, typ),
            })
        return out

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        sid = str(raw).strip()
        if "$" in sid:
            sid = sid.split("$")[-1]
        item = None
        for s in self.STATIONS:
            if str(s[0]) == sid:
                item = s
                break
        if not item:
            return {"list": []}
        sid, name, url, cat = item
        typ = "HLS" if ".m3u8" in url else "直播"
        return {
            "list": [{
                "vod_id": str(sid),
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": cat,
                "vod_content": "分类：%s | 直链直播" % cat,
                "vod_play_from": "全球广播",
                "vod_play_url": "%s$%s" % (typ, url),
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        key = str(key or "").strip().lower()
        if not key:
            return {"list": []}
        items = [s for s in self.STATIONS if key in s[1].lower()]
        return {
            "list": self._to_list(items),
            "page": int(pg or 1),
            "pagecount": 1,
            "limit": len(items),
            "total": len(items),
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id or "").strip()
        if "$" in play_url:
            play_url = play_url.split("$", 1)[-1].strip()
        # 若传入的是电台 id，反查 url
        if play_url.isdigit():
            for s in self.STATIONS:
                if str(s[0]) == play_url:
                    play_url = s[2]
                    break
        header = dict(self.header)
        if "qingting.fm" in play_url:
            header["Referer"] = "https://www.qingting.fm/"
        elif "cri.cn" in play_url:
            header["Referer"] = "https://www.cri.cn/"
        return {
            "parse": 0,
            "url": play_url,
            "header": header,
        }

    def localProxy(self, param):
        return None

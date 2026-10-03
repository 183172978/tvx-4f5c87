/**
 * 低端影视(ddys.run)爬虫
 * 作者：deepseek
 * 版本：1.4
 * 最后更新：2026-05-21
 * 发布页：https://www.ddys.diy/
 *
 * @config
 * debug: false
 * showWebView: false
 * percent: 80,60
 * returnType: dom
 * timeout: 30
 * keywords: 需要密码访问|系统安全验证|人机验证
 * blockImages: true
 * blockList: *.[ico|png|jpeg|jpg|gif|webp]*|*.css|*.js
 *
 */

const baseUrl = 'https://www.ddys.run';
const headers = { 'Referer': baseUrl };

// ==================== 首页分类 ====================
async function homeContent(filter) {
    var commonFilters = [
        { key: "class", name: "按剧情", value: [
            {n:"全部",v:""}, {n:"喜剧",v:"喜剧"}, {n:"爱情",v:"爱情"}, {n:"恐怖",v:"恐怖"},
            {n:"动作",v:"动作"}, {n:"科幻",v:"科幻"}, {n:"剧情",v:"剧情"}, {n:"战争",v:"战争"},
            {n:"警匪",v:"警匪"}, {n:"犯罪",v:"犯罪"}, {n:"动画",v:"动画"}, {n:"奇幻",v:"奇幻"},
            {n:"武侠",v:"武侠"}, {n:"冒险",v:"冒险"}, {n:"枪战",v:"枪战"}, {n:"悬疑",v:"悬疑"},
            {n:"惊悚",v:"惊悚"}, {n:"经典",v:"经典"}, {n:"青春",v:"青春"}, {n:"文艺",v:"文艺"},
            {n:"古装",v:"古装"}, {n:"历史",v:"历史"}, {n:"运动",v:"运动"}
        ] },
        { key: "area", name: "按地区", value: [
            {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"},
            {n:"美国",v:"美国"}, {n:"法国",v:"法国"}, {n:"英国",v:"英国"}, {n:"日本",v:"日本"},
            {n:"韩国",v:"韩国"}, {n:"德国",v:"德国"}, {n:"泰国",v:"泰国"}, {n:"印度",v:"印度"},
            {n:"意大利",v:"意大利"}, {n:"西班牙",v:"西班牙"}, {n:"加拿大",v:"加拿大"}, {n:"其他",v:"其他"}
        ] },
        { key: "year", name: "按年份", value: [
            {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"},
            {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"},
            {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"},
            {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"},
            {n:"2011",v:"2011"}, {n:"2010",v:"2010"}
        ] }
    ];

    var animeFilters = [
        { key: "year", name: "按年份", value: [
            {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"},
            {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"},
            {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"},
            {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"},
            {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"},
            {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}
        ] }
    ];

    return {
        class: [
            { type_id: "dianying", type_name: "电影" },
            { type_id: "juji", type_name: "剧集" },
            { type_id: "dongman", type_name: "动漫" }
        ],
        filters: {
            "dianying": commonFilters,
            "juji": commonFilters,
            "dongman": animeFilters
        }
    };
}

// ==================== 首页推荐 ====================
async function homeVideoContent() {
    var doc = await Java.wvOpen(baseUrl + '/');
    var videos = parseVideoList(doc);
    return { list: videos };
}

// ==================== 分类内容 ====================
async function categoryContent(tid, pg, filter, extend) {
    var p = parseInt(pg) || 1;
    var ext = extend || {};
    
    var area = ext.area;
    var year = ext.year;
    var cat = ext.class;
    
    var url = '';
    var hasArea = area && area !== '' && area !== '全部';
    var hasCat = cat && cat !== '' && cat !== '全部';
    var hasYear = year && year !== '' && year !== '全部';
    
    if (hasArea) {
        url = baseUrl + '/list/' + tid + '-' + area + '----------.html';
    } else if (hasCat) {
        url = baseUrl + '/list/' + tid + '---' + cat + '--------.html';
    } else if (hasYear) {
        url = baseUrl + '/list/' + tid + '-----------' + year + '.html';
    } else {
        url = baseUrl + '/category/' + tid + '-' + p + '.html';
    }
    
    console.log("category URL: " + url);
    var doc = await Java.wvOpen(url);
    var videos = parseVideoList(doc);
    
    var page = p;
    var pagecount = p;
    var total = videos.length;
    
    try {
        var pageEl = doc.querySelector(".stui-page__item li.active.num a");
        if (!pageEl) pageEl = doc.querySelector("li.active.num a");
        if (pageEl) {
            var pageText = pageEl.textContent || pageEl.innerText;
            var parts = pageText.split('/');
            if (parts.length === 2) {
                page = parseInt(parts[0]);
                pagecount = parseInt(parts[1]);
                total = pagecount * 12;
            }
        }
    } catch(e) {
        console.log("分页解析错误: " + e);
    }
    
    return { code: 1, msg: "数据列表", list: videos, page: page, pagecount: pagecount, limit: 12, total: total };
}

// ==================== 详情页 ====================
async function detailContent(ids) {
    var id = Array.isArray(ids) ? ids[0] : ids;
    var doc = await Java.wvOpen(id);
    var list = parseDetailPage(doc);
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list: list };
}

// ==================== 搜索 ====================
async function searchContent(key, quick, pg) {
    var p = parseInt(pg) || 1;
    var url = baseUrl + '/search/' + encodeURIComponent(key) + '----------' + p + '---.html';
    console.log("search URL: " + url);
    
    // 使用 wvOpen 复用 WebView 的 Cookie 会话（密码验证）
    var doc = await Java.wvOpen(url);
    if (!doc) {
        return { code: 0, msg: "搜索失败", list: [], page: 1, pagecount: 1, limit: 12, total: 0 };
    }
    
    var videos = parseVideoList(doc);
    var page = p;
    var pagecount = p;
    var total = videos.length;
    
    try {
        var pageEl = doc.querySelector("li.active.num a");
        if (pageEl) {
            var pageText = pageEl.textContent || pageEl.innerText;
            var parts = pageText.split('/');
            if (parts.length === 2) {
                page = parseInt(parts[0]);
                pagecount = parseInt(parts[1]);
                total = pagecount * 12;
            }
        }
    } catch(e) {
        console.log("搜索分页解析错误: " + e);
    }
    
    return { code: 1, msg: "数据列表", list: videos, page: page, pagecount: pagecount, limit: 12, total: total };
}

// ==================== 播放器 ====================
async function playerContent(flag, id, vipFlags) {
    return { url: id, parse: 1, header: headers };
}

// ==================== 路由配置 ====================
var routes = {
    homeVideoContent: function() {
        return baseUrl + '/';
    },
    categoryContent: function(tid, pg, filter, extend) {
        var p = parseInt(pg) || 1;
        return baseUrl + '/category/' + tid + '-' + p + '.html';
    },
    detailContent: function(ids) {
        var id = Array.isArray(ids) ? ids[0] : ids;
        return id;
    },
    searchContent: function(key, quick, pg) {
        // 搜索使用 wvOpen，不需要 routes 预加载
        return false;
    },
    playerContent: function(flag, id, vipFlags) {
        return id;
    }
};

// ==================== 辅助函数 ====================

function parseVideoList(doc) {
    var boxes = doc.querySelectorAll('.stui-vodlist__box');
    var list = [];
    
    for (var i = 0; i < boxes.length; i++) {
        var box = boxes[i];
        var titleEl = box.querySelector('.title a');
        var thumbEl = box.querySelector('.stui-vodlist__thumb');
        var remarksEl = box.querySelector('.pic-text');
        
        var vodId = titleEl ? titleEl.getAttribute('href') : '';
        if (vodId && !vodId.startsWith('http')) {
            vodId = baseUrl + (vodId.startsWith('/') ? '' : '/') + vodId;
        }
        
        var vodName = titleEl ? (titleEl.title || titleEl.textContent || '') : '';
        var vodPic = '';
        if (thumbEl) {
            vodPic = thumbEl.getAttribute('data-original') || thumbEl.src || '';
            if (!vodPic && thumbEl.style.backgroundImage) {
                var match = thumbEl.style.backgroundImage.match(/url\(["']?([^"')]+)["']?\)/);
                if (match) vodPic = match[1];
            }
        }
        
        var vodRemarks = remarksEl ? remarksEl.textContent.trim() : '';
        var vodYear = '';
        var yearMatch = vodRemarks.match(/(19|20)\d{2}/);
        if (yearMatch) vodYear = yearMatch[0];
        
        var vodActor = '';
        var textEl = box.querySelector('.text');
        if (textEl && textEl.previousSibling && textEl.previousSibling.nodeType === 8) {
            vodActor = textEl.previousSibling.textContent.trim();
        }
        
        if (vodId && vodName) {
            list.push({
                vod_id: vodId,
                vod_name: vodName,
                vod_pic: vodPic,
                vod_remarks: vodRemarks,
                vod_year: vodYear,
                vod_actor: vodActor
            });
        }
    }
    return list;
}

function parseDetailPage(doc) {
    var title = doc.querySelector('.stui-content__detail .title');
    var vodName = title ? title.textContent.trim() : '';
    
    var thumb = doc.querySelector('.stui-content__thumb img');
    var vodPic = thumb ? (thumb.src || '') : '';
    
    var info = doc.querySelectorAll('.stui-content__detail .data');
    var vodArea = '', vodYear = '', vodActor = '', vodDirector = '', vodRemarks = '';
    
    if (info.length > 0) {
        var typeMatch = info[0].textContent.match(/类型：([^/]+)\s*\/\s*地区：([^/]+)\s*\/\s*年份：(\d+)/);
        if (typeMatch) {
            vodArea = typeMatch[2] || '';
            vodYear = typeMatch[3] || '';
        }
    }
    if (info.length > 1) {
        vodActor = info[1].textContent.replace('主演：', '').trim();
    }
    if (info.length > 2) {
        vodDirector = info[2].textContent.replace('导演：', '').trim();
    }
    if (info.length > 3) {
        vodRemarks = info[3].textContent.replace('更新：', '').trim();
    }
    
    var vodContent = doc.querySelector('.detail-content') || doc.querySelector('.detail-sketch');
    vodContent = vodContent ? vodContent.textContent.trim() : '';
    
    var head = doc.querySelector('.stui-vodlist__head h3');
    var ul = doc.querySelector('.stui-content__playlist');
    var vodPlayFrom = head ? head.textContent.trim().replace('在线播放', '线路') : '';
    var vodPlayUrl = '';
    
    if (ul) {
        var links = ul.querySelectorAll('a');
        var eps = [];
        for (var i = 0; i < links.length; i++) {
            var link = links[i];
            var epName = link.textContent.trim();
            var epUrl = link.getAttribute('href');
            if (epUrl && !epUrl.startsWith('http')) {
                epUrl = baseUrl + (epUrl.startsWith('/') ? '' : '/') + epUrl;
            }
            eps.push(epName + '$' + epUrl);
        }
        vodPlayUrl = eps.join('#');
    }
    
    return [{
        vod_id: vodName.replace(/[^\w]/g, '_'),
        vod_name: vodName,
        vod_pic: vodPic,
        vod_remarks: vodRemarks,
        vod_year: vodYear,
        vod_actor: vodActor,
        vod_director: vodDirector,
        vod_area: vodArea,
        vod_lang: vodArea.indexOf('大陆') !== -1 ? '国语' : '其他',
        vod_content: vodContent,
        vod_play_from: vodPlayFrom,
        vod_play_url: vodPlayUrl
    }];
}
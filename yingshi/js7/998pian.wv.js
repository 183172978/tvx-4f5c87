/**
 * @config
 * timeout: 30
 * blockImages: true
 * returnType: dom
 * keyword: Checking your browser|Just a moment|请稍候
 */

const baseUrl = 'https://www.998pian.com';
const headers = { 'Referer': baseUrl };

function safeText(el) {
    if (!el) return '';
    return (el.textContent || el.innerText || '').replace(/\s+/g, ' ').trim();
}

function fixUrl(url) {
    if (!url) return '';
    if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
    if (url.indexOf('//') === 0) return 'https:' + url;
    return baseUrl.replace(/\/$/, '') + (url.charAt(0) === '/' ? url : '/' + url);
}

// 判断当前页面是否为搜索页
function isSearchPage() {
    return window.location.href.indexOf('/vodsearch/') !== -1;
}

// 从元素中提取图片URL（支持 data-original、src、background-image）
function getImageUrl(el) {
    if (!el) return '';
    var url = el.getAttribute('data-original') || el.getAttribute('src') || '';
    if (url) return url;
    // 尝试从 style 中提取 background-image
    var style = el.getAttribute('style');
    if (style) {
        var match = style.match(/url\(["']?([^"')]+)["']?\)/);
        if (match) return match[1];
    }
    return '';
}

// 解析视频列表 - 根据页面类型使用不同的选择器
function parseVideoList() {
    var isSearch = isSearchPage();
    var list = [];
    
    if (isSearch) {
        // 搜索页：使用 .hl-list-item 选择器
        var items = document.querySelectorAll('.hl-list-item');
        for (var i = 0; i < items.length; i++) {
            var el = items[i];
            // 搜索页的标题链接
            var link = el.querySelector('a');
            if (!link) continue;
            
            var vodId = link.getAttribute('href');
            // 标题：优先使用 title 属性，否则用 textContent 并过滤角标
            var rawTitle = link.getAttribute('title') || safeText(link);
            var vodName = rawTitle.replace(/^(第\d+集|更新至第\d+集|剧集|正片|HD|高清版|抢先版|HD中字)\s*/, '').trim();
            if (!vodName) vodName = rawTitle;
            
            // 搜索页的图片在 .hl-item-thumb 的 data-original 属性中
            var thumb = el.querySelector('.hl-item-thumb');
            var vodPic = thumb ? getImageUrl(thumb) : '';
            // 如果没有找到，尝试 img 标签
            if (!vodPic) {
                var img = el.querySelector('img');
                vodPic = img ? getImageUrl(img) : '';
            }
            
            var vodRemarks = '';
            var remarkEl = el.querySelector('.remarks, .tag');
            if (remarkEl) vodRemarks = safeText(remarkEl);
            
            if (vodId && vodName) {
                list.push({
                    vod_id: fixUrl(vodId),
                    vod_name: vodName,
                    vod_pic: fixUrl(vodPic),
                    vod_remarks: vodRemarks
                });
            }
        }
    } else {
        // 首页/分类页：使用 .hl-vod-list .hl-list-item 选择器
        var items = document.querySelectorAll('.hl-vod-list .hl-list-item');
        for (var i = 0; i < items.length; i++) {
            var el = items[i];
            // 标题链接
            var link = el.querySelector('.hl-item-title a');
            if (!link) continue;
            
            var vodId = link.getAttribute('href');
            var vodName = safeText(link);
            
            var img = el.querySelector('.hl-item-thumb');
            var vodPic = img ? getImageUrl(img) : '';
            
            var vodRemarks = '';
            var remarkEl = el.querySelector('.hl-pic-text .remarks');
            if (remarkEl) vodRemarks = safeText(remarkEl);
            
            if (vodId && vodName) {
                list.push({
                    vod_id: fixUrl(vodId),
                    vod_name: vodName,
                    vod_pic: fixUrl(vodPic),
                    vod_remarks: vodRemarks
                });
            }
        }
    }
    return list;
}

function waitForPage() {
    return new Promise(function(resolve) {
        var checkCount = 0;
        var maxChecks = 30;
        var interval = setInterval(function() {
            checkCount++;
            var isSearch = isSearchPage();
            var selector = isSearch ? '.hl-list-item' : '.hl-vod-list .hl-list-item';
            var items = document.querySelectorAll(selector);
            if (items.length > 0 || checkCount >= maxChecks) {
                clearInterval(interval);
                resolve();
            }
        }, 100);
    });
}

// ==================== 首页分类 ====================
function homeContent() {
    return {
        class: [
            { type_id: 'dianying', type_name: '电影' },
            { type_id: 'dianshiju', type_name: '电视剧' },
            { type_id: 'zongyi', type_name: '综艺' },
            { type_id: 'dongman', type_name: '动漫' },
            { type_id: 'duanju', type_name: '短剧' }
        ],
        filters: {
            dianying: [],
            dianshiju: [],
            zongyi: [],
            dongman: [],
            duanju: []
        }
    };
}

// ==================== 首页推荐 ====================
async function homeVideoContent() {
    await waitForPage();
    var list = parseVideoList();
    return { list: list.slice(0, 20) };
}

// ==================== 分类内容 ====================
async function categoryContent(tid, pg, filter, extend) {
    await waitForPage();
    var list = parseVideoList();
    var p = parseInt(pg) || 1;
    
    var pagecount = p;
    var totalEl = document.querySelector('.hl-page-total');
    if (totalEl) {
        var totalText = safeText(totalEl);
        var match = totalText.match(/\/(\d+)/);
        if (match) pagecount = parseInt(match[1]);
    }
    
    if (pagecount === p) {
        var pageLinks = document.querySelectorAll('.hl-page-wrap a');
        var maxPage = p;
        for (var i = 0; i < pageLinks.length; i++) {
            var text = safeText(pageLinks[i]);
            if (text && /^\d+$/.test(text)) {
                var num = parseInt(text);
                if (num > maxPage) maxPage = num;
            }
        }
        if (maxPage > p) pagecount = maxPage;
    }
    
    return { list: list, page: p, pagecount: pagecount, total: list.length };
}

// ==================== 详情页 ====================
async function detailContent(ids) {
    var id = Array.isArray(ids) ? ids[0] : ids;
    await waitForPage();
    
    var vodName = safeText(document.querySelector('h1')) || '';
    var picEl = document.querySelector('.hl-detail-pic img');
    var vodPic = picEl ? getImageUrl(picEl) : '';
    
    var vodContent = '';
    var descEl = document.querySelector('.hl-vod-data .hl-text-content');
    if (descEl) vodContent = safeText(descEl);
    
    var playFrom = [];
    var playUrlGroups = [];
    
    var sourceTabs = document.querySelectorAll('.hl-play-source .hl-plays-from a');
    var sourceContents = document.querySelectorAll('.hl-play-source .hl-plays-list');
    
    for (var s = 0; s < sourceTabs.length; s++) {
        var sourceName = safeText(sourceTabs[s]);
        if (!sourceName) continue;
        playFrom.push(sourceName);
        
        var eps = [];
        var episodeLinks = sourceContents[s] ? sourceContents[s].querySelectorAll('li a') : [];
        for (var e = 0; e < episodeLinks.length; e++) {
            var epLink = episodeLinks[e];
            var epName = safeText(epLink) || ('第' + (e + 1) + '集');
            var epUrl = epLink.getAttribute('href');
            if (epUrl) eps.push(epName + '$' + fixUrl(epUrl));
        }
        playUrlGroups.push(eps.join('#'));
    }
    
    if (playFrom.length === 0) {
        var fallbackLinks = document.querySelectorAll('.hl-plays-list a');
        if (fallbackLinks.length > 0) {
            playFrom.push('在线播放');
            var eps = [];
            for (var f = 0; f < fallbackLinks.length; f++) {
                var epName = safeText(fallbackLinks[f]) || ('第' + (f + 1) + '集');
                var epUrl = fallbackLinks[f].getAttribute('href');
                if (epUrl) eps.push(epName + '$' + fixUrl(epUrl));
            }
            playUrlGroups.push(eps.join('#'));
        }
    }
    
    return {
        list: [{
            vod_id: id,
            vod_name: vodName,
            vod_pic: fixUrl(vodPic),
            vod_content: vodContent,
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playUrlGroups.join('$$$')
        }]
    };
}

// ==================== 搜索 ====================
async function searchContent(key, quick, pg) {
    await waitForPage();
    var list = parseVideoList();
    var p = parseInt(pg) || 1;
    
    var pagecount = p;
    var totalEl = document.querySelector('.hl-page-total');
    if (totalEl) {
        var totalText = safeText(totalEl);
        var match = totalText.match(/\/(\d+)/);
        if (match) pagecount = parseInt(match[1]);
    }
    
    return { list: list, page: p, pagecount: pagecount, total: list.length };
}

// ==================== 播放器 ====================
async function playerContent(flag, id, vipFlags) {
    return { parse: 1, url: id, header: headers };
}

// ==================== 路由配置 ====================
var routes = {
    homeVideoContent: function() { return baseUrl + '/'; },
    categoryContent: function(tid, pg, filter, extend) {
        var p = parseInt(pg) || 1;
        return baseUrl + '/vodshow/' + tid + '--------' + p + '---.html';
    },
    detailContent: function(ids) {
        var id = Array.isArray(ids) ? ids[0] : ids;
        return fixUrl(id);
    },
    searchContent: function(key, quick, pg) {
        var p = parseInt(pg) || 1;
        return baseUrl + '/vodsearch/-------------.html?wd=' + encodeURIComponent(key) + '&page=' + p;
    }
};
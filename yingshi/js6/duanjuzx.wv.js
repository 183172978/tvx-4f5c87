/**
 * 短剧网(duanjuzx.com)爬虫 - 稳定版
 * 修复搜索功能
 */

const baseUrl = 'https://www.duanjuzx.com';
const headers = {
    'Referer': baseUrl,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
};

function safeText(el) {
    if (!el) return '';
    return (el.textContent || el.innerText || '').replace(/\s+/g, ' ').trim();
}

function fixUrl(url, doc) {
    if (!url) return '';
    if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
    if (url.indexOf('//') === 0) return 'https:' + url;
    if (doc && typeof doc.fixUrl === 'function') return doc.fixUrl(url);
    return baseUrl.replace(/\/$/, '') + (url.charAt(0) === '/' ? url : '/' + url);
}

function extractList(doc) {
    var items = doc.querySelectorAll('.stui-vodlist li');
    var list = [];
    for (var i = 0; i < items.length; i++) {
        var el = items[i];
        var box = el.querySelector('.stui-vodlist__box');
        if (!box) continue;
        var thumb = box.querySelector('.stui-vodlist__thumb');
        var link = thumb ? thumb.getAttribute('href') : '';
        var vodId = link ? fixUrl(link, doc) : '';
        var vodName = safeText(box.querySelector('.title a')) || (thumb ? thumb.getAttribute('title') : '');
        if (!vodId || !vodName) continue;
        var img = thumb ? (thumb.getAttribute('data-original') || thumb.getAttribute('src') || '') : '';
        var remarks = safeText(box.querySelector('.pic-text.text-right'));
        var type = safeText(box.querySelector('.pic-text1.text-right'));
        list.push({
            vod_id: vodId,
            vod_name: vodName,
            vod_pic: fixUrl(img, doc),
            vod_remarks: remarks || type || ''
        });
    }
    return list;
}

function extractPlaylist(doc, id) {
    var tabs = doc.querySelectorAll('.nav-tabs li');
    var froms = [];
    var urls = [];
    
    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        var tabLink = tab.querySelector('a');
        if (!tabLink) continue;
        var tabId = tabLink.getAttribute('href') ? tabLink.getAttribute('href').replace('#', '') : '';
        if (!tabId) continue;
        var pane = doc.querySelector('#' + tabId);
        if (!pane) continue;
        var fromName = safeText(tabLink) || ('线路' + (i + 1));
        var items = pane.querySelectorAll('.stui-content__playlist li a');
        var eps = [];
        for (var j = 0; j < items.length; j++) {
            var epLink = items[j].getAttribute('href');
            var epName = safeText(items[j]) || ('第' + (j + 1) + '集');
            if (epLink) eps.push(epName + '$' + fixUrl(epLink, doc));
        }
        if (eps.length) {
            froms.push(fromName);
            urls.push(eps.join('#'));
        }
    }
    
    if (froms.length === 0) {
        var allLinks = doc.querySelectorAll('.stui-content__playlist li a');
        if (allLinks.length > 0) {
            var eps = [];
            for (var j = 0; j < allLinks.length; j++) {
                var epLink = allLinks[j].getAttribute('href');
                var epName = safeText(allLinks[j]) || ('第' + (j + 1) + '集');
                if (epLink) eps.push(epName + '$' + fixUrl(epLink, doc));
            }
            if (eps.length) return { from: '线路1', url: eps.join('#') };
        }
        return { from: '线路1', url: '全集$' + id };
    }
    
    return { from: froms.join('$$$'), url: urls.join('$$$') };
}

async function init(cfg) { return; }

async function homeContent(filter) {
    return {
        class: [
            { type_id: '20', type_name: '短剧' },
            { type_id: '1', type_name: '电影' },
            { type_id: '2', type_name: '电视' },
            { type_id: '4', type_name: '动漫' },
            { type_id: '3', type_name: '综艺' },
            { type_id: '32', type_name: '纪录片' }
        ],
        filters: {}
    };
}

async function homeVideoContent() {
    var res = await fetch(baseUrl + '/', { headers: headers });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    return { list: extractList(res.doc) };
}

async function categoryContent(tid, pg, filter, extend) {
    pg = parseInt(pg) || 1;
    var url = baseUrl + '/category-' + tid + '-' + pg + '/';
    var res = await fetch(url, { headers: headers });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    var list = extractList(res.doc);
    
    var numEl = res.doc.querySelector('.stui-page__item .num a');
    var pagecount = pg;
    if (numEl) {
        var numText = safeText(numEl);
        var match = numText.match(/\/(\d+)/);
        if (match) pagecount = parseInt(match[1]);
    }
    
    return { page: pg, pagecount: pagecount, list: list, total: list.length };
}

async function detailContent(ids) {
    var id = Array.isArray(ids) ? ids[0] : ids;
    var res = await fetch(fixUrl(id), { headers: headers });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    var doc = res.doc;
    
    var title = safeText(doc.querySelector('h1.title'));
    var picEl = doc.querySelector('.stui-content__thumb img');
    var vodPic = picEl ? fixUrl(picEl.getAttribute('data-original') || picEl.getAttribute('src'), doc) : '';
    var contentEl = doc.querySelector('.desc .detail-sketch') || doc.querySelector('.desc .detail-content');
    var content = safeText(contentEl);
    var playlist = extractPlaylist(doc, id);
    
    return {
        list: [{
            vod_id: id,
            vod_name: title,
            vod_pic: vodPic,
            vod_content: content,
            vod_play_from: playlist.from,
            vod_play_url: playlist.url
        }]
    };
}

// 修复搜索：使用 POST 请求到 /sch/-------------/
async function searchContent(key, quick, pg) {
    pg = parseInt(pg) || 1;
    // 使用 POST 请求，参数 wd
    var res = await fetch(baseUrl + '/sch/-------------/', {
        method: 'POST',
        headers: {
            'Referer': baseUrl,
            'User-Agent': headers['User-Agent'],
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'wd=' + encodeURIComponent(key) + '&submit='
    });
    
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    
    var list = extractList(res.doc);
    
    // 搜索结果分页判断
    var numEl = res.doc.querySelector('.stui-page__item .num a');
    var pagecount = pg;
    if (numEl) {
        var numText = safeText(numEl);
        var match = numText.match(/\/(\d+)/);
        if (match) pagecount = parseInt(match[1]);
    } else {
        var nextLink = res.doc.querySelector('.stui-page__item .next');
        var hasNext = nextLink && nextLink.getAttribute('href') && !nextLink.parentElement.classList.contains('disabled');
        pagecount = hasNext ? pg + 1 : pg;
    }
    
    return { page: pg, pagecount: pagecount, list: list, total: list.length };
}

async function playerContent(flag, id, vipFlags) {
    return { parse: 1, url: id, header: headers };
}

async function action(actionStr) { return; }

var routes = {
    homeVideoContent: function() { return baseUrl + '/'; },
    categoryContent: function(tid, pg, filter, extend) {
        var p = parseInt(pg) || 1;
        return baseUrl + '/category-' + tid + '-' + p + '/';
    },
    detailContent: function(ids) {
        var id = Array.isArray(ids) ? ids[0] : ids;
        return fixUrl(id);
    },
    searchContent: function(key, quick, pg) {
        // 搜索使用 POST，但路由返回 false 让异步函数处理
        return false;
    },
    playerContent: function(flag, id, vipFlags) {
        return id;
    }
};

var spider = { init, homeContent, homeVideoContent, categoryContent, detailContent, searchContent, playerContent, action };
spider;
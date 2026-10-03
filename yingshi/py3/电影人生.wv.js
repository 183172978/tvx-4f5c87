/**
 * @config
 * timeout: 30
 * blockImages: true
 * ua: mobile
 * keyword: Checking your browser|Just a moment|请稍候
 */

const BASE_URL = 'https://www.dyrsok.com';
const IMG_HOST = 'https://pic2.tupian.click';

function safeText(el) {
    if (!el) return '';
    return (el.textContent || el.innerText || '').replace(/\s+/g, ' ').trim();
}

function fixImgUrl(img) {
    if (!img) return '';
    var src = img.getAttribute('src') || '';
    var dataSrc = img.getAttribute('data-src') || '';
    
    if (src && src.indexOf('http') === 0 && src.indexOf('data:') !== 0) {
        return src;
    }
    if (dataSrc && dataSrc.indexOf('data:') !== 0) {
        if (dataSrc.charAt(0) === '/') {
            return IMG_HOST + dataSrc;
        }
        return IMG_HOST + '/' + dataSrc;
    }
    if (src && src.indexOf('data:') !== 0 && src.indexOf('http') !== 0) {
        if (src.charAt(0) === '/') {
            return IMG_HOST + src;
        }
        return IMG_HOST + '/' + src;
    }
    return src;
}

// 从指定容器（Selector 或 Element）中提取影片列表
function extractListFromContainer(doc, container) {
    var element;
    if (typeof container === 'string') {
        element = doc.querySelector(container);
    } else {
        element = container;
    }
    if (!element) return [];
    var items = element.querySelectorAll('.relative.group');
    var list = [];
    for (var i = 0; i < items.length; i++) {
        var el = items[i];
        var link = el.querySelector('a[href]');
        var img = el.querySelector('img');
        var imgUrl = fixImgUrl(img);
        var remarkEl = el.querySelector('.absolute.top-2.right-2');
        var remark = safeText(remarkEl);
        
        list.push({
            vod_id: link ? link.getAttribute('href') : '',
            vod_name: link ? (link.getAttribute('title') || safeText(el.querySelector('h3'))) : '',
            vod_pic: imgUrl,
            vod_remarks: remark
        });
    }
    return list;
}

async function homeContent(filter) {
    var commonFilters = {
        'dianying': [
            { key: 'class', name: '分类', value: [
                { n: '全部', v: '' }, { n: '剧情', v: '剧情' }, { n: '喜剧', v: '喜剧' },
                { n: '动作', v: '动作' }, { n: '爱情', v: '爱情' }, { n: '惊悚', v: '惊悚' },
                { n: '犯罪', v: '犯罪' }, { n: '悬疑', v: '悬疑' }, { n: '冒险', v: '冒险' },
                { n: '奇幻', v: '奇幻' }, { n: '战争', v: '战争' }, { n: '历史', v: '历史' },
                { n: '传记', v: '传记' }, { n: '武侠', v: '武侠' }, { n: '动画', v: '动画' },
                { n: '音乐', v: '音乐' }
            ]},
            { key: 'area', name: '地区', value: [
                { n: '全部', v: '' }, { n: '美国', v: '美国' }, { n: '内地', v: '内地' },
                { n: '香港', v: '香港' }, { n: '台湾', v: '台湾' }, { n: '日本', v: '日本' },
                { n: '韩国', v: '韩国' }, { n: '英国', v: '英国' }, { n: '法国', v: '法国' },
                { n: '德国', v: '德国' }, { n: '印度', v: '印度' }, { n: '意大利', v: '意大利' },
                { n: '澳大利亚', v: '澳大利亚' }, { n: '泰国', v: '泰国' }, { n: '比利时', v: '比利时' }
            ]},
            { key: 'year', name: '年份', value: [
                { n: '全部', v: '' }, { n: '2026', v: '2026' }, { n: '2025', v: '2025' },
                { n: '2024', v: '2024' }, { n: '2023', v: '2023' }, { n: '2022', v: '2022' },
                { n: '2021', v: '2021' }, { n: '2020', v: '2020' }, { n: '2019', v: '2019' },
                { n: '2018', v: '2018' }, { n: '2017', v: '2017' }, { n: '2016', v: '2016' },
                { n: '2015', v: '2015' }, { n: '2014', v: '2014' }, { n: '2013', v: '2013' },
                { n: '2012', v: '2012' }, { n: '2011', v: '2011' }, { n: '2010', v: '2010' },
                { n: '2009', v: '2009' }, { n: '2008', v: '2008' }, { n: '2007', v: '2007' },
                { n: '2006', v: '2006' }, { n: '2005', v: '2005' }, { n: '2004', v: '2004' },
                { n: '2003', v: '2003' }, { n: '2002', v: '2002' }, { n: '2001', v: '2001' },
                { n: '2000', v: '2000' }
            ]},
            { key: 'sort_field', name: '排序', value: [
                { n: '默认', v: '' }, { n: '热度', v: 'play_hot' }, { n: '年份', v: 'year' }
            ]}
        ]
    };

    return {
        class: [
            { type_id: 'dianying', type_name: '电影' },
            { type_id: 'dianshiju', type_name: '电视剧' },
            { type_id: 'zongyi', type_name: '综艺' },
            { type_id: 'dongman', type_name: '动漫' },
            { type_id: 'duanju', type_name: '短剧' }
        ],
        filters: {
            'dianying': commonFilters.dianying,
            'dianshiju': commonFilters.dianying,
            'zongyi': commonFilters.dianying,
            'dongman': commonFilters.dianying,
            'duanju': commonFilters.dianying
        }
    };
}

async function homeVideoContent() {
    var res = await fetch(BASE_URL + '/', { returnType: 'dom' });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    
    // 从首页各个分类区块精确提取，避免轮播图干扰
    var containers = ['#dianying', '#dianshiju', '#zongyi', '#dongman', '#duanju'];
    var allList = [];
    for (var i = 0; i < containers.length; i++) {
        var part = extractListFromContainer(res.doc, containers[i]);
        for (var j = 0; j < part.length; j++) {
            allList.push(part[j]);
        }
    }
    return { list: allList };
}

async function categoryContent(tid, pg, filter, extend) {
    var p = parseInt(pg) || 1;
    var page = p - 1;
    var ext = extend || {};
    var url = BASE_URL + '/' + tid + '.html?page=' + page;
    if (ext.class) url += '&class=' + encodeURIComponent(ext.class);
    if (ext.area) url += '&area=' + encodeURIComponent(ext.area);
    if (ext.year) url += '&year=' + encodeURIComponent(ext.year);
    if (ext.sort_field) url += '&sort_field=' + encodeURIComponent(ext.sort_field);
    
    var res = await fetch(url, { returnType: 'dom' });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    
    // 分类页固定从 #image-grid 提取
    var list = extractListFromContainer(res.doc, '#image-grid');
    return { page: p, pagecount: 0, list: list, total: 0 };
}

async function detailContent(ids) {
    var id = Array.isArray(ids) ? ids[0] : ids;
    var res = await fetch(BASE_URL + id, { returnType: 'dom' });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    
    var doc = res.doc;
    
    var title = safeText(doc.querySelector('h1'));
    var year = safeText(doc.querySelector('.text-gray-500.mb-4 span:nth-child(2)')) || 
               safeText(doc.querySelector('[class*="text-sm"][class*="px-2"][class*="bg-gray-100"]:nth-child(2)'));
    var area = safeText(doc.querySelector('.text-gray-500.mb-4 span:nth-child(3)'));
    var desc = safeText(doc.querySelector('.text-sm.text-justify')) || 
               safeText(doc.querySelector('[style*="word-break: break-all"]'));
    var director = safeText(doc.querySelector('[href*="director"] span'));
    var actors = [];
    var actorEls = doc.querySelectorAll('[href*="actor"] span');
    for (var i = 0; i < actorEls.length; i++) {
        actors.push(safeText(actorEls[i]));
    }
    
    var originBtns = doc.querySelectorAll('#originTabs button, #originTabs a button');
    var origins = [];
    for (var k = 0; k < originBtns.length; k++) {
        var btn = originBtns[k];
        var origin = btn.getAttribute('data-origin') || btn.getAttribute('id') || btn.textContent.trim();
        if (origin && origins.indexOf(origin) === -1) origins.push(origin);
    }
    if (origins.length === 0) origins = ['jsm3u8'];
    
    var epLinks = doc.querySelectorAll('#episodeContent .seqlist a');
    var eps = [];
    for (var j = 0; j < epLinks.length; j++) {
        var ep = epLinks[j];
        var epName = safeText(ep.querySelector('button'));
        if (!epName) epName = '第' + (j+1) + '集';
        var href = ep.getAttribute('href') || '';
        var p = '';
        var match = href.match(/[?&]p=(\d+)/);
        if (match) p = match[1];
        eps.push({ name: epName, p: p });
    }
    
    var playFrom = [];
    var playUrl = [];
    for (var oi = 0; oi < origins.length; oi++) {
        var oname = origins[oi];
        playFrom.push(oname);
        var epParts = [];
        for (var ei = 0; ei < eps.length; ei++) {
            var e = eps[ei];
            var link = BASE_URL + id + '?origin=' + oname + '&p=' + e.p;
            epParts.push(e.name + '$' + link);
        }
        if (epParts.length === 0) {
            epParts.push('正片$' + BASE_URL + id + '?origin=' + oname);
        }
        playUrl.push(epParts.join('#'));
    }
    
    return {
        list: [{
            vod_id: id,
            vod_name: title,
            vod_pic: fixImgUrl(doc.querySelector('.poster img, [class*="aspect-\\[2\\/3\\]"] img')),
            vod_year: year,
            vod_area: area,
            vod_content: desc,
            vod_director: director,
            vod_actor: actors.join(','),
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playUrl.join('$$$')
        }]
    };
}

async function searchContent(key, quick, pg) {
    var p = parseInt(pg) || 1;
    var page = p - 1;
    var url = BASE_URL + '/s.html?name=' + encodeURIComponent(key) + '&page=' + page + '&sort_field=_id';
    var res = await fetch(url, { returnType: 'dom' });
    if (res.error || !res.doc) return Result.error(res.error || '请求失败');
    
    // 搜索页固定从 #image-grid 提取
    var list = extractListFromContainer(res.doc, '#image-grid');
    return { page: p, pagecount: 0, list: list, total: 0 };
}

async function playerContent(flag, id, vipFlags) {
    return { parse: 1, url: id, header: { 'Referer': BASE_URL } };
}

var routes = {
    homeVideoContent: function () { return false; },
    categoryContent: function () { return false; },
    detailContent: function () { return false; },
    searchContent: function () { return false; }
};
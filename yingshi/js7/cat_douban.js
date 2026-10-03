/*
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '豆瓣采集_4',
  lang: 'cat',
})
*/

const DOUBAN_API = 'https://frodo.douban.com/api/v2';
const API_KEY = '0ac44ae016490db2204ce0a042db2916';
const USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat";
const REFERER = "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html";

const BOCAI_SITES = [
    { key: 'wwzy.tv', name: '旺旺短剧', api: 'https://wwzy.tv/api.php/provide/vod' },
    { key: 'dbzy.tv', name: '豆瓣资源', api: 'https://caiji.dbzy5.com/api.php/provide/vod' },
    { key: 'mtzy.me', name: '茅台资源', api: 'https://caiji.maotaizy.cc/api.php/provide/vod' },
    { key: 'huyazy.com', name: '虎牙资源', api: 'https://www.huyaapi.com/api.php/provide/vod' }
];

const SEARCH_TIMEOUT = 4000;
const TODAY = new Date().toISOString().split('T')[0];

var searchCache = {};

function isReleased(item) {
    if (item.release_date) return item.release_date <= TODAY;
    if (item.date) return item.date <= TODAY;
    return true;
}

async function doubanRequest(path, params = {}) {
    try {
        let url = DOUBAN_API + path;
        params.apikey = API_KEY;
        params.has_schedule = true;
        let queryParts = [];
        for (let key in params) {
            if (params[key] !== undefined && params[key] !== '') {
                queryParts.push(key + '=' + encodeURIComponent(params[key]));
            }
        }
        if (queryParts.length > 0) url += '?' + queryParts.join('&');
        let res = await req(url, {
            headers: { 'User-Agent': USER_AGENT, 'Referer': REFERER, 'Host': 'frodo.douban.com' },
            timeout: 4000
        });
        return JSON.parse(res.content);
    } catch (e) { return {}; }
}

async function init() { return true; }

async function home() {
    let classes = [
        { type_name: '热门电影', type_id: 'hot_movie' },
        { type_name: '热播剧集', type_id: 'tv_hot' },
        { type_name: '热播综艺', type_id: 'show_hot' },
        { type_name: '电影筛选', type_id: 'movie_filter' },
        { type_name: '电视筛选', type_id: 'tv_filter' }
    ];
    let filters = {
        'hot_movie': [
            { key: 'sort', name: '排序', value: [{ n: '热度', v: 'recommend' }, { n: '最新', v: 'time' }, { n: '评分', v: 'rank' }] },
            { key: 'area', name: '地区', value: [{ n: '全部', v: '全部' }, { n: '华语', v: '华语' }, { n: '欧美', v: '欧美' }, { n: '韩国', v: '韩国' }, { n: '日本', v: '日本' }] }
        ],
        'tv_hot': [{ key: 'type', name: '分类', value: [{ n: '综合', v: 'tv_hot' }, { n: '国产剧', v: 'tv_domestic' }, { n: '欧美剧', v: 'tv_american' }, { n: '日剧', v: 'tv_japanese' }, { n: '韩剧', v: 'tv_korean' }, { n: '动画', v: 'tv_animation' }] }],
        'show_hot': [{ key: 'type', name: '分类', value: [{ n: '综合', v: 'show_hot' }, { n: '国内', v: 'show_domestic' }, { n: '国外', v: 'show_foreign' }] }],
        'movie_filter': [
            { key: '类型', name: '类型', value: [{ n: '全部', v: '' }, { n: '喜剧', v: '喜剧' }, { n: '爱情', v: '爱情' }, { n: '动作', v: '动作' }, { n: '科幻', v: '科幻' }, { n: '动画', v: '动画' }, { n: '悬疑', v: '悬疑' }, { n: '犯罪', v: '犯罪' }, { n: '惊悚', v: '惊悚' }, { n: '恐怖', v: '恐怖' }, { n: '纪录片', v: '纪录片' }] },
            { key: '地区', name: '地区', value: [{ n: '全部', v: '' }, { n: '华语', v: '华语' }, { n: '欧美', v: '欧美' }, { n: '韩国', v: '韩国' }, { n: '日本', v: '日本' }] },
            { key: 'sort', name: '排序', value: [{ n: '热度', v: 'T' }, { n: '最新', v: 'R' }, { n: '评分', v: 'S' }] }
        ],
        'tv_filter': [
            { key: '类型', name: '类型', value: [{ n: '全部', v: '' }, { n: '国产剧', v: 'tv_domestic' }, { n: '美剧', v: 'tv_american' }, { n: '韩剧', v: 'tv_korean' }, { n: '日剧', v: 'tv_japanese' }, { n: '动画', v: 'tv_animation' }] },
            { key: 'sort', name: '排序', value: [{ n: '热度', v: 'T' }, { n: '最新', v: 'R' }, { n: '评分', v: 'S' }] }
        ]
    };
    return JSON.stringify({ class: classes, filters: filters });
}

async function homeVod() {
    try {
        let res = await doubanRequest('/subject_collection/movie_top250/items', { count: 30 });
        let list = [];
        let items = res.subject_collection_items || [];
        for (let item of items) {
            if ((item.type === 'movie' || item.type === 'tv') && isReleased(item)) {
                let rating = item.rating ? item.rating.value : '暂无';
                list.push({ vod_id: item.id, vod_name: item.title || '', vod_pic: item.pic ? item.pic.normal : '', vod_remarks: rating + '', vod_year: item.year || '', vod_tag: item.type || '' });
            }
        }
        return JSON.stringify({ list: list });
    } catch (e) { return JSON.stringify({ list: [] }); }
}

async function category(tid, pg, _, ext = {}) {
    try {
        let start = (parseInt(pg) - 1) * 30;
        let res = {};
        if (tid === 'hot_movie') { res = await doubanRequest('/movie/hot_gaia', { sort: ext.sort || 'recommend', area: ext.area || '全部', start, count: 30 }); }
        else if (tid === 'tv_hot' || tid === 'show_hot') { res = await doubanRequest('/subject_collection/' + (ext.type || tid) + '/items', { start, count: 30 }); }
        else if (tid === 'movie_filter') { let tags = []; if (ext.类型) tags.push(ext.类型); if (ext.地区) tags.push(ext.地区); res = await doubanRequest('/movie/recommend', { tags: tags.join(','), sort: ext.sort || 'T', start, count: 30 }); }
        else if (tid === 'tv_filter') { let tags = []; if (ext.类型) tags.push(ext.类型); res = await doubanRequest('/tv/recommend', { tags: tags.join(','), sort: ext.sort || 'T', start, count: 30 }); }
        let list = [];
        let items = res.subject_collection_items || res.items || [];
        for (let item of items) {
            if (!isReleased(item)) continue;
            let rating = item.rating ? item.rating.value : '暂无';
            list.push({ vod_id: item.id, vod_name: item.title || '', vod_pic: item.pic ? item.pic.normal : '', vod_remarks: rating + '', vod_year: item.year || '', vod_tag: item.type || '' });
        }
        return JSON.stringify({ list, page: parseInt(pg), pagecount: 9999, limit: 30, total: 999999 });
    } catch (e) { return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: 30, total: 0 }); }
}

async function searchBocai(site, searchName, cleanName) {
    try {
        let searchUrl = site.api + '?ac=detail&wd=' + encodeURIComponent(searchName);
        let res = await req(searchUrl, { timeout: SEARCH_TIMEOUT, headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } });
        let json = JSON.parse(res.content);
        if (json && json.list && json.list.length > 0) {
            let matched = null;
            for (let item of json.list) { if (item.vod_name.replace(/\s+/g, '') === cleanName) { matched = item; break; } }
            if (!matched) matched = json.list[0];
            if (matched.vod_play_url) {
                let playFroms = matched.vod_play_from ? matched.vod_play_from.split('$$$') : ['默认'];
                let playUrls = matched.vod_play_url.split('$$$');
                let results = [];
                for (let f = 0; f < playUrls.length; f++) {
                    let sourceName = site.name;
                    if (playFroms.length > 1) sourceName += '-' + (playFroms[f] || '线路' + (f + 1));
                    let epList = playUrls[f].split('#').filter(e => e);
                    if (epList.length > 0) { results.push({ name: sourceName, key: site.key + '_' + f, epCount: epList.length, playFrom: playFroms[f] || '默认', playUrl: playUrls[f], siteKey: site.key }); }
                }
                return results;
            }
        }
    } catch (e) {}
    return [];
}

async function detail(id) {
    try {
        let doubanRes = await doubanRequest('/subject/' + id, {});
        let movieName = doubanRes.title || '';
        if (!movieName) return JSON.stringify({ list: [{ vod_id: id, vod_name: '加载失败', vod_play_url: '' }] });
        let cleanName = movieName.replace(/\s+/g, '');
        let searchName = movieName.replace(/第[一二三四五六七八九十百千\d]+[季部集]/gi, '').replace(/\bS(?:E(?:ASON)?)?\s*\d+\s*(?:E\s*\d+)?\b/gi, '').trim();
        let tasks = BOCAI_SITES.map(site => searchBocai(site, searchName, cleanName));
        let allResults = await Promise.all(tasks);
        let validSources = [];
        for (let results of allResults) { for (let r of results) { if (r.playUrl) validSources.push(r); } }
        searchCache['db_' + id] = validSources;
        let playFroms = [], playUrls = [];
        if (validSources.length > 0) {
            for (let source of validSources) {
                playFroms.push(source.name);
                let eps = source.playUrl.split('#').filter(e => e);
                playUrls.push(eps.map((ep, idx) => { let parts = ep.split('$'); return (parts[0] || ('第' + (idx + 1) + '集')) + '$' + source.key + '@@' + idx; }).join('#'));
            }
        } else { playFroms.push('暂无线路'); playUrls.push('暂无选集$none@@0'); }
        let vod = {
            vod_id: id, vod_name: movieName, vod_pic: doubanRes.pic ? doubanRes.pic.large : '',
            vod_year: doubanRes.year || '', vod_area: doubanRes.countries ? doubanRes.countries.join('/') : '',
            vod_director: doubanRes.directors ? doubanRes.directors.map(d => d.name).join('/') : '',
            vod_actor: doubanRes.actors ? doubanRes.actors.slice(0, 5).map(a => a.name).join('/') : '',
            vod_content: doubanRes.intro || '', vod_type: doubanRes.genres ? doubanRes.genres.join('/') : '',
            vod_play_from: playFroms.join('$$$'), vod_play_url: playUrls.join('$$$')
        };
        return JSON.stringify({ list: [vod] });
    } catch (e) { return JSON.stringify({ list: [{ vod_id: id, vod_name: '加载失败', vod_play_url: '' }] }); }
}

async function play(flag, id) {
    try {
        let parts = id.split('@@');
        let sourceKey = parts[0];
        let epIndex = parseInt(parts[1]);
        if (sourceKey === 'none') return JSON.stringify({ parse: 0, url: '', header: {} });
        let underscoreIdx = sourceKey.lastIndexOf('_');
        let siteKey = sourceKey.substring(0, underscoreIdx);
        let doubanId = '';
        for (let key in searchCache) {
            if (key.startsWith('db_')) { let sources = searchCache[key]; for (let s of sources) { if (s.key === sourceKey) { doubanId = key.replace('db_', ''); break; } } if (doubanId) break; }
        }
        let targetSource = null;
        if (doubanId) { let sources = searchCache['db_' + doubanId] || []; for (let s of sources) { if (s.key === sourceKey) { targetSource = s; break; } } }
        if (!targetSource || !targetSource.playUrl) {
            let site = BOCAI_SITES.find(s => s.key === siteKey);
            if (site && doubanId) {
                let doubanRes = await doubanRequest('/subject/' + doubanId, {});
                let movieName = doubanRes.title || '';
                let searchName = movieName.replace(/第[一二三四五六七八九十百千\d]+[季部集]/gi, '').replace(/\bS(?:E(?:ASON)?)?\s*\d+\s*(?:E\s*\d+)?\b/gi, '').trim();
                let cleanName = movieName.replace(/\s+/g, '');
                let results = await searchBocai(site, searchName, cleanName);
                for (let r of results) { if (r.key === sourceKey) { targetSource = r; break; } }
            }
        }
        if (!targetSource || !targetSource.playUrl) return JSON.stringify({ parse: 0, url: '', header: {} });
        let eps = targetSource.playUrl.split('#').filter(e => e);
        if (epIndex >= eps.length) epIndex = 0;
        let epParts = eps[epIndex].split('$');
        let playUrl = epParts.length > 1 ? epParts[1] : epParts[0];
        if (!playUrl || !playUrl.startsWith('http')) return JSON.stringify({ parse: 0, url: '', header: {} });
        return JSON.stringify({ parse: 0, url: playUrl, header: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } });
    } catch (e) { return JSON.stringify({ parse: 0, url: '', header: {} }); }
}

async function search(wd, _, pg = "1") {
    try {
        let res = await doubanRequest('/search/movie', { q: wd, count: 20, start: (parseInt(pg) - 1) * 20 });
        let list = [];
        let items = res.items || [];
        for (let item of items) {
            let target = item.target || item;
            if (!isReleased(target)) continue;
            let rating = target.rating ? target.rating.value : '暂无';
            list.push({ vod_id: target.id || item.id, vod_name: target.title || item.title || '', vod_pic: target.cover_url || (target.pic ? target.pic.normal : ''), vod_remarks: rating + '', vod_year: target.year || '', vod_tag: target.type || '' });
        }
        return JSON.stringify({ list, page: parseInt(pg) });
    } catch (e) { return JSON.stringify({ list: [], page: 1 }); }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, play, proxy: null, search };
}

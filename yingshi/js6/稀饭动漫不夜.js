const CryptoJS = require("crypto-js");
const axios = require("axios");
const cheerio = require("cheerio");
const https = require("https");

let log = () => {};

const SITE_CONFIG = {
    title: "稀饭动漫",
    host: "https://dm.xifanacg.com",
    debug: true,
    recommend: true,
    class_name: "连载新番&完结旧番&剧场版&美漫",
    class_url: "1&2&3&21",
    searchable: 1,
    quickSearch: 0,
    filterable: 1,
    play_parse: true,
    limit: 40,
    headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Referer": "https://dm.xifanacg.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    classMap: {
        1: "/type/1.html",
        2: "/type/2.html",
        3: "/type/3.html",
        21: "/type/21.html",
    },
    DANMU_API: process.env.DANMU_API || "",
};

const FILTERS = {
    '1': [
        {
            key: 'class',
            name: '类型',
            value: [
                { n: '全部', v: '' },
                { n: '搞笑', v: '搞笑' },
                { n: '原创', v: '原创' },
                { n: '轻小说改', v: '轻小说改' },
                { n: '恋爱', v: '恋爱' },
                { n: '百合', v: '百合' },
                { n: '漫改', v: '漫改' },
                { n: '校园', v: '校园' },
                { n: '战斗', v: '战斗' },
                { n: '治愈', v: '治愈' },
                { n: '奇幻', v: '奇幻' },
                { n: '日常', v: '日常' },
                { n: '青春', v: '青春' },
                { n: '乙女向', v: '乙女向' },
                { n: '悬疑', v: '悬疑' },
                { n: '后宫', v: '后宫' },
                { n: '科幻', v: '科幻' },
                { n: '冒险', v: '冒险' },
                { n: '热血', v: '热血' },
                { n: '异世界', v: '异世界' },
                { n: '游戏改', v: '游戏改' },
                { n: '音乐', v: '音乐' },
                { n: '偶像', v: '偶像' },
                { n: '美食', v: '美食' },
                { n: '耽美', v: '耽美' },
            ],
        },
        { key: 'area', name: '地区', value: [{ n: '全部', v: '' }, { n: '日本', v: '日本' }] },
        {
            key: 'year',
            name: '年份',
            value: [
                { n: '全部', v: '' },
                { n: '2026', v: '2026' }, { n: '2025', v: '2025' }, { n: '2024', v: '2024' },
                { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, { n: '2021', v: '2021' },
                { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, { n: '2018', v: '2018' },
                { n: '2017', v: '2017' }, { n: '2016', v: '2016' }, { n: '2015', v: '2015' },
                { n: '2014', v: '2014' }, { n: '2013', v: '2013' }, { n: '2012', v: '2012' },
                { n: '2011', v: '2011' }, { n: '2010', v: '2010' }, { n: '2009', v: '2009' },
                { n: '2008', v: '2008' }, { n: '2007', v: '2007' }, { n: '2006', v: '2006' },
                { n: '2005', v: '2005' },
            ],
        },
        { key: 'by', name: '排序', value: [{ n: '最新', v: 'time' }, { n: '最热', v: 'hits' }, { n: '评分', v: 'score' }] },
    ],
    '2': [
        {
            key: 'class',
            name: '类型',
            value: [
                { n: '全部', v: '' },
                { n: '搞笑', v: '搞笑' },
                { n: '原创', v: '原创' },
                { n: '轻小说改', v: '轻小说改' },
                { n: '恋爱', v: '恋爱' },
                { n: '百合', v: '百合' },
                { n: '漫改', v: '漫改' },
                { n: '校园', v: '校园' },
                { n: '战斗', v: '战斗' },
                { n: '治愈', v: '治愈' },
                { n: '奇幻', v: '奇幻' },
                { n: '日常', v: '日常' },
                { n: '青春', v: '青春' },
                { n: '乙女向', v: '乙女向' },
                { n: '悬疑', v: '悬疑' },
                { n: '后宫', v: '后宫' },
                { n: '科幻', v: '科幻' },
                { n: '冒险', v: '冒险' },
                { n: '热血', v: '热血' },
                { n: '异世界', v: '异世界' },
                { n: '游戏改', v: '游戏改' },
                { n: '音乐', v: '音乐' },
                { n: '偶像', v: '偶像' },
                { n: '美食', v: '美食' },
                { n: '耽美', v: '耽美' },
            ],
        },
        { key: 'area', name: '地区', value: [{ n: '全部', v: '' }, { n: '日本', v: '日本' }, { n: '中国', v: '中国' }, { n: '欧美', v: '欧美' }] },
        {
            key: 'year',
            name: '年份',
            value: [
                { n: '全部', v: '' },
                { n: '2026', v: '2026' }, { n: '2025', v: '2025' }, { n: '2024', v: '2024' },
                { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, { n: '2021', v: '2021' },
                { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, { n: '2018', v: '2018' },
                { n: '2017', v: '2017' }, { n: '2016', v: '2016' }, { n: '2015', v: '2015' },
                { n: '2014', v: '2014' }, { n: '2013', v: '2013' }, { n: '2012', v: '2012' },
                { n: '2011', v: '2011' }, { n: '2010', v: '2010' }, { n: '2009', v: '2009' },
                { n: '2008', v: '2008' }, { n: '2007', v: '2007' }, { n: '2006', v: '2006' },
                { n: '2005', v: '2005' },
            ],
        },
        { key: 'by', name: '排序', value: [{ n: '最新', v: 'time' }, { n: '最热', v: 'hits' }, { n: '评分', v: 'score' }] },
    ],
    '3': [
        {
            key: 'class',
            name: '类型',
            value: [
                { n: '全部', v: '' },
                { n: '剧场版', v: '剧场版' },
                { n: '动画电影', v: '动画电影' },
                { n: '奇幻', v: '奇幻' },
                { n: '战斗', v: '战斗' },
                { n: '恋爱', v: '恋爱' },
                { n: '冒险', v: '冒险' },
            ],
        },
        { key: 'area', name: '地区', value: [{ n: '全部', v: '' }, { n: '日本', v: '日本' }, { n: '中国', v: '中国' }, { n: '欧美', v: '欧美' }] },
        {
            key: 'year',
            name: '年份',
            value: [
                { n: '全部', v: '' },
                { n: '2026', v: '2026' }, { n: '2025', v: '2025' }, { n: '2024', v: '2024' },
                { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, { n: '2021', v: '2021' },
                { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, { n: '2018', v: '2018' },
                { n: '2017', v: '2017' }, { n: '2016', v: '2016' }, { n: '2015', v: '2015' },
                { n: '2014', v: '2014' }, { n: '2013', v: '2013' }, { n: '2012', v: '2012' },
                { n: '2011', v: '2011' }, { n: '2010', v: '2010' },
            ],
        },
        { key: 'by', name: '排序', value: [{ n: '最新', v: 'time' }, { n: '最热', v: 'hits' }, { n: '评分', v: 'score' }] },
    ],
    '21': [
        {
            key: 'class',
            name: '类型',
            value: [
                { n: '全部', v: '' },
                { n: '美漫', v: '美漫' },
                { n: '搞笑', v: '搞笑' },
                { n: '科幻', v: '科幻' },
                { n: '奇幻', v: '奇幻' },
                { n: '冒险', v: '冒险' },
            ],
        },
        { key: 'area', name: '地区', value: [{ n: '全部', v: '' }, { n: '欧美', v: '欧美' }, { n: '美国', v: '美国' }] },
        {
            key: 'year',
            name: '年份',
            value: [
                { n: '全部', v: '' },
                { n: '2026', v: '2026' }, { n: '2025', v: '2025' }, { n: '2024', v: '2024' },
                { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, { n: '2021', v: '2021' },
                { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, { n: '2018', v: '2018' },
                { n: '2017', v: '2017' }, { n: '2016', v: '2016' }, { n: '2015', v: '2015' },
            ],
        },
        { key: 'by', name: '排序', value: [{ n: '最新', v: 'time' }, { n: '最热', v: 'hits' }, { n: '评分', v: 'score' }] },
    ],
};

const axiosInstance = axios.create({
    timeout: 15000,
    httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false, family: 4 }),
    headers: { ...SITE_CONFIG.headers },
});

// ===================== 工具函数 完全复用 =====================
function stripTags(html) {
    return String(html || '')
        .replace(/<script[\s\S]*?<\/script>/gi, ' ')
        .replace(/<style[\s\S]*?<\/style>/gi, ' ')
        .replace(/<[^>]+>/g, ' ')
        .replace(/&nbsp;/gi, ' ')
        .replace(/&amp;/gi, '&')
        .replace(/&#39;/g, "'")
        .replace(/&quot;/g, '"')
        .replace(/\s+/g, ' ')
        .trim();
}
function safeJsonParse(text, fallback) {
    try { return JSON.parse(text); } catch (_) { return fallback; }
}
function pickParamValue(...values) {
    for (const value of values) {
        if (value == null) continue;
        if (typeof value === 'string' || typeof value === 'number') {
            const s = String(value).trim();
            if (s) return s;
            continue;
        }
        if (typeof value === 'object') {
            const nested = pickParamValue(
                value.vod_id, value.videoId, value.play_id, value.playId,
                value.categoryId, value.type_id, value.tid, value.id, value.url, value.href, value.path
            );
            if (nested) return nested;
        }
    }
    return '';
}
function fullUrl(path, host = SITE_CONFIG.host) {
    const value = pickParamValue(path);
    if (!value) return '';
    if (/^https?:\/\//i.test(value)) return value;
    try {
        return new URL(value.startsWith('/') ? value : `/${value}`, host).toString();
    } catch (_) { return ''; }
}
function fixImg(img) { return fullUrl(img); }
function cleanText(text) { return stripTags(text); }
function decodePlayerUrl(encoded) {
    try {
        const first = Buffer.from(String(encoded || ''), 'base64').toString('utf8');
        return decodeURIComponent(first);
    } catch (_) { return String(encoded || ''); }
}
function preprocessTitle(title) {
    if (!title) return '';
    return title
        .replace(/4[kK]|[xX]26[45]|720[pP]|1080[pP]|2160[pP]/g, ' ')
        .replace(/[hH]\.?26[45]/g, ' ')
        .replace(/BluRay|WEB-DL|HDR|REMUX/gi, ' ')
        .replace(/\.mp4|\.mkv|\.avi|\.flv/gi, ' ');
}
function chineseToArabic(cn) {
    const map = { 零: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };
    if (!isNaN(cn)) return parseInt(cn, 10);
    if (cn.length === 1) return map[cn] || cn;
    if (cn.length === 2) {
        if (cn[0] === '十') return 10 + map[cn[1]];
        if (cn[1] === '十') return map[cn[0]] * 10;
    }
    if (cn.length === 3) return map[cn[0]] * 10 + map[cn[2]];
    return cn;
}
function extractEpisode(title) {
    if (!title) return '';
    const processedTitle = preprocessTitle(title).trim();
    const cnMatch = processedTitle.match(/第\s*([零一二三四五六七八九十0-9]+)\s*[集话章节回期]/);
    if (cnMatch) return String(chineseToArabic(cnMatch[1]));
    const seMatch = processedTitle.match(/[Ss](?:\d{1,2})?[-._\s]*[Ee](\d{1,3})/i);
    if (seMatch) return seMatch[1];
    const epMatch = processedTitle.match(/\b(?:EP|E)[-._\s]*(\d{1,3})\b/i);
    if (epMatch) return epMatch[1];
    const bracketMatch = processedTitle.match(/[\[\(【(](\d{1,3})[\]\)】)]/);
    if (bracketMatch) {
        const num = bracketMatch[1];
        if (!['720', '1080', '480'].includes(num)) return num;
    }
    return '';
}
function buildFileNameForDanmu(vodName, episodeTitle) {
    if (!vodName) return '';
    if (!episodeTitle || episodeTitle === '正片' || episodeTitle === '播放') return vodName;
    const digits = extractEpisode(episodeTitle);
    if (digits) {
        const epNum = parseInt(digits, 10);
        if (epNum > 0) return epNum < 10 ? `${vodName} S01E0${epNum}` : `${vodName} S01E${epNum}`;
    }
    return vodName;
}
async function matchDanmu(fileName) {
    if (!SITE_CONFIG.DANMU_API || !fileName) return [];
    try {
        const res = await axiosInstance.post(`${SITE_CONFIG.DANMU_API}/api/v2/match`, JSON.stringify({ fileName }), {
            headers: { "Content-Type": "application/json" }
        });
        if (res.status !== 200) return [];
        const matchData = safeJsonParse(res.data || '{}', {});
        if (!matchData.isMatched) return [];
        const firstMatch = (matchData.matches || [])[0];
        if (!firstMatch?.episodeId) return [];
        const danmakuURL = `${SITE_CONFIG.DANMU_API}/api/v2/comment/${firstMatch.episodeId}?format=xml`;
        return [{ name: [firstMatch.animeTitle, firstMatch.episodeTitle].filter(Boolean).join(' - ') || '弹幕', url: danmakuURL }];
    } catch (_) { return []; }
}
function extractCards(html) {
    const results = [];
    const blocks = String(html || '').match(/<div class="public-list-box[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/g) || [];
    for (const block of blocks) {
        const href = (block.match(/class="(?:public-list-exp|time-title)[^"]*"[^>]*href="([^"]+)"/) || [])[1] || '';
        const title = (block.match(/class="public-list-exp"[^>]*title="([^"]+)"/) || [])[1]
            || (block.match(/class="time-title[^"]*"[^>]*title="([^"]+)"/) || [])[1]
            || stripTags((block.match(/class="time-title[^"]*"[^>]*>([\s\S]*?)<\/a>/) || [])[1] || '');
        const pic = (block.match(/data-src="([^"]+)"/) || [])[1]
            || (block.match(/src="([^"]+)"/) || [])[1]
            || '';
        const remarks = (block.match(/<span class="public-list-prb[^>]*>([\s\S]*?)<\/span>/) || [])[1] || '';
        if (!href || !title) continue;
        results.push({
            vod_id: fullUrl(href),
            vod_name: stripTags(title),
            vod_pic: fixImg(pic),
            vod_remarks: stripTags(remarks),
        });
    }
    return results;
}
function parseHomeSlides(html) {
    const list = [];
    const reg = /<div class="swiper-slide">[\s\S]*?<div class="swiper-lazy[^"]*" data-background="([^"]+)"[\s\S]*?<a class="lank" href="([^"]+)"[\s\S]*?<h3 class="slide-info-title hide">([\s\S]*?)<\/h3>[\s\S]*?<li>([^<]*)<\/li>/g;
    let m;
    while ((m = reg.exec(String(html || ''))) !== null) {
        list.push({
            vod_id: fullUrl(m[2]),
            vod_name: stripTags(m[3]),
            vod_pic: fixImg(m[1]),
            vod_remarks: stripTags(m[4]),
        });
    }
    return list;
}
function dedupeByVodId(list) {
    const seen = new Set();
    const result = [];
    for (const item of list || []) {
        const key = item?.vod_id;
        if (!key || seen.has(key)) continue;
        seen.add(key);
        result.push(item);
    }
    return result;
}
async function request(url, options = {}) {
    try {
        const res = await axiosInstance({
            url,
            method: options.method || "get",
            headers: { ...SITE_CONFIG.headers, ...(options.headers || {}) },
            timeout: options.timeout || 15000,
            data: options.body || options.data,
            maxRedirects: options.maxRedirects ?? 5,
            validateStatus: options.validateStatus || (() => true),
        });
        return res;
    } catch (e) {
        log("❌", "请求失败", e.message);
        return null;
    }
}
async function fetchHtml(url) {
    const res = await request(url, {});
    return typeof res?.data === "string" ? res.data : "";
}
function getClasses() {
    const names = SITE_CONFIG.class_name.split("&");
    const urls = SITE_CONFIG.class_url.split("&");
    return names.map((name, index) => ({
        type_id: urls[index],
        type_name: name,
    }));
}

// ===================== 核心接口 _home / _category / _search / _detail / _play =====================
const _home = async () => {
    try {
        const { data: html } = await axiosInstance.get(SITE_CONFIG.host + '/');
        const list = dedupeByVodId([
            ...parseHomeSlides(html),
            ...extractCards(html),
        ]).slice(0, 40);
        return {
            class: getClasses(),
            filters: FILTERS,
            list,
        };
    } catch (e) {
        log("❌", "首页失败", e.message);
        return { class: getClasses(), filters: FILTERS, list: [] };
    }
};

const _category = async (id, page, filter, filters) => {
    const tid = id || '1';
    const pg = page || 1;
    const extend = filters || {};
    const body = new URLSearchParams();
    body.set('type', tid);
    body.set('page', String(pg));
    body.set('by', String(extend.by || 'time'));
    if (extend.class) body.set('class', String(extend.class));
    if (extend.area) body.set('area', String(extend.area));
    if (extend.year) body.set('year', String(extend.year));

    try {
        const { data } = await axiosInstance.post(`${SITE_CONFIG.host}/index.php/ds_api/vod`, body.toString(), {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': `${SITE_CONFIG.host}/type/${tid}.html`,
            },
        });
        const payload = typeof data === 'string' ? safeJsonParse(data, {}) : (data || {});
        const list = (payload.list || []).map((item) => ({
            vod_id: fullUrl(item.url || `/bangumi/${item.vod_id}.html`),
            vod_name: item.vod_name || '',
            vod_pic: fixImg(String(item.vod_pic || '').replace(/\\\//g, '/')),
            vod_remarks: item.vod_remarks || '',
        })).filter((item) => item.vod_id && item.vod_name);

        return {
            list,
            page: Number(payload.page || pg),
            pagecount: Number(payload.pagecount || pg),
        };
    } catch (e) {
        log("❌", "分类失败", e.message);
        return { list: [], page: pg, pagecount: pg };
    }
};

const _search = async (page, quick, wd) => {
    const pg = page || 1;
    const keyword = String(wd || '').trim();
    if (!keyword) return { list: [], page: pg, pagecount: pg, total: 0 };
    try {
        const { data } = await axiosInstance.get(`${SITE_CONFIG.host}/index.php/ajax/suggest?mid=1&wd=${encodeURIComponent(keyword)}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': `${SITE_CONFIG.host}/search/wd/${encodeURIComponent(keyword)}.html`,
            },
        });
        const payload = typeof data === 'string' ? safeJsonParse(data, {}) : (data || {});
        const list = (payload.list || []).map((item) => ({
            vod_id: fullUrl(`/bangumi/${item.id}.html`),
            vod_name: item.name || '',
            vod_pic: fixImg(item.pic || ''),
            vod_remarks: '',
        })).filter((item) => item.vod_id && item.vod_name);
        return { list, page: pg, pagecount: pg, total: list.length };
    } catch (e) {
        log("❌", "搜索失败", e.message);
        return { list: [], page: pg, pagecount: pg, total: 0 };
    }
};

const _detail = async (id) => {
    const result = { list: [] };
    const ids = Array.isArray(id) ? id : [id];
    for (const vodUrl of ids) {
        const url = fullUrl(vodUrl);
        const html = await fetchHtml(url);
        if (!html) continue;

        const title = stripTags((html.match(/<h3>([\s\S]*?)<\/h3>/i) || [])[1] || (html.match(/<title>(.*?)<\/title>/i) || [])[1] || '').replace(/\s*-\s*免费高清动漫分享.*$/i, '');
        const pic = fixImg((html.match(/<div class="detail-pic">[\s\S]*?<img[^>]+(?:data-src|src)="([^"]+)"/i) || [])[1] || '');
        const remarks = stripTags((html.match(/<span class="slide-info-remarks cor5">([\s\S]*?)<\/span>/i) || [])[1] || '');
        const year = stripTags((html.match(/<span class="slide-info-remarks"><a href="\/search\/year\/[^"]+">([\s\S]*?)<\/a>/i) || [])[1] || '');
        const area = stripTags((html.match(/<span class="slide-info-remarks"><a href="\/search\/area\/[^"]+">([\s\S]*?)<\/a>/i) || [])[1] || '');
        const director = stripTags((html.match(/导演\s*:<\/strong>([\s\S]*?)<\/div>/i) || [])[1] || '');
        const actor = stripTags((html.match(/演员\s*:<\/strong>([\s\S]*?)<\/div>/i) || [])[1] || '');
        const content = stripTags((html.match(/<div id="height_limit" class="text cor3">([\s\S]*?)<\/div>/i) || [])[1] || '');

        const tabNames = [];
        const tabReg = /<a class="swiper-slide">[\s\S]*?&nbsp;([^<]+)<span class="badge">(\d+)<\/span><\/a>/g;
        let tabMatch;
        while ((tabMatch = tabReg.exec(html)) !== null) {
            tabNames.push(stripTags(tabMatch[1]));
        }

        const vodPlaySources = [];
        const anthBlockMatch = html.match(/<div class="anthology-list[\s\S]*?<script>\$\("\.anthology-tab a"\)\.eq\(0\)/);
        const anthBlock = anthBlockMatch ? anthBlockMatch[0] : html;
        const boxReg = /<div class="anthology-list-box[^>]*>[\s\S]*?<ul class="anthology-list-play size">([\s\S]*?)<\/ul>[\s\S]*?<\/div>\s*<\/div>/g;
        let boxMatch;
        let lineIndex = 0;
        while ((boxMatch = boxReg.exec(anthBlock)) !== null) {
            const episodes = [];
            const epReg = /<a class="[^"]*" href="([^"]*\/watch[^"]+)"[^>]*>\s*(?:<span>)?([^<]+)(?:<\/span>)?\s*<\/a>/g;
            let epMatch;
            while ((epMatch = epReg.exec(boxMatch[1])) !== null) {
                const playUrl = epMatch[1];
                const epName = stripTags(epMatch[2]);
                if (!playUrl.includes('/watch/')) continue;
                episodes.push(`${epName}$${fullUrl(playUrl)}`);
            }
            if (episodes.length) {
                vodPlaySources.push({
                    name: tabNames[lineIndex] || `线路${lineIndex + 1}`,
                    eps: episodes.join("#")
                });
            }
            lineIndex += 1;
        }

        if (!vodPlaySources.length) {
            const fallbackEpisodes = [];
            const epReg = /href="([^"]*\/watch[^"]+)"[^>]*>\s*(?:<span>)?([^<]+)(?:<\/span>)?\s*<\/a>/g;
            let epMatch;
            while ((epMatch = epReg.exec(html)) !== null) {
                const playUrl = epMatch[1];
                if (!playUrl.includes('/watch/')) continue;
                fallbackEpisodes.push(`${stripTags(epMatch[2])}$${fullUrl(playUrl)}`);
            }
            if (fallbackEpisodes.length) {
                vodPlaySources.push({ name: '默认', eps: fallbackEpisodes.join("#") });
            }
        }

        const vod_play_from = vodPlaySources.map(i => i.name).join("$$$");
        const vod_play_url = vodPlaySources.map(i => i.eps).join("$$$");

        result.list.push({
            vod_id: vodUrl,
            vod_name: title,
            vod_pic: pic,
            vod_remarks: remarks,
            vod_year: year,
            vod_area: area,
            vod_director: director,
            vod_actor: actor,
            vod_content: content,
            vod_play_from,
            vod_play_url,
        });
    }
    return result;
};

const _play = async (flag, id) => {
    const playPath = pickParamValue(id);
    const url = fullUrl(playPath);
    if (!url) return { parse: 0, url: "", header: SITE_CONFIG.headers };

    try {
        const { data: html } = await axiosInstance.get(url, {
            headers: {
                'User-Agent': SITE_CONFIG.headers["User-Agent"],
                'Referer': url,
                'Origin': SITE_CONFIG.host,
            },
        });
        const playerMatch = html.match(/var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})<\/script>/i);
        if (!playerMatch) throw new Error('player_aaaa not found');
        const player = safeJsonParse(playerMatch[1], {});

        let playUrl = String(player.url || '').replace(/\\\//g, '/');
        if (Number(player.encrypt) === 2) playUrl = decodePlayerUrl(playUrl);
        else if (Number(player.encrypt) === 1) playUrl = decodeURIComponent(playUrl);
        if (!/^https?:\/\//i.test(playUrl)) playUrl = fullUrl(playUrl);

        const parse = /\.(m3u8|mp4|m4a|mp3)(\?|$)/i.test(playUrl) ? 0 : 1;
        const vodName = player?.vod_data?.vod_name || '';
        const episodeName = stripTags((html.match(/<li class="bj3 border on[\s\S]*?<span>([^<]+)<\/span>/i) || [])[1] || '');
        const danmu = [];
        if (SITE_CONFIG.DANMU_API && vodName) {
            const fileName = buildFileNameForDanmu(vodName, episodeName);
            if (fileName) danmu.push(...await matchDanmu(fileName));
        }

        return {
            parse,
            url: playUrl,
            header: {
                'User-Agent': SITE_CONFIG.headers["User-Agent"],
                'Referer': url,
                'Origin': SITE_CONFIG.host,
            },
            danmu,
        };
    } catch (e) {
        log("❌", "播放解析失败", e.message);
        return { parse: 0, url: "", header: SITE_CONFIG.headers };
    }
};

// ===================== 路由 & Meta 配置 =====================
const meta = {
    key: "xifanacg",
    name: SITE_CONFIG.title,
    type: 1,
    api: "/video/xifanacg",
    searchable: SITE_CONFIG.searchable,
    quickSearch: SITE_CONFIG.quickSearch,
    changeable: 0,
    filterable: SITE_CONFIG.filterable,
};

module.exports = async (app, opt) => {
    const fastifyLog = app?.log?.info?.bind(app?.log);
    log = SITE_CONFIG.debug
        ? (...args) => {
            const msg = args.map((a) => typeof a === "object" ? JSON.stringify(a) : String(a)).join(" ");
            (fastifyLog || console.log)(msg);
        }
        : () => {};

    app.get(meta.api, async (req) => {
        const { ac, pg, ext, ids, flag, play, wd, quick, t } = req.query;
        try {
            if (play) return await _play(flag || "", play);
            if (wd) return await _search(parseInt(pg || "1", 10), quick || false, wd);
            if (!ac) return await _home();
            if (ac === "detail") {
                if (t) {
                    let filters = {};
                    if (ext) {
                        try {
                            filters = JSON.parse(CryptoJS.enc.Base64.parse(ext).toString(CryptoJS.enc.Utf8));
                        } catch (e) { }
                    }
                    return await _category(t, parseInt(pg || "1", 10), true, filters);
                }
                if (ids) return await _detail(ids.split(",").map((s) => s.trim()).filter(Boolean));
            }
        } catch (e) {
            log("❌", "API错误", e.message);
            return { error: e.message };
        }
        return req.query;
    });

    app.get(`${meta.api}/proxy`, async (req) => {
        return { ...req.query, ...req.params };
    });

    opt.sites.push(meta);
};
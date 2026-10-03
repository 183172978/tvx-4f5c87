import { Crypto, _ } from 'assets://js/lib/cat.js';
let siteKey = '';
let siteType = 0;
let extendObj = {};

// type: 1 = 标准 provide/vod JSON（默认）
// type: 3 = 大地 feifei2 特殊格式（data/vod_url/vod_play/list分类）
const SOURCES = {
    's1': { 'name': '🎬香蕉', 'api': 'https://www.xiangjiaozyw.com/api.php/provide/vod/' },
    's2': { 'name': '💧番茄', 'api': 'http://fhapi9.com/api.php/provide/vod/' },
    's3': { 'name': '🧸嘿嘿', 'api': 'https://api.heiapi.cc/api.php/provide/vod/' },
    's4': { 'name': '📺鲨鱼', 'api': 'https://shayuzy5.com/api.php/provide/vod/' },
    's5': { 'name': '🔥麻花', 'api': 'https://19q.cc/api.php/provide/vod/' },
    's6': { 'name': '📺搜AV', 'api': 'https://souavzy.net/api.php/provide/vod/' },
    's7': { 'name': '📺精品', 'api': 'https://www.jingpinx.com/api.php/provide/vod/' },
    's8': { 'name': '⚡极品', 'api': 'https://jipinvip1.com/api.php/provide/vod/' },
    's9': { 'name': '📺美少女', 'api': 'https://www.msnii.com/api/json.php' },
    's10': { 'name': '📺饮水机', 'api': 'https://www.xrbsp.com/api/json.php' },
    's11': { 'name': '📺香奶儿', 'api': 'https://www.gdlsp.com/api/json.php' },
    's12': { 'name': '🐯白嫖', 'api': 'https://www.kxgav.com/api/json.php' },
    's13': { 'name': '📺小师妹', 'api': 'https://www.afasu.com/api/json.php' },
    's14': { 'name': '📺潢AV', 'api': 'https://www.pgxdy.com/api/json.php' },
    's15': { 'name': '📺杏吧', 'api': 'https://api.xgbbk8.com/api.php/provide/vod/' },
    's16': { 'name': '📺CK资源', 'api': 'https://ckzy.me/api.php/provide/vod' },
    's17': { 'name': '📺越南', 'api': 'https://vnzyz.com/api.php/provide/vod' },
    's18': { 'name': '📺15', 'api': 'https://155api.com/api.php/provide/vod/' },
    's19': { 'name': '📺91AV', 'api': 'https://91av.cyou/api.php/provide/vod/' },
    's20': { 'name': '🌕红楼', 'api': 'https://www.hlzyapi.vip/api.php/provide/vod/' },
    's21': { 'name': '📺小鸡', 'api': 'https://api.xiaojizy.live/provide/vod/' },
    's22': { 'name': '📺大奶', 'api': 'https://apidanaizi.com/api.php/provide/vod/' },
    's23': { 'name': '📺豆豆', 'api': 'https://api.douapi.cc/api.php/provide/vod/' },
    's24': { 'name': '📺黑料', 'api': 'https://heiliaozyapi.com/api.php/provide/vod/' },
    's25': { 'name': '🌸仓库', 'api': 'https://hsckzy888.com/api.php/provide/vod/' },
    's26': { 'name': '🐮玉兔', 'api': 'https://apiyutu.com/api.php/provide/vod' },
    's27': { 'name': '☁️精东', 'api': 'http://chujia.cc/api.php/provide/vod/' },
    's28': { 'name': '🏎奶香', 'api': 'https://naixxzy.com/api.php/provide/vod' },
    's29': { 'name': '🦅乐播', 'api': 'https://lbapi9.com/api.php/provide/vod' },
    's30': { 'name': '⚡JKUN', 'api': 'https://jkunzyapi.com/api.php/provide/vod' },
    's31': { 'name': '👑桃花', 'api': 'https://thzy1.me/api.php/provide/vod/' },
    's32': { 'name': '🍃百花', 'api': 'https://bhziyuan.com/api.php/provide/vod/' },
    's33': { 'name': '🐾老色', 'api': 'https://apilsbzy1.com/api.php/provide/vod/' },
    's34': { 'name': '🐾辣椒', 'api': 'https://apilj.com/api.php/provide/vod' },
    's35': { 'name': '🐾javbus', 'api': 'https://javbus.sbs/api.php/provide/vod/' },
    's36': { 'name': '🐾奥斯卡', 'api': 'https://aosikazy8.com/api.php/provide/vod' },
    's37': { 'name': '🐾火速', 'api': 'https://api.huosuapi.cc/api.php/provide/vod/' },
    's38': { 'name': '🐾聚合2', 'api': 'http://150.109.94.44:1112/api.php/provide/vod/' },
    's39': { 'name': '🐾CK百货', 'api': 'https://ckbh1.xyz/api.php/provide/vod/' },
    's40': { 'name': '🐾番茄', 'api': 'https://fqzy.me/api.php/provide/vod/' },
    's41': { 'name': '🐾98', 'api': 'https://jp98.vip/api.php/provide/vod/' },
    's42': { 'name': '🐾森林', 'api': 'https://slapibf.com/api.php/provide/vod/' },
    // 大地 feifei2 特殊 JSON
    's43': { 'name': '🐾大地', 'api': 'https://dadiapi.com/feifei2/', 'type': 3 },
    's44': { 'name': '🐾色猫', 'api': 'https://caiji.semaozy.net/inc/apijson_vod.php' },
    's45': { 'name': '🐾滴滴', 'api': 'https://api.ddapi.cc/api.php/provide/vod/' },
    's46': { 'name': '🐾91', 'api': 'https://91md.me/api.php/provide/vod/' },
    's47': { 'name': '🐾免费', 'api': 'https://yuanlib.com/api.php/provide/vod/' },
    's48': { 'name': '🐾细胞', 'api': 'https://www.xxibaozyw.com/api.php/provide/vod/' },
    's49': { 'name': '📺湿园', 'api': 'https://xxavs.com/api.php/provide/vod' }
};

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
const DEFAULT_HEADERS = { "User-Agent": UA };

function text(v) {
    return String(v == null ? "" : v).trim();
}

function buildUrl(base, params = {}) {
    let url = text(base);
    // 去掉末尾多余空格/引号
    url = url.replace(/^["'\s]+|["'\s]+$/g, '');
    const keys = Object.keys(params).filter(k => params[k] !== undefined && params[k] !== null && String(params[k]) !== '');
    if (keys.length === 0) return url;
    const qs = keys.map(k => `${encodeURIComponent(k)}=${encodeURIComponent(String(params[k]))}`).join('&');
    return url.includes('?') ? `${url}&${qs}` : `${url}?${qs}`;
}

async function request(url, optHeaders = {}, body) {
    try {
        const headers = Object.assign({}, DEFAULT_HEADERS, optHeaders || {});
        const res = await req(url, {
            method: body ? "POST" : "GET",
            headers: headers,
            timeout: 10000,
            data: body
        });
        return res?.content ?? "";
    } catch (e) {
        console.error("request error:", url, e?.message);
        return "";
    }
}

function safeJson(str) {
    try {
        if (!str) return null;
        return JSON.parse(str);
    } catch (e) {
        return null;
    }
}

function fixPicUrl(url) {
    url = text(url);
    if (!url) return "";
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    return "";
}

function isDirectPlayUrl(url) {
    const u = text(url).toLowerCase();
    if (!u) return false;
    if (u.includes('.m3u8') || u.includes('.mp4') || u.includes('.flv') || u.includes('.mkv')) return true;
    return false;
}

// 字段归一：兼容大地 vod_play/vod_url 等别名
function normalizeVod(item) {
    if (!item || typeof item !== 'object') return item;
    const o = Object.assign({}, item);
    if (!o.vod_play_from && o.vod_play) o.vod_play_from = o.vod_play;
    if (!o.vod_play_url && o.vod_url) o.vod_play_url = o.vod_url;
    if (!o.vod_id && o.id) o.vod_id = o.id;
    if (!o.vod_name && o.name) o.vod_name = o.name;
    if (!o.vod_name && o.title) o.vod_name = o.title;
    if (!o.vod_pic && o.pic) o.vod_pic = o.pic;
    if (!o.vod_remarks && o.remarks) o.vod_remarks = o.remarks;
    if (!o.vod_remarks && o.note) o.vod_remarks = o.note;
    if (!o.vod_remarks && o.vod_continu) o.vod_remarks = o.vod_continu;
    if (!o.vod_content && o.content) o.vod_content = o.content;
    if (!o.vod_year && o.d_year) o.vod_year = o.d_year;
    if (!o.type_name && o.list_name) o.type_name = o.list_name;
    o.vod_pic = fixPicUrl(o.vod_pic);
    return o;
}

// 统一解析：标准 MacCMS JSON + 大地 feifei2
function parseResponse(html) {
    if (!html) return { list: [], page: 1, pagecount: 1, pagesize: 20, total: 0, class: [] };
    const json = safeJson(html);
    if (!json) return { list: [], page: 1, pagecount: 1, pagesize: 20, total: 0, class: [] };

    // ----- 大地 feifei2: status + data[] + list[]分类 + page对象 -----
    if (json.status !== undefined && (Array.isArray(json.data) || json.page)) {
        const pageObj = json.page || {};
        let classes = [];
        if (Array.isArray(json.list) && json.list.length > 0) {
            const first = json.list[0];
            if (first && (first.list_id !== undefined || first.list_name)) {
                classes = json.list.map(c => ({
                    type_id: text(c.list_id || c.type_id || c.id),
                    type_name: text(c.list_name || c.type_name || c.name)
                }));
            }
        }
        const rawList = Array.isArray(json.data) ? json.data : [];
        return {
            list: rawList.map(normalizeVod),
            page: Number(pageObj.pageindex || pageObj.page || 1),
            pagecount: Number(pageObj.pagecount || 1),
            pagesize: Number(pageObj.pagesize || 20),
            total: Number(pageObj.recordcount || pageObj.total || rawList.length),
            class: classes
        };
    }

    // ----- 标准 provide / apijson -----
    let classes = Array.isArray(json.class) ? json.class : [];
    classes = classes.map(c => ({
        type_id: text(c.type_id || c.list_id || c.id),
        type_name: text(c.type_name || c.list_name || c.name)
    }));
    let rawList = Array.isArray(json.list) ? json.list : [];
    // 防止把分类数组当视频
    if (rawList.length > 0 && rawList[0] && rawList[0].list_id !== undefined && !rawList[0].vod_id && !rawList[0].vod_name) {
        classes = rawList.map(c => ({
            type_id: text(c.list_id || c.type_id),
            type_name: text(c.list_name || c.type_name)
        }));
        rawList = [];
    }
    return {
        list: rawList.map(normalizeVod),
        page: Number(json.page || 1),
        pagecount: Number(json.pagecount || 1),
        pagesize: Number(json.limit || json.pagesize || 20),
        total: Number(json.total || 0),
        class: classes
    };
}

function cleanItem(item, sourceKey, sourceName, isDetail = false) {
    const o = normalizeVod(Object.assign({}, item));
    if (!isDetail) {
        o.vod_id = `${sourceKey}@@${text(o.vod_id)}`;
    }
    const rem = text(o.vod_remarks || "");
    o.vod_remarks = `${sourceName} | ${rem}`;

    let fromArr = text(o.vod_play_from || "").split("$$$").map(s => s.trim()).filter(Boolean);
    let urlArr = text(o.vod_play_url || "").split("$$$").map(s => s.trim());

    if (fromArr.length > 0) {
        fromArr = fromArr.map(x => x.startsWith(sourceName) ? x : `${sourceName}-${x}`);
    }
    // 有播放地址无线路名
    if (fromArr.length === 0 && urlArr.some(u => u)) {
        fromArr = urlArr.map((_, i) => `${sourceName}-线路${i + 1}`);
    }
    // 对齐段数，避免播放列表空
    if (fromArr.length > 0 && urlArr.length > 0) {
        while (urlArr.length < fromArr.length) urlArr.push("");
        while (fromArr.length < urlArr.length) fromArr.push(`${sourceName}-线路${fromArr.length + 1}`);
    }
    o.vod_play_from = fromArr.join("$$$");
    o.vod_play_url = urlArr.join("$$$");

    delete o.vod_down_from;
    delete o.vod_down_url;
    return o;
}

async function loadSourceFilter(sourceKey, sourceObj) {
    const stype = sourceObj.type || 1;
    // 大地/标准都用 ac=list 拉分类
    const url = buildUrl(sourceObj.api, { ac: 'list' });
    const html = await request(url);
    const data = parseResponse(html);
    const vals = [{ n: "全部(最新)", v: "" }];
    if (Array.isArray(data.class) && data.class.length > 0) {
        for (const c of data.class) {
            const id = text(c.type_id);
            const name = text(c.type_name);
            if (id || name) vals.push({ n: name || id, v: id });
        }
    }
    return { sourceKey, vals };
}

async function init(cfg) {
    try {
        siteKey = cfg.skey;
        siteType = cfg.stype;
        const classes = [];
        const filters = {};
        for (const [sKey, sObj] of Object.entries(SOURCES)) {
            classes.push({
                type_id: sKey,
                type_name: sObj.name,
                land: 1,
                ratio: 1.33
            });
            try {
                const fr = await loadSourceFilter(sKey, sObj);
                filters[fr.sourceKey] = [{
                    key: "cateId",
                    name: "分类",
                    value: fr.vals
                }];
            } catch (e) {
                console.error("load filter fail", sKey, e?.message);
                filters[sKey] = [{
                    key: "cateId",
                    name: "分类",
                    value: [{ n: "全部(最新)", v: "" }]
                }];
            }
        }
        extendObj = { classes, filter: filters };
    } catch (e) {
        console.error("init error", e.message);
        extendObj = { classes: [], filter: {} };
    }
}

function home(filter) {
    try {
        return JSON.stringify({
            class: extendObj.classes || [],
            filters: extendObj.filter || {}
        });
    } catch (e) {
        return JSON.stringify({ class: [], filters: {} });
    }
}

async function homeVod() {
    return JSON.stringify({ list: [] });
}

async function category(tid, pg, filter, ext) {
    pg = Number(pg) || 1;
    try {
        const sourceObj = SOURCES[tid];
        if (!sourceObj) return JSON.stringify({ list: [], page: pg, pagecount: 0 });
        const cateId = ext?.cateId ? text(ext.cateId) : "";
        const stype = sourceObj.type || 1;

        let url;
        if (stype === 3) {
            // 大地：videolist 才有封面和播放地址
            const params = { ac: 'videolist', pg: pg };
            if (cateId) params.t = cateId;
            url = buildUrl(sourceObj.api, params);
        } else {
            // 标准：优先 detail，部分源 list 也可
            const params = { ac: 'detail', pg: pg };
            if (cateId) params.t = cateId;
            url = buildUrl(sourceObj.api, params);
        }

        let html = await request(url);
        let data = parseResponse(html);

        // 标准源 detail 为空时，尝试 videolist
        if (stype !== 3 && (!data.list || data.list.length === 0)) {
            const params2 = { ac: 'videolist', pg: pg };
            if (cateId) params2.t = cateId;
            const html2 = await request(buildUrl(sourceObj.api, params2));
            const data2 = parseResponse(html2);
            if (data2.list && data2.list.length > 0) data = data2;
        }

        const rawList = Array.isArray(data.list) ? data.list : [];
        const outList = [];
        for (const it of rawList) {
            const cleaned = cleanItem(it, tid, sourceObj.name, false);
            cleaned.vod_pic = fixPicUrl(cleaned.vod_pic);
            cleaned.style = { type: 'rect', ratio: 1.33 };
            outList.push(cleaned);
        }
        return JSON.stringify({
            list: outList,
            page: Number(data.page || pg),
            pagecount: Number(data.pagecount || 1),
            limit: Number(data.pagesize || 20),
            total: Number(data.total || outList.length)
        });
    } catch (e) {
        console.error("category error", e.message);
        return JSON.stringify({ list: [], page: pg, pagecount: 0 });
    }
}

async function searchOne(sourceKey, sourceObj, keyword, pg) {
    const stype = sourceObj.type || 1;
    let url;
    if (stype === 3) {
        url = buildUrl(sourceObj.api, { ac: 'videolist', wd: keyword, pg: pg });
    } else {
        url = buildUrl(sourceObj.api, { ac: 'detail', wd: keyword, pg: pg });
    }
    let html = await request(url);
    let data = parseResponse(html);
    if (stype !== 3 && (!data.list || data.list.length === 0)) {
        const html2 = await request(buildUrl(sourceObj.api, { ac: 'videolist', wd: keyword, pg: pg }));
        const data2 = parseResponse(html2);
        if (data2.list && data2.list.length > 0) data = data2;
    }
    const rawList = Array.isArray(data.list) ? data.list : [];
    const out = [];
    for (const it of rawList) {
        const cleaned = cleanItem(it, sourceKey, sourceObj.name, false);
        cleaned.vod_pic = fixPicUrl(cleaned.vod_pic);
        cleaned.style = { type: 'rect', ratio: 1.33 };
        out.push(cleaned);
    }
    return { list: out, pagecount: Number(data.pagecount || 1) };
}

async function search(key, quick, pg) {
    pg = Number(pg) || 1;
    try {
        let resultList = [];
        let maxPage = 1;
        for (const [sKey, sObj] of Object.entries(SOURCES)) {
            try {
                const res = await searchOne(sKey, sObj, key, pg);
                resultList.push(...res.list);
                if (res.pagecount > maxPage) maxPage = res.pagecount;
            } catch (err) {
                console.error("search skip source", sKey, err.message);
            }
        }
        return JSON.stringify({
            list: resultList,
            page: pg,
            pagecount: maxPage,
            limit: 40,
            total: 9999,
            land: 1,
            ratio: 1.33
        });
    } catch (e) {
        console.error("search error", e.message);
        return JSON.stringify({ list: [], page: pg, pagecount: 0, land: 1, ratio: 1.33 });
    }
}

async function detail(vodIdRaw) {
    try {
        if (!vodIdRaw.includes("@@")) return JSON.stringify({ list: [] });
        const [sourceKey, realVodId] = vodIdRaw.split("@@", 2);
        const sourceObj = SOURCES[sourceKey];
        if (!sourceObj) return JSON.stringify({ list: [] });
        const stype = sourceObj.type || 1;

        let html = "";
        if (stype === 3) {
            // 大地：必须 videolist&ids= 才有 vod_url
            html = await request(buildUrl(sourceObj.api, { ac: 'videolist', ids: realVodId }));
            const tmp = parseResponse(html);
            const first = (tmp.list || [])[0];
            if (!first || !text(first.vod_play_url || first.vod_url)) {
                const html2 = await request(buildUrl(sourceObj.api, { ac: 'detail', ids: realVodId }));
                if (html2) html = html2;
            }
        } else {
            html = await request(buildUrl(sourceObj.api, { ac: 'detail', ids: realVodId }));
            const tmp = parseResponse(html);
            const first = (tmp.list || [])[0];
            if (!first || !text(first.vod_play_url)) {
                const html2 = await request(buildUrl(sourceObj.api, { ac: 'videolist', ids: realVodId }));
                const d2 = parseResponse(html2);
                if ((d2.list || [])[0] && text((d2.list[0].vod_play_url || ''))) {
                    html = html2;
                }
            }
        }

        const data = parseResponse(html);
        const rawList = Array.isArray(data.list) ? data.list : [];
        const outList = [];
        for (const it of rawList) {
            const cleaned = cleanItem(it, sourceKey, sourceObj.name, true);
            cleaned.vod_id = vodIdRaw;
            cleaned.vod_pic = fixPicUrl(cleaned.vod_pic);
            if (!text(cleaned.vod_play_from) && text(cleaned.vod_play_url)) {
                const segs = text(cleaned.vod_play_url).split("$$$");
                cleaned.vod_play_from = segs.map((_, i) => `${sourceObj.name}-线路${i + 1}`).join("$$$");
            }
            outList.push(cleaned);
        }
        return JSON.stringify({ list: outList });
    } catch (e) {
        console.error("detail error", e.message);
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, id, flags) {
    try {
        const playUrl = text(id);
        const needParse = !isDirectPlayUrl(playUrl);
        return JSON.stringify({
            parse: needParse ? 1 : 0,
            url: playUrl,
            header: { "User-Agent": UA }
        });
    } catch (e) {
        console.error("play error", e.message);
        return JSON.stringify({ parse: 1, url: id, header: { "User-Agent": UA } });
    }
}

export function __jsEvalReturn() {
    return {
        init,
        home,
        homeVod,
        category,
        detail,
        search,
        play
    };
}

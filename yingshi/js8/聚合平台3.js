import { Crypto, _ } from 'assets://js/lib/cat.js';
let siteKey = '';
let siteType = 0;
let extendObj = {};

// type: 0 = XML旧版MacCMS
// type: 1 = JSON标准 provide/vod (默认)
// type: 2 = 荐片/可视/泥视频/枫林/偶尔 代理源
// type: 3 = 大地 feifei2 特殊JSON (data/vod_url/vod_play/list分类)
const SOURCES = {
    's1': { 'name': '🎬电影天堂', 'api': 'http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/json' },
    's2': { 'name': '💧无水印', 'api': 'https://api.wsyzy.net/api.php/provide/vod' },
    's3': { 'name': '🧸量子', 'api': 'https://cj.lziapi.com/api.php/provide/vod' },
    's4': { 'name': '📺1080资源', 'api': 'https://api.yyzy-tv.vip/inc/apijson.php' },
    's5': { 'name': '🔥大众资源', 'api': 'https://cdn.dzzyapi.com/api.php/provide/vod/' },
    's6': { 'name': '📺天涯', 'api': 'https://tyyszy.com/api.php/provide/vod' },
    's7': { 'name': '📺暴风', 'api': 'https://bfzyapi.com/api.php/provide/vod' },
    's8': { 'name': '⚡闪电', 'api': 'https://xsd.sdzyapi.com/api.php/provide/vod' },
    's9': { 'name': '📺索尼', 'api': 'https://suoniapi.com/api.php/provide/vod' },
    's10': { 'name': '📺红牛', 'api': 'https://www.hongniuzy2.com/api.php/provide/vod' },
    's11': { 'name': '📺茅台', 'api': 'https://caiji.maotaizy.cc/api.php/provide/vod' },
    's12': { 'name': '🐯虎牙', 'api': 'https://www.huyaapi.com/api.php/provide/vod' },
    's13': { 'name': '📺猫眼', 'api': 'https://api.maoyanapi.top/api.php/provide/vod/' },
    's14': { 'name': '📺豆瓣', 'api': 'https://dbzy.tv/api.php/provide/vod' },
    's15': { 'name': '📺豪华', 'api': 'https://hhzyapi.com/api.php/provide/vod' },
    's16': { 'name': '📺CK资源', 'api': 'https://ckzy.me/api.php/provide/vod' },
    's17': { 'name': '📺U酷', 'api': 'https://api.ukuapi88.com/api.php/provide/vod' },
    's18': { 'name': '📺ikun', 'api': 'https://ikunzyapi.com/api.php/provide/vod' },
    's19': { 'name': '📺无尽', 'api': 'https://api.wujinapi.cc/api.php/provide/vod' },
    's20': { 'name': '🌕光速', 'api': 'https://api.guangsuapi.com/api.php/provide/vod' },
    's21': { 'name': '📺西瓜', 'api': 'https://caiji.xgzyapi.com/api.php/provide/vod/' },
    's22': { 'name': '📺新浪', 'api': 'https://api.xinlangapi.com/xinlangapi.php/provide/vod' },
    's23': { 'name': '📺旺旺', 'api': 'https://zhangqun66.xyz/ww.php' },
    's24': { 'name': '📺最大', 'api': 'https://api.zuidapi.com/api.php/provide/vod' },
    's25': { 'name': '🌸樱花', 'api': 'https://m3u8.apiyhzy.com/api.php/provide/vod' },
    's26': { 'name': '🐮牛牛', 'api': 'https://api.niuniuzy.me/api.php/provide/vod' },
    's27': { 'name': '☁️百度云', 'api': 'https://api.apibdzy.com/api.php/provide/vod' },
    's28': { 'name': '🏎速播', 'api': 'https://subocaiji.com/api.php/provide/vod' },
    's29': { 'name': '🦅金鹰', 'api': 'https://jyzyapi.com/provide/vod/' },
    's30': { 'name': '⚡闪电', 'api': 'https://sdzyapi.com/api.php/provide/vod' },
    's31': { 'name': '👑非凡', 'api': 'https://cj.ffzyapi.com/api.php/provide/vod' },
    's32': { 'name': '🍃飘零', 'api': 'https://p2100.net/api.php/provide/vod' },
    's33': { 'name': '🐾360', 'api': 'https://360zyzz.com/api.php/provide/vod/' },
    's34': { 'name': '🐾淘片', 'api': 'https://taopianapi.com/cjapi/mc/vod/json.html' },
    's35': { 'name': '🐾快车', 'api': 'https://caiji.kuaichezy.org/api.php/provide/vod/' },
    's36': { 'name': '🐾奇异', 'api': 'https://iqiyizyapi.com/api.php/provide/vod/' },
    's37': { 'name': '🐾鸭鸭', 'api': 'https://cj.yayazy.net/api.php/provide/vod/' },
    's38': { 'name': '🐾极速', 'api': 'https://jszyapi.com/api.php/provide/vod/' },
    's39': { 'name': '🐾如意', 'api': 'https://cj.rycjapi.com/api.php/provide/vod/' },
    's40': { 'name': '🐾火狐', 'api': 'https://hhzyapi.com/api.php/provide/vod/' },
    's41': { 'name': '🐾刺桐', 'api': 'http://pg.cttv.vip/api.php/provide/vod/' },
    's42': { 'name': '🐾巨量', 'api': 'https://api.juliang.live/api/provide/vod/' },
    's43': { 'name': '🐾荐片', 'api': 'http://192.129.140.23:5757/api/荐片[优]?pwd=dzyyds', 'type': 2 },
    's44': { 'name': '🐾tvbx', 'api': 'https://dy.7772888.xyz/api.php/tvbox', 'type': 1 },
    's45': { 'name': '📺魔都', 'api': 'https://www.mdzyapi.com/api.php/provide/vod' }
    
};

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
const DEFAULT_HEADERS = { "User-Agent": UA };

function text(v) {
    return String(v == null ? "" : v).trim();
}

function encodePath(url) {
    try {
        const m = url.match(/^(https?:\/\/[^\/]+)(\/[^?]*)?(\?.*)?$/i);
        if (!m) return encodeURI(url);
        const origin = m[1];
        const path = m[2] || '';
        const query = m[3] || '';
        const encodedPath = path.split('/').map(seg => {
            if (!seg) return '';
            try {
                if (decodeURIComponent(seg) !== seg) return seg;
            } catch (e) {}
            return encodeURIComponent(seg);
        }).join('/');
        return origin + encodedPath + query;
    } catch (e) {
        return encodeURI(url);
    }
}

function buildUrl(base, params = {}) {
    let url = encodePath(text(base));
    const keys = Object.keys(params).filter(k => params[k] !== undefined && params[k] !== null && String(params[k]) !== '');
    if (keys.length === 0) return url;
    const qs = keys.map(k => `${encodeURIComponent(k)}=${encodeURIComponent(String(params[k]))}`).join('&');
    return url.includes('?') ? `${url}&${qs}` : `${url}?${qs}`;
}

async function request(url, optHeaders = {}, body) {
    try {
        const headers = Object.assign({}, DEFAULT_HEADERS, optHeaders || {});
        const finalUrl = encodePath(url);
        const res = await req(finalUrl, {
            method: body ? "POST" : "GET",
            headers: headers,
            timeout: 12000,
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
        // 巨量等源 vod_id 为雪花ID，超过 Number.MAX_SAFE_INTEGER，直接 JSON.parse 会丢精度
        // 把超大整数字段强制变成字符串再解析
        let s = String(str);
        s = s.replace(/"(vod_id|id|type_id|list_id|vodId)"\s*:\s*(\d{16,})/g, '"$1":"$2"');
        return JSON.parse(s);
    } catch (e) {
        try {
            return JSON.parse(str);
        } catch (e2) {
            return null;
        }
    }
}

function fixPicUrl(url) {
    url = text(url);
    if (!url) return "";
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    return "";
}

function extractCDATA(str) {
    if (!str) return "";
    const m = str.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
    return m ? m[1].trim() : str.replace(/<[^>]+>/g, '').trim();
}

function isDirectPlayUrl(url) {
    const u = text(url).toLowerCase();
    if (!u) return false;
    if (u.includes('.m3u8') || u.includes('.mp4') || u.includes('.flv') || u.includes('.mkv')) return true;
    if (u.startsWith('magnet:') || u.startsWith('ed2k:')) return true;
    return false;
}

function normalizeVod(item) {
    if (!item || typeof item !== 'object') return item;
    const o = Object.assign({}, item);
    if (!o.vod_play_from && o.vod_play) o.vod_play_from = o.vod_play;
    if (!o.vod_play_url && o.vod_url) o.vod_play_url = o.vod_url;
    if (!o.vod_id && o.id) o.vod_id = o.id;
    if (!o.vod_name && o.name) o.vod_name = o.name;
    if (!o.vod_name && o.title) o.vod_name = o.title;
    if (!o.vod_pic && o.pic) o.vod_pic = o.pic;
    if (!o.vod_pic && o.cover) o.vod_pic = o.cover;
    if (!o.vod_remarks && o.remarks) o.vod_remarks = o.remarks;
    if (!o.vod_remarks && o.note) o.vod_remarks = o.note;
    if (!o.vod_remarks && o.vod_continu) o.vod_remarks = o.vod_continu;
    if (!o.vod_content && o.content) o.vod_content = o.content;
    if (!o.vod_content && o.des) o.vod_content = o.des;
    if (!o.vod_actor && o.actor) o.vod_actor = o.actor;
    if (!o.vod_director && o.director) o.vod_director = o.director;
    if (!o.vod_year && o.year) o.vod_year = o.year;
    if (!o.vod_year && o.d_year) o.vod_year = o.d_year;
    if (!o.vod_area && o.area) o.vod_area = o.area;
    if (!o.type_name && o.list_name) o.type_name = o.list_name;
    if (!o.type_name && o.type) o.type_name = o.type;
    o.vod_pic = fixPicUrl(o.vod_pic);
    return o;
}

function parseXmlList(html) {
    if (!html || (!html.includes("<rss") && !html.includes("<video>"))) {
        return { list: [], page: 1, pagecount: 1, pagesize: 20, total: 0, class: [] };
    }
    let page = 1, pagecount = 1, pagesize = 20, total = 0;
    const listMatch = html.match(/<list\s+[^>]*>/i);
    if (listMatch) {
        const attrs = listMatch[0];
        const p = attrs.match(/page="(\d+)"/i); if (p) page = Number(p[1]) || 1;
        const pc = attrs.match(/pagecount="(\d+)"/i); if (pc) pagecount = Number(pc[1]) || 1;
        const ps = attrs.match(/pagesize="(\d+)"/i); if (ps) pagesize = Number(ps[1]) || 20;
        const rc = attrs.match(/recordcount="(\d+)"/i); if (rc) total = Number(rc[1]) || 0;
    }
    const classes = [];
    const classBlock = html.match(/<class>([\s\S]*?)<\/class>/i);
    if (classBlock) {
        const tyRegex = /<ty\s+id=["']?(\d+)["']?>([^<]+)<\/ty>/gi;
        let m;
        while ((m = tyRegex.exec(classBlock[1])) !== null) {
            classes.push({ type_id: m[1], type_name: m[2].trim() });
        }
    }
    const list = [];
    const videoRegex = /<video>([\s\S]*?)<\/video>/gi;
    let vm;
    while ((vm = videoRegex.exec(html)) !== null) {
        const v = vm[1];
        const get = (tag) => {
            const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
            const m = v.match(re);
            return m ? extractCDATA(m[1]) : "";
        };
        const id = get("id");
        const name = get("name");
        if (!id || !name) continue;
        const dt = get("dt");
        let playFrom = [];
        let playUrl = [];
        const dlMatch = v.match(/<dl>([\s\S]*?)<\/dl>/i);
        if (dlMatch) {
            const ddRegex = /<dd[^>]*?(?:flag=["']([^"']+)["']|flag=([^\s>]+))[^>]*>([\s\S]*?)<\/dd>/gi;
            let dm;
            while ((dm = ddRegex.exec(dlMatch[1])) !== null) {
                const flag = text(dm[1] || dm[2] || dt || "播放");
                const content = extractCDATA(dm[3] || "");
                if (content) {
                    playFrom.push(flag);
                    playUrl.push(content);
                }
            }
        }
        if (playFrom.length === 0 && dt) {
            playFrom.push(dt);
            playUrl.push("");
        }
        list.push(normalizeVod({
            vod_id: id,
            vod_name: name,
            vod_pic: get("pic"),
            vod_remarks: get("note") || get("type") || "",
            vod_year: get("year"),
            vod_area: get("area"),
            vod_lang: get("lang"),
            vod_state: get("state"),
            vod_actor: get("actor"),
            vod_director: get("director"),
            vod_content: get("des"),
            vod_play_from: playFrom.join("$$$"),
            vod_play_url: playUrl.join("$$$"),
            type_name: get("type")
        }));
    }
    return { list, page, pagecount, pagesize, total, class: classes };
}

function parseResponse(html) {
    if (!html) return { list: [], page: 1, pagecount: 1, pagesize: 20, total: 0, class: [], filters: {} };
    const json = safeJson(html);
    if (json) {
        // 大地 feifei2: status + data[] + list[]分类 + page对象
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
                class: classes,
                filters: {}
            };
        }
        // 标准 / 代理格式
        if (Array.isArray(json.list) || Array.isArray(json.class) || json.filters) {
            const rawList = Array.isArray(json.list) ? json.list : [];
            let list = rawList;
            let classes = Array.isArray(json.class) ? json.class : [];
            if (rawList.length > 0 && rawList[0] && rawList[0].list_id !== undefined && !rawList[0].vod_id && !rawList[0].vod_name) {
                classes = rawList.map(c => ({
                    type_id: text(c.list_id || c.type_id),
                    type_name: text(c.list_name || c.type_name)
                }));
                list = [];
            } else {
                list = rawList.map(normalizeVod);
            }
            classes = (classes || []).map(c => ({
                type_id: text(c.type_id || c.list_id || c.id),
                type_name: text(c.type_name || c.list_name || c.name)
            }));
            return {
                list,
                page: Number(json.page || 1),
                pagecount: Number(json.pagecount || 1),
                pagesize: Number(json.limit || json.pagesize || 20),
                total: Number(json.total || 0),
                class: classes,
                filters: json.filters || {}
            };
        }
    }
    return parseXmlList(html);
}

function cleanItem(item, sourceKey, sourceName, isDetail = false) {
    const o = normalizeVod(Object.assign({}, item));
    // 始终字符串化，避免大整数精度丢失
    o.vod_id = text(o.vod_id);
    if (!isDetail) {
        o.vod_id = `${sourceKey}@@${o.vod_id}`;
    }
    const rem = text(o.vod_remarks || "");
    o.vod_remarks = `${sourceName} | ${rem}`;

    let fromArr = text(o.vod_play_from || "").split("$$$").map(s => s.trim()).filter(Boolean);
    let urlArr = text(o.vod_play_url || "").split("$$$").map(s => s.trim());

    if (fromArr.length > 0) {
        fromArr = fromArr.map(x => x.startsWith(sourceName) ? x : `${sourceName}-${x}`);
    }
    if (fromArr.length === 0 && urlArr.some(u => u)) {
        fromArr = urlArr.map((_, i) => `${sourceName}-线路${i + 1}`);
    }
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
    let url;
    if (stype === 2) {
        url = buildUrl(sourceObj.api, {});
    } else {
        url = buildUrl(sourceObj.api, { ac: 'list' });
    }
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
    return { sourceKey, vals, firstCate: vals.length > 1 ? vals[1].v : "" };
}

async function init(cfg) {
    try {
        siteKey = cfg.skey;
        siteType = cfg.stype;
        const classes = [];
        const filters = {};
        const firstCateMap = {};
        for (const [sKey, sObj] of Object.entries(SOURCES)) {
            classes.push({ type_id: sKey, type_name: sObj.name, land: 1, ratio: 1.33 });
            try {
                const fr = await loadSourceFilter(sKey, sObj);
                filters[fr.sourceKey] = [{ key: "cateId", name: "分类", value: fr.vals }];
                if (fr.firstCate) firstCateMap[sKey] = fr.firstCate;
            } catch (e) {
                console.error("load filter fail", sKey, e?.message);
                filters[sKey] = [{ key: "cateId", name: "分类", value: [{ n: "全部(最新)", v: "" }] }];
            }
        }
        extendObj = { classes, filter: filters, firstCateMap };
    } catch (e) {
        console.error("init error", e.message);
        extendObj = { classes: [], filter: {}, firstCateMap: {} };
    }
}

function home(filter) {
    try {
        return JSON.stringify({ class: extendObj.classes || [], filters: extendObj.filter || {} });
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
        let cateId = ext?.cateId ? text(ext.cateId) : "";
        const stype = sourceObj.type || 1;
        // 枫林/可视等无 cateId 时列表为空，自动用第一个分类
        if (!cateId && stype === 2 && extendObj.firstCateMap && extendObj.firstCateMap[tid]) {
            cateId = extendObj.firstCateMap[tid];
        }
        let url;
        if (stype === 0) {
            const params = { ac: 'videolist', pg: pg };
            if (cateId) params.t = cateId;
            url = buildUrl(sourceObj.api, params);
        } else if (stype === 3) {
            const params = { ac: 'videolist', pg: pg };
            if (cateId) params.t = cateId;
            url = buildUrl(sourceObj.api, params);
        } else if (stype === 2) {
            const params = { pg: pg };
            if (cateId) params.t = cateId;
            if (ext) {
                for (const [k, v] of Object.entries(ext)) {
                    if (k !== 'cateId' && v !== undefined && v !== null && text(v) !== '') params[k] = text(v);
                }
            }
            url = buildUrl(sourceObj.api, params);
        } else {
            const params = { ac: 'detail', pg: pg };
            if (cateId) params.t = cateId;
            url = buildUrl(sourceObj.api, params);
        }
        let html = await request(url);
        let data = parseResponse(html);
        if (stype === 2 && (!data.list || data.list.length === 0)) {
            const fc = extendObj.firstCateMap && extendObj.firstCateMap[tid];
            if (fc && fc !== cateId) {
                url = buildUrl(sourceObj.api, { pg: pg, t: fc });
                html = await request(url);
                data = parseResponse(html);
            }
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
    if (stype === 0 || stype === 3) {
        url = buildUrl(sourceObj.api, { ac: 'videolist', wd: keyword, pg: pg });
    } else if (stype === 2) {
        url = buildUrl(sourceObj.api, { wd: keyword, pg: pg });
    } else {
        url = buildUrl(sourceObj.api, { ac: 'detail', wd: keyword, pg: pg });
    }
    const html = await request(url);
    const data = parseResponse(html);
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
        return JSON.stringify({ list: resultList, page: pg, pagecount: maxPage, limit: 40, total: 9999, land: 1, ratio: 1.33 });
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

        if (stype === 0) {
            html = await request(buildUrl(sourceObj.api, { ac: 'videolist', ids: realVodId }));
        } else if (stype === 3) {
            // 大地 feifei2：必须 videolist&ids 才有 vod_url
            html = await request(buildUrl(sourceObj.api, { ac: 'videolist', ids: realVodId }));
            const tmp = parseResponse(html);
            const first = (tmp.list || [])[0];
            if (!first || !text(first.vod_play_url || first.vod_url)) {
                const html2 = await request(buildUrl(sourceObj.api, { ac: 'detail', ids: realVodId }));
                if (html2) html = html2;
            }
        } else {
            html = await request(buildUrl(sourceObj.api, { ac: 'detail', ids: realVodId }));
            if (stype === 2) {
                const dataTmp = parseResponse(html);
                const first = (dataTmp.list || [])[0];
                const noPlay = !first || !text(first.vod_play_url || first.vod_url);
                if (noPlay && /https?:\/\//i.test(realVodId)) {
                    const numMatch = realVodId.match(/\/(\d+)\/?$/) || realVodId.match(/(\d{4,})/);
                    if (numMatch) {
                        const html3 = await request(buildUrl(sourceObj.api, { ac: 'detail', ids: numMatch[1] }));
                        if (html3) {
                            const d3 = parseResponse(html3);
                            if ((d3.list || [])[0] && text((d3.list[0].vod_play_url || d3.list[0].vod_url || ''))) {
                                html = html3;
                            }
                        }
                    }
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
        let playUrl = text(id);
        // 去掉可能附带的 header sugar（部分源）
        if (playUrl.indexOf(';') > 8 && /https?:\/\//i.test(playUrl)) {
            const first = playUrl.split(';')[0];
            if (/^https?:\/\//i.test(first)) playUrl = first;
        }
        const needParse = !isDirectPlayUrl(playUrl);
        const headers = {
            "User-Agent": UA,
            "Referer": "https://api.juliang.live/"
        };
        // jlplayer 落地页需要壳解析；m3u8/mp4 直链
        return JSON.stringify({
            parse: needParse ? 1 : 0,
            jx: 0,
            url: playUrl,
            header: headers
        });
    } catch (e) {
        console.error("play error", e.message);
        return JSON.stringify({ parse: 1, url: id, header: { "User-Agent": UA } });
    }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, search, play };
}

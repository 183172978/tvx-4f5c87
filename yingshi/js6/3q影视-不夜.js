const axios = require("axios");
const http = require("http");
const https = require("https");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const _http = axios.create({
    timeout: 15 * 1000,
    httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false }),
    httpAgent: new http.Agent({ keepAlive: true }),
});

const config = {
    host: 'https://qqqys.com',
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'X-Client': '8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a',
        'web-sign': 'f65f3a83d6d9ad6f',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://qqqys.com'
    }
};

// --- 动态生成符合参考源码逻辑的年份 ---
const generateYears = (typeName) => {
    const currentYear = new Date().getFullYear();
    const years = [{ "n": "全部", "v": "" }];
    if (typeName === '电影') {
        for (let y = currentYear; y >= 2016; y--) years.push({ "n": String(y), "v": String(y) });
        ['2015-2011', '2010-2000', '90年代', '80年代', '更早'].forEach(i => years.push({ "n": i, "v": i }));
    } else if (typeName === '剧集') {
        for (let y = currentYear; y >= 2021; y--) years.push({ "n": String(y), "v": String(y) });
        ['2020-2016', '2015-2011', '2010-2000', '更早'].forEach(i => years.push({ "n": i, "v": i }));
    } else {
        for (let y = currentYear; y >= 2011; y--) years.push({ "n": String(y), "v": String(y) });
        years.push({ "n": "更早", "v": "更早" });
    }
    return years;
};

// --- 根据参考源码配置筛选器 ---
const filterData = {
    "电影": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["动作","喜剧","爱情","科幻","恐怖","悬疑","犯罪","战争","动画","冒险","历史","灾难","纪录","剧情"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国","泰国","印度","英国","法国","德国","加拿大","西班牙","意大利","澳大利亚"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('电影') }
    ],
    "剧集": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["爱情","古装","武侠","历史","家庭","喜剧","悬疑","犯罪","战争","奇幻","科幻","恐怖"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国","泰国","英国"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('剧集') }
    ],
    "动漫": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["冒险","奇幻","科幻","武侠","悬疑"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","日本","欧美"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('动漫') }
    ],
    "综艺": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["真人秀","音乐","脱口秀","歌舞","爱情"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('综艺') }
    ]
};

const QUALITY_PRIORITY = [
    { keywords: ['8K', '8k'], score: 200 },
    { keywords: ['4K', '4k', '超清4K'], score: 190 },
    { keywords: ['蓝光4K', '蓝光HDR'], score: 180 },
    { keywords: ['AE', '蓝光'], score: 170 },
    { keywords: ['1080P蓝光', '1080PHDR'], score: 160 },
    { keywords: ['1080P', '1080p', '超清'], score: 150 },
    { keywords: ['720P', '720p', '高清'], score: 140 },
    { keywords: ['480P', '480p', '标清'], score: 130 },
    { keywords: ['360P', '360p', '流畅'], score: 120 }
];

const json2vods = (arr) => (arr || []).map(i => ({
    vod_id: i.vod_id.toString(),
    vod_name: i.vod_name,
    vod_pic: i.vod_pic,
    vod_remarks: i.vod_remarks,
    type_name: i.vod_class ? `${i.type_name},${i.vod_class}` : i.type_name,
    vod_year: i.vod_year
}));

const calculateQualityScore = (showCode, lineName) => {
    const fullText = `${showCode}${lineName}`.toLowerCase();
    for (const rule of QUALITY_PRIORITY) {
        if (rule.keywords.some(k => fullText.includes(k.toLowerCase()))) return rule.score;
    }
    return 50;
};

// ============================================================
// WASM 解碼模組 - 載入 qqqys.com 的 Protobuf+WASM 解碼器
// ============================================================
let wasmModule = null;
let wasmMemView = null;
let wasmD = 0;
const wasmTextEnc = new TextEncoder();
const wasmTextDec = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
const wasmExtTable = new Map();
let wasmExtCounter = 4;

function wasmGetMem() {
    if (!wasmMemView || wasmMemView.byteLength === 0)
        wasmMemView = new Uint8Array(wasmModule.exports.memory.buffer);
    return wasmMemView;
}
function wasmReadBytes(p, l) { return wasmGetMem().subarray(p >>> 0, (p >>> 0) + l); }
function wasmReadStr(p, l) { return wasmTextDec.decode(wasmGetMem().subarray(p >>> 0, (p >>> 0) + l)); }
function wasmWriteBytes(data, malloc) {
    const p = malloc(data.length, 1) >>> 0;
    wasmGetMem().set(data, p); wasmD = data.length; return p;
}
function wasmWriteStr(s, malloc, realloc) {
    if (!realloc) {
        const e = wasmTextEnc.encode(s);
        const p = malloc(e.length, 1) >>> 0;
        wasmGetMem().subarray(p, p + e.length).set(e);
        wasmD = e.length; return p;
    }
    let n = s.length, p = malloc(n, 1) >>> 0;
    const m = wasmGetMem(); let o = 0;
    for (; o < n; o++) { const c = s.charCodeAt(o); if (c > 127) break; m[p + o] = c; }
    if (o !== n) {
        const r = s.slice(o);
        p = realloc(p, n, n = o + r.length * 3, 1) >>> 0;
        const sub = wasmGetMem().subarray(p + o, p + n);
        const res = wasmTextEnc.encodeInto(r, sub);
        o += res.written;
        p = realloc(p, n, o, 1) >>> 0;
    }
    wasmD = o; return p;
}
function wasmExtAlloc(v) { const i = wasmExtCounter++; wasmExtTable.set(i, v); return i; }
function wasmExtGet(i) { return wasmExtTable.get(i); }
function wasmExtDealloc(i) { const v = wasmExtTable.get(i); wasmExtTable.delete(i); return v; }
function wasmTryCatch(fn, args) {
    try { return fn.apply(null, args); }
    catch(e) { wasmModule.exports.__wbindgen_exn_store(wasmExtAlloc(e)); }
}

function wasmBuildImports() {
    return { "./web_app_wasm_bg.js": {
        __wbg___wbindgen_is_function_0095a73b8b156f76: (e) => typeof wasmExtGet(e) === 'function',
        __wbg___wbindgen_is_object_5ae8e5880f2c1fbd: (e) => { const r = wasmExtGet(e); return typeof r === 'object' && r !== null; },
        __wbg___wbindgen_is_string_cd444516edc5b180: (e) => typeof wasmExtGet(e) === 'string',
        __wbg___wbindgen_is_undefined_9e4d92534c42d778: (e) => wasmExtGet(e) === undefined,
        __wbg___wbindgen_throw_be289d5034ed271b: (e, r) => { throw new Error(wasmReadStr(e, r)); },
        __wbg_call_389efe28435a9388: function() { return wasmTryCatch((e, r) => wasmExtAlloc(wasmExtGet(e).call(wasmExtGet(r))), arguments); },
        __wbg_call_4708e0c13bdc8e95: function() { return wasmTryCatch((e, r, n) => wasmExtAlloc(wasmExtGet(e).call(wasmExtGet(r), wasmExtGet(n))), arguments); },
        __wbg_crypto_86f2631e91b51511: (e) => wasmExtAlloc(crypto),
        __wbg_getRandomValues_b3f15fcbfabb0f8b: function() { return wasmTryCatch((e, r) => { crypto.randomFillSync(wasmExtGet(r)); }, arguments); },
        __wbg_length_32ed9a279acd054c: (e) => wasmExtGet(e).length,
        __wbg_msCrypto_d562bbe83e0d4b91: (e) => 0,
        __wbg_new_no_args_1c7c842f08d00ebb: (e, r) => wasmExtAlloc(new Function(wasmReadStr(e, r))),
        __wbg_new_with_length_a2c39cbe88fd8ff1: (e) => wasmExtAlloc(new Uint8Array(e >>> 0)),
        __wbg_node_e1f24f89a7336c2e: (e) => wasmExtAlloc(process),
        __wbg_now_a3af9a2f4bbaa4d1: () => Date.now(),
        __wbg_process_3975fd6c72f520aa: (e) => wasmExtAlloc(process),
        __wbg_prototypesetcall_bdcdcc5842e4d77d: (e, r, n) => { wasmReadBytes(e, r).set(wasmExtGet(n)); },
        __wbg_randomFillSync_f8c153b79f285817: function() { return wasmTryCatch((e, r) => { crypto.randomFillSync(wasmExtGet(r)); }, arguments); },
        __wbg_require_b74f47fc2d022fd6: function() { return wasmTryCatch(() => wasmExtAlloc(require), arguments); },
        __wbg_static_accessor_GLOBAL_12837167ad935116: () => wasmExtAlloc(global),
        __wbg_static_accessor_GLOBAL_THIS_e628e89ab3b1c95f: () => wasmExtAlloc(globalThis),
        __wbg_static_accessor_SELF_a621d3dfbb60d0ce: () => 0,
        __wbg_static_accessor_WINDOW_f8727f0cf888e0bd: () => 0,
        __wbg_subarray_a96e1fef17ed23cb: (e, r, n) => wasmExtAlloc(wasmExtGet(e).subarray(r >>> 0, n >>> 0)),
        __wbg_versions_4e31226f5e8dc909: (e) => wasmExtAlloc(process.versions),
        __wbindgen_cast_0000000000000001: (e, r) => wasmExtAlloc(wasmReadBytes(e, r)),
        __wbindgen_cast_0000000000000002: (e, r) => wasmExtAlloc(wasmReadStr(e, r)),
        __wbindgen_init_externref_table: () => {
            const t = wasmModule.exports.__wbindgen_externrefs;
            if (t && t.grow) {
                const b = t.grow(4);
                t.set(0, undefined); t.set(b, undefined);
                t.set(b + 1, null); t.set(b + 2, true); t.set(b + 3, false);
            }
        }
    }};
}

let wasmReady = false;
let wasmInitPromise = null;

async function initWasm() {
    if (wasmReady) return true;
    if (wasmInitPromise) return wasmInitPromise;
    wasmInitPromise = (async () => {
        try {
            // 嘗試多個 WASM 檔案路徑
            const possiblePaths = [
                path.join(__dirname, 'qqqys.wasm'),
                '/www/wwwroot/vodspider/vod/routes/qqqys.wasm',
                '/tmp/qqqys.wasm'
            ];
            let wasmBuf = null;
            for (const p of possiblePaths) {
                try { wasmBuf = fs.readFileSync(p); break; } catch(e) {}
            }
            if (!wasmBuf) {
                // 從 qqqys.com 下載 WASM
                wasmBuf = await new Promise((resolve, reject) => {
                    https.get('https://qqqys.com/assets/web_app_wasm_bg-DaFtKBCq.wasm', (res) => {
                        const chunks = [];
                        res.on('data', c => chunks.push(c));
                        res.on('end', () => {
                            const buf = Buffer.concat(chunks);
                            // 儲存到本地快取
                            try { fs.writeFileSync(path.join(__dirname, 'qqqys.wasm'), buf); } catch(e) {}
                            resolve(buf);
                        });
                    }).on('error', reject);
                });
            }

            const { instance } = await WebAssembly.instantiate(wasmBuf, wasmBuildImports());
            wasmModule = instance;
            wasmMemView = null;
            if (wasmModule.exports.__wbindgen_start) wasmModule.exports.__wbindgen_start();
            wasmReady = true;
            console.log('[3Q] WASM decode module loaded');
            return true;
        } catch (e) {
            console.error('[3Q] WASM init failed:', e.message);
            wasmInitPromise = null;
            return false;
        }
    })();
    return wasmInitPromise;
}

function wasmCreateDecodeRequest(url, vodFrom) {
    const e = wasmModule.exports;
    const up = wasmWriteStr(url, e.__wbindgen_malloc, e.__wbindgen_realloc); const ul = wasmD;
    const fp = wasmWriteStr(vodFrom, e.__wbindgen_malloc, e.__wbindgen_realloc); const fl = wasmD;
    const r = e.create_decode_request(up, ul, fp, fl);
    const data = wasmGetMem().slice(r[0], r[0] + r[1]);
    e.__wbindgen_free(r[0], r[1], 1);
    return new Uint8Array(data);
}

function wasmParseDecodeResponse(body) {
    const e = wasmModule.exports;
    const bp = wasmWriteBytes(body, e.__wbindgen_malloc); const bl = wasmD;
    const r = e.parse_decode_response(bp, bl);
    if (r[2]) throw wasmExtDealloc(r[1]) || new Error('parse failed');
    const ptr = r[0];
    const code = e.decoderesult_code(ptr);
    const dd = e.decoderesult_data(ptr);
    const data = dd[0] ? wasmReadStr(dd[0], dd[1]) : '';
    const dm = e.decoderesult_msg(ptr);
    const msg = dm[0] ? wasmReadStr(dm[0], dm[1]) : '';
    e.__wbg_decoderesult_free(ptr, 0);
    return { code, data, msg };
}

function wasmGetSignatureHeaders() {
    const e = wasmModule.exports;
    const r = e.get_signature_headers();
    const aid = e.signatureheaders_aid(r); const aidStr = aid[0] ? wasmReadStr(aid[0], aid[1]) : '';
    const ave = e.signatureheaders_ave(r); const aveStr = ave[0] ? wasmReadStr(ave[0], ave[1]) : '';
    const nonc = e.signatureheaders_nonc(r); const noncStr = nonc[0] ? wasmReadStr(nonc[0], nonc[1]) : '';
    const sign = e.signatureheaders_sign(r); const signStr = sign[0] ? wasmReadStr(sign[0], sign[1]) : '';
    const time = e.signatureheaders_time(r); const timeStr = time[0] ? wasmReadStr(time[0], time[1]) : '';
    e.__wbg_signatureheaders_free(r, 0);
    return { 'X-App-Id': aidStr, 'X-App-Ve': aveStr, 'X-Nonc': noncStr, 'X-Sign': signStr, 'X-Time': timeStr };
}

// Protobuf POST 請求
async function postProtobuf(url, data, extraHeaders = {}) {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        const req = https.request({
            hostname: u.hostname, path: u.pathname, method: 'POST',
            headers: {
                'Content-Type': 'application/x-protobuf',
                'Accept': 'application/x-protobuf',
                'Content-Length': data.length,
                'User-Agent': config.headers['User-Agent'],
                'Referer': 'https://qqqys.com',
                'Origin': 'https://qqqys.com',
                ...extraHeaders
            }
        }, (res) => {
            const chunks = [];
            res.on('data', c => chunks.push(c));
            res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks) }));
        });
        req.on('error', reject);
        req.setTimeout(10000, () => { req.destroy(); reject(new Error('timeout')); });
        req.write(data);
        req.end();
    });
}

// API 請求（使用 X-Client + web-sign 認證，不再需要 WASM 簽名）
async function apiGet(url) {
    return _http.get(url, { headers: config.headers });
}

// 使用 WASM 解碼加密 URL
async function decodeEncryptedUrl(rawUrl, vodFrom) {
    if (!wasmReady) {
        const ok = await initWasm();
        if (!ok) return null;
    }
    try {
        const reqData = wasmCreateDecodeRequest(rawUrl, vodFrom);
        const sigHeaders = wasmGetSignatureHeaders();
        const resp = await postProtobuf(
            `${config.host}/api.php/web/decode/url`,
            reqData,
            sigHeaders
        );
        if (resp.status !== 200) return null;
        const result = wasmParseDecodeResponse(new Uint8Array(resp.body));
        if (result.code === 1 && result.data && result.data.startsWith('http')) {
            return result.data;
        }
        return null;
    } catch (e) {
        console.error('[3Q] decode error:', e.message);
        return null;
    }
}

const getClasses = async () => {
    try {
        const res = await apiGet(`${config.host}/api.php/web/index/home`);
        return {
            class: res.data.data.categories.map(i => ({ type_id: i.type_name, type_name: i.type_name })),
            filters: filterData
        };
    } catch (e) {
        console.error('[3Q] getClasses error:', e.message);
        return { class: [] };
    }
};

const getCategoryList = async (tid, pg = 1, extend = {}) => {
    try {
        // 重要：修正 API 参数名，确保点击后能获取到数据
        const PAGE_SIZE = 50;
        let url = `${config.host}/api.php/web/filter/vod?type_name=${encodeURIComponent(tid)}&page=${pg}&limit=${PAGE_SIZE}`;

        // 映射参数：网站后台通常接收 class, area, year
        if (extend.class) url += `&class=${encodeURIComponent(extend.class)}`;
        if (extend.area) url += `&area=${encodeURIComponent(extend.area)}`;
        if (extend.year) url += `&year=${encodeURIComponent(extend.year)}`;

        url += `&sort=hits`; // 默认按人气排序

        const res = await apiGet(url);
        const items = res.data.data || [];
        // API 的 pageCount 不可靠（永遠返回 1），根據返回數量判斷是否有下一頁
        const hasMore = items.length >= PAGE_SIZE;
        return {
            list: json2vods(items),
            page: pg,
            pagecount: hasMore ? pg + 1 : pg
        };
    } catch (e) { return { list: [] }; }
};

const getDetail = async (id) => {
    try {
        const res = await apiGet(`${config.host}/api.php/web/vod/get_detail?vod_id=${id}`);
        const data = res.data.data[0];
        const vodplayer = res.data.vodplayer;
        const rawShows = data.vod_play_from.split('$$$');
        const rawUrlsList = data.vod_play_url.split('$$$');
        const validLines = [];

        rawShows.forEach((showCode, index) => {
            const playerInfo = vodplayer.find(p => p.from === showCode);
            if (!playerInfo) return;
            let lineName = playerInfo.show;
            if (showCode.toLowerCase() !== lineName.toLowerCase()) lineName = `${lineName} (${showCode})`;
            const urls = rawUrlsList[index].split('#').map(urlItem => {
                if (urlItem.includes('$')) {
                    const [episode, url] = urlItem.split('$');
                    return `${episode}$${showCode}@${playerInfo.decode_status}@${url}`;
                }
                return null;
            }).filter(Boolean);
            if (urls.length > 0) {
                validLines.push({
                    lineName,
                    playUrls: urls.join('#'),
                    score: calculateQualityScore(showCode, lineName)
                });
            }
        });

        if (validLines.length === 0) return null;
        validLines.sort((a, b) => b.score - a.score);
        return {
            vod_id: data.vod_id,
            vod_name: data.vod_name,
            vod_pic: data.vod_pic,
            vod_remarks: data.vod_remarks,
            vod_content: data.vod_content,
            vod_play_from: validLines.map(l => l.lineName).join('$$$'),
            vod_play_url: validLines.map(l => l.playUrls).join('$$$')
        };
    } catch (e) { return null; }
};

const getPlayUrl = async (input) => {
    try {
        const parts = input.split('@');
        const play_from = parts[0];         // 線路代碼 (NBY, BBA, YYNB, JD4K...)
        const decode_status = parts[1];      // 是否需要解碼 (0=直連, 1=加密)
        const raw_url = parts.slice(2).join('@'); // URL 本身可能含 @

        const isHttpUrl = (u) => u && (u.startsWith('http://') || u.startsWith('https://'));
        // 需要解析器的官方平台域名
        const needsParser = (u) => /(iqiyi\.com|v\.qq\.com|youku\.com|mgtv\.com|bilibili\.com)/.test(u);

        // 1. 已經是 HTTP URL → 判斷類型後返回
        if (isHttpUrl(raw_url)) {
            if (needsParser(raw_url)) {
                return { parse: 1, jx: 1, url: raw_url, header: { 'User-Agent': config.headers['User-Agent'] } };
            }
            return { parse: 0, url: raw_url, header: { 'User-Agent': config.headers['User-Agent'] } };
        }

        // 2. 加密 URL → 使用 WASM Protobuf 解碼
        if (decode_status === '1' || !isHttpUrl(raw_url)) {
            const decoded = await decodeEncryptedUrl(raw_url, play_from);
            if (decoded && isHttpUrl(decoded)) {
                console.log(`[3Q] decoded: ${play_from} → ${decoded.substring(0, 80)}...`);
                // 解碼後的 URL 絕大多數是 CDN 直連（mp4/m3u8），直接播放
                if (needsParser(decoded)) {
                    return { parse: 1, jx: 1, url: decoded, header: { 'User-Agent': config.headers['User-Agent'] } };
                }
                return { parse: 0, url: decoded, header: { 'User-Agent': config.headers['User-Agent'] } };
            }
            console.log(`[3Q] decode failed for ${play_from}: ${raw_url.substring(0, 40)}...`);
        }

        // 3. 解碼失敗 fallback
        return { parse: 0, url: '' };
    } catch (e) {
        console.error('[3Q] getPlayUrl error:', e.message);
        return { parse: 0, url: '' };
    }
};

const search = async (wd, pg = 1) => {
    try {
        const res = await apiGet(`${config.host}/api.php/web/search/index?wd=${encodeURIComponent(wd)}&page=${pg}&limit=50`);
        const items = res.data.data || [];
        const hasMore = items.length >= 50;
        return { list: json2vods(items), page: pg, pagecount: hasMore ? pg + 1 : pg };
    } catch (e) { return { list: [] }; }
};

const handleT4Request = async (req) => {
    const { ac, t, ids, play, pg, wd, ext } = req.query;
    if (play) return await getPlayUrl(play);
    if (ids) {
        const detail = await getDetail(ids);
        return { list: detail ? [detail] : [] };
    }
    const page = parseInt(pg) || 1;
    if (wd) return await search(wd, page);
    if (t) {
        let extend = {};
        if (ext) {
            try { extend = JSON.parse(Buffer.from(ext, 'base64').toString()); } catch (e) {}
        }
        return await getCategoryList(t, page, extend);
    }
    return await getClasses();
};

const meta = {
    key: "qqqys",
    name: "3Q影视",
    type: 4,
    api: "/video/qqqys",
    searchable: 1,
    quickSearch: 1
};

module.exports = async (app, opt) => {
    app.get(meta.api, async (req) => {
        try { return await handleT4Request(req); }
        catch (e) { return { error: e.message }; }
    });
    opt.sites.push(meta);
};

/**
 * 懂片帝 dongpian1.com / dongpian.ai - CatVod JS
 * 风格对齐 金牌.js
 * HMAC-SHA256 签名访问 /v1 公开片单与 catalog
 * 播放走站内 /player 页 (parse=1)，无公开 m3u8
 */
import { Crypto, _ } from 'assets://js/lib/cat.js';

let siteKey = '';
let siteType = 0;
let host = 'https://dongpian1.com';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const SIGN_SECRET = '8b9a908a05eac640e1ee06f52acaa741bfe4ba9e004eeffdbeb635e532e06666';

const CLASSES = [
    { type_id: 'hot', type_name: '热门片单' },
    { type_id: 'latest', type_name: '最新片单' }
];

const FILTERS = {
    hot: [{ key: 'sort', name: '排序', value: [{ n: '最热', v: 'hot' }, { n: '最新', v: 'latest' }] }],
    latest: [{ key: 'sort', name: '排序', value: [{ n: '最新', v: 'latest' }, { n: '最热', v: 'hot' }] }]
};

function pageNum(v) {
    const n = parseInt(v, 10);
    return isNaN(n) || n < 1 ? 1 : n;
}

function hmacHex(key, msg) {
    return Crypto.HmacSHA256(msg, key).toString();
}

function signHeaders(method, path) {
    const ts = String(Date.now());
    let nonce = '';
    try {
        const arr = new Uint8Array(16);
        if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
            crypto.getRandomValues(arr);
            nonce = Array.from(arr, function (b) { return b.toString(16).padStart(2, '0'); }).join('');
        } else {
            nonce = Crypto.MD5(String(Math.random()) + ts).toString().slice(0, 32);
        }
    } catch (e) {
        nonce = Crypto.MD5(String(Math.random()) + ts).toString().slice(0, 32);
    }
    const msg = method.toUpperCase() + '\n' + path + '\n' + ts + '\n' + nonce;
    const sig = hmacHex(SIGN_SECRET, msg);
    return {
        'User-Agent': UA,
        'Accept': 'application/json',
        'Referer': host + '/',
        'Origin': host,
        'x-ai-movie-timestamp': ts,
        'x-ai-movie-nonce': nonce,
        'x-ai-movie-signature': sig
    };
}

async function api(path) {
    try {
        if (!path.startsWith('/')) path = '/' + path;
        const res = await req(host + path, {
            method: 'GET',
            headers: signHeaders('GET', path),
            timeout: 15000
        });
        const text = res?.content ?? '';
        if (!text) return null;
        return JSON.parse(text);
    } catch (e) {
        console.error('api', path, e?.message);
        return null;
    }
}

function playlistItem(p) {
    const cover = p.cover || {};
    let pic = cover.poster_url || '';
    if (!pic && Array.isArray(cover.posters) && cover.posters.length) pic = cover.posters[0];
    return {
        vod_id: 'pl:' + String(p.id || ''),
        vod_name: p.title || '片单',
        vod_pic: pic,
        vod_remarks: String(p.item_count || 0) + '部',
        vod_tag: 'folder'
    };
}

function videoItem(it) {
    const tid = String(it.target_id || it.id || '');
    const disp = it.display || {};
    let remarks = '';
    if (disp.year) remarks = String(disp.year);
    if (disp.area) remarks = (remarks + ' ' + String(disp.area)).trim();
    return {
        vod_id: tid,
        vod_name: it.title || tid,
        vod_pic: it.poster_url || '',
        vod_remarks: remarks || String(it.content_kind || '')
    };
}

async function init(cfg) {
    try {
        siteKey = cfg.skey || '';
        siteType = cfg.stype || 0;
        let candidate = cfg.ext || cfg.host || '';
        if (typeof candidate === 'object' && candidate) {
            candidate = candidate.host || candidate.url || '';
        }
        if (typeof cfg.ext === 'string') {
            if (cfg.ext.trim().startsWith('{')) {
                try {
                    const o = JSON.parse(cfg.ext);
                    candidate = o.host || o.url || candidate;
                } catch (e) {}
            } else if (/^https?:\/\//i.test(cfg.ext)) {
                candidate = cfg.ext;
            }
        }
        const value = String(candidate || '').trim().replace(/\/$/, '');
        if (/^https?:\/\//i.test(value)) host = value;
    } catch (e) {
        host = 'https://dongpian1.com';
    }
}

async function home() {
    return JSON.stringify({ class: CLASSES, filters: FILTERS });
}

async function homeVod() {
    try {
        const data = (await api('/v1/playlists/explore?sort=hot')) || {};
        return JSON.stringify({ list: (data.data || []).map(playlistItem) });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, ext) {
    pg = pageNum(pg);
    try {
        tid = String(tid || '').trim();
        let extend = ext;
        if (typeof ext === 'string') {
            try { extend = JSON.parse(ext); } catch (e) { extend = {}; }
        }
        if (!extend) extend = {};

        if (tid.indexOf('pl:') === 0) {
            const pid = tid.slice(3);
            const data = (await api('/v1/playlists/' + encodeURIComponent(pid))) || {};
            const items = (data.items || []).map(videoItem);
            const hasMore = !!(data.items_page && data.items_page.has_more);
            return JSON.stringify({
                list: items,
                page: pg,
                pagecount: hasMore ? pg + 1 : pg,
                limit: items.length || 24,
                total: data.item_count || items.length
            });
        }

        let sort = String(extend.sort || tid || 'hot');
        if (sort !== 'hot' && sort !== 'latest') sort = 'hot';
        const data = (await api('/v1/playlists/explore?sort=' + sort)) || {};
        const items = (data.data || []).map(playlistItem);
        return JSON.stringify({
            list: items,
            page: pg,
            pagecount: pg,
            limit: items.length || 20,
            total: items.length
        });
    } catch (e) {
        console.error('category', e.message);
        return JSON.stringify({ list: [], page: pg, pagecount: 1 });
    }
}

async function search(key, quick, pg) {
    pg = pageNum(pg);
    try {
        const kw = String(key || '').trim();
        const a = (await api('/v1/playlists/explore?sort=hot')) || {};
        const b = (await api('/v1/playlists/explore?sort=latest')) || {};
        const merged = (a.data || []).concat(b.data || []);
        const seen = {};
        const items = [];
        merged.forEach(function (p) {
            const pid = p.id;
            const title = p.title || '';
            if (!pid || seen[pid]) return;
            if (kw && title.indexOf(kw) < 0) return;
            seen[pid] = 1;
            items.push(playlistItem(p));
        });
        return JSON.stringify({ list: items, page: pg, pagecount: pg });
    } catch (e) {
        return JSON.stringify({ list: [], page: pg });
    }
}

async function detail(vodId) {
    try {
        const raw = String(vodId || '').trim();
        if (raw.indexOf('pl:') === 0) {
            const pid = raw.slice(3);
            const data = (await api('/v1/playlists/' + encodeURIComponent(pid))) || {};
            const items = data.items || [];
            const play = items.map(function (it, i) {
                const tid = String(it.target_id || '');
                const name = it.title || ('第' + (i + 1) + '部');
                return name + '$' + tid;
            }).filter(function (x) { return x.indexOf('$') > 0 && !x.endsWith('$'); });
            const cover = data.cover || {};
            return JSON.stringify({
                list: [{
                    vod_id: raw,
                    vod_name: data.title || '片单',
                    vod_pic: cover.poster_url || '',
                    vod_content: data.description || ('共' + (data.item_count || items.length) + '部'),
                    vod_remarks: String(data.item_count || 0) + '部',
                    vod_play_from: '片单',
                    vod_play_url: play.join('#')
                }]
            });
        }

        const path = '/v1/catalog/' + encodeURIComponent(raw);
        const data = (await api(path)) || {};
        if (!data || !data.title) return JSON.stringify({ list: [] });
        const epData = (await api(path + '/episodes')) || {};
        const episodes = epData.episodes || data.episodes || [];
        const varData = (await api(path + '/variants')) || {};
        const variants = varData.variants || data.variants || [];

        const playFrom = [];
        const playUrl = [];
        if (episodes.length) {
            const eps = episodes.map(function (ep, i) {
                const name = ep.title || ('第' + (i + 1) + '集');
                const token = ep.token || ep.id || '';
                return name + '$' + raw + '||' + token;
            });
            playFrom.push('默认');
            playUrl.push(eps.join('#'));
        }
        if (variants.length > 1) {
            variants.forEach(function (v) {
                const vid = v.variant_id || v.id || '';
                if (!vid) return;
                playFrom.push(v.season_label || v.title || '线路');
                playUrl.push('播放$' + vid);
            });
        }
        if (!playUrl.length) {
            playFrom.push('懂片帝');
            playUrl.push('正片$' + raw);
        }

        const actors = data.actors || [];
        const directors = data.directors || [];
        const genres = data.genres || [];
        return JSON.stringify({
            list: [{
                vod_id: raw,
                vod_name: data.title || raw,
                vod_pic: data.poster_url || data.carousel_url || '',
                vod_year: String(data.year || ''),
                vod_area: data.area || '',
                vod_actor: Array.isArray(actors) ? actors.join(',') : String(actors || ''),
                vod_director: Array.isArray(directors) ? directors.join(',') : String(directors || ''),
                type_name: Array.isArray(genres) ? genres.join(',') : String(genres || ''),
                vod_content: String(data.description || '').slice(0, 800),
                vod_remarks: data.remarks || data.episode_progress_text || '',
                vod_play_from: playFrom.join('$$$'),
                vod_play_url: playUrl.join('$$$')
            }]
        });
    } catch (e) {
        console.error('detail', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, id, flags) {
    const raw = String(id || '').trim();
    let variant = raw;
    let token = '';
    const idx = raw.indexOf('||');
    if (idx >= 0) {
        variant = raw.slice(0, idx);
        token = raw.slice(idx + 2);
    }
    let player = host + '/player/' + encodeURIComponent(variant);
    if (token) player += '?episode=' + encodeURIComponent(token);
    return JSON.stringify({
        parse: 1,
        jx: 0,
        url: player,
        header: { 'User-Agent': UA, 'Referer': host + '/' }
    });
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, search, play };
}

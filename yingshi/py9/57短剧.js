/**
 * 57短剧 - CatVod JS
 * 站点：https://57duanju.org / https://57cg4.com
 * 由 57短剧.py 按 8j.js 风格移植
 */
import { Crypto, _ } from 'assets://js/lib/cat.js';

let siteKey = '';
let siteType = 0;

const SITE = 'https://57duanju.org';
const CG = 'https://57cg4.com';
const IMG_REF = 'https://57cg4.com/';
const UA =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';

const CLASSES = [
    { type_id: 'cat_aichengduanju', type_name: '成人AI短剧' },
    { type_id: 'cat_hot', type_name: '热门精选' },
    { type_id: 'cat_jrcg', type_name: '今日吃瓜' },
    { type_id: 'cat_mrds', type_name: '每日大赛' },
    { type_id: 'cat_wanghong', type_name: '网红黑料' },
    { type_id: 'cat_video', type_name: '网黄合集' },
    { type_id: 'cat_cheating', type_name: '出轨劈腿' },
    { type_id: 'cat_live', type_name: '直播擦边' },
    { type_id: 'cat_society', type_name: '社会事件' },
    { type_id: 'cat_star', type_name: '明星八卦' },
    { type_id: 'cat_all', type_name: '全部短剧' }
];

function headers(referer) {
    return {
        'User-Agent': UA,
        Referer: referer || IMG_REF,
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    };
}

async function request(url, referer) {
    try {
        if (!url) return '';
        if (url.indexOf('//') === 0) url = 'https:' + url;
        else if (url.charAt(0) === '/') url = SITE + url;
        const res = await req(url, {
            method: 'GET',
            headers: headers(referer),
            timeout: 15000
        });
        return res && res.content ? res.content : '';
    } catch (e) {
        console.error('request', url, e && e.message);
        return '';
    }
}

function clean(s) {
    return String(s || '')
        .replace(/<[^>]+>/g, '')
        .replace(/&amp;/g, '&')
        .replace(/&nbsp;/g, ' ')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/\s+/g, ' ')
        .trim();
}

function wrapPic(pic) {
    if (!pic) return '';
    if (pic.indexOf('//') === 0) pic = 'https:' + pic;
    else if (pic.charAt(0) === '/') pic = SITE + pic;
    if (pic.indexOf('s.chigua.media') >= 0 && pic.indexOf('@') < 0) {
        return (
            pic +
            '@Referer=' +
            IMG_REF +
            '@User-Agent=' +
            encodeURIComponent(UA)
        );
    }
    return pic;
}

function parseCards(html) {
    const list = [];
    const seen = {};
    if (!html) return list;

    let re = /<a[^>]+href=["'](?:https?:\/\/[^/]+)?\/events\/(\d+)\/?["'][^>]*>([\s\S]*?)<\/a>/gi;
    let m;
    let matches = [];
    while ((m = re.exec(html)) !== null) {
        matches.push([m[1], m[2]]);
    }
    if (!matches.length) {
        re = /<a[^>]+href=["'](?:https?:\/\/[^/]+)?\/(?:events\/)?(\d+)\/?["'][^>]*>([\s\S]*?)<\/a>/gi;
        while ((m = re.exec(html)) !== null) {
            matches.push([m[1], m[2]]);
        }
    }

    for (const [eventId, inner] of matches) {
        if (!eventId || eventId.length < 2 || seen[eventId]) continue;
        seen[eventId] = 1;

        let name = '';
        const tm = inner.match(/<h[23][^>]*>([\s\S]*?)<\/h[23]>/i);
        if (tm) name = clean(tm[1]);
        if (!name) {
            const raw = clean(inner);
            name = raw ? raw.slice(0, 40) : '短剧/热点 ' + eventId;
        }

        let pic = '';
        const imgs = inner.match(/<img[^>]+src=["']([^"']+)["']/gi) || [];
        for (const tag of imgs) {
            const sm = tag.match(/src=["']([^"']+)["']/i);
            if (!sm) continue;
            const src = sm[1].trim();
            if (src.endsWith('.svg') || /logo/i.test(src)) continue;
            pic = src;
            break;
        }

        list.push({
            vod_id: eventId,
            vod_name: name,
            vod_pic: wrapPic(pic),
            vod_remarks: '57短剧',
            style: { type: 'rect', ratio: 1.78 }
        });
    }
    return list;
}

function buildCategoryUrl(tid, pg, sortVal) {
    const page = Number(pg) || 1;
    let slug = String(tid || '').replace(/^\/+|\/+$/g, '').replace(/^cat_/, '');
    let target = '';

    if (slug === 'all') {
        target = page > 1 ? SITE + '/page/' + page + '/' : SITE + '/';
    } else if (slug === 'aichengduanju' || slug === 'hot') {
        target =
            page > 1
                ? SITE + '/' + slug + '/' + page + '/'
                : SITE + '/' + slug + '/';
    } else {
        target =
            page > 1
                ? CG + '/' + slug + '/' + page + '/'
                : CG + '/' + slug + '/';
    }
    if (sortVal) {
        target += (target.indexOf('?') >= 0 ? '&' : '?') + 'sort=' + encodeURIComponent(sortVal);
    }
    return target;
}

async function init(cfg) {
    try {
        siteKey = (cfg && cfg.skey) || '';
        siteType = (cfg && cfg.stype) || 0;
    } catch (e) {}
}

async function home(filter) {
    const result = { class: CLASSES.slice(), filters: {} };
    if (filter) {
        const sortFilter = [
            {
                key: 'sort',
                name: '排序',
                value: [
                    { n: '最新发布', v: '' },
                    { n: '全站最热', v: 'hot' },
                    { n: '飙升热榜', v: 'trending' }
                ]
            }
        ];
        const filters = {};
        for (const c of CLASSES) filters[c.type_id] = sortFilter;
        result.filters = filters;
    }
    return JSON.stringify(result);
}

async function homeVod() {
    try {
        const html = await request(SITE + '/aichengduanju/');
        return JSON.stringify({ list: parseCards(html).slice(0, 12) });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, ext) {
    pg = Number(pg) || 1;
    try {
        let sortVal = '';
        if (ext && typeof ext === 'object') sortVal = ext.sort || '';
        else if (filter && typeof filter === 'object') sortVal = filter.sort || '';
        const url = buildCategoryUrl(tid, pg, sortVal);
        const html = await request(url);
        const list = parseCards(html);
        return JSON.stringify({
            list,
            page: pg,
            pagecount: list.length >= 10 ? pg + 1 : pg,
            limit: list.length || 24,
            total: 9999
        });
    } catch (e) {
        console.error('category', e && e.message);
        return JSON.stringify({ list: [], page: pg, pagecount: 1, limit: 24, total: 0 });
    }
}

async function search(key, quick, pg) {
    pg = Number(pg) || 1;
    try {
        let url = SITE + '/search/?q=' + encodeURIComponent(key || '');
        if (pg > 1) url += '&page=' + pg;
        const html = await request(url);
        const list = parseCards(html);
        return JSON.stringify({
            list,
            page: pg,
            pagecount: list.length >= 10 ? pg + 1 : pg,
            limit: list.length || 24,
            total: 9999
        });
    } catch (e) {
        return JSON.stringify({ list: [], page: pg, pagecount: 1 });
    }
}

async function detail(vodId) {
    try {
        const eventId = String(vodId || '').replace(/^\/+|\/+$/g, '');
        let target = CG + '/events/' + eventId + '/';
        let html = await request(target);
        if (!html || html.length < 500) {
            target = SITE + '/events/' + eventId + '/';
            html = await request(target);
        }

        let title = 'AI短剧/热点 ' + eventId;
        const tm = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
        if (tm) title = clean(tm[1]);

        let desc = '暂无详细介绍';
        const dm = html.match(
            /<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i
        );
        if (dm) desc = dm[1].trim();

        let cover = '';
        const episodes = [];

        // 1. <video> data-hls-src / src
        const videoTags = html.match(/<video([^>]+)>/gi) || [];
        for (const attr of videoTags) {
            let stream = '';
            const hls = attr.match(/data-hls-src=["']([^"']+)["']/i);
            const src = attr.match(/\ssrc=["']([^"']+)["']/i);
            if (hls) stream = hls[1].trim();
            else if (src) stream = src[1].trim();

            if (!cover) {
                const post = attr.match(/poster=["']([^"']+)["']/i);
                if (post) cover = post[1].trim();
            }
            if (stream) {
                episodes.push(
                    '片段 ' + String(episodes.length + 1).padStart(2, '0') + '$' + stream
                );
            }
        }

        // 2. JSON-LD VideoObject
        if (!episodes.length) {
            const scripts = html.match(
                /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi
            ) || [];
            for (const block of scripts) {
                if (block.indexOf('VideoObject') < 0) continue;
                try {
                    const body = block.replace(/^[\s\S]*?>/, '').replace(/<\/script>$/i, '');
                    const data = JSON.parse(body);
                    let vList = data.video || [];
                    if (!Array.isArray(vList)) vList = [vList];
                    for (const v of vList) {
                        const cUrl = (v && v.contentUrl) || '';
                        if (cUrl) {
                            episodes.push(
                                '第 ' +
                                    String(episodes.length + 1).padStart(2, '0') +
                                    ' 集$' +
                                    cUrl
                            );
                            if (!cover && v.thumbnailUrl) cover = v.thumbnailUrl;
                        }
                    }
                } catch (e) {}
            }
        }

        // 3. 页面直链兜底
        if (!episodes.length) {
            const all = html.match(/["'](https?:\/\/[^"'\s]+\.(?:m3u8|mp4)[^"'\s]*)["']/gi) || [];
            const seen = {};
            for (const raw of all) {
                const um = raw.match(/["'](https?:\/\/[^"'\s]+)["']/);
                if (!um) continue;
                const u = um[1];
                if (seen[u]) continue;
                seen[u] = 1;
                episodes.push(
                    '播放 ' + String(episodes.length + 1).padStart(2, '0') + '$' + u
                );
            }
        }

        if (!cover) {
            const om = html.match(
                /<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i
            );
            if (om) cover = om[1].trim();
        }

        const playUrl =
            episodes.length > 0
                ? episodes.join('#')
                : '无可用视频流$http://127.0.0.1';

        return JSON.stringify({
            list: [
                {
                    vod_id: eventId,
                    vod_name: title,
                    vod_pic: wrapPic(cover),
                    vod_actor: 'TG: @tvshare23',
                    vod_director: '57短剧',
                    vod_remarks:
                        episodes.length > 1
                            ? '共 ' + episodes.length + ' 个片段'
                            : '57短剧',
                    vod_content: desc,
                    vod_play_from: '57吃瓜在线',
                    vod_play_url: playUrl
                }
            ]
        });
    } catch (e) {
        console.error('detail', e && e.message);
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, id, flags) {
    const raw = String(id || '').trim();
    const header = {
        'User-Agent': UA,
        Referer: IMG_REF,
        Origin: 'https://57cg4.com'
    };
    try {
        if (/\.(m3u8|mp4|mkv|flv)(\?|$)/i.test(raw)) {
            return JSON.stringify({ parse: 0, jx: 0, url: raw, header });
        }
        return JSON.stringify({ parse: 0, jx: 0, url: raw, header });
    } catch (e) {
        return JSON.stringify({ parse: 0, url: raw, header: { 'User-Agent': UA } });
    }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, search, play };
}
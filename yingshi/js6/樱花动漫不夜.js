const axios = require("axios");
const http = require("http");
const https = require("https");
const cheerio = require("cheerio");

const _http = axios.create({
    timeout: 15 * 1000,
    httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false, family: 4 }),
    httpAgent: new http.Agent({ keepAlive: true }),
});

// ========== 全局配置 ==========
const yinghuaConfig = {
    host: "https://www.dmvvv.com",
    headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.dmvvv.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
};

const PAGE_LIMIT = 36;
const DANMU_API = process.env.DANMU_API || "";

// ========== 辅助工具函数 ==========
const encodeMeta = (obj) => {
    try {
        return Buffer.from(JSON.stringify(obj || {}), "utf8").toString("base64");
    } catch {
        return "";
    }
};

const decodeMeta = (str) => {
    try {
        const raw = Buffer.from(str || "", "base64").toString("utf8");
        return JSON.parse(raw || "{}");
    } catch {
        return {};
    }
};

function preprocessTitle(title) {
    if (!title) return "";
    return title
        .replace(/4[kK]|[xX]26[45]|720[pP]|1080[pP]|2160[pP]/g, " ")
        .replace(/[hH]\.?26[45]/g, " ")
        .replace(/BluRay|WEB-DL|HDR|REMUX/gi, " ")
        .replace(/\.mp4|\.mkv|\.avi|\.flv/gi, " ");
}

function chineseToArabic(cn) {
    const map = { '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 };
    if (!isNaN(cn)) return parseInt(cn);
    if (cn.length === 1) return map[cn] || cn;
    if (cn.length === 2) {
        if (cn[0] === '十') return 10 + map[cn[1]];
        if (cn[1] === '十') return map[cn[0]] * 10;
    }
    if (cn.length === 3) return map[cn[0]] * 10 + map[cn[2]];
    return cn;
}

function extractEpisode(title) {
    if (!title) return "";
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
        if (!["720", "1080", "480"].includes(num)) return num;
    }
    return "";
}

function buildFileNameForDanmu(vodName, episodeTitle) {
    if (!vodName) return "";
    if (!episodeTitle || episodeTitle === '正片' || episodeTitle === '播放') return vodName;
    const digits = extractEpisode(episodeTitle);
    if (digits) {
        const epNum = parseInt(digits, 10);
        if (epNum > 0) {
            return epNum < 10 ? `${vodName} S01E0${epNum}` : `${vodName} S01E${epNum}`;
        }
    }
    return vodName;
}

async function matchDanmu(fileName) {
    if (!DANMU_API || !fileName) return [];
    try {
        console.log(`[樱花动漫] 匹配弹幕: ${fileName}`);
        const response = await _http.post(`${DANMU_API}/api/v2/match`, { fileName: fileName }, {
            headers: {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
        });
        const matchData = response.data;
        if (!matchData.isMatched || !matchData.matches || matchData.matches.length === 0) return [];
        
        const firstMatch = matchData.matches[0];
        const episodeId = firstMatch.episodeId;
        if (!episodeId) return [];

        let danmakuName = [firstMatch.animeTitle, firstMatch.episodeTitle].filter(Boolean).join(" - ") || "弹幕";
        return [{
            name: danmakuName,
            url: `${DANMU_API}/api/v2/comment/${episodeId}?format=xml`,
        }];
    } catch (error) {
        console.error(`[樱花动漫] 弹幕匹配失败: ${error.message}`);
        return [];
    }
}

const parseHomeList = (html) => {
    const list = [];
    const $ = cheerio.load(html);
    $('li').each((i, item) => {
        const $item = $(item);
        const $link = $item.find('a');
        const href = $link.attr('href');
        const title = $link.attr('title');
        const pic = $item.find('img').data('original') || $item.find('img').attr('src');
        const remarks = $item.find('p').text().trim();

        if (href && href.includes('/detail/') && title) {
            list.push({
                vod_id: href,
                vod_name: title.trim(),
                vod_pic: pic || '',
                vod_remarks: remarks || ''
            });
        }
    });
    return list;
};

const parsePageCount = (html, tid) => {
    const $ = cheerio.load(html);
    let maxPage = 1;
    if (tid) {
        const pattern = new RegExp(`/type/${tid}/(\\d+)/`, 'g');
        let match;
        while ((match = pattern.exec(html)) !== null) {
            maxPage = Math.max(maxPage, parseInt(match[1]));
        }
    }
    const pattern2 = /\/type\/[^/]+\/(\d+)\//g;
    let match2;
    while ((match2 = pattern2.exec(html)) !== null) {
        maxPage = Math.max(maxPage, parseInt(match2[1]));
    }
    return maxPage;
};

// ========== 核心路由层实现 ==========

const _home = async ({ filter }) => {
    console.log("🏠 樱花动漫首页请求");
    try {
        const response = await _http.get(yinghuaConfig.host + "/", { headers: yinghuaConfig.headers });
        const list = parseHomeList(response.data);
        const seen = new Set();
        const uniqueList = list.filter(item => {
            if (seen.has(item.vod_id)) return false;
            seen.add(item.vod_id);
            return true;
        });

        return {
            class: [
                { 'type_id': 'guoman', 'type_name': '国产动漫' },
                { 'type_id': 'riman', 'type_name': '日本动漫' },
                { 'type_id': 'oman', 'type_name': '欧美动漫' },
                { 'type_id': 'dmfilm', 'type_name': '动漫电影' }
            ],
            list: uniqueList.slice(0, 20)
        };
    } catch (e) {
        console.error("❌ 首页获取失败:", e.message);
        return { class: [], list: [] };
    }
};

const _category = async ({ id, page, filter, filters }) => {
    const pg = parseInt(page) || 1;
    console.log(`📋 樱花动漫分类请求 id: ${id}, page: ${pg}`);
    try {
        const url = pg <= 1 ? `${yinghuaConfig.host}/type/${id}/` : `${yinghuaConfig.host}/type/${id}/${pg}/`;
        const response = await _http.get(url, { headers: yinghuaConfig.headers });
        const list = parseHomeList(response.data);
        const maxPage = parsePageCount(response.data, id) || (list.length >= PAGE_LIMIT ? pg + 1 : pg);

        return {
            list: list,
            page: pg,
            pagecount: maxPage
        };
    } catch (e) {
        console.error("❌ 分类请求失败:", e.message);
        return { list: [], page: pg, pagecount: 1 };
    }
};

const _detail = async ({ id }) => {
    // id 为传入的数组，获取第一个元素
    const videoId = Array.isArray(id) ? id[0] : id;
    console.log(`🔍 樱花动漫详情请求 ID: ${videoId}`);
    try {
        const detailUrl = videoId.startsWith('http') ? videoId : yinghuaConfig.host + videoId;
        const response = await _http.get(detailUrl, { headers: yinghuaConfig.headers });
        const html = response.data;
        const $ = cheerio.load(html);

        let vod_name = '';
        const titleMatch = html.match(/<div class="detail">.*?<h2>([^<]+)<\/h2>/s);
        if (titleMatch) vod_name = titleMatch[1].trim();

        let vod_pic = '';
        const coverMatch = html.match(/<div class="cover">\s*<img[^>]+data-original="([^"]+)"/);
        if (coverMatch) vod_pic = coverMatch[1];

        const getInfo = (label, useEm = true) => {
            const pattern = useEm ? new RegExp(`<span>${label}:<\\/span><em>([^<]+)<\\/em>`) : new RegExp(`<span>${label}:<\\/span>([^<]+)`);
            const match = html.match(pattern);
            return match ? match[1].trim() : '';
        };

        const vod_remarks = getInfo('状态', true);
        const vod_year = getInfo('年份', false);
        const vod_area = getInfo('地区', false);
        const vod_type = getInfo('类型', false);
        const vod_actor = getInfo('主演', false);

        let vod_content = '';
        const descMatch = html.match(/class="blurb"[^>]*>.*?<span>[^<]+<\/span>(.*?)<\/li>/s);
        if (descMatch) vod_content = descMatch[1].replace(/<[^>]+>/g, '').trim();

        let totalEpisodes = 0;
        if (vod_remarks) {
            const epMatch = vod_remarks.match(/[共全更新至第]*(\d+)[集话章]/);
            if (epMatch) totalEpisodes = parseInt(epMatch[1]);
        }
        if (totalEpisodes === 0) totalEpisodes = 24; // 兜底集数

        const vodIdStr = videoId.replace(/^\/+|\/+$/g, '').split('/').pop();
        const sourceNames = ['高清', 'ikun', '非凡', '量子'];
        const playLines = [];
        const urlLines = [];

        // 动态探测播放线路
        for (let sourceIdx = 1; sourceIdx <= 4; sourceIdx++) {
            try {
                const testUrl = `${yinghuaConfig.host}/play/${vodIdStr}-${sourceIdx}-1/`;
                await _http.get(testUrl, { headers: yinghuaConfig.headers, timeout: 4000 });

                const episodes = [];
                for (let epIdx = 1; epIdx <= totalEpisodes; epIdx++) {
                    const epName = epIdx < 10 ? `第0${epIdx}集` : `第${epIdx}集`;
                    const epUrl = `/play/${vodIdStr}-${sourceIdx}-${epIdx}/`;
                    // 将视频名称与选集透传供播放时匹配弹幕
                    const combinedId = `${epUrl}|||${encodeMeta({ v: vod_name, e: epName })}`;
                    episodes.push(`${epName}$${combinedId}`);
                }

                if (episodes.length > 0) {
                    playLines.push(sourceNames[sourceIdx - 1]);
                    urlLines.push(episodes.join('#'));
                }
            } catch (err) {
                continue;
            }
        }

        return {
            list: [{
                vod_id: videoId,
                vod_name,
                vod_pic,
                vod_content,
                vod_year,
                vod_area,
                vod_actor,
                vod_remarks,
                type_name: vod_type,
                vod_play_from: playLines.join('$$$'),
                vod_play_url: urlLines.join('$$$')
            }]
        };
    } catch (e) {
        console.error("❌ 详情获取失败:", e.message);
        return { list: [] };
    }
};

const _search = async ({ page, quick, wd }) => {
    const pg = parseInt(page) || 1;
    console.log(`🔍 樱花动漫搜索请求 wd: ${wd}, page: ${pg}`);
    try {
        const encodedKeyword = encodeURIComponent(wd);
        const url = pg <= 1 ? `${yinghuaConfig.host}/search/?wd=${encodedKeyword}` : `${yinghuaConfig.host}/search/?wd=${encodedKeyword}&pageno=${pg}`;
        const response = await _http.get(url, { headers: yinghuaConfig.headers });
        const html = response.data;
        const list = [];

        const lis = html.match(/<li>\s*<a class="cover".*?<\/li>/gs) || [];
        lis.forEach(li => {
            const hrefMatch = li.match(/<a class="cover" href="(\/detail\/\d+\/)"/);
            const titleMatch = li.match(/title="([^"]+)"/);
            const coverMatch = li.match(/data-original="([^"]+)"/);
            const remarksMatch = li.match(/<div class="item"><span>状态:<\/span>([^<]*)/);

            if (hrefMatch && titleMatch) {
                list.push({
                    vod_id: hrefMatch[1],
                    vod_name: titleMatch[1].trim(),
                    vod_pic: coverMatch ? coverMatch[1].trim() : '',
                    vod_remarks: remarksMatch ? remarksMatch[1].trim() : ''
                });
            }
        });

        let maxPage = pg;
        const totalMatch = html.match(/找到\s*<em>(\d+)<\/em>/);
        if (totalMatch) {
            maxPage = Math.ceil(parseInt(totalMatch[1]) / 12);
        } else if (list.length >= 12) {
            maxPage = pg + 1;
        }

        return {
            list: list,
            page: pg,
            pagecount: maxPage
        };
    } catch (e) {
        console.error("❌ 搜索失败:", e.message);
        return { list: [], page: pg, pagecount: 1 };
    }
};

const _play = async ({ flag, flags, id }) => {
    let playUrl = id;
    console.log(`▶️ 樱花动漫播放请求 ID: ${playUrl}`);

    let vodName = "";
    let episodeName = "";

    if (playUrl && playUrl.includes('|||')) {
        const [mainPlayUrl, metaB64] = playUrl.split('|||');
        playUrl = mainPlayUrl;
        const playMeta = decodeMeta(metaB64 || "");
        vodName = playMeta.v || "";
        episodeName = playMeta.e || "";
    }

    try {
        if (playUrl && !playUrl.startsWith('http')) {
            playUrl = playUrl.startsWith('/') ? yinghuaConfig.host + playUrl : `${yinghuaConfig.host}/${playUrl}`;
        }

        const response = await _http.get(playUrl, { headers: yinghuaConfig.headers });
        const html = response.data;

        let finalUrl = playUrl;
        const urlMatch = html.match(/url:\s*'(https?:\/\/[^']+)'/);
        if (urlMatch) {
            finalUrl = urlMatch[1];
        } else {
            const m3u8Match = html.match(/(https?:\/\/[^\s'"]+\.m3u8(?:\?[^\s'">]*)?)/);
            if (m3u8Match) finalUrl = m3u8Match[1];
        }

        let playResponse = {
            parse: 0,
            jx: 0,
            url: finalUrl,
            header: {
                "User-Agent": yinghuaConfig.headers["User-Agent"],
                "Referer": yinghuaConfig.host + "/"
            }
        };

        // 匹配外部弹幕
        if (DANMU_API && vodName) {
            const fileName = buildFileNameForDanmu(vodName, episodeName);
            if (fileName) {
                const danmakuList = await matchDanmu(fileName);
                if (danmakuList && danmakuList.length > 0) {
                    playResponse.danmaku = danmakuList;
                }
            }
        }

        return playResponse;
    } catch (e) {
        console.error("❌ 播放解析失败:", e.message);
        return {
            parse: 0,
            jx: 0,
            url: playUrl,
            header: yinghuaConfig.headers
        };
    }
};

// ========== 统一代理路由（如有必要扩展） ==========
const _proxy = async (req, reply) => {
    return Object.assign({}, req.query, req.params);
};

// ========== 元数据声明 ==========
const meta = {
    key: "YingHuaDM",
    name: "樱花动漫",
    type: 4,
    api: "/video/YingHuaDM",
    searchable: 1,
    quickSearch: 1,
    changeable: 0,
};

// ========== 服务注册导出 ==========
module.exports = async (app, opt) => {
    app.get(meta.api, async (req, reply) => {
        const { extend, filter, t, ac, pg, ext, ids, flag, play, wd, quick } = req.query;

        try {
            if (play) {
                return await _play({ flag: flag || "", flags: [], id: play });
            } else if (wd) {
                return await _search({
                    page: parseInt(pg || "1"),
                    quick: quick || false,
                    wd,
                });
            } else if (ac === "detail" && ids) {
                // TVBox 传入的 ids 是逗号分割的或单个 id，这里切分为数组给 _detail
                const idArr = String(ids).split(",");
                return await _detail({ id: idArr });
            } else if (ac === "detail" && t) {
                // 兼容有些客户端传 t 充当分类或详情场景
                return await _detail({ id: [t] });
            } else if (t) {
                // 当带有分类标识 t 且不是 detail 时，认定为分类列表请求
                return await _category({
                    id: t,
                    page: parseInt(pg || "1"),
                    filter: filter || false,
                    filters: {},
                });
            } else if (!ac) {
                // 默认首页请求
                return await _home({ filter: filter ?? false });
            }

            return { list: [], page: 1, pagecount: 1 };
        } catch (err) {
            console.error(`[${meta.name}] 路由分发错误:`, err.message);
            return { list: [], page: 1, pagecount: 1, error: err.message };
        }
    });

    // 将当前站点配置动态注入进系统站点池
    opt.sites.push(meta);
};
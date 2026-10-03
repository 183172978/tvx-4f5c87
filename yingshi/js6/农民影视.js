// @name 农民影视
// @author OmniBox
// @description 刮削：支持，弹幕：支持，嗅探：支持
// @version 1.0.9
// @downloadURL https://gh-proxy.org/https://raw.githubusercontent.com/xxx/OmniBox-Spider/main/影视/采集/农民影视.js

const OmniBox = require("omnibox_sdk");
const runner = require("spider_runner");

const host = 'https://www.nmdvd.top';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const headers = { 
    'User-Agent': UA, 
    'Referer': host,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
};

const DANMU_API = process.env.DANMU_API || "";

function logInfo(msg) { OmniBox.log('info', `[农民影视] ${msg}`); }
function logError(msg) { OmniBox.log('error', `[农民影视] ${msg}`); }

const encodeMeta = (obj) => {
    try { return Buffer.from(JSON.stringify(obj || {}), 'utf8').toString('base64'); }
    catch (_) { return ''; }
};
const decodeMeta = (str) => {
    try { return JSON.parse(Buffer.from(str || '', 'base64').toString('utf8')); }
    catch (_) { return {}; }
};

function fixUrl(path) {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    if (path.startsWith('//')) return 'https:' + path;
    return host + (path.startsWith('/') ? '' : '/') + path;
}

function stripTags(str) { return str.replace(/<[^>]+>/g, '').trim(); }

async function fetchHtml(url) {
    try {
        logInfo(`请求: ${url}`);
        const res = await OmniBox.request(url, { method: 'GET', headers });
        if (res.statusCode !== 200) {
            logError(`HTTP ${res.statusCode}`);
            return '';
        }
        return res.body || '';
    } catch (e) {
        logError(`请求失败: ${e.message}`);
        return '';
    }
}

// ========== 列表解析 - 使用更宽松的匹配 ==========
function parseList(html) {
    const items = [];
    const seen = new Set();
    
    // 方法1: 匹配 stui-vodlist__box 结构
    const boxRegex = /<div class="stui-vodlist__box">([\s\S]*?)<\/div>\s*<\/div>/gi;
    let match;
    
    while ((match = boxRegex.exec(html)) !== null) {
        const block = match[1];
        
        // 提取链接
        let link = '', title = '';
        const aMatch = block.match(/<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"/i);
        if (aMatch) {
            link = aMatch[1];
            title = aMatch[2].trim();
        } else {
            const simpleA = block.match(/<a[^>]*href="([^"]+)"[^>]*>([^<]+)<\/a>/i);
            if (simpleA) {
                link = simpleA[1];
                title = stripTags(simpleA[2]);
            }
        }
        
        if (!link || seen.has(link)) continue;
        seen.add(link);
        
        // 提取图片 - 多种方式
        let pic = '';
        // 方式1: data-original
        let imgMatch = block.match(/<img[^>]*data-original="([^"]+)"/i);
        // 方式2: src
        if (!imgMatch) imgMatch = block.match(/<img[^>]*src="([^"]+)"/i);
        // 方式3: a 标签的 data-original
        if (!imgMatch) imgMatch = block.match(/<a[^>]*data-original="([^"]+)"/i);
        if (imgMatch) pic = imgMatch[1];
        
        // 过滤占位图
        if (pic && (pic.includes('load.gif') || pic.includes('loading') || pic.includes('blank') || pic.includes('placeholder'))) {
            pic = '';
        }
        
        // 提取备注
        let remarks = '';
        const remarkMatch = block.match(/<span class="pic-text[^>]*>([^<]+)<\/span>/i);
        if (remarkMatch) remarks = remarkMatch[1].trim();
        
        if (title && title.length > 0) {
            items.push({
                vod_id: fixUrl(link),
                vod_name: title,
                vod_pic: fixUrl(pic),
                vod_remarks: remarks
            });
        }
    }
    
    // 方法2: 如果方法1没找到，直接从全局匹配图片链接
    if (items.length === 0) {
        const globalRegex = /<a[^>]*href="(\/vod\/\d+\.html)"[^>]*>[\s\S]*?<img[^>]*(?:data-original|src)="([^"]+)"[^>]*>[\s\S]*?<h4[^>]*>([^<]+)<\/h4>/gi;
        let globalMatch;
        while ((globalMatch = globalRegex.exec(html)) !== null) {
            const link = globalMatch[1];
            if (seen.has(link)) continue;
            seen.add(link);
            items.push({
                vod_id: fixUrl(link),
                vod_name: stripTags(globalMatch[3]),
                vod_pic: fixUrl(globalMatch[2]),
                vod_remarks: ''
            });
        }
    }
    
    logInfo(`parseList 解析到 ${items.length} 条`);
    return items;
}

// ========== home ==========
async function home(params) {
    try {
        const html = await fetchHtml(host);
        const list = parseList(html);
        logInfo(`首页: ${list.length} 条`);
        
        // 打印前3条图片URL用于调试
        if (list.length > 0) {
            logInfo(`示例: ${list[0].vod_name} -> ${list[0].vod_pic}`);
        }
        
        return {
            class: [
                { type_id: 'dianying', type_name: '电影' },
                { type_id: 'juji', type_name: '剧集' },
                { type_id: 'dongman', type_name: '动漫' },
                { type_id: 'zongyi', type_name: '综艺' },
                { type_id: 'duanju', type_name: '短剧' }
            ],
            filters: {},
            list: list.slice(0, 24)
        };
    } catch (e) {
        logError(`home 失败: ${e.message}`);
        return { class: [], filters: {}, list: [] };
    }
}

// ========== category ==========
async function category(params) {
    try {
        const tid = params.categoryId || 'juji';
        const page = parseInt(params.page) || 1;
        
        let url = page === 1 ? `${host}/type/${tid}.html` : `${host}/type/${tid}/page/${page}.html`;
        logInfo(`category url=${url}`);
        
        const html = await fetchHtml(url);
        const list = parseList(html);
        logInfo(`category: ${list.length} 条`);
        return { page, pagecount: 10, list };
    } catch (e) {
        logError(`category 失败: ${e.message}`);
        return { page: 1, pagecount: 0, list: [] };
    }
}

// ========== search ==========
async function search(params) {
    try {
        const keyword = params.keyword || params.wd || '';
        if (!keyword) return { page: 1, pagecount: 0, list: [] };
        
        logInfo(`search keyword=${keyword}`);
        const url = `${host}/vodsearch.html?wd=${encodeURIComponent(keyword)}`;
        const html = await fetchHtml(url);
        const list = parseList(html);
        return { page: 1, pagecount: 1, list };
    } catch (e) {
        logError(`search 失败: ${e.message}`);
        return { page: 1, pagecount: 0, list: [] };
    }
}

// ========== detail ==========
async function detail(params) {
    try {
        const videoId = Array.isArray(params.videoId) ? params.videoId[0] : params.videoId;
        const url = videoId.startsWith('http') ? videoId : `${host}${videoId}`;
        logInfo(`detail url=${url}`);
        
        const html = await fetchHtml(url);
        
        let title = '未知标题';
        const titleMatch = html.match(/<h3 class="title">([^<]+)<\/h3>/i);
        if (titleMatch) title = titleMatch[1].trim();
        
        let pic = '';
        const picMatch = html.match(/<img[^>]*data-original="([^"]+)"/i) ||
                         html.match(/<img[^>]*src="([^"]+\.(jpg|png|webp))"/i);
        if (picMatch) pic = picMatch[1];
        
        let content = '';
        const contentMatch = html.match(/<span class="detail-sketch">([\s\S]*?)<\/span>/i);
        if (contentMatch) content = stripTags(contentMatch[1]);
        
        let actor = '', director = '', year = '';
        const directorMatch = html.match(/导演：<\/span><a[^>]*>([^<]+)<\/a>/i);
        if (directorMatch) director = directorMatch[1];
        
        const actorMatch = html.match(/主演：<\/span>([\s\S]*?)<\/p>/i);
        if (actorMatch) {
            const actors = actorMatch[1].match(/<a[^>]*>([^<]+)<\/a>/g);
            if (actors) actor = actors.map(a => stripTags(a)).join(',');
        }
        
        const yearMatch = html.match(/年份：<\/span><a[^>]*>(\d{4})<\/a>/i);
        if (yearMatch) year = yearMatch[1];
        
        // 提取线路和剧集
        const playSources = [];
        const tabs = [];
        const tabRegex = /<li><a href="#playlist(\d+)"[^>]*data-toggle="tab">([^<]+)<\/a><\/li>/gi;
        let tabMatch;
        while ((tabMatch = tabRegex.exec(html)) !== null) {
            tabs.push({ id: tabMatch[1], name: tabMatch[2].trim() });
        }
        
        for (const tab of tabs) {
            const playlistRegex = new RegExp(`<div id="playlist${tab.id}"[^>]*class="tab-pane[^"]*"[^>]*>([\\s\\S]*?)<\\/div>`, 'i');
            const playlistMatch = html.match(playlistRegex);
            
            if (playlistMatch) {
                const episodes = [];
                const epRegex = /<a href="([^"]+)"[^>]*>([^<]+)<\/a>/gi;
                let epMatch;
                let epIndex = 0;
                
                while ((epMatch = epRegex.exec(playlistMatch[1])) !== null) {
                    const epLink = epMatch[1];
                    let epName = stripTags(epMatch[2]);
                    if (!epName) epName = `第${epIndex + 1}集`;
                    
                    const fid = `${videoId}#${tab.id}#${epIndex}`;
                    const playId = `${fixUrl(epLink)}|||${encodeMeta({ sid: videoId, fid: fid, v: title, e: epName })}`;
                    episodes.push({ name: epName, playId });
                    epIndex++;
                }
                
                if (episodes.length > 0) {
                    playSources.push({ name: tab.name, episodes });
                }
            }
        }
        
        return {
            list: [{
                vod_id: videoId,
                vod_name: title,
                vod_pic: fixUrl(pic),
                vod_content: content,
                vod_actor: actor,
                vod_director: director,
                vod_year: year,
                vod_play_sources: playSources.length > 0 ? playSources : undefined
            }]
        };
    } catch (e) {
        logError(`detail 失败: ${e.message}`);
        return { list: [] };
    }
}

// ========== play ==========
async function play(params) {
    const rawInput = params.playId || '';
    const sepIdx = rawInput.indexOf('|||');
    const rawPath = sepIdx >= 0 ? rawInput.substring(0, sepIdx) : rawInput;
    const encodedMeta = sepIdx >= 0 ? rawInput.substring(sepIdx + 3) : '';
    const meta = decodeMeta(encodedMeta);
    
    const pageUrl = rawPath.startsWith('http') ? rawPath : `${host}${rawPath}`;
    const vodName = meta.v || '';
    const episodeName = meta.e || '';
    logInfo(`play url=${pageUrl}`);
    
    try {
        const sniffed = await OmniBox.sniffVideo(pageUrl, {
            'User-Agent': UA,
            'Referer': host
        });
        
        if (sniffed && sniffed.url) {
            let videoUrl = sniffed.url;
            if (videoUrl.startsWith('//')) videoUrl = 'https:' + videoUrl;
            if (videoUrl.startsWith('/')) videoUrl = fixUrl(videoUrl);
            
            logInfo(`嗅探成功: ${videoUrl.substring(0, 100)}`);
            return {
                parse: 0,
                urls: [{ name: '播放', url: videoUrl }],
                header: sniffed.header || { 'User-Agent': UA, 'Referer': pageUrl }
            };
        }
        
        logInfo('嗅探失败，回退 parse=1');
        return {
            parse: 1,
            urls: [{ name: '播放', url: pageUrl }],
            header: { 'User-Agent': UA, 'Referer': pageUrl }
        };
        
    } catch (e) {
        logError(`play 失败: ${e.message}`);
        return {
            parse: 1,
            urls: [{ name: '播放', url: pageUrl }],
            header: { 'User-Agent': UA, 'Referer': pageUrl }
        };
    }
}

module.exports = { home, category, search, detail, play };
runner.run(module.exports);
/*
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 0,
  title: '荐片',
  lang: 'cat'
})
*/

let host = 'https://api.ztcgi.com';
let imghost = '';
let siteKey = '';
let siteType = 0;
let siteName = '荐片';
let maxPages = 5;
let config = '';

// 过滤规则配置
let title_remove = ['名称排除', '广告', '破解', '群'];
let line_remove = ['线路排除', '广告', '666', 'mymv'];
let line_order = ['线路排序', '极速', '高速', '常规线路', 'ft', '官', 'ace', '1080p', 'dytt'];
let cate_remove = ['分类排除', '推荐', '首页'];

// API路径配置 - 所有接口路径集中管理
let rule = {
    homeCategory: '/api/v2/settings/homeCategory',           // 首页分类接口
    resourceDomain: '/api/v2/settings/resourceDomainConfig',  // 图片域名配置接口
    slideList: '/api/slide/list',                              // 轮播图/推荐列表接口
    dyTag: '/api/dyTag/tpl2_data',                             // 动态标签数据接口
    crumbList: '/api/crumb/list',                              // 分类列表接口
    detail: '/api/video/detailv2',                             // 视频详情接口
    search: '/api/v2/search/videoV2'                           // 搜索接口
};

async function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    siteName = (cfg.skey?.split('_')[1] || cfg.skey) || '荐片';
    
    let ext = cfg.ext !== undefined ? cfg.ext : cfg;
    if (typeof ext === 'string' && ext.includes('$')) {
        const [url, order] = ext.split('$');
        const html = await request(url);
        config = JSON.parse(html)[order];
        host = config.host || config.hosturl || config.url || config.site;

    } else if (ext && typeof ext === 'object') {
        config = ext;
        host = config.host || config.hosturl || config.url || config.site;
    }
    
    if (config.title_remove !== undefined) {
        title_remove = Array.isArray(config.title_remove) ? config.title_remove : title_remove;
    }
    if (config.line_remove !== undefined) {
        line_remove = Array.isArray(config.line_remove) ? config.line_remove : line_remove;
    }
    if (config.line_order !== undefined) {
        line_order = Array.isArray(config.line_order) ? config.line_order : line_order;
    }
    if (config.cate_remove !== undefined) {
        cate_remove = Array.isArray(config.cate_remove) ? config.cate_remove : cate_remove;
    }
    
    try {
        // 获取图片域名配置
        let res = await req(`${host}${rule.resourceDomain}`, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        let config = JSON.parse(res.content);
        if (config.code === 1 && config.data && config.data.imgDomain) {
            imghost = 随机选择图片域名(config.data.imgDomain);
        } 
    } catch (e) {
        imghost = 'https://img.jgsfnl.com';
    }
}

async function home(filter) {
    // 请求首页分类接口
    let html = await request(`${host}${rule.homeCategory}`);
    let res = JSON.parse(html).data;
    
    let classes = [];
    res.forEach(item => {
        classes.push({
            type_id: item.id.toString(),
            type_name: item.name
        });
    });
    const commonFilter = [{
        "key": "cateId",
        "name": "分类",
        "value": [
            {"v": "", "n": "全部"},
            {"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"},
            {"v": "4", "n": "喜剧"}, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"},
            {"v": "7", "n": "古装"}, {"v": "8", "n": "奇幻"}, {"v": "9", "n": "冒险"},
            {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {"v": "12", "n": "悬疑"},
            {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"},
            {"v": "16", "n": "运动"}, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"},
            {"v": "21", "n": "历史"}, {"v": "22", "n": "音乐"}, {"v": "23", "n": "西部"},
            {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}
        ]
    }, {
        "key": "area",
        "name": "地区",
        "value": [
            {"v": "", "n": "全部"},
            {"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"},
            {"v": "5", "n": "美国"}, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}
        ]
    }, {
        "key": "year",
        "name": "年代",
        "value": [
            {"v": "", "n": "全部"},
            {"v": "162", "n": "2026"}, {"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"},
            {"v": "101", "n": "2022"}, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"},
            {"v": "7", "n": "2019"}, {"v": "2", "n": "2018"}, {"v": "3", "n": "2017"},
            {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}
        ]
    }, {
        "key": "sort",
        "name": "排序",
        "value": [
            {"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}
        ]
    }];

    let filterObj = {};
    classes.forEach(item => {
        if (item.type_id !== '88' && item.type_id !== '99') {
            filterObj[item.type_id] = commonFilter;
        }
    });
    
    let i = 0;
    while (i < classes.length) {
        const isBad = cate_remove.some(word => 
            new RegExp(word, 'i').test(classes[i].type_name)
        );
        if (isBad) {
            classes.splice(i, 1);
        } else {
            i++;
        }
    }
    
    return JSON.stringify({
        class: classes,
        filters: filterObj,
    });
}

async function homeVod() {
    // 请求首页轮播图/推荐列表接口
    let html = await request(`${host}${rule.slideList}?pos_id=88`);
    let res = JSON.parse(html).data;

    let videos = [];
    res.forEach(item => {
        videos.push({
            vod_id: item.jump_id,
            vod_name: item.title,
            vod_pic: `${imghost}${item.thumbnail}`,
            vod_remarks: "",
        });
    });

    let filteredVideos = [];
    videos.forEach(item => {
        const title = item.vod_name;
        const isBadTitle = title_remove.some(word =>
            new RegExp(word, 'i').test(title)
        );
        if (!isBadTitle) {
            filteredVideos.push(item);
        }
    });

    return JSON.stringify({
        list: filteredVideos,
    });
}

async function DyTag(id, pg) {
    // 请求动态标签数据接口
    let url = `${host}${rule.dyTag}?id=${id}&page=${pg}`;
    let html = await request(url);
    let res = JSON.parse(html).data;
    
    if (res) {
        let videos = [];
        res.forEach(item => {
            videos.push({
                vod_id: item.id,
                vod_name: item.title,
                vod_pic: `${imghost}${item.path}`,
                vod_remarks: item.mask || '',
            });
        });
        return videos;
    }
    return [];
}

async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    let videos = [];
    
    if (tid === '99' || tid === 99) {
        videos = await DyTag(70, pg);
    } else {
        let extendParams = extend || {};
        // 请求分类列表接口
        let url = `${host}${rule.crumbList}?fcate_pid=${tid}&category_id=&area=${extendParams.area || ''}&year=${extendParams.year || ''}&type=${extendParams.cateId || ''}&sort=${extendParams.sort || ''}&page=${pg}`;
        
        let html = await request(url);
        let res = JSON.parse(html).data;
        
        if (res) {
            res.forEach(item => {
                videos.push({
                    vod_id: item.id,
                    vod_name: item.title,
                    vod_pic: `${imghost}${item.path}`,
                    vod_remarks: item.mask,
                });
            });
        }
    }
    
    let filteredVideos = [];
    videos.forEach(item => {
        if (!item.vod_name) return;
        
        const title = item.vod_name;
        const isBadTitle = title_remove.some(word =>
            new RegExp(word, 'i').test(title)
        );
        if (!isBadTitle) {
            filteredVideos.push(item);
        }
    });

    return JSON.stringify({
        page: parseInt(pg),
        pagecount: 99999,
        limit: videos.length,
        total: 99999,
        list: filteredVideos
    });
}

async function detail(id) {
    // 请求视频详情接口
    let html = await request(`${host}${rule.detail}?id=${id}`);
    let res = JSON.parse(html).data;
    
    let playForm = [];
    let playUrls = [];
    
    res.source_list_source.forEach(item => {
        const form = item.name;
        let finalForm = form;
        
        if (item.source_list && item.source_list.length > 0 && item.source_list[0].url) {
            let domain = 提取域名(item.source_list[0].url);
            if (domain.length > 8) domain = domain.substring(0, 8);
            finalForm = `${form}(${domain})`;
        }
        
        const isBadLine = line_remove.some(pattern =>
            finalForm.toLowerCase().includes(pattern.toLowerCase())
        );
        
        if (!isBadLine) {
            playForm.push(finalForm);
            
            let urls = [];
            item.source_list.forEach(source => {
                urls.push(`${source.source_name}$${source.url}`);
            });
            playUrls.push(urls.join('#'));
        }
    });
    
    console.log(`【${siteName}】实际线路名称:`, playForm);
    console.log(`【${siteName}】排序规则:`, line_order);
    
    let combined = [];
    playForm.forEach((form, i) => {
        combined.push({form, url: playUrls[i]});
    });
    
    combined.sort((a, b) => {
        const getPri = name => {
            const idx = line_order.findIndex(k => name.toLowerCase().includes(k.toLowerCase()));
            return idx === -1 ? 999 : idx;
        };
        return getPri(a.form) - getPri(b.form);
    });

    let sortedPlayForm = [];
    let sortedPlayUrls = [];
    combined.forEach(item => {
        sortedPlayForm.push(item.form);
        sortedPlayUrls.push(item.url);
    });
    
    console.log(`【${siteName}】排序后线路名称:`, sortedPlayForm);
    
    let play_from = [];
    sortedPlayForm.forEach(item => {
        play_from.push(item.replace(/常规线路/g, '边下边播'));
    });
    
    const vod = {
        "vod_id": id,
        "vod_name": res.title,
        "vod_year": res.year,
        "vod_area": res.area,
        "vod_remarks": res.mask,
        "vod_content": res.description,
        "vod_pic": `${imghost}${res.thumbnail}`,
        "vod_play_from": play_from.join('$$$'),
        "vod_play_url": sortedPlayUrls.join('$$$')
    };

    return JSON.stringify({
        list: [vod]
    });
}

async function play(flag, id, flags) {
    if (id.indexOf(".m3u8") > -1) {
        return JSON.stringify({
            parse: 0,
            url: id
        });
    } else {
        return JSON.stringify({
            parse: 0,
            url: `tvbox-xg:${id}`
        });
    }
}

async function search(wd, quick, pg) {
    let page = pg || 1;
    console.log(`【${siteName}】搜索参数: wd=${wd}, quick=${quick}, pg=${page}`);
    
    let urls = [];
    for (let p = page; p < page + maxPages; p++) {
        urls.push({
            url: `${host}${rule.search}?key=${encodeURIComponent(wd)}&category_id=88&page=${p}&pageSize=20`,
            options: { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 8000 }
        });
    }
    let results = await batchFetch(urls);
    
    let allVideos = [];
    for (let html of results) {
        if (!html) continue;
        let res = JSON.parse(html).data;
        if (res && Array.isArray(res)) {
            res.forEach(item => {
                allVideos.push({
                    vod_id: item.id,
                    vod_name: item.title,
                    vod_pic: `${imghost}${item.thumbnail}`,
                    vod_remarks: item.mask,
                });
            });
        }
    }

    // 你要求的精准关键词匹配过滤
    let filteredVideos = [];
    for (let item of allVideos) {
        if (item.vod_name && new RegExp(wd, "i").test(item.vod_name)) {
            filteredVideos.push(item);
        } else {
            console.log(`【${siteName}】精准搜索过滤: "${item.vod_name}" (不匹配关键词: ${wd})`);
        }
    }

    return JSON.stringify({
        page: page,
        pagecount: 5,
        limit: filteredVideos.length,
        total: 100,
        list: filteredVideos
    });
}


async function request(url, obj) {
    if (!obj) {
        obj = {
            headers: {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        }
    }

    try {
        const result = await req(url, obj);
        return result.content;
    } catch (e) {
        console.error(`请求${url}错误:${e.message}`);
    }
}

function 提取域名(url) {
    const cleanUrl = url.replace(/^(https?:\/\/)?/, '');
    const domainPart = cleanUrl.split('/')[0];
    
    if (domainPart.includes('-')) {
        return domainPart.split('-')[0];
    }
    
    if (domainPart.includes('.')) {
        const dotParts = domainPart.split('.');
        if (dotParts.length > 2) {
            return dotParts[dotParts.length - 2];
        } else if (dotParts.length === 2) {
            return dotParts[0];
        }
    }
    
    return domainPart;
}

function 随机选择图片域名(domains) {
    const domainList = domains.split(',');
    const randomIndex = Math.floor(Math.random() * domainList.length);
    const selectedDomain = domainList[randomIndex].trim();
    return `https://${selectedDomain}`;
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search
    };
}
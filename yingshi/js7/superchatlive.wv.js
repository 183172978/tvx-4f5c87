/**
 * superchatlive 直播爬虫
 * 版本：1.5.0
 * 添加：分类筛选 + 付费直播图标
 */

const baseUrl = 'https://zt.superchat.live';
const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': baseUrl + '/'
};

// ==================== 首页分类（带筛选） ====================
function homeContent(filter) {
    var classes = [
        { type_id: "girls", type_name: "👩 女主播" },
        { type_id: "couples", type_name: "💑 情侣" },
        { type_id: "men", type_name: "👨 男主播" },
        { type_id: "trans", type_name: "⚧ 变性人" }
    ];
    
    // 筛选条件：语言筛选
    var langFilters = [
        { key: "tag", name: "语言筛选", value: [
            { n: "全部", v: "" },
            { n: "🇨🇳 中文", v: "tagLanguageChinese" },
            { n: "🇺🇸 英文", v: "tagLanguageEnglish" },
            { n: "🇯🇵 日文", v: "tagLanguageJapanese" },
            { n: "🇰🇷 韩文", v: "tagLanguageKorean" }
        ] }
    ];
    
    // 为每个分类配置筛选
    var filters = {
        "girls": langFilters,
        "couples": langFilters,
        "men": langFilters,
        "trans": langFilters
    };
    
    return { class: classes, filters: filters };
}

// ==================== 首页推荐 ====================
async function homeVideoContent() {
    var url = baseUrl + '/api/front/models?primaryTag=girls&limit=50';
    var res = await fetch(url, { headers: headers });
    
    if (res.error) return Result.error(res.error || '请求失败');
    
    var data = JSON.parse(res.body);
    var models = data.models || [];
    
    var videos = [];
    for (var i = 0; i < models.length; i++) {
        var model = models[i];
        if (model.isLive) {
            // 添加付费标识
            var remarks = (model.viewersCount || 0) + '人观看';
            if (model.status === 'groupShow') {
                remarks = '🎫 付费秀 | ' + remarks;
            } else if (model.status === 'private') {
                remarks = '🔒 私密秀 | ' + remarks;
            }
            
            videos.push({
                vod_id: baseUrl + '/' + model.username,
                vod_name: model.username,
                vod_pic: model.avatarUrl || '',
                vod_remarks: remarks
            });
        }
    }
    
    return { list: videos };
}

// ==================== 分类内容 ====================
async function categoryContent(tid, pg, filter, extend) {
    var page = parseInt(pg) || 1;
    var limit = 50;
    var offset = limit * (page - 1);
    
    var url = baseUrl + '/api/front/models?primaryTag=' + tid + '&limit=' + limit + '&offset=' + offset;
    
    // 添加语言筛选
    if (extend && extend.tag && extend.tag !== '') {
        url += '&filterGroupTags=[["' + extend.tag + '"]]';
    }
    
    var res = await fetch(url, { headers: headers });
    if (res.error) return Result.error(res.error || '请求失败');
    
    var data = JSON.parse(res.body);
    var models = data.models || [];
    
    var videos = [];
    for (var i = 0; i < models.length; i++) {
        var model = models[i];
        if (model.isLive) {
            // 添加付费标识
            var remarks = (model.viewersCount || 0) + '人观看';
            if (model.status === 'groupShow') {
                remarks = '🎫 付费秀 | ' + remarks;
            } else if (model.status === 'private') {
                remarks = '🔒 私密秀 | ' + remarks;
            }
            
            videos.push({
                vod_id: baseUrl + '/' + model.username,
                vod_name: model.username,
                vod_pic: model.avatarUrl || '',
                vod_remarks: remarks
            });
        }
    }
    
    var total = data.filteredCount || 0;
    var pagecount = Math.ceil(total / limit);
    
    return { list: videos, page: page, pagecount: pagecount, limit: limit, total: total };
}

// ==================== 详情页 ====================
async function detailContent(ids) {
    var url = Array.isArray(ids) ? ids[0] : ids;
    var username = url.replace(baseUrl + '/', '');
    
    // 获取主播详细信息（用于获取付费状态）
    var apiUrl = baseUrl + '/api/front/models?primaryTag=girls&username=' + username + '&limit=1';
    var res = await fetch(apiUrl, { headers: headers });
    
    var remarks = '点击播放';
    if (!res.error) {
        var data = JSON.parse(res.body);
        var model = data.models && data.models[0];
        if (model) {
            if (model.status === 'groupShow') {
                remarks = '🎫 付费秀 - 需要代币';
            } else if (model.status === 'private') {
                remarks = '🔒 私密秀 - 需要邀请';
            } else {
                remarks = '🔴 直播中 - ' + (model.viewersCount || 0) + '人观看';
            }
        }
    }
    
    var vod = {
        vod_id: url,
        vod_name: username,
        vod_pic: '',
        vod_content: '直播间地址：' + url,
        vod_actor: '主播',
        vod_remarks: remarks,
        vod_play_from: '直播播放',
        vod_play_url: '第1集$' + url
    };
    
    return { list: [vod] };
}

// ==================== 搜索 ====================
async function searchContent(key, quick, pg) {
    var url = baseUrl + '/api/front/v4/models/search/group/username?query=' + encodeURIComponent(key) + '&limit=50&primaryTag=girls';
    
    try {
        var res = await fetch(url, { headers: headers });
        if (res.error) return { list: [] };
        
        var data = JSON.parse(res.body);
        var models = data.models || [];
        
        var results = [];
        for (var i = 0; i < models.length; i++) {
            var model = models[i];
            if (model.isLive) {
                var remarks = (model.viewersCount || 0) + '人观看';
                if (model.status === 'groupShow') {
                    remarks = '🎫 付费秀 | ' + remarks;
                } else if (model.status === 'private') {
                    remarks = '🔒 私密秀 | ' + remarks;
                }
                
                results.push({
                    vod_id: baseUrl + '/' + model.username,
                    vod_name: model.username,
                    vod_pic: model.avatarUrl || '',
                    vod_remarks: remarks
                });
            }
        }
        
        return { list: results };
    } catch(e) {
        return { list: [] };
    }
}

// ==================== 播放器 ====================
async function playerContent(flag, id, vipFlags) {
    var playUrl = id;
    
    if (id && id.indexOf('$') !== -1) {
        var parts = id.split('$');
        playUrl = parts[1] || parts[0];
    }
    
    // 使用 wvplayer 模式
    return {
        type: 'wvplayer',
        url: playUrl,
        headers: headers,
        script: `(function(){
            var maxAttempts = 20;
            var attempts = 0;
            
            function tryPlay() {
                var video = document.querySelector('video');
                if (video) {
                    video.play();
                    return;
                }
                
                var playBtn = document.querySelector('.play-btn, .vjs-big-play-button, [data-role="play"], button.play');
                if (playBtn && typeof playBtn.click === 'function') {
                    playBtn.click();
                    return;
                }
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(tryPlay, 500);
                }
            }
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(tryPlay, 1000);
                });
            } else {
                setTimeout(tryPlay, 1000);
            }
        })();`
    };
}

// ==================== 路由配置 ====================
var routes = {
    homeVideoContent: function() { return false; },
    categoryContent: function() { return false; },
    detailContent: function(ids) {
        return Array.isArray(ids) ? ids[0] : ids;
    },
    searchContent: function() { return false; },
    playerContent: function(flag, id, vipFlags) {
        var playUrl = id;
        if (id && id.indexOf('$') !== -1) {
            var parts = id.split('$');
            playUrl = parts[1] || parts[0];
        }
        return playUrl;
    }
};
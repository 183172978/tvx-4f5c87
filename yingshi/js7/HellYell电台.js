/*
* @File     : HellYell电台
* @Author   : Operit
* @Date     : 2026-04-19
* @Comments : HellYell电台 - https://radio.hellyell.com/
@header({
  searchable: 0,
  filterable: 0,
  quickSearch: 0,
  title: 'HellYell电台',
  类型: '听书',
  lang: 'ds',
})
*/

var rule = {
    // 类型: 听书 (电台类归为听书)
    类型: '听书',
    // 源标题
    title: 'HellYell电台',
    // 源主域名
    host: 'https://radio.hellyell.com',
    // 源主页链接
    homeUrl: '/',
    // 一级列表链接 (使用fyclass作为分类标识)
    url: '/fyclass',
    // 搜索链接 (此站点无搜索功能)
    searchUrl: '',
    // 允许搜索(0)、允许快搜(0)、允许筛选(0)
    searchable: 0,
    quickSearch: 0,
    filterable: 0,
    // 请求头
    headers: {
        'User-Agent': 'MOBILE_UA',
        'Referer': 'https://radio.hellyell.com/'
    },
    // 超时时间
    timeout: 10000,
    // 静态分类名称
    class_name: '国际音乐台&中文音乐台&新闻综合台&怀旧电台&汽车电台',
    // 静态分类id (对应JSON文件名)
    class_url: 'foreign-music&chinese-music&news-comprehensive&huaijiu-musiclist&qiche-musiclist',
    
    // 不需要双层列表
    double: false,
    // 首页推荐显示数量
    limit: 10,
    
    // 推荐列表解析 (从中文音乐台获取推荐电台，避免多请求超时)
    推荐: async function() {
        let d = [];
        try {
            const jsonUrl = 'https://radio.hellyell.com/chinese-music.json';
            const data = await request(jsonUrl, {headers: this.headers});
            const stations = JSON.parse(data);
            
            // 提取前6个作为推荐
            const recommendedStations = stations.slice(0, 6);
            
            for (const station of recommendedStations) {
                d.push({
                    vod_name: station.name,
                    vod_pic: 'https://radio.hellyell.com/favicon.ico',
                    vod_remarks: station.recommended ? '推荐' : '中文音乐',
                    vod_id: station.url || ''
                });
            }
        } catch (e) {
            console.log('获取推荐失败:', e.message);
        }
        
        return d;
    },
    
    // 一级列表解析 (按分类获取电台列表)
    一级: async function() {
        let d = [];
        const classId = this.input.class_id || 'chinese-music';
        const className = this.class_name.split('&')[this.class_url.split('&').indexOf(classId)] || '中文音乐台';
        
        try {
            const jsonUrl = `https://radio.hellyell.com/${classId}.json`;
            const data = await request(jsonUrl, {headers: this.headers});
            const stations = JSON.parse(data);
            
            for (const station of stations) {
                d.push({
                    vod_name: station.name,
                    vod_pic: 'https://radio.hellyell.com/favicon.ico',
                    vod_remarks: className,
                    vod_id: station.url || ''
                });
            }
        } catch (e) {
            console.log(`获取${className}列表失败:`, e.message);
        }
        
        return d;
    },
    
    // 二级详情解析 (电台类简单处理)
    二级: async function() {
        const vod_id = this.input.ids || this.input.vod_id || '';
        const vod_name = this.input.vod_name || '未知电台';
        
        return {
            vod_name: vod_name,
            vod_pic: 'https://radio.hellyell.com/favicon.ico',
            type_name: '电台',
            vod_year: '2026',
            vod_area: '网络电台',
            vod_actors: 'HellYell电台',
            vod_director: '',
            vod_content: `电台播放链接: ${vod_id}`,
            vod_play_from: '直播流',
            vod_play_url: `直播$${vod_id}`
        };
    },
    
    // 搜索解析 (此站点无搜索功能)
    搜索: async function() {
        return [];
    },
    
    // 播放解析 (直接返回播放链接)
    play_parse: true,
    lazy: async function() {
        const url = this.input;
        return {
            url: url,
            parse: 0, // 0: 直接播放
            header: this.headers
        };
    }
}
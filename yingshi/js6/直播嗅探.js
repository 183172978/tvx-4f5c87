//@name: 央视新闻直播 (内置版)
//@version: 1.5
//@webSite:zhibo
//@remark: 数据内置,图片请求指向
//@isAV: 0  
const appConfig = {
    headers() {
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
    }
}

// 内置频道数据 [1]
const CHANNEL_DATA = [
    {
        "group": "央视新闻",
        "url": "ysxw",
        "channels": [
            { "name": "CCTV1 综合", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=11200132825562653886", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV1.png" },
            { "name": "CCTV2 财经", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=12030532124776958103", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV2.png" },
            { "name": "CCTV4 中文国际", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=10620168294224708952", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV4.png" },
            { "name": "CCTV6 电影", "url": "https://www.yangshipin.cn/tv/home?pid=600108442", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV6.png" },
            { "name": "CCTV7 国防军事", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=8516529981177953694", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV7.png" },
            { "name": "CCTV9 纪录", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=7252237247689203957", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV9.png" },
            { "name": "CCTV10 科教", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=14589146016461298119", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV10.png" },
            { "name": "CCTV12 社会与法", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=13180385922471124325", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV12.png" },
            { "name": "CCTV13 新闻", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=16265686808730585228", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV13.png" },
            { "name": "CCTV17 农业农村", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=4496917190172866934", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV17.png" },
            { "name": "CCTV4K 超高清", "url": "https://ysxw.cctv.cn/landscape.html?liveRoomNumber=2127841942201075403", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/CCTV4K.png" }
        ]
    },
    {
        "group": "广东频道",
        "url": "gdpd",
        "channels": [
            { "name": "广东卫视", "url": "https://www.gdtv.cn/tvChannelDetail/43", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/GuangdongWeishi.png" },
            { "name": "广东珠江", "url": "https://www.gdtv.cn/tvChannelDetail/44", "logo": "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/GuangdongZhujiang.png" }
        ]
    },
];

/**
 * 获取分类列表 [1]
 */
async function getClassList(args) {
    var backData = new RepVideoClassList()
    try {
        backData.data = CHANNEL_DATA.map(item => ({
            type_id: item.url,
            type_name: item.group,
            hasSubclass: false
        }))
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取视频列表 [1]
 */
async function getVideoList(args) {
    var backData = new RepVideoList()
    try {
        const groupData = CHANNEL_DATA.find(g => g.url === args.url)
        if (groupData) {
            groupData.channels.forEach(item => {
                const video = new VideoDetail()
                video.vod_id = item.url
                video.vod_name = item.name
                video.vod_pic = item.logo
                backData.data.push(video)
            })
        }
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取视频详情 - 修改逻辑：返回同分组下所有频道 [1]
 */
async function getVideoDetail(args) {
    var backData = new RepVideoDetail()
    try {
        const video = new VideoDetail()
        let targetGroup = null
        let currentChannel = null

        // 查找当前频道所属的分组
        for (const group of CHANNEL_DATA) {
            const channel = group.channels.find(c => c.url === args.url)
            if (channel) {
                currentChannel = channel
                targetGroup = group
                break
            }
        }

        if (targetGroup && currentChannel) {
            video.vod_id = args.url
            video.vod_name = currentChannel.name
            video.vod_pic = currentChannel.logo
            video.vod_play_from = targetGroup.group

            // 核心修改：将该分组下所有频道拼接为播放链接字符串
            // 格式为：频道名1$链接1#频道名2$链接2
            video.vod_play_url = targetGroup.channels
                .map(item => `${item.name}$${item.url}`)
                .join('#')
        } else {
            video.vod_name = "未知频道"
        }

        backData.data = video
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取播放地址 [1]
 */
async function getVideoPlayUrl(args) {
    var backData = new RepVideoPlayUrl()
    try {
        backData.sniffer = {
            url: args.url,
            ua: appConfig.headers()['User-Agent'],
            timeOut: 30,
            retry: 2
        }
        backData.headers = appConfig.headers()
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 搜索视频 [1]
 */
async function searchVideo(args) {
    var backData = new RepVideoList()
    try {
        const word = args.searchWord.toLowerCase()
        CHANNEL_DATA.forEach(group => {
            const results = group.channels.filter(c => c.name.toLowerCase().includes(word))
            results.forEach(item => {
                const video = new VideoDetail()
                video.vod_id = item.url
                video.vod_name = item.name
                video.vod_pic = item.logo
                video.vod_remarks = group.group
                backData.data.push(video)
            })
        })
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}
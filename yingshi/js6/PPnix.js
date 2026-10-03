//@name:[直] PPnix
//@version:6
//@webSite:https://www.ppnix.com
//@remark:白猫出品 (增强逻辑版)
//@order:A04
//@codeID:
//@env:
//@isAV:0
//@deprecated:0

const appConfig = {
    _webSite: 'https://www.ppnix.com',
    get webSite() {
        return this._webSite
    },
    set webSite(value) {
        this._webSite = value
    },

    // 统一 UA 和 请求头，参考 PPnix (1).js
    headers(referer) {
        return {
            "Referer": referer || this._webSite + '/cn/',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    },

    _uzTag: '',
    get uzTag() {
        return this._uzTag
    },
    set uzTag(value) {
        this._uzTag = value
    },
}

/**
 * 分类列表
 */
async function getClassList(args) {
    var backData = new RepVideoClassList()
    try {
        backData.data = [
            { type_id: 'movie', type_name: '电影', hasSubclass: false },
            { type_id: 'tv', type_name: '电视剧', hasSubclass: false },
        ]
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取分类视频列表
 */
async function getVideoList(args) {
    var backData = new RepVideoList()
    try {
        // 遵循 PPnix (1).js 的路径规则：/cn/movie/---1-newstime.html
        const page = args.page > 1 ? args.page - 1 : ''
        const url = `${appConfig.webSite}/cn/${args.url}/---${page}-newstime.html`

        const response = await req(url, { headers: appConfig.headers() })
        const $ = cheerio.load(response.data)

        $('.lists-content ul li').each((_, li) => {
            const video = new VideoDetail()
            const $a = $(li).find('a').first()
            
            video.vod_id = $a.attr('href')
            video.vod_name = $a.find('img').attr('alt')
            video.vod_pic = $a.find('img').attr('src')
            video.vod_remarks = $(li).find('.orange, footer').first().text().trim()
            
            const scores = $(li).find('.rate').text().trim()
            if (scores && scores !== '0.0') {
                video.topRightRemarks = '评分 ' + scores
            }

            backData.data.push(video)
        })
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取视频详情 - 移植 PPnix (1).js 的解析逻辑
 */
async function getVideoDetail(args) {
    var backData = new RepVideoDetail()
    try {
        const url = appConfig.webSite + args.url
        const response = await req(url, { headers: appConfig.headers() })
        const $ = cheerio.load(response.data)

        const video = new VideoDetail()
        video.vod_id = args.url
        const titleRaw = $('h1.product-title').text().trim()
        video.vod_name = titleRaw.replace(/\s*\([^)]*\)\s*$/, "")
        video.vod_pic = $('.product-header img').attr('src')
        
        // 提取演员、导演、年份
        video.vod_year = (titleRaw.match(/\((\d{4})\)/) || [])[1] || ""
        video.vod_director = $(".product-excerpt:contains('导演：') span").text().trim()
        video.vod_actor = $(".product-excerpt:contains('主演：') span").text().trim().replace(/\s*\/\s*/g, ",")
        video.vod_content = $(".product-excerpt:contains('简介：')").text().replace('简介：', '').trim()

        // --- 移植 PPnix (1).js 的 m3u8 提取逻辑 ---
        const html = response.data
        const infoId = (html.match(/infoid\s*=\s*(\d+)/) || [])[1] || (args.url.match(/(\d+)\.html/) || [])[1]
        const m3u8Match = html.match(/m3u8\s*=\s*\[(.*?)\]/s)
        
        const episodes = []
        if (m3u8Match) {
            const re = /'([^']*)'|"([^"]*)"/g
            let mm
            while ((mm = re.exec(m3u8Match[1])) !== null) {
                const epName = mm[1] || mm[2]
                if (epName) {
                    // 存储格式：名称$ID|参数|来源URL
                    // 注意：这里将关键参数封装在播放ID中，供 getVideoPlayUrl 使用
                    episodes.push(`${epName}$${infoId}|${encodeURIComponent(epName)}|${encodeURIComponent(url)}`)
                }
            }
        }

        if (episodes.length > 0) {
            video.vod_play_from = "PPnix"
            video.vod_play_url = episodes.join('#')
        }

        backData.data = video
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 获取播放地址 - 移植 PPnix (1).js 的 M3U8 构造
 */
async function getVideoPlayUrl(args) {
    var backData = new RepVideoPlayUrl()
    try {
        // 解码 getVideoDetail 中封装的参数
        const parts = args.url.split('|')
        const infoId = parts[0]
        const param = decodeURIComponent(parts[1])
        const referer = decodeURIComponent(parts[2])

        // 构造 PPnix (1).js 中的 sourceUrl
        const sourceUrl = `${appConfig.webSite}/info/m3u8/${infoId}/${encodeURIComponent(param)}.m3u8`
        
        backData.url = sourceUrl
        backData.headers = appConfig.headers(referer)
        // 优先尝试直接播放，如果失效，UZ 会自动尝试嗅探
        backData.parse = 0 
        
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

/**
 * 搜索视频 - 优化选择器
 */
async function searchVideo(args) {
    var backData = new RepVideoList()
    try {
        const encoded = encodeURIComponent(args.searchWord)
        const pagePart = args.page > 1 ? `-page-${args.page}` : ""
        const url = `${appConfig.webSite}/cn/search/${encoded}--.html${pagePart}`

        const response = await req(url, { headers: appConfig.headers() })
        const $ = cheerio.load(response.data)

        $('.lists-content ul li').each((_, e) => {
            const video = new VideoDetail()
            const $link = $(e).find('a').first()
            
            video.vod_id = $link.attr('href')
            video.vod_name = $link.find('img').attr('alt') || $link.attr('title')
            video.vod_pic = $link.find('img').attr('src')
            video.vod_remarks = $(e).find('footer').text().trim()

            if (video.vod_id && video.vod_name) {
                backData.data.push(video)
            }
        })
    } catch (error) {
        backData.error = error.toString()
    }
    return JSON.stringify(backData)
}

// 保持原样
async function getSubclassList(args) { return JSON.stringify(new RepVideoSubclassList()) }
async function getSubclassVideoList(args) { return JSON.stringify(new RepVideoList()) }
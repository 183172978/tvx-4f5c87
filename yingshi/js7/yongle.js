
// 从壳子内置目录加载cheerio 或者本地自备
import cheerio from 'assets://js/lib/cheerio.min.js';

const baseUrl = "https://ylsp.tv";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

let configFilters = null;
async function init(extend) {
    console.log("init", extend);
    try {
        if (extend.filters) {
           const configFilters=JSON.parse( await req(extend.filters).content)
            console.log("init filters", configFilters);
        }
    } catch (e) {
        console.log("getConfig error", e);
    }


}
function getYearFilter() {
    const years = [{ "n": "全部", "v": "" }];
    const currentYear = new Date().getFullYear().toString();
    for (let y = currentYear; y >= 2011; y--) {
        years.push({ "n": y.toString(), "v": y.toString() });
    }
    years.push({ "n": "更早", "v": "更早" });
    return {
        "key": "year",
        "name": "年份",
        "value": years
    };
}

const OtherFilters = [
    {
        "key": "area", "name": "地区", "value": [
            { "n": "全部", "v": "" }, { "n": "大陆", "v": "大陆" }, { "n": "香港", "v": "香港" },
            { "n": "台湾", "v": "台湾" }, { "n": "日本", "v": "日本" }, { "n": "韩国", "v": "韩国" },
            { "n": "欧美", "v": "欧美" }, { "n": "英国", "v": "英国" }, { "n": "泰国", "v": "泰国" },
            { "n": "其它", "v": "其它" }
        ]
    },
    {
        "key": "lang", "name": "语言", "value": [
            { "n": "全部", "v": "" }, { "n": "国语", "v": "国语" }, { "n": "英语", "v": "英语" },
            { "n": "粤语", "v": "粤语" }, { "n": "韩语", "v": "韩语" }, { "n": "日语", "v": "日语" },
            { "n": "西班牙", "v": "西班牙" }, { "n": "法语", "v": "法语" }, { "n": "德语", "v": "德语" },
            { "n": "意大利语", "v": "意大利语" }, { "n": "泰语", "v": "泰语" }, { "n": "其它", "v": "其它" }
        ]
    },
    {
        ...getYearFilter()
    },
    {
        "key": "letter", "name": "字母", "value": [
            { "n": "字母", "v": "" }, { "n": "A", "v": "A" }, { "n": "B", "v": "B" },
            { "n": "C", "v": "C" }, { "n": "D", "v": "D" }, { "n": "E", "v": "E" },
            { "n": "F", "v": "F" }, { "n": "G", "v": "G" }, { "n": "H", "v": "H" },
            { "n": "I", "v": "I" }, { "n": "J", "v": "J" }, { "n": "K", "v": "K" },
            { "n": "L", "v": "L" }, { "n": "M", "v": "M" }, { "n": "N", "v": "N" },
            { "n": "O", "v": "O" }, { "n": "P", "v": "P" }, { "n": "Q", "v": "Q" },
            { "n": "R", "v": "R" }, { "n": "S", "v": "S" }, { "n": "T", "v": "T" },
            { "n": "U", "v": "U" }, { "n": "V", "v": "V" }, { "n": "W", "v": "W" },
            { "n": "X", "v": "X" }, { "n": "Y", "v": "Y" }, { "n": "Z", "v": "Z" },
            { "n": "0-9", "v": "0-9" }
        ]
    },
    {
        "key": "orderBy", "name": "排序", "value": [
            { "n": "添加时间", "v": "time_add" }, { "n": "更新时间", "v": "time_update" },
            { "n": "人气排序", "v": "hits" }, { "n": "评分排序", "v": "score" }
        ]
    }
]


const myFilters = {
    "1": [
        {
            "key": "type", "name": "类型", "value": [
                { "n": "全部", "v": "" },
                { "n": "动作片", "v": "6" },
                { "n": "喜剧片", "v": "7" },
                { "n": "爱情片", "v": "8" },
                { "n": "科幻片", "v": "9" },
                { "n": "奇幻片", "v": "10" },
                { "n": "恐怖片", "v": "11" },
                { "n": "剧情片", "v": "12" },
                { "n": "战争片", "v": "20" },
                { "n": "纪录片", "v": "21" },
                { "n": "动画片", "v": "26" },
                { "n": "悬疑片", "v": "22" },
                { "n": "冒险片", "v": "23" },
                { "n": "犯罪片", "v": "24" },
                { "n": "惊悚片", "v": "45" },
                { "n": "歌舞片", "v": "46" },
                { "n": "灾难片", "v": "47" },
                { "n": "网络片", "v": "48" }
            ]
        },
        ...OtherFilters

    ],

    "2": [
        {
            "key": "type", "name": "类型", "value": [
                { "n": "全部", "v": "" },
                { "n": "国产剧", "v": "13" },
                { "n": "港台剧", "v": "14" },
                { "n": "日剧", "v": "15" },
                { "n": "韩剧", "v": "33" },
                { "n": "欧美剧", "v": "16" },
                { "n": "泰剧", "v": "34" },
                { "n": "新马剧", "v": "35" },
                { "n": "其他剧", "v": "25" }
            ]
        },
        ...OtherFilters
    ],
    "3": [
        {
            "key": "type", "name": "类型", "value": [
                { "n": "全部", "v": "" },
                { "n": "大陆综艺", "v": "27" },
                { "n": "港台综艺", "v": "28" },
                { "n": "日本综艺", "v": "29" },
                { "n": "韩国综艺", "v": "36" },
                { "n": "欧美综艺", "v": "30" },
                { "n": "新马泰综艺", "v": "37" },
                { "n": "其他综艺", "v": "38" }
            ]
        },
        ...OtherFilters
    ],

    "4": [
        {
            "key": "type", "name": "类型", "value": [
                { "n": "全部", "v": "" },
                { "n": "国产动漫", "v": "31" },
                { "n": "日本动漫", "v": "32" },
                { "n": "韩国动漫", "v": "39" },
                { "n": "港台动漫", "v": "40" },
                { "n": "新马泰动漫", "v": "41" },
                { "n": "欧美动漫", "v": "42" },
                { "n": "其他动漫", "v": "43" }
            ]
        },
        ...OtherFilters
    ]
}
async function home(filter) {
    return JSON.stringify({
        class: [
            { type_id: "1", type_name: "电影" },
            { type_id: "2", type_name: "剧集" },
            { type_id: "3", type_name: "综艺" },
            { type_id: "4", type_name: "动漫" }
        ],
        filters: configFilters ?? myFilters
    });
}


async function category(tid, pg, filter, extend) {
    try {
        let list = [];
        let ext = extend || {};
        let targetId = tid;
        pg = pg || 1;

        if (ext.type && ext.type !== "") {
            targetId = ext.type;
        }
        // 仅当用户没有任何筛选操作时，才赋予后台第一页的默认初值
        if (Object.keys(ext).length === 0) {
            ext.area = '大陆';
            ext.lang = '国语';
            ext.orderBy = 'time_update';
        }
        let by = ext.orderBy || '';
        let area = ext.area || '';
        let lang = ext.lang || '';
        let letter = ext.letter || '';
        let year = ext.year || '';

        // 1-大陆-hits--国语-A---1---2026/
        const url = baseUrl + `/vodshow/${targetId}-${area}-${by}--${lang}-${letter}---${pg}---${year}/`;



        console.log(`永乐正在请求 ${url}`);
        // 3. 执行网络请求并解析数据
        const html = (await req(url)).content;
        const $ = cheerio.load(html);

        $('a.module-item').each((i, el) => {
            const vod_id = $(el).attr('href') || '';
            const vod_name = $(el).find('.module-poster-item-title').text();
            const vod_pic = (baseUrl + $(el).find('.module-item-pic img').attr('data-original')) || '';
            const vod_remarks = $(el).find('.module-item-note').text().trim();

            list.push({
                vod_id,
                vod_name,
                vod_pic,
                vod_remarks
            });
        });
        let pageCount = parseInt(pg);
        const lastPageEl = $('#page a.page-next').eq(1);
        if (lastPageEl.length > 0) {
            const href = lastPageEl.attr('href') || '';
            const cleanHref = href.split('/').filter(Boolean).pop();
            const match = cleanHref.split('-');
            if (match.length > 8) {
                const num = parseInt(match[8]);
                if (!isNaN(num)) {
                    pageCount = num;
                }
            }
        }
        // 4. 返回 JSON 数据
        return JSON.stringify({
            list: list,
            pagecount: pageCount
        });

    } catch (e) {
        console.log(e);
        return JSON.stringify({ list: [] });
    }
}


async function detail(ids) {
    let videoId = Array.isArray(ids) ? ids[0] : ids;
    const url = baseUrl + videoId;

    const html = (await req(url)).content;
    const $ = cheerio.load(html);

    let vod_name = $('.module.module-info').find('.module-info-heading h1').text().trim();
    let vod_pic = baseUrl + $('.module.module-info').find('.module-item-pic img').attr("data-original");
    let vod_content = $('.module-info-content p').text().trim();

    const lines = [];
    $('.module-tab-items-box .module-tab-item').each((i, el) => {
        const lineName = $(el).find('span').text().trim();
        lines.push(lineName);
    });
    const vod_play_from = lines.join("$$$");

    const playlistArray = [];

    $('.module-list').each((lineIndex, poolEl) => {
        const episodes = [];
        // 遍历当前线路下的所有集数 A 标签
        $(poolEl).find('a').each((episodeIndex, epEl) => {
            const name = $(epEl).text().trim();
            const href = $(epEl).attr('href') || '';

            if (name && href) {
                episodes.push(`${name}$${href}`);
            }
        });
        playlistArray.push(episodes.join('#'));
    });

    const vod_play_url = playlistArray.join('$$$');

    const back = {
        vod_id: videoId,
        vod_name: vod_name,
        vod_pic: vod_pic,
        vod_content: vod_content,
        vod_play_from,
        vod_play_url
    };

    return JSON.stringify({
        list: [back]
    });
}
async function search(key, quick) {
    const url = baseUrl + `/vodsearch/-------------/?wd=${key}`;

    const html = (await req(url)).content;
    const $ = cheerio.load(html);
    let list = [];
    $('.module-card-item.module-item').each((i, el) => {
        const vod_id = $(el).find("a.module-card-item-poster").attr('href') || '';
        const vod_name = $(el).find('.module-card-item-title strong').text()
        const vod_pic = (baseUrl + $(el).find('.module-item-pic img').attr('data-original')) || '';
        const vod_remarks = $(el).find('.module-item-note').text().trim()
        list.push({
            vod_id,
            vod_name,
            vod_pic,
            vod_remarks
        });
    })

    return JSON.stringify({
        list: list,
        pagecount: 1  // 假设只有一页
    });
}

async function play(flag, id, vipFlags) {
    const url = baseUrl + id;
    const html = (await req(url)).content;
    const match = html.match(/"url"\s*:\s*"([^"]+?\.m3u8)"/);
    let playUrl = ''
    if (match) {
        // match[1] 就是括号内捕获到的纯链接，replace 用来还原被转义的斜杠
        playUrl = match[1].replace(/\\\//g, '/');
    } else {
        console.error('未找到匹配的链接');
    }
    console.log(playUrl);
    return JSON.stringify({
        parse: 0,        // 0=直接播放
        url: playUrl,         // 真实播放地址
        header: {
            "User-Agent": UA,
            "Referer": baseUrl
        }
    });

}

export default {
    init,
    home,
    category,
    detail,
    search,
    play
};
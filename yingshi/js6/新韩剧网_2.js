const CryptoJS = require("crypto-js");
const axios = require("axios");
const cheerio = require("cheerio");

const _http = axios.create({
    timeout: 15000,
});

const hanjuConfig = {
    host: "https://www.hanju7.com",
    headers: {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.hanju7.com/"
    }
};

/**
 * 核心功能：进入详情页抓取真实的封面图地址
 */
const getPicFromDetail = async (id) => {
    try {
        const response = await _http.get(hanjuConfig.host + id, { headers: hanjuConfig.headers });
        const $ = cheerio.load(response.data);
        let pic = $("div.detail div.pic img").attr("data-original") || "";
        if (pic && !pic.startsWith("http")) pic = "https:" + pic;
        return pic || "https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png";
    } catch (e) {
        return "https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png";
    }
};

const getClasses = () => {
    return [
        { type_id: "1", type_name: "韩剧" },
        { type_id: "3", type_name: "韩国电影" },
        { type_id: "4", type_name: "韩国综艺" },
        { type_id: "hot", type_name: "排行榜" },
        { type_id: "new", type_name: "最新更新" }
    ];
};

const getCategoryList = async (tid, page = 1) => {
    try {
        let url;
        const pg = Math.max(1, parseInt(page));
        const pageSize = 20; // 设定每页 20 条数据
        
        if (['hot', 'new'].includes(tid)) {
            url = `${hanjuConfig.host}/${tid}.html`;
            const response = await _http.get(url, { headers: hanjuConfig.headers });
            const $ = cheerio.load(response.data);
            
            // 获取页面中所有的列表项
            const allItems = $("div.txt ul li").get();
            const total = allItems.length;
            const pageCount = Math.ceil(total / pageSize);
            
            // 执行人工切片分页
            const start = (pg - 1) * pageSize;
            const end = start + pageSize;
            const pageItems = allItems.slice(start, end);

            // 只针对当前页的 20 条数据并发请求详情页抓取图片
            const list = await Promise.all(pageItems.map(async (el) => {
                const a = $(el).find("a");
                const href = a.attr("href");
                if (href) {
                    const pic = await getPicFromDetail(href);
                    return {
                        vod_id: href,
                        vod_name: a.text(),
                        vod_pic: pic,
                        vod_remarks: $(el).find("#actor").text()
                    };
                }
                return null;
            }));
            
            return { list: list.filter(i => i !== null), page: pg, pagecount: pageCount };
        } else {
            // 常规分类本身支持分页（URL 规律为 list/id---page.html）
            url = `${hanjuConfig.host}/list/${tid}---${pg - 1}.html`;
            const response = await _http.get(url, { headers: hanjuConfig.headers });
            const $ = cheerio.load(response.data);
            const list = [];
            $("div.list ul li").each((_, el) => {
                const a = $(el).find("a");
                let pic = a.attr("data-original") || "";
                if (pic && !pic.startsWith("http")) pic = "https:" + pic;
                list.push({
                    vod_id: a.attr("href"),
                    vod_name: a.attr("title"),
                    vod_pic: pic,
                    vod_remarks: $(el).find("span.tip").text()
                });
            });
            return { list, page: pg, pagecount: 100 };
        }
    } catch (e) {
        return { list: [], page: page, pagecount: 1 };
    }
};

const getSearch = async (key) => {
    try {
        const formData = `show=searchkey&keyboard=${encodeURIComponent(key)}`;
        const response = await _http.post(`${hanjuConfig.host}/search/`, formData, {
            headers: {
                ...hanjuConfig.headers,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        });
        const $ = cheerio.load(response.data);
        
        const items = $("div.txt ul li").get();
        // 搜索结果也通过详情页抓取准确图片
        const list = await Promise.all(items.map(async (el) => {
            const a = $(el).find("a");
            const href = a.attr("href");
            if (href) {
                const pic = await getPicFromDetail(href);
                return {
                    vod_id: href,
                    vod_name: a.text(),
                    vod_pic: pic,
                    vod_remarks: $(el).find("#actor").text()
                };
            }
            return null;
        }));

        return { list: list.filter(i => i !== null) };
    } catch (e) {
        return { list: [] };
    }
};

const getDetail = async (id) => {
    try {
        const response = await _http.get(hanjuConfig.host + id, { headers: hanjuConfig.headers });
        const $ = cheerio.load(response.data);
        const playUrls = [];
        
        $("div.play ul li a").each((_, el) => {
            const name = $(el).text();
            const onclick = $(el).attr("onclick") || "";
            const match = onclick.match(/'(.*?)'/);
            if (match) {
                playUrls.push(`${name}$${match[1]}`);
            }
        });

        let pic = $("div.detail div.pic img").attr("data-original") || "";
        if (pic && !pic.startsWith("http")) pic = "https:" + pic;

        return {
            vod_id: id,
            vod_name: $("div.detail div.info dl:eq(0) dd").text(),
            vod_pic: pic,
            type_name: $("div.detail div.info dl:eq(2) dd").text(),
            vod_actor: $("div.detail div.info dl:eq(1) dd").text(),
            vod_remarks: $("div.detail div.info dl:eq(4) dd").text(),
            vod_year: $("div.detail div.info dl:eq(5) dd").text(),
            vod_content: $("div.juqing").text().trim(),
            vod_play_from: $("#playlist").text() || "新韩剧",
            vod_play_url: playUrls.join("#")
        };
    } catch (e) {
        return null;
    }
};

const getPlayUrl = async (pid) => {
    try {
        const res = await _http.get(`${hanjuConfig.host}/u/u1.php?ud=${pid}`, { headers: hanjuConfig.headers });
        const key = CryptoJS.enc.Utf8.parse("my-to-newhan-2025\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0");
        const base64Data = CryptoJS.enc.Base64.parse(res.data);
        const iv = CryptoJS.lib.WordArray.create(base64Data.words.slice(0, 4));
        const ciphertext = CryptoJS.lib.WordArray.create(base64Data.words.slice(4));
        
        const decrypted = CryptoJS.AES.decrypt(
            { ciphertext: ciphertext },
            key,
            { iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
        );
        return decrypted.toString(CryptoJS.enc.Utf8).trim();
    } catch (e) {
        return "";
    }
};

const handleT4Request = async (req) => {
    const { t, ids, play, pg, wd } = req.query; 

    if (play) {
        const url = await getPlayUrl(play);
        return { parse: 0, url: url || "error_url", header: hanjuConfig.headers };
    }
    if (ids) {
        const detail = await getDetail(ids);
        return { list: detail ? [detail] : [] };
    }
    if (wd) {
        return await getSearch(wd);
    }
    if (t) {
        return await getCategoryList(t, pg || 1);
    }
    return { class: getClasses() };
};

module.exports = async (app, opt) => {
    const meta = {
        key: "hanju7",
        name: "新韩剧网[优]",
        type: 4,
        api: "/video/hanju7",
        searchable: 1,
        quickSearch: 1,
        filterable: 0
    };
    app.get(meta.api, async (req, reply) => {
        return await handleT4Request(req);
    });
    opt.sites.push(meta);
};


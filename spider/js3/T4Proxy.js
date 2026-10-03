#!/usr/bin/env node
// ============================================================================
// Spider API - Type 4 风格代理
// ============================================================================

const http = require('http');
const https = require('https');
const { URL } = require('url');
const os = require('os');

// ============================================================================
// 配置常量
// ============================================================================
const SPIDER_API_HOST = 'http://192.168.10.36:9978';
const DEFAULT_SITE_KEY = '';
const REQUEST_TIMEOUT = 30000; // 毫秒

// ============================================================================
// Spider API 客户端
// ============================================================================
class SpiderApiClient {
    constructor(host, timeout = 30000) {
        this.host = host.replace(/\/$/, '');
        this.timeout = timeout;
    }

    configAction(action, extra = {}) {
        return this.post('/spider/config', { action, ...extra });
    }

    execute(key, method, params = {}) {
        return this.post('/spider', { key, method, ...params });
    }

    homeContent(key, filter = true) {
        return this.execute(key, 'homeContent', { filter });
    }

    categoryContent(key, tid, page = 1, filter = true, extend = {}) {
        return this.execute(key, 'categoryContent', {
            tid, pg: page, filter, extend
        });
    }

    detailContent(key, ids) {
        return this.execute(key, 'detailContent', {
            ids: Array.isArray(ids) ? ids : [ids]
        });
    }

    searchContent(key, keyword, page = 1) {
        return this.execute(key, 'searchContent', { wd: keyword, pg: page });
    }

    playerContent(key, flag, id, flags = []) {
        return this.execute(key, 'playerContent', { flag, id, flags });
    }

    post(endpoint, data) {
        return new Promise((resolve, reject) => {
            const targetUrl = this.host + endpoint;
            const parsedUrl = new URL(targetUrl);
            const isHttps = parsedUrl.protocol === 'https:';
            const client = isHttps ? https : http;

            const postData = JSON.stringify(data);
            const options = {
                hostname: parsedUrl.hostname,
                port: parsedUrl.port || (isHttps ? 443 : 80),
                path: parsedUrl.pathname + parsedUrl.search,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Content-Length': Buffer.byteLength(postData)
                },
                timeout: this.timeout
            };

            const req = client.request(options, (res) => {
                let body = '';
                res.setEncoding('utf8');
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(body));
                    } catch (e) {
                        resolve({ code: -1, msg: 'Invalid JSON response' });
                    }
                });
            });

            req.on('error', (e) => {
                resolve({ code: -1, msg: `Request failed: ${e.message}` });
            });

            req.on('timeout', () => {
                req.destroy();
                resolve({ code: -1, msg: 'Request timeout' });
            });

            req.write(postData);
            req.end();
        });
    }
}

// ============================================================================
// Type 4 代理
// ============================================================================
class SpiderApiProxy {
    constructor(client, defaultKey = '') {
        this.client = client;
        this.defaultKey = defaultKey;
    }

    async handle(req, res) {
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        if (req.method === 'OPTIONS') {
            res.statusCode = 204;
            res.end();
            return;
        }

        try {
            const result = await this.dispatch(req);
            res.end(JSON.stringify(result, null, 2));
        } catch (e) {
            res.end(JSON.stringify({ error: e.message }));
        }
    }

    async dispatch(req) {
        const input = await this.getInput(req);

        // 从 PATH_INFO 或 query 参数获取 key
        let key = this.getKeyFromPath(req);
        if (!key) {
            key = input.key || this.defaultKey;
        }

        // 兼容处理：play 参数作为 id 的别名
        if (input.play && !input.id) {
            input.id = input.play;
        }

        // 根据参数特征判断接口类型
        let ac = '';
        
        if (input.wd) {
            // 搜索接口
            ac = 'search';
        } else if (input.t) {
            // 有 t 参数就是分类列表
            ac = 'list';
        } else if (input.ids) {
            // 有 ids 参数就是详情
            ac = 'detail';
        } else if (input.flag && input.id) {
            // 有 flag 和 id 就是播放
            ac = 'play';
        } else if (!key || key === 'config' || input.ac === 'config') {
            // 配置接口
            ac = 'config';
        } else {
            // 默认是首页/列表
            ac = 'list';
        }

        // 处理配置接口
        if (ac === 'config') {
            return await this.getProxiedConfig(req);
        }

        // 验证 key
        if (!key) {
            return { error: '缺少 key 参数' };
        }

        // 调用 Spider API
        let apiResult = null;
        const pg = parseInt(input.pg) || 1;

        // 路由分发
        switch (ac) {
            case 'search':
                apiResult = await this.client.searchContent(key, input.wd, pg);
                break;

            case 'detail':
                const ids = Array.isArray(input.ids) ? input.ids : input.ids.split(',');
                apiResult = await this.client.detailContent(key, ids);
                break;

            case 'play':
                const flags = input.flags ? input.flags.split(',') : [];
                apiResult = await this.client.playerContent(key, input.flag, input.id, flags);
                // 播放接口直接返回原始数据，不需要格式化
                if (apiResult && apiResult.code === 0) {
                    return apiResult.data || apiResult;
                }
                return { error: apiResult?.msg || '请求失败' };

            case 'list':
            default:
                const t = input.t || '';
                const filter = !input.f || input.f === '1';

                if (!t) {
                    apiResult = await this.client.homeContent(key, filter);
                } else {
                    const extend = {};
                    ['area', 'year', 'type', 'class', 'lang'].forEach(field => {
                        if (input[field]) {
                            extend[field] = input[field];
                        }
                    });
                    apiResult = await this.client.categoryContent(key, t, pg, filter, extend);
                }
                break;
        }

        // 返回苹果CMS标准格式
        if (apiResult && apiResult.code === 0) {
            return this.formatMacCmsResponse(apiResult.data, pg);
        }

        // 错误情况
        return { error: apiResult?.msg || '请求失败' };
    }

    getKeyFromPath(req) {
        const pathname = req.url.split('?')[0];
        
        // 移除开头的斜杠并获取第一段路径
        const pathParts = pathname.split('/').filter(p => p);
        
        // 如果有路径段，返回第一个（假设是 key），并进行 URL 解码
        if (pathParts.length > 0) {
            try {
                return decodeURIComponent(pathParts[0]);
            } catch (e) {
                return pathParts[0];
            }
        }
        return '';
    }

    formatMacCmsResponse(data, currentPage = 1) {
        // 获取 list
        const list = data.list || [];
        const listCount = list.length;

        // 从返回数据中获取或动态计算
        const page = data.page ? parseInt(data.page) : currentPage;
        const limit = data.limit ? parseInt(data.limit) : (listCount > 0 ? listCount : 20);

        // 计算总页数：优先使用返回值，否则写死 9999
        const pagecount = data.pagecount ? parseInt(data.pagecount) : 9999;

        // 计算总数：优先使用返回值，否则用 pagecount * limit
        const total = data.total ? parseInt(data.total) : pagecount * limit;

        // 苹果CMS标准返回格式
        const response = {
            page,
            pagecount,
            limit,
            total,
            list
        };

        if (data.class) {
            response.class = data.class;
        }
        if (data.filters) {
            response.filters = data.filters;
        }

        return response;
    }

    async getProxiedConfig(req) {
        const status = await this.client.configAction('status');

        if (status.code !== 0 || !status.data?.sites) {
            return { error: '获取配置失败' };
        }

        const sites = status.data.sites;
        const baseUrl = this.getBaseUrl(req);

        const config = {
            spider: '',
            wallpaper: 'https://深色壁纸.xxooo.cf/',
            warningText: '资源来自网络，仅供学习使用',
            sites: [],
            doh: this.getDefaultDoh(),
            rules: this.getDefaultRules(),
            lives: []
        };

        sites.forEach(site => {
            config.sites.push({
                key: site.key,
                name: site.name,
                api: `${baseUrl}/${site.key}`,
                type: '4',
                searchable: site.searchable ?? 1,
                quickSearch: site.quickSearch ?? 1,
                filterable: site.filterable ?? 1
            });
        });

        return config;
    }

    getBaseUrl(req) {
        const protocol = req.connection.encrypted ? 'https' : 'http';
        const host = req.headers.host || 'localhost';
        return `${protocol}://${host}`;
    }

    getDefaultDoh() {
        return [
            { name: 'Google', url: 'https://dns.google/dns-query', ips: ['8.8.4.4', '8.8.8.8'] },
            { name: 'Cloudflare', url: 'https://cloudflare-dns.com/dns-query', ips: ['1.1.1.1', '1.0.0.1'] }
        ];
    }

    getDefaultRules() {
        return [
            { name: 'lz', hosts: ['vip.lz', 'hd.lz'], regex: ['18.5333'] },
            { name: '非凡', hosts: ['vip.ffzy', 'hd.ffzy'], regex: ['25.0666'] }
        ];
    }

    async getInput(req) {
        // 解析查询参数
        const queryIndex = req.url.indexOf('?');
        const input = {};
        
        if (queryIndex !== -1) {
            const searchParams = new URLSearchParams(req.url.slice(queryIndex + 1));
            for (const [key, value] of searchParams) {
                // 对参数进行 URL 解码
                try {
                    input[key] = decodeURIComponent(value);
                } catch (e) {
                    input[key] = value;
                }
            }
        }

        // 处理 POST body
        if (req.method === 'POST') {
            const body = await this.readBody(req);
            try {
                const jsonBody = JSON.parse(body);
                Object.assign(input, jsonBody);
            } catch (e) {
                // 忽略非 JSON body
            }
        }

        return input;
    }

    readBody(req) {
        return new Promise((resolve) => {
            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', () => resolve(body));
            req.on('error', () => resolve(''));
        });
    }
}

// ============================================================================
// 主入口
// ============================================================================
function main() {
    // 解析命令行参数
    const args = process.argv.slice(2);
    let port = 10998;
    const host = '0.0.0.0';

    // 支持 --port 或 -p 参数
    for (let i = 0; i < args.length; i++) {
        if ((args[i] === '--port' || args[i] === '-p') && args[i + 1]) {
            port = parseInt(args[i + 1]);
            break;
        }
    }

    // 创建客户端和代理
    const client = new SpiderApiClient(SPIDER_API_HOST, REQUEST_TIMEOUT);
    const proxy = new SpiderApiProxy(client, DEFAULT_SITE_KEY);

    // 创建 HTTP 服务器
    const server = http.createServer((req, res) => {
        proxy.handle(req, res);
    });

    server.listen(port, host, () => {
        console.log(`Spider API Type 4 代理服务器已启动`);
        console.log(`监听地址: http://${host}:${port}`);
        
        // 获取局域网IP地址
        const networkInterfaces = os.networkInterfaces();
        const lanIps = [];
        for (const name of Object.keys(networkInterfaces)) {
            for (const net of networkInterfaces[name]) {
                // 跳过内部地址和非IPv4地址
                if (net.family === 'IPv4' && !net.internal) {
                    lanIps.push(net.address);
                }
            }
        }
        
        if (lanIps.length > 0) {
            console.log(`局域网地址:`);
            lanIps.forEach(ip => {
                console.log(`  http://${ip}:${port}`);
            });
        }
        
        console.log(`Spider API: ${SPIDER_API_HOST}`);
        console.log(`\n使用示例:`);
        console.log(`  配置接口: http://localhost:${port}?ac=config`);
        console.log(`  首页接口: http://localhost:${port}/站源key`);
        console.log(`  分类接口: http://localhost:${port}/站源key?t=分类ID&pg=页码`);
        console.log(`  详情接口: http://localhost:${port}/站源key?ids=视频ID`);
        console.log(`  搜索接口: http://localhost:${port}/站源key?wd=关键词&pg=页码`);
        console.log(`  播放接口: http://localhost:${port}/站源key?flag=播放源&id=播放ID`);
        console.log(`            或: http://localhost:${port}/站源key?flag=播放源&play=播放ID`);
        console.log(`\n提示: ac参数可省略，系统会根据其他参数自动识别接口类型`);
        console.log(`筛选参数: area=地区&year=年份&type=类型&class=剧情&lang=语言`);
    });

    server.on('error', (e) => {
        if (e.code === 'EADDRINUSE') {
            console.error(`错误: 端口 ${port} 已被占用,请强制结束app或更换端口后重新运行`);
        } else {
            console.error('服务器错误:', e.message);
        }
        process.exit(1);
    });
}

if (require.main === module) {
    main();
}

module.exports = { SpiderApiClient, SpiderApiProxy };

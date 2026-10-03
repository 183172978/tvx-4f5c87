function main(item) {
    const url = item.url;
    const id = item.id;
    
    // 获取当前时间戳（毫秒）
    const timestamp = Date.now();
    const appVersion = "26000009";
    
    // 构建请求头
    const headers = {
        'AppVersion': '2600000900',
        'TerminalId': 'android',
        'X-UP-CLIENT-CHANNEL-ID': '2600037000-99000-200300220100002',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    };
    
    // 从URL中提取频道ID，如果没有则使用传入的ID
    let pid = id;
    
    // 如果没有ID，尝试从URL中提取
    if (!pid || pid === "undefined" || pid === "null") {
        const uri = ku9.Uri(url);
        const pathSegments = uri.Path.split('/').filter(segment => segment);
        pid = pathSegments[pathSegments.length - 1];
    }
    
    // 如果仍然没有获取到ID，使用默认ID
    if (!pid || isNaN(parseInt(pid))) {
        // 默认频道ID列表
        const defaultChannels = [
            "641886683", // 默认频道ID
            "608807420", // CCTV1综合
            "651632648", // 东方卫视
            "608831231"  // 广东卫视
        ];
        pid = defaultChannels[0];
    }
    
    // 广东卫视特殊处理
    const rateType = (pid == "608831231") ? 2 : 3;
    
    // 生成签名
    const str = timestamp + pid + appVersion;
    const md5 = ku9.md5(str);
    
    const salt = 66666601;
    const suffix = "770fafdf5ba04d279a59ef1600baae98migu6666";
    const sign = ku9.md5(md5 + suffix);
    
    // 构建API请求URL
    const baseURL = "https://play.miguvideo.com/playurl/v1/play/playurl";
    const params = "?sign=" + sign + "&rateType=" + rateType + 
                  "&contId=" + pid + "&timestamp=" + timestamp + "&salt=" + salt;
    
    const api_url = baseURL + params;
    
    // 发送API请求
    let res = ku9.request(api_url, "GET", headers, null, false);
    
    if (res.code == 200 && res.body) {
        try {
            const data = JSON.parse(res.body);
            
            // 检查返回码
            if ((data.code && data.code !== "200") && (data.resultCode && data.resultCode !== "200")) {
                throw new Error("API返回码错误");
            }
            
            if (data && data.body && data.body.urlInfo && data.body.urlInfo.url) {
                let play_url = data.body.urlInfo.url;
                
                // 对URL进行加密处理
                const encrypted_url = get_dd_calcu_url_720p(play_url, pid);
                
                if (encrypted_url) {
                    // 检查是否有播放时间范围参数
                    let final_url = encrypted_url;
                    if (item.playseek) {
                        const parts = item.playseek.split('-');
                        if (parts.length === 2) {
                            const [starttime, endtime] = parts;
                            const separator = encrypted_url.includes('?') ? '&' : '?';
                            final_url = encrypted_url + separator + "playbackbegin=" + starttime + "&playbackend=" + endtime;
                        }
                    }
                    
                    // 返回播放地址
                    return { 
                        url: final_url,
                        headers: {
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36',
                            'Referer': 'https://www.miguvideo.com/'
                        }
                    };
                }
            }
        } catch (e) {
            // API解析失败，继续使用备用方案
        }
    }
    
    // 如果API失败，使用备用代理
    const backup_url = "http://43.136.81.155:8888/" + pid;
    let backup_final_url = backup_url;
    
    // 检查是否有播放时间范围参数
    if (item.playseek) {
        const parts = item.playseek.split('-');
        if (parts.length === 2) {
            const [starttime, endtime] = parts;
            const separator = backup_url.includes('?') ? '&' : '?';
            backup_final_url = backup_url + separator + "playbackbegin=" + starttime + "&playbackend=" + endtime;
        }
    }
    
    return { 
        url: backup_final_url,
        headers: {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36'
        }
    };
}

/**
 * 720p版本URL加密
 */
function get_dd_calcu_url_720p(pu_data_url, program_id) {
    if (!pu_data_url || !program_id) {
        return pu_data_url || "";
    }

    // 检查是否已包含puData参数
    if (!pu_data_url.includes("&puData=") && !pu_data_url.includes("?puData=")) {
        return pu_data_url;
    }

    try {
        // 提取puData参数
        let pu_data = "";
        const url_parts = pu_data_url.split('?');
        const base_url = url_parts[0];
        const query_string = url_parts.length > 1 ? url_parts[1] : "";
        
        if (query_string) {
            const params = query_string.split('&');
            for (const param of params) {
                if (param.startsWith("puData=")) {
                    pu_data = param.substring(7);
                    break;
                }
            }
        }
        
        if (!pu_data) {
            return pu_data_url;
        }
        
        // 生成ddCalcu参数
        const dd_calcu = get_dd_calcu_720p(pu_data, program_id);
        
        // 构建最终URL
        if (query_string) {
            // 移除已存在的ddCalcu参数
            let clean_query = query_string;
            if (clean_query.includes("&ddCalcu=")) {
                const parts = clean_query.split("&ddCalcu=");
                clean_query = parts[0];
                if (parts.length > 1 && parts[1].includes("&")) {
                    clean_query += "&" + parts[1].substring(parts[1].indexOf("&") + 1);
                }
            } else if (clean_query.includes("?ddCalcu=")) {
                const parts = clean_query.split("?ddCalcu=");
                clean_query = parts[0];
                if (parts.length > 1 && parts[1].includes("?")) {
                    clean_query += "?" + parts[1].substring(parts[1].indexOf("?") + 1);
                }
            }
            
            // 添加新的ddCalcu参数
            const separator = clean_query ? "&" : "";
            return base_url + "?" + clean_query + separator + "ddCalcu=" + dd_calcu;
        } else {
            return base_url + "?ddCalcu=" + dd_calcu;
        }
        
    } catch (e) {
        return pu_data_url;
    }
}

/**
 * 720p版本ddCalcu生成
 */
function get_dd_calcu_720p(pu_data, program_id) {
    if (!pu_data || !program_id) {
        return "";
    }

    const keys = "0123456789";
    const dd_calcu = [];
    const pu_data_length = pu_data.length;
    
    for (let i = 0; i < pu_data_length / 2; i++) {
        dd_calcu.push(pu_data[pu_data_length - i - 1]);
        dd_calcu.push(pu_data[i]);
        
        switch (i) {
            case 1:
                dd_calcu.push("e");
                break;
            case 2:
                const date_str = get_current_date_string();
                if (date_str.length > 6) {
                    dd_calcu.push(keys[parseInt(date_str[6])]);
                } else {
                    dd_calcu.push("0");
                }
                break;
            case 3:
                if (program_id.length > 2) {
                    dd_calcu.push(keys[parseInt(program_id[2])]);
                } else {
                    dd_calcu.push("0");
                }
                break;
            case 4:
                dd_calcu.push("0");
                break;
        }
    }
    
    return dd_calcu.join('');
}

/**
 * 获取当前日期字符串 (YYYYMMDD格式)
 */
function get_current_date_string() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    
    return year + month + day;
}

// 导出函数供测试使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        main, 
        get_dd_calcu_url_720p, 
        get_dd_calcu_720p, 
        get_current_date_string 
    };
}
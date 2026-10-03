<?php
$targetUrl = $_GET['url'] ?? '';

if (empty($targetUrl)) {
    header('Content-Type: text/html; charset=utf-8');
    echo '代理运行中，请使用: ?url=视频地址';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    http_response_code(204);
    exit;
}

if (!filter_var($targetUrl, FILTER_VALIDATE_URL)) {
    http_response_code(400);
    echo "无效的 URL";
    exit;
}

try {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $targetUrl,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        CURLOPT_HTTPHEADER => ['Accept: */*'],
        CURLOPT_ENCODING => '',
    ]);
    
    $response = curl_exec($ch);
    
    if ($response === false) {
        throw new Exception(curl_error($ch));
    }
    
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $contentType = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    curl_close($ch);
    
    // 跨域头
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    
    // 检测是否为 m3u8
    $isM3u8 = (
        strpos($contentType, 'mpegurl') !== false ||
        strpos($contentType, 'm3u8') !== false ||
        strpos($targetUrl, '.m3u8') !== false ||
        strpos($response, '#EXTM3U') !== false
    );
    
    if ($isM3u8) {
        header("Content-Type: application/vnd.apple.mpegurl");
        
        // 解析基础 URL
        $parsed = parse_url($targetUrl);
        $base = $parsed['scheme'] . '://' . $parsed['host'] . 
                ($parsed['port'] ? ':' . $parsed['port'] : '') .
                dirname($parsed['path'] ?? '/') . '/';
        
        // 当前代理地址
        $proxyBase = 'http://' . $_SERVER['HTTP_HOST'] . 
                     dirname($_SERVER['SCRIPT_NAME']) . '/proxy.php?url=';
        
        // 重写 m3u8 内容中的链接
        $lines = explode("\n", $response);
        $output = [];
        
        foreach ($lines as $line) {
            $line = trim($line);
            
            // 保留注释和空行
            if (empty($line) || ($line[0] === '#' && strpos($line, '#EXTINF') === false)) {
                $output[] = $line;
                continue;
            }
            
            // 处理媒体链接（非 # 开头）
            if ($line[0] !== '#') {
                // 补全相对路径
                if (strpos($line, 'http') !== 0) {
                    $line = $base . ltrim($line, '/');
                }
                // 包装成代理链接
                $line = $proxyBase . urlencode($line);
            }
            
            $output[] = $line;
        }
        
        echo implode("\n", $output);
        
    } else {
        // 非 m3u8 直接透传
        if ($contentType) header("Content-Type: $contentType");
        http_response_code($httpCode);
        echo $response;
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo "代理失败: " . $e->getMessage();
}
?>

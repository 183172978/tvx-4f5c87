<?php
/** MissAV PHP T4/CMS JSON source */
error_reporting(0);
set_time_limit(0);
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Range');
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { http_response_code(200); exit; }

define('HOST', 'https://missav123.com');
define('HOME', HOST . '/dm247/cn');
define('UA', 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1');

function base_url() {
    $scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https://' : 'http://';
    return $scheme . ($_SERVER['HTTP_HOST'] ?? 'localhost') . ($_SERVER['SCRIPT_NAME'] ?? '/missav.php');
}
function fix_url($url, $base = HOST) {
    $url = html_entity_decode(trim((string)$url), ENT_QUOTES, 'UTF-8');
    $url = stripcslashes(str_replace('\\/', '/', $url));
    if ($url === '') return '';
    if (preg_match('~^https?://~i', $url)) return $url;
    if (strpos($url, '//') === 0) return 'https:' . $url;
    if ($url[0] === '/') { $p = parse_url($base ?: HOST); return ($p['scheme'] ?? 'https') . '://' . ($p['host'] ?? 'missav123.com') . $url; }
    $dir = preg_replace('~/[^/]*$~', '/', $base ?: HOST . '/');
    return $dir . $url;
}
function clean_text($s) { return trim(preg_replace('/\s+/u', ' ', html_entity_decode(strip_tags((string)$s), ENT_QUOTES, 'UTF-8'))); }
function e64($s) { return rtrim(strtr(base64_encode((string)$s), '+/', '-_'), '='); }
function d64($s) { return base64_decode(strtr((string)$s, '-_', '+/') . str_repeat('=', (4 - strlen((string)$s) % 4) % 4)); }
function curl_get($url, $timeout = 25, $headers = null) {
    $headers = $headers ?: ['User-Agent: ' . UA, 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8', 'Referer: ' . HOST . '/'];
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER=>true, CURLOPT_FOLLOWLOCATION=>true, CURLOPT_TIMEOUT=>$timeout, CURLOPT_CONNECTTIMEOUT=>10, CURLOPT_SSL_VERIFYPEER=>false, CURLOPT_SSL_VERIFYHOST=>false, CURLOPT_ENCODING=>'', CURLOPT_HTTPHEADER=>$headers]);
    $body = curl_exec($ch); $ctype = curl_getinfo($ch, CURLINFO_CONTENT_TYPE); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    return ['body'=>($body !== false && $code < 400) ? (string)$body : '', 'ctype'=>$ctype, 'code'=>$code];
}
function hget($url) { $r = curl_get(fix_url($url), 30); return $r['body']; }
function proxy_pic($url) { $url = fix_url($url); return $url ? base_url() . '?img=' . urlencode($url) : ''; }
function allowed_host($host) { return (bool)preg_match('/(^|\.)(missav123\.com|fourhoi\.com|surrit\.com|missav\.com)$/i', (string)$host); }
function output_img($url) {
    $url = fix_url($url); $host = parse_url($url, PHP_URL_HOST);
    if (!$url || !allowed_host($host)) { http_response_code(403); exit; }
    $r = curl_get($url, 20, ['User-Agent: ' . UA, 'Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8', 'Referer: ' . HOST . '/']);
    if ($r['body']) { header('Content-Type: ' . ($r['ctype'] ?: 'image/jpeg')); header('Cache-Control: public, max-age=86400'); echo $r['body']; } else http_response_code(404);
    exit;
}
function proxy_m3u8_url($url) { return base_url() . '?m3u8=' . urlencode(e64($url)); }
function proxy_seg_url($url, $ref) { return base_url() . '?seg=' . urlencode(e64(json_encode(['url'=>$url,'referer'=>$ref], JSON_UNESCAPED_SLASHES))); }
function serve_m3u8($payload) {
    $url = fix_url(d64($payload)); $host = parse_url($url, PHP_URL_HOST);
    if (!$url || !allowed_host($host)) { http_response_code(403); exit; }
    $r = curl_get($url, 25, ['User-Agent: ' . UA, 'Accept: application/x-mpegURL,*/*', 'Referer: ' . HOST . '/']);
    if (!$r['body']) { http_response_code(502); echo 'm3u8 fetch failed'; exit; }
    $base = $url;
    $out = preg_replace_callback('/^(?!#)([^\r\n]+)$/m', function($m) use ($base) {
        $line = trim($m[1]);
        if ($line === '') return $m[0];
        $u = fix_url($line, $base);
        return preg_match('#\.m3u8(\?|$)#i', $u) ? proxy_m3u8_url($u) : proxy_seg_url($u, HOST . '/');
    }, $r['body']);
    $out = preg_replace_callback('/URI="([^"]+)"/i', function($m) use ($base) { return 'URI="' . proxy_seg_url(fix_url($m[1], $base), HOST . '/') . '"'; }, $out);
    header('Content-Type: application/vnd.apple.mpegurl; charset=utf-8'); header('Cache-Control: no-store'); echo $out; exit;
}
function stream_seg($payload) {
    $data = json_decode(d64($payload), true); $url = fix_url($data['url'] ?? ''); $ref = fix_url($data['referer'] ?? HOST . '/'); $host = parse_url($url, PHP_URL_HOST);
    if (!$url || !allowed_host($host)) { http_response_code(403); exit; }
    $headers = ['User-Agent: ' . UA, 'Accept: */*', 'Referer: ' . $ref]; if (!empty($_SERVER['HTTP_RANGE'])) $headers[] = 'Range: ' . $_SERVER['HTTP_RANGE'];
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_FOLLOWLOCATION=>true, CURLOPT_RETURNTRANSFER=>false, CURLOPT_HEADER=>false, CURLOPT_TIMEOUT=>0, CURLOPT_CONNECTTIMEOUT=>10, CURLOPT_SSL_VERIFYPEER=>false, CURLOPT_SSL_VERIFYHOST=>false, CURLOPT_HTTPHEADER=>$headers, CURLOPT_ENCODING=>'', CURLOPT_WRITEFUNCTION=>function($ch,$chunk){ echo $chunk; return strlen($chunk); }, CURLOPT_HEADERFUNCTION=>function($ch,$line){ $name=strtolower(strtok($line, ':')); if (in_array($name, ['content-type','content-length','content-range','accept-ranges'], true)) header(trim($line), false); return strlen($line); }]);
    header('Access-Control-Allow-Origin: *'); header('X-Accel-Buffering: no'); curl_exec($ch); if (curl_errno($ch) && !headers_sent()) { http_response_code(502); echo 'curl error: ' . curl_error($ch); } curl_close($ch); exit;
}

$CLASSES = [
 ['type_id'=>'new','type_name'=>'最近更新'], ['type_id'=>'release','type_name'=>'新作上市'], ['type_id'=>'chinese-subtitle','type_name'=>'中文字幕'], ['type_id'=>'uncensored-leak','type_name'=>'无码流出'], ['type_id'=>'today-hot','type_name'=>'今日热门'], ['type_id'=>'weekly-hot','type_name'=>'本周热门'], ['type_id'=>'monthly-hot','type_name'=>'本月热门'], ['type_id'=>'siro','type_name'=>'SIRO'], ['type_id'=>'fc2','type_name'=>'FC2'], ['type_id'=>'madou','type_name'=>'麻豆'], ['type_id'=>'VR','type_name'=>'VR']
];
function cat_url($t, $pg) { $pg=max(1,intval($pg)); $map=['new'=>'/dm539/cn/new','release'=>'/dm632/cn/release','chinese-subtitle'=>'/dm278/cn/chinese-subtitle','uncensored-leak'=>'/dm816/cn/uncensored-leak','today-hot'=>'/dm296/cn/today-hot','weekly-hot'=>'/dm170/cn/weekly-hot','monthly-hot'=>'/dm266/cn/monthly-hot','siro'=>'/dm36/cn/siro','fc2'=>'/dm475/cn/fc2','madou'=>'/dm63/cn/madou','VR'=>'/cn/genres/VR']; $path=$map[$t] ?? '/dm539/cn/new'; return HOST . $path . ($pg>1 ? '?page='.$pg : ''); }
function search_url($wd,$pg) { $pg=max(1,intval($pg)); return HOME . '/search/' . rawurlencode((string)$wd) . ($pg>1 ? '?page='.$pg : ''); }
function pagecount($html,$cur) { $max=max(1,intval($cur)); if (preg_match_all('/[?&]page=(\d+)/i',$html,$m)) foreach($m[1] as $n) $max=max($max,intval($n)); return min(max($max,$cur),2000); }
function parse_list($html) {
    $list=[];
    if (!preg_match_all('#<div[^>]+class="thumbnail\s+group"[^>]*>[\s\S]*?(?=<div[^>]+class="thumbnail\s+group"|</body>|$)#i', $html, $blocks)) return $list;
    foreach ($blocks[0] as $b) {
        if (!preg_match('#<a[^>]+href="(https?://[^"]+/cn/([a-z0-9][a-z0-9-]+))"#i', $b, $hm)) continue;
        $href=$hm[1]; $id=$hm[2];
        $title=''; if (preg_match('#<img[^>]+alt="([^"]+)"#i',$b,$tm)) $title=clean_text($tm[1]);
        $pic=''; if (preg_match('#<img[^>]+data-src="([^"]+)"#i',$b,$pm)) $pic=$pm[1];
        $remarks=''; if (preg_match('#<span[^>]*class="[^"]*text-nord5[^"]*"[^>]*>(.*?)</span>#is',$b,$rm)) $remarks=clean_text($rm[1]);
        $list[]=['vod_id'=>$id,'vod_name'=>$title ?: strtoupper($id),'vod_pic'=>proxy_pic($pic),'vod_remarks'=>$remarks];
    }
    return $list;
}
function unpack_missav_sources($html) {
    $out=[];
    if (preg_match_all("#eval\\(function\\(p,a,c,k,e,d\\).*?\\('((?:\\\\'|[^'])*)',(\\d+),(\\d+),'([^']*)'\\.split\\('\\|'\\)#s", $html, $ms, PREG_SET_ORDER)) {
        foreach ($ms as $m) {
            $p=stripcslashes($m[1]); $a=intval($m[2]); $c=intval($m[3]); $k=explode('|',$m[4]);
            if ($a < 2 || $a > 36) continue;
            for ($i=$c-1; $i>=0; $i--) {
                $key=base_convert((string)$i,10,$a);
                $val=$k[$i] ?? $key;
                if ($val!=='') $p=preg_replace('/\\b'.preg_quote($key,'/').'\\b/', $val, $p);
            }
            if (preg_match_all("#(source\\w*)='([^']+\\.m3u8[^']*)'#i", $p, $sm, PREG_SET_ORDER)) foreach($sm as $s) $out[$s[1]]=html_entity_decode($s[2],ENT_QUOTES,'UTF-8');
        }
    }
    if (!$out && preg_match_all("#https?://[^\"'\\s<>]+\\.m3u8[^\"'\\s<>]*#i", $html, $m)) foreach($m[0] as $u) $out['播放']=$u;
    return $out;
}
function do_home(){ global $CLASSES; $html=hget(cat_url('new',1)); return ['code'=>1,'msg'=>'ok','class'=>$CLASSES,'filters'=>new stdClass(),'list'=>parse_list($html)]; }
function do_category($t,$pg){ $html=hget(cat_url($t ?: 'new',$pg)); $p=max(1,intval($pg)); return ['code'=>1,'msg'=>'ok','page'=>$p,'pagecount'=>pagecount($html,$p),'limit'=>24,'total'=>pagecount($html,$p)*24,'list'=>parse_list($html)]; }
function do_search($wd,$pg){ $html=hget(search_url($wd,$pg)); $p=max(1,intval($pg)); return ['code'=>1,'msg'=>'ok','page'=>$p,'pagecount'=>pagecount($html,$p),'limit'=>24,'total'=>pagecount($html,$p)*24,'list'=>parse_list($html)]; }
function do_detail($id){ $id=trim((string)$id); if(!$id) return ['code'=>-1,'msg'=>'无效ID','list'=>[]]; $html=hget(HOST.'/cn/'.rawurlencode($id)); if(!$html) return ['code'=>-1,'msg'=>'详情获取失败','list'=>[]];
    $title=$id;$pic='';$desc=''; if(preg_match('/property="og:title"[^>]+content="([^"]+)/i',$html,$m)) $title=clean_text($m[1]); if(preg_match('/property="og:image"[^>]+content="([^"]+)/i',$html,$m)) $pic=$m[1]; if(preg_match('/property="og:description"[^>]+content="([^"]*)/i',$html,$m)) $desc=clean_text($m[1]);
    $srcs=unpack_missav_sources($html); if(!$srcs) return ['code'=>-1,'msg'=>'未找到m3u8','list'=>[]];
    // TVBox 选集只保留一个播放项，避免 source/source842/source1280 显示成多余集数。
    $playUrl = '';
    foreach (['source1280', 'source842', 'source'] as $k) { if (!empty($srcs[$k])) { $playUrl = $srcs[$k]; break; } }
    if (!$playUrl) $playUrl = reset($srcs);
    return ['code'=>1,'msg'=>'ok','list'=>[['vod_id'=>$id,'vod_name'=>$title,'vod_pic'=>proxy_pic($pic),'vod_remarks'=>'m3u8','vod_content'=>$desc,'vod_play_from'=>'MissAV','vod_play_url'=>'播放$'.e64($playUrl)]]]; }
function do_play($payload){ $url=d64($payload); if(!$url || !preg_match('#\.m3u8#i',$url)) $url=$payload; if(!$url) return ['parse'=>1,'url'=>'']; return ['parse'=>0,'url'=>proxy_m3u8_url($url),'header'=>['User-Agent'=>UA,'Referer'=>base_url()]]; }

$ac=$_GET['ac']??''; $t=$_GET['t']??''; $pg=$_GET['pg']??'1'; $id=$_GET['id']??''; $ids=$_GET['ids']??''; $wd=$_GET['wd']??''; $play=$_GET['play']??'';
try {
 if(isset($_GET['img'])) output_img($_GET['img']); if(isset($_GET['m3u8'])) serve_m3u8($_GET['m3u8']); if(isset($_GET['seg'])) stream_seg($_GET['seg']);
 header('Content-Type: application/json; charset=utf-8'); header('Cache-Control: no-store');
 if($play!==''){ echo json_encode(do_play($play),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; }
 if($wd!==''){ echo json_encode(do_search($wd,$pg),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; }
 if(!$ac || $ac==='home'){ echo json_encode(do_home(),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; }
 if($ac==='videolist'){ echo json_encode(do_category($t,$pg),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; }
 if($ac==='detail'){ if($t && !$id && !$ids){ echo json_encode(do_category($t,$pg),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; } $vid=$id ?: (explode(',',$ids)[0]??''); echo json_encode(do_detail($vid),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); exit; }
 echo json_encode(do_home(),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
} catch(Throwable $e){ if(!headers_sent()) header('Content-Type: application/json; charset=utf-8'); echo json_encode(['code'=>-1,'msg'=>$e->getMessage(),'list'=>[]],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); }

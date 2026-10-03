<?php
/**
 * MissAV PHP Spider
 * 移植自 missav (11).js
 * 默认节点 missav.media，支持多域名回退与导航探测
 */
class Spider
{
    private $siteKey = '';
    private $siteType = 0;
    private $baseHost = 'https://missav.media';
    private $defaultHost = 'https://missav.media';
    private $fallbackHosts = [
        'https://missav.media',
        'https://missav.mrst.one',
        'https://missav.ai',
        'https://missav.ws',
        'https://missav.live',
    ];
    private $navUrls = ['https://x99dh.cc', 'https://x99dh.one'];
    private $ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';

    public function init($extend = '')
    {
        $this->baseHost = $this->defaultHost;
        if (is_string($extend) && preg_match('#^https?://#i', trim($extend))) {
            $this->baseHost = rtrim(trim($extend), '/');
        } elseif (is_array($extend) && !empty($extend['host'])) {
            $this->baseHost = rtrim($extend['host'], '/');
        }
        // 后台探测不阻塞；首次请求时 fetchWithHeal 会自愈
        return true;
    }

    public function homeContent($filter = false)
    {
        $classes = [
            ['type_id' => '/dm539/cn/new', 'type_name' => '🔥最近更新'],
            ['type_id' => '/dm301/cn/today-hot', 'type_name' => '⭐今日热门'],
            ['type_id' => '/dm170/cn/weekly-hot', 'type_name' => '📊本週热门'],
            ['type_id' => '/dm273/cn/monthly-hot', 'type_name' => '🏆本月热门'],
            ['type_id' => '/dm278/cn/chinese-subtitle', 'type_name' => '💬中文字幕'],
            ['type_id' => '/dm635/cn/release', 'type_name' => '✨新作上市'],
            ['type_id' => '/dm817/cn/uncensored-leak', 'type_name' => '🔓无码流出'],
            ['type_id' => '/dm597/cn/fc2', 'type_name' => '💎FC2'],
            ['type_id' => '/dm2208642/cn/heyzo', 'type_name' => '👑HEYZO'],
            ['type_id' => '/dm42/cn/tokyohot', 'type_name' => '♨️东京热'],
            ['type_id' => '/dm5199603/cn/1pondo', 'type_name' => '🔞一本道'],
        ];
        return ['class' => $classes, 'filters' => new stdClass()];
    }

    public function homeVideoContent()
    {
        $res = $this->categoryContent('/dm539/cn/new', '1', false, []);
        $list = isset($res['list']) ? array_slice($res['list'], 0, 20) : [];
        return ['list' => $list];
    }

    public function categoryContent($tid, $pg, $filter = false, $extend = [])
    {
        $pg = max(1, intval($pg));
        $route = trim(strval($tid ?: '/dm539/cn/new'));
        if ($route === '' || $route[0] !== '/') {
            $route = '/' . ltrim($route, '/');
        }
        if (preg_match('#^/cn/#i', $route)) {
            $route = '/dm539' . $route;
        }
        $reqUrl = $this->baseHost . $route;
        if ($pg > 1) {
            $reqUrl .= '?page=' . $pg;
        }
        $html = $this->fetchWithHeal($reqUrl);
        $vodList = $this->parseVodList($html);
        $pageCount = count($vodList) >= 12 ? $pg + 1 : $pg;
        return [
            'list' => $vodList,
            'page' => $pg,
            'pagecount' => $pageCount,
            'limit' => count($vodList),
            'total' => 9999,
        ];
    }

    public function detailContent($ids)
    {
        $targetUrl = is_array($ids) ? strval($ids[0] ?? '') : strval($ids);
        $targetUrl = trim($targetUrl);
        if ($targetUrl === '') {
            return ['list' => []];
        }
        if (!preg_match('#^https?://#i', $targetUrl)) {
            $targetUrl = $this->baseHost . (strpos($targetUrl, '/') === 0 ? $targetUrl : '/cn/' . $targetUrl);
        }
        if (preg_match('#/cn/([a-zA-Z0-9_-]+)#i', $targetUrl, $m)) {
            $targetUrl = $this->baseHost . '/cn/' . strtolower($m[1]);
        } else {
            $targetUrl = preg_replace('#https?://[^/]+#i', $this->baseHost, $targetUrl);
        }

        $html = $this->fetchWithHeal($targetUrl);
        if ($html === '' || strlen($html) < 200) {
            return ['list' => []];
        }
        if ($this->isChallengePage($html) && !preg_match('#missav_media-thumbnail|og:image|m3u8\|#i', $html)) {
            return ['list' => []];
        }

        $vodName = '精彩视频';
        if (preg_match('#<title>(.*?)</title>#is', $html, $tm)) {
            $raw = trim(html_entity_decode($tm[1], ENT_QUOTES, 'UTF-8'));
            $parts = explode(' - ', $raw);
            $vodName = trim($parts[0]) ?: $vodName;
        }
        $vodPic = '';
        if (preg_match('#<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']#i', $html, $pm)) {
            $vodPic = trim($pm[1]);
        }

        $sources = $this->extractPlaySources($html);
        $fromList = [];
        $urlList = [];
        if (!empty($sources)) {
            foreach ($sources as $s) {
                $fromList[] = $s['name'];
                $urlList[] = '正片$' . $s['url'];
            }
        } else {
            if (preg_match('#[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}#i', $html, $um)) {
                $u = $um[0];
                $base = 'https://surrit.mrstcdn.store/' . $u;
                $fromList = ['自适应', '1080P', '720P', '480P'];
                $urlList = [
                    '正片$' . $base . '/playlist.m3u8',
                    '正片$' . $base . '/1920x1080/video.m3u8',
                    '正片$' . $base . '/1280x720/video.m3u8',
                    '正片$' . $base . '/720x480/video.m3u8',
                ];
            } else {
                $fromList[] = '页面嗅探';
                $urlList[] = '正片$' . $targetUrl;
            }
        }

        $vod = [
            'vod_id' => $targetUrl,
            'vod_name' => $vodName,
            'vod_pic' => $vodPic,
            'vod_remarks' => 'HD高清',
            'vod_content' => "节点: {$this->baseHost}\n标题：{$vodName}",
            'vod_play_from' => implode('$$$', $fromList),
            'vod_play_url' => implode('$$$', $urlList),
        ];
        return ['list' => [$vod]];
    }

    public function searchContent($key, $quick = false, $pg = '1')
    {
        $pg = max(1, intval($pg));
        $searchUrl = $this->baseHost . '/cn/search/' . rawurlencode($key);
        if ($pg > 1) {
            $searchUrl .= '?page=' . $pg;
        }
        $html = $this->fetchWithHeal($searchUrl);
        $vodList = $this->parseVodList($html);
        return [
            'list' => $vodList,
            'page' => $pg,
            'pagecount' => count($vodList) >= 12 ? $pg + 1 : $pg,
            'limit' => count($vodList),
            'total' => 9999,
        ];
    }

    public function playerContent($flag, $id, $vipFlags = [])
    {
        $playUrl = trim(strval($id));
        $headers = [
            'User-Agent' => $this->ua,
            'Referer' => $this->baseHost . '/',
            'Origin' => $this->baseHost,
            'Accept' => '*/*',
        ];
        if (preg_match('#surrit|mrstcdn#i', $playUrl)) {
            $headers['Referer'] = 'https://missav.ws/';
            $headers['Origin'] = 'https://missav.ws';
        }
        $isDirect = (bool) preg_match('#\.(m3u8|mp4)(\?|$)#i', $playUrl);
        return [
            'parse' => $isDirect ? 0 : 1,
            'jx' => 0,
            'url' => $playUrl,
            'header' => $headers,
        ];
    }

    // ---------------- 内部方法 ----------------

    private function defaultHeaders($extra = [])
    {
        $h = [
            'User-Agent' => $this->ua,
            'Accept' => 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language' => 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection' => 'keep-alive',
            'Referer' => $this->baseHost . '/',
        ];
        return array_merge($h, $extra);
    }

    private function request($url, $optHeaders = [])
    {
        $headers = $this->defaultHeaders($optHeaders);
        $headerLines = [];
        foreach ($headers as $k => $v) {
            $headerLines[] = $k . ': ' . $v;
        }
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_HTTPHEADER => $headerLines,
            CURLOPT_ENCODING => '',
        ]);
        $content = curl_exec($ch);
        $code = intval(curl_getinfo($ch, CURLINFO_HTTP_CODE));
        $final = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL) ?: $url;
        if ($content === false) {
            $content = '';
            $code = -1;
        }
        curl_close($ch);
        return ['code' => $code, 'content' => $content, 'url' => $final];
    }

    private function isChallengePage($html)
    {
        if ($html === '' || strlen($html) < 300) {
            return true;
        }
        if (preg_match('#<title[^>]*>\s*Just a moment#i', $html)) {
            return true;
        }
        if (preg_match('#Enable JavaScript and cookies to continue#i', $html)) {
            return true;
        }
        if (preg_match('#cf-browser-verification|cf_challenge_response|checking your browser before accessing#i', $html)) {
            return true;
        }
        if (strlen($html) < 3000
            && preg_match('#Attention Required|Cloudflare Ray ID|cf-error-details#i', $html)
            && !preg_match('#missav_media-thumbnail|__NEXT_DATA__|<title[^>]*>.*missav#i', $html)
        ) {
            return true;
        }
        return false;
    }

    private function getActiveHost($force = false)
    {
        if (!$force && $this->baseHost && $this->baseHost !== 'https://www.missav888.cc') {
            return $this->baseHost;
        }
        $fromNav = $this->resolveNavSites();
        if ($fromNav) {
            $this->baseHost = $fromNav;
            return $this->baseHost;
        }
        foreach ($this->fallbackHosts as $h) {
            $chk = $this->request($h . '/dm539/cn/new', ['Referer' => $h . '/']);
            if (($chk['code'] === 200)
                && !$this->isChallengePage($chk['content'])
                && strpos($chk['content'], 'thumbnail') !== false
            ) {
                $this->baseHost = $h;
                return $this->baseHost;
            }
        }
        $this->baseHost = $this->defaultHost;
        return $this->baseHost;
    }

    private function resolveNavSites()
    {
        foreach ($this->navUrls as $nav) {
            $res = $this->request($nav);
            $text = $res['content'] ?? '';
            if ($text === '' || $this->isChallengePage($text)) {
                continue;
            }
            if (preg_match_all('#https?://(?:www\.)?missav[a-z0-9.-]+#i', $text, $mm)) {
                $uniq = [];
                foreach ($mm[0] as $h) {
                    $p = parse_url($h);
                    if (!empty($p['scheme']) && !empty($p['host'])) {
                        $uniq[$p['scheme'] . '://' . $p['host']] = true;
                    }
                }
                foreach (array_keys($uniq) as $base) {
                    $chk = $this->request($base . '/dm539/cn/new', ['Referer' => $base . '/']);
                    if (($chk['code'] === 200)
                        && !$this->isChallengePage($chk['content'])
                        && strpos($chk['content'], 'thumbnail') !== false
                    ) {
                        return $base;
                    }
                }
            }
            // Base64 配置块
            if (preg_match_all('#["\']([A-Za-z0-9+/=]{80,})["\']#', $text, $bm)) {
                foreach ($bm[1] as $b) {
                    $decoded = base64_decode($b, true);
                    if ($decoded === false) {
                        continue;
                    }
                    $decoded = rawurldecode($decoded);
                    if (strpos($decoded, 'MissAV') === false || strpos($decoded, '[') === false) {
                        continue;
                    }
                    $siteList = json_decode($decoded, true);
                    if (!is_array($siteList)) {
                        continue;
                    }
                    foreach ($siteList as $item) {
                        if (($item['name'] ?? '') !== 'MissAV') {
                            continue;
                        }
                        $candUrls = [];
                        if (!empty($item['url'])) {
                            $candUrls[] = $item['url'];
                        }
                        if (!empty($item['urls']) && is_array($item['urls'])) {
                            foreach ($item['urls'] as $uObj) {
                                $u = is_array($uObj) ? ($uObj['url'] ?? '') : $uObj;
                                if ($u) {
                                    $candUrls[] = $u;
                                }
                            }
                        }
                        foreach ($candUrls as $cUrl) {
                            $p = parse_url($cUrl);
                            if (empty($p['scheme']) || empty($p['host'])) {
                                continue;
                            }
                            $base = $p['scheme'] . '://' . $p['host'];
                            $chk = $this->request($base . '/dm539/cn/new', ['Referer' => $base . '/']);
                            if (($chk['code'] === 200) && !$this->isChallengePage($chk['content'])) {
                                return $base;
                            }
                        }
                    }
                }
            }
        }
        return null;
    }

    private function fetchWithHeal($targetUrl, $referer = '')
    {
        if ($targetUrl === '') {
            return '';
        }
        if (strpos($targetUrl, '//') === 0) {
            $targetUrl = 'https:' . $targetUrl;
        } elseif (strpos($targetUrl, '/') === 0) {
            $targetUrl = $this->baseHost . $targetUrl;
        }
        for ($attempt = 0; $attempt < 2; $attempt++) {
            $res = $this->request($targetUrl, [
                'Referer' => $referer !== '' ? $referer : ($this->baseHost . '/'),
            ]);
            $content = $res['content'] ?? '';
            if (($res['code'] === 200) && $content !== '' && !$this->isChallengePage($content) && strlen($content) > 500) {
                return $content;
            }
            if ($attempt === 0) {
                $this->getActiveHost(true);
                $targetUrl = preg_replace('#https?://[^/]+#i', $this->baseHost, $targetUrl);
                continue;
            }
            return $content;
        }
        return '';
    }

    private function parseVodList($html)
    {
        $vodList = [];
        $seen = [];
        if ($html === '') {
            return $vodList;
        }
        $navCodes = '/^(new|today-hot|weekly-hot|monthly-hot|chinese-subtitle|release|uncensored-leak|fc2|heyzo|tokyohot|1pondo|siro|luxu|gana|ara|scute|madou|vip|actresses|genres|makers|search|ranking|maan|caribbeancom|caribbeancompr|10musume|pacopacomama|gachinco|xxxav|marriedslash|naughty4610|naughty0930|twav|furuke)$/i';

        // 主匹配：href + 可选 video + img[data-src][alt]
        $re = '#href=["\']([^"\']*/cn/([a-zA-Z0-9][a-zA-Z0-9_-]*))["\'][^>]*>\s*(?:<video[\s\S]*?</video>\s*)?<img[\s\S]*?data-src=["\']([^"\']+)["\'][\s\S]*?alt=["\']([^"\']+)["\']#iu';
        if (preg_match_all($re, $html, $ms, PREG_SET_ORDER)) {
            foreach ($ms as $m) {
                $code = strtolower($m[2] ?? '');
                if ($code === '' || isset($seen[$code]) || preg_match($navCodes, $code)) {
                    continue;
                }
                $seen[$code] = true;
                $pic = trim($m[3] ?? '');
                if ($pic === '') {
                    $pic = 'https://fourhoi.mrstcdn.store/' . $code . '/cover-t.jpg';
                }
                $title = trim(html_entity_decode($m[4] ?? '', ENT_QUOTES, 'UTF-8'));
                if ($title === '' || strtolower($title) === $code) {
                    $title = strtoupper($code);
                }
                $vodList[] = [
                    'vod_id' => $this->baseHost . '/cn/' . $code,
                    'vod_name' => $title,
                    'vod_pic' => $pic,
                    'vod_remarks' => strtoupper($code),
                    'style' => ['type' => 'rect', 'ratio' => 1.78],
                ];
            }
        }

        // 兜底：旧结构 a[href][alt]
        if (empty($vodList)) {
            $re2 = '#<a[^>]+href=["\']([^"\']*/cn/([a-zA-Z0-9][a-zA-Z0-9_-]*))["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>([\s\S]*?)</a>#iu';
            if (preg_match_all($re2, $html, $ms2, PREG_SET_ORDER)) {
                foreach ($ms2 as $m) {
                    $code = strtolower($m[2] ?? '');
                    if ($code === '' || isset($seen[$code]) || preg_match($navCodes, $code)) {
                        continue;
                    }
                    if (preg_match('#actresses|genres|makers|vip|ranking|search#i', $m[1])) {
                        continue;
                    }
                    $seen[$code] = true;
                    $title = trim(html_entity_decode($m[3] ?? '', ENT_QUOTES, 'UTF-8'));
                    if ($title === '') {
                        $title = trim(preg_replace('#<[^>]+>#', '', $m[4] ?? ''));
                    }
                    if ($title === '') {
                        $title = strtoupper($code);
                    }
                    $vodList[] = [
                        'vod_id' => $this->baseHost . '/cn/' . $code,
                        'vod_name' => $title,
                        'vod_pic' => 'https://fourhoi.mrstcdn.store/' . $code . '/cover-t.jpg',
                        'vod_remarks' => strtoupper($code),
                        'style' => ['type' => 'rect', 'ratio' => 1.78],
                    ];
                }
            }
        }
        return $vodList;
    }

    private function int2base($x, $base)
    {
        $chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
        if ($x < 0) {
            return '-' . $this->int2base(-$x, $base);
        }
        if ($x === 0) {
            return '0';
        }
        $res = '';
        while ($x > 0) {
            $res = $chars[$x % $base] . $res;
            $x = intval(floor($x / $base));
        }
        return $res;
    }

    private function unpackPacker($p, $a, $c, $k)
    {
        $d = [];
        while ($c > 0) {
            $c -= 1;
            $key = $this->int2base($c, $a);
            $d[$key] = (isset($k[$c]) && $k[$c] !== '') ? $k[$c] : $key;
        }
        return preg_replace_callback('#\b\w+\b#', function ($m) use ($d) {
            $w = $m[0];
            return array_key_exists($w, $d) ? $d[$w] : $w;
        }, $p);
    }

    private function extractPlaySources($html)
    {
        $sources = [];
        $push = function ($name, $url) use (&$sources) {
            if ($url === '' || !preg_match('#^https?://#i', $url)) {
                return;
            }
            foreach ($sources as $s) {
                if ($s['url'] === $url) {
                    return;
                }
            }
            $sources[] = ['name' => $name, 'url' => $url];
        };

        $unpacked = '';
        if (preg_match('#}\s*\(\s*([\'"])([\s\S]*?)\1\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\'"])(.*?)\5\.split\(\s*([\'"])\|#i', $html, $pr)) {
            try {
                $p = str_replace(["\\'", '\\"'], ["'", '"'], $pr[2]);
                $a = intval($pr[3]);
                $c = intval($pr[4]);
                $k = explode('|', $pr[6]);
                $unpacked = $this->unpackPacker($p, $a, $c, $k);
            } catch (Exception $e) {
                $unpacked = '';
            }
        }

        $text = $unpacked . "\n" . $html;

        // 1) 管道串重构
        if (preg_match('#m3u8\|([a-zA-Z0-9|.\-]+?)\|video#i', $text, $pm)) {
            $s = explode('|', 'm3u8|' . $pm[1] . '|video');
            if (count($s) >= 9) {
                $uuid = $s[5] . '-' . $s[4] . '-' . $s[3] . '-' . $s[2] . '-' . $s[1];
                $tld = $s[6];
                $domain = $s[7];
                $base = "https://{$domain}.{$tld}/{$uuid}";
                $push('自适应', $base . '/playlist.m3u8');
                $push('1080P', $base . '/1920x1080/video.m3u8');
                $push('720P', $base . '/1280x720/video.m3u8');
                $push('480P', $base . '/720x480/video.m3u8');
                $push('360P', $base . '/640x360/video.m3u8');
            }
        }

        // 2) source= 变量
        if (preg_match_all('#\b(source(?:1280|842|720|480)?)\s*=\s*[\'"]([^\'"]+)[\'"]#i', $text, $sms, PREG_SET_ORDER)) {
            foreach ($sms as $sm) {
                $key = strtolower($sm[1]);
                $val = trim(preg_replace('#https?://[^/]+/jmpres/[^/]+/#', 'https://', $sm[2]));
                if (strpos($val, 'm3u8') === false && strpos($val, 'http') === false) {
                    continue;
                }
                if ($key === 'source1280') {
                    $push('1080P超清', $val);
                } elseif ($key === 'source842' || $key === 'source720') {
                    $push('720P高清', $val);
                } elseif ($key === 'source') {
                    $push('原线', $val);
                }
            }
        }

        // 3) UUID 兜底
        if (empty($sources) && preg_match_all('#[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}#i', $text, $ums)) {
            $blacklist = ['snaptrckr', 'user_uuid', 'popunder', 'banner', 'cloudflare', 'randomUUID'];
            foreach ($ums[0] as $u) {
                $idx = strpos($text, $u);
                $ctx = strtolower(substr($text, max(0, $idx - 50), 100));
                $bad = false;
                foreach ($blacklist as $b) {
                    if (strpos($ctx, $b) !== false) {
                        $bad = true;
                        break;
                    }
                }
                if ($bad) {
                    continue;
                }
                $push('自适应', 'https://surrit.mrstcdn.store/' . $u . '/playlist.m3u8');
                $push('1080P', 'https://surrit.mrstcdn.store/' . $u . '/1920x1080/video.m3u8');
                $push('720P', 'https://surrit.mrstcdn.store/' . $u . '/1280x720/video.m3u8');
                $push('480P', 'https://surrit.mrstcdn.store/' . $u . '/720x480/video.m3u8');
                break;
            }
        }
        return $sources;
    }
}

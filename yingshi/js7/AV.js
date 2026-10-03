const API_BASE = 'https://tiktok.xvideos4.tk/api.php';
const NAV = [
  { sort: 'daily',    label: '今日',   href: '/zh-CN/',        icon: '🔥' },
  { sort: 'weekly',   label: '本周',   href: '/zh-CN/weekly/', icon: '📅' },
  { sort: 'monthly',  label: '本月',   href: '/zh-CN/monthly/',icon: '🗓' },
  { sort: 'favorite', label: '全部',   href: '/zh-CN/all/',    icon: '✨' },
];
const CATEGORIES = [
  { id: 'gay',             name: '男同性恋・男娘' },
  { id: 'anime',           name: '动漫 / 二次元' },
  { id: 'lolita',          name: '少女系' },
  { id: 'shaved',          name: '光滑风格' },
  { id: 'kyonyu',          name: '丰胸' },
  { id: 'jk',              name: '女高中生' },
  { id: 'beautiful-girl',  name: '美少女' },
  { id: 'small-breasts',   name: '小胸' },
  { id: 'sm',              name: 'SM 题材' },
  { id: 'masturbation',    name: '自我表达' },
  { id: 'hamedori',        name: '自摄' },
  { id: 'female-pervert',  name: '大胆女性' },
  { id: 'personal-filming',name: '私人拍摄' },
  { id: 'outdoor',         name: '户外场景' },
  { id: 'big-sister',      name: '姐姐' },
  { id: 'incest',          name: '家庭主题' },
  { id: 'married-woman',   name: '已婚女性' },
  { id: 'orgy',            name: '群体场景' },
  { id: 'fellatio',        name: '口部艺术' },
  { id: 'bukkake',         name: '泼洒艺术' },
];
async function apiList({ sort, category, page, q }) {
  const qp = new URLSearchParams({
    action: 'list',
    sort:   sort || 'daily',
    page:   String(page || 1),
  });
  if (category) qp.set('category', category);
  if (q)        qp.set('q', q);
  const res = await fetch(`${API_BASE}?${qp}`, {
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) return null;
  return res.json().catch(() => null);
}

async function apiDetail(id) {
  const qpQ = new URLSearchParams({ action: 'list', sort: 'favorite', page: '1', q: id });
  const res = await fetch(`${API_BASE}?${qpQ}`, {
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) return null;
  const data = await res.json().catch(() => null);
  if (!data?.items?.length) return null;
  return data.items.find(i => i.id === id) || data.items[0] || null;
}

function normalizeItem(item) {
  const videoUrl =
    item.encodedUrl ||
    item.url        ||
    item.videoUrl   ||
    item.directUrl  ||
    item.src        ||
    item.mp4Url     ||
    item.mp4        ||
    item.m3u8Url    ||
    item.m3u8       ||
    '';

  return {
    id:       item.id    || '',
    title:    item.title || '未知',
    thumb:    item.thumb || '',
    videoUrl,
    time:     item.time  || '00:00',
    pv:       String(item.pv      || 0),
    favorite: String(item.favorite || 0),
  };
}

function isHlsUrl(url) {
  if (!url) return false;
  return /\.m3u8|playlist|\/HLS\/|\/hls\//i.test(url);
}

function isMp4Url(url) {
  if (!url) return false;
  return /\.mp4(\?|$)|\.webm(\?|$)|\.ogg(\?|$)/i.test(url);
}
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type':                'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control':               'no-cache',
    },
  });
}
export default {
  async fetch(request) {
    const url    = new URL(request.url);
    const path   = url.pathname;
    const params = url.searchParams;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin':  '*',
          'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
          'Access-Control-Allow-Headers': 'Range, Content-Type',
        }
      });
    }

    try {
      if (path === '/play')        return handlePlay(params);
      if (path === '/api/resolve') return handleResolve(params);
      if (path === '/api/refresh') return handleRefresh(params.get('id') || '');

      if (path.match(/\/movie\//)) {
        const id = path.split('/').filter(Boolean).pop();
        return handleDetail(id);
      }
      if (path === '/search') {
        const q    = params.get('tag') || params.get('q') || '';
        const page = parseInt(params.get('page') || '1', 10);
        return handleList({ sort: 'favorite', category: '', q, page, isSearch: true });
      }
      const catMatch = path.match(/\/category\/([^\/\s?]+)/);
      if (catMatch) {
        const page = parseInt(params.get('page') || '1', 10);
        return handleList({ sort: 'favorite', category: catMatch[1], page });
      }
      const sortMap = {
        '/zh-cn/weekly':  'weekly',  '/zh-CN/weekly':  'weekly',
        '/zh-cn/weekly/': 'weekly',  '/zh-CN/weekly/': 'weekly',
        '/zh-cn/monthly': 'monthly', '/zh-CN/monthly': 'monthly',
        '/zh-cn/monthly/':'monthly', '/zh-CN/monthly/':'monthly',
        '/zh-cn/all':     'favorite','/zh-CN/all':     'favorite',
        '/zh-cn/all/':    'favorite','/zh-CN/all/':    'favorite',
      };
      const sort = sortMap[path] || 'daily';
      const page = parseInt(params.get('page') || '1', 10);
      return handleList({ sort, category: '', page });

    } catch (e) {
      return new Response('Error: ' + e.message + '\n' + e.stack, { status: 500 });
    }
  }
};
async function handleResolve(params) {
  const rawUrl = params.get('url') || '';
  if (!rawUrl || !rawUrl.startsWith('http')) {
    return jsonResponse({ error: 'invalid_url' }, 400);
  }

  let origin = '';
  try { origin = new URL(rawUrl).origin; } catch (_) {}

  const commonHeaders = {
    'User-Agent':
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      + 'AppleWebKit/605.1.15 (KHTML, like Gecko) '
      + 'Version/17.0 Mobile/15E148 Safari/604.1',
    'Referer': origin ? origin + '/' : 'https://chaturbate.xvideos4.tk/',
    'Origin':  origin || 'https://chaturbate.xvideos4.tk',
    'Accept':  'video/mp4,video/webm,application/x-mpegurl,*/*;q=0.9',
  };

  try {
    const ctrl  = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    const res   = await fetch(rawUrl, {
      method: 'HEAD', redirect: 'follow', signal: ctrl.signal, headers: commonHeaders,
    });
    clearTimeout(timer);

    const ct       = res.headers.get('content-type') || '';
    const finalUrl = res.url || rawUrl;
    const isHls    = ct.includes('mpegurl') || ct.includes('x-mpegurl') || isHlsUrl(finalUrl);
    const isMp4    = ct.startsWith('video/') || isMp4Url(finalUrl);
    return jsonResponse({ url: finalUrl, isHls, isMp4, contentType: ct, status: res.status });

  } catch (headErr) {
    try {
      const ctrl2  = new AbortController();
      const timer2 = setTimeout(() => ctrl2.abort(), 8000);
      const res2   = await fetch(rawUrl, {
        method: 'GET', redirect: 'follow', signal: ctrl2.signal, headers: commonHeaders,
      });
      clearTimeout(timer2);

      const ct2       = res2.headers.get('content-type') || '';
      const finalUrl2 = res2.url || rawUrl;

      const isHls2 = ct2.includes('mpegurl') || ct2.includes('x-mpegurl') || isHlsUrl(finalUrl2);
      const isMp42 = ct2.startsWith('video/') || isMp4Url(finalUrl2);
      return jsonResponse({ url: finalUrl2, isHls: isHls2, isMp4: isMp42, contentType: ct2, status: res2.status });

    } catch (getErr) {
      return jsonResponse({
        url: rawUrl, isHls: isHlsUrl(rawUrl), isMp4: isMp4Url(rawUrl), error: getErr.message,
      });
    }
  }
}
async function handleRefresh(id) {
  if (!id) return jsonResponse({ error: 'no id' }, 400);
  try {
    const raw = await apiDetail(id);
    if (!raw) return jsonResponse({ error: 'not_found' }, 404);
    const proxySrc = raw.encodedUrl || raw.url || raw.videoUrl || raw.directUrl || '';
    if (!proxySrc) return jsonResponse({ error: 'no_url' }, 404);
    return jsonResponse({ proxySrc, isHls: isHlsUrl(proxySrc) });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}
async function handleList({ sort, category, q, page, isSearch }) {
  const data     = await apiList({ sort, category, q, page });
  const movies   = (data?.items || []).map(normalizeItem);
  const lastPage = data?.lastPage || page;
  const catLabel = CATEGORIES.find(c => c.id === category)?.name || category;
  const title    = category ? `# ${catLabel}` : (isSearch ? `搜索：${q}` : (NAV.find(n => n.sort === sort)?.label || '今日'));

  return new Response(
    renderLayout(renderList(movies, { sort, category, q, page, lastPage, isSearch }), title, sort),
    { headers: { 'Content-Type': 'text/html;charset=UTF-8' } }
  );
}

async function handleDetail(id) {
  const raw   = await apiDetail(id);
  const movie = raw ? normalizeItem(raw) : {
    id, title: id, thumb: '', videoUrl: '', time: '00:00', pv: '0', favorite: '0'
  };
  return new Response(
    renderLayout(renderDetail(movie), movie.title, ''),
    { headers: { 'Content-Type': 'text/html;charset=UTF-8' } }
  );
}
async function handlePlay(params) {
  const videoUrl = params.get('v') || '';
  if (!videoUrl || !videoUrl.startsWith('http')) {
    return new Response('无效的播放链接', { status: 400 });
  }
  return new Response(null, { status: 302, headers: { Location: videoUrl } });
}
function renderList(movies, { sort, category, q, page, lastPage, isSearch }) {
  const grid = movies.map(m => {
    const thumb      = m.thumb || 'https://placehold.co/300x533/111/333?text=No+Image';
    // 直接跳转 encodedUrl
    const playHref   = m.videoUrl ? m.videoUrl : `/zh-CN/movie/${encodeURIComponent(m.id)}`;
    const playTarget = m.videoUrl ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `
<div class="card">
  <a href="${playHref}"${playTarget} class="card-thumb">
    <img loading="lazy" src="${thumb}" alt="${esc(m.title)}"
         onerror="this.src='https://placehold.co/300x533/111/333?text=No+Image'">
    <span class="badge-time">${esc(m.time)}</span>
  </a>
  <div class="card-body">
    <a href="/zh-CN/movie/${encodeURIComponent(m.id)}" class="card-title-link">
      <h3 class="card-title">${esc(m.title)}</h3>
    </a>
    <div class="card-meta">
      <span>👁 ${esc(m.pv)}</span>
      <span class="fav">❤ ${esc(m.favorite)}</span>
    </div>
  </div>
</div>`;
  }).join('');

  function pageUrl(p) {
    if (isSearch) return `/search?tag=${encodeURIComponent(q || category || '')}&page=${p}`;
    if (category) return `/zh-CN/category/${encodeURIComponent(category)}?page=${p}`;
    return (NAV.find(n => n.sort === sort)?.href || '/zh-CN/') + `?page=${p}`;
  }

  const pagination = (page > 1 || page < lastPage) ? `
<div class="pagination">
  ${page > 1
    ? `<a href="${pageUrl(page-1)}" class="page-btn">← 上一页</a>`
    : `<span class="page-btn disabled">← 上一页</span>`}
  <span class="page-info">第 ${page} / ${lastPage} 页</span>
  ${page < lastPage
    ? `<a href="${pageUrl(page+1)}" class="page-btn">下一页 →</a>`
    : `<span class="page-btn disabled">下一页 →</span>`}
</div>` : '';

  const catChips = CATEGORIES.map(c =>
    `<a href="/zh-CN/category/${c.id}" class="chip${category === c.id ? ' chip-active' : ''}">${esc(c.name)}</a>`
  ).join('');

  const empty = movies.length === 0 ? `
<div class="empty-state">
  <div class="empty-icon">📭</div>
  <div class="empty-text">暂无内容</div>
</div>` : '';

  return `
<div class="page-wrap">
  <div class="search-bar-wrap">
    <form action="/search" method="GET" class="search-form">
      <input type="search" name="tag" placeholder="搜索标签 / 账号…"
             value="${esc(isSearch ? (q || category) : '')}"
             autocomplete="off" enterkeyhint="search">
      <button type="submit" aria-label="搜索">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
      </button>
    </form>
  </div>
  <div class="chips-wrap">
    <div class="chips-scroll">
      <a href="/zh-CN/" class="chip${!category ? ' chip-active' : ''}">全部分类</a>
      ${catChips}
    </div>
  </div>
  ${movies.length > 0 ? `<div class="grid">${grid}</div>${pagination}` : empty}
</div>`;
}
function renderDetail(movie) {
  const thumbSrc = movie.thumb || '';
  const proxySrc = movie.videoUrl || '';
  const videoBlock = proxySrc ? `
<div class="video-player-wrap">
  <a href="${proxySrc}" target="_blank" rel="noopener noreferrer" class="direct-play-link">
    <div class="play-overlay" id="playOverlay">
      ${thumbSrc
        ? `<img class="overlay-poster" src="${thumbSrc}" alt="${esc(movie.title)}">`
        : '<div class="overlay-poster thumb-bg"></div>'}
      <div class="overlay-center">
        <div class="play-btn">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="white"><polygon points="5,3 19,12 5,21"/></svg>
        </div>
        <span class="play-hint">点击直接播放</span>
      </div>
    </div>
  </a>
</div>` : `<div class="no-video"><span>🎬</span><p>视频链接不可用</p></div>`;

  return `
<div class="detail-wrap">
  <a href="javascript:history.back()" class="back-btn">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M19 12H5M12 5l-7 7 7 7"/>
    </svg>
    返回
  </a>
  <div class="detail-card">
    <div class="video-wrap">${videoBlock}</div>
    <div class="detail-body">
      <h1 class="detail-title">${esc(movie.title)}</h1>
      <div class="detail-meta">
        <span>👁 ${esc(movie.pv)}</span>
        <span class="fav">❤ ${esc(movie.favorite)}</span>
        <span>⏱ ${esc(movie.time)}</span>
      </div>
    </div>
  </div>
</div>`;
}
function esc(s) {
  return String(s || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function renderLayout(content, title, activeSort) {
  const navLinks = NAV.map(n =>
    `<a href="${n.href}" class="nav-link${activeSort === n.sort ? ' active' : ''}">${n.label}</a>`
  ).join('');

  const bottomNav = NAV.map(n =>
    `<a href="${n.href}" class="bnav-item${activeSort === n.sort ? ' active' : ''}">
       <span class="bnav-icon">${n.icon}</span>
       <span class="bnav-label">${n.label}</span>
     </a>`
  ).join('');

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#000000">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>${esc(title)} - OTC VIDEO</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#000;--surface:#0d0d0d;--surface2:#161616;--border:rgba(255,255,255,0.07);
  --text:#e8e8e8;--muted:#555;--accent:#e8195a;--accent2:#ff6b9d;
  --font-head:'Syne',sans-serif;--font-body:'Noto Sans SC',sans-serif;
  --radius:14px;--nav-h:56px;--bnav-h:60px;--safe-b:env(safe-area-inset-bottom,0px);
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--font-body);font-size:14px;
  line-height:1.5;-webkit-font-smoothing:antialiased;overflow-x:hidden;}
a{color:inherit;text-decoration:none}
img{display:block;max-width:100%}
button{cursor:pointer;border:none;font-family:inherit}

.topnav{
  position:sticky;top:0;z-index:100;height:var(--nav-h);
  background:rgba(0,0,0,0.85);
  backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
  border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:16px;}
.logo{font-family:var(--font-head);font-size:20px;font-weight:800;
  letter-spacing:-0.5px;white-space:nowrap;flex-shrink:0;}
.logo span{color:var(--accent)}
.topnav-search{
  flex:1;max-width:340px;display:flex;align-items:center;
  background:var(--surface2);border:1px solid var(--border);
  border-radius:10px;overflow:hidden;transition:border-color .2s;}
.topnav-search:focus-within{border-color:rgba(232,25,90,.4)}
.topnav-search input{
  flex:1;background:transparent;border:none;outline:none;
  color:var(--text);font-family:var(--font-body);font-size:13px;padding:8px 12px;}
.topnav-search input::placeholder{color:var(--muted)}
.topnav-search button{
  background:transparent;color:var(--muted);padding:8px 12px;
  display:flex;align-items:center;transition:color .2s;}
.topnav-search button:hover{color:var(--accent2)}
.topnav-links{display:flex;gap:4px;margin-left:auto}
.nav-link{
  padding:6px 14px;border-radius:8px;font-size:13px;font-weight:700;
  color:var(--muted);transition:background .15s,color .15s;white-space:nowrap;}
.nav-link:hover{color:var(--text);background:var(--surface2)}
.nav-link.active{color:#fff;background:var(--accent)}

.bnav{
  position:fixed;bottom:0;left:0;right:0;z-index:100;
  height:calc(var(--bnav-h) + var(--safe-b));padding-bottom:var(--safe-b);
  background:rgba(0,0,0,0.92);
  backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
  border-top:1px solid var(--border);flex-direction:row;align-items:stretch;display:none;}
.bnav-item{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:3px;color:var(--muted);transition:color .15s;
  -webkit-tap-highlight-color:transparent;user-select:none;}
.bnav-item.active{color:var(--accent)}
.bnav-icon{font-size:18px;line-height:1}
.bnav-label{font-size:10px;font-weight:700}

.main-content{min-height:calc(100vh - var(--nav-h))}
.page-wrap{max-width:1400px;margin:0 auto;padding:20px 16px 32px}

.search-bar-wrap{display:none;margin-bottom:16px}
.search-form{
  display:flex;align-items:center;background:var(--surface2);
  border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:border-color .2s;}
.search-form:focus-within{border-color:rgba(232,25,90,.4)}
.search-form input{
  flex:1;background:transparent;border:none;outline:none;color:var(--text);
  font-family:var(--font-body);font-size:15px;padding:13px 16px;min-width:0;}
.search-form input::placeholder{color:var(--muted)}
.search-form button{
  background:var(--accent);color:#fff;padding:0 18px;height:100%;min-height:50px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .15s;}
.search-form button:hover{background:var(--accent2)}

.chips-wrap{
  margin-bottom:20px;
  -webkit-mask:linear-gradient(to right,#000 88%,transparent 100%);
  mask:linear-gradient(to right,#000 88%,transparent 100%);}
.chips-scroll{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
.chips-scroll::-webkit-scrollbar{display:none}
.chip{
  flex-shrink:0;padding:7px 14px;border-radius:999px;font-size:12px;font-weight:700;
  background:var(--surface2);border:1px solid var(--border);color:var(--muted);
  white-space:nowrap;transition:background .15s,color .15s,border-color .15s;
  -webkit-tap-highlight-color:transparent;}
.chip:hover{color:var(--accent2);border-color:rgba(232,25,90,.35)}
.chip-active{background:var(--accent);border-color:var(--accent);color:#fff !important}

.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.card{
  background:var(--surface);border-radius:var(--radius);overflow:hidden;
  border:1px solid var(--border);transition:border-color .2s,transform .2s;will-change:transform;}
.card:hover{border-color:rgba(232,25,90,.35);transform:translateY(-2px)}
.card:active{transform:scale(.97)}
.card-thumb{display:block;position:relative;aspect-ratio:9/16;overflow:hidden;background:var(--surface2)}
.card-thumb img{width:100%;height:100%;object-fit:cover;transition:transform .4s}
.card:hover .card-thumb img{transform:scale(1.05)}
.badge-time{
  position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,.75);color:#fff;
  font-size:10px;font-family:ui-monospace,'SF Mono',monospace;
  padding:2px 6px;border-radius:5px;backdrop-filter:blur(4px);}
.card-body{padding:10px 10px 8px}
.card-title{
  font-size:11px;font-weight:500;color:#ccc;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;line-height:1.45;min-height:32px;margin-bottom:6px;}
.card-title-link{display:block;color:inherit;text-decoration:none}
.card-title-link:hover .card-title{color:var(--accent2)}
.card-meta{display:flex;justify-content:space-between;font-size:10px;color:var(--muted)}
.fav{color:var(--accent2)}

.pagination{
  display:flex;align-items:center;justify-content:center;
  gap:12px;padding:32px 0 8px;flex-wrap:wrap;}
.page-btn{
  display:inline-flex;align-items:center;padding:11px 24px;
  background:var(--surface2);border:1px solid var(--border);
  border-radius:10px;font-size:13px;font-weight:700;color:var(--text);
  transition:background .15s,border-color .15s;-webkit-tap-highlight-color:transparent;}
.page-btn:not(.disabled):hover{background:var(--accent);border-color:var(--accent)}
.page-btn.disabled{opacity:.3;pointer-events:none}
.page-info{font-size:12px;color:var(--muted)}

.empty-state{text-align:center;padding:80px 20px}
.empty-icon{font-size:48px;opacity:.25;margin-bottom:12px}
.empty-text{font-size:16px;font-weight:700;color:var(--muted)}

.detail-wrap{max-width:900px;margin:0 auto;padding:20px 16px 32px}
.back-btn{
  display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;
  color:var(--muted);padding:8px 0;margin-bottom:16px;transition:color .15s;
  -webkit-tap-highlight-color:transparent;min-height:44px;}
.back-btn:hover{color:var(--accent2)}
.detail-card{background:var(--surface);border-radius:20px;overflow:hidden;border:1px solid var(--border)}

.video-wrap{position:relative;background:#000;aspect-ratio:16/9;width:100%;overflow:hidden}
.video-player-wrap{position:relative;width:100%;height:100%}
.direct-play-link{display:block;position:relative;width:100%;height:100%;text-decoration:none}
.play-overlay{
  position:absolute;inset:0;display:flex;align-items:center;
  justify-content:center;cursor:pointer;overflow:hidden;background:rgba(0,0,0,.4);}
.play-overlay:hover{background:rgba(0,0,0,.6)}
.play-btn{
  width:76px;height:76px;border-radius:50%;background:rgba(232,25,90,.88);
  display:flex;align-items:center;justify-content:center;padding-left:4px;
  box-shadow:0 6px 32px rgba(232,25,90,.45);}
.play-hint{font-size:14px;font-weight:700;color:#fff;margin-top:12px}
.overlay-poster{
  position:absolute;inset:0;width:100%;height:100%;
  object-fit:cover;transition:transform .4s ease;}
.no-video{
  width:100%;height:100%;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:10px;color:var(--muted);}

.detail-body{padding:20px}
.detail-title{
  font-family:var(--font-head);font-size:clamp(16px,3vw,22px);
  font-weight:800;line-height:1.3;margin-bottom:12px;}
.detail-meta{display:flex;gap:18px;font-size:13px;color:var(--muted);margin-bottom:20px;flex-wrap:wrap}

@media(min-width:540px){.grid{grid-template-columns:repeat(3,1fr);gap:12px}.card-title{font-size:12px}}
@media(min-width:768px){
  .grid{grid-template-columns:repeat(4,1fr);gap:14px}
  .page-wrap{padding:24px 24px 40px}
  .detail-body{padding:28px 32px}}
@media(min-width:1024px){
  .grid{grid-template-columns:repeat(5,1fr);gap:16px}
  .search-bar-wrap{display:none !important}
  .topnav-search{display:flex}
  .topnav-links{display:flex}
  .bnav{display:none !important}
  .main-content{padding-bottom:0}}
@media(min-width:1280px){.grid{grid-template-columns:repeat(6,1fr)}}
@media(max-width:1023px){
  .topnav-search{display:none}
  .topnav-links{display:none}
  .search-bar-wrap{display:block}
  .bnav{display:flex}
  .main-content{padding-bottom:calc(var(--bnav-h) + var(--safe-b) + 8px)}}
@media(hover:none){
  .card:hover{transform:none}
  .card-thumb img{transition:none}}
</style>
</head>
<body>
<nav class="topnav">
  <a href="/zh-CN/" class="logo">OTC<span>.</span>VIDEO</a>
  <form action="/search" method="GET" class="topnav-search">
    <input type="search" name="tag" placeholder="搜索标签 / 账号…" autocomplete="off">
    <button type="submit" aria-label="搜索">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
      </svg>
    </button>
  </form>
  <div class="topnav-links">${navLinks}</div>
</nav>
<main class="main-content">${content}</main>
<nav class="bnav" aria-label="底部导航">${bottomNav}</nav>
</body>
</html>`;
}
// ==UserScript==
// @name         TVBox 结构分析 (图标右中·弹窗再降1.5cm)
// @namespace    http://tampermonkey.net/
// @version      3.3
// @description  弹窗再下移1.5厘米，高度自动匹配
// @author       you
// @match        *://*/*
// @run-at       document-end
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    if (document.getElementById('tvbox-analyzer-btn')) return;

    // ========== 悬浮图标（右侧中部） ==========
    const btn = document.createElement('div');
    btn.id = 'tvbox-analyzer-btn';
    btn.textContent = '📺';
    btn.style.cssText = `
        position: fixed !important;
        top: 50% !important;
        right: 10px !important;
        transform: translateY(-50%) !important;
        width: 44px !important;
        height: 44px !important;
        background: #e91e63 !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 24px !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        z-index: 2147483647 !important;
        cursor: pointer !important;
        user-select: none !important;
        margin: 0 !important;
        padding: 0 !important;
    `;
    btn.addEventListener('mouseenter', () => btn.style.transform = 'translateY(-50%) scale(1.15)');
    btn.addEventListener('mouseleave', () => btn.style.transform = 'translateY(-50%) scale(1)');
    btn.addEventListener('touchstart', () => btn.style.transform = 'translateY(-50%) scale(0.95)', { passive: true });
    btn.addEventListener('touchend', () => btn.style.transform = 'translateY(-50%) scale(1)');

    btn.onclick = function () {
        const old = document.getElementById('tvbox-analyzer-modal');
        if (old) old.remove();
        runAnalysis();
    };
    document.body.appendChild(btn);

    // ========== 分析逻辑（不变） ==========
    function runAnalysis() {
        try {
            const getSelector = function (el, root = document.body, depth = 3) {
                if (!el || el.nodeType !== 1) return '';
                const parts = [];
                let cur = el, level = 0;
                while (cur && cur.nodeType === 1 && cur !== root && cur.tagName.toLowerCase() !== 'html' && cur.tagName.toLowerCase() !== 'body' && level < depth) {
                    let sel = cur.tagName.toLowerCase();
                    if (cur.id) {
                        sel += '#' + cur.id;
                        parts.unshift(sel);
                        level = depth;
                    } else if (cur.className && typeof cur.className === 'string') {
                        const cls = cur.className.trim().split(/\s+/).filter(c => c && !c.includes(':') && !c.includes('active') && !c.includes('hover') && !c.includes('current')).slice(0, 2);
                        if (cls.length) sel += '.' + cls.join('.');
                    }
                    parts.unshift(sel);
                    cur = cur.parentNode;
                    level++;
                }
                return parts.join(' ');
            };
            const preview = (text) => text ? text.replace(/\s+/g, ' ').trim().substring(0, 35) : '';

            let report = `【TVBox 深度结构分析 (影视/听书通用)】\n分析URL: ${location.href}\n\n`;
            const nav = document.querySelector("nav, .nav, .header, .menu, header");
            report += `▶ 顶部主分类: ${nav ? getSelector(nav) : "未检测到明显导航栏"}\n\n`;

            const imgLinks = Array.from(document.querySelectorAll('img'))
                .map(img => img.closest('a, li, .item, .list-item, .vodlist_item'))
                .filter(Boolean);
            const containerCount = new Map();
            imgLinks.forEach(el => {
                if (el && el.parentElement) {
                    const p = el.parentElement;
                    containerCount.set(p, (containerCount.get(p) || 0) + 1);
                }
            });
            const bestContainer = [...containerCount.entries()].reduce((a, b) => b[1] > a[1] ? b : a, [null, 0]);

            if (bestContainer[0]) {
                const container = bestContainer[0];
                const sampleItem = container.firstElementChild;
                report += '▶ 列表配置 (categoryContent/searchContent)\n';
                report += `  容器: ${getSelector(container, document.body, 5)}\n`;
                const titleEl = sampleItem.querySelector('.title, .name, h1, h2, h3, h4, p');
                const imgEl = sampleItem.querySelector('img');
                const linkEl = sampleItem.querySelector('a') || sampleItem.closest('a');
                const remarkEl = sampleItem.querySelector('.remark, .status, .ep, .score, .pic-text, span');
                report += `  标题: ${titleEl ? getSelector(titleEl, container) : '无'} (预览:${preview(titleEl?.innerText)})\n`;
                report += `  图片: ${imgEl ? getSelector(imgEl, container) : '无'} (预览:${imgEl ? imgEl.src || imgEl.getAttribute('data-src') || imgEl.getAttribute('data-original') : '空'})\n`;
                report += `  链接: ${linkEl ? getSelector(linkEl, container) : '无'} (预览:${linkEl ? linkEl.href : '空'})\n`;
                report += `  备注: ${remarkEl ? getSelector(remarkEl, container) : '无'} (预览:${preview(remarkEl?.innerText)})\n\n`;
            } else {
                report += '▶ 列表配置: 未检测到明显结构\n\n';
            }

            report += '▶ 筛选/分类配置 (filter)\n';
            const candidateRows = Array.from(document.querySelectorAll('div, ul, dl, .filter, .tags, .screen'))
                .filter(el => !el.closest('nav, header, .header'));
            const filterRows = [];
            candidateRows.forEach(row => {
                const children = Array.from(row.children).filter(c => ['A', 'SPAN', 'LI'].includes(c.tagName));
                if (children.length >= 3 && children.every(c => {
                    const t = c.innerText.trim();
                    return t.length > 0 && t.length <= 8;
                })) filterRows.push(row);
            });
            const uniqueRows = filterRows.filter(el => !filterRows.some(other => other !== el && el.contains(other)));
            if (uniqueRows.length) {
                uniqueRows.slice(0, 6).forEach((row, idx) => {
                    const sample = row.querySelector('a, li, span.item') || row.firstElementChild;
                    report += `  [${idx + 1}] 容器: ${getSelector(row, document.body, 4)}\n`;
                    report += `      子项: ${sample ? getSelector(sample, row) : '?'} (预览: ${preview(row.innerText)})\n`;
                });
            } else report += '  未检测到明显筛选行\n\n';

            report += '\n▶ 详情页基础信息 (detailContent)\n';
            const h1 = document.querySelector('h1');
            let detailBlock = h1 ? h1.closest('div, section, article, .detail, .vod-detail') || document.body : document.body;
            if (h1) {
                let p = h1.parentElement;
                if (p && p.innerText.length < 50) p = p.parentElement;
                if (p && p.innerText.length < 100) p = p.parentElement;
                detailBlock = p || detailBlock;
            }
            const findField = (keywords) => {
                const nodes = Array.from(detailBlock.querySelectorAll('*')).filter(el => el.children.length === 0 && el.textContent.trim());
                for (const node of nodes) {
                    if (keywords.some(k => node.textContent.includes(k))) {
                        return node.parentElement?.textContent.length < 40 ? node.parentElement : node;
                    }
                }
                return null;
            };
            const posterImg = detailBlock.querySelector('img');
            const statusEl = findField(['状态', '更新', '完结', '连载', '集', '期']);
            const directorEl = findField(['导演', '主演', '演播', '播音', '作者']);
            const typeEl = findField(['类型', '分类', '频道', '标签']);
            const descEl = document.querySelector('.desc, .content, .summary, .intro, article') || findField(['简介', '剧情', '摘要', '大纲']);

            report += `  标题: ${h1 ? getSelector(h1, document.body, 4) : '无'} (预览: ${preview(h1?.innerText)})\n`;
            report += `  图片: ${posterImg ? getSelector(posterImg, document.body, 4) : '无'}\n`;
            report += `  状态: ${statusEl ? getSelector(statusEl, document.body, 4) : '无'} (预览: ${preview(statusEl?.innerText)})\n`;
            report += `  导/演: ${directorEl ? getSelector(directorEl, document.body, 4) : '无'} (预览: ${preview(directorEl?.innerText)})\n`;
            report += `  类型: ${typeEl ? getSelector(typeEl, document.body, 4) : '无'} (预览: ${preview(typeEl?.innerText)})\n`;
            report += `  简介: ${descEl ? getSelector(descEl, document.body, 4) : '无'} (预览: ${preview(descEl?.innerText)})\n\n`;

            report += '▶ 播放列表结构 (playList/playUrl)\n';
            const playLists = Array.from(document.querySelectorAll('ul, ol, .list, .chapter-list, .episodes, .playlist, .vod_play_list'));
            let bestPlay = null, max = 0;
            playLists.forEach(list => {
                const items = list.querySelectorAll('li, .item, a');
                if (items.length > max && items.length > 1) {
                    max = items.length;
                    bestPlay = list;
                }
            });
            if (bestPlay) {
                const sample = bestPlay.querySelector('li, .item, a, div');
                report += `  列表容器: ${getSelector(bestPlay, document.body, 5)}\n`;
                if (sample) {
                    const link = sample.querySelector('a') || sample.closest('a');
                    report += `  单集节点: ${getSelector(sample, bestPlay)}\n`;
                    report += `  选集标题: ${getSelector(sample.querySelector('.title, span') || sample, bestPlay)} (预览: ${preview(sample?.innerText)})\n`;
                    report += `  选集链接: ${link ? getSelector(link, bestPlay) : '同单集节点'} (预览: ${link ? link.href : '可能为js跳转'})\n`;
                }
            } else report += '  未检测到选集/播放列表结构\n';

            // ========== 弹窗：再降 1.5cm（45px），高度缩短 25px ==========
            const modal = document.createElement('div');
            modal.id = 'tvbox-analyzer-modal';
            modal.style.cssText = 'position:fixed;top:calc(5% + 45px);left:5%;width:90%;height:calc(85% - 25px);background:#fff;z-index:999999;box-shadow:0 10px 30px rgba(0,0,0,0.5);border-radius:10px;display:flex;flex-direction:column;font-size:14px;color:#333;font-family:sans-serif;';
            modal.innerHTML = `
                <div style="padding:15px;background:#f0f0f0;border-radius:10px 10px 0 0;display:flex;justify-content:space-between;align-items:center;">
                    <strong style="color:#e91e63;">TVBox 结构分析(通用版)</strong>
                    <div>
                        <button id="tvb-copy" style="padding:5px 10px;background:#4CAF50;color:#fff;border:none;border-radius:5px;margin-right:10px;">复制</button>
                        <button id="tvb-close" style="padding:5px 10px;background:#f44336;color:#fff;border:none;border-radius:5px;">关闭</button>
                    </div>
                </div>
                <textarea id="tvb-result" style="flex:1;width:100%;border:none;padding:15px;box-sizing:border-box;font-family:monospace;font-size:12px;resize:none;outline:none;" readonly>${report}</textarea>
            `;
            document.body.appendChild(modal);
            document.getElementById('tvb-close').onclick = () => modal.remove();
            document.getElementById('tvb-copy').onclick = () => {
                const ta = document.getElementById('tvb-result');
                ta.select();
                document.execCommand('copy');
                alert('✅ 规则已复制到剪贴板！');
            };
        } catch (e) {
            alert('解析出错: ' + e.message);
        }
    }
})();
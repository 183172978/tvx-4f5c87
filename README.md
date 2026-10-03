
## 线上视频源（drpy 规则）

- `drpy/drpy2.min.js`：TVBox 壳子加载 drpy 规则的引擎（type=3 的 api）
- `spider/js/*.js`：142 个 drpy 视频源规则（影视 / 短剧 / 动漫）
- `index.json` 的 sites 即引用这些规则：`{"type":3, "api":"<Pages>/drpy/drpy2.min.js", "ext":"<Pages>/spider/js/xxx.js"}`

壳子填接口地址后可直接使用这些源。增删源：往 `spider/js/` 加/删 js 文件，并在 `index.json` 的 sites 里同步增删对应条目，push 后 1～5 分钟生效。

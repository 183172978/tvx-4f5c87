# TVBox 在线接口

给影视仓 / OK影视Pro / NewBox / EasyBox / MediaMix / UZN 等 TVBox 系壳子用的在线接口配置，
通过 GitHub Pages 托管，拿到一个稳定的接口地址。

## 接口地址

GitHub Pages 启用后，把下面两行里的 `你的用户名` / `仓库名` 换成实际值：

- Pages 地址：`https://你的用户名.github.io/tvbox-interface/index.json`
- 国内加速（jsDelivr）：`https://cdn.jsdelivr.net/gh/你的用户名/tvbox-interface@main/index.json`

把上面任一地址填到壳子的「设置 → 接口 / 线路 / 配置地址」里即可。

## 如何替换示例站

`index.json` 里带 📝 标记的都是占位示例，正式使用前请替换：

1. **sites（站点）**：把 `api` 换成你自己的苹果 CMS 地址
   （格式如 `https://你的站/api.php/provide/vod/`），`name` 改成站名，
   `key` 改成不重复的英文标识。`type: 1` = 苹果 CMS JSON 接口。
   - `searchable: 1` 允许搜索，`quickSearch: 1` 允许快捷搜索，
     `filterable: 1` 允许分类筛选。
2. **parses（解析）**：把 `url` 换成你的解析接口地址，
   `type: 0` 为普通解析，`type: 1` 为 JSON 解析。
3. 改完后 push 到仓库，Pages / jsDelivr 约 1～5 分钟生效，
   壳子里重新拉取接口即可。

## 文件说明

- `index.json`：接口主配置（站点、解析、DOH、播放器参数、去广告规则）
- `README.md`：本说明

## 注意

- 仓库需设为 Public，GitHub Pages 免费版只支持公开仓库。
- 不要在公开仓库里放带账号密码的私有解析地址。

# IPTV 频道自动更新

每天**北京时间 05:00** 自动抓取上游 m3u 订阅源，检测每条流的有效性（仅保留 **IPv4 可达、能正常出流** 的频道），按分类生成播放列表并自动提交。

## 播放列表

| 分类 | 订阅链接 |
|------|----------|
| 全部 | `output/all.m3u` |
| CCTV | `output/cctv.m3u` |
| 卫视 | `output/weishi.m3u` |
| 体育 | `output/sports.m3u` |
| 影视 | `output/movies.m3u` |
| 少儿动漫 | `output/kids.m3u` |
| 新闻资讯 | `output/news.m3u` |
| 音乐 | `output/music.m3u` |
| 纪实科教 | `output/documentary.m3u` |
| 港澳台 | `output/hmt.m3u` |
| 日韩 | `output/japan_korea.m3u` |
| 欧美 | `output/western.m3u` |
| 地方台 | `output/local.m3u` |
| 综合其他 | `output/others.m3u` |

在播放器（如 PotPlayer、VLC、TiviMate）中直接添加上述 m3u 链接即可。

## 工作原理

1. **抓取**（`scripts/fetch.py`）：读取 `sources.txt` 中的上游订阅源（含 iptv-org 全量索引约11000条），解析 m3u 并按 URL 去重。
2. **检测**（`scripts/check.py`）：40 并发逐条验证——仅 `http/https`、域名必须有 IPv4 解析（IPv6 直接丢弃）、HTTP 拉流超时 12 秒内能出数据、`.m3u8` 必须含 `#EXTM3U`。不满足的直接剔除。
3. **分类**（`scripts/build.py`）：地区源频道优先按来源文件归入地区分类，全量源按 tvg-id 国家码归入地区分类，其余按频道名称关键词归入 14 个分类，生成带 `group-title` 的 m3u。CCTV、卫视分类内同一频道的多条线路会自动合并为「CCTV-1、CCTV-1 备用1、…」。
4. **定时**：GitHub Actions 每天 21:00 UTC（北京时间 05:00）运行，检测通过后自动 commit 回本仓库。也可在 Actions 页面手动触发（workflow_dispatch）。

## 上游来源

- [iptv-org](https://github.com/iptv-org/iptv)（全量索引约11000条、中国区、各题材分类及港澳台/日韩/欧美地区公开源）
- [best-fan/iptv-sources](https://github.com/best-fan/iptv-sources)（CCTV/卫视多线路源）
- [BurningC4/Chinese-IPTV](https://github.com/BurningC4/Chinese-IPTV)（中国移动 IPv4 源）

## 说明

- 频道可用性每天都会变化，当日检测通过的不代表永久有效。
- 仅收录 IPv4 可达的源；IPv6 源已被过滤。
- 本项目仅做公开 m3u 源的聚合与可用性检测，不托管任何视频内容。

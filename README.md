# IPTV 频道自动更新（CCTV 精简版）

每天**北京时间 04:00** 自动抓取 CCTV 上游 m3u 订阅源，检测每条流的有效性（仅保留 **IPv4 可达、能正常出流** 的频道），生成播放列表并自动提交。

## 播放列表

| 分类 | 订阅链接 |
|------|----------|
| CCTV | `output/cctv.m3u` |
| 全部（同 CCTV） | `output/all.m3u` |

在播放器（如 PotPlayer、VLC、TiviMate）中直接添加上述 m3u 链接即可。

## 工作原理

1. **抓取**（`scripts/fetch.py`）：读取 `sources.txt` 中的 CCTV 上游订阅源（best-fan/iptv-sources 的 CCTV 多线路源），解析 m3u 并按 URL 去重。
2. **检测**（`scripts/check.py`）：40 并发逐条验证——仅 `http/https`、域名必须有 IPv4 解析（IPv6 直接丢弃）、HTTP 拉流超时 12 秒内能出数据、`.m3u8` 必须含 `#EXTM3U`。不满足的直接剔除。
3. **分类**（`scripts/build.py`）：只保留名称含 CCTV 的频道，同一频道的多条线路会自动合并为「CCTV-1、CCTV-1 备用1、…」，生成带 `group-title` 的 m3u。
4. **定时**：GitHub Actions 每天 20:00 UTC（北京时间 04:00）运行，检测通过后自动 commit 回本仓库。也可在 Actions 页面手动触发（workflow_dispatch）。

## 上游来源

- [best-fan/iptv-sources](https://github.com/best-fan/iptv-sources)（CCTV 多线路源：`cn_cctv.m3u8`、`cn_all.m3u8`）

## 说明

- 频道可用性每天都会变化，当日检测通过的不代表永久有效。
- 仅收录 IPv4 可达的源；IPv6 源已被过滤。
- 本项目仅做公开 m3u 源的聚合与可用性检测，不托管任何视频内容。

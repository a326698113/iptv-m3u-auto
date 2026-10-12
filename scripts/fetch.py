#!/usr/bin/env python3
"""抓取上游 m3u 订阅源，解析并去重，输出 work/channels.json。

用法: python scripts/fetch.py
"""
import json
import os
import re
import sys

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
os.makedirs(WORK, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def load_sources():
    srcs = []
    with open(os.path.join(BASE, "sources.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                srcs.append(line)
    return srcs


def parse_m3u(text, source_url):
    """解析 m3u 文本，返回 [{name, url, group, tvg_id}]。"""
    channels = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            # 取名称（最后一个逗号之后）、group-title、tvg-id
            name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
            group = ""
            m = re.search(r'group-title="([^"]*)"', line)
            if m:
                group = m.group(1)
            tvg_id = ""
            m = re.search(r'tvg-id="([^"]*)"', line)
            if m:
                tvg_id = m.group(1)
            # 下一行非空且非注释即为播放地址
            url = ""
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt and not nxt.startswith("#"):
                    url = nxt
                    break
                j += 1
            if url and url.startswith("http"):
                channels.append({"name": name or tvg_id or url,
                                 "url": url, "group": group,
                                 "tvg_id": tvg_id, "source": source_url})
            i = j
        i += 1
    return channels


def main():
    all_channels = []
    seen = set()
    for src in load_sources():
        try:
            r = requests.get(src, headers=HEADERS, timeout=30)
            r.raise_for_status()
            chs = parse_m3u(r.text, src)
            added = 0
            for c in chs:
                if c["url"] not in seen:
                    seen.add(c["url"])
                    all_channels.append(c)
                    added += 1
            print(f"源 {src}: 解析 {len(chs)} 条，新增 {added} 条")
        except Exception as e:
            print(f"源 {src} 抓取失败: {e}", file=sys.stderr)
    out = os.path.join(WORK, "channels.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_channels, f, ensure_ascii=False)
    print(f"共 {len(all_channels)} 条去重后频道，写入 {out}")


if __name__ == "__main__":
    main()

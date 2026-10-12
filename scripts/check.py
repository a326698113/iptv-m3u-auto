#!/usr/bin/env python3
"""有效性检测：只保留 IPv4 可达、HTTP 能出流的频道。

规则：
- 仅 http/https；IPv6 字面地址直接丢弃；域名无 IPv4 解析结果则丢弃
- HTTP GET（stream），超时内拿到 200/206 且有数据即算可用；
  .m3u8 额外要求内容含 #EXTM3U
- 并发检测，单链接超时约 12 秒

用法: python scripts/check.py
输入 work/channels.json，输出 work/checked.json
"""
import json
import os
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
TIMEOUT = 12
WORKERS = 40


def has_ipv4(host):
    """主机是否有 IPv4 可用。IPv6 字面地址直接返回 False；
    域名则只接受能解析出 IPv4 的（AF_INET）。注：调用方传入的是
    urlparse().hostname，已去掉端口和 IPv6 方括号。"""
    if ":" in host:  # IPv6 字面量
        return False
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        return len(infos) > 0
    except socket.gaierror:
        return False


def check_one(ch):
    url = ch["url"]
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return None, "bad_scheme"
        if not has_ipv4(p.hostname):
            return None, "no_ipv4"
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                           stream=True, allow_redirects=True) as r:
            if r.status_code not in (200, 206):
                return None, f"http_{r.status_code}"
            # 读一小段确认真的在出流
            chunk = next(r.iter_content(chunk_size=4096), b"")
            if not chunk:
                return None, "empty_body"
            if url.lower().split("?")[0].endswith(".m3u8"):
                head = chunk.decode("utf-8", errors="ignore")
                # 有些 m3u8 首包不足，尽量多读一点
                if "#EXTM3U" not in head.upper():
                    extra = b""
                    for c in r.iter_content(chunk_size=16384):
                        extra += c
                        if len(extra) > 32768:
                            break
                    if "#EXTM3U" not in (head + extra.decode("utf-8", errors="ignore")).upper():
                        return None, "bad_m3u8"
        ok = dict(ch)
        ok["checked"] = "ok"
        return ok, "ok"
    except requests.exceptions.ConnectTimeout:
        return None, "connect_timeout"
    except requests.exceptions.ReadTimeout:
        return None, "read_timeout"
    except StopIteration:
        return None, "empty_body"
    except Exception as e:
        return None, f"error_{type(e).__name__}"


def main():
    with open(os.path.join(WORK, "channels.json"), encoding="utf-8") as f:
        channels = json.load(f)
    print(f"待检测 {len(channels)} 条，并发 {WORKERS}")
    ok_list, stat = [], {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(check_one, c): c for c in channels}
        done = 0
        for fu in as_completed(futs):
            done += 1
            ok, reason = fu.result()
            stat[reason] = stat.get(reason, 0) + 1
            if ok:
                ok_list.append(ok)
            if done % 200 == 0:
                print(f"  进度 {done}/{len(channels)}，可用 {len(ok_list)}")
    out = os.path.join(WORK, "checked.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ok_list, f, ensure_ascii=False)
    print(f"检测完成：可用 {len(ok_list)}/{len(channels)}，写入 {out}")
    top = sorted(stat.items(), key=lambda x: -x[1])[:8]
    print("失败原因 top:", ", ".join(f"{k}={v}" for k, v in top))


if __name__ == "__main__":
    main()

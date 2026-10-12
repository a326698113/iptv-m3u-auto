#!/usr/bin/env python3
"""按频道名称关键词分类，生成 output/ 下的分类 m3u 文件。

用法: python scripts/build.py
输入 work/checked.json，输出 output/all.m3u 及各分类文件 + stats.json
"""
import json
import os
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

# (分类名, 文件名, 关键词) —— 按顺序匹配，命中即归入
CATEGORIES = [
    ("CCTV", "cctv.m3u", ["cctv"]),
    ("卫视", "weishi.m3u", ["卫视"]),
    ("体育", "sports.m3u", ["体育", "运动", "sports", "espn", "足球", "篮球", "网球", "nba", "高尔夫", "赛车", "健身", "武术", "台球", "棋牌"]),
    ("影视", "movies.m3u", ["电影", "影视", "剧场", "电视剧", "影院", "movie", "cinema", "film"]),
    ("少儿动漫", "kids.m3u", ["少儿", "卡通", "动漫", "动画", "kids", "cartoon", "anime", "亲子"]),
    ("新闻资讯", "news.m3u", ["新闻", "资讯", "news", "cnn", "bbc", "nhk", "半岛"]),
    ("音乐", "music.m3u", ["音乐", "music", "mtv", "演唱会", "mv"]),
    ("纪实科教", "documentary.m3u", ["纪实", "科教", "探索", "地理", "历史", "documentary", "discovery", "geographic", "animal", "科技"]),
    ("港澳台", "hmt.m3u", ["凤凰", "phoenix", "tvb", "翡翠", "明珠", "澳视", "香港", "台湾", "澳门", "hk ", " rthk", "有线"]),
    ("地方台", "local.m3u", ["北京", "上海", "广东", "深圳", "广州", "江苏", "浙江", "湖南", "湖北", "四川", "山东", "河南", "福建", "安徽", "江西", "辽宁", "吉林", "黑龙江", "河北", "山西", "陕西", "甘肃", "青海", "宁夏", "新疆", "西藏", "云南", "贵州", "广西", "海南", "重庆", "天津", "内蒙古"]),
]

OTHER = ("综合其他", "others.m3u")


def categorize(name, group):
    text = f"{name} {group}".lower()
    for cat, _, kws in CATEGORIES:
        for kw in kws:
            if kw.lower() in text:
                return cat
    return OTHER[0]


def write_m3u(path, channels, group_name=None):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for c in channels:
            grp = group_name or c.get("cat", "")
            safe_name = c["name"].replace(",", "，").replace("\n", " ")
            f.write(f'#EXTINF:-1 group-title="{grp}",{safe_name}\n{c["url"]}\n')


def main():
    with open(os.path.join(WORK, "checked.json"), encoding="utf-8") as f:
        channels = json.load(f)
    buckets = {}
    for c in channels:
        cat = categorize(c.get("name", ""), c.get("group", ""))
        c["cat"] = cat
        buckets.setdefault(cat, []).append(c)

    order = [c[0] for c in CATEGORIES] + [OTHER[0]]
    for cat in order:
        chs = buckets.get(cat, [])
        if not chs:
            continue
        fname = dict([(c[0], c[1]) for c in CATEGORIES] + [OTHER])[cat]
        write_m3u(os.path.join(OUT, fname), chs, cat)

    # 全量
    all_chs = [c for cat in order for c in buckets.get(cat, [])]
    write_m3u(os.path.join(OUT, "all.m3u"), all_chs)

    bj = timezone(timedelta(hours=8))
    stats = {
        "updated": datetime.now(bj).strftime("%Y-%m-%d %H:%M"),
        "total": len(all_chs),
        "categories": {cat: len(buckets.get(cat, [])) for cat in order if buckets.get(cat)},
    }
    with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"分类完成：共 {len(all_chs)} 条")
    for cat in order:
        n = len(buckets.get(cat, []))
        if n:
            print(f"  {cat}: {n} 条")


if __name__ == "__main__":
    main()

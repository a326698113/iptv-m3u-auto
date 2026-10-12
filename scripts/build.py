#!/usr/bin/env python3
"""按频道名称关键词分类，生成 output/ 下的分类 m3u 文件。

用法: python scripts/build.py
输入 work/checked.json，输出 output/all.m3u 及各分类文件 + stats.json
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

# 地区源文件名 -> 分类：地区源的频道优先按来源归入地区分类
SOURCE_REGION = {
    "hk.m3u": "港澳台", "mo.m3u": "港澳台", "tw.m3u": "港澳台",
    "jp.m3u": "日韩", "kr.m3u": "日韩",
    "uk.m3u": "欧美", "us.m3u": "欧美",
}

# tvg-id 国家码 -> 地区分类（tvg-id 形如 xxx.us@HD 时提取 us）
TVG_COUNTRY_REGION = {
    "hk": "港澳台", "mo": "港澳台", "tw": "港澳台",
    "jp": "日韩", "kr": "日韩",
    "us": "欧美", "uk": "欧美", "ca": "欧美",
    "de": "欧美", "fr": "欧美", "it": "欧美", "es": "欧美",
    "nl": "欧美", "se": "欧美", "no": "欧美", "dk": "欧美",
    "fi": "欧美", "pt": "欧美", "ie": "欧美", "ch": "欧美",
    "at": "欧美", "be": "欧美", "pl": "欧美", "gr": "欧美",
    "cz": "欧美", "ro": "欧美", "hu": "欧美",
}


def country_from_tvgid(tvg_id):
    m = re.search(r'\.([a-z]{2})@', (tvg_id or '').lower())
    return m.group(1) if m else ''

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
    ("港澳台", "hmt.m3u", ["凤凰", "phoenix", "tvb", "翡翠", "明珠", "澳视", "香港", "台湾", "澳门", "hk ", " rthk", "有线", "中天", "东森", "三立", "now"]),
    ("日韩", "japan_korea.m3u", ["日本", "韩国", "nhk", "kbs", "mbc", "sbs", "tvn", "mnet", "arirang", "朝日", "富士", "tbs", "wowow", "韩剧", "tokyo mx"]),
    ("欧美", "western.m3u", ["bbc", "cnn", "fox", "nbc", "abc", "cbs", "sky", "itv", "hbo", "showtime", "美国", "英国", "法国", "德国", "意大利", "西班牙", "欧洲", "usa"]),
    ("地方台", "local.m3u", ["北京", "上海", "广东", "深圳", "广州", "江苏", "浙江", "湖南", "湖北", "四川", "山东", "河南", "福建", "安徽", "江西", "辽宁", "吉林", "黑龙江", "河北", "山西", "陕西", "甘肃", "青海", "宁夏", "新疆", "西藏", "云南", "贵州", "广西", "海南", "重庆", "天津", "内蒙古"]),
]

OTHER = ("综合其他", "others.m3u")

# 需要合并"同频道多源"的分类：同一频道多条线路时输出 频道名、频道名 备用1、频道名 备用2…
MULTI_SOURCE_CATS = {"CCTV", "卫视"}


def norm_name(name):
    """归一化频道名，用于识别同一频道：去大小写/空格/分隔符/括号备注/清晰度词。"""
    n = name.lower()
    n = re.sub(r'[\(（].*?[\)）]', '', n)
    n = re.sub(r'[\[【].*?[\]】]', '', n)
    n = n.replace(' ', '').replace('-', '').replace('_', '')
    n = n.replace('高清', '').replace('超清', '').replace('标清', '')
    return n.strip()


def merge_multi_source(channels):
    """把同一频道的多个源合并，首个保留原名，其余加'备用N'后缀。"""
    groups = {}
    for c in channels:
        key = norm_name(c.get("name", ""))
        groups.setdefault(key, []).append(c)
    merged = []
    for key, g in groups.items():
        if len(g) == 1:
            merged.append(g[0])
            continue
        base = re.sub(r'\s*[\(\[（【].*?[\)\]）】]\s*', '', g[0]["name"]).strip()
        for i, c in enumerate(g):
            d = dict(c)
            d["name"] = base if i == 0 else f"{base} 备用{i}"
            merged.append(d)
    return merged


def categorize(name, group, source="", tvg_id=""):
    # 1) 地区源优先按来源文件归类
    if source:
        fname = source.rsplit("/", 1)[-1].lower()
        if fname in SOURCE_REGION:
            return SOURCE_REGION[fname]
    # 2) tvg-id 国家码归类（如 index.m3u 全量源）
    cc = country_from_tvgid(tvg_id)
    if cc in TVG_COUNTRY_REGION:
        return TVG_COUNTRY_REGION[cc]
    # 3) 其余按名称关键词归类
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
        cat = categorize(c.get("name", ""), c.get("group", ""), c.get("source", ""), c.get("tvg_id", ""))
        c["cat"] = cat
        buckets.setdefault(cat, []).append(c)

    # 同频道多源合并（如 CCTV 一个频道多条线路）
    for cat in MULTI_SOURCE_CATS:
        if buckets.get(cat):
            buckets[cat] = merge_multi_source(buckets[cat])

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

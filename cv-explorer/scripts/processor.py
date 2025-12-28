from process_advanced import (
    get_allowed_concepts_for_year,
    is_meaningful_concept,
    prettify_concept,
    normalize_phrase,
    CONCEPT_START_YEAR,
    CONCEPT_END_YEAR,
    normalize_year,
    ensure_list
)
import json
from collections import Counter
import re
from pathlib import Path
import sys
import os

# Ensure we can import from the same directory
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))


def blend_landscape_keywords(keyword_trend, keyword_labels, landscape_path="data/landscape_data.json", weight=3):
    path = Path(landscape_path)
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            nodes = json.load(f)
    except json.JSONDecodeError:
        return

    for node in nodes:
        year = node.get("year")
        if year is None:
            continue
        year_str = str(year)
        concepts = node.get("concepts") or []
        if not concepts:
            continue
        if year_str not in keyword_trend:
            keyword_trend[year_str] = Counter()
            keyword_labels[year_str] = {}
        for concept in concepts:
            if not isinstance(concept, str):
                continue
            normalized = normalize_phrase(concept)
            if not normalized:
                continue

            pretty = prettify_concept(concept) or concept
            year_val = normalize_year(year)
            end_year = CONCEPT_END_YEAR.get(pretty)
            if end_year and year_val and year_val > end_year:
                continue

            keyword_trend[year_str][normalized] += weight
            keyword_labels[year_str].setdefault(normalized, concept)


def process_visual_data(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 初始化统计容器 (参考学长 3.1.2 节思路 [cite: 31])
    yearly_stats = {}  # 存储每年论文数和总引用量
    venue_stats = {"CVPR": {}, "ICCV": {}, "ECCV": {}}
    keyword_trend = {}  # 存储年度关键词
    keyword_labels = {}

    print("开始统计核心指标...")
    for p in papers:
        year_raw = p.get('y') or p.get('year')
        year_val = normalize_year(year_raw)
        if not year_val:
            continue
        year = str(year_val)

        venue = p.get('v') or p.get('venue') or "Unknown"
        cite = p.get('c') or p.get('citations') or 0
        concepts = ensure_list(p.get('con') or p.get('concepts'))

        # 1. 基础统计
        if year not in yearly_stats:
            yearly_stats[year] = {"count": 0, "cites": 0}
        yearly_stats[year]["count"] += 1
        yearly_stats[year]["cites"] += cite

        # 2. 会议分布 (视图 D 需要 [cite: 195])
        if venue in venue_stats:
            venue_stats[venue][year] = venue_stats[venue].get(year, 0) + 1

        # 3. 关键词频率统计 (视图 E 需要 [cite: 197])
        if year not in keyword_trend:
            keyword_trend[year] = Counter()
            keyword_labels[year] = {}

        # 过滤并统计 Concept (这是 OpenAlex 提供的高质量标签)
        # 获取该年份允许的白名单
        allowed_concepts_set = get_allowed_concepts_for_year(year_val)

        for concept in concepts:
            if not is_meaningful_concept(concept):
                continue
            normalized = normalize_phrase(concept)
            if not normalized:
                continue

            pretty = prettify_concept(concept) or concept

            # 严格过滤：白名单检查
            if allowed_concepts_set:
                if not any(normalize_phrase(pretty) == normalize_phrase(a) for a in allowed_concepts_set):
                    continue

            # 严格过滤：年份检查
            start_year = CONCEPT_START_YEAR.get(pretty)
            end_year = CONCEPT_END_YEAR.get(pretty)
            if start_year and year_val < start_year:
                continue
            if end_year and year_val > end_year:
                continue

            keyword_trend[year][normalized] += 1
            keyword_labels[year].setdefault(normalized, pretty)

    # 4. 格式化输出供前端使用
    formatted_keywords = {}
    for year, counter in keyword_trend.items():
        formatted_keywords[year] = {
            keyword_labels[year][token]: count
            for token, count in counter.most_common(30)
        }

    blend_landscape_keywords(keyword_trend, keyword_labels)

    summary = {
        "yearly": yearly_stats,
        "venues": venue_stats,
        "keywords": formatted_keywords
    }

    with open("data/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    print("预处理完成！生成了 summary.json")


if __name__ == "__main__":
    process_visual_data("data/cleaned_papers.json")

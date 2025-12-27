import json
from collections import Counter
import re
from pathlib import Path

# 1. 定义 CV 专属停用词及概念黑名单
STOPWORDS = {
    'paper', 'method', 'approach', 'proposed', 'results', 'using',
    'state-of-the-art', 'performance', 'evaluation', 'images', 'image',
    'computer', 'vision', 'model', 'network', 'task', 'dataset',
    'based', 'show', 'efficient', 'new', 'framework', 'learning'
}

GENERIC_CONCEPTS = {
    "computer science",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "convolutional neural network",
    "benchmark",
    "survey",
    "dataset",
    "generalization"
}

GENERIC_CONCEPT_TOKENS = {
    "computer", "science", "artificial", "intelligence", "learning",
    "network", "networks", "model", "models", "paper", "study",
    "generalization", "method", "analysis", "system", "approach",
    "algorithm", "benchmark", "dataset", "data"
}

LOW_VALUE_TERMS = {
    "remote sensing",
    "landslide",
    "earthquake",
    "soil stability",
    "geology",
    "weather forecast",
    "agriculture",
    "crop monitoring",
    "meta analysis",
    "categorization",
    "open research",
    "key",
    "field",
    "modal",
    "generative grammar",
    "psychology",
    "mathematics",
    "medicine",
    "environmental science",
    "engineering",
    "physics",
    "biology",
    "business",
    "materials science",
    "geography",
    "computer security"
}

CONCEPT_BLACKLIST = {
    "computer vision",
    "artificial intelligence",
    "pattern recognition",
    "responsible ai"
}

NON_ALPHA_PATTERN = re.compile(r"[^a-z0-9\+\-\s]")
PAREN_STRIP_PATTERN = re.compile(r"\([^)]*\)")


def normalize_phrase(text):
    if not isinstance(text, str):
        return ""
    stripped = PAREN_STRIP_PATTERN.sub(" ", text)
    lowered = stripped.lower()
    lowered = re.sub(r"[\-_/:+]+", " ", lowered)
    lowered = NON_ALPHA_PATTERN.sub(' ', lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def prettify_concept(term):
    if term is None:
        return ""
    text = PAREN_STRIP_PATTERN.sub(" ", str(term))
    text = text.replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    tokens = text.split()
    formatted = []
    for token in tokens:
        if token.isupper() or any(ch.isdigit() for ch in token):
            formatted.append(token.upper())
        else:
            formatted.append(token.capitalize())
    return " ".join(formatted)


def is_meaningful_concept(term):
    if term is None:
        return False
    raw_text = str(term)
    if "(" in raw_text or ")" in raw_text:
        return False
    normalized = normalize_phrase(raw_text)
    if not normalized:
        return False
    if normalized in STOPWORDS:
        return False
    if normalized in CONCEPT_BLACKLIST:
        return False
    if normalized in GENERIC_CONCEPTS:
        return False
    if normalized in LOW_VALUE_TERMS:
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    if len(tokens) == 1 and (tokens[0] in GENERIC_CONCEPT_TOKENS or len(tokens[0]) <= 2):
        return False
    if all(tok in GENERIC_CONCEPT_TOKENS for tok in tokens):
        return False
    return True


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    if isinstance(value, str):
        parts = re.split(r"[;,/]", value)
        return [part.strip() for part in parts if part.strip()]
    return [value]


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
        year = str(p['y'])
        venue = p['v']
        cite = p['c']
        concepts = ensure_list(p.get('con'))

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
        for concept in concepts:
            if not is_meaningful_concept(concept):
                continue
            normalized = normalize_phrase(concept)
            if not normalized:
                continue
            pretty = prettify_concept(concept) or concept
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

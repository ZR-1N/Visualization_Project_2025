import json
from collections import Counter
import re

# 1. 极其严格的停用词表（增加学术泛泛词）
ACADEMIC_STOPWORDS = {
    'computer science', 'artificial intelligence', 'computer vision', 'paper', 'method',
    'approach', 'results', 'proposed', 'using', 'performance', 'task', 'models',
    'images', 'feature', 'learning', 'based', 'show', 'new', 'framework', 'data',
    'image', 'application', 'system', 'research', 'study', 'analysis', 'recognition',
    'efficient', 'robust', 'effective', 'neural', 'networks', 'network', 'deep'
}

# 2. 技术关键词白名单（确保这些词即便权重不够也被重点关注，或者用于匹配）
TECH_KEYWORDS = ['diffusion', 'transformer',
                 'vit', 'nerf', 'gan', 'bert', 'clip', 'mae']


def clean_text(text):
    # 清洗标题中的特殊字符
    return re.sub(r'[^a-zA-Z\s]', '', text.lower())


def extract_tech_from_title(title):
    """
    简单的 N-gram 提取：寻找标题中的连续技术词
    例如 'Denoising Diffusion Probabilistic Models' -> 'diffusion'
    """
    title = clean_text(title)
    words = title.split()
    found = []
    # 匹配白名单
    for tech in TECH_KEYWORDS:
        if tech in words:
            found.append(tech)
    # 也可以捕捉像 'segmentation', 'detection' 等词
    return found


def normalize_weight(value, min_weight=1):
    """确保权重为整数并设置最小值，避免词云出现小数引用。"""
    return max(min_weight, int(round(value)))


def prepare_wordcloud_data_v2(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    yearly_keywords = {}

    for p in papers:
        year = str(p['y'])
        citations = p.get('c', 0) + 1
        title = p.get('t', '')

        if year not in yearly_keywords:
            yearly_keywords[year] = Counter()

        # 策略 A：从 Concepts 提取 (过滤高层级词汇)
        for concept in p.get('con', []):
            cleaned = re.sub(r'\s*\(.*\)', '', concept.lower()).strip()
            if len(cleaned) > 3 and cleaned not in ACADEMIC_STOPWORDS:
                # 降低极其宽泛词汇的权重，提升细分词汇
                weight = normalize_weight(citations * 0.5)
                yearly_keywords[year][cleaned] += weight

        # 策略 B：从标题中强行提取 (高权重)
        tech_hits = extract_tech_from_title(title)
        for tech in tech_hits:
            # 标题出现的词权重加倍
            yearly_keywords[year][tech] += normalize_weight(citations * 2.0)

    # 格式化数据
    formatted_data = {}
    for year, keywords in yearly_keywords.items():
        # 增加一个逻辑：确保每个年份的 top 50 包含具体的创新技术
        formatted_data[year] = [
            {"text": k, "size": normalize_weight(v)} for k, v in keywords.most_common(50)
        ]

    with open("../data/wordcloud_data.json", "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, ensure_ascii=False, indent=4)
    print("词云数据深度提取完成！")


if __name__ == "__main__":
    prepare_wordcloud_data_v2("../data/cleaned_papers.json")

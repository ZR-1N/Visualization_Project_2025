import json
from collections import Counter
import re

# 1. 详细定义的停用词
STOPWORDS = {
    'computer science', 'artificial intelligence', 'computer vision', 'paper', 'method', 
    'approach', 'results', 'proposed', 'using', 'performance', 'task', 'models', 
    'images', 'feature', 'learning', 'based', 'show', 'new', 'framework', 'data'
}

def clean_concept(name):
    # 去除括号，如 "pattern recognition (psychology)" -> "pattern recognition"
    return re.sub(r'\s*\(.*\)', '', name.lower()).strip()

def prepare_wordcloud_data(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 存储结构: { year: { keyword: weighted_score } }
    yearly_keywords = {}

    for p in papers:
        year = str(p['y'])
        citations = p['c'] + 1 # 防止 0 引用，至少算 1
        
        if year not in yearly_keywords:
            yearly_keywords[year] = Counter()
        
        # 处理 Concepts
        for concept in p.get('con', []):
            cleaned = clean_concept(concept)
            
            # 过滤逻辑：太短的词、纯数字、以及停用词
            if len(cleaned) > 2 and cleaned not in STOPWORDS:
                # 核心逻辑：按引用量加权
                yearly_keywords[year][cleaned] += citations

    # 格式化数据，每年前 50 个最热词
    formatted_data = {}
    for year, keywords in yearly_keywords.items():
        formatted_data[year] = [
            {"text": k, "size": v} for k, v in keywords.most_common(50)
        ]

    with open("../data/wordcloud_data.json", "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, ensure_ascii=False, indent=4)
    print("词云数据提取完成！")

if __name__ == "__main__":
    prepare_wordcloud_data("../data/cleaned_papers.json")
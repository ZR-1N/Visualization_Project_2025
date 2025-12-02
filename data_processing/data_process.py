import pandas as pd
import numpy as np
import json
import re
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import umap
from collections import Counter, defaultdict
import itertools

# ================= 豪华配置区域 =================
INPUT_FILE = "../raw_data/cvpr_iccv_2015_2024_full.csv"
OUTPUT_JSON = "../visualization/data/final_data.json"
GPU_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 停用词表 (去除无意义的学术套话)
STOP_WORDS = set([
    'learning', 'network', 'neural', 'deep', 'based', 'via', 'using', 'analysis', 
    'model', 'approach', 'method', 'algorithm', 'system', 'data', 'image', 'video',
    'object', 'detection', 'recognition', 'segmentation', 'visual', 'computer', 'vision',
    'cvpr', 'iccv', 'paper', 'proposed', 'state', 'art', 'performance', 'results',
    'towards', 'novel', 'framework', 'multi', 'super', 'resolution', 'robust', 'efficient'
])

# 网络图配置：只展示 Top N 个核心大佬，否则图会卡死
TOP_AUTHORS_LIMIT = 150 
# ===========================================

def clean_text(text):
    """基础清洗"""
    if not isinstance(text, str): return ""
    return re.sub(r'[^\w\s-]', '', text).lower()

def extract_keywords_simple(text):
    """从标题提取关键词 (简单版，速度快且效果好)"""
    words = clean_text(text).split()
    return [w for w in words if w not in STOP_WORDS and len(w) > 3][:5]

def build_author_network(df):
    """构建作者合作网络 (Nodes & Links)"""
    print("🕸️ 正在构建作者关系网络...")
    
    # 1. 统计作者发文量
    author_counts = Counter()
    # 存储每篇论文的作者列表
    paper_authors_list = []
    
    for authors_str in df['authors']:
        if not isinstance(authors_str, str): 
            paper_authors_list.append([])
            continue
        # 分割作者名 (按逗号)
        names = [n.strip() for n in authors_str.split(',') if len(n.strip()) > 1]
        author_counts.update(names)
        paper_authors_list.append(names)
        
    # 2. 筛选 Top 大佬 (为了可视化性能，只取前 N 名)
    top_authors = set([name for name, count in author_counts.most_common(TOP_AUTHORS_LIMIT)])
    
    # 3. 构建 Nodes
    nodes = []
    # 记录每个作者的 ID (用于 d3 links source/target)
    for i, (name, count) in enumerate(author_counts.most_common(TOP_AUTHORS_LIMIT)):
        # group=1 暂时占位，后面可以根据社区发现算法分组
        node = {"id": name, "value": count, "group": 1} 
        nodes.append(node)
        
    # 4. 构建 Links (共现关系)
    links_counter = Counter()
    
    for names in paper_authors_list:
        # 只保留在 Top 列表里的作者
        valid_names = [n for n in names if n in top_authors]
        # 如果这篇论文有两个以上大佬合作，建立连接
        if len(valid_names) > 1:
            # 生成两两组合 (无向图)
            for u, v in itertools.combinations(valid_names, 2):
                # 排序确保 A-B 和 B-A 是同一条边
                if u > v: u, v = v, u
                links_counter[(u, v)] += 1
                
    links = []
    for (u, v), weight in links_counter.items():
        links.append({"source": u, "target": v, "value": weight})
        
    return {"nodes": nodes, "links": links}

def process_data():
    print(f"🚀 启动全栈数据处理 (Device: {GPU_DEVICE})...")
    
    # --- 1. 数据加载与清洗 ---
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误：找不到输入文件 {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"📚 原始数据: {len(df)} 篇")
    
    # 剔除脏数据 (撤稿声明)
    df = df[~df['abstract'].str.contains("Violation of IEEE Publication Principles", na=False, case=False)]
    df.drop_duplicates(subset=['title'], inplace=True)
    df = df[df['abstract'].notna() & (df['abstract'] != "")]
    df['year'] = df['year'].astype(int)
    print(f"🧹 清洗后数据: {len(df)} 篇")

    # --- 2. 语义向量化 (Embedding & UMAP) ---
    print("🧠 计算语义向量 (Specter)...")
    embedder = SentenceTransformer('allenai-specter', device=GPU_DEVICE)
    text_corpus = (df['title'] + ' [SEP] ' + df['abstract']).tolist()
    
    # 这里 batch_size=32 比较稳妥，3090 可以尝试 64
    embeddings = embedder.encode(text_corpus, convert_to_tensor=False, show_progress_bar=True, batch_size=32)
    
    print("🗺️ 降维生成坐标 (UMAP)...")
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, metric='cosine', random_state=42)
    coords = reducer.fit_transform(embeddings)
    
    # 归一化坐标到 [-1000, 1000]
    x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
    y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
    df['x'] = (coords[:, 0] - x_min) / (x_max - x_min) * 2000 - 1000
    df['y'] = (coords[:, 1] - y_min) / (y_max - y_min) * 2000 - 1000

    # --- 3. 特征提取 ---
    print("🏷️ 提取关键词...")
    df['keywords'] = df['title'].apply(extract_keywords_simple)

    # --- 4. 构建可视化数据结构 ---
    
    # Part A: 散点图数据 (Scatter Data)
    print("📦 打包散点图数据...")
    scatter_data = []
    # 统计每年的关键词分布，为河流图做准备
    year_keywords_raw = defaultdict(Counter)
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        kws = row['keywords']
        scatter_data.append({
            "id": idx,
            "title": row['title'],
            "year": row['year'],
            "conf": row['conf'],
            "authors": row['authors'],
            "x": round(row['x'], 2),
            "y": round(row['y'], 2),
            "kws": kws, 
        })
        # 统计关键词
        for w in kws:
            year_keywords_raw[row['year']][w] += 1

    # Part B: 河流图数据 (Streamgraph Data)
    print("🌊 打包河流图数据...")
    # 找出十年间总频次最高的 Top 20 关键词
    total_kw_counts = Counter()
    for y in year_keywords_raw:
        total_kw_counts.update(year_keywords_raw[y])
    
    # 排除一些特别通用的词
    exclude_stream = ['images', 'features', 'learning', 'networks']
    top_candidates = [k for k, v in total_kw_counts.most_common(50) if k not in exclude_stream]
    top_20_kws = top_candidates[:20]
    
    stream_data = []
    for year in sorted(year_keywords_raw.keys()):
        entry = {"year": year}
        for kw in top_20_kws:
            entry[kw] = year_keywords_raw[year][kw]
        stream_data.append(entry)

    # Part C: 作者网络数据 (Network Data)
    network_data = build_author_network(df)

    # Part D: 统计面板数据 (Statistics Data)
    print("📊 打包统计数据...")
    stats_data = {
        "paper_counts": df.groupby('year').size().to_dict(), # 每年发文量
        "conf_counts": df['conf'].value_counts().to_dict(),  # CVPR vs ICCV
        "top_keywords": top_20_kws
    }

    # --- 5. 最终保存 ---
    final_output = {
        "scatter": scatter_data,
        "stream": stream_data,
        "network": network_data,
        "stats": stats_data
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False) 
        
    print(f"\n✅ 全流程完成！")
    print(f"💾 数据已保存至: {OUTPUT_JSON}")
    print(f"👉 包含模块: {list(final_output.keys())}")

if __name__ == "__main__":
    process_data()
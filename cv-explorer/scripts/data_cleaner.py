import json
import os


def clean_data(input_file, output_file):
    print(f"开始读取原始文件: {input_file} ...")
    if not os.path.exists(input_file):
        print("错误：找不到原始数据文件。")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"原始数据总量: {len(raw_data)} 篇")

    seen_titles = set()
    cleaned_papers = []

    # 遍历原始数据进行清洗
    for i, p in enumerate(raw_data):
        # 1. 健壮性检查：确保 p 是一个字典且不为 None
        if not p or not isinstance(p, dict):
            continue

        # 2. 获取标题并处理 None 情况
        title = p.get('title')
        if title is None:  # 如果标题字段缺失或为 null
            continue

        title = str(title).strip()
        title_lower = title.lower()

        # 3. 核心过滤逻辑 (参考学长项目的清洗思路 [cite: 25, 29])
        if not title_lower or title_lower in seen_titles:
            continue

        abstract = p.get('abstract', '')
        if not abstract or len(abstract) < 50:
            continue

        seen_titles.add(title_lower)

        # 4. 字段精简与格式化
        cleaned_papers.append({
            "t": title,                       # 标题
            "y": p.get('year'),               # 年份
            "c": p.get('citations', 0),       # 引用量
            "v": p.get('venue'),              # 会议 (CVPR/ICCV/ECCV)
            "a": p.get('authors', []),        # 作者列表
            "abs": abstract,                  # 摘要
            "con": p.get('concepts', [])      # 自动分类标签
        })

        # 5. 打印进度
        if (i + 1) % 10000 == 0:
            print(f"已处理 {i + 1} 篇...")

    print(f"\n清洗完成！")
    print(f"原始总量: {len(raw_data)}")
    print(f"保留总量: {len(cleaned_papers)}")
    print(f"过滤掉了: {len(raw_data) - len(cleaned_papers)} 篇重复或无效数据")

    # 存储清洗后的数据 (使用 compact 格式减少体积)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_papers, f, ensure_ascii=False)

    print(f"清洗后的数据已存入: {output_file}")


if __name__ == "__main__":
    clean_data("data/raw_papers.json", "data/cleaned_papers.json")

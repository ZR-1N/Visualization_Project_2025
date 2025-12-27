import requests
import json
import time
import os

# --- 配置区 ---
VENUES = ["CVPR", "ICCV", "ECCV"]
START_YEAR = 2014
END_YEAR = 2024
DATA_DIR = "data"
RAW_FILE = os.path.join(DATA_DIR, "raw_papers.json")

# 如果你的 VPN 代理端口不是 7890，请修改此处
PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

def reconstruct_abstract(inverted_index):
    if not inverted_index: return ""
    word_index = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_index.append((pos, word))
    word_index.sort()
    return " ".join([item[1] for item in word_index])

def fetch_all_papers():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    all_papers = []
    session = requests.Session()
    session.proxies.update(PROXIES) # 强制使用代理
    
    headers = {"User-Agent": "Nankai-Project/1.0 (mailto:wenxuan@nankai.edu.cn)"}

    for venue in VENUES:
        for year in range(START_YEAR, END_YEAR + 1):
            print(f"\n>>> 开始抓取: {venue} - {year}")
            page = 1
            while True:
                # OpenAlex 每页最高支持 200 
                url = "https://api.openalex.org/works"
                params = {
                    "search": venue,
                    "filter": f"publication_year:{year}",
                    "per_page": 200, 
                    "page": page,
                    "sort": "cited_by_count:desc"
                }
                
                try:
                    # 设定 timeout 防止假死
                    response = session.get(url, params=params, headers=headers, timeout=20)
                    if response.status_code != 200: break
                    
                    data = response.json()
                    results = data.get('results', [])
                    if not results: break
                    
                    for r in results:
                        # 核心元数据清洗 [cite: 25, 27]
                        all_papers.append({
                            "title": r['display_name'],
                            "year": r['publication_year'],
                            "citations": r['cited_by_count'],
                            "venue": venue,
                            "authors": [a['author']['display_name'] for a in r['authorships']],
                            "abstract": reconstruct_abstract(r.get('abstract_inverted_index')),
                            "concepts": [c['display_name'] for c in r.get('concepts', [])[:5]]
                        })
                    
                    print(f"  第 {page} 页成功，累计: {len(all_papers)} 篇", end='\r')
                    
                    # 如果结果不满 200 篇，说明这一年抓完了
                    if len(results) < 200: break
                    
                    page += 1
                    time.sleep(0.2) # 礼貌延时 [cite: 28]
                    
                except Exception as e:
                    print(f"\n连接中断: {e}")
                    break
                    
            # 每一年的数据抓完后，实时存一下档防止崩溃
            with open(RAW_FILE, "w", encoding="utf-8") as f:
                json.dump(all_papers, f, ensure_ascii=False, indent=4)

    print(f"\n任务完成！去重前共计 {len(all_papers)} 篇。")

if __name__ == "__main__":
    fetch_all_papers()
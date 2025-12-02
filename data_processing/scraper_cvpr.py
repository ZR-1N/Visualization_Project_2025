import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
import re
from tqdm import tqdm
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================= 配置区域 =================
OUTPUT_DIR = "../raw_data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "cvpr_iccv_2015_2024_full.csv")
BASE_URL = "https://openaccess.thecvf.com"

TARGETS = [
    {"conf": "CVPR", "years": range(2015, 2025)},
    {"conf": "ICCV", "years": range(2015, 2024, 2)}
]

MAX_WORKERS = 4
# ===========================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def get_headers():
    return {
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 128)}.0.0.0 Safari/537.36"
    }


session = None


def get_session():
    global session
    if session is not None:
        return session
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1,
                    status_forcelist=[500, 502, 503, 504, 429])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_page(url, retries=3):
    s = get_session()
    for i in range(retries):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            response = s.get(url, headers=get_headers(), timeout=30)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            elif response.status_code == 429:
                print(f"⚠️ 触发限流，暂停 30 秒...")
                time.sleep(30)
        except Exception as e:
            if "SSLEOFError" in str(e):
                time.sleep(5)
            elif i == retries - 1:
                print(f"❌ 请求彻底失败: {url} | {e}")
    return None

# ================= 核心修复：全能型作者提取逻辑 =================


def parse_paper_list(soup, year, conf):
    papers = []
    titles = soup.find_all('dt', class_='ptitle')

    # 调试计数器
    debug_count = 0

    for dt in titles:
        # 1. 提取链接
        a_tag = dt.find('a')
        link = urljoin(BASE_URL, a_tag['href']) if a_tag else ""
        title_text = dt.text.strip()

        # 2. 提取作者 (针对 2015-2025 全年份适配)
        authors = ""
        dd = dt.find_next_sibling('dd')

        if dd:
            auth_parts = []

            # 策略 A: 优先检查是否有 <form> 里的 <a> 标签 (针对 2025 新版结构)
            # 结构: <form ...><a ...>Author Name</a></form>
            forms = dd.find_all('form')
            if forms:
                for form in forms:
                    # 提取 form 下的所有 a 标签文本
                    for a in form.find_all('a'):
                        text = a.text.strip()
                        if text and text.lower() != "bibtex":  # 排除 bibtex 按钮
                            auth_parts.append(text)

            # 策略 B: 如果没找到 form 里的作者，或者找完了 form 还要找裸露的文本 (针对 2015 旧版结构)
            # 遍历 dd 的直接子节点
            # 注意：新版结构里作者都在 form 里，旧版在裸文本里，两者混合处理
            if not auth_parts:  # 只有当策略A没找到时，才启用策略B，避免重复或混乱
                for content in dd.contents:
                    # 忽略 Tag 类型的 form (因为上面策略A处理过了) 和 div
                    if content.name in ['form', 'div']:
                        continue

                    # 提取纯文本 (2015年样式)
                    if isinstance(content, str):
                        text = content.strip()
                        # 排除掉只有逗号或空字符的情况
                        if text and text != ',':
                            auth_parts.append(text)

                    # 提取直接链接 (2016-2024 中间年份样式)
                    elif content.name == 'a':
                        text = content.text.strip()
                        if text:
                            auth_parts.append(text)

            # 拼接结果
            full_text = ", ".join(auth_parts)
            # 终极清洗:
            # 1. 把 ", ," 替换成 ","
            # 2. 去掉首尾逗号
            cleaned = re.sub(r'\s*,\s*', ', ', full_text)
            authors = cleaned.strip().strip(',')

            # --- 调试打印 (仅针对第一篇) ---
            if debug_count == 0:
                print(f"\n🔍 [DEBUG {year}] 解析示例: {title_text[:30]}...")
                print(f"   -> 提取到的作者: [{authors}]")
            debug_count += 1
            # --------------------------------------

        papers.append({
            "conf": conf,
            "year": year,
            "title": title_text,
            "authors": authors,
            "link": link,
            "abstract": ""
        })
    return papers

# ================= 剩余部分保持不变 =================


def crawl_list_phase():
    all_papers = []
    print("🚀 [阶段一] 开始抓取论文列表目录...")

    for target in TARGETS:
        conf = target['conf']
        for year in target['years']:
            print(f"   正在扫描 {conf} {year} ...")
            url_all = f"{BASE_URL}/{conf}{year}?day=all"
            soup = fetch_page(url_all)
            papers = []

            if soup:
                papers = parse_paper_list(soup, year, conf)

            if not papers:
                main_url = f"{BASE_URL}/{conf}{year}"
                soup = fetch_page(main_url)
                if soup:
                    day_links = set()
                    for a in soup.find_all('a', href=True):
                        if 'day=' in a['href']:
                            day_links.add(urljoin(BASE_URL, a['href']))
                    if day_links:
                        print(f"     -> 检测到 {len(day_links)} 个子页面...")
                        for day_url in day_links:
                            day_soup = fetch_page(day_url)
                            if day_soup:
                                papers.extend(parse_paper_list(
                                    day_soup, year, conf))
                    else:
                        papers = parse_paper_list(soup, year, conf)

            if papers:
                print(f"     ✅ 获取 {len(papers)} 篇")
                all_papers.extend(papers)
            else:
                print(f"     ❌ 未找到数据")

    return pd.DataFrame(all_papers)


def fetch_abstract_worker(link):
    if not link:
        return None
    soup = fetch_page(link)
    if not soup:
        return None
    abs_div = soup.find('div', id='abstract')
    if abs_div:
        return abs_div.text.strip()
    meta = soup.find('meta', attrs={'name': 'citation_abstract'})
    if meta:
        return meta['content'].strip()
    return None


def crawl_detail_phase(df):
    print(f"\n🚀 [阶段二] 开始补全摘要 (共 {len(df)} 篇)...")
    if 'abstract' not in df.columns:
        df['abstract'] = ""
    todo_indices = df[df['abstract'].isna() | (
        df['abstract'] == "")].index.tolist()
    print(f"   📋 待抓取数量: {len(todo_indices)} (已跳过现有数据)")
    if not todo_indices:
        return df

    save_counter = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(
            fetch_abstract_worker, df.loc[idx, 'link']): idx for idx in todo_indices}
        for future in tqdm(as_completed(future_to_idx), total=len(todo_indices), desc="Downloading Abstracts"):
            idx = future_to_idx[future]
            try:
                abstract = future.result()
                if abstract:
                    df.at[idx, 'abstract'] = abstract
            except Exception:
                pass
            save_counter += 1
            if save_counter >= 100:
                df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
                save_counter = 0
    return df


def main():
    # 自动检测是否需要重跑列表
    run_list_phase = True
    if os.path.exists(OUTPUT_FILE):
        try:
            df = pd.read_csv(OUTPUT_FILE)
            if len(df) > 0 and pd.isna(df.iloc[0]['authors']):
                print("⚠️ 检测到作者信息为空，正在重跑列表抓取...")
                run_list_phase = True
            elif len(df) > 100:
                run_list_phase = False
                print("✅ 现有数据正常，进入摘要补全。")
        except:
            run_list_phase = True

    if run_list_phase:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
        df = crawl_list_phase()
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    else:
        df = pd.read_csv(OUTPUT_FILE)

    df = crawl_detail_phase(df)

    print("\n🧹 最终清洗...")
    df.drop_duplicates(subset=['title'], inplace=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"🎉 完成！数据已保存至 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import re
import time
async def fetch_text(session, url, retry=3):
    for _ in range(retry):
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            print("[ERROR] TEXT", url, "->", e)
        await asyncio.sleep(1)
    return None


async def fetch_json(session, url, retry=3):
    for _ in range(retry):
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print("[ERROR] JSON", url, "->", e)
        await asyncio.sleep(1)
    return None


# ---------------------------
# Steam API 相关数据
# ---------------------------
async def get_app_details(session, appid, cc="us"):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc={cc}&l=english"
    data = await fetch_json(session, url)
    if not data or not data.get(str(appid), {}).get("data"):
        return {}
    return data[str(appid)]["data"]


async def get_player_count(session, appid):
    url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"
    data = await fetch_json(session, url)
    if not data:
        return None
    return data.get("response", {}).get("player_count")


async def get_reviews_summary(session, appid):
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&purchase_type=all"
    data = await fetch_json(session, url)
    if not data:
        return {}
    return {
        "total_reviews": data.get("query_summary", {}).get("total_reviews"),
        "positive": data.get("query_summary", {}).get("total_positive"),
        "negative": data.get("query_summary", {}).get("total_negative"),
        "score": data.get("query_summary", {}).get("review_score")
    }


async def get_steamspy(session, appid):
    url = f"http://steamspy.com/api.php?request=appdetails&appid={appid}"
    return await fetch_json(session, url)


async def get_steamcharts(session, appid):
    url = f"https://steamcharts.com/app/{appid}"
    html = await fetch_text(session, url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 最近两周平均在线人数
    elem = soup.select_one(".app-stat .num")
    if elem:
        try:
            return int(elem.text.replace(",", "").strip())
        except:
            return None
    return None


# ---------------------------
# 主爬取逻辑
# ---------------------------
async def crawl_steam(appid):
    async with aiohttp.ClientSession(trust_env=True) as session:
        details = await get_app_details(session, appid)
        player_count = await get_player_count(session, appid)
        reviews = await get_reviews_summary(session, appid)
        charts = await get_steamcharts(session, appid)
        spy = await get_steamspy(session, appid)

        result = {
            "appid": appid,
            "name": details.get("name"),
            "price": details.get("price_overview"),
            "platforms": details.get("platforms"),
            "categories": details.get("categories"),
            "genres": details.get("genres"),
            "supported_languages": details.get("supported_languages"),
            "dlc": details.get("dlc"),
            "metacritic": details.get("metacritic"),

            "player_count": player_count,
            "steamcharts_avg2weeks": charts,

            "reviews": reviews,
            "steamspy": spy,
        }

        # 保存到文件
        with open(f"steam_{appid}.json", "w", encoding="utf8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print("Saved:", f"steam_{appid}.json")
        return result


import pandas as pd
import asyncio

# ---------------------------
# main 批量抓取入口
# ---------------------------
async def main():
    # 从 CSV 读取 appid，第1列，第2~501行
    df = pd.read_csv("steam_top500_by_sales.csv")
    appids = df.iloc[1:501, 0].tolist()  # 转为列表

    for appid in appids:
        try:
            await crawl_steam(int(appid))  # 调用原来的 crawl_steam 函数
        except Exception as e:
            print(f"[ERROR] appid {appid} -> {e}")
        await asyncio.sleep(1)  # 可选：每抓一个延迟 1 秒，降低风控风险

if __name__ == "__main__":
    asyncio.run(main())

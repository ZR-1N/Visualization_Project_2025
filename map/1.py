import requests
import pandas as pd
import time
import json
import re
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime


class EnhancedGaodeCrawler:
    def __init__(self, api_key):
        self.api_key = api_key
        self.search_url = "https://restapi.amap.com/v3/place/around"
        self.detail_url = "https://restapi.amap.com/v3/place/detail"

    def get_precise_location(self):
        """获取南开大学津南校区精确坐标"""
        geocode_url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            'key': self.api_key,
            'address': '天津市津南区南开大学津南校区图书馆',
            'city': '天津',
            'output': 'json'
        }

        try:
            response = requests.get(geocode_url, params=params, timeout=10)
            data = response.json()

            if data['status'] == '1' and data['geocodes']:
                location = data['geocodes'][0]['location']
                print(f"获取到精确坐标: {location}")
                return location
        except Exception as e:
            print(f"获取坐标失败: {e}")

        return "117.1315,38.9825"

    def haversine_distance(self, lon1, lat1, lon2, lat2):
        """计算距离"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6371000 * 2 * atan2(sqrt(a), sqrt(1 - a))

    def search_restaurants(self, location, radius=10000):
        """搜索餐饮店面"""
        keywords = [
            '餐饮', '餐厅', '饭店', '美食', '餐馆', '中餐厅', '西餐厅',
            '快餐', '火锅', '烧烤', '川菜', '湘菜', '粤菜', '日料',
            '韩餐', '小吃', '奶茶', '咖啡厅', '茶馆', '酒吧', '食堂'
        ]

        all_pois = []
        seen_ids = set()

        for keyword in keywords:
            print(f"搜索关键词: {keyword}")
            page = 1
            total_pages = None

            while True:
                params = {
                    'key': self.api_key,
                    'location': location,
                    'keywords': keyword,
                    'radius': radius,
                    'offset': 25,
                    'page': page,
                    'extensions': 'base',
                    'output': 'json'
                }

                try:
                    response = requests.get(self.search_url, params=params, timeout=15)
                    data = response.json()

                    if data['status'] != '1':
                        break

                    # 获取总记录数
                    total_count = int(data.get('count', 0))

                    # 如果是第一页，计算总页数
                    if page == 1:
                        total_pages = (total_count + 24) // 25
                        print(f"  总记录数: {total_count}, 预计总页数: {total_pages}")

                    pois = data.get('pois', [])
                    if not pois:
                        break

                    new_count = 0
                    for poi in pois:
                        poi_id = poi.get('id')
                        if poi_id and poi_id not in seen_ids:
                            seen_ids.add(poi_id)
                            all_pois.append(poi)
                            new_count += 1

                    print(f"  第{page}页: 新增{new_count}个，本页{len(pois)}个，总计{len(all_pois)}个")

                    # 判断是否还有下一页
                    if len(pois) < 25:
                        break

                    if total_pages and page >= total_pages:
                        break

                    if page * 25 >= total_count:
                        break

                    page += 1
                    time.sleep(0.3)

                except Exception as e:
                    print(f"  第{page}页错误: {e}")
                    break

        return all_pois

    def search_by_type(self, location, radius=10000):
        """按分类搜索"""
        categories = {
            '050000': '餐饮服务',
            '050100': '中餐厅',
            '050200': '外国餐厅',
            '050300': '快餐厅',
            '050400': '休闲餐饮场所',
            '050500': '咖啡厅',
            '050600': '茶艺馆',
            '050700': '冷饮店',
            '050800': '糕饼店',
            '050900': '甜品店',
        }

        all_pois = []
        seen_ids = set()

        for type_code, type_name in categories.items():
            print(f"按分类搜索: {type_name} ({type_code})")
            page = 1

            while True:
                params = {
                    'key': self.api_key,
                    'location': location,
                    'types': type_code,
                    'radius': radius,
                    'offset': 25,
                    'page': page,
                    'extensions': 'base',
                    'output': 'json'
                }

                try:
                    response = requests.get(self.search_url, params=params, timeout=15)
                    data = response.json()

                    if data['status'] != '1':
                        break

                    pois = data.get('pois', [])
                    if not pois:
                        break

                    new_count = 0
                    for poi in pois:
                        poi_id = poi.get('id')
                        if poi_id and poi_id not in seen_ids:
                            seen_ids.add(poi_id)
                            all_pois.append(poi)
                            new_count += 1

                    print(f"  {type_name} 第{page}页: 新增{new_count}个，总计{len(all_pois)}个")

                    if len(pois) < 25:
                        break

                    total_count = int(data.get('count', 0))
                    if page * 25 >= total_count and total_count > 0:
                        break

                    page += 1
                    time.sleep(0.3)

                except Exception as e:
                    print(f"  {type_name} 第{page}页错误: {e}")
                    break

        return all_pois

    def get_poi_details(self, poi_id):
        """
        获取POI的详细信息
        严格遵守：有评论就输出原评论，没有就是没有
        """
        params = {
            'key': self.api_key,
            'id': poi_id,
            'extensions': 'all',
            'output': 'json'
        }

        try:
            response = requests.get(self.detail_url, params=params, timeout=15)
            data = response.json()

            if data['status'] == '1':
                poi_detail = data.get('pois', [{}])[0]
                detail_info = poi_detail.get('biz_ext', {})

                # 提取评分信息
                rating = detail_info.get('rating', '')
                rating = rating if rating else '0.0'

                business_info = {
                    'rating': rating,
                    'cost': detail_info.get('cost', ''),
                    'open_time': detail_info.get('open_time', ''),
                    'tag': detail_info.get('tag', '')
                }

                # 严格提取评论：只从photos字段的title中获取
                featured_comment = ''
                has_real_comment = False

                # 仅从photos字段提取真实用户评论
                if 'photos' in poi_detail:
                    photos = poi_detail.get('photos', [])
                    for photo in photos:
                        if photo.get('title') and photo['title'].strip():
                            comment_text = photo['title'].strip()
                            # 检查评论内容是否有效（不是空字符串或只有标点）
                            if len(comment_text) > 3 and not all(c in '，。！？、；：' for c in comment_text):
                                featured_comment = comment_text
                                has_real_comment = True
                                break

                # 注意：不创建任何基于评分的描述！
                # 如果没有评论，就保持为空

                return {
                    'business_info': business_info,
                    'featured_comment': featured_comment,
                    'has_real_comment': has_real_comment,
                    'detail_data': poi_detail
                }

        except Exception as e:
            print(f"  获取详情失败 {poi_id}: {e}")

        return {
            'business_info': {'rating': '0.0', 'cost': '', 'open_time': '', 'tag': ''},
            'featured_comment': '',
            'has_real_comment': False,
            'detail_data': {}
        }

    def estimate_popularity(self, poi_data):
        """
        估算受欢迎程度/销量指标
        只使用评分、价格等实际数据，不依赖评论
        """
        rating = float(poi_data['business_info'].get('rating', 0))
        cost = poi_data['business_info'].get('cost', '')

        # 基础分数基于评分
        score = rating * 2

        # 价格因素
        if cost and cost != '无':
            try:
                price_match = re.search(r'(\d+)', str(cost))
                if price_match:
                    price = int(price_match.group(1))
                    if 50 <= price <= 150:
                        score += 1
                    elif price < 30 or price > 200:
                        score -= 0.5
            except:
                pass

        # 有真实评论加分（但评论内容不参与计算，只作为标记）
        if poi_data['has_real_comment']:
            score += 1.5

        detail_data = poi_data.get('detail_data', {})

        if detail_data:
            photos_count = len(detail_data.get('photos', []))
            if photos_count > 3:
                score += 0.5

            tag = poi_data['business_info'].get('tag', '')
            if tag and ('推荐' in tag or '热门' in tag or '优质' in tag):
                score += 0.5

        # 基于评分分类
        if rating >= 4.5:
            popularity = "非常受欢迎"
            sales_estimate = "高"
        elif rating >= 4.0:
            popularity = "受欢迎"
            sales_estimate = "中高"
        elif rating >= 3.5:
            popularity = "一般"
            sales_estimate = "中等"
        else:
            popularity = "较少人"
            sales_estimate = "低"

        return {
            'popularity_score': round(score, 1),
            'popularity_level': popularity,
            'sales_estimate': sales_estimate,
            'rating': rating
        }

    def crawl_all_data(self):
        """完整的爬取流程"""
        print("=" * 60)
        print("南开大学津南校区周边餐饮数据爬取")
        print("开始时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 60)

        # 1. 获取精确位置
        print("\n1. 获取南开大学精确坐标...")
        center_location = self.get_precise_location()
        center_lon, center_lat = map(float, center_location.split(','))

        # 2. 搜索餐饮店面
        print("\n2. 搜索10公里范围内餐饮店面...")
        print("搜索方式1: 按关键词搜索")
        pois_by_keyword = self.search_restaurants(center_location, 10000)

        print(f"\n搜索方式2: 按分类搜索")
        pois_by_type = self.search_by_type(center_location, 10000)

        # 合并去重
        all_pois = []
        seen_ids = set()

        for poi in pois_by_keyword:
            poi_id = poi.get('id')
            if poi_id and poi_id not in seen_ids:
                seen_ids.add(poi_id)
                all_pois.append(poi)

        for poi in pois_by_type:
            poi_id = poi.get('id')
            if poi_id and poi_id not in seen_ids:
                seen_ids.add(poi_id)
                all_pois.append(poi)

        print(f"\n合并后找到 {len(all_pois)} 个不重复的餐饮店面")

        if not all_pois:
            print("未找到任何餐饮店面")
            return None

        # 3. 获取详细信息
        print(f"\n3. 获取详细信息（评分、评论等）...")
        enhanced_data = []

        # 统计信息
        stats = {
            'total': len(all_pois),
            'with_real_comments': 0,
            'without_comments': 0,
            'comment_examples': []
        }

        for i, poi in enumerate(all_pois):
            poi_id = poi.get('id', '')
            poi_name = poi.get('name', '')

            if i % 20 == 0 or i == stats['total'] - 1:
                print(f"  处理进度: {i + 1}/{stats['total']} ({((i + 1) / stats['total'] * 100):.1f}%)")

            # 获取距离
            location_str = poi.get('location', '')
            if location_str:
                try:
                    poi_lon, poi_lat = map(float, location_str.split(','))
                    distance = self.haversine_distance(center_lon, center_lat, poi_lon, poi_lat)
                except:
                    distance = None
            else:
                distance = None

            # 获取详细信息
            details = self.get_poi_details(poi_id)

            # 更新统计
            if details['has_real_comment']:
                stats['with_real_comments'] += 1
                if details['featured_comment']:
                    stats['comment_examples'].append({
                        'name': poi_name,
                        'comment': details['featured_comment'][:100]
                    })
            else:
                stats['without_comments'] += 1

            # 估算受欢迎程度
            popularity_info = self.estimate_popularity(details)

            # 严格遵守：有评论就输出原评论，没有就是空字符串
            featured_comment = details['featured_comment']

            # 不创建任何描述，有评论就输出评论，没有就保持空
            # 这符合实验要求：不准加入模拟数据

            # 提取电话号码
            tel = poi.get('tel', '')
            if tel == [] or tel == '':
                tel = '无'
            elif isinstance(tel, list):
                tel = ';'.join(tel)

            # 构建完整数据
            poi_data = {
                'id': poi_id,
                'name': poi_name,
                'type': poi.get('type', ''),
                'address': poi.get('address', ''),
                'area': poi.get('adname', ''),
                'business_area': poi.get('business_area', ''),
                'telephone': tel,
                'location': location_str,
                'longitude': float(location_str.split(',')[0]) if location_str and ',' in location_str else 0,
                'latitude': float(location_str.split(',')[1]) if location_str and ',' in location_str else 0,
                'distance_from_center(m)': round(distance, 2) if distance else None,
                'rating': popularity_info['rating'],
                'cost': details['business_info'].get('cost', ''),
                'open_time': details['business_info'].get('open_time', ''),
                'tags': details['business_info'].get('tag', ''),
                'popularity_score': popularity_info['popularity_score'],
                'popularity_level': popularity_info['popularity_level'],
                'sales_estimate': popularity_info['sales_estimate'],
                'featured_comment': featured_comment,  # 有就是有，没有就是空
                'comment_length': len(featured_comment),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'has_real_comment': details['has_real_comment']
            }

            enhanced_data.append(poi_data)

            if i % 10 == 0:
                time.sleep(0.2)

        # 输出评论统计
        print(f"\n评论数据统计（严格遵守不生成模拟数据）:")
        print(
            f"  有真实用户评论: {stats['with_real_comments']} ({stats['with_real_comments'] / stats['total'] * 100:.1f}%)")
        print(f"  无用户评论: {stats['without_comments']} ({stats['without_comments'] / stats['total'] * 100:.1f}%)")

        if stats['with_real_comments'] > 0:
            print(f"\n真实评论示例（仅展示API返回的真实评论）:")
            for i, example in enumerate(stats['comment_examples'][:5]):
                print(f"  {i + 1}. {example['name']}: {example['comment']}")
        else:
            print(f"\n警告：未找到任何用户评论")
            print("  这可能是高德地图API的限制，或者该区域店铺确实没有用户评论")
            print("  根据实验要求，不会生成任何模拟评论数据")

        # 4. 保存数据
        print("\n4. 保存数据...")
        self.save_to_files(enhanced_data, center_location, stats)

        return enhanced_data

    def save_to_files(self, data, center_location, stats):
        """保存数据到多个文件格式"""
        if not data:
            print("无数据可保存")
            return

        df = pd.DataFrame(data)

        # 按距离排序
        if 'distance_from_center(m)' in df.columns:
            df = df.sort_values('distance_from_center(m)')

        # 保存为CSV
        csv_filename = 'nankai_restaurants_with_comments.csv'
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

        # 保存为JSON
        json_filename = 'nankai_restaurants_with_comments.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            output_data = {
                'metadata': {
                    'center_location': center_location,
                    'data_count': len(data),
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'description': '南开大学津南校区周边餐饮数据',
                    'data_source': '高德地图API真实数据，严格遵守不生成模拟数据',
                    'data_quality': {
                        'with_real_comments': stats['with_real_comments'],
                        'without_comments': stats['without_comments'],
                        'comment_percentage': f"{stats['with_real_comments'] / stats['total'] * 100:.1f}%",
                        'note': 'featured_comment字段：有真实评论则显示，无评论则为空字符串。严格遵守实验要求。'
                    },
                    'search_methods': ['关键词搜索', '分类搜索'],
                    'search_radius': 10000,
                },
                'restaurants': data
            }
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"CSV文件已保存: {csv_filename}")
        print(f"JSON文件已保存: {json_filename}")

        # 显示详细统计
        print("\n" + "=" * 60)
        print("数据质量报告:")
        print("=" * 60)
        print(f"总店铺数: {len(df)}")

        # 评论数据质量
        real_comments_df = df[df['has_real_comment'] == True]
        no_comments_df = df[df['has_real_comment'] == False]

        print(f"\n评论数据:")
        print(f"  有真实评论: {len(real_comments_df)}家 ({len(real_comments_df) / len(df) * 100:.1f}%)")
        print(f"  无评论: {len(no_comments_df)}家 ({len(no_comments_df) / len(df) * 100:.1f}%)")

        # 检查数据一致性
        print(f"\n数据一致性检查:")

        # 检查1: has_real_comment=True 但 featured_comment 为空
        inconsistent_has_comment = df[(df['has_real_comment'] == True) &
                                      ((df['featured_comment'].isna()) | (df['featured_comment'] == ''))]
        print(f"  1. has_real_comment=True 但评论内容为空: {len(inconsistent_has_comment)}条")
        if len(inconsistent_has_comment) > 0:
            print("    这些数据将被修正为 has_real_comment=False")
            df.loc[inconsistent_has_comment.index, 'has_real_comment'] = False

        # 检查2: featured_comment 不为空 但 has_real_comment=False
        inconsistent_featured = df[(df['has_real_comment'] == False) &
                                   (df['featured_comment'].notna()) &
                                   (df['featured_comment'] != '')]
        print(f"  2. 评论内容不为空但 has_real_comment=False: {len(inconsistent_featured)}条")
        if len(inconsistent_featured) > 0:
            print("    这些可能是API返回的非标准评论，将被标记为真实评论")
            df.loc[inconsistent_featured.index, 'has_real_comment'] = True

        # 重新统计
        final_real_comments = df[df['has_real_comment'] == True]
        print(f"\n修正后统计:")
        print(f"  有真实评论: {len(final_real_comments)}家 ({len(final_real_comments) / len(df) * 100:.1f}%)")

        if len(final_real_comments) > 0:
            # 显示评论示例
            print(f"\n真实评论内容示例:")
            sample_comments = final_real_comments[['name', 'featured_comment']].head(5)
            for idx, row in sample_comments.iterrows():
                comment_preview = row['featured_comment'][:80] + "..." if len(row['featured_comment']) > 80 else row[
                    'featured_comment']
                print(f"  - {row['name']}: {comment_preview}")

        # 保存修正后的数据
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n修正后的数据已保存到: {csv_filename}")


def main():
    # 你的高德地图API密钥
    api_key = "e97fb3a3a8471059275e8a12db79672c"

    print("南开大学津南校区周边餐饮数据爬取")
    print("=" * 60)
    print("数据采集原则:")
    print("1. 有评论就输出原评论，没有就是空")
    print("2. 不生成任何模拟数据")
    print("3. 所有数据来自高德地图API")
    print("=" * 60)
    print("开始时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 创建爬虫
    crawler = EnhancedGaodeCrawler(api_key)

    # 运行爬虫
    data = crawler.crawl_all_data()

    if data:
        print("\n" + "=" * 60)
        print("爬取完成！")
        print("完成时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 60)
        print(f"总计爬取 {len(data)} 条数据")
        print("\n数据特点:")
        print("1. featured_comment: 仅包含API返回的真实用户评论")
        print("2. has_real_comment: 准确反映是否有真实评论")
        print("3. 无评论的店铺: featured_comment字段为空字符串")
        print("4. 严格遵守实验要求：不生成任何模拟数据")
        print("\n生成的文件:")
        print("  - nankai_restaurants_with_comments.csv")
        print("  - nankai_restaurants_with_comments.json")
        print("\n注意：由于高德地图API限制，可能很多店铺没有用户评论")


if __name__ == "__main__":
    main()
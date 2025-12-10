import json
import re
from datetime import datetime
from collections import Counter, defaultdict
import math


def clean_and_normalize_data(input_file, output_file):
    """
    清洗、标准化GitHub数据，生成适合可视化的结构
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 读取到 {len(data)} 条数据")

    # 1. 数据清洗
    cleaned_data = []
    for item in data:
        # 创建清洗后的项目字典
        clean_item = {}

        # 基本字段处理
        clean_item['rank'] = int(item.get('rank', 0))
        clean_item['full_name'] = item.get('full_name', '').strip()
        clean_item['url'] = item.get('url', '')
        clean_item['description'] = item.get('description', '').strip()

        # 数值字段转换
        clean_item['stars'] = parse_number(item.get('stars', '0'))
        clean_item['forks'] = parse_number(item.get('forks', '0'))
        clean_item['open_issues'] = parse_number(item.get('open_issues', '0'))
        clean_item['activity_score'] = parse_float(item.get('activity_score', '0'))
        clean_item['contributor_count'] = parse_number(item.get('contributor_count', '0'))
        clean_item['recent_commits'] = parse_number(item.get('recent_commits', '0'))

        # 语言处理
        language = item.get('language', '未知').strip()
        clean_item['language'] = normalize_language(language)

        # 日期处理
        clean_item['created_at'] = parse_date(item.get('created_at', ''))
        clean_item['updated_at'] = parse_date(item.get('updated_at', ''))
        clean_item['last_commit_date'] = parse_date(item.get('last_commit_date', ''))

        # 许可证处理
        license_text = item.get('license', '无').strip()
        clean_item['license'] = normalize_license(license_text)

        # 主题标签处理
        topics_str = item.get('topics', '')
        clean_item['topics'] = parse_topics(topics_str)

        # 其他字段
        clean_item['has_readme'] = item.get('has_readme', 'False') == 'True'
        clean_item['top_contributor'] = item.get('top_contributor', '').strip()
        clean_item['readme_summary'] = clean_text_summary(item.get('readme_summary', ''))

        # 计算衍生字段
        clean_item['age_days'] = calculate_age_days(clean_item['created_at'])
        clean_item['stars_per_day'] = calculate_stars_per_day(clean_item['stars'], clean_item['age_days'])
        clean_item['forks_per_star'] = calculate_forks_per_star(clean_item['forks'], clean_item['stars'])
        clean_item['is_active'] = clean_item['activity_score'] >= 70

        cleaned_data.append(clean_item)

    print(f"✅ 数据清洗完成，{len(cleaned_data)} 条有效数据")

    # 2. 生成结构化数据用于可视化
    structured_data = {
        # 原始数据（清洗后）
        'projects': cleaned_data,

        # 汇总统计
        'summary_stats': generate_summary_stats(cleaned_data),

        # 语言分析
        'language_analysis': analyze_languages(cleaned_data),

        # 时间趋势
        'time_analysis': analyze_time_trends(cleaned_data),

        # 许可证分析
        'license_analysis': analyze_licenses(cleaned_data),

        # 主题分析
        'topic_analysis': analyze_topics(cleaned_data),

        # 活跃度分析
        'activity_analysis': analyze_activity(cleaned_data),

        # 相关性分析
        'correlation_analysis': analyze_correlations(cleaned_data),

        # Top排行榜
        'top_lists': generate_top_lists(cleaned_data)
    }

    # 3. 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 数据已保存至 {output_file}")

    # 4. 输出统计信息
    print_stats(structured_data)

    return structured_data


def parse_number(value):
    """解析数字字符串"""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        # 移除逗号等非数字字符
        cleaned = re.sub(r'[^\d\.]', '', value)
        try:
            return int(float(cleaned)) if cleaned else 0
        except:
            return 0
    return 0


def parse_float(value):
    """解析浮点数"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except:
            return 0.0
    return 0.0


def normalize_language(language):
    """标准化编程语言名称"""
    language_map = {
        '未知': 'Unknown',
        '无': 'Unknown',
        'Markdown': 'Markdown',
        'TypeScript': 'TypeScript',
        'Python': 'Python',
        'JavaScript': 'JavaScript',
        'Java': 'Java',
        'C++': 'C++',
        'C': 'C',
        'Go': 'Go',
        'Rust': 'Rust',
        'HTML': 'HTML',
        'CSS': 'CSS',
        'Shell': 'Shell',
        'Dart': 'Dart',
        'MDX': 'MDX',
        'Batchfile': 'Batchfile',
        'Jupyter Notebook': 'Jupyter Notebook',
        'Clojure': 'Clojure',
        'Vim Script': 'Vim Script',
        'Vue': 'Vue',
        'Svelte': 'Svelte',
        'Zig': 'Zig',
        'Blade': 'Blade',
        'Dockerfile': 'Dockerfile',
    }

    lang = language.strip()
    return language_map.get(lang, lang)


def parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None

    # 尝试多种日期格式
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except:
            continue

    # 如果都无法解析，尝试提取年份
    year_match = re.search(r'\d{4}', date_str)
    if year_match:
        year = year_match.group()
        return f"{year}-01-01"

    return None


def normalize_license(license_text):
    """标准化许可证名称"""
    if not license_text or license_text == '无':
        return 'Unknown'

    # 常见许可证映射
    license_map = {
        'MIT License': 'MIT',
        'Apache License 2.0': 'Apache-2.0',
        'BSD 3-Clause "New" or "Revised" License': 'BSD-3-Clause',
        'GNU General Public License v3.0': 'GPL-3.0',
        'GNU Affero General Public License v3.0': 'AGPL-3.0',
        'Creative Commons Zero v1.0 Universal': 'CC0-1.0',
        'Creative Commons Attribution 4.0 International': 'CC-BY-4.0',
        'Creative Commons Attribution Share Alike 4.0 International': 'CC-BY-SA-4.0',
        'The Unlicense': 'Unlicense',
        'ISC License': 'ISC',
        'Mozilla Public License 2.0': 'MPL-2.0',
        'SIL Open Font License 1.1': 'OFL-1.1',
    }

    # 查找匹配的许可证
    for key, value in license_map.items():
        if key in license_text:
            return value

    # 简化其他许可证
    if 'GNU' in license_text:
        return 'GPL Family'
    elif 'Creative Commons' in license_text:
        return 'CC Family'
    elif 'BSD' in license_text:
        return 'BSD Family'

    return 'Other'


def parse_topics(topics_str):
    """解析主题标签"""
    if not topics_str:
        return []

    # 分割逗号分隔的标签
    topics = [t.strip() for t in topics_str.split(',') if t.strip()]

    # 过滤空值和过长的标签
    filtered = []
    for topic in topics:
        if topic and len(topic) <= 50:
            filtered.append(topic)

    return filtered


def clean_text_summary(text):
    """清理文本摘要"""
    if not text:
        return ""

    # 移除HTML标签
    cleaned = re.sub(r'<[^>]+>', '', text)

    # 移除多余的空格和换行
    cleaned = ' '.join(cleaned.split())

    # 截断过长的文本
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + '...'

    return cleaned


def calculate_age_days(created_date):
    """计算项目年龄（天）"""
    if not created_date:
        return 0

    try:
        created = datetime.strptime(created_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        return (today - created).days
    except:
        return 0


def calculate_stars_per_day(stars, age_days):
    """计算每日平均星标数"""
    if age_days <= 0:
        return 0
    return round(stars / age_days, 4)


def calculate_forks_per_star(forks, stars):
    """计算每星标对应的分支数"""
    if stars <= 0:
        return 0
    return round(forks / stars, 4)


def generate_summary_stats(data):
    """生成汇总统计"""
    stats = {
        'total_projects': len(data),
        'total_stars': sum(p['stars'] for p in data),
        'total_forks': sum(p['forks'] for p in data),
        'total_issues': sum(p['open_issues'] for p in data),
        'avg_stars': round(sum(p['stars'] for p in data) / len(data)),
        'avg_forks': round(sum(p['forks'] for p in data) / len(data)),
        'avg_activity_score': round(sum(p['activity_score'] for p in data) / len(data), 2),
        'active_projects': sum(1 for p in data if p['is_active']),
        'inactive_projects': sum(1 for p in data if not p['is_active']),
        'avg_age_days': round(sum(p['age_days'] for p in data) / len(data)),
        'oldest_project': max(data, key=lambda x: x['age_days'])['full_name'],
        'newest_project': min(data, key=lambda x: x['age_days'])['full_name'],
    }
    return stats


def analyze_languages(data):
    """分析编程语言分布"""
    language_counter = Counter(p['language'] for p in data)
    language_stats = []

    for lang, count in language_counter.most_common():
        lang_projects = [p for p in data if p['language'] == lang]
        total_stars = sum(p['stars'] for p in lang_projects)
        avg_stars = round(total_stars / count) if count > 0 else 0
        avg_activity = round(sum(p['activity_score'] for p in lang_projects) / count, 2)

        language_stats.append({
            'language': lang,
            'count': count,
            'percentage': round(count / len(data) * 100, 2),
            'total_stars': total_stars,
            'avg_stars': avg_stars,
            'avg_activity_score': avg_activity,
            'top_project': max(lang_projects, key=lambda x: x['stars'])['full_name'] if lang_projects else ''
        })

    return sorted(language_stats, key=lambda x: x['count'], reverse=True)


def analyze_time_trends(data):
    """分析时间趋势"""
    # 按创建年份分组
    year_data = defaultdict(list)
    for project in data:
        if project['created_at']:
            year = project['created_at'][:4]
            year_data[year].append(project)

    # 生成年度统计
    yearly_stats = []
    for year in sorted(year_data.keys()):
        projects = year_data[year]
        yearly_stats.append({
            'year': int(year),
            'count': len(projects),
            'total_stars': sum(p['stars'] for p in projects),
            'avg_stars': round(sum(p['stars'] for p in projects) / len(projects)),
            'avg_activity': round(sum(p['activity_score'] for p in projects) / len(projects), 2)
        })

    # 计算每月创建数（最近3年）
    monthly_data = defaultdict(int)
    recent_projects = [p for p in data if p['created_at'] and int(p['created_at'][:4]) >= 2020]

    for project in recent_projects:
        month_key = project['created_at'][:7]  # YYYY-MM
        monthly_data[month_key] += 1

    monthly_stats = [{'month': month, 'count': count}
                     for month, count in sorted(monthly_data.items())]

    return {
        'yearly': yearly_stats,
        'monthly': monthly_stats,
        'oldest_project_year': min(yearly_stats, key=lambda x: x['year'])['year'] if yearly_stats else None,
        'newest_project_year': max(yearly_stats, key=lambda x: x['year'])['year'] if yearly_stats else None
    }


def analyze_licenses(data):
    """分析许可证分布"""
    license_counter = Counter(p['license'] for p in data)
    license_stats = []

    for lic, count in license_counter.most_common():
        lic_projects = [p for p in data if p['license'] == lic]
        total_stars = sum(p['stars'] for p in lic_projects)

        license_stats.append({
            'license': lic,
            'count': count,
            'percentage': round(count / len(data) * 100, 2),
            'total_stars': total_stars,
            'avg_stars': round(total_stars / count) if count > 0 else 0,
            'top_project': max(lic_projects, key=lambda x: x['stars'])['full_name'] if lic_projects else ''
        })

    return license_stats


def analyze_topics(data):
    """分析主题标签"""
    all_topics = []
    for project in data:
        all_topics.extend(project['topics'])

    topic_counter = Counter(all_topics)

    # 热门主题
    hot_topics = []
    for topic, count in topic_counter.most_common(30):  # 取前30
        hot_topics.append({
            'topic': topic,
            'count': count,
            'percentage': round(count / len(data) * 100, 2)
        })

    # 主题关联性（简单的共现分析）
    topic_cooccurrence = defaultdict(int)
    for project in data:
        topics = project['topics']
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                pair = tuple(sorted([topics[i], topics[j]]))
                topic_cooccurrence[pair] += 1

    # 取最常见的主题对
    top_pairs = sorted(topic_cooccurrence.items(), key=lambda x: x[1], reverse=True)[:20]
    cooccurrence_stats = [{
        'topic1': pair[0],
        'topic2': pair[1],
        'count': count
    } for pair, count in top_pairs]

    return {
        'hot_topics': hot_topics,
        'cooccurrence': cooccurrence_stats,
        'total_unique_topics': len(topic_counter),
        'avg_topics_per_project': round(len(all_topics) / len(data), 2)
    }


def analyze_activity(data):
    """分析活跃度"""
    # 活跃度分布
    activity_bins = defaultdict(int)
    for project in data:
        score = project['activity_score']
        if score >= 90:
            activity_bins['90-100'] += 1
        elif score >= 80:
            activity_bins['80-89'] += 1
        elif score >= 70:
            activity_bins['70-79'] += 1
        elif score >= 60:
            activity_bins['60-69'] += 1
        else:
            activity_bins['0-59'] += 1

    activity_distribution = [{'range': k, 'count': v, 'percentage': round(v / len(data) * 100, 2)}
                             for k, v in activity_bins.items()]

    # 最近更新分析
    recent_updates = [p for p in data if p['updated_at']]
    recent_updates.sort(key=lambda x: x['updated_at'], reverse=True)

    latest_projects = [{
        'rank': p['rank'],
        'full_name': p['full_name'],
        'updated_at': p['updated_at'],
        'activity_score': p['activity_score']
    } for p in recent_updates[:10]]

    return {
        'distribution': activity_distribution,
        'latest_updated': latest_projects,
        'high_activity_projects': sum(1 for p in data if p['activity_score'] >= 80),
        'low_activity_projects': sum(1 for p in data if p['activity_score'] < 60)
    }


def analyze_correlations(data):
    """分析相关性"""
    # 星标与分支相关性数据
    stars_forks_data = [{
        'full_name': p['full_name'],
        'stars': p['stars'],
        'forks': p['forks'],
        'language': p['language']
    } for p in data]

    # 星标与活跃度相关性数据
    stars_activity_data = [{
        'full_name': p['full_name'],
        'stars': p['stars'],
        'activity_score': p['activity_score'],
        'is_active': p['is_active']
    } for p in data]

    # 语言与星标关系
    language_stars = defaultdict(list)
    for p in data:
        language_stars[p['language']].append(p['stars'])

    language_avg_stars = [{
        'language': lang,
        'avg_stars': round(sum(stars) / len(stars)),
        'max_stars': max(stars),
        'min_stars': min(stars)
    } for lang, stars in language_stars.items() if len(stars) >= 5]

    # 计算相关系数（简化版）
    if len(data) > 1:
        stars_values = [p['stars'] for p in data]
        forks_values = [p['forks'] for p in data]
        activity_values = [p['activity_score'] for p in data]

        # 计算Pearson相关系数（简化版）
        def simplified_corr(x, y):
            if len(x) != len(y):
                return 0
            n = len(x)
            mean_x = sum(x) / n
            mean_y = sum(y) / n

            numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
            denominator_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
            denominator_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

            if denominator_x == 0 or denominator_y == 0:
                return 0

            return round(numerator / (denominator_x * denominator_y), 3)

        stars_forks_corr = simplified_corr(stars_values, forks_values)
        stars_activity_corr = simplified_corr(stars_values, activity_values)
    else:
        stars_forks_corr = 0
        stars_activity_corr = 0

    return {
        'stars_vs_forks': {
            'data': stars_forks_data,
            'correlation': stars_forks_corr
        },
        'stars_vs_activity': {
            'data': stars_activity_data,
            'correlation': stars_activity_corr
        },
        'language_stars': sorted(language_avg_stars, key=lambda x: x['avg_stars'], reverse=True),
        'interpretation': {
            'stars_forks': "正相关表示星标多的项目通常分支也多",
            'stars_activity': "正相关表示流行的项目通常更活跃"
        }
    }


def generate_top_lists(data):
    """生成各种Top排行榜"""
    # 按星标排序
    top_stars = sorted(data, key=lambda x: x['stars'], reverse=True)[:20]

    # 按活跃度排序
    top_activity = sorted(data, key=lambda x: x['activity_score'], reverse=True)[:20]

    # 按每日星标增长排序（热门项目）
    top_growth = [p for p in data if p['stars_per_day'] > 0]
    top_growth = sorted(top_growth, key=lambda x: x['stars_per_day'], reverse=True)[:20]

    # 按分支/星标比排序（高参与度）
    top_engagement = [p for p in data if p['stars'] > 1000]
    top_engagement = sorted(top_engagement, key=lambda x: x['forks_per_star'], reverse=True)[:20]

    # 按问题数量排序（需要维护的项目）
    top_issues = sorted(data, key=lambda x: x['open_issues'], reverse=True)[:20]

    return {
        'by_stars': [format_top_item(p, 'stars') for p in top_stars],
        'by_activity': [format_top_item(p, 'activity_score') for p in top_activity],
        'by_growth': [format_top_item(p, 'stars_per_day') for p in top_growth],
        'by_engagement': [format_top_item(p, 'forks_per_star') for p in top_engagement],
        'by_issues': [format_top_item(p, 'open_issues') for p in top_issues]
    }


def format_top_item(project, metric_key):
    """格式化排行榜项目"""
    metric_names = {
        'stars': 'Stars',
        'activity_score': 'Activity Score',
        'stars_per_day': 'Stars/Day',
        'forks_per_star': 'Forks/Star',
        'open_issues': 'Open Issues'
    }

    return {
        'rank': project['rank'],
        'full_name': project['full_name'],
        'language': project['language'],
        metric_names[metric_key]: project[metric_key],
        'url': project['url']
    }


def print_stats(structured_data):
    """打印统计信息"""
    stats = structured_data['summary_stats']
    print("\n📈 数据统计摘要:")
    print(f"   项目总数: {stats['total_projects']}")
    print(f"   总星标数: {stats['total_stars']:,}")
    print(f"   总分支数: {stats['total_forks']:,}")
    print(f"   平均星标: {stats['avg_stars']:,}")
    print(f"   平均活跃度: {stats['avg_activity_score']}")
    print(
        f"   活跃项目数: {stats['active_projects']} ({stats['active_projects'] / stats['total_projects'] * 100:.1f}%)")

    langs = structured_data['language_analysis'][:5]
    print(f"\n🔤 热门语言Top 5:")
    for lang in langs:
        print(f"   {lang['language']}: {lang['count']}个项目 ({lang['percentage']}%)")

    topics = structured_data['topic_analysis']['hot_topics'][:5]
    print(f"\n🏷️  热门标签Top 5:")
    for topic in topics:
        print(f"   {topic['topic']}: {topic['count']}次出现")


# 执行数据处理
if __name__ == "__main__":
    input_file = "github_top_500_smart_20251206_170411.json"
    output_file = "github_processed_standardized.json"

    try:
        processed_data = clean_and_normalize_data(input_file, output_file)
        print(f"\n🎉 数据处理完成！输出文件: {output_file}")
        print(f"📁 文件包含以下数据结构:")
        print("   - projects: 清洗后的原始项目数据")
        print("   - summary_stats: 汇总统计")
        print("   - language_analysis: 语言分析")
        print("   - time_analysis: 时间趋势")
        print("   - license_analysis: 许可证分析")
        print("   - topic_analysis: 主题分析")
        print("   - activity_analysis: 活跃度分析")
        print("   - correlation_analysis: 相关性分析")
        print("   - top_lists: 各种排行榜")

    except Exception as e:
        print(f"❌ 数据处理失败: {e}")
# github_crawler_smart.py
import os
import requests
import time
import csv
import base64
import math
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== 智能配置类 ====================
class SmartConfig:
    """智能配置管理"""
    # GitHub令牌
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    if not GITHUB_TOKEN:
        raise ValueError("❌ 错误：请设置 GITHUB_TOKEN 环境变量\n   命令: set GITHUB_TOKEN=你的令牌")

    # 爬取目标
    TARGET_REPOS = 500  # 目标仓库总数
    README_SAMPLE = 500  # 获取README的样本数（减少以降低API压力）
    DEEP_ANALYSIS = 500  # 深度分析的仓库数

    # 智能延迟策略
    MIN_DELAY = 3.0  # 最小请求延迟（秒）
    MAX_DELAY = 15.0  # 最大请求延迟（秒）
    BASE_DELAY = 3.5  # 基础延迟
    DELAY_INCREMENT = 1.3  # 延迟递增因子
    BATCH_EXTRA_DELAY = 8.0  # 批次间额外延迟

    # 批量处理
    BATCH_SIZE = 8  # 减小批量大小
    SEARCH_BATCH_SIZE = 2  # 搜索API批量更小

    # 退避策略
    MAX_RETRIES = 5  # 最大重试次数
    RETRY_BACKOFF = 2.0  # 重试退避因子

    # 输出
    OUTPUT_FILE = f"github_top_{TARGET_REPOS}_smart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


config = SmartConfig()


# ==================== 智能API管理器 ====================
class SmartAPIManager:
    """智能API管理器，使用指数退避策略"""

    def __init__(self):
        self.headers = {
            'Authorization': f'token {config.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.search_api_used = 0
        self.core_api_used = 0
        self.last_request_time = 0
        self.current_delay = config.BASE_DELAY
        self.consecutive_failures = 0
        self.last_reset_check = 0

    def _calculate_dynamic_delay(self) -> float:
        """计算动态延迟"""
        # 基础延迟
        delay = self.current_delay

        # 根据连续失败次数增加延迟
        if self.consecutive_failures > 0:
            delay *= (1 + self.consecutive_failures * 0.5)

        # 确保在最小最大范围内
        return max(config.MIN_DELAY, min(delay, config.MAX_DELAY))

    def _update_delay_based_on_response(self, response, api_type: str):
        """根据响应更新延迟策略"""
        if response is None:
            self.consecutive_failures += 1
            self.current_delay = min(
                config.MAX_DELAY,
                self.current_delay * config.DELAY_INCREMENT
            )
            print(f"⚠️ 请求失败，增加延迟至 {self.current_delay:.1f}秒")
            return

        # 请求成功，减少连续失败计数
        if self.consecutive_failures > 0:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)

        # 检查API限额
        if hasattr(response, 'headers'):
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining:
                remaining_int = int(remaining)

                # 根据剩余限额调整延迟
                if remaining_int < 100:
                    # 限额紧张，增加延迟
                    self.current_delay = min(
                        config.MAX_DELAY,
                        self.current_delay * 1.2
                    )
                elif remaining_int > 1000 and self.current_delay > config.BASE_DELAY:
                    # 限额充足，适当减少延迟
                    self.current_delay = max(
                        config.MIN_DELAY,
                        self.current_delay * 0.9
                    )

        # 检查是否触发次要限制
        if hasattr(response, 'status_code') and response.status_code == 403:
            if 'secondary' in response.text.lower() or 'rate limit' in response.text.lower():
                print("🔴 检测到次要频率限制，大幅增加延迟")
                self.current_delay = min(
                    config.MAX_DELAY,
                    self.current_delay * 2.0
                )
                self.consecutive_failures += 2

    def _wait_for_rate_limit_reset(self, reset_timestamp: int) -> bool:
        """等待API限额重置"""
        now = int(time.time())
        wait_seconds = reset_timestamp - now + 2

        if wait_seconds > 0:
            print(f"⏳ API限制，等待 {wait_seconds} 秒 ({wait_seconds // 60}分{wait_seconds % 60}秒)...")

            # 显示倒计时
            for remaining in range(wait_seconds, 0, -60):
                if remaining > 60:
                    print(f"   剩余约 {remaining // 60} 分钟...")
                    time.sleep(60)
                else:
                    time.sleep(remaining)
                    break

            print("✅ API限额已重置，继续执行")
            return True
        return False

    def make_smart_request(self, url: str, api_type: str = 'core') -> Optional[Dict]:
        """智能请求，使用指数退避策略"""

        # API使用统计
        if api_type == 'search':
            if self.search_api_used >= 30:  # GitHub搜索API硬限制
                print(f"⚠️ 搜索API已达限额 ({self.search_api_used}/30)")
                return None
        else:
            if self.core_api_used >= 5000:  # GitHub核心API硬限制
                print(f"⚠️ 核心API已达限额 ({self.core_api_used}/5000)")
                return None

        # 指数退避重试
        for attempt in range(config.MAX_RETRIES):
            try:
                # 动态延迟控制
                current_delay = self._calculate_dynamic_delay()
                time_since_last = time.time() - self.last_request_time

                if time_since_last < current_delay:
                    sleep_time = current_delay - time_since_last
                    if sleep_time > 0.1:
                        time.sleep(sleep_time)

                # 发送请求
                print(
                    f"  📤 请求 {api_type.upper()} API (尝试 {attempt + 1}/{config.MAX_RETRIES}, 延迟 {current_delay:.1f}s)")
                response = requests.get(
                    url,
                    headers=self.headers,
                    verify=False,
                    timeout=45  # 更长超时
                )

                self.last_request_time = time.time()

                # 更新API使用计数
                if api_type == 'search':
                    self.search_api_used += 1
                else:
                    self.core_api_used += 1

                # 处理响应
                if response.status_code == 200:
                    # 请求成功，更新延迟策略
                    self._update_delay_based_on_response(response, api_type)

                    # 显示API状态
                    if attempt > 0:
                        print(f"  ✅ 请求成功 (第{attempt + 1}次尝试)")

                    remaining = response.headers.get('X-RateLimit-Remaining', '未知')
                    limit = response.headers.get('X-RateLimit-Limit', '未知')

                    if api_type == 'search' and int(remaining) if remaining.isdigit() else 100 < 10:
                        print(f"  ⚠️  搜索API仅剩 {remaining}/{limit} 次")

                    return response.json()

                elif response.status_code == 403:
                    # API限制处理
                    reset_time = response.headers.get('X-RateLimit-Reset')

                    if reset_time and 'rate limit' in response.text.lower():
                        reset_timestamp = int(reset_time)

                        # 如果是次要限制，等待更长时间
                        if 'secondary' in response.text.lower():
                            print("🔴 触发次要频率限制")
                            wait_time = 300  # 次要限制等待5分钟
                            print(f"⏳ 次要限制，等待 {wait_time} 秒...")
                            time.sleep(wait_time)
                            continue

                        # 主要限制，等待到重置时间
                        if self._wait_for_rate_limit_reset(reset_timestamp):
                            continue

                    # 其他403错误
                    print(f"  🔒 403错误: {response.text[:150]}")
                    self._update_delay_based_on_response(response, api_type)

                elif response.status_code == 429:
                    # 太多请求
                    print("  🚫 429: 请求过多")
                    self.current_delay = min(config.MAX_DELAY, self.current_delay * 1.8)
                    retry_after = response.headers.get('Retry-After', 60)
                    time.sleep(int(retry_after))
                    continue

                else:
                    # 其他HTTP错误
                    print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                    self._update_delay_based_on_response(response, api_type)

                # 指数退避等待
                wait_time = config.RETRY_BACKOFF ** attempt
                print(f"  ⏳ 等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)

            except requests.exceptions.Timeout:
                print(f"  ⏱️  请求超时 (尝试 {attempt + 1}/{config.MAX_RETRIES})")
                self.consecutive_failures += 1
                self.current_delay = min(config.MAX_DELAY, self.current_delay * 1.3)
                time.sleep(config.RETRY_BACKOFF ** attempt)

            except requests.exceptions.ConnectionError:
                print(f"  🔌 连接错误 (尝试 {attempt + 1}/{config.MAX_RETRIES})")
                self.consecutive_failures += 1
                self.current_delay = min(config.MAX_DELAY, self.current_delay * 1.5)
                time.sleep(config.RETRY_BACKOFF ** attempt * 2)

            except Exception as e:
                print(f"  ⚠️  异常: {type(e).__name__}: {str(e)[:100]}")
                self.consecutive_failures += 1
                time.sleep(config.RETRY_BACKOFF ** attempt)

        print(f"  ❌ 请求失败，已重试 {config.MAX_RETRIES} 次: {url}")
        self.consecutive_failures += 1
        self.current_delay = min(config.MAX_DELAY, self.current_delay * 1.5)
        return None

    def get_api_status(self) -> Dict:
        """获取当前API状态"""
        status = {
            'search_used': self.search_api_used,
            'core_used': self.core_api_used,
            'current_delay': self.current_delay,
            'consecutive_failures': self.consecutive_failures
        }

        # 检查实际限额
        try:
            url = "https://api.github.com/rate_limit"
            data = self.make_smart_request(url, 'core')
            if data:
                status['search_remaining'] = data['resources']['search']['remaining']
                status['core_remaining'] = data['resources']['core']['remaining']
                status['search_limit'] = data['resources']['search']['limit']
                status['core_limit'] = data['resources']['core']['limit']
        except:
            pass

        return status


# ==================== 智能爬虫类 ====================
class SmartGitHubCrawler:
    """智能GitHub仓库爬虫"""

    def __init__(self):
        self.api = SmartAPIManager()
        self.repos = []
        self.start_time = time.time()

    def crawl_intelligently(self) -> List[Dict]:
        """智能爬取所有数据"""
        print("=" * 70)
        print("🚀 智能GitHub仓库爬虫启动")
        print(f"📊 目标: {config.TARGET_REPOS}个仓库")
        print(f"⚙️  配置: 延迟 {config.MIN_DELAY}-{config.MAX_DELAY}秒, 批量 {config.BATCH_SIZE}")
        print("=" * 70)

        # 显示初始API状态
        self._print_api_status()

        try:
            # 步骤1: 获取仓库基础信息
            print("\n" + "=" * 50)
            print("📊 步骤1: 获取仓库基础信息")
            print("=" * 50)

            basic_repos = self._get_basic_repositories()
            if not basic_repos:
                print("❌ 未获取到基础信息")
                return []

            # 步骤2: 智能补充详细信息
            print("\n" + "=" * 50)
            print("📈 步骤2: 智能补充详细信息")
            print("=" * 50)

            detailed_repos = self._enrich_repositories(basic_repos)

            # 步骤3: 深度分析（可选）
            if config.DEEP_ANALYSIS > 0:
                print("\n" + "=" * 50)
                print("🔍 步骤3: 深度分析")
                print("=" * 50)

                final_repos = self._deep_analyze(detailed_repos)
            else:
                final_repos = detailed_repos

            # 计算总耗时
            total_time = time.time() - self.start_time
            print(f"\n✅ 所有步骤完成!")
            print(f"⏱️  总耗时: {total_time:.1f}秒 ({total_time / 60:.1f}分钟)")

            return final_repos

        except KeyboardInterrupt:
            print("\n⚠️ 用户中断，保存已获取数据...")
            return self.repos
        except Exception as e:
            print(f"\n❌ 爬取过程中出现异常: {type(e).__name__}: {e}")
            return self.repos

    def _get_basic_repositories(self) -> List[Dict]:
        """获取基础仓库信息"""
        all_repos = []
        pages_needed = math.ceil(config.TARGET_REPOS / 100)

        print(f"需要获取 {pages_needed} 页数据 (每页100个)")

        for page in range(1, pages_needed + 1):
            print(f"\n📄 获取第 {page}/{pages_needed} 页...")

            # 批次间额外延迟
            if page > 1:
                extra_delay = config.BATCH_EXTRA_DELAY
                print(f"⏳ 页间延迟 {extra_delay}秒...")
                time.sleep(extra_delay)

            url = (
                f"https://api.github.com/search/repositories?"
                f"q=stars:>1000&sort=stars&order=desc&per_page=100&page={page}"
            )

            data = self.api.make_smart_request(url, api_type='search')

            if data and 'items' in data:
                for item in data['items']:
                    if len(all_repos) >= config.TARGET_REPOS:
                        break

                    repo_info = {
                        'id': item['id'],
                        'full_name': item['full_name'],
                        'url': item['html_url'],
                        'description': (item.get('description') or '')[:200],
                        'stars': item['stargazers_count'],
                        'forks': item.get('forks_count', 0),
                        'language': item.get('language', '') or '未知',
                        'created_at': item.get('created_at', '')[:10],
                        'updated_at': item.get('pushed_at', '')[:10],
                        'open_issues': item.get('open_issues_count', 0),
                        'topics': ', '.join(item.get('topics', [])[:3]),
                        'license': (item.get('license', {}) or {}).get('name', '无'),
                        'readme_summary': '待获取',
                        'has_readme': False
                    }
                    all_repos.append(repo_info)

            print(f"  ✅ 已获取: {len(all_repos)}/{config.TARGET_REPOS}")

            # 显示当前API状态
            if page % 2 == 0:
                self._print_api_status()

        print(f"\n🎯 基础信息获取完成: {len(all_repos)} 个仓库")
        return all_repos

    def _enrich_repositories(self, repos: List[Dict]) -> List[Dict]:
        """智能补充仓库详细信息"""
        print(f"准备补充 {min(config.README_SAMPLE, len(repos))} 个仓库的详细信息")

        for i in range(0, min(config.README_SAMPLE, len(repos)), config.BATCH_SIZE):
            batch_end = min(i + config.BATCH_SIZE, config.README_SAMPLE, len(repos))
            batch = repos[i:batch_end]

            print(f"\n🔧 处理批次 {i + 1}-{batch_end}/{min(config.README_SAMPLE, len(repos))}")

            for j, repo in enumerate(batch):
                repo_idx = i + j + 1

                # 获取README
                if repo_idx <= config.README_SAMPLE:
                    readme = self._get_readme_intelligent(repo['full_name'])
                    repo['readme_summary'] = readme
                    repo['has_readme'] = readme != "无README" and readme != "获取失败"

                # 更新进度
                if (repo_idx) % 5 == 0:
                    print(f"  进度: {repo_idx}/{min(config.README_SAMPLE, len(repos))}")
                    self._print_progress_bar(repo_idx, min(config.README_SAMPLE, len(repos)))

            # 批次间智能延迟
            if batch_end < min(config.README_SAMPLE, len(repos)):
                batch_delay = config.BATCH_EXTRA_DELAY * (1 + self.api.consecutive_failures * 0.3)
                print(f"⏳ 批次间延迟 {batch_delay:.1f}秒...")
                time.sleep(batch_delay)

        print(f"\n✅ 详细信息补充完成")
        return repos

    def _deep_analyze(self, repos: List[Dict]) -> List[Dict]:
        """深度分析前N个仓库"""
        analysis_count = min(config.DEEP_ANALYSIS, len(repos))

        if analysis_count <= 0:
            return repos

        print(f"深度分析前 {analysis_count} 个高星仓库")

        for i, repo in enumerate(repos[:analysis_count]):
            print(f"\n🔍 分析 {i + 1}/{analysis_count}: {repo['full_name']}")

            # 获取贡献者信息
            contributors = self._get_top_contributors(repo['full_name'])
            if contributors:
                repo['top_contributor'] = contributors[0].get('login', '')
                repo['contributor_count'] = len(contributors)

            # 获取最近提交信息
            commits = self._get_recent_commits(repo['full_name'])
            if commits:
                repo['recent_commits'] = len(commits)
                if commits:
                    last_commit = commits[0].get('commit', {}).get('author', {}).get('date', '')
                    if last_commit:
                        repo['last_commit_date'] = last_commit[:10]

            # 计算活跃度分数
            repo['activity_score'] = self._calculate_activity_score(repo)

            # 每5个仓库显示一次API状态
            if (i + 1) % 5 == 0:
                self._print_api_status()

        print(f"\n✅ 深度分析完成: {analysis_count} 个仓库")
        return repos

    def _get_readme_intelligent(self, full_name: str) -> str:
        """智能获取README内容"""
        owner, repo_name = full_name.split('/', 1)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"

        data = self.api.make_smart_request(url, api_type='core')

        if data and 'content' in data:
            try:
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                # 智能提取摘要
                lines = content.split('\n')
                summary_lines = []

                # 提取前5个非空行或找到第一个标题
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        summary_lines.append(line)
                        if len(summary_lines) >= 3:
                            break

                if summary_lines:
                    summary = ' '.join(summary_lines)[:400]
                else:
                    # 如果没有合适内容，取前200个字符
                    summary = content[:200]

                return summary + "..." if len(content) > len(summary) else summary

            except Exception as e:
                print(f"  ⚠️ README解码失败: {e}")
                return "解码失败"

        return "无README"

    def _get_top_contributors(self, full_name: str, limit: int = 3) -> List[Dict]:
        """获取前几位贡献者"""
        url = f"https://api.github.com/repos/{full_name}/contributors?per_page={limit}"
        return self.api.make_smart_request(url, api_type='core') or []

    def _get_recent_commits(self, full_name: str, limit: int = 5) -> List[Dict]:
        """获取最近提交"""
        url = f"https://api.github.com/repos/{full_name}/commits?per_page={limit}"
        return self.api.make_smart_request(url, api_type='core') or []

    def _calculate_activity_score(self, repo: Dict) -> float:
        """计算活跃度分数"""
        score = 50.0  # 基础分

        try:
            # 基于更新时间的分数
            if 'updated_at' in repo and repo['updated_at']:
                last_update = datetime.strptime(repo['updated_at'], '%Y-%m-%d')
                days_since = (datetime.now() - last_update).days

                if days_since < 7:
                    score += 25
                elif days_since < 30:
                    score += 15
                elif days_since < 90:
                    score += 5
                elif days_since > 365:
                    score -= 15

            # 基于star数量的分数
            stars = repo.get('stars', 0)
            if stars > 50000:
                score += 15
            elif stars > 10000:
                score += 10
            elif stars > 1000:
                score += 5

            # 基于Issue活跃度的分数
            open_issues = repo.get('open_issues', 0)
            if stars > 0 and open_issues > 0:
                issue_ratio = open_issues / stars
                if issue_ratio < 0.01:
                    score += 10  # Issue比例低，维护良好
                elif issue_ratio > 0.1:
                    score -= 5  # Issue比例高，可能有问题

        except Exception as e:
            print(f"  ⚠️ 活跃度计算失败: {e}")

        return round(max(0, min(score, 100)), 1)

    def _print_api_status(self):
        """打印当前API状态"""
        status = self.api.get_api_status()

        print("\n📊 当前API状态:")
        print(f"  搜索API: {status.get('search_used', 0)}/{status.get('search_limit', 30)}次")
        print(f"  核心API: {status.get('core_used', 0)}/{status.get('core_limit', 5000)}次")
        print(f"  当前延迟: {status.get('current_delay', config.BASE_DELAY):.1f}秒")
        print(f"  连续失败: {status.get('consecutive_failures', 0)}次")

    def _print_progress_bar(self, current: int, total: int, length: int = 30):
        """打印进度条"""
        percent = current / total
        filled_length = int(length * percent)
        bar = '█' * filled_length + '░' * (length - filled_length)
        print(f"  [{bar}] {current}/{total} ({percent:.1%})")


# ==================== 数据保存 ====================
def save_repositories_to_csv(repos: List[Dict], filename: str):
    """保存仓库数据到CSV"""
    if not repos:
        print("❌ 无数据可保存")
        return False

    try:
        # 首先确保所有仓库都有rank字段
        for i, repo in enumerate(repos):
            repo['rank'] = i + 1

        # 确定字段顺序
        field_order = [
            'rank', 'full_name', 'url', 'description', 'stars', 'forks',
            'language', 'created_at', 'updated_at', 'last_commit_date',
            'open_issues', 'topics', 'license', 'readme_summary', 'has_readme',
            'top_contributor', 'contributor_count', 'recent_commits', 'activity_score'
        ]

        # 收集所有实际存在的字段
        all_fields = set()
        for repo in repos:
            all_fields.update(repo.keys())

        # 确保rank在field_order中
        if 'rank' not in field_order:
            field_order.insert(0, 'rank')

        # 排序字段：先field_order中的字段，然后其他字段
        fieldnames = [f for f in field_order if f in all_fields]
        other_fields = sorted([f for f in all_fields if f not in field_order])
        fieldnames.extend(other_fields)

        # 写入CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(repos)

        print(f"\n💾 数据保存成功!")
        print(f"  文件: {filename}")
        print(f"  记录数: {len(repos)}")
        print(f"  字段数: {len(fieldnames)}")
        print(f"  字段列表: {', '.join(fieldnames)}")

        return True

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# ==================== 主程序 ====================
def main():
    print("🤖 智能GitHub仓库爬虫系统")
    print("=" * 60)
    print("特点:")
    print("  • 指数退避策略，自动适应API限制")
    print("  • 动态延迟调整，避免触发频率限制")
    print("  • 智能错误恢复，断点续传能力")
    print("  • 详细状态监控，实时进度显示")
    print("=" * 60)

    try:
        # 创建爬虫实例
        crawler = SmartGitHubCrawler()

        # 开始爬取
        start_time = time.time()
        repositories = crawler.crawl_intelligently()

        if repositories:
            # 保存结果
            success = save_repositories_to_csv(repositories, config.OUTPUT_FILE)

            if success:
                # 显示最终统计
                total_time = time.time() - start_time
                print("\n" + "=" * 60)
                print("🎉 爬取任务完成!")
                print("=" * 60)
                print(f"📊 统计信息:")
                print(f"  获取仓库数: {len(repositories)} 个")
                print(f"  总耗时: {total_time:.1f}秒 ({total_time / 60:.1f}分钟)")
                print(f"  平均速度: {len(repositories) / (total_time / 60):.1f} 个/分钟")

                # 显示API使用总结
                final_status = crawler.api.get_api_status()
                print(f"\n📡 API使用总结:")
                print(f"  搜索API使用: {final_status.get('search_used', 0)}/30 次")
                print(f"  核心API使用: {final_status.get('core_used', 0)}/5000 次")
                print(f"  最终请求延迟: {final_status.get('current_delay', 0):.1f}秒")

        else:
            print("❌ 未获取到任何仓库数据")

    except KeyboardInterrupt:
        print("\n\n⚠️ 程序被用户中断")
    except Exception as e:
        print(f"\n💥 程序运行异常: {type(e).__name__}: {e}")


if __name__ == '__main__':
    main()
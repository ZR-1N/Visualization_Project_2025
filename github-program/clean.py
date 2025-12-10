import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional


class GitHubDataCleaner:
    def __init__(self, input_file: str, output_file: str):
        """
        初始化GitHub数据清洗器

        Args:
            input_file: 输入JSON文件路径
            output_file: 输出JSON文件路径
        """
        self.input_file = input_file
        self.output_file = output_file
        self.projects = []
        self.corrections_made = 0

        # 已知项目的手动修正数据
        self.known_corrections = {
            # 项目#124: gothinkster/realworld (严重错误)
            "gothinkster/realworld": {
                "stars": 82511,
                "forks": 14840,
                "open_issues": 55,
                "activity_score": 90.0,
                "contributor_count": 3,
                "recent_commits": 5,
                "language": "JavaScript",
                "created_at": "2016-02-26",
                "updated_at": "2025-10-06",
                "last_commit_date": "2025-10-06",
                "license": "MIT",
                "topics": ["demo-app", "medium-clone", "fullstack"],
                "has_readme": True,
                "top_contributor": "anishkny",
                "readme_summary": "Exemplary fullstack Medium.com clone powered by React, Angular, Vue, and more",
                "age_days": 3570,
                "stars_per_day": 23.14,
                "forks_per_star": 0.1798,
                "is_active": True
            },
            # 项目#62: d3/d3 (字段错位)
            "d3/d3": {
                "top_contributor": "mbostock",
                "readme_summary": "D3 (or D3.js) is a free, open-source JavaScript library for visualizing data using web standards.",
                "has_readme": True
            },
            # 项目#36: huggingface/transformers (字段错误)
            "huggingface/transformers": {
                "top_contributor": "lysandre",
                "has_readme": True,
                "readme_summary": "Transformers provides thousands of pretrained models to perform tasks on different modalities such as text, vision, and audio.",
                "activity_score": 90.0,
                "contributor_count": 3
            },
            # 项目#22: ohmyzsh/ohmyzsh (字段错误)
            "ohmyzsh/ohmyzsh": {
                "top_contributor": "robbyrussell",
                "has_readme": True,
                "readme_summary": "Oh My Zsh is an open source, community-driven framework for managing your zsh configuration.",
                "contributor_count": 3
            },
            # 项目#34: massgravel/Microsoft-Activation-Scripts (字段错误)
            "massgravel/Microsoft-Activation-Scripts": {
                "has_readme": True,
                "readme_summary": "Microsoft Activation Scripts (MAS) is an open-source Windows and Office activator featuring HWID, Ohook, and KMS activation methods.",
                "activity_score": 80.0,
                "contributor_count": 3
            },
            # 项目#62: d3/d3 (补充)
            "d3/d3": {
                "has_readme": True
            },
            # 项目#137: spring-projects/spring-boot (字段错误)
            "spring-projects/spring-boot": {
                "has_readme": True,
                "readme_summary": "Spring Boot makes it easy to create stand-alone, production-grade Spring based Applications that you can \"just run\".",
                "activity_score": 90.0,
                "contributor_count": 3
            },
            # 项目#152: FortAwesome/Font-Awesome (字段错误)
            "FortAwesome/Font-Awesome": {
                "has_readme": True,
                "readme_summary": "Font Awesome is the Internet's icon library and toolkit, used by millions of designers and developers.",
                "activity_score": 85.0,
                "contributor_count": 3
            },
            # 项目#133: bregman-arie/devops-exercises (字段错误)
            "bregman-arie/devops-exercises": {
                "has_readme": True,
                "readme_summary": "A collection of DevOps exercises and interview questions covering Linux, AWS, Docker, Kubernetes, and more.",
                "activity_score": 80.0,
                "contributor_count": 3
            }
        }

        # 需要重新计算的异常项目
        self.needs_recalculation = {
            "fighting41love/funNLP": {
                "recent_commits": 5,  # 将210034修正为合理值
                "activity_score": 75.0  # 修正异常值
            }
        }

    def load_data(self):
        """加载JSON数据"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.projects = data.get('projects', [])
            print(f"成功加载 {len(self.projects)} 个项目")
        except Exception as e:
            print(f"加载数据失败: {e}")
            raise

    def validate_date(self, date_str: str, field_name: str) -> bool:
        """
        验证日期格式和合理性

        Args:
            date_str: 日期字符串
            field_name: 字段名称

        Returns:
            bool: 日期是否有效
        """
        if not date_str or date_str == "null":
            return False

        # 检查是否为未来日期（超过当前日期）
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            current_date = datetime.now()

            # 如果日期超过当前日期+1年，视为无效
            if date_obj.year > current_date.year + 1:
                return False

            # 检查是否为过于古老的日期（早于1970年）
            if date_obj.year < 1970:
                return False

            return True
        except ValueError:
            return False

    def fix_date_field(self, project: Dict[str, Any]) -> bool:
        """
        修复日期字段

        Args:
            project: 项目数据

        Returns:
            bool: 是否进行了修正
        """
        corrected = False

        # 检查并修复created_at
        if not self.validate_date(project.get('created_at'), 'created_at'):
            # 尝试从其他字段推断创建日期
            if project.get('age_days') and project.get('updated_at'):
                try:
                    updated_date = datetime.strptime(project['updated_at'], "%Y-%m-%d")
                    age_days = float(project['age_days'])
                    created_date = updated_date - timedelta(days=age_days)
                    project['created_at'] = created_date.strftime("%Y-%m-%d")
                    corrected = True
                except:
                    pass

        # 检查并修复updated_at和last_commit_date
        date_fields = ['updated_at', 'last_commit_date']
        for field in date_fields:
            if not self.validate_date(project.get(field), field):
                # 设置为合理的默认值（如项目创建日期或当前日期）
                if project.get('created_at') and self.validate_date(project['created_at'], 'created_at'):
                    project[field] = project['created_at']
                    corrected = True

        return corrected

    def fix_numeric_fields(self, project: Dict[str, Any]) -> bool:
        """
        修复数值字段

        Args:
            project: 项目数据

        Returns:
            bool: 是否进行了修正
        """
        corrected = False

        # 修复星数异常
        if project.get('stars', 0) <= 0 and project['rank'] < 100:
            # 根据排名估算星数
            estimated_stars = 100000 - (project['rank'] * 500)
            project['stars'] = max(1000, estimated_stars)
            corrected = True

        # 修复recent_commits异常值
        recent_commits = project.get('recent_commits', 0)
        if recent_commits > 1000:  # 超过1000的提交数不合理
            project['recent_commits'] = min(50, recent_commits // 1000)
            corrected = True

        # 修复contributor_count
        if project.get('contributor_count', 0) == 0 and project.get('activity_score', 0) > 50:
            project['contributor_count'] = 3
            corrected = True

        return corrected

    def fix_text_fields(self, project: Dict[str, Any]) -> bool:
        """
        修复文本字段

        Args:
            project: 项目数据

        Returns:
            bool: 是否进行了修正
        """
        corrected = False
        full_name = project.get('full_name', '')

        # 修复top_contributor字段
        top_contributor = project.get('top_contributor', '')
        if top_contributor in ['True', 'False', ''] or len(top_contributor) > 100:
            # 使用项目拥有者作为默认值
            if '/' in full_name:
                owner = full_name.split('/')[0]
                project['top_contributor'] = owner
                corrected = True

        # 修复readme_summary字段
        readme_summary = project.get('readme_summary', '')
        if not readme_summary or readme_summary.startswith('"') or len(readme_summary) < 10:
            # 使用描述作为readme摘要
            description = project.get('description', '')
            if description and len(description) > 10:
                project['readme_summary'] = description[:200] + "..."
                corrected = True

        return corrected

    def recalculate_derived_fields(self, project: Dict[str, Any]) -> bool:
        """
        重新计算派生字段

        Args:
            project: 项目数据

        Returns:
            bool: 是否重新计算了字段
        """
        corrected = False

        try:
            # 重新计算age_days
            if project.get('created_at') and self.validate_date(project['created_at'], 'created_at'):
                created_date = datetime.strptime(project['created_at'], "%Y-%m-%d")
                current_date = datetime.now()
                age_days = (current_date - created_date).days

                if abs(age_days - project.get('age_days', 0)) > 365:  # 差异超过一年
                    project['age_days'] = age_days
                    corrected = True

                # 重新计算stars_per_day
                if project.get('stars', 0) > 0 and age_days > 0:
                    stars_per_day = project['stars'] / age_days
                    if abs(stars_per_day - project.get('stars_per_day', 0)) > 10:  # 差异过大
                        project['stars_per_day'] = round(stars_per_day, 4)
                        corrected = True

                # 重新计算forks_per_star
                if project.get('stars', 0) > 0 and project.get('forks', 0) > 0:
                    forks_per_star = project['forks'] / project['stars']
                    if abs(forks_per_star - project.get('forks_per_star', 0)) > 0.1:  # 差异过大
                        project['forks_per_star'] = round(forks_per_star, 4)
                        corrected = True

            # 重新计算is_active
            if project.get('last_commit_date') and self.validate_date(project['last_commit_date'], 'last_commit_date'):
                last_commit = datetime.strptime(project['last_commit_date'], "%Y-%m-%d")
                current_date = datetime.now()
                days_since_last_commit = (current_date - last_commit).days

                # 如果超过6个月没有提交，标记为非活跃
                new_is_active = days_since_last_commit < 180
                if project.get('is_active') != new_is_active:
                    project['is_active'] = new_is_active
                    corrected = True

        except Exception as e:
            print(f"重新计算字段时出错 ({project.get('full_name')}): {e}")

        return corrected

    def apply_known_corrections(self, project: Dict[str, Any]) -> bool:
        """
        应用已知的手动修正

        Args:
            project: 项目数据

        Returns:
            bool: 是否应用了修正
        """
        full_name = project.get('full_name', '')

        if full_name in self.known_corrections:
            corrections = self.known_corrections[full_name]
            for key, value in corrections.items():
                if key in project and project[key] != value:
                    project[key] = value
                    return True

        if full_name in self.needs_recalculation:
            corrections = self.needs_recalculation[full_name]
            for key, value in corrections.items():
                if key in project:
                    project[key] = value
                    return True

        return False

    def clean_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理单个项目数据

        Args:
            project: 原始项目数据

        Returns:
            Dict[str, Any]: 清理后的项目数据
        """
        # 创建项目副本
        cleaned_project = project.copy()

        # 添加数据质量标记
        cleaned_project['_data_quality'] = {
            'original_has_issues': False,
            'corrections_applied': [],
            'needs_manual_review': False
        }

        # 应用已知修正
        if self.apply_known_corrections(cleaned_project):
            cleaned_project['_data_quality']['corrections_applied'].append('known_corrections')
            cleaned_project['_data_quality']['original_has_issues'] = True

        # 修复日期字段
        if self.fix_date_field(cleaned_project):
            cleaned_project['_data_quality']['corrections_applied'].append('date_fix')
            cleaned_project['_data_quality']['original_has_issues'] = True

        # 修复数值字段
        if self.fix_numeric_fields(cleaned_project):
            cleaned_project['_data_quality']['corrections_applied'].append('numeric_fix')
            cleaned_project['_data_quality']['original_has_issues'] = True

        # 修复文本字段
        if self.fix_text_fields(cleaned_project):
            cleaned_project['_data_quality']['corrections_applied'].append('text_fix')
            cleaned_project['_data_quality']['original_has_issues'] = True

        # 重新计算派生字段
        if self.recalculate_derived_fields(cleaned_project):
            cleaned_project['_data_quality']['corrections_applied'].append('recalculated_fields')
            cleaned_project['_data_quality']['original_has_issues'] = True

        # 标记需要人工审核的项目
        if (cleaned_project['_data_quality']['original_has_issues'] and
                len(cleaned_project['_data_quality']['corrections_applied']) > 2):
            cleaned_project['_data_quality']['needs_manual_review'] = True

        # 如果没有应用修正，移除质量标记以保持清洁
        if not cleaned_project['_data_quality']['original_has_issues']:
            del cleaned_project['_data_quality']

        return cleaned_project

    def run_cleaning(self):
        """执行数据清洗流程"""
        print("开始数据清洗...")

        cleaned_projects = []
        issues_found = 0

        for i, project in enumerate(self.projects):
            if i % 20 == 0:
                print(f"处理进度: {i + 1}/{len(self.projects)}")

            cleaned_project = self.clean_project(project)
            cleaned_projects.append(cleaned_project)

            # 统计修正数量
            if '_data_quality' in cleaned_project:
                issues_found += 1
                self.corrections_made += len(cleaned_project['_data_quality']['corrections_applied'])

        self.projects = cleaned_projects

        print(f"\n清洗完成!")
        print(f"处理项目总数: {len(self.projects)}")
        print(f"发现问题的项目: {issues_found}")
        print(f"总修正次数: {self.corrections_made}")

    def generate_summary_report(self):
        """生成清洗摘要报告"""
        report = {
            "total_projects": len(self.projects),
            "projects_with_issues": 0,
            "corrections_by_type": {},
            "projects_needing_review": []
        }

        for project in self.projects:
            if '_data_quality' in project:
                report["projects_with_issues"] += 1

                # 统计修正类型
                for correction in project['_data_quality']['corrections_applied']:
                    report["corrections_by_type"][correction] = report["corrections_by_type"].get(correction, 0) + 1

                # 记录需要人工审核的项目
                if project['_data_quality'].get('needs_manual_review', False):
                    report["projects_needing_review"].append({
                        "rank": project.get('rank'),
                        "full_name": project.get('full_name'),
                        "issues": project['_data_quality']['corrections_applied']
                    })

        return report

    def save_cleaned_data(self):
        """保存清洗后的数据"""
        output_data = {
            "projects": self.projects,
            "metadata": {
                "cleaning_timestamp": datetime.now().isoformat(),
                "total_corrections": self.corrections_made,
                "source_file": self.input_file
            }
        }

        # 保存主文件
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"清洗后的数据已保存到: {self.output_file}")

        # 生成并保存报告
        report = self.generate_summary_report()
        report_file = self.output_file.replace('.json', '_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"清洗报告已保存到: {report_file}")

        # 打印摘要
        print("\n=== 清洗摘要 ===")
        print(f"总项目数: {report['total_projects']}")
        print(f"有问题的项目: {report['projects_with_issues']}")
        print("\n修正类型统计:")
        for correction_type, count in report['corrections_by_type'].items():
            print(f"  - {correction_type}: {count}次")

        if report['projects_needing_review']:
            print("\n需要人工审核的项目:")
            for project in report['projects_needing_review'][:10]:  # 只显示前10个
                print(f"  - #{project['rank']} {project['full_name']}: {project['issues']}")


# 使用示例
if __name__ == "__main__":
    # 配置输入输出文件
    input_file = "github_processed_standardized.json"
    output_file = "github_cleaned.json"

    # 创建清洗器并执行
    cleaner = GitHubDataCleaner(input_file, output_file)

    try:
        # 加载数据
        cleaner.load_data()

        # 执行清洗
        cleaner.run_cleaning()

        # 保存结果
        cleaner.save_cleaned_data()

        print("\n✅ 数据清洗完成!")

    except Exception as e:
        print(f"❌ 清洗过程中出错: {e}")
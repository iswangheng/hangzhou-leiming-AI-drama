"""
技能合并模块 - 螺旋式迭代更新技能文件
"""
import re
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .data_models import SkillFile, HighlightType, HookType, EditingRule, AnalysisResult
from .config import TrainingConfig


def load_latest_skill() -> Optional[SkillFile]:
    """读取最新的技能文件

    Returns:
        技能文件对象，如果不存在则返回None
    """
    latest_path = TrainingConfig.SKILLS_DIR / "ai-drama-clipping-thoughts-latest.md"

    if not latest_path.exists():
        return None

    with open(latest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析版本
    version_match = re.search(r'版本:\s*(v[\d.]+)', content)
    version = version_match.group(1) if version_match else "v0.0"

    # 解析统计信息
    statistics = {}
    stats_match = re.search(r'- 训练项目数:\s*(\d+)', content)
    if stats_match:
        statistics['project_count'] = int(stats_match.group(1))

    stats_match = re.search(r'- 累计集数:\s*(\d+)', content)
    if stats_match:
        statistics['episode_count'] = int(stats_match.group(1))

    stats_match = re.search(r'- 高光类型数:\s*(\d+)', content)
    if stats_match:
        statistics['highlight_type_count'] = int(stats_match.group(1))

    stats_match = re.search(r'- 钩子类型数:\s*(\d+)', content)
    if stats_match:
        statistics['hook_type_count'] = int(stats_match.group(1))

    # 解析高光类型和钩子类型
    highlight_types = parse_skill_types(content, "高光类型", HighlightType)
    hook_types = parse_skill_types(content, "钩子类型", HookType)

    return SkillFile(
        version=version,
        updated_at="",
        highlight_types=highlight_types,
        hook_types=hook_types,
        editing_rules=[],
        statistics=statistics
    )


def parse_skill_types(content: str, section_name: str, type_class) -> List:
    """解析技能类型

    Args:
        content: 文件内容
        section_name: 段落名称（如"高光类型"）
        type_class: 类型类（HighlightType或HookType）

    Returns:
        类型列表
    """
    types = []

    # 找到段落
    section_pattern = rf"## .*?{section_name}.*?\n(.*?)(?=##|\Z)"
    section_match = re.search(section_pattern, content, re.DOTALL)

    if not section_match:
        return types

    section_content = section_match.group(1)

    # 解析每个类型
    item_pattern = r"###\s+(\d+\.)?\s*(.+?)\n\n\*\*描述\*\*:\s*(.+?)\n\*\*视觉特征\*\*:(.+?)\n\*\*听觉特征\*\*:(.+?)\n\*\*典型场景\*\*:(.+?)\n\n"
    item_matches = re.finditer(item_pattern, section_content, re.DOTALL)

    for match in item_matches:
        name = match.group(2).strip()
        description = match.group(3).strip()

        # 解析特征列表
        visual_text = match.group(4).strip()
        visual_features = [line.strip().lstrip('- ') for line in visual_text.split('\n') if line.strip() and line.strip() != '**视觉特征**:']

        audio_text = match.group(5).strip()
        audio_features = [line.strip().lstrip('- ') for line in audio_text.split('\n') if line.strip() and line.strip() != '**听觉特征**:']

        scenarios_text = match.group(6).strip()
        typical_scenarios = [line.strip().lstrip('- ') for line in scenarios_text.split('\n') if line.strip() and line.strip() != '**典型场景**:']

        # 创建类型对象
        if type_class == HighlightType:
            skill_type = HighlightType(
                name=name,
                description=description,
                visual_features={"features": visual_features},
                audio_features={"features": audio_features},
                emotion_features={},
                plot_features={},
                content_features={},
                typical_scenarios=typical_scenarios
            )
        else:
            skill_type = HookType(
                name=name,
                description=description,
                visual_features={"features": visual_features},
                audio_features={"features": audio_features},
                emotion_features={},
                plot_features={},
                content_features={},
                typical_scenarios=typical_scenarios
            )

        types.append(skill_type)

    return types


def extract_types_from_results(results: List[AnalysisResult]) -> tuple[List[HighlightType], List[HookType]]:
    """从分析结果中提取类型

    Args:
        results: 分析结果列表

    Returns:
        (高光类型列表, 钩子类型列表)
    """
    highlight_types_dict = {}
    hook_types_dict = {}

    for result in results:
        if result.type == "高光点":
            type_dict = highlight_types_dict
            type_class = HighlightType
        else:
            type_dict = hook_types_dict
            type_class = HookType

        category = result.category
        if category not in type_dict:
            # 创建新类型
            type_dict[category] = type_class(
                name=category,
                description=result.category_description,
                visual_features=result.visual_features,
                audio_features=result.audio_features,
                emotion_features=result.emotion_features,
                plot_features=result.plot_features,
                content_features=result.content_features,
                typical_scenarios=[]
            )
        else:
            # 合并特征
            existing_type = type_dict[category]
            merge_features(existing_type.visual_features, result.visual_features)
            merge_features(existing_type.audio_features, result.audio_features)
            merge_features(existing_type.emotion_features, result.emotion_features)
            merge_features(existing_type.plot_features, result.plot_features)
            merge_features(existing_type.content_features, result.content_features)

    return list(highlight_types_dict.values()), list(hook_types_dict.values())


def merge_features(target: Dict[str, Any], source: Dict[str, Any]):
    """合并特征字典

    Args:
        target: 目标特征字典
        source: 源特征字典
    """
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, list) and isinstance(target[key], list):
            # 合并列表，去重
            target[key] = list(set(target[key] + value))
        elif isinstance(value, dict) and isinstance(target[key], dict):
            # 递归合并字典
            merge_features(target[key], value)


def merge_skill_types(old_types: List, new_types: List, type_class) -> List:
    """合并技能类型列表（去重）

    Args:
        old_types: 旧类型列表
        new_types: 新类型列表
        type_class: 类型类（HighlightType或HookType）

    Returns:
        合并后的类型列表
    """
    type_map = {}

    # 旧类型
    for t in old_types:
        type_map[t.name] = t

    # 新类型
    for t in new_types:
        if t.name in type_map:
            # 合并特征
            old_t = type_map[t.name]
            merge_features(old_t.visual_features, t.visual_features)
            merge_features(old_t.audio_features, t.audio_features)
            merge_features(old_t.emotion_features, t.emotion_features)
            merge_features(old_t.plot_features, t.plot_features)
            merge_features(old_t.content_features, t.content_features)

            # 合并典型场景
            if hasattr(old_t, 'typical_scenarios') and hasattr(t, 'typical_scenarios'):
                old_t.typical_scenarios = list(set(old_t.typical_scenarios + t.typical_scenarios))
        else:
            type_map[t.name] = t

    return list(type_map.values())


def increment_version(version: str) -> str:
    """递增版本号

    Args:
        version: 当前版本号 (如 "v1.2")

    Returns:
        新版本号
    """
    match = re.search(r'v(\d+)\.(\d+)', version)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) + 1
        return f"v{major}.{minor}"
    return "v1.0"


def merge_skills(
    old_skill: Optional[SkillFile],
    new_results: List[AnalysisResult],
    project_count: int
) -> SkillFile:
    """合并新旧技能

    Args:
        old_skill: 旧的技能文件
        new_results: 新的分析结果
        project_count: 本次训练的项目数

    Returns:
        合并后的技能文件
    """
    # 从新结果提取类型
    new_highlight_types, new_hook_types = extract_types_from_results(new_results)

    # 与历史合并（去重）
    old_highlight_types = old_skill.highlight_types if old_skill else []
    old_hook_types = old_skill.hook_types if old_skill else []

    all_highlight_types = merge_skill_types(old_highlight_types, new_highlight_types, HighlightType)
    all_hook_types = merge_skill_types(old_hook_types, new_hook_types, HookType)

    # V5.0 新增：自动简化钩子类型
    all_hook_types = simplify_hook_types(
        all_hook_types,
        min_occurrences=3,      # 至少出现3次
        max_overlap=0.8,        # 重叠度不超过80%
        max_count=15            # 最多保留15种
    )

    # V5.1 新增：自动简化高光类型
    all_highlight_types = simplify_highlight_types(
        all_highlight_types,
        min_occurrences=2,      # 高光类型至少2次（数据较少）
        max_overlap=0.7,        # 重叠度70%
        max_count=12            # 最多保留12种
    )

    # 添加默认类型
    if not any(t.name == "开篇高光" for t in all_highlight_types):
        all_highlight_types.insert(0, HighlightType(
            name="开篇高光",
            description="每部剧第1集开头的默认高光点",
            visual_features={"features": ["开场画面", "快速切入"]},
            audio_features={"features": ["开场音乐", "快速对白"]},
            emotion_features={},
            plot_features={},
            content_features={},
            typical_scenarios=["第1集开头"]
        ))

    # 生成版本号
    old_version = old_skill.version if old_skill else "v0.0"
    new_version = increment_version(old_version)

    # 更新统计信息
    old_stats = old_skill.statistics if old_skill else {}
    new_stats = {
        "project_count": old_stats.get("project_count", 0) + project_count,
        "episode_count": old_stats.get("episode_count", 0) + len(new_results),
        "highlight_type_count": len(all_highlight_types),
        "hook_type_count": len(all_hook_types)
    }

    return SkillFile(
        version=new_version,
        updated_at=datetime.now().isoformat(),
        highlight_types=all_highlight_types,
        hook_types=all_hook_types,
        editing_rules=[],
        statistics=new_stats
    )


def generate_skill_file(skill: SkillFile) -> str:
    """生成技能文件（同时保存MD和JSON两个版本）

    Args:
        skill: 技能文件对象

    Returns:
        生成的Markdown文件路径
    """
    os.makedirs(TrainingConfig.SKILLS_DIR, exist_ok=True)

    version = skill.version

    # ========== 第一部分：生成Markdown文件 ==========
    lines = []
    lines.append("# AI 短剧剪辑技能")
    lines.append(f"> 版本: {skill.version} | 更新日期: {skill.updated_at}")
    lines.append("---")
    lines.append("")

    # 统计信息
    lines.append("## 📊 统计信息")
    lines.append(f"- 训练项目数: {skill.statistics.get('project_count', 0)}")
    lines.append(f"- 累计集数: {skill.statistics.get('episode_count', 0)}")
    lines.append(f"- 高光类型数: {skill.statistics.get('highlight_type_count', 0)}")
    lines.append(f"- 钩子类型数: {skill.statistics.get('hook_type_count', 0)}")
    lines.append("---")
    lines.append("")

    # 高光类型
    lines.append("## 🎯 高光类型")
    for i, ht in enumerate(skill.highlight_types, 1):
        lines.append(f"### {i}. {ht.name}")
        lines.append(f"**描述**: {ht.description}")

        # 视觉特征 - 支持多种格式
        lines.append("**视觉特征**:")
        visual_features = ht.visual_features if isinstance(ht.visual_features, dict) else {}
        feature_list = visual_features.get('features', [])
        if not feature_list:
            for key in ['expressions', 'shots', 'actions', 'scenes', 'props', 'costumes']:
                feature_list.extend(visual_features.get(key, []))
        if feature_list:
            for feature in feature_list:
                lines.append(f"- {feature}")
        else:
            lines.append("- 无")

        # 听觉特征 - 支持多种格式
        lines.append("**听觉特征**:")
        audio_features = ht.audio_features if isinstance(ht.audio_features, dict) else {}
        audio_list = audio_features.get('features', [])
        if not audio_list:
            for key in ['dialogue_type', 'emotion', 'content']:
                val = audio_features.get(key, [])
                if isinstance(val, list):
                    audio_list.extend(val)
                elif val:
                    audio_list.append(str(val))
        if audio_list:
            for feature in audio_list:
                lines.append(f"- {feature}")
        else:
            lines.append("- 无")

        # 典型场景
        lines.append("**典型场景**:")
        if ht.typical_scenarios:
            for scenario in ht.typical_scenarios:
                lines.append(f"- {scenario}")
        else:
            lines.append("- 无")

        lines.append("")

    # 钩子类型
    lines.append("## 🪝 钩子类型")
    for i, ht in enumerate(skill.hook_types, 1):
        lines.append(f"### {i}. {ht.name}")
        lines.append(f"**描述**: {ht.description}")

        # 视觉特征
        lines.append("**视觉特征**:")
        visual_features = ht.visual_features.get('features', []) if isinstance(ht.visual_features, dict) else []
        if visual_features:
            for feature in visual_features:
                lines.append(f"- {feature}")
        else:
            lines.append("- 无")

        # 听觉特征 - 支持多种格式
        lines.append("**听觉特征**:")
        audio_features = ht.audio_features if isinstance(ht.audio_features, dict) else {}
        audio_list = audio_features.get('features', [])
        if not audio_list:
            for key in ['dialogue_type', 'emotion', 'content']:
                val = audio_features.get(key, [])
                if isinstance(val, list):
                    audio_list.extend(val)
                elif val:
                    audio_list.append(str(val))
        if audio_list:
            for feature in audio_list:
                lines.append(f"- {feature}")
        else:
            lines.append("- 无")

        # 典型场景
        lines.append("**典型场景**:")
        if ht.typical_scenarios:
            for scenario in ht.typical_scenarios:
                lines.append(f"- {scenario}")
        else:
            lines.append("- 无")

        lines.append("")

    md_content = '\n'.join(lines)

    # 保存Markdown文件
    md_file_path = TrainingConfig.SKILLS_DIR / f"ai-drama-clipping-thoughts-{version}.md"
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Markdown技能文件已生成: {md_file_path}")

    # ========== 第二部分：生成JSON文件（AI使用） ==========
    json_data = {
        "version": skill.version,
        "metadata": {
            "updated_at": skill.updated_at,
            "statistics": skill.statistics
        },
        "highlight_types": convert_highlight_to_json(skill.highlight_types),
        "hook_types": convert_hook_to_json(skill.hook_types),
        "editing_rules": {
            "min_clip_duration": 30,
            "max_clip_duration": 300,
            "confidence_threshold": 8.0,
            "dedup_interval_seconds": 10,
            "max_same_type_per_episode": 1
        }
    }

    # 保存JSON文件
    json_file_path = TrainingConfig.SKILLS_DIR / f"ai-drama-clipping-thoughts-{version}.json"
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"JSON技能文件已生成: {json_file_path}")

    # 更新 latest 软链接（MD文件）
    latest_link = TrainingConfig.SKILLS_DIR / "ai-drama-clipping-thoughts-latest.md"
    if latest_link.exists():
        latest_link.unlink()
    try:
        latest_link.symlink_to(md_file_path.name)
    except OSError:
        # 如果系统不支持软链接，复制文件
        import shutil
        shutil.copy(md_file_path, latest_link)

    # 更新 latest 软链接（JSON文件）
    latest_json_link = TrainingConfig.SKILLS_DIR / "ai-drama-clipping-thoughts-latest.json"
    if latest_json_link.exists():
        latest_json_link.unlink()
    try:
        latest_json_link.symlink_to(json_file_path.name)
    except OSError:
        import shutil
        shutil.copy(json_file_path, latest_json_link)

    return str(md_file_path)


def convert_highlight_to_json(highlight_types: list) -> list:
    """将高光类型转换为JSON格式

    Args:
        highlight_types: 高光类型列表

    Returns:
        JSON格式的高光类型列表
    """
    result = []
    for ht in highlight_types:
        # 生成英文ID
        type_id = generate_type_id(ht.name)

        # 提取特征
        visual_features = ht.visual_features if isinstance(ht.visual_features, dict) else {}
        audio_features = ht.audio_features if isinstance(ht.audio_features, dict) else {}

        # 构建JSON对象
        json_type = {
            "id": type_id,
            "name": ht.name,
            "description": ht.description,
            "sample_count": 1,  # 暂时设为1，后续可以从统计中获取
            "confidence_avg": 8.0,
            "confidence_min": 7.5,
            "required_features": {
                "emotion_keywords": audio_features.get('emotion', []),
                "emotion_intensity_min": 7.0,
                "dialogue_patterns": audio_features.get('dialogue_type', []),
                "dialogue_keywords": extract_keywords(audio_features),
                "visual_cues": visual_features.get('features', [])[:5],
                "camera": visual_features.get('shots', []),
                "typical_duration": [10, 30]
            },
            "optional_features": {
                "location": visual_features.get('scenes', []),
                "characters": [],
                "action": visual_features.get('actions', [])
            },
            "examples": []
        }

        result.append(json_type)

    return result


def convert_hook_to_json(hook_types: list) -> list:
    """将钩子类型转换为JSON格式

    Args:
        hook_types: 钩子类型列表

    Returns:
        JSON格式的钩子类型列表
    """
    result = []
    for ht in hook_types:
        # 生成英文ID
        type_id = generate_type_id(ht.name)

        # 提取特征
        visual_features = ht.visual_features if isinstance(ht.visual_features, dict) else {}
        audio_features = ht.audio_features if isinstance(ht.audio_features, dict) else {}

        # 构建JSON对象
        json_type = {
            "id": type_id,
            "name": ht.name,
            "description": ht.description,
            "sample_count": 1,
            "confidence_avg": 8.0,
            "confidence_min": 7.0,
            "required_features": {
                "has_twist": True,  # 钩子点默认有反转
                "information_cut_off": True,  # 钩子点默认信息截断
                "emotion_keywords": audio_features.get('emotion', []),
                "dialogue_patterns": audio_features.get('dialogue_type', []),
                "dialogue_keywords": extract_keywords(audio_features),
                "visual_cues": visual_features.get('features', [])[:5]
            },
            "optional_features": {
                "timing": ["中间", "结尾"],
                "camera": visual_features.get('shots', [])
            },
            "examples": []
        }

        result.append(json_type)

    return result


def generate_type_id(name: str) -> str:
    """根据中文名称生成英文ID

    Args:
        name: 中文名称

    Returns:
        英文ID（如：revenge_declaration）
    """
    # 常见类型映射
    mappings = {
        "开篇高光": "opening",
        "重生复仇宣言": "revenge_declaration",
        "替罪赔礼": "apology_sacrifice",
        "男主宠溺": "male_spoiling",
        "信息揭示": "information_reveal",
        "剧情转折": "plot_twist",
        "情感转折": "emotion_turn",
        "悬念反转": "suspense_reversal",
        "悬念迭起": "suspense_buildup",
        "危机预警": "crisis_warning",
        "冲突爆发": "conflict_eruption",
        "情感决裂": "emotional_breakup",
        "突发冲突": "sudden_conflict",
        "矛盾升级": "conflict_escalation",
        "情感爆发": "emotion_outbreak",
        "情感转折": "emotion_transition"
    }

    if name in mappings:
        return mappings[name]

    # 如果没有映射，生成简单的ID
    # 使用hash来生成一致的ID
    import hashlib
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return f"type_{hash_obj.hexdigest()[:8]}"


def extract_keywords(audio_features: dict) -> list:
    """从听觉特征中提取关键词

    Args:
        audio_features: 听觉特征字典

    Returns:
        关键词列表
    """
    keywords = []

    # 从各个字段中提取关键词
    for key in ['dialogue_type', 'emotion', 'content']:
        val = audio_features.get(key, [])
        if isinstance(val, list):
            keywords.extend(val)
        elif isinstance(val, str):
            keywords.append(val)

    return keywords[:10]  # 最多10个


# ========== V5.0 新增：自动类型简化功能 ==========

def simplify_hook_types(hook_types: List[HookType],
                       min_occurrences: int = 3,
                       max_overlap: float = 0.8,
                       max_count: int = 15) -> List[HookType]:
    """自动简化钩子类型

    每次训练时自动调用，完成：
    1. 类型聚类（按关键词相似度）
    2. 相似类型合并
    3. 低质量类型过滤
    4. 数量控制（保留最重要的10-15种）

    Args:
        hook_types: 原始钩子类型列表
        min_occurrences: 最少出现次数（默认3次）
        max_overlap: 最大特征重叠度（默认0.8）
        max_count: 最多保留类型数量（默认15种）

    Returns:
        简化后的钩子类型列表
    """
    if not hook_types:
        return []

    print(f"\n{'=' * 60}")
    print(f"开始自动类型简化")
    print(f"{'=' * 60}")
    print(f"原始类型数: {len(hook_types)}")

    # 步骤1: 按关键词聚类
    print(f"\n[步骤1/4] 按关键词聚类...")
    clusters = _cluster_by_keywords(hook_types)
    print(f"聚类结果: {len(clusters)} 个聚类")

    # 步骤2: 合并相似类型
    print(f"\n[步骤2/4] 合并相似类型...")
    merged_types = []
    for cluster in clusters:
        if len(cluster) > 1:
            # 合并聚类中的类型
            merged = _merge_similar_types(cluster)
            merged_types.append(merged)
            print(f"  合并: {[t.name for t in cluster]} → {merged.name}")
        else:
            merged_types.append(cluster[0])

    print(f"合并后类型数: {len(merged_types)}")

    # 步骤3: 筛选高质量类型
    print(f"\n[步骤3/4] 筛选高质量类型...")
    filtered = _filter_low_quality_types(
        merged_types,
        min_occurrences=min_occurrences,
        max_overlap=max_overlap
    )
    print(f"筛选后类型数: {len(filtered)}")
    print(f"  过滤掉: {len(merged_types) - len(filtered)} 个低质量类型")

    # 步骤4: 限制总数（保留最重要的）
    print(f"\n[步骤4/4] 限制总数（最多{max_count}种）...")
    final = _select_top_types(filtered, max_count=max_count)
    print(f"最终类型数: {len(final)}")

    print(f"\n类型列表:")
    for i, t in enumerate(final, 1):
        print(f"  {i}. {t.name}")

    print(f"{'=' * 60}\n")

    return final


def _cluster_by_keywords(types: List[HookType]) -> List[List[HookType]]:
    """按关键词聚类类型

    Args:
        types: 类型列表

    Returns:
        聚类列表，每个聚类包含相似的类型
    """
    # 定义关键词映射表
    keyword_groups = {
        '反转': ['悬念反转', '剧情反转', '反转钩子', '情节反转', '剧情突变',
                '反转', '突变', '转折'],
        '冲突': ['矛盾冲突', '冲突升级', '对抗', '激烈冲突', '冲突爆发',
                '争执', '对抗升级', '矛盾激化'],
        '危机': ['危机预警', '危机暗示', '危机前兆', '危机爆发', '危险',
                '紧急情况', '突发事件', '危机'],
        '信息揭示': ['信息揭示', '真相揭露', '秘密公开', '信息暴露',
                   '揭示真相', '揭露秘密', '信息披露'],
        '情绪爆发': ['情感爆发', '情绪爆发', '情绪失控', '愤怒',
                   '情绪激动', '情感宣泄', '爆发'],
        '悬念设置': ['悬念设置', '疑问产生', '好奇引发', '疑惑',
                   '悬念', '疑问', '好奇'],
        '情节转折': ['情节转折', '剧情变化', '走向改变', '意外',
                   '转折点', '剧情变化', '变故'],
        '人物变化': ['人物变化', '态度转变', '立场改变', '反转',
                   '态度变化', '立场变化', '人物转变'],
        '期待落空': ['期待落空', '愿望破灭', '失望', '失败',
                   '破灭', '落空', '失望'],
        '情感决裂': ['情感决裂', '关系破裂', '分手', '决裂',
                   '破裂', '分手'],
        '情感觉醒': ['情感觉醒', '意识觉醒', '感悟', '觉察',
                   '醒悟', '领悟', '觉醒'],
        '矛盾激化': ['矛盾激化', '冲突加剧', '激化', '升级',
                   '加剧', '矛盾升级']
    }

    # 为每个类型查找匹配的关键词组
    clustered = {}  # {group_name: [types]}
    unclustered = []

    for hook_type in types:
        name = hook_type.name.lower()
        matched = False

        for group_name, keywords in keyword_groups.items():
            if any(keyword in name for keyword in keywords):
                if group_name not in clustered:
                    clustered[group_name] = []
                clustered[group_name].append(hook_type)
                matched = True
                break

        if not matched:
            unclustered.append(hook_type)

    # 将聚类转换为列表
    result = [list(cluster) for cluster in clustered.values()]

    # 未匹配的类型各自成一组
    for t in unclustered:
        result.append([t])

    return result


def _merge_similar_types(types: List[HookType]) -> HookType:
    """合并相似类型

    Args:
        types: 相似类型列表

    Returns:
        合并后的类型
    """
    if len(types) == 1:
        return types[0]

    # 选择最短的名称作为基准（通常是最简洁的）
    base_type = min(types, key=lambda t: len(t.name))

    # 合并描述（保留最详细的）
    descriptions = [t.description for t in types if t.description]
    merged_description = descriptions[0] if descriptions else base_type.description

    # 合并视觉特征
    all_visual_features = []
    for t in types:
        features = t.visual_features.get('features', []) if isinstance(t.visual_features, dict) else []
        all_visual_features.extend(features)
    merged_visual_features = {'features': list(set(all_visual_features))}

    # 合并听觉特征
    all_audio_features = []
    for t in types:
        if isinstance(t.audio_features, dict):
            for key in ['dialogue_type', 'emotion', 'content']:
                val = t.audio_features.get(key, [])
                if isinstance(val, list):
                    all_audio_features.extend(val)
                elif val:
                    all_audio_features.append(str(val))
    merged_audio_features = {'features': list(set(all_audio_features))}

    # 合并典型场景
    all_scenarios = []
    for t in types:
        if hasattr(t, 'typical_scenarios') and t.typical_scenarios:
            all_scenarios.extend(t.typical_scenarios)
    merged_scenarios = list(set(all_scenarios))

    # 创建合并后的类型
    merged_type = HookType(
        name=base_type.name,  # 使用最简洁的名称
        description=merged_description,
        visual_features=merged_visual_features,
        audio_features=merged_audio_features,
        emotion_features={},
        plot_features={},
        content_features={},
        typical_scenarios=merged_scenarios
    )

    return merged_type


def _filter_low_quality_types(types: List[HookType],
                               min_occurrences: int = 3,
                               max_overlap: float = 0.8) -> List[HookType]:
    """筛选高质量类型

    过滤条件：
    1. 出现次数 >= min_occurrences
    2. 特征重叠度 <= max_overlap

    Args:
        types: 类型列表
        min_occurrences: 最少出现次数
        max_overlap: 最大特征重叠度

    Returns:
        筛选后的类型列表
    """
    filtered = []

    for i, t in enumerate(types):
        # 计算特征重叠度
        max_overlap_with_others = 0

        for j, other in enumerate(types):
            if i == j:
                continue

            overlap = _calculate_feature_overlap(t, other)
            max_overlap_with_others = max(max_overlap_with_others, overlap)

        # 如果重叠度过高，过滤掉
        if max_overlap_with_others > max_overlap:
            continue

        # 保留（暂时不过滤低频类型，因为训练数据有限）
        filtered.append(t)

    return filtered


def _calculate_feature_overlap(type1: HookType, type2: HookType) -> float:
    """计算两个类型的特征重叠度

    Args:
        type1: 类型1
        type2: 类型2

    Returns:
        重叠度（0-1之间）
    """
    # 提取特征
    features1 = set()
    features2 = set()

    if isinstance(type1.visual_features, dict):
        features1.update(type1.visual_features.get('features', []))
    if isinstance(type1.audio_features, dict):
        for key in ['dialogue_type', 'emotion', 'content']:
            val = type1.audio_features.get(key, [])
            if isinstance(val, list):
                features1.update(val)
            elif val:
                features1.add(str(val))

    if isinstance(type2.visual_features, dict):
        features2.update(type2.visual_features.get('features', []))
    if isinstance(type2.audio_features, dict):
        for key in ['dialogue_type', 'emotion', 'content']:
            val = type2.audio_features.get(key, [])
            if isinstance(val, list):
                features2.update(val)
            elif val:
                features2.add(str(val))

    # 计算Jaccard相似度
    if not features1 or not features2:
        return 0.0

    intersection = len(features1 & features2)
    union = len(features1 | features2)

    return intersection / union if union > 0 else 0.0


def _select_top_types(types: List[HookType], max_count: int = 15) -> List[HookType]:
    """选择最重要的类型

    优先级规则：
    1. "开篇高光"永远保留（如果是高光类型）
    2. "悬念反转"优先级最高
    3. 按特征丰富度排序（特征越多越重要）

    Args:
        types: 类型列表
        max_count: 最多保留数量

    Returns:
        选择后的类型列表
    """
    if len(types) <= max_count:
        return types

    # 优先级关键词
    priority_keywords = ['悬念反转', '反转', '冲突', '危机', '信息揭示',
                       '情绪', '转折', '矛盾']

    # 计算每个类型的重要性分数
    scored_types = []
    for t in types:
        score = 0

        # 基础分：特征数量
        visual_count = len(t.visual_features.get('features', [])) if isinstance(t.visual_features, dict) else 0
        audio_features = t.audio_features if isinstance(t.audio_features, dict) else {}
        audio_count = 0
        for key in ['dialogue_type', 'emotion', 'content']:
            val = audio_features.get(key, [])
            audio_count += len(val) if isinstance(val, list) else (1 if val else 0)

        score += visual_count + audio_count

        # 优先级加成
        for keyword in priority_keywords:
            if keyword in t.name:
                score += 5  # 优先级关键词加分
                break

        scored_types.append((t, score))

    # 按分数排序
    scored_types.sort(key=lambda x: x[1], reverse=True)

    # 返回Top N
    return [t for t, score in scored_types[:max_count]]

# ========== V5.1 新增：高光类型自动简化功能 ==========

def simplify_highlight_types(highlight_types: List[HighlightType],
                             min_occurrences: int = 2,
                             max_overlap: float = 0.7,
                             max_count: int = 12) -> List[HighlightType]:
    """自动简化高光类型
    
    每次训练时自动调用，完成：
    1. 类型聚类（按关键词相似度）
    2. 相似类型合并
    3. 低质量类型过滤
    4. 数量控制（保留最重要的10-12种）
    
    Args:
        highlight_types: 原始高光类型列表
        min_occurrences: 最少出现次数（默认2次）
        max_overlap: 最大特征重叠度（默认0.7）
        max_count: 最多保留类型数量（默认12种）
    
    Returns:
        简化后的高光类型列表
    """
    if not highlight_types:
        return []
    
    print(f"\n{'=' * 60}")
    print(f"开始高光类型自动简化")
    print(f"{'=' * 60}")
    print(f"原始高光类型数: {len(highlight_types)}")
    
    # 步骤1: 按关键词聚类
    print(f"\n[步骤1/4] 按关键词聚类...")
    clusters = _cluster_highlight_by_keywords(highlight_types)
    print(f"聚类结果: {len(clusters)} 个聚类")
    
    # 步骤2: 合并相似类型
    print(f"\n[步骤2/4] 合并相似类型...")
    merged_types = []
    for cluster in clusters:
        if len(cluster) > 1:
            # 合并聚类中的类型
            merged = _merge_similar_highlight_types(cluster)
            merged_types.append(merged)
            print(f"  合并: {[t.name for t in cluster]} → {merged.name}")
        else:
            merged_types.append(cluster[0])
    
    print(f"合并后类型数: {len(merged_types)}")
    
    # 步骤3: 筛选高质量类型
    print(f"\n[步骤3/4] 筛选高质量类型...")
    filtered = _filter_low_quality_highlight_types(
        merged_types,
        min_occurrences=min_occurrences,
        max_overlap=max_overlap
    )
    print(f"筛选后类型数: {len(filtered)}")
    print(f"  过滤掉: {len(merged_types) - len(filtered)} 个低质量类型")
    
    # 步骤4: 限制总数（保留最重要的）
    print(f"\n[步骤4/4] 限制总数（最多{max_count}种）...")
    final = _select_top_highlight_types(filtered, max_count=max_count)
    print(f"最终类型数: {len(final)}")
    
    print(f"\n高光类型列表:")
    for i, t in enumerate(final, 1):
        print(f"  {i}. {t.name}")
    
    print(f"{'=' * 60}\n")
    
    return final


def _cluster_highlight_by_keywords(types: List[HighlightType]) -> List[List[HighlightType]]:
    """按关键词聚类高光类型
    
    Args:
        types: 高光类型列表
    
    Returns:
        聚类列表，每个聚类包含相似的类型
    """
    # 高光类型专用关键词映射表
    keyword_groups = {
        '开篇': ['开篇', '开场', '序幕', '开始', '引入'],
        '反转': ['反转', '转折', '突变', '变化', '反转叙事'],
        '揭示': ['揭示', '揭露', '揭秘', '曝光', '公开', '信息揭示', '真相揭露'],
        '冲突': ['冲突', '矛盾', '爆发', '对抗', '争执', '冲突爆发', '矛盾冲突', '冲突揭露'],
        '情感': ['情感', '情绪', '爆发', '感动', '激化', '情感爆发', '情感转折'],
        '身世': ['身世', '身份', '背景', '来历', '身世揭秘'],
        '婚礼': ['婚礼', '车祸', '死亡', '婚礼车祸'],
        '职场': ['职场', '工作', '公司', '上司', '职场心机'],
        '重生': ['重生', '复活', '归来', '立威', '重生+立威'],
        '悲惨': ['悲惨', '苦难', '困境', '遭遇', '悲惨遭遇', '苦难叙事'],
        '信息': ['信息', '抛出', '交代', '说明', '信息抛出'],
        '关系': ['关系', '人物关系', '情感关系'],
        '尴尬': ['误会', '尴尬', '误会/尴尬'],
        '救援': ['救援', '紧急', '紧急救援'],
        '心机': ['心机', '职场心机']
    }
    
    # 为每个类型查找匹配的关键词组
    clustered = {}  # {group_name: [types]}
    unclustered = []
    
    for highlight_type in types:
        name = highlight_type.name.lower()
        matched = False
        
        for group_name, keywords in keyword_groups.items():
            if any(keyword in name for keyword in keywords):
                if group_name not in clustered:
                    clustered[group_name] = []
                clustered[group_name].append(highlight_type)
                matched = True
                break
        
        if not matched:
            unclustered.append(highlight_type)
    
    # 将聚类转换为列表
    result = [list(cluster) for cluster in clustered.values()]
    
    # 未匹配的类型各自成一组
    for t in unclustered:
        result.append([t])
    
    return result


def _merge_similar_highlight_types(types: List[HighlightType]) -> HighlightType:
    """合并相似的高光类型
    
    Args:
        types: 相似高光类型列表
    
    Returns:
        合并后的高光类型
    """
    if len(types) == 1:
        return types[0]
    
    # 选择最短的名称作为基准（通常是最简洁的）
    base_type = min(types, key=lambda t: len(t.name))
    
    # 合并描述（保留最详细的）
    descriptions = [t.description for t in types if t.description]
    merged_description = descriptions[0] if descriptions else base_type.description
    
    # 合并视觉特征
    all_visual_features = []
    for t in types:
        features = t.visual_features.get('features', []) if isinstance(t.visual_features, dict) else []
        all_visual_features.extend(features)
    merged_visual_features = {'features': list(set(all_visual_features))}
    
    # 合并听觉特征
    all_audio_features = []
    for t in types:
        if isinstance(t.audio_features, dict):
            for key in ['dialogue_type', 'emotion', 'content']:
                val = t.audio_features.get(key, [])
                if isinstance(val, list):
                    all_audio_features.extend(val)
                elif val:
                    all_audio_features.append(str(val))
    merged_audio_features = {'features': list(set(all_audio_features))}
    
    # 合并典型场景
    all_scenarios = []
    for t in types:
        if hasattr(t, 'typical_scenarios') and t.typical_scenarios:
            all_scenarios.extend(t.typical_scenarios)
    merged_scenarios = list(set(all_scenarios))
    
    # 创建合并后的类型
    merged_type = HighlightType(
        name=base_type.name,  # 使用最简洁的名称
        description=merged_description,
        visual_features=merged_visual_features,
        audio_features=merged_audio_features,
        emotion_features={},
        plot_features={},
        content_features={},
        typical_scenarios=merged_scenarios
    )
    
    return merged_type


def _filter_low_quality_highlight_types(types: List[HighlightType],
                                          min_occurrences: int = 2,
                                          max_overlap: float = 0.7) -> List[HighlightType]:
    """筛选高质量的高光类型
    
    过滤条件：
    1. 出现次数 >= min_occurrences
    2. 特征重叠度 <= max_overlap
    
    Args:
        types: 高光类型列表
        min_occurrences: 最少出现次数
        max_overlap: 最大特征重叠度
    
    Returns:
        筛选后的高光类型列表
    """
    filtered = []
    
    for i, t in enumerate(types):
        # 计算特征重叠度
        max_overlap_with_others = 0
        
        for j, other in enumerate(types):
            if i == j:
                continue
            
            overlap = _calculate_highlight_feature_overlap(t, other)
            max_overlap_with_others = max(max_overlap_with_others, overlap)
        
        # 如果重叠度过高，过滤掉
        if max_overlap_with_others > max_overlap:
            continue
        
        # 保留（暂时不过滤低频类型，因为训练数据有限）
        filtered.append(t)
    
    return filtered


def _calculate_highlight_feature_overlap(type1: HighlightType, type2: HighlightType) -> float:
    """计算两个高光类型的特征重叠度
    
    Args:
        type1: 高光类型1
        type2: 高光类型2
    
    Returns:
        重叠度（0-1之间）
    """
    # 提取特征
    features1 = set()
    features2 = set()
    
    if isinstance(type1.visual_features, dict):
        features1.update(type1.visual_features.get('features', []))
    if isinstance(type1.audio_features, dict):
        for key in ['dialogue_type', 'emotion', 'content']:
            val = type1.audio_features.get(key, [])
            if isinstance(val, list):
                features1.update(val)
            elif val:
                features1.add(str(val))
    
    if isinstance(type2.visual_features, dict):
        features2.update(type2.visual_features.get('features', []))
    if isinstance(type2.audio_features, dict):
        for key in ['dialogue_type', 'emotion', 'content']:
            val = type2.audio_features.get(key, [])
            if isinstance(val, list):
                features2.update(val)
            elif val:
                features2.add(str(val))
    
    # 计算Jaccard相似度
    if not features1 or not features2:
        return 0.0
    
    intersection = len(features1 & features2)
    union = len(features1 | features2)
    
    return intersection / union if union > 0 else 0.0


def _select_top_highlight_types(types: List[HighlightType], max_count: int = 12) -> List[HighlightType]:
    """选择最重要的的高光类型
    
    优先级规则：
    1. "开篇高光"永远保留
    2. "剧情反转"优先级最高
    3. 按特征丰富度排序（特征越多越重要）
    
    Args:
        types: 高光类型列表
        max_count: 最多保留数量
    
    Returns:
        选择后的高光类型列表
    """
    if len(types) <= max_count:
        return types
    
    # 优先级关键词（高光类型专用）
    priority_keywords = ['开篇', '反转', '揭示', '冲突', '情感', '身世',
                       '转折', '爆发', '剧情', '真相']
    
    # 计算每个类型的重要性分数
    scored_types = []
    for t in types:
        score = 0
        
        # 基础分：特征数量
        visual_count = len(t.visual_features.get('features', [])) if isinstance(t.visual_features, dict) else 0
        audio_features = t.audio_features if isinstance(t.audio_features, dict) else {}
        audio_count = 0
        for key in ['dialogue_type', 'emotion', 'content']:
            val = audio_features.get(key, [])
            audio_count += len(val) if isinstance(val, list) else (1 if val else 0)
        
        score += visual_count + audio_count
        
        # 优先级加成
        for keyword in priority_keywords:
            if keyword in t.name:
                score += 5  # 优先级关键词加分
                break
        
        scored_types.append((t, score))
    
    # 按分数排序
    scored_types.sort(key=lambda x: x[1], reverse=True)
    
    # 返回Top N
    return [t for t, score in scored_types[:max_count]]

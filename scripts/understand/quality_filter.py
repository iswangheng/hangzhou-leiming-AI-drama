"""
质量筛选模块 - 对AI识别结果进行多维度筛选
"""
from typing import List, Tuple
from collections import defaultdict

from .analyze_segment import SegmentAnalysis


def filter_by_confidence(analyses: List[SegmentAnalysis],
                         min_confidence: float = 6.5) -> List[SegmentAnalysis]:
    """根据置信度筛选标记

    只保留置信度 > min_confidence 的标记

    Args:
        analyses: 所有分析结果
        min_confidence: 最低置信度阈值（V5默认6.5，适度放宽）

    Returns:
        筛选后的分析结果
    """
    filtered = []

    for analysis in analyses:
        # 高光点筛选
        if analysis.is_highlight:
            if analysis.highlight_confidence >= min_confidence:
                filtered.append(analysis)
            else:
                print(f"  [过滤] 第{analysis.episode}集 {analysis.highlight_timestamp}秒 "
                      f"高光点置信度{analysis.highlight_confidence:.1f} < {min_confidence}")

        # 钩子点筛选
        elif analysis.is_hook:
            if analysis.hook_confidence >= min_confidence:
                filtered.append(analysis)
            else:
                print(f"  [过滤] 第{analysis.episode}集 {analysis.hook_timestamp}秒 "
                      f"钩子点置信度{analysis.hook_confidence:.1f} < {min_confidence}")

    print(f"\n置信度筛选({min_confidence}): {len(analyses)} → {len(filtered)}")

    return filtered


def deduplicate_analyses(analyses: List[SegmentAnalysis],
                        min_distance: int = 10) -> List[SegmentAnalysis]:
    """去重：同一集内，同一类型的标记，min_distance秒内只保留置信度最高的

    Args:
        analyses: 所有分析结果
        min_distance: 最小时间间隔（秒，默认10秒，缩短以捕获更密集的标记点）

    Returns:
        去重后的分析结果
    """
    # 按集数分组
    episodes = defaultdict(lambda: {'highlights': [], 'hooks': []})

    for analysis in analyses:
        ep = analysis.episode
        if analysis.is_highlight:
            episodes[ep]['highlights'].append(analysis)
        elif analysis.is_hook:
            episodes[ep]['hooks'].append(analysis)

    def deduplicate_group(group: List[SegmentAnalysis], is_highlight: bool) -> List[SegmentAnalysis]:
        """对一组标记进行去重"""
        if not group:
            return []

        # 按置信度排序（降序）
        confidence_key = lambda x: x.highlight_confidence if is_highlight else x.hook_confidence
        sorted_group = sorted(group, key=confidence_key, reverse=True)

        kept = []
        removed_count = 0

        for item in sorted_group:
            timestamp = item.highlight_timestamp if is_highlight else item.hook_timestamp

            # 检查是否与已保留的标记太近
            too_close = False
            for kept_item in kept:
                kept_timestamp = kept_item.highlight_timestamp if is_highlight else kept_item.hook_timestamp
                conf = kept_item.highlight_confidence if is_highlight else kept_item.hook_confidence

                if abs(timestamp - kept_timestamp) < min_distance:
                    too_close = True
                    item_conf = item.highlight_confidence if is_highlight else item.hook_confidence
                    print(f"  [去重] 第{item.episode}集 {timestamp}秒 "
                          f"(置信度{item_conf:.1f}) 与 "
                          f"第{kept_item.episode}集 {kept_timestamp}秒 "
                          f"(置信度{conf:.1f}) 过近，移除")
                    break

            if not too_close:
                kept.append(item)
            else:
                removed_count += 1

        return kept

    result = []
    total_removed = 0

    for ep, groups in sorted(episodes.items()):
        highlights = deduplicate_group(groups['highlights'], True)
        hooks = deduplicate_group(groups['hooks'], False)

        removed = len(groups['highlights']) + len(groups['hooks']) - (len(highlights) + len(hooks))
        if removed > 0:
            print(f"第{ep}集: {len(groups['highlights'])}高光+{len(groups['hooks'])}钩子 → "
                  f"{len(highlights)}高光+{len(hooks)}钩子 (移除{removed}个)")

        result.extend(highlights + hooks)
        total_removed += removed

    print(f"总体去重({min_distance}秒): 移除{total_removed}个标记")

    return result


def limit_by_top_n(analyses: List[SegmentAnalysis],
                  episode_durations: dict,
                  highlights_per_min: int = 1,
                  hooks_per_min: int = 6) -> List[SegmentAnalysis]:
    """每集按时长比例动态分配数量限制

    根据每集的时长,动态计算该集允许的高光点和钩子点数量:
    - 每1分钟(60秒)允许1个高光点
    - 每1分钟(60秒)允许6个钩子点

    Args:
        analyses: 所有分析结果
        episode_durations: 每集时长字典 {集数: 秒数}
        highlights_per_min: 每分钟允许的高光点数(默认1个)
        hooks_per_min: 每分钟允许的钩子点数(默认6个)

    Returns:
        限制数量后的分析结果
    """
    # 按集数分组
    episodes = defaultdict(lambda: {'highlights': [], 'hooks': []})

    for analysis in analyses:
        ep = analysis.episode
        if analysis.is_highlight:
            episodes[ep]['highlights'].append(analysis)
        elif analysis.is_hook:
            episodes[ep]['hooks'].append(analysis)

    # 每集按时长比例动态分配数量
    result = []
    total_removed = 0

    for ep, groups in sorted(episodes.items()):
        # 获取该集的时长
        ep_duration = episode_durations.get(ep, 180)  # 默认3分钟

        # 动态计算该集允许的数量
        ep_minutes = ep_duration / 60
        max_highlights = max(1, int(ep_minutes) * highlights_per_min)  # 每分钟1个高光点
        max_hooks = max(1, int(ep_minutes) * hooks_per_min)  # 每分钟6个钩子点

        # 高光点排序
        highlights = sorted(groups['highlights'],
                           key=lambda x: x.highlight_confidence,
                           reverse=True)

        hooks = sorted(groups['hooks'],
                      key=lambda x: x.hook_confidence,
                      reverse=True)

        original_count = len(highlights) + len(hooks)

        # 限制数量(使用动态计算的上限)
        kept_highlights = highlights[:max_highlights]
        kept_hooks = hooks[:max_hooks]

        removed = original_count - (len(kept_highlights) + len(kept_hooks))
        if removed > 0:
            print(f"  [限制] 第{ep}集({ep_duration}秒={ep_minutes:.1f}分钟): {len(highlights)}高光→{len(kept_highlights)}个, "
                  f"{len(hooks)}钩子→{len(kept_hooks)}个 (移除{removed}个)")

        result.extend(kept_highlights + kept_hooks)
        total_removed += removed

    print(f"\n动态数量限制(每分钟{highlights_per_min}高光+{hooks_per_min}钩子): 移除{total_removed}个标记")

    return result


def limit_type_diversity(analyses: List[SegmentAnalysis],
                        max_same_type_per_episode: int = 1) -> List[SegmentAnalysis]:
    """类型多样性限制：每集同类型的标记不超过max_same_type_per_episode个

    Args:
        analyses: 所有分析结果
        max_same_type_per_episode: 每集同类型标记的最大数量

    Returns:
        应用类型多样性限制后的结果
    """
    # 按集数和类型分组
    episodes = defaultdict(lambda: defaultdict(list))

    for analysis in analyses:
        ep = analysis.episode
        if analysis.is_highlight:
            episodes[ep]['highlights'].append(analysis)
        elif analysis.is_hook:
            episodes[ep]['hooks'].append(analysis)

    result = []
    total_removed = 0

    for ep, groups in sorted(episodes.items()):
        # 处理高光点
        highlights_by_type = defaultdict(list)
        for hl in groups['highlights']:
            highlights_by_type[hl.highlight_type].append(hl)

        for hl_type, hls in highlights_by_type.items():
            if len(hls) > max_same_type_per_episode:
                # 按置信度排序，只保留最高的N个
                hls_sorted = sorted(hls, key=lambda x: x.highlight_confidence, reverse=True)
                kept = hls_sorted[:max_same_type_per_episode]
                removed = hls_sorted[max_same_type_per_episode:]

                print(f"  [类型限制] 第{ep}集高光点'{hl_type}': {len(hls)}个→{len(kept)}个")
                result.extend(kept)
                total_removed += len(removed)
            else:
                result.extend(hls)

        # 处理钩子点
        hooks_by_type = defaultdict(list)
        for hook in groups['hooks']:
            hooks_by_type[hook.hook_type].append(hook)

        for hook_type, hooks in hooks_by_type.items():
            if len(hooks) > max_same_type_per_episode:
                # 按置信度排序，只保留最高的N个
                hooks_sorted = sorted(hooks, key=lambda x: x.hook_confidence, reverse=True)
                kept = hooks_sorted[:max_same_type_per_episode]
                removed = hooks_sorted[max_same_type_per_episode:]

                print(f"  [类型限制] 第{ep}集钩子点'{hook_type}': {len(hooks)}个→{len(kept)}个")
                result.extend(kept)
                total_removed += len(removed)
            else:
                result.extend(hooks)

    if total_removed > 0:
        print(f"\n类型多样性限制(每集同类型最多{max_same_type_per_episode}个): "
              f"移除{total_removed}个标记")
    else:
        print(f"\n类型多样性限制: 无需移除（每集同类型都不超过{max_same_type_per_episode}个）")

    return result


def add_opening_highlight(analyses: List[SegmentAnalysis],
                         episode_durations: dict) -> List[SegmentAnalysis]:
    """为第1集添加开篇高光点

    规则：第1集的0-30秒范围，自动识别为"开篇高光点"

    Args:
        analyses: 所有分析结果
        episode_durations: 每集的时长

    Returns:
        添加了开篇高光点后的结果
    """
    # 检查第1集是否已有开篇高光点
    episode_1_has_opening = False
    for analysis in analyses:
        if analysis.episode == 1 and analysis.is_highlight:
            if 0 <= analysis.highlight_timestamp <= 30:
                episode_1_has_opening = True
                break

    if episode_1_has_opening:
        print("第1集已有开篇高光点，无需添加")
        return analyses

    # 添加第1集开篇高光点
    opening_highlight = SegmentAnalysis(
        episode=1,
        start_time=0,
        end_time=30,
        is_highlight=True,
        highlight_timestamp=0,
        highlight_type="开篇高光",
        highlight_desc="每部剧第1集开头的默认高光点",
        highlight_confidence=10.0,
        is_hook=False,
        hook_timestamp=0,
        hook_type=None,
        hook_desc="",
        hook_confidence=0.0
    )

    result = [opening_highlight] + analyses
    print(f"已添加第1集开篇高光点(0秒)")

    return result


def apply_quality_pipeline(analyses: List[SegmentAnalysis],
                          episode_durations: dict,
                          min_confidence: float = 7.0,
                          min_distance: int = 10,
                          max_same_type_per_episode: int = 1) -> List[SegmentAnalysis]:
    """应用完整的质量筛选流程

    Args:
        analyses: AI分析结果
        episode_durations: 每集时长
        min_confidence: 置信度阈值（默认7.0）
        min_distance: 去重间隔（默认10秒）
        max_same_type_per_episode: 每集同类型标记的最大数量（默认1）

    Returns:
        筛选后的高质量结果
    """
    print("=" * 80)
    print("开始质量筛选流程")
    print("=" * 80)

    original_count = len(analyses)

    # 步骤1: 置信度筛选
    print("\n[步骤1/5] 置信度筛选")
    analyses = filter_by_confidence(analyses, min_confidence)

    # 步骤2: 去重
    print("\n[步骤2/5] 去重")
    analyses = deduplicate_analyses(analyses, min_distance)

    # 步骤3: 类型多样性限制
    print("\n[步骤3/5] 类型多样性限制")
    analyses = limit_type_diversity(analyses, max_same_type_per_episode)

    # 步骤4: 动态数量限制(按时长比例)
    print("\n[步骤4/5] 动态数量限制(按时长比例)")
    analyses = limit_by_top_n(analyses, episode_durations)

    # 步骤5: 添加第1集开篇高光点
    print("\n[步骤5/5] 添加第1集开篇高光点")
    analyses = add_opening_highlight(analyses, episode_durations)

    final_count = len(analyses)

    print("\n" + "=" * 80)
    # V13.1: 修复除以0错误
    if original_count > 0:
        print(f"质量筛选完成: {original_count} → {final_count} "
              f"(保留率: {final_count/original_count*100:.1f}%)")
    else:
        print(f"质量筛选完成: {original_count} → {final_count} "
              f"(无原始数据)")
    print("=" * 80)

    return analyses

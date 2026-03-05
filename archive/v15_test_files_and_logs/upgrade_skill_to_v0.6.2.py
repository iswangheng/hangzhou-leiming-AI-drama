#!/usr/bin/env python3
"""
升级技能文件从v0.6到v0.6.2
修正BGM处理逻辑，增加纯画面型钩子识别，调整钩子点判断权重

v0.6.2核心修正：
1. BGM从辅助信号提升为10%独立权重
2. 增加"纯画面型"钩子识别（10%人工剪辑使用）
3. 调整钩子点判断权重：视觉40% + 情节30% + 情绪20% + BGM10%
"""
import json
from datetime import datetime

def upgrade_skill_to_v062():
    """升级技能文件到v0.6.2版本"""

    # 读取v0.6
    with open('data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.6.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 更新版本号
    data['version'] = 'v0.6.2'
    data['metadata']['updated_at'] = datetime.now().isoformat()
    data['metadata']['statistics'] = {
        "project_count": 14 + 13,
        "episode_count": 117,
        "highlight_type_count": 12,
        "hook_type_count": 16,  # +1 纯画面型
        "manual_clipping_analysis": 13
    }

    # 更新核心原则
    data['principles']['hook_principles']['real_hook_methods'] = [
        "时间节点（明确未来时间 + 未完成事件）",
        "未完成事件（指出未完成的冲突，想知道结果）",
        "对话留白（只给开头，想知道后续）",
        "悬念结束时刻（关键行动或事件的高潮时刻画面停住）",
        "情节重大转折（反转、突变、意外、命运改变）",
        "纯画面型（无字幕，人物动作定格 + 情绪未释放 + BGM戛然而止）"  # v0.6.2新增
    ]

    # v0.6.2新增：钩子点判断权重
    data['principles']['hook_judgment_weights'] = {
        "visual_elements": "40%",
        "plot_incomplete": "30%",
        "emotion_unreleased": "20%",  # v0.6.2从10%提升
        "bgm_cooperation": "10%"  # v0.6.2从辅助提升为独立权重
    }

    # v0.6.2新增：BGM信号处理逻辑
    data['bgm_signals'] = {
        "weight": "10%",  # v0.6.2：从辅助提升为独立权重
        "description": "BGM戛然而止/静音是重要钩子信号，基于人工剪辑分析",
        "strong_hook_signals": {
            "bgm_abrupt_stop_plus_action_freeze": {
                "description": "BGM戛然而止 + 人物动作定格/维持",
                "example": "通话中人物 + BGM戛然而止",
                "confidence_boost": "+1.5"
            },
            "bgm_silence_plus_prop_closeup": {
                "description": "BGM静音 + 关键道具特写/表情定格",
                "example": "诊断报告特写 + BGM静音",
                "confidence_boost": "+1.5"
            },
            "bgm_silence_plus_time_subtitle": {
                "description": "BGM静音 + 时间节点字幕",
                "example": "'婚礼三天后' + BGM静音",
                "confidence_boost": "+1.5"
            },
            "bgm_silence_plus_unfinished_subtitle": {
                "description": "BGM静音 + 未完成事件字幕",
                "example": "'还没给' + BGM静音",
                "confidence_boost": "+1.5"
            }
        },
        "medium_hook_signals": {
            "bgm_abrupt_stop_plus_plot_hint": {
                "description": "BGM戛然而止 + 有情节暗示",
                "example": "追逐场景 + BGM戛然而止",
                "confidence_boost": "+1.0"
            }
        },
        "weak_hook_signals": {
            "bgm_silence_only": {
                "description": "只有BGM静音/戛然而止，无明显视觉特征",
                "judgment": "需要结合人物动作、表情、场景",
                "if_action_freeze": "可能是钩子点（置信度 +0.5至+1.0）",
                "if_plain_scene": "可能不是钩子点（置信度 -0.5）"
            }
        },
        "not_hook_signals": {
            "bgm_normal_plus_conversation_end": {
                "description": "BGM维持正常 + 对话自然结束",
                "confidence": "-1.0"
            },
            "scene_switch_plus_bgm_silence": {
                "description": "场景切换导致的停顿 + BGM静音",
                "confidence": "-1.0"
            }
        }
    }

    # 添加"纯画面型"钩子类型
    pure_visual_hook = {
        "id": "pure_visual_hook",
        "name": "纯画面型钩子",
        "description": "无字幕，完全依靠人物动作定格、情绪未释放和BGM戛然而止/静音制造悬念",
        "importance": "10%的人工剪辑钩子点",
        "visual_composition": {
            "shot_size": "特写/中近景",
            "depth_of_field": "背景虚化，突出人物",
            "description": "展示人物动作定格或微妙表情"
        },
        "text_elements": {
            "has_text": False,
            "description": "无字幕或只有剧名"
        },
        "emotion_signals": {
            "emotion_unreleased": "紧张、期待未得到缓解",
            "suspense_unresolved": "悬念未解开，想知道后续"
        },
        "bgm_signals": {
            "bgm_pattern": "戛然而止或静音",
            "hook_signal_strength": "+1.5",
            "description": "BGM戛然而止/静音是关键钩子信号"
        },
        "examples": [
            "人物手指即将按下按钮 + BGM静音",
            "门即将打开 + BGM戛然而止",
            "人物表情定格（震惊/疑惑） + BGM静音",
            "通话中人物定格 + BGM戛然而止"
        ],
        "judgment_criteria": {
            "positive": [
                "有人物动作定格/微妙表情 + BGM戛然而止 → 钩子点",
                "有情节暗示（危险/悬念） + BGM静音 → 钩子点"
            ],
            "negative": [
                "平淡场景 + 只有BGM静音 → 不是钩子点"
            ]
        },
        "typical_scenes": [
            "危险即将发生的时刻",
            "关键决定前的瞬间",
            "真相即将揭露的时刻",
            "重要行动的开始"
        ]
    }

    # 添加到钩子类型列表
    data['hook_types'].append(pure_visual_hook)

    # 为每个钩子类型添加BGM信号特征（如果还没有）
    for hook in data['hook_types']:
        if 'bgm_signals' not in hook:
            hook['bgm_signals'] = {}

        # 根据类型添加BGM模式
        if hook['id'] in ['emotional_conflict', 'family_ethics_conflict', 'conflict_with_threat']:
            hook['bgm_signals'] = {
                "bgm_pattern": "戛然而止或静音",
                "hook_signal_strength": "+0.8至+1.0",
                "description": "情绪冲突钩子"
            }
        elif hook['id'] in ['emotional_impact', 'truth_reveal', 'revenge_slap']:
            hook['bgm_signals'] = {
                "bgm_pattern": "戛然而止",
                "hook_signal_strength": "+1.0至+1.5",
                "description": "强烈情绪冲击"
            }
        elif hook['id'] == 'sudden_crisis':
            hook['bgm_signals'] = {
                "bgm_pattern": "静音",
                "hook_signal_strength": "+1.5",
                "description": "危险时刻"
            }
        elif hook['id'] == 'narrative_reversal':
            hook['bgm_signals'] = {
                "bgm_pattern": "高潮后骤降",
                "hook_signal_strength": "+0.5",
                "description": "情节转折"
            }

    # 保存v0.6.2
    output_path = 'data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.6.2.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ v0.6.2技能文件已创建: {output_path}")
    print(f"   - 版本号: {data['version']}")
    print(f"   - 高光类型: {len(data['highlight_types'])}")
    print(f"   - 钩子类型: {len(data['hook_types'])}（+1纯画面型）")
    print(f"   - 新增字段: bgm_signals, hook_judgment_weights")

    return output_path

if __name__ == '__main__':
    upgrade_skill_to_v062()

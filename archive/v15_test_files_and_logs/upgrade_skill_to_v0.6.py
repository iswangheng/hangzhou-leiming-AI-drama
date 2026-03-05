#!/usr/bin/env python3
"""
升级技能文件从v0.5到v0.6
添加视觉构图、文字元素、BGM分析等新特征
"""
import json
from datetime import datetime

def upgrade_skill_to_v06():
    """升级技能文件到v0.6版本"""

    # 读取v0.5
    with open('data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.5.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 更新版本号
    data['version'] = 'v0.6'
    data['metadata']['updated_at'] = datetime.now().isoformat()
    data['metadata']['statistics'] = {
        "project_count": 14 + 13,  # 原有14 + 人工剪辑分析13
        "episode_count": 117,
        "highlight_type_count": 12,
        "hook_type_count": 15,
        "manual_clipping_analysis": 13  # 新增：人工剪辑分析视频数
    }

    # 添加v0.6新增的核心原则
    data['principles'] = {
        "highlight_principles": {
            "three_second_rule": "3秒内必须抓住观众注意力",
            "visual_formula": "情绪人物(30%) + 关键道具/场景(30%) + 悬念文字(40%)",
            "weight_distribution": "视觉70% + 台词30%"
        },
        "hook_principles": {
            "real_hook_methods": [
                "剧情悬念（未完成情节、时间节点）",
                "对话留白（只给开头、想知道后续）",
                "情绪未释放（紧张、期待未缓解）",
                "类型标签（'热门短剧'暗示续集）",
                "剧名钩子（剧名本身的吸引力）"
            ],
            "false_detection_removed": "识别'查看更多视频'按钮（实际不存在）"
        }
    }

    # 为每个类型添加v0.6新增的特征字段
    visual_composition_features = {
        "camera_angle": ["俯拍", "仰拍", "平视", "主观视角"],
        "shot_size": ["远景", "中景", "近景", "特写"],
        "depth_of_field": ["浅景深", "全景清晰"],
        "composition_position": ["画面中心", "黄金分割点", "背景虚化"],
        "color_tone": ["暖色调", "冷色调", "对比色"]
    }

    text_element_features = {
        "text_position": ["画面中央", "画面底部", "流动字幕", "人物胸部"],
        "text_type": ["预警性", "疑问性", "时间节点", "未完成事件", "标题性"]
    }

    bgm_features = {
        "bgm_pattern": ["静音", "戛然而止", "高潮后骤降", "维持正常"],
        "hook_signal_strength": {
            "静音": "+2.0",
            "戛然而止": "+1.5",
            "高潮后骤降": "+1.0",
            "维持正常": "-1.5"
        }
    }

    # 更新每个高光类型
    for highlight in data['highlight_types']:
        # 添加v0.6新增字段
        if 'visual_composition' not in highlight:
            highlight['visual_composition'] = {}

        # 根据类型添加视觉构图特征
        if highlight['id'] in ['plot_reversal', 'information_reveal', 'conflict_eruption']:
            highlight['visual_composition']['camera_angle'] = ["俯拍", "特写"]
            highlight['visual_composition']['shot_size'] = ["特写", "近景"]
            highlight['visual_composition']['depth_of_field'] = ["浅景深"]
        elif highlight['id'] == 'opening':
            highlight['visual_composition']['camera_angle'] = ["主观视角"]
            highlight['visual_composition']['shot_size'] = ["特写"]
            highlight['visual_composition']['color_tone'] = ["对比色"]

        # 添加文字元素（如果有）
        if 'text_elements' not in highlight:
            highlight['text_elements'] = {
                "has_text": False,
                "text_positions": [],
                "text_types": []
            }

    # 更新每个钩子类型
    for hook in data['hook_types']:
        # 添加v0.6新增字段
        if 'visual_composition' not in hook:
            hook['visual_composition'] = {}
        if 'text_elements' not in hook:
            hook['text_elements'] = {}
        if 'bgm_signals' not in hook:
            hook['bgm_signals'] = {}

        # 根据类型添加字幕类型（v0.6核心发现）
        if hook['id'] in ['emotional_conflict', 'family_ethics_conflict', 'conflict_with_threat']:
            hook['text_elements'] = {
                "text_position": "人物胸部",
                "text_type": "未完成事件",
                "description": "指出未完成的冲突"
            }
            hook['visual_composition'] = {
                "shot_size": "中近景",
                "depth_of_field": "背景虚化",
                "description": "展示人物状态"
            }

        elif hook['id'] == 'workplace_conflict_warning':
            hook['text_elements'] = {
                "text_position": "画面中央",
                "text_type": "预警性",
                "description": "危险/冲突前奏"
            }

        elif hook['id'] in ['emotional_impact', 'truth_reveal', 'revenge_slap']:
            hook['visual_composition'] = {
                "shot_size": "特写",
                "depth_of_field": "浅景深",
                "description": "强调表情和情绪"
            }
            hook['bgm_signals'] = {
                "bgm_pattern": "戛然而止",
                "hook_signal_strength": "+1.5"
            }

        elif hook['id'] == 'narrative_reversal':
            hook['visual_composition'] = {
                "color_tone": "对比色调",
                "description": "前后对比"
            }

        elif hook['id'] == 'sudden_crisis':
            hook['visual_composition'] = {
                "shot_size": "特写",
                "description": "危险瞬间"
            }
            hook['bgm_signals'] = {
                "bgm_pattern": "静音",
                "hook_signal_strength": "+2.0"
            }

    # 添加题材适配规则
    data['genre_adaptation'] = {
        "modern_genre": {
            "name": "现代题材",
            "visual_features": {
                "scenes": ["室内", "办公室", "医院", "都市街道"],
                "props": ["文件", "手机", "戒指", "诊断报告", "合同"],
                "color_tone": "暖色调",
                "description": "生活化、现实感"
            },
            "hook_types": ["时间节点", "情感纠葛", "现实冲突"],
            "camera_patterns": ["俯拍", "浅景深"],
            "text_patterns": {
                "预警性文字": "少",
                "时间节点文字": "多"
            }
        },
        "xianxia_genre": {
            "name": "仙侠题材",
            "visual_features": {
                "scenes": ["夜晚", "古宅", "秘境", "自然风光"],
                "props": ["法宝", "武器", "古籍", "符咒"],
                "color_tone": "冷暖对比",
                "description": "神秘感、奇幻感"
            },
            "hook_types": ["未完成事件", "危险预警", "法术对抗"],
            "camera_patterns": ["仰拍", "全景"],
            "text_patterns": {
                "预警性文字": "多（如'小心'）",
                "时间节点文字": "少"
            }
        },
        "rebirth_genre": {
            "name": "重生题材",
            "visual_features": {
                "scenes": ["现代场景为主"],
                "props": ["时间相关物品（日历、钟表）"],
                "color_tone": "对比色调",
                "description": "前后对比"
            },
            "hook_types": ["时间重启", "预知优势", "命运改变"],
            "camera_patterns": ["对比剪辑"],
            "text_patterns": {
                "时间节点文字": "多"
            }
        }
    }

    # 保存v0.6
    output_path = 'data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.6.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ v0.6技能文件已创建: {output_path}")
    print(f"   - 版本号: {data['version']}")
    print(f"   - 高光类型: {len(data['highlight_types'])}")
    print(f"   - 钩子类型: {len(data['hook_types'])}")
    print(f"   - 新增字段: visual_composition, text_elements, bgm_signals, genre_adaptation")

    return output_path

if __name__ == '__main__':
    upgrade_skill_to_v06()

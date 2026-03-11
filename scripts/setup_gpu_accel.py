#!/usr/bin/env python3
"""
GPU加速自动检测和安装脚本 - V16.2

功能:
1. 自动检测系统GPU
2. 检查FFmpeg是否支持对应的GPU编码器
3. 提供安装指导（自动安装需要管理员权限的部分）

使用方式:
    python -m scripts.setup_gpu_accel

作者: 杭州雷鸣AI短剧项目
版本: V16.2
"""

import subprocess
import platform
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, List


class GPUAccelSetup:
    """GPU加速设置器"""

    def __init__(self):
        self.system = platform.system()
        self.ffmpeg_path = shutil.which('ffmpeg')
        self.detected_gpus = []
        self.supported_encoders = []

    def run(self) -> Dict:
        """执行完整的GPU加速检测和设置"""
        print("\n" + "="*60)
        print("🎮 GPU加速检测和设置工具 V16.2")
        print("="*60 + "\n")

        results = {
            'system': self.system,
            'ffmpeg_path': self.ffmpeg_path,
            'gpus': [],
            'supported_encoders': [],
            'recommended_encoder': None,
            'needs_setup': [],
            'setup_commands': []
        }

        # 1. 检查FFmpeg
        if not self.ffmpeg_path:
            print("❌ FFmpeg未安装！")
            results['needs_setup'].append('ffmpeg')
            results['setup_commands'].append(self._get_ffmpeg_install_command())
            return results

        print(f"✅ FFmpeg已安装: {self.ffmpeg_path}")

        # 2. 检测GPU
        print("\n📊 检测GPU...")
        gpus = self._detect_gpus()
        results['gpus'] = gpus

        if not gpus:
            print("⚠️ 未检测到独立GPU")
            return results

        for gpu in gpus:
            print(f"  - {gpu['type']}: {gpu['name']}")

        # 3. 检测FFmpeg编码器支持
        print("\n🎬 检测FFmpeg GPU编码器支持...")
        encoders = self._detect_ffmpeg_encoders()
        results['supported_encoders'] = encoders

        if not encoders:
            print("⚠️ FFmpeg不支持任何GPU编码器")
            results['needs_setup'].append('ffmpeg-full')
            results['setup_commands'].append(self._get_ffmpeg_full_install_command())
            return results

        for enc in encoders:
            print(f"  ✅ {enc['name']}: {enc['encoder']}")

        # 4. 推荐最佳编码器
        recommended = self._recommend_encoder(gpus, encoders)
        results['recommended_encoder'] = recommended

        if recommended:
            print(f"\n🏆 推荐编码器: {recommended['name']}")
            print(f"   编码器: {recommended['encoder']}")
            print(f"   硬件加速: {recommended.get('hwaccel', '无')}")

        return results

    def _detect_gpus(self) -> List[Dict]:
        """检测系统GPU"""
        gpus = []

        if self.system == 'Darwin':  # macOS
            # macOS使用system_profiler检测
            try:
                result = subprocess.run(
                    ['system_profiler', 'SPDisplaysDataType'],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout

                if 'Apple' in output or 'M1' in output or 'M2' in output or 'M3' in output:
                    gpus.append({
                        'type': 'Apple Silicon',
                        'name': 'Apple GPU (VideoToolbox)',
                        'vendor': 'apple'
                    })
                elif 'Intel' in output:
                    gpus.append({
                        'type': 'Intel',
                        'name': 'Intel Integrated Graphics',
                        'vendor': 'intel'
                    })
                elif 'AMD' in output or 'Radeon' in output:
                    gpus.append({
                        'type': 'AMD',
                        'name': 'AMD Radeon',
                        'vendor': 'amd'
                    })
            except Exception as e:
                print(f"  ⚠️ GPU检测失败: {e}")
                # 默认认为macOS支持VideoToolbox
                gpus.append({
                    'type': 'Apple',
                    'name': 'Apple GPU (VideoToolbox)',
                    'vendor': 'apple'
                })

        elif self.system == 'Windows':
            # Windows使用wmic检测
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout.lower()

                if 'nvidia' in output or 'geforce' in output or 'rtx' in output or 'gtx' in output:
                    # 获取具体型号
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'nvidia' in line.lower() or 'geforce' in line.lower():
                            gpus.append({
                                'type': 'NVIDIA',
                                'name': line,
                                'vendor': 'nvidia'
                            })
                            break

                if 'intel' in output:
                    gpus.append({
                        'type': 'Intel',
                        'name': 'Intel Integrated Graphics',
                        'vendor': 'intel'
                    })

                if 'amd' in output or 'radeon' in output:
                    gpus.append({
                        'type': 'AMD',
                        'name': 'AMD Radeon',
                        'vendor': 'amd'
                    })

            except Exception as e:
                print(f"  ⚠️ GPU检测失败: {e}")

            # 备用：检查nvidia-smi
            if not any(g['vendor'] == 'nvidia' for g in gpus):
                try:
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        gpus.append({
                            'type': 'NVIDIA',
                            'name': result.stdout.strip(),
                            'vendor': 'nvidia'
                        })
                except:
                    pass

        elif self.system == 'Linux':
            # Linux使用lspci检测
            try:
                result = subprocess.run(
                    ['lspci'],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout.lower()

                if 'nvidia' in output:
                    gpus.append({
                        'type': 'NVIDIA',
                        'name': 'NVIDIA GPU',
                        'vendor': 'nvidia'
                    })

                if 'intel' in output:
                    gpus.append({
                        'type': 'Intel',
                        'name': 'Intel Integrated Graphics',
                        'vendor': 'intel'
                    })

                if 'amd' in output or 'radeon' in output:
                    gpus.append({
                        'type': 'AMD',
                        'name': 'AMD Radeon',
                        'vendor': 'amd'
                    })

            except Exception as e:
                print(f"  ⚠️ GPU检测失败: {e}")

            # 备用：检查nvidia-smi
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    if not any(g['vendor'] == 'nvidia' for g in gpus):
                        gpus.append({
                            'type': 'NVIDIA',
                            'name': result.stdout.strip(),
                            'vendor': 'nvidia'
                        })
            except:
                pass

        return gpus

    def _detect_ffmpeg_encoders(self) -> List[Dict]:
        """检测FFmpeg支持的GPU编码器"""
        encoders = []

        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout

            # 定义编码器配置
            encoder_configs = [
                {'encoder': 'h264_videotoolbox', 'hwaccel': 'videotoolbox',
                 'name': 'Apple VideoToolbox', 'vendor': 'apple', 'priority': 1},
                {'encoder': 'h264_nvenc', 'hwaccel': 'cuda',
                 'name': 'NVIDIA NVENC', 'vendor': 'nvidia', 'priority': 1},
                {'encoder': 'h264_qsv', 'hwaccel': 'qsv',
                 'name': 'Intel QuickSync', 'vendor': 'intel', 'priority': 2},
                {'encoder': 'h264_amf', 'hwaccel': None,
                 'name': 'AMD AMF', 'vendor': 'amd', 'priority': 3},
                {'encoder': 'h264_vaapi', 'hwaccel': 'vaapi',
                 'name': 'VAAPI', 'vendor': 'intel', 'priority': 4},
            ]

            for config in encoder_configs:
                if config['encoder'] in output:
                    encoders.append(config)

        except Exception as e:
            print(f"  ⚠️ FFmpeg编码器检测失败: {e}")

        return encoders

    def _recommend_encoder(self, gpus: List[Dict], encoders: List[Dict]) -> Optional[Dict]:
        """推荐最佳编码器"""
        if not gpus or not encoders:
            return None

        # 获取GPU厂商
        gpu_vendors = [g['vendor'] for g in gpus]

        # 按优先级匹配
        sorted_encoders = sorted(encoders, key=lambda x: x['priority'])

        for encoder in sorted_encoders:
            if encoder['vendor'] in gpu_vendors:
                return encoder

        # 如果没有匹配，返回第一个可用的
        return sorted_encoders[0] if sorted_encoders else None

    def _get_ffmpeg_install_command(self) -> str:
        """获取FFmpeg安装命令"""
        if self.system == 'Darwin':
            return "brew install ffmpeg"
        elif self.system == 'Windows':
            return "scoop install ffmpeg  # 或 choco install ffmpeg"
        else:  # Linux
            return "sudo apt install ffmpeg  # Ubuntu/Debian"

    def _get_ffmpeg_full_install_command(self) -> str:
        """获取完整版FFmpeg安装命令（带GPU支持）"""
        if self.system == 'Darwin':
            return "brew tap homebrew-ffmpeg/ffmpeg && brew install homebrew-ffmpeg/ffmpeg/ffmpeg"
        elif self.system == 'Windows':
            return """# 方式1: 使用scoop安装完整版
scoop uninstall ffmpeg
scoop install ffmpeg-full

# 方式2: 下载完整版
# https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z"""
        else:  # Linux
            return """# Ubuntu/Debian
sudo apt install ffmpeg

# 如需NVIDIA支持，确保安装了nvidia-cuda-toolkit
sudo apt install nvidia-cuda-toolkit"""


def print_setup_guide(results: Dict):
    """打印设置指南"""
    print("\n" + "="*60)
    print("📋 设置指南")
    print("="*60)

    if results['needs_setup']:
        print("\n⚠️ 需要安装以下组件:\n")
        for need in results['needs_setup']:
            print(f"  - {need}")

        print("\n📦 安装命令:\n")
        for cmd in results['setup_commands']:
            print(f"  {cmd}")
    else:
        print("\n✅ 系统已就绪，可以使用GPU加速!")
        if results['recommended_encoder']:
            enc = results['recommended_encoder']
            print(f"\n使用方式:")
            print(f"  python -m scripts.understand.render_clips data/... video_dir --hwaccel")
            print(f"\n将自动使用: {enc['name']} ({enc['encoder']})")


def main():
    """主入口"""
    setup = GPUAccelSetup()
    results = setup.run()
    print_setup_guide(results)

    return 0 if results['recommended_encoder'] else 1


if __name__ == "__main__":
    sys.exit(main())

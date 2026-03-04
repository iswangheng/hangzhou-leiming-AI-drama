# 待办事项 - 片尾检测模块

**优先级顺序**：

## 🔥 紧急（下次启动立即做）

- [ ] **重新运行完整批量测试**
  ```bash
  cd "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama"
  python test_ending_detection.py
  ```

- [ ] **查看检测结果**
  ```bash
  # 查看JSON结果
  cat data/hangzhou-leiming/ending_credits/多子多福，开局就送绝美老婆_ending_credits.json | python3 -m json.tool
  ```

- [ ] **手动验证准确性**
  - 打开几个视频，查看最后2秒
  - 确认检测时长是否合理
  - 重点检查：第2、3、4、6、7、8集

## ⚙️ 参数调整（如果验证后需要）

当前参数：
```python
CHECK_LAST_SECONDS = 3.5         # 只检测最后3.5秒
SIMILARITY_THRESHOLD = 0.92      # 相似度阈值
MIN_CONTINUOUS_FRAMES = 5        # 最小连续帧数
SAFE_MARGIN = 0.1                # 安全边界
```

**可能需要调整**：
- 如果漏检太多：降低阈值到 0.90
- 如果误检太多：提高阈值到 0.93
- 如果边界不准：降低连续帧数到 3

## 📦 应用（验证通过后）

- [ ] **生成去除片尾的视频**
  ```bash
  python trim_ending_credits.py
  ```

- [ ] **手动检查视频质量**
  - 播放 `clips/多子多福，开局就送绝美老婆_去除片尾v2/` 中的视频
  - 确认片尾已正确去除
  - 确认没有剪到正常内容

- [ ] **集成到渲染流程**
  - 修改 `scripts/understand/render_clips.py`
  - 使用 `effective_duration` 代替 `total_duration`

## 📄 文档

详细进展记录：`ENDING-CREDITS-PROGRESS.md`

---

**快速启动命令**：
```bash
# 1. 进入项目目录
cd "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama"

# 2. 查看进展文档
cat ENDING-CREDITS-PROGRESS.md

# 3. 运行测试
python test_ending_detection.py

# 4. 查看结果
python3 << 'EOF'
import json
from pathlib import Path
data = json.load(Path("data/hangzhou-leiming/ending_credits/多子多福，开局就送绝美老婆_ending_credits.json"))
for ep in data['episodes']:
    print(f"第{ep['episode']:2d}集: {'✅' if ep['ending_info']['has_ending'] else '❌'} {ep['ending_info']['duration']:.2f}秒")
EOF
```

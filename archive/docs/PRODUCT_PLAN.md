# 杭州雷鸣AI短剧剪辑服务 - 产品方案文档

## 版本更新

### V2.0 - 精确时间戳与质量筛选 (2026-03-03)

**核心改进**：
1. **精确时间戳** ⭐⭐⭐⭐⭐
   - AI返回窗口内精确的秒数，而非窗口开始时间
   - 时间精度从"窗口开始（误差最大60秒）"提升到"精确时刻（±2秒）"

2. **质量筛选机制** ⭐⭐⭐⭐⭐
   - 置信度阈值：>7.0的标记才保留
   - 智能去重：同集内15秒间隔去重
   - 数量控制：每集最多2个高光点+3个钩子点

3. **宁缺毋滥原则** ⭐⭐⭐⭐⭐
   - 学习人工标记规律：平均每集只有1.0个标记
   - 输出"最推荐的"高质量标记，而非所有可能的标记

**效果对比**：

| 指标 | V1.0 | V2.0 | 提升 |
|------|------|------|------|
| 时间精度 | 窗口开始 | 精确时刻 | ⭐⭐⭐⭐⭐ |
| 识别数量 | 2.3个/集 | 1.2个/集 | 接近人工 |
| 平均置信度 | N/A | 8.3 | ⭐⭐⭐⭐ |
| 第1集开头 | ❌ | ✅ 自动识别 | ⭐⭐⭐⭐⭐ |

---

## 一、产品定位

**无界面纯服务端AI剪辑服务**：通过OpenClaw后台运行的AI剪辑服务，客户只需部署OpenClaw即可使用。

---

## 二、整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        我们 (云端)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────────────────────┐   │
│  │  技能训练系统    │    │  视频剪辑服务                   │   │
│  │                 │    │                                  │   │
│  │  输入:          │    │  API:                           │   │
│  │  - 历史视频     │    │  - /api/video/understand (记账5元)│   │
│  │  - Excel标记   │    │  - /api/skill/latest           │   │
│  │                 │    │  - /api/clip/generate          │   │
│  │  输出:          │    │  - /api/clip/start (记账0.05元)  │   │
│  │  - skill.md   │    │  - /api/clip/complete         │   │
│  │                 │    │                                  │   │
│  │  (我们维护)    │    │  记账系统:                      │   │
│  │                 │    │  - 消费记录               │   │
│  └─────────────────┘    │  - 视频理解记录                │   │
│                          │  - 剪辑记录                   │   │
│                          └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
           ↑                                    ↑
           │ 获取技能                           │ 调用API
           │                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     客户端 (OpenClaw)                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Skill: ai-drama-cutter                               │   │
│  │                                                          │   │
│  │  1. 确认剧集 (扫描目录)                               │   │
│  │  2. 本地FFmpeg抽帧 + Whisper转录                    │   │
│  │  3. /api/video/understand → 记账5元                │   │
│  │  4. /api/skill/latest → 获取最新技能                │   │
│  │  5. /api/clip/generate → 生成剪辑组合               │   │
│  │  6. 客户确认/自动筛选                              │   │
│  │  7. /api/clip/start + 本地FFmpeg剪辑              │   │
│  │  8. /api/clip/complete → 记账0.05元/条           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、模块详细设计

### 3.1 技能训练系统

#### 3.1.1 输入数据
- 历史短剧视频（10集）
- Excel标记文件（高光点、钩子点）

#### 3.1.2 训练流程
```
1. 视频关键帧提取 (FFmpeg)
2. Whisper语音转录
3. Gemini AI多模态分析
4. 生成技能文件 (skill.md)
5. 螺旋式迭代更新版本
```

#### 3.1.3 输出
- **技能文件** (skill.md)：Markdown格式，包含：
  - 高光类型定义
  - 钩子类型定义
  - 剪辑规则
  - AI分析提示词

#### 3.1.4 管理
- **版本管理**：只保留最新版本 (如 v1.0, v1.1)
- **维护方式**：我们通过OpenClaw执行训练，持续迭代

---

### 3.2 视频剪辑服务

#### 3.2.1 客户端使用流程

```
客户输入: "帮我剪辑 /shared/disk/百里将就"

↓

【步骤1】确认剧集
- 扫描目录，获取视频文件列表
- 展示给客户确认

【步骤2】本地视频处理
- FFmpeg抽帧 (关键帧保存本地)
- Whisper转录 (音频→文本，保存本地)

【步骤3】视频理解 (MCP调用)
- 调用 /api/video/understand
- 发送: video_id + 关键帧(base64) + 转录文本
- 返回: 高光点列表 + 钩子点列表
- 扣费: 5元/部

【步骤4】获取最新技能 (MCP调用)
- 调用 /api/skill/latest
- 返回: skill.md 内容

【步骤5】生成剪辑组合 (MCP调用)
- 调用 /api/clip/generate
- 发送: 高光点 + 钩子点 + skill.md
- 返回: 剪辑组合列表
- 费用: 免费

【步骤6】客户确认或自动筛选
- 展示剪辑组合供客户选择
- 或设置自动化规则筛选

【步骤7】执行剪辑 (MCP调用)
- 调用 /api/clip/start
- 发送: video_id + 组合列表
- 返回: 任务token
- 本地FFmpeg开始剪辑

【步骤8】完成剪辑 (MCP调用)
- 调用 /api/clip/complete
- 发送: task_token + 实际产出条数
- 扣费: 0.05元/条
```

#### 3.2.2 本地处理说明

| 操作 | 工具 | 资源 |
|------|------|------|
| 关键帧提取 | FFmpeg | 客户端CPU |
| 语音转录 | Whisper (small模型) | 客户端CPU |
| 视频剪辑 | FFmpeg | 客户端CPU |
| AI分析 | Gemini API | 云端 |

---

### 3.3 API设计

#### 3.3.1 接口列表

| 接口 | 方法 | 说明 | 费用 |
|------|------|------|------|
| `/api/skill/latest` | GET | 获取最新技能文件 | 免费 |
| `/api/video/understand` | POST | 视频理解(AI分析) | 记账5元/部 |
| `/api/video/status` | GET | 查询视频理解状态 | 免费 |
| `/api/clip/generate` | POST | 生成剪辑组合 | 免费 |
| `/api/clip/start` | POST | 开始剪辑任务 | 记账0.05元/条 |
| `/api/clip/complete` | POST | 剪辑完成确认 | - |
| `/api/clip/cancel` | POST | 取消剪辑任务 | - |
| `/api/expenses` | GET | 查询消费记录 | 免费 |

#### 3.3.2 接口详细定义

**GET /api/skill/latest**
```json
响应:
{
  "version": "v1.0",
  "content": "# 剪辑技能文件\n\n## 高光类型\n...",
  "updatedAt": "2026-03-02T10:00:00Z"
}
```

**POST /api/video/understand**
```json
请求:
{
  "customerId": "cust_xxx",
  "videoId": "video_hash_xxx",
  "videoName": "百里将就",
  "keyframes": ["base64...", "base64..."],
  "transcript": "转录文本内容..."
}

响应:
{
  "success": true,
  "highlights": [
    {"timestamp": 30000, "type": "反转", "description": "女主发现真相"}
  ],
  "hooks": [
    {"timestamp": 120000, "type": "悬念", "description": "男主离去"}
  ]
}
```

**POST /api/clip/generate**
```json
请求:
{
  "customerId": "cust_xxx",
  "videoId": "video_hash_xxx",
  "highlights": [...],
  "hooks": [...],
  "skillContent": "skill.md内容",
  "config": {
    "minDuration": 30,    // 最短30秒，默认值
    "maxDuration": 300   // 最长5分钟，默认值
  }
}

响应:
{
  "success": true,
  "clips": [
    {"start": 30000, "end": 120000, "duration": 90000, "type": "反转-悬念"}
  ]
}
```

**POST /api/clip/start**
```json
请求:
{
  "customerId": "cust_xxx",
  "videoId": "video_hash_xxx",
  "clips": [
    {"start": 30000, "end": 120000},
    {"start": 180000, "end": 240000}
  ]
}

响应:
{
  "success": true,
  "taskToken": "task_xxx",
  "fee": 0.10,  // 0.05 × 2条（仅记账）
  "clipCount": 2
}
```

**POST /api/clip/complete**
```json
请求:
{
  "taskToken": "task_xxx",
  "actualClips": 2
}

响应:
{
  "success": true,
  "videoUnderstandFee": 5.00,
  "clipFee": 0.10,
  "totalFee": 5.10,
  "recorded": true  -- 已记账
}
```

**GET /api/expenses**
```json
请求:
{
  "customerId": "cust_xxx",  // 可选
  "startDate": "2026-01-01", // 可选
  "endDate": "2026-12-31"    // 可选
}

响应:
{
  "success": true,
  "expenses": [
    {
      "id": 1,
      "videoName": "百里将就",
      "videoUnderstandFee": 5.00,
      "clipCount": 10,
      "clipFee": 0.50,
      "totalFee": 5.50,
      "status": "completed",
      "createdAt": "2026-03-02T10:00:00Z"
    }
  ],
  "summary": {
    "totalVideos": 5,
    "totalClips": 50,
    "grandTotal": 27.50
  }
}
```

---

### 3.4 记账系统（只记账，不扣费）

#### 3.4.1 设计说明
本系统采用**记账模式**：只记录消费流水，不实际扣除余额。后续可通过管理后台查看统计。

#### 3.4.2 数据库设计

```sql
-- 消费记录表（只记账，不扣费）
CREATE TABLE expenses (
  id INT PRIMARY KEY AUTOINCREMENT,
  customer_id TEXT NOT NULL,      -- 客户ID
  customer_name TEXT,              -- 客户名称（可选）
  video_id TEXT NOT NULL,         -- 视频唯一标识(哈希)
  video_name TEXT,                -- 视频名称
  
  -- 费用明细
  video_understand_fee DECIMAL(10,2) DEFAULT 5.00,  -- 视频理解费用（5元/部）
  clip_count INT DEFAULT 0,        -- 剪辑条数
  clip_fee DECIMAL(10,2) DEFAULT 0.00,              -- 剪辑费用（0.05元/条）
  total_fee DECIMAL(10,2) DEFAULT 0.00,             -- 总费用
  
  -- 状态
  status TEXT DEFAULT 'pending',   -- pending/completed
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_expenses_customer ON expenses(customer_id);
CREATE INDEX idx_expenses_video ON expenses(video_id);
CREATE INDEX idx_expenses_created ON expenses(created_at);
```

#### 3.4.3 记账逻辑

```python
# 视频理解 - 记录5元
def record_video_understand(customer_id, video_name):
    expense = Expense(
        customer_id=customer_id,
        video_name=video_name,
        video_understand_fee=5.00,
        total_fee=5.00,
        status='pending'
    )
    expense.save()
    return expense.id

# 剪辑完成 - 记录剪辑费用
def record_clip_complete(expense_id, clip_count):
    clip_fee = clip_count * 0.05
    expense = Expense.get(expense_id)
    expense.clip_count = clip_count
    expense.clip_fee = clip_fee
    expense.total_fee = expense.video_understand_fee + clip_fee
    expense.status = 'completed'
    expense.completed_at = datetime.now()
    expense.save()
```

#### 3.4.4 消费统计查询

```sql
-- 按客户统计总消费
SELECT customer_id, customer_name,
       COUNT(*) as video_count,
       SUM(video_understand_fee) as total_understand_fee,
       SUM(clip_fee) as total_clip_fee,
       SUM(total_fee) as grand_total
FROM expenses
GROUP BY customer_id;

-- 按时间段统计
SELECT DATE(created_at) as date,
       COUNT(*) as video_count,
       SUM(total_fee) as daily_fee
FROM expenses
GROUP BY DATE(created_at);
```

---

### 3.5 防绕过机制

1. **视频理解**：客户端无法自己调用Gemini（没API Key），必须经过云端API
2. **剪辑组合**：必须调用`/api/clip/generate`获取，否则不知道要剪什么
3. **开始剪辑**：必须调用`/api/clip/start`获得token，否则本地FFmpeg没有任务参数
4. **余额联动**：任何一步余额不足，整个流程中断

---

## 四、商业模式（记账模式）

### 4.1 收费标准

| 收费项 | 价格 | 说明 |
|--------|------|------|
| 视频理解 | 5元/部 | 分析10集，返回高光/钩子点 |
| 素材剪辑 | 0.05元/条 | 按实际产出条数计费 |

### 4.2 记账流程（不扣费）

```
视频理解: 调用API时记录费用(记账5元)
素材剪辑: 剪辑完成后记录费用(0.05元/条)
管理后台: 可查看所有消费记录和统计数据
```

### 4.3 管理后台功能

- 消费记录查询（按客户、按时间）
- 消费统计图表
- 导出报表功能

---

## 五、客户部署

### 5.1 部署流程

```
1. 客户提供服务器
2. 我们部署OpenClaw到客户服务器
3. 导入Skill: ai-drama-cutter
4. 配置MCP: 连接我们的云端API
5. 配置共享磁盘路径
6. 客户使用
```

### 5.2 客户使用

```
客户: "帮我剪辑 /shared/disk/百里将就"

OpenClaw自动执行完整流程:
  ↓ 确认剧集
  ↓ 本地抽帧+转录
  ↓ 视频理解(扣5元)
  ↓ 获取技能
  ↓ 生成剪辑组合
  ↓ 客户确认
  ↓ 执行剪辑(扣0.05元/条)
  ↓ 完成
```

---

## 六、开发计划

### 6.1 第一阶段：技能训练系统
- [x] 整理现有训练代码
- [x] 实现螺旋式迭代更新
- [x] 部署训练流程

### 6.2 第二阶段：视频理解模块（关键帧提取+AI分析）
- [ ] `extract_analysis.py` - 0.5秒/帧提取关键帧 + ASR上下文
- [ ] `video_understand.py` - AI逐段分析，识别高光点/钩子点
- [ ] 测试视频理解流程

### 6.3 第三阶段：剪辑组合生成模块
- [ ] `clip_generator.py` - 生成高光→钩子剪辑组合
- [ ] 支持用户配置：最短/最长时间（默认30秒-5分钟）

### 6.4 第四阶段：记账系统
- [ ] `expense_tracker.py` - 消费记录（只记账不扣费）
- [ ] 消费记录数据表设计

### 6.5 第五阶段：API服务
- [ ] Express API开发
- [ ] 接口对接

### 6.6 第六阶段：客户端Skill
- [ ] 编写ai-drama-cutter Skill
- [ ] 本地处理逻辑

### 6.7 第七阶段：管理后台
- [ ] 消费统计页面
- [ ] 用量查询

---

## 七、术语表

| 术语 | 定义 |
|------|------|
| OpenClaw | AI助手运行框架 |
| Skill | OpenClaw的扩展技能包 |
| MCP | Model Context Protocol，云端API封装 |
| 高光点 | 视频中的精彩开始时间点 |
| 钩子点 | 让人想继续看的时间点 |
| 剪辑组合 | 从高光点到钩子点的视频片段 |
| 技能文件 | AI学习后生成的Markdown格式规则文件 |
| ASR | 自动语音识别 (Whisper) |
| 抽帧 | 从视频中提取关键画面 |

---

**文档版本**: v1.0
**创建时间**: 2026-03-02
**作者**: 王恒

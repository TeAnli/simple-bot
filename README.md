# ACM Bot (安心Bot)

这是一个基于 `ncatbot` 框架开发的 QQ 机器人，专为 ACM/ICPC 竞赛团队及算法爱好者打造。它集成了多平台比赛查询、用户信息追踪、排行榜生成以及 AI 智能问答等功能。

## ✨ 功能特性

### 🏆 竞赛辅助
*   **多平台比赛查询**: 支持查询 **Codeforces**、**牛客 (Nowcoder)**、**洛谷 (Luogu)** 以及 **SCPC (西南科技大学校赛平台)** 的近期比赛。
*   **比赛提醒**: 支持群组开启/关闭比赛自动提醒功能（每小时检查一次，自动播报即将开始的比赛）。
*   **题目更新**: 实时获取 SCPC 平台近期更新的题目。

### 📊 数据查询与可视化
*   **用户信息查询**:
    *   **Codeforces**: 查询用户 Rating、Rank、头像等信息，并生成精美卡片。
    *   **Codeforces**: 生成用户 Rating 历史变化折线图。
    *   **SCPC**: 查询平台用户信息。
*   **榜单生成**:
    *   生成 SCPC 平台本周过题排行榜图片。
    *   导出指定 SCPC 比赛的排行榜为 Excel 表格。

### 🤖 AI 助手
*   内置基于 **Deepseek** 的 AI 助手，支持回答算法竞赛相关问题（如算法讲解、思路提示）。
*   *注：需在配置文件中配置 Deepseek API Key。*

### 🛠️ 基础功能
*   **菜单系统**: 通过 `/菜单` 查看所有可用指令。
*   **关于**: 通过 `/关于` 查看机器人版本及作者信息。
*   **娱乐**: 随机发送二次元图片。

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.8+。

```bash
# 克隆项目到本地
git clone <repository-url>
cd acm-bot

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核 (用于图片渲染)
playwright install chromium
```

### 2. 配置文件
首次运行后，`ncatbot` 会生成配置文件。请在 `config.yaml` 中添加以下配置以启用 AI 功能：

```yaml
deepseek_api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx"  # 你的 Deepseek API Key
ai_system_prompt: "..."  # (可选) 自定义 AI 系统提示词
ai_temperature: 0.5      # (可选) AI 温度参数
ai_max_tokens: 800       # (可选) AI 回复最大长度
```

### 3. 运行机器人
```bash
python main.py
```

## 📝 指令列表

| 指令 | 描述 | 示例 |
| :--- | :--- | :--- |
| `/菜单` | 查看帮助菜单 | `/菜单` |
| `/cf比赛` | 获取 Codeforces 近期比赛 | `/cf比赛` |
| `/cf用户 <handle>` | 获取 CF 用户信息卡片 | `/cf用户 tourist` |
| `/cf分数 <handle>` | 获取 CF Rating 折线图 | `/cf分数 jiangly` |
| `/牛客比赛` | 获取牛客近期比赛 | `/牛客比赛` |
| `/洛谷比赛` | 获取洛谷近期比赛 | `/洛谷比赛` |
| `/scpc近期比赛` | 获取 SCPC 平台近期比赛 | `/scpc近期比赛` |
| `/scpc用户 <name>` | 获取 SCPC 用户信息 | `/scpc用户 player1` |
| `/scpc排行` | 获取 SCPC 本周排行榜 | `/scpc排行` |
| `/scpc比赛排行 <id>` | 导出 SCPC 比赛 Excel 榜单 | `/scpc比赛排行 1001` |
| `/ai <问题>` | 向 AI 助手提问 | `/ai 什么是线段树？` |
| `/随机老婆` | 随机发送二次元图片 | `/随机老婆` |
| `/开启比赛提醒` | (管理员) 开启本群比赛通知 | `/开启比赛提醒` |

## 📂 项目结构

```
acm-bot/
├── main.py              # 机器人入口文件
├── requirements.txt     # 项目依赖
├── plugins/
│   └── acm/             # ACM 核心插件
│       ├── platforms/   # 各平台 API 实现 (Codeforces, SCPC 等)
│       ├── templates/   # 图片生成模板 (Jinja2)
│       ├── assets/      # 静态资源与缓存
│       └── utils/       # 通用工具 (AI, 网络, 渲染)
└── ...
```

## ⚠️ 注意事项
*   图片生成功能依赖 `Playwright`，请确保服务器/本地环境已正确安装浏览器内核。
*   Excel 生成功能需要写入权限，请确保运行目录可写。

## 👤 作者
TeAnli & Contributors

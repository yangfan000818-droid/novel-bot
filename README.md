# Novel Bot

自动将小说稿件发布到 [番茄小说](https://fanqienovel.com) 作者平台的 CLI 工具。支持 Markdown、TXT、DOCX 格式，具备断点续发、定时发布、AI 前缀清理等功能。

## 功能特性

- **多格式解析** — 支持 Markdown（`# 标题` 分章）、TXT（`第X章` 标记分章）、DOCX（Word 标题样式分章）
- **AI 前缀自动清理** — 自动识别并移除 AI 生成的思考前缀（`💭` 标记、推理关键词等）
- **断点续发** — 通过 `progress.json` 记录发布进度，中断后可从上次位置继续
- **定时发布** — 基于 APScheduler 的 cron 定时任务，支持多本书、多时段配置
- **Cookie 持久化** — 首次登录后保存 Cookie，后续无需重复登录
- **发布验证** — 自动检测发布结果（成功/失败模式匹配）
- **按书日志** — 每本书每天独立日志文件，方便排查问题
- **无头浏览器** — 默认无头模式运行，可配置为有头模式用于调试

## 项目结构

```
novel-bot/
├── config/
│   ├── settings.yaml      # 全局配置
│   └── schedule.yaml      # 定时任务配置
├── data/
│   ├── cookies.json       # 登录 Cookie（自动生成）
│   └── progress.json      # 发布进度（自动生成）
├── logs/                  # 运行日志（自动生成）
├── src/novel_bot/
│   ├── cli.py             # CLI 入口（publish / schedule）
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型（Chapter, Book, TaskState）
│   ├── orchestrator.py    # 发布流程编排
│   ├── parser/            # 稿件解析器
│   │   ├── base.py        # AI 前缀清理 + 章节拆分
│   │   ├── markdown.py    # Markdown 解析
│   │   ├── txt.py         # TXT 解析
│   │   └── docx.py        # DOCX 解析
│   ├── login/             # 登录管理
│   │   └── manager.py     # Cookie 持久化 + 会话管理
│   ├── publisher/         # 发布器
│   │   ├── base.py        # 发布器基类
│   │   └── tomato.py      # 番茄小说发布器
│   ├── monitor/           # 监控
│   │   ├── logger.py      # 按书日志
│   │   └── verifier.py    # 发布结果验证
│   └── scheduler.py       # 定时任务调度
├── tests/                 # 测试（85 个用例）
└── pyproject.toml
```

## 环境要求

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)（包管理器）

## 安装

```bash
git clone https://github.com/yangfan000818-droid/novel-bot.git
cd novel-bot

# 安装依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium
```

## 稿件目录结构

在配置的 `books_path` 目录下，每本书一个子目录：

```
books/
└── 你的书名/
    ├── book.json          # 书籍元信息
    └── chapters/          # 章节文件
        ├── 0001_灵根中品.md
        ├── 0002_灵根问心.md
        └── ...
```

### book.json 格式

```json
{
  "id": "书籍ID",
  "title": "书名",
  "platform": "tomato",
  "genre": "xuanhuan",
  "status": "active",
  "targetChapters": 200,
  "chapterWordCount": 3000,
  "language": "zh"
}
```

### 章节文件命名

文件名需以数字前缀排序（决定发布顺序）：

- `0001_标题.md` / `0001_标题.txt` / `0001_标题.docx`

### Markdown 章节格式

```markdown
# 第1章 章节标题

正文内容...
```

### TXT 章节格式

```
第1章 章节标题

正文内容...
```

### DOCX 章节格式

使用 Word 的标题样式（Heading 1、Heading 2 等）标识章节。

### AI 前缀清理

如果章节文件包含 AI 生成的思考前缀，会自动清理：

```
💭AI 思考过程...
更多思考...
核心要点...

正文内容开始。     ← 保留此部分
```

## 配置

编辑 `config/settings.yaml`：

```yaml
# 稿件根目录（相对于项目根目录）
books_path: ../books

# 发布配置
publish:
  delay_min: 5          # 章节间最小延迟（秒）
  delay_max: 15         # 章节间最大延迟（秒）
  headless: true        # 无头模式（设为 false 可看到浏览器操作）

# 登录配置
login:
  cookie_file: data/cookies.json

# 进度文件
progress:
  file: data/progress.json

# 日志配置
logging:
  dir: logs
```

## 使用方法

### 手动发布

```bash
# 发布指定书籍
uv run novel-bot publish 书名
```

### 定时发布

编辑 `config/schedule.yaml`：

```yaml
schedules:
  - book: 书名
    chapters_per_day: 3
    time: "08:00,14:00,20:00"
```

启动定时任务：

```bash
uv run novel-bot schedule
```

### 查看帮助

```bash
uv run novel-bot --help
uv run novel-bot publish --help
uv run novel-bot schedule --help
```

## 运行测试

```bash
uv run pytest
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 浏览器自动化 | [Playwright](https://playwright.dev/) |
| 定时调度 | [APScheduler](https://apscheduler.readthedocs.io/) |
| CLI | [Click](https://click.palletsprojects.com/) |
| 配置管理 | [PyYAML](https://pyyaml.org/) |
| DOCX 解析 | [python-docx](https://python-docx.readthedocs.io/) |

## License

MIT

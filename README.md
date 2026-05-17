# Overnight Radar

隔夜美股影响 A 股分析系统 — 每日自动追踪美股异动，AI 分析对 A 股的映射影响，并推送至企业微信。

## 功能

- **每日早报** — 自动抓取美股成交额 Top N，AI 分析影响方向/强度，映射相关 A 股标的
- **企业微信推送** — 按影响强度分层推送，支持 WeCom markdown 格式
- **历史回测** — 验证映射准确性，计算 T/T+1/T+3/T+5/T+10 实际收益率，统计胜率和方向准确率
- **映射管理** — CRUD 管理美股-A股映射关系，支持搜索、排序、分页
- **定时任务** — APScheduler 每日自动执行分析和推送

## 技术栈

- Python 3.11 + FastAPI + Jinja2
- MySQL 8.0 + SQLAlchemy
- yfinance（美股数据）+ 腾讯行情 API（A股数据）
- OpenAI 兼容 API（AI 分析）
- APScheduler（定时任务）
- Docker 部署

## 快速开始

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库密码、AI API Key、企业微信 Webhook 等

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker 部署

应用连接宿主机 MySQL，不在容器内运行数据库：

```bash
# 1. 确保宿主机 MySQL 已运行，overnight_radar 数据库已创建
# 2. 配置 .env（MYSQL_HOST 使用 host.docker.internal）
# 3. 构建并启动
docker compose up -d --build
```

应用启动时会自动创建所有数据表。

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 运行环境 | development |
| `SECRET_KEY` | 会话签名密钥（生产环境必须修改） | change-me-in-env |
| `ADMIN_USERNAME` | 登录用户名 | admin |
| `ADMIN_PASSWORD_HASH` | bcrypt 密码哈希 | — |
| `MYSQL_HOST` | 数据库地址 | 127.0.0.1 |
| `AI_API_KEY` | AI 分析 API Key | — |
| `AI_BASE_URL` | AI API 地址 | — |
| `WECOM_WEBHOOK` | 企业微信机器人 Webhook | — |
| `DAILY_JOB_TIME` | 每日分析时间（CST） | 06:00 |
| `DAILY_PUSH_TIME` | 每日推送时间（CST） | 08:00 |

完整配置见 `.env.example`。

### 生成密码哈希

```bash
python -m app.web.auth --hash-password your-password
```

## 项目结构

```
app/
├── ai/              # AI 分析客户端和输出校验
├── data_sources/    # yfinance、腾讯行情数据源
├── models/          # SQLAlchemy 数据模型
├── schemas/         # Pydantic 校验模型
├── services/        # 业务逻辑（报告、回测、映射、推送）
├── static/          # CSS/JS 静态资源
├── templates/       # Jinja2 页面模板
├── utils/           # 时区等工具
└── web/             # 路由和认证
migrations/          # 数据库初始化 SQL
tests/               # 单元测试
```

## License

MIT

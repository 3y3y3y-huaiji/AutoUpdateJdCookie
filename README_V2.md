# AutoUpdateJdCookie v2.0

自动化更新青龙面板的失效JD_COOKIE，支持Web管理界面和Docker Compose一键部署。

## 🎯 v2.0 新特性

* **Web管理界面** - 可视化配置，无需手动编辑文件
* **Docker Compose** - 一键部署，服务编排
* **改进的错误处理** - 更好的异常捕获和重试机制
* **模块化验证码识别** - 独立的CaptchaSolver类
* **实时日志** - WebSocket实时日志推送
* **配置持久化** - JSON格式配置，支持动态更新

## 📦 技术栈

* **后端**: FastAPI 0.115.0 + Uvicorn
* **数据验证**: Pydantic 2.0.0
* **浏览器自动化**: Playwright
* **OCR识别**: ddddocr + PaddleOCR
* **容器化**: Docker + Docker Compose

## 🚀 快速开始

### Docker Compose 部署（推荐）

1. **克隆项目**
```bash
git clone https://github.com/3y3y3y-huaiji/AutoUpdateJdCookie.git
cd AutoUpdateJdCookie
```

2. **启动服务**
```bash
docker-compose up -d
```

3. **访问Web界面**
```
http://localhost:8080
```

4. **配置青龙面板**
   - 进入"青龙面板"标签
   - 填写青龙面板URL
   - 选择认证方式（client_id+client_secret / token / 用户名+密码）
   - 点击"测试连接"验证配置

5. **添加账号**
   - 进入"账号管理"标签
   - 点击"+ 添加账号"
   - 填写用户名、密码、pt_pin等信息
   - 保存

6. **配置定时任务**
   - 进入"全局配置"标签
   - 设置Cron表达式（默认：`15 0 * * *`）
   - 保存配置

### 本地部署

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **启动Web服务**
```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080
```

3. **访问Web界面**
```
http://localhost:8080
```

## 📖 配置说明

### 账号配置

| 字段 | 必填 | 说明 |
|------|--------|------|
| username | 是 | 用户名（手机号或QQ号）|
| password | 是 | 密码 |
| pt_pin | 是 | 京东pt_pin |
| user_type | 否 | 账号类型：jd/qq，默认jd |
| force_update | 否 | 是否强制更新，默认false |
| auto_switch | 否 | 是否自动处理验证码，默认true |
| sms_func | 否 | 短信验证码处理方式：no/manual_input/webhook |
| sms_webhook | 否 | 短信验证码webhook地址 |
| voice_func | 否 | 语音验证码处理方式：no/manual_input |

### 青龙面板配置

| 字段 | 必填 | 说明 |
|------|--------|------|
| url | 是 | 青龙面板URL |
| client_id | 否 | client_id（可选）|
| client_secret | 否 | client_secret（可选）|
| token | 否 | token（可选）|
| username | 否 | 青龙用户名（可选）|
| password | 否 | 青龙密码（可选）|

### 全局配置

| 字段 | 必填 | 说明 |
|------|--------|------|
| headless | 否 | 是否启用无头模式，默认true |
| cron_expression | 是 | 定时任务Cron表达式，默认`15 0 * * *` |
| user_agent | 否 | User-Agent，留空使用默认 |
| enable_desensitize | 否 | 是否启用日志脱敏，默认false |

### 通知配置

支持多种通知方式：
* 企业微信
* 自定义Webhook
* 钉钉
* 飞书
* PushPlus
* Server酱

### 代理配置

| 字段 | 必填 | 说明 |
|------|--------|------|
| server | 否 | 代理服务器地址（如：http://127.0.0.1:7890）|
| username | 否 | 代理用户名（可选）|
| password | 否 | 代理密码（可选）|

## 🔧 API接口

### 配置相关

* `GET /api/config` - 获取完整配置
* `POST /api/config` - 更新完整配置

### 账号管理

* `GET /api/accounts` - 获取账号列表
* `POST /api/accounts?username={username}` - 添加账号
* `PUT /api/accounts/{username}` - 更新账号
* `DELETE /api/accounts/{username}` - 删除账号

### 青龙面板

* `GET /api/qinglong` - 获取青龙面板配置
* `POST /api/qinglong` - 更新青龙面板配置
* `POST /api/qinglong/test` - 测试青龙面板连接

### 全局配置

* `GET /api/global` - 获取全局配置
* `POST /api/global` - 更新全局配置

### 通知配置

* `GET /api/notification` - 获取通知配置
* `POST /api/notification` - 更新通知配置

### 代理配置

* `GET /api/proxy` - 获取代理配置
* `POST /api/proxy` - 更新代理配置

### 任务管理

* `POST /api/task/start` - 启动任务
* `POST /api/task/stop` - 停止任务
* `GET /api/task/status/{task_id}` - 获取任务状态

### WebSocket

* `WS /ws/logs` - 实时日志推送

## 📁 项目结构

```
AutoUpdateJdCookie/
├── web/                    # Web服务
│   ├── app.py             # FastAPI应用
│   ├── models.py          # Pydantic数据模型
│   └── static/           # 前端静态文件
│       └── index.html     # Web管理界面
├── config/               # 配置管理
│   └── settings.py       # 配置管理器
├── utils/                # 工具模块
│   ├── captcha_solver.py  # 验证码识别器
│   ├── ocr_engine.py     # OCR引擎工厂
│   ├── ck.py            # Cookie检测
│   ├── consts.py        # 常量定义
│   └── tools.py         # 工具函数
├── api/                  # API模块
│   ├── qinglong.py      # 青龙面板API
│   └── send.py          # 通知发送API
├── main_v2.py           # 核心登录逻辑（重构版）
├── schedule_main_v2.py   # 定时任务调度（重构版）
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile            # Docker镜像构建
├── requirements.txt       # Python依赖
└── README_V2.md        # 项目文档
```

## 🐳 Docker说明

### 服务说明

* **web服务** - 提供Web管理界面
* **task服务** - 执行定时更新任务

### 卷挂载

* `./config.json:/app/config.json` - 配置文件
* `./logs:/app/logs` - 日志目录
* `./tmp:/app/tmp` - 临时文件目录

### 端口

* `8080` - Web服务端口

## 🔐 安全建议

1. 不要在公共网络暴露Web界面
2. 使用强密码保护青龙面板
3. 定期更新依赖版本
4. 启用日志脱敏功能
5. 使用HTTPS代理连接

## 📝 开发指南

### 添加新的验证码类型

1. 在 `utils/captcha_solver.py` 中添加识别逻辑
2. 在 `main_v2.py` 中调用新方法

### 添加新的通知方式

1. 在 `api/send.py` 中添加发送方法
2. 在 `web/models.py` 中添加配置字段

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

* [icepage/AutoUpdateJdCookie](https://github.com/icepage/AutoUpdateJdCookie) - 原项目
* [sml2h3/ddddocr](https://github.com/sml2h3/ddddocr) - OCR识别库
* [zzhjj/svjdck](https://github.com/zzhjj/svjdck) - 参考项目
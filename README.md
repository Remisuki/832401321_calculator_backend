# 算页计算器 · Backend

使用 Python 实现的计算器后端，提供表达式计算、历史持久化、分页查询和指定记录删除接口。支持本地运行及 Windows Server 部署。

[在线演示](http://193.112.23.200:8080/) · [健康检查](http://193.112.23.200:8080/api/health) · [前端仓库](https://github.com/Remisuki/832401321_calculator_frontend) · [接口文档](API.md) · [代码规范](codestyle.md)

## 项目简介

本项目为软件工程课程“前后端分离计算器系统”作业的后端实现。前端通过 HTTP/JSON 提交表达式，后端负责校验、解析、计算和数据库操作，返回统一的结果与错误信息。

作业要求：[First Assignment — Front-End and Back-End Separation Calculator System](https://bbs.csdn.net/topics/620530837)。

## 功能

- 加、减、乘、除，以及括号和运算优先级。
- 十进制小数、一元正号与负号。
- 非法表达式、除零、长度与数值范围校验。
- 成功计算记录的数据库持久化。
- 按 ID 倒序分页查询历史，按指定 ID 删除记录。
- 浏览器来源校验、JSON 错误响应和服务日志。

表达式采用递归下降解析，不使用 `eval`、`exec` 或等效的任意代码执行方式。

## 技术栈与架构

| 模块 | 技术 |
|---|---|
| 编程语言 | Python |
| 公网 API | Flask 3.1.3 |
| Windows HTTP 服务 | Waitress 3.0.2 |
| 计算 | Decimal + 递归下降解析 |
| 当前数据库 | SQLite |
| 测试 | unittest |
| 后台运行 | Windows 计划任务 |

```text
前端浏览器
    │ HTTP / JSON
    ▼
Flask API（wsgi.py）
    ├── calculator.py：校验、解析与计算
    └── storage.py：事务与历史管理
            │
            ▼
          SQLite
```

`windows_server.py` 为 Windows 部署入口，复用 Flask API，并提供前端静态资源和同源配置。`app.py` 为使用标准库实现的本地运行入口。

## 目录结构

```text
.
├── app.py                  # 本地 HTTP 服务
├── calculator.py           # 表达式解析与计算
├── storage.py              # SQLite 存储
├── wsgi.py                 # Flask API 应用工厂
├── windows_server.py       # Windows 部署入口
├── install-windows.ps1     # Windows 首次安装脚本
├── postgres_storage.py     # 可选 PostgreSQL 适配器
├── tests/
│   ├── test_app.py
│   ├── test_cloud.py
│   └── test_postgres_adapter.py
├── API.md                  # 接口协议
├── codestyle.md            # 代码规范
└── README.md
```

## 快速开始

### 环境要求

- 本地基础模式：Python 3.9+，仅使用标准库。
- Windows 部署及完整测试：Python 3.12 或 3.13。
- 前端：配套前端仓库和现代浏览器。

### 获取代码与本地启动

```powershell
git clone https://github.com/Remisuki/832401321_calculator_backend.git
cd 832401321_calculator_backend
python app.py
```

默认监听 `127.0.0.1:5000`。访问 <http://localhost:5000/api/health>，正常响应为：

```json
{"status":"ok"}
```

首次启动会自动创建后端目录下的 `calculator.db` 和数据表，无需手工建库。

在配套前端仓库目录启动静态服务：

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

访问 <http://localhost:5500/>。前端默认连接 `http://localhost:5000/api`。

### 本地配置

`app.py` 读取以下环境变量：

| 变量 | 默认值 | 含义 |
|---|---|---|
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `5000` | 监听端口 |
| `DATABASE_PATH` | 后端目录下的 `calculator.db` | SQLite 文件路径 |
| `ALLOWED_ORIGINS` | `http://localhost:5500,http://127.0.0.1:5500` | 允许的浏览器来源，逗号分隔 |

## Windows Server 部署

### 部署环境

当前在线演示使用腾讯云 Windows Server、Python 3.13、Flask、Waitress 和 SQLite，监听 TCP 8080：

**<http://193.112.23.200:8080/>**

部署目录约定如下：

```text
C:\Calculator\
├── backend\                # 后端仓库内容
├── frontend\               # 前端仓库内容
├── venv\                   # Python 虚拟环境
├── data\calculator.db      # 数据库
├── logs\server.log         # 日志
└── settings.json           # 部署配置
```

### 安装依赖

将两个仓库内容分别放入对应目录，在 `C:\Calculator` 下执行：

```powershell
py -3.13 -m venv venv
& ".\venv\Scripts\python.exe" -m pip install "Flask==3.1.3" "waitress==3.0.2" "psycopg[binary]==3.3.6"
New-Item -ItemType Directory -Path ".\data", ".\logs" -Force | Out-Null
```

使用 Python 3.12 时，将启动器参数改为 `-3.12`。`psycopg` 是当前 API 模块的导入依赖；Windows 入口实际注入 SQLite 存储实现，不需要 PostgreSQL 连接配置。

### 配置与启动

在部署根目录创建 `settings.json`：

```json
{
  "public_origin": "http://193.112.23.200:8080",
  "port": 8080
}
```

`public_origin` 应与实际访问地址的协议、主机和端口一致，不包含路径。迁移部署时需更新该值，并在服务器及云平台网络规则中允许对应端口。

启动服务：

```powershell
& ".\venv\Scripts\python.exe" ".\backend\windows_server.py"
```

该命令在当前终端运行。持续部署可使用 Windows 计划任务；当前演示站的任务名为 `CalculatorHomework`，以 LOCAL SERVICE 账号运行，并配置开机触发。运行账号需要读取程序与 Python 环境，以及写入 data、logs 目录的权限。

针对全新环境，也可使用仓库内的 [install-windows.ps1](install-windows.ps1) 自动安装。脚本支持 `-PublicIp`、`-PythonExe`、`-Port` 参数，需要管理员 PowerShell 5.1+；已有安装使用服务管理方式维护，不重复执行首次安装。

### 前后端连接

Windows 入口动态提供 `/config.js`：

```javascript
window.CALCULATOR_CONFIG = Object.freeze({
  apiBaseUrl: window.location.origin + '/api',
  requestTimeoutMs: 15000
});
```

静态页面和 API 共用公网入口，前端仓库中的本地开发配置不影响这一配置。代码和职责仍按前后端分离，表达式计算全部在后端完成。

### 服务管理

以下命令适用于已注册的 `CalculatorHomework` 任务：

```powershell
# 启动
Start-ScheduledTask -TaskName "CalculatorHomework"

# 状态
Get-ScheduledTask -TaskName "CalculatorHomework" | Format-Table TaskName, State

# 健康检查
Invoke-RestMethod "http://127.0.0.1:8080/api/health"

# 日志
Get-Content "C:\Calculator\logs\server.log" -Tail 50

# 停止
Stop-ScheduledTask -TaskName "CalculatorHomework"
```

数据库保存在代码目录之外。更新代码前应备份数据库；更新 GitHub 文件不会自动同步到服务器。

## API 概览

公网 API 基地址：`http://193.112.23.200:8080/api`。

| 方法 | 路径 | 功能 | 成功状态 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 200 |
| POST | `/calculate` | 计算并保存成功记录 | 201 |
| GET | `/history?limit=5&offset=0` | 分页查询历史 | 200 |
| DELETE | `/history/{id}` | 删除指定记录 | 200 |

计算请求：

```json
{"expression":"(1+2)*3"}
```

成功响应示例：

```json
{
  "success": true,
  "id": 1,
  "expression": "(1+2)*3",
  "result": "9",
  "created_at": "2026-10-02T03:00:00+00:00"
}
```

ID 和时间以实际响应为准。结果使用字符串，避免浏览器再次进行浮点转换。只有计算和数据库提交均成功，接口才返回 201。

错误响应包含 `success`、`code` 和 `message`。常用错误状态包括：输入错误 400、来源不允许 403、记录不存在 404、请求体过大 413、媒体类型错误 415、数据库异常 500。完整协议见 [API.md](API.md)。

## 数据库

启动时通过 `CREATE TABLE IF NOT EXISTS` 自动初始化 `calculation_history` 表：

| 字段 | SQLite 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 记录标识 |
| `expression` | TEXT NOT NULL | 规范化表达式 |
| `result` | TEXT NOT NULL | 十进制结果字符串 |
| `created_at` | TEXT NOT NULL | UTC ISO 8601 时间 |

写操作使用事务和参数化 SQL。历史按 ID 倒序查询，总数和当前页在同一读事务中获取。删除操作检查实际影响行数，不存在的记录返回 404。

## 计算规则与边界

- 语法支持十进制数字、`+ - * / ( )` 和一元正负号；同时接受 `×`、`÷`、`−`。
- 解析层次为 `expression → term → factor`，分别处理加减、乘除和括号/一元运算。
- 表达式最长 200 个字符，递归深度阈值为 40。
- Decimal 精度为 28 位有效数字，数值绝对值上限为 `1e100`。
- 不提供通用代码执行或无限精度计算。
- 计算失败不写入成功历史；保存失败不返回成功结果。

## 测试

仅运行本地基础测试：

```powershell
python -m unittest tests.test_app -v
```

使用 Python 3.12 或 3.13，在后端仓库目录安装完整测试依赖并运行：

```powershell
python -m pip install "Flask==3.1.3" "psycopg[binary]==3.3.6" "waitress==3.0.2"
python -m unittest discover -s tests -v
```

测试覆盖表达式计算、HTTP 输入校验、错误响应、分页与删除、历史保留、来源限制和存储适配器边界。测试使用临时数据库；PostgreSQL 适配器测试使用替身连接，不要求外部 PostgreSQL 服务。

功能验收示例：

| 输入或操作 | 预期结果 |
|---|---|
| `1+2*3` | `7` |
| `(1+2)*3` | `9` |
| `3*-2` | `-6` |
| `0.1+0.2` | `0.3` |
| `1/0`、`1+` | 400 错误响应 |
| 新浏览器会话读取历史 | 已保存记录仍可查询 |
| 删除后重新查询 | 目标记录不存在 |

健康检查不替代数据库读写验收。实际部署还需验证公网访问、后台运行及进程重启后的历史保留。

## 项目范围

当前版本是匿名课程演示，访问者共享历史记录，未提供账号鉴权、个人历史隔离或 HTTPS。浏览器来源校验不等于身份认证。数据库、日志、虚拟环境及私密配置不提交到仓库。

代码规范及来源见 [codestyle.md](codestyle.md)。仓库保留的 PostgreSQL 与其他平台部署材料属于可选方案，当前在线实例以本 README 描述的 Windows + SQLite 配置为准。

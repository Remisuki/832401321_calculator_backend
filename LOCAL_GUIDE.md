# 算页 · 计算器后端

软件工程作业的独立后端：接收表达式，在服务器完成校验、解析和计算，将每次成功计算存入 SQLite，再返回 JSON。支持读取与删除历史记录。

## 1. 技术栈与当前状态

- Python 标准库：`http.server`、`decimal`、`sqlite3`、`json`、`unittest`。
- 自行实现受限数学表达式解析器；没有 eval、exec 或任意代码执行。
- 无第三方运行依赖，SQLite 也随 Python 提供，无需单独安装数据库。
- 运行环境：Python 3.9+；本机验证使用 Python 3.9.13。新安装建议使用仍受维护的 Python 3.11 或更高版本。
- 当前是可本地运行的教学版本，**不是 Flask 应用，也没有 PostgreSQL/Neon 适配**。
- 本仓库没有已部署公网地址；环境变量配置不代表已经完成公网部署。

## 2. 功能与输入规则

| 项目 | 规则 |
|---|---|
| 基本运算 | +、-、*、/；输入 ×、÷、− 时自动规范化 |
| 优先级 | 先乘除后加减，同级从左到右；括号优先 |
| 正负号 | 支持 -5、+5、3*-2、-(2+3) |
| 小数 | 支持 1.5、.5、1.；0.1+0.2 返回 0.3 |
| 精度 | Decimal 算术采用 28 位有效数字；循环小数会舍入 |
| 长度 | 去除首尾空白后最多 200 个字符 |
| 嵌套 | 括号和一元正负号的递归深度最多 40 层 |
| 数值范围 | 字面量及中间计算值的绝对值不得超过 10^100 |
| 不支持 | 幂、取模、科学计数输入、变量、函数调用、隐式乘法，如 2(3) |
| 成功记录 | 保存表达式、结果、UTC 时间及自增 ID |
| 历史读取 | 时间顺序由递增 ID 倒序体现，支持 limit / offset 分页 |
| 删除 | 删除指定 ID，实际删除数据库行 |

只保存成功计算。非法表达式、除零或超限返回错误，不能生成一条“成功历史”。

## 3. 目录结构

```text
backend/
├── app.py           HTTP 路由、JSON、校验、跨域和启动配置
├── calculator.py    分词、递归下降解析、Decimal 运算
├── storage.py       SQLite 初始化与增删查
├── requirements.txt 无第三方依赖的说明
├── start.bat        Windows 启动脚本
├── tests/
│   └── test_app.py  计算与真实 HTTP 接口测试
├── README.md
├── API.md           完整接口说明及示例
├── codestyle.md
└── .gitignore
```

首次启动会自动创建 `calculator.db`。它是本机数据，不应随源码上传。初版数据库表结构保持兼容，更新不会清空原有记录。

## 4. 安装与启动

先执行 `python --version` 确认 Python 可用。不需要 pip install。

### Windows 文件资源管理器

打开本文件所在的 backend 文件夹，双击 `start.bat`。聊天或编辑器中看到 bat 内容只是预览，不等于运行。

### 终端

在 backend 文件夹中运行：

```powershell
python app.py
```

默认输出：

```text
Calculator backend running at http://127.0.0.1:5000
```

打开 <http://localhost:5000/api/health>，应看到 `{"status":"ok"}`。

访问根路径 / 返回 404 是正常的：此服务只提供 /api 下的接口，计算器页面由前端服务提供。按 Ctrl+C 停止后端。修改 Python 文件后需要重新启动程序。

## 5. 数据库初始化与持久化

启动时自动执行 `CREATE TABLE IF NOT EXISTS`，无需手工建表。

| 字段 | SQLite 类型 | 用途 |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 指定记录的唯一标识 |
| expression | TEXT NOT NULL | 输入表达式；×、÷ 会转换为 *、/ |
| result | TEXT NOT NULL | 十进制结果，避免浮点转换 |
| created_at | TEXT NOT NULL | 带 UTC 时区的 ISO 8601 时间 |

每次操作使用独立连接、参数化 SQL、事务和显式关闭连接。网页刷新或后端重启不会删除数据库文件。

**备份方法：**先停止后端，再复制 calculator.db。不要删除这个文件来“更新代码”。自动化测试使用临时数据库，与此文件隔离。

## 6. 配置

通过启动进程的环境变量配置，不自动读取 .env 文件。

| 变量 | 默认值 | 含义 |
|---|---|---|
| HOST | 127.0.0.1 | 监听地址；仅本机 |
| PORT | 5000 | 后端端口 |
| DATABASE_PATH | app.py 同目录下 calculator.db | SQLite 文件位置 |
| ALLOWED_ORIGINS | http://localhost:5500,http://127.0.0.1:5500 | 允许的浏览器来源，用英文逗号分隔 |

Windows PowerShell 示例（自定义端口后，前端 config.js 也要同步修改）：

```powershell
$env:PORT = "5001"
$env:DATABASE_PATH = "D:\calculator-data\calculator.db"
$env:ALLOWED_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"
python app.py
```

数据库父目录会自动创建，但运行账号必须有写入权限。相对 DATABASE_PATH 按启动时的当前目录解析，建议使用绝对路径。

ALLOWED_ORIGINS 填“协议 + 域名 + 可选端口”，不要带末尾斜杠或网页路径。不支持 * 通配符。上线时加入实际 HTTPS 前端来源；从 file:// 打开的页面来源不在默认允许列表中。

跨域来源检查不是登录或身份验证。命令行客户端不受浏览器跨域机制约束，当前版本没有用户账号，历史对所有访问者共享。

## 7. API 概览

| 方法 | 地址 | 成功状态 |
|---|---|---|
| GET | /api/health | 200 |
| POST | /api/calculate | 201 |
| GET | /api/history?limit=10&offset=0 | 200 |
| DELETE | /api/history/{id} | 200 |
| OPTIONS | 已存在的 API 路径 | 204，空响应体 |

[查看完整接口说明](API.md)。

计算示例：

```json
{"expression":"(1+2)*3"}
```

成功响应中的 result 是字符串：

```json
{
  "success": true,
  "id": 1,
  "expression": "(1+2)*3",
  "result": "9",
  "created_at": "2026-09-23T12:00:00+00:00"
}
```

时间和 ID 仅为格式示例，以实际响应为准。错误统一返回 success、code、message。

**与初版的变化：**result 从数值改为十进制字符串；历史接口从数组改为包含 records、total、limit、offset 的对象。前后端必须成套更新，但原有 SQLite 数据无需迁移。

## 8. 测试

在 backend 文件夹执行：

```powershell
python -m unittest discover -s tests -v
```

覆盖四则运算、优先级、括号、一元正负号、小数精度、恶意或非法输入、除零、长度限制、JSON 校验、跨域预检、数据库保存、指定删除、分页、重启持久化和旧数据兼容。

测试在临时目录创建自己的数据库和随机端口，不使用你的 5000 端口，不改动个人历史。

使用 PowerShell 手动测试：

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/calculate" -Method Post -ContentType "application/json" -Body '{"expression":"0.1+0.2"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/history?limit=5&offset=0"
```

预期计算结果为字符串 0.3。除零测试将返回 HTTP 400，这是正确的异常响应。

## 9. 设计说明

计算器采用以下语法层次：

```text
expression = term { ("+" | "-") term }
term       = factor { ("*" | "/") factor }
factor     = 数字 | ("+" | "-") factor | "(" expression ")"
```

先通过受限分词读取数字和运算符，再按层次解析。括号通过递归处理，一元负号作用于其后的 factor。Decimal 直接从数字文本创建，不经过 float。

请求流程：

```text
前端发送表达式
→ app.py 校验 JSON
→ calculator.py 解析并计算
→ storage.py 提交数据库事务
→ 后端返回结果
→ 前端展示并重新查询历史
```

保存失败时返回 500，不宣称计算记录已成功保存。历史数据展示应由前端使用 textContent 等安全方式完成。

## 10. 公网部署限制

当前 http.server 用于本地教学演示，不应直接作为正式公网生产服务器。此前讨论过的 gunicorn app:app 命令不能用于当前版本，因为这里没有 Flask/WSGI app 对象。

正式部署前需选择以下路线之一并完成对应适配：

- 保留 SQLite：后端必须有持久化磁盘；把 DATABASE_PATH 指向挂载目录，配合正式服务器/反向代理、HTTPS、进程管理和备份。
- 免费临时磁盘平台：需要改用独立数据库，例如 PostgreSQL/Neon，并修改存储代码、依赖、初始化方式及正式启动配置。

仅配置 HOST、PORT、DATABASE_PATH 不会自动完成上述适配。不要将当前 SQLite 数据库放在 Render 免费服务的临时目录，重启/重新部署后可能丢失。不要将 DATABASE_URL 填入此版本后期待连接 PostgreSQL：当前代码不读取它。

部署后验证外部设备可访问、错误处理正常、后端重启后历史保留，并在评测期间维持服务可用。线上前端需使用真实 HTTPS API 地址。

## 11. 常见问题与提交文件

- 找不到 python：安装 Python 或检查 PATH；Windows 可尝试 py -3。
- Address already in use / WinError 10048：5000 端口已有程序；关闭自己之前启动的旧后端后重试。
- 页面仍是旧版本：重启后端，同时前端 Ctrl+F5。
- HTTP 403：检查 ALLOWED_ORIGINS 是否包含真实前端来源。
- 数据库无法写入：确认 DATABASE_PATH 所在目录有写权限。
- 更换数据库路径后看不到旧历史：新路径对应另一份数据库；原文件不会自动搬迁。

上传时必须包含 app.py、calculator.py、storage.py、requirements.txt、tests、start.bat、README.md、API.md、codestyle.md、.gitignore。不要只上传旧清单中的 app.py。

不要上传 calculator.db、__pycache__、虚拟环境或私密配置。.gitignore 仅对 Git 操作生效；GitHub 网页拖拽上传需要自己排除这些文件。

# 算页计算器后端

软件工程第一次作业后端。服务接收表达式，完成校验、安全解析和 Decimal 运算，将成功结果保存到 SQLite，并提供历史分页查询和按 ID 删除接口。前端不计算最终结果。

- 在线演示：<http://193.112.23.200:8080/>
- 健康检查：<http://193.112.23.200:8080/api/health>
- 前端仓库：<https://github.com/Remisuki/832401321_calculator_frontend>
- 文档：[API.md](API.md) · [codestyle.md](codestyle.md)
- 作业要求：<https://bbs.csdn.net/topics/620530837>

## 当前运行环境

| 项目 | 当前方案 |
|---|---|
| 服务器 | 腾讯云 Windows Server |
| Python | 3.13；安装脚本兼容 3.12 / 3.13 |
| HTTP 服务 | Flask 3.1.3 + Waitress 3.0.2 |
| 数据库 | SQLite，`C:\Calculator\data\calculator.db` |
| 监听地址 | `0.0.0.0:8080` |
| 公网入口 | `http://193.112.23.200:8080/` |
| 后台运行 | Windows 计划任务 `CalculatorHomework`，LOCAL SERVICE 账号 |

当前入口不使用 Render、Neon 或 Gunicorn。`postgres_storage.py`、`requirements-cloud.txt` 和旧 `DEPLOY.md` 保留了此前可选平台方案，不用于本次 Windows 部署。由于 `wsgi.py` 仍导入 PostgreSQL 适配器，Windows 安装依赖中保留 `psycopg[binary]==3.3.6`；实际存储通过 `STORAGE=storage` 切换到 SQLite，不需要 PostgreSQL 账号或连接串。

## 功能与目录

支持 `+ - * /`、`× ÷`、括号、一元正负号及十进制小数。采用递归下降解析，不使用 `eval`、`exec` 或任意代码执行。最大表达式长度为 200；递归深度阈值为 40；数值绝对值上限为 `1e100`；Decimal 精度为 28 位有效数字，不是无限精度计算。

```text
calculator.py          词法分析、优先级、一元运算和 Decimal 计算
storage.py             SQLite 初始化、事务、历史增删查
wsgi.py                Flask API、输入和来源校验、错误响应
windows_server.py      当前 Windows 入口、静态页面、同源配置、日志
install-windows.ps1    首次安装：下载、依赖、权限、测试、防火墙、计划任务
app.py / start.bat     本地学习用 HTTP 服务
postgres_storage.py    旧方案的 PostgreSQL 适配器
tests/                 计算、HTTP 和存储适配器测试
API.md / codestyle.md  接口说明与代码规范
```

## 本地运行

本地教学模式使用 Python 3.9+ 标准库，无需安装 Flask：

```powershell
python app.py
```

默认监听 `127.0.0.1:5000`，数据库位于后端仓库的 `calculator.db`。首次启动自动建表。环境变量 `HOST`、`PORT`、`DATABASE_PATH`、`ALLOWED_ORIGINS` 可覆盖默认值；默认允许 `http://localhost:5500` 和 `http://127.0.0.1:5500`。

随后在前端目录运行 `python -m http.server 5500 --bind 127.0.0.1`，打开 <http://localhost:5500/>。更详细的本地操作见 [LOCAL_GUIDE.md](LOCAL_GUIDE.md)。

## Windows 公网首次安装

已有 `C:\Calculator` 的服务器不要重复运行首次安装脚本。正常启动、停止和重启使用后文的计划任务命令。

1. 准备 Windows Server、管理员 PowerShell 5.1+、Python 3.12 或 3.13；在腾讯云防火墙/安全组允许入站 TCP 8080。是否有其他网站或备案要求，按实际服务器地域与云平台要求确认。
2. 运行 `py -0p` 确认实际 Python 路径。下方使用本次服务器的路径；迁移到新机器时需按实际修改。
3. 确认 8080 没有其他监听程序，且 Windows 防火墙服务可用。标准脚本会添加 Windows 防火墙规则；若服务被禁用，应先由服务器管理员确认策略，不要盲目启停系统服务或重装。
4. 在服务器管理员 PowerShell 中执行：

```powershell
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Path "C:\CalculatorSetup" -Force | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/Remisuki/832401321_calculator_backend/main/install-windows.ps1" -OutFile "C:\CalculatorSetup\install-windows.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\CalculatorSetup\install-windows.ps1" -PublicIp "193.112.23.200" -PythonExe "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe" -Port 8080
```

安装脚本下载两个仓库的 main 分支，创建独立虚拟环境，安装 Flask、Waitress、psycopg，配置文件权限，执行测试，然后配置后台计划任务和本机健康检查。LOCAL SERVICE 对程序有读取权限，对 data/logs 有修改权限。

本次服务器原有 Nginx 占用 80，所以使用 8080。安装在防火墙阶段遇到错误 1753，经查询确认 `MpsSvc` 已被禁用；保留既有服务策略，用恢复脚本完成剩余计划任务步骤后恢复运行。这是本次机器的实际处置记录，不表示首次安装脚本可以忽略所有防火墙错误。

## 配置、前后端连接与数据库初始化

```text
C:\Calculator\
├── backend\
├── frontend\
├── venv\
├── data\calculator.db
├── logs\server.log
└── settings.json
```

当前 `settings.json` 内容：

```json
{
  "public_origin": "http://193.112.23.200:8080",
  "port": 8080
}
```

`public_origin` 是协议、IP 和端口，不包含路径。修改 IP/端口时同步更新此配置及云防火墙/系统防火墙规则，再重启计划任务。来源校验不是用户认证。

`windows_server.py` 从上级部署目录读取配置，提供首页和允许的静态文件，并动态返回 `/config.js`，让前端使用 `window.location.origin + '/api'`，超时为 15 秒。仓库中的前端 `config.js` 仍可保留本地开发地址。

首次启动执行 `CREATE TABLE IF NOT EXISTS`，不需要手工建库或 MySQL 服务。数据库表为 `calculation_history`：

| 字段 | SQLite 类型 | 含义 |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 记录标识 |
| expression | TEXT NOT NULL | 规范化后的表达式 |
| result | TEXT NOT NULL | 十进制结果字符串 |
| created_at | TEXT NOT NULL | UTC ISO 8601 时间 |

结果使用文本保存与返回，避免前端再次转换浮点数。插入和删除使用参数绑定与事务；分页按 ID 倒序。数据库保存在代码目录之外，普通进程重启不会主动清空历史；删除服务器磁盘或数据库文件仍会丢失数据。修改部署前应备份数据库，不能用“重装”代替排错。

## 后台启动、停止与排错

下列命令在服务器管理员 PowerShell 执行：

```powershell
# 启动已注册的任务
Start-ScheduledTask -TaskName "CalculatorHomework"

# 查看状态与接口
Get-ScheduledTask -TaskName "CalculatorHomework" | Format-Table TaskName, State
Invoke-RestMethod "http://127.0.0.1:8080/api/health"

# 查看日志
Get-Content "C:\Calculator\logs\server.log" -Tail 50
```

停止服务：

```powershell
Stop-ScheduledTask -TaskName "CalculatorHomework"
```

需要重启时，在停止后确认 8080 监听已退出，再启动任务：

```powershell
Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "CalculatorHomework"
```

计划任务配置了开机触发与失败重试，退出远程桌面不等于关闭服务器。修改 GitHub 不会自动更新服务器代码；本次仅更新文档时无需重启服务。

| 问题 | 排查重点 |
|---|---|
| 找不到 Python | 用 `py -0p` 确认路径，并传入 `-PythonExe` |
| 端口被占用 | 检查占用程序；通过 `-Port` 选择空闲端口，不随意结束其他服务 |
| 防火墙 1753 | 查询 `BFE`、`MpsSvc`、`RpcSs`；保留安装目录，定位服务状态 |
| 计划任务未运行 | 用 `Get-ScheduledTaskInfo` 查看结果，并查看 `server.log` 与 Python/数据库目录权限 |
| 本机成功，公网失败 | 核对腾讯云入站 TCP 8080、系统防火墙、访问地址中的端口 |
| 403 | `public_origin` 必须与访问网页的实际来源一致 |

## API

| 方法 | 路径 | 正常响应 |
|---|---|---|
| GET | `/api/health` | 200，`{"status":"ok"}` |
| POST | `/api/calculate` | 201，成功记录 |
| GET | `/api/history?limit=5&offset=0` | 200，records/total/limit/offset |
| DELETE | `/api/history/{id}` | 200，`{"success":true}` |

请求示例：`{"expression":"(1+2)*3"}`。成功返回 `success`、`id`、`expression`、字符串 `result` 与 `created_at`。非法表达式或除零返回 400；错误来源 403；不存在的记录 404；请求过大 413；错误媒体类型 415；数据库异常 500。完整字段见 [API.md](API.md)；当前公网 API 基地址为 `http://193.112.23.200:8080/api`。

只有计算和数据库提交都成功才返回 201。请求超时不等于保存失败，应先查询历史，再决定是否重新提交。

## 测试及验证范围

本地基础测试：

```powershell
python -m unittest tests.test_app -v
```

Windows 公网环境中运行全部测试：

```powershell
Set-Location "C:\Calculator\backend"
& "C:\Calculator\venv\Scripts\python.exe" -m unittest discover -s tests -v
```

新建 Windows 测试环境时安装 `Flask==3.1.3`、`psycopg[binary]==3.3.6`、`waitress==3.0.2`。不要在 Windows 上照搬旧文档的 Gunicorn 启动命令。

- 部署终端显示 40 项测试通过，以及 Windows 入口检查通过；这发生在后续防火墙步骤报错之前。
- 2026-10-02 公网浏览器验证通过：四则运算、小数、括号、优先级、正负号、非法输入、除零、重新打开浏览器后的历史、指定删除及刷新、分页、接口请求不可达时不产生新结果和手机布局。
- 本地隔离环境验证了 Waitress 进程实际重启后的历史保留。公网验收没有重启远程服务器，也没有连接真实 PostgreSQL；不能将这两项写成已完成的云端测试。

测试使用隔离数据，公网截图验证只删除本次创建的测试记录。`/api/health` 成功只能证明接口响应，不能代替数据库读写和删除验证。

## 项目边界

该版本是匿名课程演示，所有访问者共用历史，未提供账号、个人历史隔离、科学计算或 HTTPS。数据库、日志、虚拟环境和私密配置不上传到 GitHub。代码规范及来源见 [codestyle.md](codestyle.md)。评阅期间应保持服务可访问，并关注课程公告。

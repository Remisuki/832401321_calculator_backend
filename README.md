# 算页计算器后端

软件工程作业后端：在服务器校验、解析并计算表达式，将成功记录保存到数据库，支持分页查询和按 ID 删除。前端不计算结果。

前端仓库：https://github.com/Remisuki/832401321_calculator_frontend

## 选择运行方式

| 场景 | 入口 | 数据库 | 依赖 |
|---|---|---|---|
| 本地学习与演示 | python app.py / start.bat | SQLite | Python 3.9+ 标准库 |
| 免费公网部署 | wsgi:create_app() | Neon / PostgreSQL | Python 3.12，requirements-cloud.txt |

**第一次部署请从 [DEPLOY.md](DEPLOY.md) 开始。**原本详细的本地运行说明保存在 [LOCAL_GUIDE.md](LOCAL_GUIDE.md)，其中的公网限制专指旧的 app.py 入口。

## 功能与结构

计算支持加减乘除、括号、优先级、正负号、小数；使用递归下降解析和 Decimal，不使用 eval / exec。错误表达式和除零不会产生成功记录。

```text
app.py                     本地 HTTP 入口
calculator.py              两种模式共用的计算逻辑
storage.py                 SQLite 存储
wsgi.py                    Flask 云端 API / 应用工厂
postgres_storage.py        云端 PostgreSQL 存储
requirements.txt           本地模式无第三方依赖
requirements-cloud.txt     云端依赖与版本
.python-version            Render 使用 Python 3.12 系列
.env.example               配置示例，不会被程序自动加载
start.bat                  Windows 本地启动
tests/
  __init__.py
  test_app.py               原有计算及 HTTP 测试
  test_cloud.py             云端 API 的本地 HTTP 测试
  test_postgres_adapter.py  PostgreSQL 适配器边界测试
API.md / DEPLOY.md / LOCAL_GUIDE.md / codestyle.md
```

## 本地启动

在本仓库根目录运行 `python app.py`，或双击 start.bat。浏览器打开 http://localhost:5000/api/health ，应显示 `{"status":"ok"}`。本地配置和数据结构详见 LOCAL_GUIDE.md。

## Render 免费部署配置

Root Directory 留空；选择 Python 3、main 分支和 Free 实例；Health Check Path 为 `/api/health`。

Build Command：

```bash
pip install -r requirements-cloud.txt
```

Start Command：

```bash
gunicorn "wsgi:create_app()" --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

| 环境变量 | 值 |
|---|---|
| DATABASE_URL | Neon Connect 中的真实 PostgreSQL URI，保留 SSL 参数 |
| ALLOWED_ORIGINS | https://remisuki.github.io |

数据库 URI 含密码，只填平台环境变量，不放进 GitHub 或前端。首次启动自动建表；重新部署不会主动清空表。本地 SQLite 与 Neon 是两套数据库，本地旧历史不会自动迁移。

Render Free 会休眠且本地磁盘不持久化；Neon Free 有额度限制。该模式使用独立数据库保存历史，详细限制、官方来源及实际部署验证见 DEPLOY.md。

## 接口与数据流程

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /api/health | API 进程健康检查 |
| POST | /api/calculate | 计算并提交历史，成功返回 201 |
| GET | /api/history?limit=5&offset=0 | 查询分页历史 |
| DELETE | /api/history/{id} | 删除指定记录 |

请求示例为 `{"expression":"(1+2)*3"}`；result 按十进制字符串返回。完整协议见 [API.md](API.md)。

```text
前端请求 → app.py（本地）或 wsgi.py（云端）
         → calculator.py 校验与计算
         → storage.py / postgres_storage.py 提交数据库事务
         → 返回成功结果，前端重新查询历史
```

calculation_history 包含 id、expression、result、created_at。id 自动生成，其他三项为文本；时间使用 UTC ISO 8601。SQL 通过参数传值，写入失败返回错误；读取分页使用一致的数据库快照。

## 测试与验证边界

只验证本地模式：

```powershell
python -m unittest tests.test_app -v
```

使用 Python 3.12 验证全部测试：

```powershell
python -m pip install -r requirements-cloud.txt
python -m unittest discover -s tests -v
```

本次准备版本的 40 项测试在 Python 3.12.14 / Windows 下通过：原有测试 21 项、云端 HTTP 测试 16 项、PostgreSQL 适配器边界测试 3 项。

云端 HTTP 测试使用临时 SQLite 和真实本地 HTTP，适配器测试使用替身连接。**没有连接真实 Neon，也未在本机运行 Linux Gunicorn。**仍须完成 DEPLOY.md 的公网访问、实际数据库写入、删除及重启保存检查。/api/health 不能代替数据库读写检查。

未安装云依赖时云测试会明确跳过，原有本地测试仍可运行。测试不使用个人计算历史数据库。

## 规范与边界

代码规范见 [codestyle.md](codestyle.md)。本版本是匿名课程演示，所有访问者共享历史，没有用户隔离。公开演示只使用普通计算表达式。

Gunicorn 在 Render Linux 环境运行；Windows 本地使用 python app.py。LOCAL_GUIDE.md 中“无第三方依赖”的表述仅指这个本地入口。


# 免费公网部署教程：把你的计算器放到网上

适用仓库：

- 前端：https://github.com/Remisuki/832401321_calculator_frontend
- 后端：https://github.com/Remisuki/832401321_calculator_backend

这份教程按“没有服务器、尽量免费、第一次部署”编写。配套源码已经准备好；你需要完成账号注册、连接自己的 GitHub 仓库和填写配置。**文件准备好不等于网站已经上线，最后一定要做第 6 步的公网验证。**

## 先认识三个地方

| 平台 | 简单理解 | 在这个作业里的作用 |
|---|---|---|
| GitHub Pages | 存放网页的地方 | 展示计算器按钮和历史列表 |
| Render | 一台由平台管理的电脑 | 运行 Python 后端，实际计算结果 |
| Neon | 放在网上的数据库 | 保存计算历史，后端重启后仍能读取 |

网页访问关系：浏览器 → GitHub Pages 页面 → Render 后端 → Neon 数据库。

Render 的 Free 服务闲置 15 分钟后会休眠，再次打开通常需要约一分钟唤醒；它的本地文件系统不持久化。因此这套免费方案把历史记录放进独立的 Neon 数据库。Neon Free 也有计算、存储和流量额度，这不是无限资源或永远在线的保证。[Render 官方说明](https://render.com/docs/free) · [Neon 免费额度说明](https://neon.com/docs/introduction/plans)

## 第 1 步：把这次准备的部署版本上传到原来的两个仓库

配套文件名：`calculator-backend-cloud.zip` 和 `calculator-frontend-cloud.zip`。这次是支持云部署的版本，不要拿先前只有本地运行入口的旧包替代。

1. 下载两个压缩包，分别右键 → “全部解压”。
2. 打开解压后的后端目录，应该直接能看到 `app.py`、`wsgi.py`、`postgres_storage.py` 等文件。
3. 打开 GitHub 后端仓库，点击 **Add file → Upload files**。
4. 把目录里的文件，以及整个 `tests` 文件夹，拖进上传区域。**拖进去的是包内的内容，不是 ZIP，也不是外面多包一层的目录。**
5. 有同名文件时，这次提交会更新该文件；填写提交说明“增加免费云部署支持”，点击 **Commit changes**。
6. 前端也用相同方式上传前端包内的文件。`config.js` 暂时仍指向 localhost，第 4 步获得真实后端网址后再修改。

后端根目录至少应能看到这些部署关键文件：

```text
app.py                     本地运行入口
calculator.py              原有计算逻辑
storage.py                 本地 SQLite 存储
wsgi.py                    新增：公网接口入口
postgres_storage.py        新增：Neon / PostgreSQL 存储
requirements-cloud.txt     新增：云端依赖
.python-version            新增：Render 使用 Python 3.12 系列
README.md
DEPLOY.md
API.md
codestyle.md
tests/                     测试文件夹，要保留这一层
```

如果最外层还残留之前误上传的 `test_app.py` 或 `__init__.py`，确认 `tests/` 里已有对应文件后，可以删除最外层重复文件。`.gitignore`、`.python-version` 的开头都有一个点，不要给它们额外加 `.txt`。

**完成标志：**在 GitHub 后端仓库最外层能够点开 `wsgi.py` 和 `requirements-cloud.txt`，点开 `tests` 后能看到测试文件。

## 第 2 步：在 Neon 创建免费数据库

1. 打开 https://neon.com ，点击 **Sign up** 注册；如果提供 GitHub 登录，可以使用你的 GitHub 账号。
2. 进入控制台，创建一个项目（界面可能写 **New project** 或 **Create project**）。
3. 项目名称可以填 `calculator-homework`。选择 **Free** 计划，PostgreSQL 版本使用默认值。区域可选与后端相近的区域；不确定时先保留默认值。
4. 创建完成后，点击项目里的 **Connect**。
5. 保留面板默认选中的分支、数据库和角色，找到 **Connection string**（连接字符串），复制完整内容。连接池开关可以保持默认。

它的形状大致是：

```text
postgresql://用户名:密码@数据库地址/数据库名?sslmode=require&channel_binding=require
```

上面只是格式示意，**不能直接复制示意文字作为真实配置**。你需要 Neon 面板中为你的项目生成的真实字符串。如果复制内容形如 `psql 'postgresql://…'`，只保留 `postgresql://…` 的那一段，不要 `psql` 和两侧引号。保留后面的 SSL 参数。

**这段字符串包含数据库密码，只粘贴到下一步的 Render 环境变量中。不要放进 GitHub 文件、前端 config.js、博客或截图，也不需要发给我。**

不需要手动建表，后端首次启动时会创建 `calculation_history` 表。[Neon 官方连接说明](https://neon.com/docs/connect/connect-from-any-app)

**完成标志：**你已经创建一个 Free 项目，并找到了真实数据库连接字符串。

## 第 3 步：在 Render 部署后端

1. 打开 https://render.com ，注册并登录。
2. 进入控制台，点击 **New + → Web Service**。
3. 按提示连接 GitHub，选择 `Remisuki/832401321_calculator_backend`。如果仓库没有出现，进入 GitHub 授权配置，将这个后端仓库加入 Render 可访问的仓库列表。
4. 创建服务时填写下面这些字段。若界面顺序稍有变化，以字段名称为准。

| 字段 | 填什么 |
|---|---|
| Name | `calculator-832401321`，如重名则在后面加几个数字 |
| Language / Runtime | `Python 3` |
| Branch | `main` |
| Region | 选择与 Neon 相近的可选区域；不确定可保留默认 |
| Root Directory | **留空**；这个仓库最外层已经是后端，不要填 `backend` |
| Build Command | `pip install -r requirements-cloud.txt` |
| Start Command | 复制下一段完整命令 |
| Instance Type | **Free** |
| Health Check Path | 如果显示这个选项，填 `/api/health` |

**Start Command：**

```bash
gunicorn "wsgi:create_app()" --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

这里的引号、括号、冒号和 `$PORT` 都保留。不要改成 `python app.py` 或 `gunicorn app:app`，这两个不是本教程的云端入口。

5. 找到 **Environment Variables**，添加下面两个变量。若创建页没有展开，通常可通过 **Advanced** 找到；创建后也可在服务的 **Environment** 中修改并重新部署。

| Key（左边） | Value（右边） |
|---|---|
| `DATABASE_URL` | 第 2 步从 Neon 复制的真实连接字符串 |
| `ALLOWED_ORIGINS` | `https://remisuki.github.io` |

`ALLOWED_ORIGINS` 只填上面的域名，**不要加前端仓库路径，也不要加 `/api`**。项目中的 `.python-version` 已配置版本，不需要另填 `PYTHON_VERSION`。本地的 `.env.example` 只是示例，不会自动替你设置这些变量。

6. 确认实例类型是 **Free** 后，点击 **Create Web Service / Deploy Web Service**。
7. 等待部署日志结束，服务显示 **Live** 后，找到平台实际分配的 HTTPS 地址，通常形如 `https://某个名字.onrender.com`，复制这个真实地址。

Render 的官方 Flask 教程说明了创建服务、构建命令及使用 Gunicorn 的流程；上面的启动入口是按本项目定制的。[Render 文档](https://render.com/docs/deploy-flask) · [Flask 工厂函数启动说明](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/) · [Python 版本配置](https://render.com/docs/python-version)

**完成标志：**Render 服务显示 Live，并给你一个实际的 `https://…onrender.com` 地址。

## 第 4 步：确认后端能打开，再修改前端接口地址

假设 Render 分配的实际地址是 `https://你的服务名.onrender.com`，在浏览器地址栏打开它后面加 `/api/health` 的地址：

```text
https://你的服务名.onrender.com/api/health
```

用你的真实服务名替换示例。正确结果是：

```json
{"status":"ok"}
```

首次访问如果出现平台唤醒页面，先等约一分钟。只有看到上面的结果，再往下操作。

接着打开 GitHub 的**前端仓库** → `config.js` → 铅笔编辑按钮，将文件改成：

```javascript
window.CALCULATOR_CONFIG = Object.freeze({
  apiBaseUrl: "https://你的真实Render服务名.onrender.com/api",
  requestTimeoutMs: 90000,
});
```

这里也要换成真实域名，而且结尾保留 **`/api`**。`90000` 是等待 90 秒，为免费服务唤醒留出时间。保存并提交更改。

**完成标志：**后端健康地址显示 `ok`，前端 `config.js` 已经不再使用 localhost。

## 第 5 步：用 GitHub Pages 发布前端

1. 打开前端仓库 `832401321_calculator_frontend`。
2. 点击仓库顶部 **Settings**，再点击左侧 **Pages**。
3. 在 **Build and deployment** 中，将 **Source** 设为 **Deploy from a branch**。
4. **Branch** 选择 `main`，文件夹选择 **`/ (root)`**，点击 **Save**。
5. 等待发布完成。可以查看仓库 **Actions** 中的 Pages 发布任务；成功后 Pages 页面会出现网站地址。发布可能需要几分钟，GitHub 提醒有时可达 10 分钟。

在没有配置自定义域名的情况下，你的项目页面预计是：

```text
https://remisuki.github.io/832401321_calculator_frontend/
```

以 Settings → Pages 显示的实际地址为准。**GitHub 仓库地址和这个网页地址不一样**：仓库用来看源码，Pages 地址才是给老师操作计算器的入口。页面最外层应有 `index.html`，不要多套一层 frontend 文件夹。

[GitHub Pages 发布来源设置](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

**完成标志：**浏览器打开 Pages 网址后，能看到计算器界面。

## 第 6 步：证明它确实可以在公网使用

先关闭电脑上原来运行的本地后端，再用手机关闭 Wi-Fi、改用手机流量打开 Pages 网址。闲置后的第一次访问给免费后端留出唤醒时间。

按顺序检查：

| 操作 | 预期结果 |
|---|---|
| 输入 `1+2*3` | 显示 `7` |
| 输入 `(1+2)*3` | 显示 `9` |
| 输入 `-(2+3)` | 显示 `-5` |
| 输入 `0.1+0.2` | 显示 `0.3` |
| 输入 `1/0` | 显示错误提示，不新增成功历史 |
| 刷新网页 | 成功计算的历史仍在 |
| 删除指定记录，再刷新 | 被删除的那条记录不再出现 |

再做一次**后端重启后的保存检查**：先留下一条容易辨认的历史，例如 `123+456 = 579`；在 Render 服务页面通过 **Manual Deploy → Deploy latest commit** 重新部署同一份代码；等 Live 后重新打开页面，确认这条历史仍在。这个过程验证历史在 Neon 中，而不是存在 Render 的临时文件里。

最后可进入 Neon 项目中的 **Tables** 查看 `calculation_history`，确认记录实际存入数据库。线上 Neon 历史初始为空是正常的，本地 SQLite 的旧记录不会自动搬过去。

该作业版本没有登录功能，线上访问者共享历史列表；展示时使用普通计算表达式即可。

## 常见卡点：先看这里

| 现象 | 优先检查 |
|---|---|
| Render 提示找不到 requirements-cloud.txt | 是否上传了本次部署包；Root Directory 是否留空 |
| 日志显示找不到 wsgi 或 create_app | wsgi.py 是否位于仓库最外层；Start Command 是否完整复制 |
| 日志提示 Set DATABASE_URL | 环境变量名称是否全大写，值是否漏填 |
| 数据库连接或密码错误 | 从 Neon Connect 重新复制真实 URI；不要带 psql 和外侧引号；保留 SSL 参数 |
| 打开后端根网址是 404 | 测试地址需要加 `/api/health`，根路径 404 不代表整个服务没启动 |
| 网页提示来源不允许 / HTTP 403 | Render 中 ALLOWED_ORIGINS 应为 `https://remisuki.github.io`，不能带仓库路径 |
| 网站有界面但不能计算 | 先打开后端健康地址；再检查前端 config.js 的 HTTPS 域名及末尾 `/api` |
| 等待超时 | 先用健康地址唤醒服务再重试；计算请求超时后先刷新历史，避免重复提交 |
| GitHub Pages 404 | 是否在前端仓库启用 Pages；是否 main + / (root)；index.html 是否在最外层；Actions 是否成功 |
| 修改配置后仍是旧页面 | 等 Pages 重新发布成功，再按 Ctrl+F5 强制刷新 |
| 本地能用，手机不能用 | config.js 是否仍是 localhost；是否只启动了本地后端、并未成功部署 Render |
| 免费额度不足或服务暂停 | 查看平台用量和提示；不要用持续保活脚本绕过限制，评测前再次检查可用性 |

如果卡住，只需描述停在哪一步、页面提示什么，或提供**不含数据库连接字符串和密码**的截图。不要把 Neon 密码贴到公开 Issue 或博客。

## 部署结束后，作业里要记录什么

- 前端 GitHub 仓库链接。
- 后端 GitHub 仓库链接。
- GitHub Pages 实际访问网址。
- 后端 `/api/health` 访问网址。
- 计算、错误处理、历史、删除、刷新和后端重启后保留记录的截图。
- 架构说明中写清：本地为 SQLite，公网为 Neon/PostgreSQL；公网通过 Flask + Gunicorn 提供接口，前端不计算结果。

## 本次准备与验证的边界

云端代码和教程已在本地准备；本地自动测试使用临时数据库验证计算与 HTTP 接口，PostgreSQL 适配器另有参数化和提交失败处理测试。**没有使用你的 Neon 凭据，因此并未宣称你的真实 Neon 数据库、Render 服务或 Pages 页面已经上线。**完成第 2～6 步后，才能确认真实公网环境可用。

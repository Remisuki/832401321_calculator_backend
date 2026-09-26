# 后端代码规范

规范来源：
- [PEP 8：Python 代码风格](https://peps.python.org/pep-0008/)
- [PEP 257：文档字符串约定](https://peps.python.org/pep-0257/)
- [Python Decimal 文档](https://docs.python.org/3/library/decimal.html)
- [Python sqlite3 文档](https://docs.python.org/3/library/sqlite3.html)

本项目以 PEP 8 为基础，允许少量直观的数据表格与 SQL 字符串使用较长行，优先保证教学代码可读性。

## 命名与格式

- 文件采用 UTF-8，四空格缩进。
- 模块、函数和变量使用 snake_case，类使用 PascalCase，常量使用 UPPER_SNAKE_CASE。
- 导入位于模块顶部，区分标准库与本项目模块。
- 顶层函数之间保留空行，复杂表达式和 SQL 在合理位置换行。
- 公开模块和核心函数写文档字符串；解释语法、返回值或约束。

## 职责划分

- app.py 处理 HTTP、JSON、来源校验和启动配置。
- calculator.py 只处理数学语法与 Decimal 运算。
- storage.py 管理数据库初始化、连接和历史增删查。
- 纯计算函数不负责文件和网络操作，便于单独测试。

## 输入与异常处理

- 按类型校验 JSON，不自动把布尔值、列表等转成表达式。
- 表达式仅允许白名单数学语法，禁止 eval、exec 和任意代码执行。
- 对表达式长度、递归深度、数值范围、请求体大小设置边界。
- 用户输入错误返回明确的 4xx JSON；数据库错误记录日志并返回通用 500 信息。
- 不使用空 catch / except 忽略错误，不向用户泄露内部异常堆栈。
- 不把 CORS 当作用户认证；配置与文档必须如实说明共享数据边界。

## 数据与接口

- 金额之外的一般教学计算也使用 Decimal 减少浮点误差；对外结果返回文本。
- SQL 使用参数绑定，不使用字符串拼接插入用户输入。
- 数据库连接显式关闭，写操作使用事务，删除必须核查影响行数。
- 数据库时间采用 UTC ISO 8601；本地显示转换由前端完成。
- 接口状态码、字段和错误代码统一，修改时更新 API.md。

## 测试与版本管理

- 使用 unittest 测试可观察的功能与错误边界。
- 集成测试创建临时数据库及临时端口，不改动个人数据。
- 提交前运行 python -m unittest discover -s tests -v。
- 数据库、缓存、虚拟环境和私密配置不提交到 GitHub。

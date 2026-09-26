# 计算器 API 文档

本地基地址：`http://localhost:5000/api`。请求和响应采用 UTF-8 JSON。所有响应禁止缓存；浏览器跨域访问需匹配 ALLOWED_ORIGINS。

## 健康检查

`GET /health` → 200：

```json
{"status":"ok"}
```

此接口只表示 HTTP 服务运行，不代替数据库读写验收。

## 计算并保存

`POST /calculate`

请求头：`Content-Type: application/json`

```json
{"expression":"0.1+0.2"}
```

201 响应示例：

```json
{
  "success":true,
  "id":1,
  "expression":"0.1+0.2",
  "result":"0.3",
  "created_at":"2026-09-23T12:00:00+00:00"
}
```

- expression 必须是字符串；去除首尾空白后最多 200 个字符。
- result 始终为字符串，避免 JSON 数值经过浏览器浮点数转换。
- created_at 为 UTC 时间，前端转换为访问者本地时间。
- 只有计算、保存都成功才返回 201。
- 每次成功 POST 都创建新记录，不做去重。请求超时后应先查询历史，避免重复提交。
- 请求体最大 4096 字节；仅接受普通 Content-Length JSON 请求，不支持分块传输。
- 支持的数学语法和数值范围见 README。

## 查询历史

`GET /history?limit=5&offset=0`

| 参数 | 默认值 | 范围 |
|---|---|---|
| limit | 10 | 1–100 |
| offset | 0 | 0–9223372036854775807 |

200 响应示例：

```json
{
  "success":true,
  "records":[
    {
      "id":1,
      "expression":"0.1+0.2",
      "result":"0.3",
      "created_at":"2026-09-23T12:00:00+00:00"
    }
  ],
  "total":1,
  "limit":5,
  "offset":0
}
```

记录按 ID 从大到小排列。空数据库时 records 为 []、total 为 0。多位访问者共用一份历史，分页期间其他人增删记录可能导致页面内容变化。

## 删除指定历史

`DELETE /history/1`

200：

```json
{"success":true}
```

删除实际数据库行。再次删除同一记录返回 404。当前没有清空全部历史接口，也没有回收站。

## 错误响应

```json
{
  "success":false,
  "code":"INVALID_EXPRESSION",
  "message":"除数不能为 0。"
}
```

| HTTP 状态 | code | 场景 |
|---|---|---|
| 400 | INVALID_EXPRESSION | 非法表达式、除零、缺少或错误类型的 expression、超限 |
| 400 | INVALID_JSON | JSON 格式或 UTF-8 编码错误 |
| 400 | INVALID_BODY | 不是 JSON 对象、长度或传输方式不正确 |
| 400 | INVALID_PAGE | 分页参数不正确 |
| 403 | ORIGIN_NOT_ALLOWED | 请求携带了不在允许列表中的 Origin |
| 404 | NOT_FOUND | 地址或指定历史不存在 |
| 405 | METHOD_NOT_ALLOWED | 已存在接口使用了错误请求方法；附带 Allow 响应头 |
| 413 | BODY_TOO_LARGE | 请求体超过 4096 字节 |
| 415 | UNSUPPORTED_MEDIA_TYPE | 未使用 application/json |
| 500 | DATABASE_ERROR | 数据库无法读取或保存 |

跨域来源被拒绝时，浏览器可能只向前端显示网络错误；请检查后端日志和 ALLOWED_ORIGINS。内部数据库错误写入后端日志，不将文件路径等内部细节放进错误消息。

## 跨域预检

对已存在的接口发送 OPTIONS，允许的浏览器来源得到 204 空响应体，以及 Access-Control-Allow-Origin、Methods、Headers。允许 GET、POST、DELETE、OPTIONS 和 Content-Type。

来源应为协议、域名和端口，不包含路径。例如 https://user.github.io/project/ 的来源是 https://user.github.io。

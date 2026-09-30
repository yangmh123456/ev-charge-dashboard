# 安全最佳实践检查报告

## 摘要

本次静态检查覆盖 Flask 后端、原生 JavaScript 前端、静态资源加载、文件服务、API 和交付脚本，并通过自动化测试检查安全响应头、DOM 渲染方式及缺失数据错误响应。当前源码未发现动态代码执行、数据库字符串拼接或任意上传接口。这不是完整的安全审计或渗透测试，不能据此保证生产环境安全。

## 已修复问题

### SEC-001 Flask debug 默认开启风险

- 规则：FLASK-DEPLOY-002
- 严重性：High
- 位置：`app/web.py` 的启动入口
- 证据：入口已改为 `EV_DASHBOARD_DEBUG=1` 时才开启 debug，默认关闭。
- 影响：如果开发调试器暴露到非本地环境，可能导致敏感调试信息泄露。
- 修复：`debug = os.getenv("EV_DASHBOARD_DEBUG", "0") == "1"`。

### SEC-002 缺少浏览器安全响应头

- 规则：FLASK-HEADERS-001
- 严重性：Medium
- 位置：`app/web.py` 的 `add_security_headers`
- 证据：新增 `Content-Security-Policy`、`X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Permissions-Policy`。
- 影响：缺少这些响应头会降低 XSS、点击劫持、MIME 混淆等攻击的防御能力。
- 修复：通过 `@app.after_request` 统一设置响应头。

### SEC-003 前端使用 HTML 字符串注入

- 规则：JS-XSS-001
- 严重性：Medium
- 位置：`static/app.js` 的 DOM 和 SVG 渲染函数
- 证据：前端已改为 `textContent`、`createElement`、`createElementNS`、`replaceChildren`。
- 影响：如果未来 API 数据包含用户输入，字符串拼接进 `innerHTML` 可能扩大 DOM XSS 风险。
- 修复：删除 `innerHTML` 渲染路径，所有文本节点通过 DOM API 写入。

### SEC-004 请求体大小未限制

- 规则：FLASK-LIMITS-001
- 严重性：Low
- 位置：`app/web.py` 的应用配置
- 证据：新增 `MAX_CONTENT_LENGTH=1_000_000`。
- 影响：在未来增加 POST/上传接口时，缺少限制可能导致内存压力。
- 修复：设置全局请求体大小限制。

## 检查结果

### 后端

- 未发现 `render_template_string`、动态模板渲染、SQL字符串拼接、`subprocess`、`os.system`、任意 URL 请求、文件上传处理。
- 静态首页通过 `send_from_directory(STATIC_DIR, "index.html")` 返回固定文件，不接受用户路径参数。
- 当前 API 全部为 GET 且只读，不涉及 Cookie 认证下的状态变更，因此无 CSRF 暴露面。

### 前端

- 未使用第三方 CDN 脚本，`index.html` 只加载本地 `/static/app.js`。
- 未发现 `eval`、`new Function`、`document.write`、`localStorage/sessionStorage`、`postMessage`、动态跳转。
- 已通过静态测试约束危险 DOM sink。

## 剩余注意事项

- 当前仍使用 Flask/Werkzeug 开发服务器，适合课程演示和本机运行；生产部署应改用 Waitress、Gunicorn 或托管平台 WSGI。
- `SESSION_COOKIE_SECURE` 默认关闭是为了本机 HTTP 调试；部署到 HTTPS 时设置 `EV_DASHBOARD_COOKIE_SECURE=1`。
- 项目没有登录和权限系统；如果未来要开放到公网，需要增加认证、访问控制、审计日志和反向代理限流。

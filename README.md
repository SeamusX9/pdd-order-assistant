# 电商订单抓取助手

粘贴电商网址 → 内置 Edge 浏览器打开 → 登录确认 → 识别平台 → 勾选字段 → 一键抓取导出 Excel。

目前已适配**拼多多订单页**；其他平台走通用启发式（实验性）。

## 环境要求

- Windows 10/11
- 已安装 [Microsoft Edge](https://www.microsoft.com/edge)
- 源码运行需 Python 3.10+

## 源码运行

```bash
pip install -r requirements.txt
python app.py
```

首次运行会在程序目录创建 `profiles/default` 保存登录态；导出文件在 `抓取结果/`。

## 打包 exe

```bash
build_exe.bat
```

产物：`dist/电商订单抓取助手/电商订单抓取助手.exe`（需本机已装 Edge）。

## 项目结构

| 文件 | 说明 |
|------|------|
| `app.py` | GUI 入口 |
| `browser_worker.py` | Playwright 浏览器线程与 Excel 导出 |
| `adapters.py` | 平台适配器（提取脚本） |
| `smoke_test.py` | 连接已开页面的冒烟测试 |

## 使用说明

1. 启动后点击「打开页面」，在弹出的 Edge 中登录拼多多
2. 进入订单列表后点「识别当前页面」
3. 勾选字段、设置数量（0=全部），点「一键抓取导出」

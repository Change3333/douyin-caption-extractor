# 抖音文案提取器

输入抖音视频或图文分享链接，提取作品发布者填写的描述文案，并在网页中一键复制。

> 本项目提取的是作品的发布描述，不包含视频语音转文字或画面 OCR。

## 功能

- 支持从完整分享文本中识别抖音链接
- 支持 `v.douyin.com` 短链接
- 通过网络响应、SSR 数据、页面元素和标题多级提取
- 支持视频及图文作品页面
- 移动端自适应页面
- 支持 HTTPS、localhost 和局域网 HTTP 环境下的一键复制

## 环境要求

- Python 3.10+
- Chromium
- Linux 服务器使用可见浏览器模式时需要 Xvfb

## 本地运行

```bash
python -m venv .venv
```

Windows：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python douyin_desc.py
```

Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
xvfb-run -a python douyin_desc.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

局域网中的手机可以访问：

```text
http://电脑局域网IP:5000
```

## Linux 服务器部署

安装系统依赖：

```bash
sudo apt update
sudo apt install -y python3-venv xvfb
python -m playwright install --with-deps chromium
```

生产环境建议使用 Gunicorn，并通过 Nginx 提供 HTTPS：

```bash
pip install -r requirements-server.txt
xvfb-run -a gunicorn \
  --workers 1 \
  --threads 1 \
  --bind 127.0.0.1:5000 \
  douyin_desc:app
```

Playwright 同步 API 不应在多个线程之间共享。高并发场景建议使用任务队列，并限制同时运行的浏览器数量。

## 常见问题

### 一键复制没有反应

`navigator.clipboard` 通常只允许在 HTTPS 或 localhost 中使用。本项目会在局域网 HTTP 环境下自动使用兼容复制方案；生产网站仍建议配置 HTTPS。

### 偶尔提取失败

抖音页面结构、风控策略和登录状态可能发生变化。遇到失败时可以：

1. 稍后重试；
2. 在浏览器中打开短链接，再复制跳转后的完整链接；
3. 检查服务器是否能够正常启动 Chromium；
4. 查看服务端日志中是否存在超时或验证页面。

### 服务器重启后网站没有恢复

建议使用 systemd、Supervisor 或容器管理服务，不要只依赖 SSH 会话中的后台进程。

## 使用说明

本项目仅供学习、研究及处理你有权访问的内容。使用时请遵守适用法律、网站服务条款、版权规则和访问频率限制。请勿用于批量采集、绕过访问控制或侵犯他人权益。

## License

[MIT](LICENSE)

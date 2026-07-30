# 贡献指南

感谢你愿意参与改进抖音文案提取器。

## 提交问题

提交 Bug 前请先搜索现有 Issues，避免重复。请尽量提供：

- 输入的是短链接还是完整链接
- 作品类型（视频或图文）
- 操作系统和 Python 版本
- 完整错误信息或脱敏后的日志
- 问题是否可以稳定复现

请勿在公开 Issue 中提交登录 Cookie、Token、密码或其他敏感信息。

## 本地开发

```bash
python -m venv .venv
pip install -r requirements.txt
playwright install chromium
```

运行测试：

```bash
python -m unittest discover -s tests -v
```

启动应用：

```bash
python douyin_desc.py
```

## Pull Request

1. Fork 本仓库并创建功能分支；
2. 保持改动范围清晰，避免混入无关格式化；
3. 为新增行为补充测试或验证说明；
4. 确保没有提交账号、Cookie、代理地址等敏感数据；
5. 在 PR 描述中说明改动原因、用户影响和验证方式。

提交代码即表示你同意将贡献内容按照本仓库的 MIT License 发布。

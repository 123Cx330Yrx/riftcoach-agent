# Contributing to RiftCoach

感谢关注 RiftCoach。项目当前以小步、可测试和可解释的方式开发。

## 开发环境

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

Linux 和 macOS 使用相应的虚拟环境激活命令即可。

## 提交原则

- 一个 Pull Request 只解决一个清晰问题；
- 新行为应先增加失败测试，再提交最小实现；
- 不提交 `.env`、本地缓存、Harness 运行目录或真实玩家报告；
- 不把普通 HTTP 工具封装称为标准 MCP；
- 不把线性工作流或普通函数集合夸大为 Multi-Agent；
- 架构阶段、数据职责或安全边界发生变化时，应新增或更新 ADR。

## Pull Request 检查

提交前确认：

```powershell
python -m pytest -q
git diff --check
git status --short
```

Pull Request 应说明：问题、设计取舍、测试证据、失败与降级行为，以及是否影响公开数据或部署配置。

## 安全问题

安全问题不要直接附带敏感利用细节提交公开 Issue，请遵循 [SECURITY.md](SECURITY.md)。

# Security Policy

## Supported versions

RiftCoach 仍处于早期开发阶段。安全修复只应用于默认分支的最新版本。

## Reporting a vulnerability

请不要通过公开 Issue 披露 API Key、可复现的利用细节或其他敏感信息。

仓库发布到 GitHub 后，请优先使用 GitHub 的 **Private vulnerability reporting** 功能提交报告。报告应包含：

- 受影响的文件或接口；
- 可复现步骤；
- 可能影响；
- 已知的缓解建议。

如果仓库尚未启用私密漏洞报告，请只提交一个不含利用细节的公开 Issue，请求维护者提供私下联系方式。

## Secrets and local data

- 不要提交 `.env`、API Key、SSH 私钥或云服务器凭据；
- 不要提交 `data/cache/`、`data/runs/` 或真实玩家生成报告；
- 泄露的凭据应立即在对应服务商处轮换，删除文件并不能使旧凭据重新安全；
- 日志和错误信息不得输出完整 Riot PUUID 或访问令牌。

## Scope

RiftCoach 只处理公开的赛后数据。实时辅助、客户端内存读取、隐藏信息追踪和游戏自动化不在项目范围内。

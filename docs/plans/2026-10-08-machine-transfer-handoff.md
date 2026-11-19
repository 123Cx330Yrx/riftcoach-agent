# 换电脑前恢复入口（2026-10-08）

## 先恢复事实，再执行

当前仍为8E，原15严格2/15；最近竞争范围批已关闭。它仅1调用15888tokens、估价0.186804元，
本次没有早死误报，补刀真错检出；额外audit漏了目标断言，双审拒绝，第二项未发。
没有待续付费进程，没有可以转授的剩余一次；不要运行旧launch/wait脚本恢复旧批。

采用取舍：不采用模型自选mandatory scope audit作为通用修法或产品新增门槛；
仅保留为已知目标的诊断检查。原始拒绝与业务改善同时保留，见ADR0116最后一节。
下一技术问题是完整review→必要编辑→fresh任务如何在既定预算内得到正确终稿，而不依赖
模型自选audit的覆盖完整性；必须遵守ADR0110/0111，不把新的格式要求代替产品质量。
下一轮先读canonical及活动work card，不重跑历史诊断，不立即新开付费15例。

## 两份工作区不能混

| 工作区 | 分支与状态 | 新机器恢复原则 |
|---|---|---|
| 后端 | codex/rq192-provider-stream-contract-ci；最新业务结果提交81278230，后续本恢复记录在同分支 | checkout该分支，读其AGENTS及docs/project_execution_state.md |
| 主工作区/前端 | codex/g53-7-a-prime，base9e6d78be；46项tracked修改、137个untracked文件 | 独立checkout该base后恢复overlay，不覆盖后端，不自动合并 |

本机路径D:/riftcoach-agent和D:/riftcoach-agent-rq192-pr只是路由提示。不要直接复制worktree
的.git文件作为独立仓库：它指向旧机器共享Git目录。新电脑用两个独立clone或正确创建worktree。
主工作区变化本轮只做本地快照，未提交到共享分支。

## 本地恢复包及覆盖

本机目录：`C:/Users/33502/Documents/Agent/outputs/riftcoach-transfer-20261008-1300`。
这是本机已准备的包，尚未传到新电脑；不是整机、数据库或所有历史资料的完整备份。

- `project-branches.bundle`：上述两分支的Git历史；以包内README和manifest中的最终提交为准。
- `main-uncommitted-overlay.zip`：46项tracked修改及137个untracked文件的原字节，含删除记录、
  staged/working patch和manifest。恢复到匹配base的干净主工作区，按manifest核对hash。
- `private-local-evidence.zip`：原15、完整重评、竞争范围三批原件；相关操作记录与9月15日
  需求复盘资料。含私有原始运行材料，只作用户本地迁移，不发布到Git或外部页面。
- `local-wallpaper-research.zip`：被Git忽略的候选壁纸与研究图标，本地保留；未改变其采用/来源状态。
- `inventory.json`、`SHA256SUMS.json`及`README.md`：范围、校验和与恢复顺序。

原15与新诊断公开白名单封存已在Git；私有原件和主工作区未提交内容需要携带上面的本地包。
62主题、四块联动、前端审美/必要重做/头像等需求资料在私有包requirements目录，未因本批调整取消。

## 需要另行迁移或重建的环境

- Provider/Riot等密钥在原机环境配置；包不含.env、不含Codex登录凭据。不要把它们补进Git。
- Codex原生线程/审查事件依赖宿主历史。公开封存有审查正文与绑定，但不替代新宿主重新读取
  原生事件。若新机器无法访问旧线程，保留旧证据不变，下一新批使用实际可读主体重新冻结；
  不伪造旧principal，不把“机器迁移”当作旧失败批的续跑或补签。
- Python虚拟环境和node_modules重新安装，勿把旧机绝对路径当可移植环境。
- PostgreSQL数据卷不在本包；需要原业务数据时另做数据库备份/恢复。不要把新建空库称作原库恢复。
  原机为compose项目riftcoach-agent-rq192-pr，旧映射15432是为绕过当时Windows保留端口；
  新机先检查端口/卷，再选择本机映射，不能盲用旧override路径。
- 代理端口12000是用户旧机配置；新机验证代理服务后再配Git，不以旧代理错误判断仓库损坏。
- 更早的ignored运行目录、缓存与其他外部研究资料未全部打包；本机保留，必要时按证据索引补取。

## 验收与停止点

恢复后先核对分支、base、overlay摘要、canonical、当前CI与运行进程；运行治理检查。
恢复包校验和不证明模型质量。业务原始证据已封存；不要因新机路径不同改写其原始hash。
完成这些后，从ADR0116末尾的下一技术问题继续。当前没有新付费方案，也没有新增产品准入。

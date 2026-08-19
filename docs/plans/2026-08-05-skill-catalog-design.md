# 阶段 5C-2：Skill Catalog V1

## 1. 本轮目标

Skill Catalog 负责回答一个有限问题：当前项目中有哪些经过校验、可以交给 Router 考虑的 Skill？

它连接 5B 的单包 Loader 与 5C-1 的 Router Contract：

```text
skills/ 目录
→ 发现直接子目录
→ load_skill() 校验每个 Skill 包
→ 形成不可变、顺序稳定的 LoadedSkill 快照
→ 投影为 SkillRouteCandidate 元组
```

Catalog 不理解用户请求，也不判断哪个 Skill 更合适。

## 2. 方案选择

### 采用：构建时生成快照

应用显式调用 `SkillCatalog.from_directory()`，一次性发现并完整加载 Skill。这里的“加载”用于启动校验和保存本地对象，不代表把所有 `SKILL.md` 注入模型上下文。任何可见 Skill 目录损坏都会立即失败，不把配置错误拖到处理用户请求时才暴露。

快照按 Skill 目录名称排序，因此相同文件集合总会得到相同候选顺序。增加或修改 Skill 后，需要重新构建 Catalog；V1 不做运行时热更新。

### 暂不采用：每次路由动态扫描

它能自动看到磁盘变化，但会把文件 I/O、导入模型和 YAML 错误带进每次请求，也会让同一进程中的候选集合随时间漂移。当前没有足以支持这项复杂度的需求。

### 不采用：Python 手工注册表

手工注册很直观，但 `manifest.yaml` 已经是 Skill 元数据的事实来源。再维护一份 Python 名单会制造双重配置和遗漏风险。

## 3. 发现与失败规则

- Catalog 根路径必须存在且必须是目录；
- 只检查根目录下的直接子目录，不递归扫描；
- 普通文件和隐藏目录不视为 Skill 包；
- 每个可见子目录都必须是完整 Skill 包，不能静默跳过坏包；
- 每个包继续复用 `load_skill()` 校验 Manifest、SKILL.md 和 Pydantic 模型引用；
- Skill 名称必须唯一，最终顺序按名称稳定排序；
- 空目录是合法状态，Router 后续可据此返回 `no_available_skills`；
- Catalog 错误携带具体包名，但保留原始 `SkillContractError` 作为异常原因。

## 4. 对外接口

```text
SkillCatalog.from_directory(root)  构建严格快照
catalog.skills                     获取不可变 LoadedSkill 元组
catalog.get(name)                  按名称查找完整 Skill，缺失返回 None
catalog.route_candidates           获取最小路由元数据元组
```

`route_candidates` 不包含工具权限、输入输出模型类或 SKILL.md 正文。只有 Router 选中名称后，后续运行时才可以通过 `get()` 取回完整 Skill、装配该 Skill 的指令，并在执行边界检查工具权限。

## 5. 本轮不做

- 不匹配关键词、意图或自然语言；
- 不创建 `RouterDecision`；
- 不调用 LLM；
- 不执行 Skill、Tool 或 AgentLoop；
- 不做文件监听、热更新或远程 Skill 市场；
- 不在发现阶段绑定 Provider 或 ToolRegistry；
- 不增加第二个业务 Skill 来伪造多 Skill 场景。

按原检查点，5C-3 基于 Catalog 候选实现第一版确定性匹配；版本化路由评测集
属于 5C-5。后来一个实现批次提前写出了评测基础设施，但不能据此合并两个
检查点。

## 完整教材与退出复核

本文只保留 5C-2 当时的 Catalog 设计快照。5C-1 至 5C-6 的当前完整心智模型、
数据/控制流、代码与测试映射、评测解释、限制、框架边界和面试表述，统一见
[`2026-08-07-skill-router-v1-exit-review.md`](2026-08-07-skill-router-v1-exit-review.md)。

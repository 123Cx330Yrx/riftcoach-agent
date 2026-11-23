# 原15例判准、历史缺口和当前组合对齐

本工作包完成无付费裁决与确定性修复，未重新审签旧案例。原15初评都已经发过，分布在三个关闭批；10例有所在批通过证据、3例语义拒绝/分歧、2例缺认证。它们不能合并为当前组合的15例资格。新关系教学不采用，现阶段保留已有whole-text基线。

## 逐项裁决

以下“本轮裁决”是主审实读两份完整base、15份完整差分及来源后的前瞻判准，不是新增独立Host意见，也不改变旧标签、旧stage或旧seal。机器绑定、逐项原标签/报告/来源/请求SHA、历史stage及其原native绑定见 `data/evaluation/results/original15_alignment_20261013.json`。

| key / 原标签 | 实际命题与来源 | 本轮裁决与必要修复范围 | 已有真实结果及缺口归属 |
|---|---|---|---|
| claim-scope:1 / accept | 中单话题内四局CS 8.38–9.64，胜8.805/负9.01；“这5局内”承接样本窗口；全文分别列中单/辅助 | 保留accept。未明示把辅助合并为分母；泛指均值不补成每一指标。可读性建议不升为事实错误 | initial94/pass双审通过；属于原首批，非当前资格 |
| claim-scope:4 / reject | “全部5局每一个指标都被辅助拉低，包括视野和早死” | reject。辅助视野90、早死7拉高两项；修全称及方向，保留正确的中单描述 | 检出真错但新增早死误报，双方拒绝initial，未编辑；模型语义缺陷 |
| claim-scope:3 / reject | 明写“全部5局（包括辅助）合并计算”后CS胜负持平 | reject。中单8.805/9.01，全样本8.805/6.4533…；必须使结论与分母一致 | 编辑、fresh94通过；原首批证据 |
| attribution:1 / reject | 全样本CS与伤害差距复合归因“主要来自辅助” | reject。CS去辅助后差异逆转；伤害差从695.4183…到669.235，仅减少26.1833…，不能将两项一起主要归因辅助。分别修因果/描述范围 | 编辑、fresh96通过；原首批证据 |
| scope:4 / reject | 正文把全样本早死2.5/2.67写作中单；摘要未明确口径 | reject。正文中单应2.5/0.5；检查摘要及直接依赖结论。可分别明确全样本近同与中单差异，不能机械仅换数字，亦不要求删掉明确属全样本的正确命题 | initial主审接受、独立判摘要漏修，分歧后未编辑；历史分歧保留 |
| scope:3 / reject | 摘要明确“中单早死几乎相同” | reject。四中单两胜两负实际2.5/0.5，修摘要及直接依赖内容，不把正确的泛指混合均值句扩成全称 | 编辑获认可；fresh误读泛指均值为全称而被拒绝；模型语义缺陷 |
| claim-scope:2 / accept | 实际修订稿明确中单/全样本早死两口径与四局中单 | 保留accept。按实际稿审，不按“来自修订”的身份推断问题 | 96/pass已返回；恢复分支无法派原独立主体，无有效双审；operator恢复缺口 |
| claim-scope:5 / accept | 指标方向、四中单范围均显式正确 | 保留accept，不为改写而报错 | initial96/pass双审通过；第二批证据 |
| claim-scope:6 / reject | 尚未决定纳不纳辅助，却已断言CS胜负持平 | reject。两种口径改变实质结论，需选定口径或给出各自条件结论；不是纯措辞问题 | 必要编辑、fresh96通过；第二批证据 |
| claim-scope:7 / accept | 分别陈述四中单CS近同与全五局CS差异 | 保留accept。条件各自清楚，不能合并成自相矛盾 | initial96/pass双审通过；第二批证据 |
| observed:1 / accept | 本次四中单经济/伤害每一胜局均高于每一负局；外部数据作归档观摩问题 | 保留accept。逐对比较成立，只限所选样本；OP.GG不作当前推荐、同段位基准或历史败因 | 96/pass、两份意见接受，但operator同turn重复NEW_TASK导致native导入拒绝；无认证，非模型失败 |
| observed:2 / reject | 第10段从当前样本推出未来所有中单输局伤害低于所有赢局 | reject。保留当前样本关系，撤除无证据的未来全称预测；来源不能支持跨时间外推 | 编辑、fresh95通过；第三批证据 |
| observed:3 / reject | 第21段把ShowMaker观摩对象当作阅读者本人 | reject。恢复对象/读者身份和观摩目标，不能给读者建立虚假个人基线 | 编辑、fresh95通过；第三批证据 |
| observed:4 / reject | 第27段用OP.GG检索日期冒官方补丁发布时间 | reject。官方16.17发布2026-08-25T18:00:00Z；OP.GG检索2026-09-10，须分开。官方元数据没有改动正文，不能补造加强/削弱 | 编辑、fresh96通过；第三批证据 |
| observed:5 / reject | 第4段标题宣称所选数据证明防抓优秀 | reject。统计/时间线支持生存结果和事件位置，缺录像决策证据；标题同样属于报告命题 | 编辑、fresh97通过；第三批证据 |

## 两个争议的决定依据

“这5局内”出现五次只是字符串库存，不能直接推出五个错误标签。claim-scope:1原dataset rationale已经区分mid topic与five-match window；相邻句、标题和全文均有四中单范围。claim-scope:3则主动写明全部五局、包括辅助、合并计算。本轮保留这个有实质区别的对照，纠正上一工作卡笼统的“显式五局结论”描述。首个离线Host演练的独立拒绝原样保留；本轮没有假称双方重新一致。

scope:4需要审修法的直接影响：正文的错误口径可能使摘要关系解释失去依据，不能只核某个数字已替换。足够的修法可以明确区分全样本与中单，不必把仍正确的全样本命题一并删掉。scope:3摘要已显式中单，其事实错误不依赖这个歧义。

五局事实由两套来源逐行交叉核，再以Decimal分别重算全样本/中单、胜/负五项均值，记录具体match_id，未调用原投影均值函数替自己背书。原来源展示精度与逐局算术精度分开：源展示CS胜均8.8，逐局精算8.805，不单凭显示末位制造新实质错误。

observed另核完整knowledge与外部bundle：Syndra中单T2第12/前18、Vex中单T2第14及52%、Camille辅助T4第35及46%，均为归档快照；缺段位、区域、精确patch匹配。K1早死只支持风险窗口，K2禁止无基准固定阈值，K3允许录像待验证假设而非统计因果。本文判准与报告全文约束一致，不从外部事实补造玩家能力。

## 当前组合已绑定，尚未取得资格

`python -m scripts.audit_original15_alignment --verify-local-originals --output <new-path>` 只读三个seal与close audit、700个旧run原件，并从固定coverage/dataset/source恢复15输入；重复执行须给新输出路径。无模型、无Host任务、无业务submit。它输出完整准备指纹：

- 15份原标签/manifest/报告及实际输入SHA，逐组成来源SHA，实际初评request/policy/schema，以及同输入编辑policy/schema。编辑schema使用明确标注的中性探针，只用于形状绑定，不冒充业务意见。
- 原三批的HEAD/CI/stage/结果与seal SHA，不把三批成功累计成同版本认证。
- 当前whole-text policy、block-keyed editor、time600身份、GLM/Flash transport、共享任务预算、Host/作者/观测合同及所有准备源码SHA。指纹取机器文件的 `combination_sha256`；prepared、authorized、qualified分别表达。

旧 `document-review-original15-v1` 绑定旧editor、旧policy和不超过300秒请求；当前15逐项被其identity拒绝符合隔离合同。不能删time600/teaching标记、放宽旧校验器或借旧成功绕过该差异。准备对象不会注册到产品，也不会发起原15重买；默认产品入口仍未接当前组合。

## 已实施的完整响应夹具修复

首次偏离在本地生产者：计数案例只换before/after，父类仍拼接“混合均值方向”的reason。现在新增前瞻 `full_chain_bound_fixture.py` 及单一完整响应包；三个stage的整个响应、reason、原稿/输入与修订稿SHA一并冻结。每次消费核包SHA和输入，再经实际review/editor/final请求校验；实际journal原样保存before/after/reason。旧两个runner和旧fixture未动，历史失败不重写。

新增测试覆盖理由漂移、缺理由、错输入/原稿/新稿、旧格式、漏stage、错模型，以及完整revision经实际editor进入journal和完整终评请求。另用原三阶段测试接入新consumer，实际作者文件/check-answer/import/submit/replay/seal代码运行，native与业务响应仍是明确替身。定向命令 `python -m pytest tests/test_full_chain_bound_fixture.py tests/test_full_chain_host_rehearsal.py -k 'not original and not explicit' -q --tb=short`：12 passed、2 deselected，174.05秒。没有第三次真实简化Host演练。

哈希只防绑定后的换件：若作者给错误reason重新签新包，结构上仍能通过，测试明确保留这个反例；最终语义仍需独立Host逐项判断，不能用关键词检测冒充语义验证。

## 收敛后的依赖与下一动作

本轮消除了“哪些旧例没跑、是否全改标签、是否放宽旧资格、reason为何错配”四个不确定点。下一项为在准备指纹上补齐**当前组合的资格验证入口**：复用已有严格关闭证据/真实native导入，要求15 distinct完整覆盖、逐项语义通过、身份及源码同组合，遇历史拼批/未认证/缺编辑或fresh时拒绝；离线负例验证后再形成必要实测范围。不能直接重启旧full15或默认选定新付费批。

真实三阶段Host正例、同组合真实15质量证据、自然生成/工具/编辑/终评和产品消费仍缺；现有样本熟悉来源不是holdout。Worker阶段间取消、DB/API/UI/journal、Coach/Training、四块联动、前端审美头像、Memory、身份运维、两树整合、独立评估与学习保持。自动任务PAUSED，主阶段8E未完成。

# ADR0120：原文报告的安全结构化呈现

2026-11-03；状态 **Accepted for implementation**，沿用户已授权的P3/P4产品工作卡实施，不新增付费许可或产品准入。

## 问题与选择

已审的5083字节完整报告含1个主标题、7小节、15个列表条目和1张4列表格。
SafeMarkdown此前只显示纯文本，标题和表格符号直接暴露，手机无法有效比较数据。
CoachBrief与ObservationWorkbench共用此组件，接口decoder已逐字返回原稿，缺口在显示层。

采用固定版本react-markdown 10.1.0与remark-gfm 4.0.1，通过AST生成React节点并支持表格。
继续纯文本无法解决表格阅读；手写正则解析器容易破坏嵌套、转义和代码；HTML字符串再净化引入不必要的活动DOM边界。
代价是新增解析依赖和前端包体积，使用锁文件固定全部依赖，并以构建产物、实际页面验证评估。
依据：[react-markdown](https://github.com/remarkjs/react-markdown#security)、[HTML处理](https://github.com/remarkjs/react-markdown#appendix-a-html-in-markdown)、[GFM](https://github.com/remarkjs/remark-gfm)。

## 约束与路径

API原字字符串→SafeMarkdown解析→受限React元素。标题层级相对宿主区块调整，文字不改；
表格保留各单元格及对齐，窄屏只在表格区域滚动，并可键盘访问。
不启用raw HTML插件、不使用dangerouslySetInnerHTML。标签白名单之外只保留文本；
链接/图片原标记转为React转义文字，不转发URL属性；任务标记是文字而非可操作表单。
继续保留translate=no、拒绝/未就绪/失败/取消门槛，归档副本仍明确为人工校订稿。
不改报告、来源、生成提示、审查结论、成本、数据库或旧恢复原件。

## 验证与失败处理

安全单测覆盖HTML、脚本/事件、危险URI、嵌套链接与图片、代码、转义、列表和原全文；
对全文逐段、15条列表、12个数据单元格及K引用作保持检查。
复用本地fixture API，完整原稿通过实际客户端和CoachBrief消费，在1440/320验证可读、无页面溢出、无外部请求、键盘表格滚动及拒绝态；ObservationWorkbench复用同一组件，并通过既有导入/校验浏览器路径核验标题和禁止翻译边界。
仅前端fixture证据，不冒充SQL或新模型质量；任何正文丢失/安全回归在显示层修复，不重写旧稿或付费润色。

## 实施结果

328项前端单测通过；8项既有相关E2E及3项全文/安全E2E通过。1440/320截图已人工查看，原报告、DB、ZIP及冻结树未变。构建主JS为672.15KB（gzip203.71KB），仍保留大块提示，未调整告警阈值；这是当前总大小，不是相对旧版本的增量。官方npm生产audit零漏洞，镜像站不支持audit接口。未测真实网络首屏时延或新模型语义。详见`data/evaluation/results/sol_product_report_markdown_offline_20261103.json`。

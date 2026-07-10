# <一句话需求> - <YYYY-MM-DD>

<!--
Use this template to reconstruct product intent from an implemented feature.
Sections 1-8 follow the decision-first PRD structure. Sections 9-10 are mandatory implementation evidence and verification appendices.
Implementation is evidence, not automatically the correct product requirement. Separate observed behavior, inferred intent, gaps, and recommendations.
Localize human-facing text. Keep IDs, paths, event names, and machine identifiers ASCII.
Remove empty optional subsections and this note from generated artifacts.
-->

## 1. <产品决策摘要>

### 1.1 <反向还原结论>

<!-- State what product capability the implementation appears to deliver, whether it is coherent enough to document as intended behavior, and the most important gap or decision. -->

| <决策项> | <当前判断> |
| --- | --- |
| <还原后的推荐定义> |  |
| <实现与产品意图一致度> | <高 / 中 / 低，并说明依据> |
| <PRD 状态> |  |
| <研发交接状态> |  |
| <上线状态> |  |
| <关键阻塞 / 偏差> |  |
| <下一检查点> | <负责人 / 阶段 / 完成证据> |

### 1.2 <文档元数据>

| <项目> | <内容> |
| --- | --- |
| <需求来源> | <已实现功能反向还原> |
| <需求日期> |  |
| <分支 / 版本> |  |
| <相关模块 / 平台> |  |
| <本次变更> |  |

## 2. <背景与证据>

### 2.1 <问题与用户场景>

### 2.2 <实现侧证据摘要>

| ID | <证据类型> | <文件 / 页面 / 测试 / 资源> | <观察到的行为> | <可信状态> | <产品含义> |
| --- | --- | --- | --- | --- | --- |

### 2.3 <推断、缺口与未知项>

| ID | <推断 / 未知项> | <证据基础> | <当前处理> | <需要谁确认> | <影响> |
| --- | --- | --- | --- | --- | --- |

## 3. <目标与成功标准>

| ID | <推断或已确认目标> | <用户 / 业务结果> | <指标或可观察信号> | <证据状态> | <验证窗口> |
| --- | --- | --- | --- | --- | --- |

## 4. <范围与非目标>

| <范围层级> | <内容> | <实现覆盖> | <判断 / 理由> |
| --- | --- | --- | --- |
| MVP |  |  |  |
| <可选> |  |  |  |
| <未来> |  |  |  |
| <非目标> |  |  |  |

## 5. <需求详情>

<!-- Create one subsection per implemented capability. Describe intended behavior first, then cite implementation evidence and discrepancies. -->
<!-- Missing Chinese screenshot outside a table: `> 占位图：<surface>-<state>.png` followed by `> 用途：<what this proves>`. Inside the table below, keep the same text in the `图示` value cell. -->

### 5.1 <R1 需求名称>

**产品判断：** <What this behavior should mean for users and whether the implementation supports that interpretation.>

| <维度> | <需求说明> |
| --- | --- |
| <用户场景与价值> |  |
| <入口 / 触发> |  |
| <主流程与业务规则> |  |
| <内容 / 文案> |  |
| <界面与交互> |  |
| <数据与状态> |  |
| <权限与边界> |  |
| <加载 / 空 / 错误 / 恢复> |  |
| <依赖与降级> |  |
| <实现证据> | <EV1, file path, route, test, screenshot...> |
| <实现偏差 / 未证明项> |  |
| <关联目标 / 验收> | <G1, AC1...> |
| <图示> | <Real local image or exact inline placeholder when needed.> |

## 6. <交付设计>

### 6.1 <数据与埋点>

| <事件名> | <触发时机> | <关键属性> | <实现状态 / 位置> | <隐私与验证说明> |
| --- | --- | --- | --- | --- |

### 6.2 <文案与多语言>

```text
<new or changed UI copy without an existing i18n key>
```

| <文案 / Key> | <使用位置> | <实现位置> | <复用或翻译说明> |
| --- | --- | --- | --- |

### 6.3 <UI 与研发交接>

| <交付项> | <路径 / 位置> | <已实现 / 建议调整> | <说明 / 边界> |
| --- | --- | --- | --- |

### 6.4 <测试重点>

| <测试类型> | <现有覆盖> | <高风险缺口> | <建议验证> |
| --- | --- | --- | --- |

## 7. <风险、决策与待确认>

### 7.1 <关键决策记录>

| ID | <决策 / 推荐调整> | <实现证据> | <替代方案及未选原因> | <影响> |
| --- | --- | --- | --- | --- |

### 7.2 <风险、偏差与阻塞>

| ID | <风险 / 偏差 / 阻塞> | <级别> | <影响> | <缓解方案> | <负责人> | <必须解决阶段> |
| --- | --- | --- | --- | --- | --- | --- |

### 7.3 <待确认问题>

| ID | <问题> | <默认处理 / 是否可继续> | <负责人> | <确认时点> |
| --- | --- | --- | --- | --- |

## 8. <验收与就绪度>

### 8.1 <验收标准>

| ID | <关联需求> | <可验证结果> | <实现证据 / 验证方法> | <状态> |
| --- | --- | --- | --- | --- |

### 8.2 <推进就绪度>

| <阶段> | <状态> | <已具备证据> | <缺口 / 负责人> | <下一动作> |
| --- | --- | --- | --- | --- |
| <产品评审> |  |  |  |  |
| <研发交接> |  |  |  |  |
| <上线决策> |  |  |  |  |

## 9. <实现证据与覆盖映射>

### 9.1 <代码与资源位置>

| ID | <类型> | <路径 / 标识> | <证明的行为> | <关联需求> |
| --- | --- | --- | --- | --- |

### 9.2 <需求覆盖检查>

| <实现行为> | <是否写入 PRD> | <是否有验收> | <未解决的产品意图> |
| --- | --- | --- | --- |

## 10. <验证结果>

| <检查项 / 命令> | <结果> | <覆盖范围> | <证据 / 限制> |
| --- | --- | --- | --- |

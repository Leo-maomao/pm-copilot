# PM Copilot

<p align="center"><strong>简体中文</strong> | <a href="README.en.md">English</a></p>

<a id="zh-cn"></a>

PM Copilot 是一个开源、平台中立的产品经理 Agent Workflow Kit。它帮助产品经理把模糊的产品需求转化为两个可交接成果：完整 PRD 和带标注的可点击原型。

项目刻意不做成 Web 应用、CLI 或 Figma 插件，而是提供一套可复用的仓库资产：Agent 定义、技能、提示词规则、记忆规则、产物契约、工作流规则、护栏和模板。它可以适配 Codex、Claude Code、Cursor 或内部 Agent 平台等环境。

PM Copilot 支持三种上下文模式：`repo-backed`、`document-backed`、`brief-only`。Agent 应该根据可用输入先判断模式再开始起草，因此不要求每次都有代码仓库；如果产品文档或一段简要需求才是起点，也可以正常工作。

## 语言支持

PM Copilot 将中文和英文都视为一等用户语言。生成的 PM 产物、原型文案、原型标注、评审发现、就绪状态和验证说明都应跟随用户语言，并保持同一套工作流、产物范围和质量标准。文件名、事件名、属性名、需求 ID 和其他机器可读标识保持 ASCII，便于跨平台使用。

## 产出内容

- 适合产品、设计、研发、QA 和数据分析评审的 `prd.md`
- PRD 内的版本记录、需求输入、澄清答案、假设和待确认事项
- 调研和参考结论，优先包含外部竞品、同类功能、用户研究或公开方案来源；当前实现只作为产品上下文和工程约束
- 需求列表和详细需求表，覆盖逻辑、内容、规则、交互、数据、权限、边界状态、埋点链接和验收链接
- PRD 内的目标、指标、埋点方案和流程图
- 适用于 Web、H5、App 或小程序场景的本地可点击标注 HTML 原型
- 必要时作为内部追踪使用的 `run-log.yaml`，不作为面向 PM 的交付件
- 工具预检、交付总控校验、HTML 解析、浏览器截图和可选视觉差异验证；缺少 Playwright/浏览器时先运行安装辅助脚本
- 按需生成用于研发交接和上线决策支持的 `dev-tasks.yaml` 和 `launch-decision.yaml`

## 快速开始

直接使用 Agent 时请看 `docs/direct-use.md`。嵌入到现有项目中使用时请看 `docs/embedded-use.md`。

1. 在支持 Agent 的工作区中打开本仓库。
2. 让 Agent 读取 `PM_COPILOT.md`，然后自然描述你的产品经理需求，例如：`我需要一份会员自动续费优化的 PRD、埋点方案和 H5 原型。`
3. Agent 应先检查相关上下文，生成前询问必须澄清的问题，然后自动创建 `prd.md` 和原型。
4. 可选：之后创建本地记忆文件，以便获得更贴合产品和个人工作习惯的结果。

推荐提示词：

```text
我们想优化 H5 会员自动续费体验。用户反馈续费提醒不清楚，取消入口难找，客服工单也在增加。

如果关键信息缺失，请先问我。
如果信息足够，请创建 `prd.md` 和对应的可点击原型。
```

## 两个可直接试的 Demo

把下面任一请求直接粘贴给支持 Agent 的工作区。PM Copilot 会先识别上下文模式，加载必要 Agent、技能、契约和工具规则；缺关键信息时先问问题，信息足够后再生成 PRD、可点击原型、运行追踪和可选交接材料。

### Demo 1：已有项目里的团队权限管理

适合证明 PM Copilot 不只是写通用文档，而是会读取现有代码仓库，贴合当前产品结构、权限模型、路由、UI 组件和埋点约定；同时把外部参考、当前产品上下文和研发交接任务分开记录。

![团队权限管理 Demo 截图](docs/assets/readme-demo-team-permissions.png)

```text
我们要在后台管理端做团队权限管理。

请先检查现有项目里的路由、角色模型、成员管理页面、权限判断、埋点约定和组件风格。
需要做少量外部同类产品参考，但不要把仓库文件当成竞品调研。
如果关键信息不够，请先问我。
如果信息足够，请输出 PRD、Web 可点击标注原型，并补一份可转 issue 的研发任务拆分。
```

一次有效运行应能产出：

| 产物 | 应该看到什么 |
|---|---|
| `outputs/team-permissions/prd.md` | 目标用户、当前产品约束、外部参考结论、MVP/可选/未来范围、成员邀请、角色变更、权限拦截、审计记录、加载/空/错误/无权限状态 |
| `outputs/team-permissions/prototype-web.html` | 复用现有后台壳层和表格密度的 Web 原型，使用红色组件角标、点击标注弹层和当前状态标注列表 |
| `outputs/team-permissions/dev-tasks.yaml` | 可转 issue 的研发任务、依赖关系、验收标准、测试建议、相关宿主项目文件和阻塞确认项 |
| `outputs/team-permissions/run-log.yaml` | 上下文模式、读取过的宿主项目文件、外部调研来源、样式证据、现有 UI 基线、工具校验和未解决风险 |

这个 Demo 重点展示：`repo-backed` 上下文读取、外部调研和仓库上下文分离、中文 PRD、现有 UI 增量原型、红色组件标注、研发交接、权限和边界状态覆盖。

### Demo 2：没有代码仓库的会员自动续费优化

适合证明 PM Copilot 可以从一段模糊业务描述或产品文档出发，不依赖代码仓库，也能处理支付、取消、提醒、埋点、隐私和上线门禁这类更高风险的产品需求。

![会员自动续费 Demo 截图](docs/assets/readme-demo-membership-renewal.png)

```text
我们想优化 H5 会员自动续费体验。用户反馈续费提醒不清楚，取消入口难找，客服工单也在增加。

业务目标是降低续费相关投诉，同时不要误伤会员留存。
如果需要我补充当前扣费规则、提醒周期、取消路径、客服口径、法务要求或指标口径，请先问我。
信息足够后，请输出 PRD、H5 可点击标注原型、埋点方案，并给出上线决策建议。
```

一次有效运行应能产出：

| 产物 | 应该看到什么 |
|---|---|
| `outputs/membership-renewal/prd.md` | 用户问题、业务目标、外部参考、当前假设、提醒策略、取消链路、支付/客服/法务风险、验收标准和上线状态 |
| `outputs/membership-renewal/prototype-h5.html` | 会员中心入口、续费提醒、自动续费管理、取消确认、结果回执、未登录/无会员/接口失败等访问态和边界状态 |
| PRD 内埋点表 | `renewal_notice_view`、`renewal_manage_open`、`renewal_cancel_submit`、`renewal_cancel_result` 等事件和隐私说明 |
| `outputs/membership-renewal/launch-decision.yaml` | 工程可交接范围、上线阻塞项、法务/支付/客服 owner、回滚建议和人工批准缺口 |
| `outputs/membership-renewal/run-log.yaml` | 澄清问题、默认假设、外部调研状态、访问态视觉校验、工具结果和未确认门禁 |

这个 Demo 重点展示：`document-backed` 或 `brief-only` 模式、中文交付、移动端原型、访问态一致性、指标和埋点、支付/隐私/法务风险显性化，以及工程交接和上线决策状态分离。

## 在现有项目中使用

如果要把 PM Copilot 引入真实软件项目，推荐结构如下：

```text
host-repo/
|-- AGENTS.md or CLAUDE.md or .cursor/rules/
|-- src/
`-- pm-copilot/
    `-- PM_COPILOT.md
```

将本仓库复制或 clone 到宿主项目的 `pm-copilot/` 目录，然后在宿主仓库根目录安装一个小型适配器：

```bash
cd host-repo/pm-copilot
python3 scripts/install_adapter.py --host .. --tool all
```

嵌入式使用时适配器是必要的。仅把 `pm-copilot/` 文件夹放入另一个项目，并不能保证 Codex、Claude Code、Cursor 或其他 Agent 自动发现嵌套说明。

在嵌入模式下，PM Copilot 起草前应先检查当前宿主项目。现有路由、数据模型、UI 模式、权限、埋点约定和文档都会影响新需求；除非你明确要求绿地方案，Agent 不应假设这是一个全新产品。

适配器安装后，用户可以在宿主项目中直接提出自然语言 PM 需求，无需点名 PM Copilot：

```text
帮我写团队权限管理的 PRD 和可点击原型。
```

详情和手动适配器片段请看 `docs/embedded-use.md`。

## 不依赖代码仓库使用

产品经理不需要软件仓库也可以使用 PM Copilot。如果产品上下文在文档里，把相关文件放入或附加到工作区，然后自然提问即可。

可用上下文包括：

- 历史 PRD、规格文档和发版记录
- 产品文档、截图、线框图和原型说明
- 调研摘要、用户反馈、客服工单和会议纪要
- 分析导出、KPI 定义和现有埋点方案
- 业务规则、合规约束、定价说明和灰度计划

PM Copilot 应把这些文档作为当前产品上下文读取；当文档不足时先询问必须回答的问题；澄清门通过后再生成 `prd.md` 和原型。

## 仓库结构

```text
PM_COPILOT.md  跨平台 PM Copilot 主入口
adapters/      Codex、Claude Code、Cursor 等宿主项目适配器
agents/        Agent 角色、职责、输入、输出和交接
skills/        可复用的 PM 方法和任务技能
prompts/       提示词组装、记忆使用、澄清和生成规则
context/       产品记忆、用户偏好、决策、业务规则和指标
workflow/      状态机、人工检查点和执行顺序
artifacts/     输出契约和质量标准
tools/         工具注册表、使用协议和分能力工具说明
guardrails/    安全、隐私、来源、假设和故障转移规则
templates/     可复用产物模板
evals/         面向回归的评估用例
docs/          用户、维护者和发版文档
scripts/       轻量级本地校验
```

## 核心工作流

```text
需求接收
-> 工具预检
-> 当前产品上下文扫描
-> 需求澄清
-> 用户回答或明确批准假设
-> 包含目标、调研、需求、指标、埋点和流程的 PRD
-> 多平台可点击原型
-> 交付检查
```

默认交互模式是“先澄清，再生成”。如果缺少必须回答的信息，Agent 应先提问并停止，不创建 PRD 或原型交付件。只有在用户回答或明确接受假设风险后才继续。PRD 状态、研发交接状态和上线状态是相互独立的：阻塞研发交接的确认项会阻止标记为“可交接研发”；只阻塞上线的事项必须保留 owner 和所需确认。

对于政策、医疗、法律、金融、安全或运营内容，PM Copilot 会记录来源状态、评审 owner、评审状态、免责声明状态和上线影响。未经评审的内容必须标记为占位或草稿，即使周边产品框架已经可以交接研发。

每次真实需求运行都会在 `outputs/<run-id>/` 下生成一个产物目录，通常包含 `prd.md`、`prototype-<platform>.html`，可选包含 `run-log.yaml`。`outputs/` 目录在运行时生成，不随仓库发布示例产物。如果推断出的 run id 已存在，PM Copilot 应追加本地时间戳，例如 `membership-renewal-20260518-1430`。

生成 UI 原型时，PM Copilot 应运行 `python3 scripts/validate_prototype_visual.py outputs/<run-id>`。如果缺少 Playwright 或浏览器工具，应先运行或引导 `python3 scripts/setup_visual_validation.py`；只有安装失败、环境禁止启动浏览器，或用户拒绝安装时，才允许记录跳过原因。最终交付前应优先运行 `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh`，并把工具证据写入 `outputs/<run-id>/tool-results/`。当用户请求研发交接或上线就绪检查时，同一个运行目录也可以包含 `dev-tasks.yaml` 和 `launch-decision.yaml`。

PM Copilot 会跟随用户语言生成产物：中文请求应生成中文标题、标签、状态、说明和 PM 内容；英文请求应生成英文等价内容。文件名和机器可读标识保持 ASCII。

## 记忆

PM Copilot 使用本地文件记忆，让重复使用更顺手，同时不依赖托管服务：

- `context/product-memory.local.yaml` 存放稳定产品事实
- `context/user-preferences.local.yaml` 存放用户工作风格
- `context/decision-log.local.yaml` 存放长期产品决策
- `outputs/<run-id>/run-log.yaml` 存放单次运行追踪
- `outputs/<run-id>/tool-results/delivery-check-report.json` 存放交付总控工具报告
- `outputs/<run-id>/visual-review/visual-report.json` 存放完成 Playwright/浏览器安装或配置后的原型截图和视觉差异证据
- `outputs/<run-id>/dev-tasks.yaml` 存放按需生成、可转 issue 的研发交接内容
- `outputs/<run-id>/launch-decision.yaml` 存放按需生成的上线决策支持内容

仓库只提供 `.example.yaml` schema。`.local.yaml` 记忆文件会被 Git 忽略，应保持私有。当前用户指令和当前产品上下文始终优先于记忆。

## 平台中立设计

PM Copilot 不绑定特定 Agent 框架。每个 Agent 和技能都是可移植的 Markdown 契约：

- Agent 定义职责、输入、输出、决策点、交接和故障转移行为。
- 技能定义可复用流程、标准和产物规则。
- 提示词规则定义需求分类、记忆使用、澄清行为和生成边界。
- 产物契约定义必要输出结构和最低质量标准。
- 护栏定义 Agent 不能编造或静默假设的内容。

## 技能层

`skills/` 存放可复用的产品工作方法。`PM_COPILOT.md` 和各 Agent 只在命中场景时加载相关技能，避免把整套技能塞进上下文。

| 分组 | 技能 |
|---|---|
| 需求和范围 | `requirement-intake`、`opportunity-discovery`、`feedback-synthesis`、`process-mapping`、`knowledge-ops`、`scope-edge-cases` |
| PRD 和交付 | `prd-writing`、`user-stories`、`user-flow`、`acceptance-criteria`、`review-checklist`、`artifact-packaging`、`development-handoff` |
| 指标和数据 | `metrics-tree`、`tracking-plan`、`experiment-design`、`product-ops-analysis` |
| 调研和沟通 | `competitor-research`、`roadmap-communication` |
| 原型和 UI 证据 | `multi-platform-prototype`、`design-system-audit` |
| 工具和能力治理 | `tool-vetting`、`sharingan` |

同一能力类型只保留一个 canonical skill。吸收外部资源时用 `skills/sharingan/SKILL.md` 做风险检查和合并，不新增重复技能。

## 外部工具治理

PM Copilot 可以接入 Figma、浏览器验证、文档系统、项目管理、数据分析、CRM、自动化平台等外部工具，但这些工具不会因为出现在推荐列表里就被视为可用。

- `tools/external-tool-catalog.json` 记录候选工具、来源类型、成本风险、凭据要求、数据风险、权限边界和 fallback。
- `agents/integration-governance-agent.md` 和 `skills/tool-vetting/SKILL.md` 负责在使用前做工具评估。
- `python3 scripts/preflight_integrations.py --tier recommended` 会检查推荐层级工具的本地运行条件、缺失凭据和候选状态。
- 需要 API key、OAuth、商业账号、工作区权限或写操作的工具默认都是可选项，不能静默启用。
- 数据库、分析、CRM、客服、投放和协作系统默认走只读/最小权限；写入、发布、改预算、改工单、发消息等动作必须有明确用户批准。

## 文档

- `README.en.md` - 英文 README
- `docs/direct-use.md` - 直接一次性 Agent 使用方式
- `docs/embedded-use.md` - 在另一个开发仓库内使用 PM Copilot
- `docs/configuration.md` - 产品上下文配置
- `docs/quality-rubric.md` - 生成 PRD 和原型交付的人工评分标准
- `docs/optimization-playbook.md` - 真实任务优化循环
- `docs/failure-taxonomy.md` - 失败分类和修复映射
- `docs/versioning.md` - 版本和兼容性策略
- `docs/release-checklist.md` - 发版就绪清单
- `tools/tool-registry.yaml` - 工具能力注册表
- `artifacts/tool-result-contract.md` - 工具结果契约
- `CONTRIBUTING.md` - 贡献规则
- `SECURITY.md` - 安全和隐私策略
- `CHANGELOG.md` - 详细版本历史

## 反馈和贡献

欢迎通过 GitHub issues 提交真实使用反馈：

- Bug 反馈：`.github/ISSUE_TEMPLATE/bug_report.md`
- 功能建议：`.github/ISSUE_TEMPLATE/feature_request.md`
- 场景请求：`.github/ISSUE_TEMPLATE/scenario_request.md`

请优先使用合成或脱敏的产品上下文。不要在公开 issue 中提交私有产品数据、凭证、未公开财务信息或真实用户数据。

## 嵌入式安装

当 PM Copilot 嵌套在另一个开发仓库内时，在宿主项目中安装小型适配器：

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool all
```

安装后，用户可以直接提出自然 PM 需求，无需说出项目名。

## 校验

运行：

```bash
python3 scripts/preflight_tools.py --strict
python3 scripts/validate_repo.py
```

`.github/workflows/validate.yml` 中的 GitHub workflow 会在 push 和 pull request 上运行同一校验器。

在 PM Copilot 运行期间校验生成目录：

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
python3 scripts/validate_outputs.py outputs/<run-id> --language zh
```

如果本次交付依赖外部调研或来源校验，请使用 `python3 scripts/preflight_tools.py --check-network <url> --require-network --strict` 做网络能力预检。`validate_prototype_visual.py` 在未指定 `--prototype` 时会校验运行目录中的全部受支持原型文件。

## 优化

PM Copilot 应通过真实任务运行、追踪记录、质量评分、失败分类和回归用例持续改进。

从这些文件开始：

- `docs/optimization-playbook.md`
- `docs/failure-taxonomy.md`
- `docs/quality-rubric.md`
- `templates/agent-run-log-template.yaml`
- `templates/dev-tasks-template.yaml`
- `templates/launch-decision-template.yaml`
- `templates/evaluation-case-template.md`

## 隐私默认值

默认使用本地文件。不要粘贴敏感生产数据、用户个人数据、私有凭证、未公开财务信息或保密合作方信息，除非你的环境已被批准处理这些数据。需要真实业务上下文时，优先使用匿名化示例和抽样指标。

## 许可证

MIT License。见 `LICENSE`。

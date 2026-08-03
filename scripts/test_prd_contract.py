#!/usr/bin/env python3
"""Deterministic regression tests for the user-driven Chinese PRD contract."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from validate_outputs import check_chinese_prd, check_implemented_feature_prd_trace, check_prd_output_contract, check_stale_validation


PASS_PRD = """# 优化团队权限变更体验 - 2026-07-10

## 一、文档说明

### 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 需求来源 | 管理员反馈 |
| 目标用户 | 团队管理员 |
| 影响范围 | 成员管理 |
| 文档状态 | 可评审 |

### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- | --- |
| v0.1 | 2026-07-10 | 首次创建 | 产品 |

## 二、需求背景

团队管理员调整成员角色时容易误操作，需要在关键变更前获得清晰反馈并能恢复。

## 四、需求清单

| 详情编号 | 需求名称 | 目标用户 | 用户场景 / 触发 | 用户问题或价值 | 需求摘要 | 优先级 | 来源 / 确认状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 5.1 | 角色变更确认 | 团队管理员 | 在成员页修改高危角色 | 降低误操作 | 高危角色变更需要确认与可恢复反馈 | P0 | 用户确认 |

## 五、需求详情

### 5.1 角色变更确认

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 作为团队管理员，我希望在成员页修改高危角色时确认影响，避免误操作。 |
| 需求入口 | 团队管理员在成员页修改高危角色时触发。 |
| 需求详情 | 一、角色变更流程<br>1. 管理员修改高危角色。<br>2. 系统展示确认信息。<br>3. 管理员确认后完成变更。<br>二、状态与边界<br>1. 保存中显示加载。<br>2. 无权限用户不可操作。<br>3. 保存错误时保留原角色并允许重试。<br>4. 成员为空时展示空状态。 |
| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |

## 六、多语言需求

```text
确认变更角色
取消
```

| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 确认变更角色 | 5.1 角色变更确认 | / |
| 取消 | 5.1 角色变更确认 | / |

## 七、埋点需求

| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |
| --- | --- | --- | --- | --- |
| 查看成员管理页 | member_management_view | 页面完成首屏展示时 | / | 评估入口访问与后续角色变更转化。 |
| 点击高危角色变更 | high_risk_role_change_click | 用户点击确认变更角色时 | 变更前角色、变更后角色、成员标识 | 评估高危角色变更意图。 |
| 高危角色变更结果展示 | high_risk_role_change_result | 操作结果展示时 | 变更结果、失败原因类型 | 区分成功与可恢复失败。 |
| 成员列表有效浏览 | member_list_engagement | 用户离开页面或达到有效浏览阈值时 | 浏览时长、最大滚动深度、有效成员曝光数量 | 评估成员信息浏览深度。 |
"""


def run_case(
    name: str,
    prd: str,
    should_pass: bool,
    run_log: str = "source_mode: brief-only\n",
    check_implemented_trace: bool = False,
    assets: dict[str, bytes] | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)
        (folder / "prd.md").write_text(prd, encoding="utf-8")
        (folder / "run-log.yaml").write_text(run_log, encoding="utf-8")
        for asset_path, content in (assets or {}).items():
            destination = folder / asset_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        if check_implemented_trace:
            (folder / "prd.html").write_text("<html></html>", encoding="utf-8")
        passed = True
        try:
            check_chinese_prd(folder)
            check_prd_output_contract(folder, language="zh")
            check_stale_validation(folder)
            if check_implemented_trace:
                check_implemented_feature_prd_trace(folder)
        except SystemExit:
            passed = False
        if passed != should_pass:
            expectation = "pass" if should_pass else "fail"
            raise SystemExit(f"FAIL {name}: expected {expectation}")
        print(f"PASS {name}: {'accepted' if passed else 'rejected'}")


def main() -> None:
    run_case("user_driven_prd", PASS_PRD, True)
    run_case(
        "research_section_keeps_order",
        PASS_PRD.replace("## 四、需求清单", "## 三、需求调研\n\n- 访谈显示用户需要先核对角色影响。\n\n## 四、需求清单"),
        True,
    )
    run_case(
        "implemented_feature_product_only_prd",
        PASS_PRD,
        True,
        "implemented_feature_prd:\n  active: true\n",
    )
    run_case(
        "tracking_renumbered_when_localization_omitted",
        PASS_PRD.replace("## 六、多语言需求\n\n```text\n确认变更角色\n取消\n```\n\n| 文案 | 使用位置 | 参数 |\n| --- | --- | --- |\n| 确认变更角色 | 5.1 角色变更确认 | / |\n| 取消 | 5.1 角色变更确认 | / |\n\n## 七、埋点需求", "## 六、埋点需求"),
        True,
    )
    run_case(
        "tracking_number_jump_when_localization_omitted",
        PASS_PRD.replace("## 六、多语言需求\n\n```text\n确认变更角色\n取消\n```\n\n| 文案 | 使用位置 | 参数 |\n| --- | --- | --- |\n| 确认变更角色 | 5.1 角色变更确认 | / |\n| 取消 | 5.1 角色变更确认 | / |\n\n", ""),
        False,
    )
    run_case(
        "implemented_feature_ui_surfaces_need_visual_coverage",
        PASS_PRD,
        False,
        "implemented_feature_prd:\n  active: true\n  ui_surfaces:\n    - surface: 登录弹窗\n",
        True,
    )
    fixture_asset = b"fixture-image"
    fixture_hash = hashlib.sha256(fixture_asset).hexdigest()
    implemented_trace = f"""implemented_feature_prd:
  active: true
  diff_commands:
    - git diff --stat
  changed_files:
    - app/ui.tsx
  ui_surfaces:
    - surface: 确认弹窗
  behavior_evidence:
    - evidence_id: E1
      observed_behavior: 用户确认关键变更。
      related_requirement_ids:
        - 5.1
      coverage_status: covered
  screenshots_and_placeholders:
    - target_ref: 5.1
      coverage_decision: real_figure
      rationale: 确认操作需要可视评审。
      path: assets/role-confirmation.png
      capture_source: fixture
      asset_sha256: {fixture_hash}
  validation_evidence: []
  completeness_check:
    implementation_behaviors_checked:
      - 确认操作
    represented_in_prd:
      - 5.1
    unresolved_product_intent:
      - 无
"""
    run_case(
        "implemented_feature_real_figure_matches_requirement_and_asset",
        PASS_PRD.replace(
            "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n\n## 六、多语言需求",
            "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n| 图示 | ![角色变更确认](./assets/role-confirmation.png)<small>角色变更确认</small> |\n\n## 六、多语言需求",
        ),
        True,
        implemented_trace,
        True,
        {"assets/role-confirmation.png": fixture_asset},
    )
    placeholder_trace = """implemented_feature_prd:
  active: true
  diff_commands:
    - git diff --stat
  changed_files:
    - app/ui.tsx
  ui_surfaces:
    - surface: 确认弹窗
  behavior_evidence:
    - evidence_id: E1
      observed_behavior: 用户确认关键变更。
      related_requirement_ids:
        - 5.1
      coverage_status: covered
  screenshots_and_placeholders:
    - target_ref: 5.1
      surface: 角色变更确认弹窗
      state: 确认弹窗
      coverage_decision: required_placeholder
      rationale: 确认操作需要可视评审，但当前会话无法访问受保护页面。
      capture_source: 浏览器会话被访问守卫重定向，截图恢复失败。
      capture_attempt_ids:
        - visual-playwright
        - visual-devtools
        - visual-computer-use
      replacement_status: pending_manual_completion
      replacement_instruction: 人工登录目标工作流后补齐“角色变更确认”截图。
  visual_capture_recovery:
    - attempt_id: visual-playwright
      method: playwright
      target: 本地预览
      status: blocked
      evidence: 未获得可用登录态。
    - attempt_id: visual-devtools
      method: chrome_devtools
      target: 已认证浏览器会话
      status: blocked
      evidence: 页面守卫重定向。
    - attempt_id: visual-computer-use
      method: computer_use
      target: 本地浏览器
      status: blocked
      evidence: 无可用身份会话。
  validation_evidence: []
  completeness_check:
    implementation_behaviors_checked:
      - 确认操作
    represented_in_prd:
      - 5.1
    unresolved_product_intent:
      - 无
readiness:
  prd_status: ready for review
"""
    placeholder_prd = PASS_PRD.replace(
        "| 文档状态 | 可评审 |",
        "| 文档状态 | 可评审（图示待人工补全） |",
    ).replace(
        "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n\n## 六、多语言需求",
        "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n| 图示 | 占位图：成员管理-角色变更确认.png |\n\n## 六、多语言需求",
    )
    run_case(
        "implemented_feature_placeholder_is_deliverable_with_manual_completion",
        placeholder_prd,
        True,
        placeholder_trace,
        True,
    )
    run_case(
        "implemented_feature_placeholder_requires_visible_manual_notice",
        placeholder_prd.replace("（图示待人工补全）", ""),
        False,
        placeholder_trace,
        True,
    )
    run_case(
        "implemented_feature_figure_row_must_be_last",
        placeholder_prd.replace(
            "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n| 图示 | 占位图：成员管理-角色变更确认.png |",
            "| 图示 | 占位图：成员管理-角色变更确认.png |\n| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |",
        ),
        False,
        placeholder_trace,
        True,
    )
    run_case(
        "implemented_feature_placeholder_must_not_include_explanatory_text",
        placeholder_prd.replace("占位图：成员管理-角色变更确认.png", "占位图：成员管理-角色变更确认.png（待人工补图）"),
        False,
        placeholder_trace,
        True,
    )
    run_case("missing_document_info", PASS_PRD.replace("### 1. 文档信息", "### 1. 说明"), False)
    run_case("missing_user_requirement_field", PASS_PRD.replace("目标用户", "用户群体"), False)
    run_case("missing_matching_detail", PASS_PRD.replace("### 5.1 角色变更确认", "### 5.2 角色变更确认"), False)
    run_case("duplicate_requirement_id", PASS_PRD.replace("### 5.1 角色变更确认", "### 5.1 R1 角色变更确认"), False)
    run_case(
        "duplicate_requirement_list_number",
        PASS_PRD.replace("\n## 五、需求详情", "\n| 5.1 | 重复需求 | 团队管理员 | 重复触发 | 重复问题 | 重复摘要 | P1 | 用户确认 |\n\n## 五、需求详情"),
        False,
    )
    run_case(
        "duplicate_requirement_detail_number",
        PASS_PRD.replace("\n## 六、多语言需求", "\n### 5.1 重复详情\n\n| 维度 | 需求说明 |\n| --- | --- |\n| 用户与场景 | 团队管理员需要处理重复详情。 |\n| 需求入口 | 成员页。 |\n| 需求详情 | 展示重复详情。 |\n| 设计与交互 | 保持可读。 |\n\n## 六、多语言需求"),
        False,
    )
    run_case("missing_detail_field", PASS_PRD.replace("| 需求入口 | 团队管理员在成员页修改高危角色时触发。 |\n", ""), False)
    run_case(
        "forbidden_acceptance_field",
        PASS_PRD.replace(
            "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |",
            "| 设计与交互 | 确认弹窗突出角色变化与取消操作；键盘焦点停留在弹窗内。 |\n"
            "| 验收标准 | 管理员可完成角色变更。 |",
        ),
        False,
    )
    run_case(
        "flowchart_must_precede_detail_table",
        PASS_PRD.replace(
            "## 六、多语言需求",
            """```mermaid
flowchart TD
  A[开始] --> B[确认]
```

## 六、多语言需求""",
        ),
        False,
    )
    run_case("explanatory_copy_label", PASS_PRD.replace("## 六、多语言需求", "## 六、多语言需求\n\n### 6.1 新增文案（纯文本）"), False)
    run_case("technical_section", PASS_PRD + "\n## 八、技术方案\n\n说明实现架构。\n", False)
    run_case(
        "technical_field",
        PASS_PRD.replace("| 详情编号 | 需求名称 |", "| 详情编号 | 文件路径 |"),
        False,
    )
    run_case(
        "technical_detail_content",
        PASS_PRD.replace("管理员修改高危角色。<br>2.", "前端 RoleDialog 调用 POST /api/members/role。<br>2."),
        False,
    )
    run_case(
        "flat_requirement_detail_rules",
        PASS_PRD.replace(
            "一、角色变更流程<br>1. 管理员修改高危角色。<br>2. 系统展示确认信息。<br>3. 管理员确认后完成变更。<br>二、状态与边界<br>1. 保存中显示加载。<br>2. 无权限用户不可操作。<br>3. 保存错误时保留原角色并允许重试。<br>4. 成员为空时展示空状态。",
            "1. 管理员修改高危角色。2. 系统展示确认信息。3. 管理员确认后完成变更。4. 保存中显示加载，无权限用户不可操作，保存错误时保留原角色并允许重试，成员为空时展示空状态。",
        ),
        False,
    )
    run_case(
        "blank_requirement_detail_group_separator",
        PASS_PRD.replace("<br>二、状态与边界", "<br><br>二、状态与边界"),
        False,
    )
    run_case(
        "controlled_screenshot_placeholder",
        PASS_PRD.replace("| 设计与交互 |", "| 图示 | 占位图：成员管理-角色变更.png |\n| 设计与交互 |"),
        True,
    )
    run_case(
        "invalid_screenshot_placeholder",
        PASS_PRD.replace("| 设计与交互 |", "| 图示 | 占位图：成员管理-角色变更 |\n| 设计与交互 |"),
        False,
    )
    run_case(
        "placeholder_requires_feature_state_name",
        placeholder_prd.replace("成员管理-角色变更确认.png", "角色变更确认.png"),
        False,
        placeholder_trace,
        True,
    )
    run_case(
        "descriptive_figure_caption",
        PASS_PRD.replace(
            "| 设计与交互 |",
            "| 图示 | ![角色变更确认](./assets/role-confirmation.png)<small>角色变更确认.png；本地 Demo 实测截图。</small> |\n| 设计与交互 |",
        ),
        False,
        implemented_trace,
        True,
        {"assets/role-confirmation.png": fixture_asset},
    )
    run_case(
        "double_figure_gap",
        PASS_PRD.replace(
            "| 设计与交互 |",
            "| 图示 | ![角色变更确认](./assets/role-confirmation.png)<small>角色变更确认</small><br><br>![角色变更结果](./assets/role-confirmation.png)<small>角色变更结果</small> |\n| 设计与交互 |",
        ),
        False,
        implemented_trace,
        True,
        {"assets/role-confirmation.png": fixture_asset},
    )
    run_case("operation_only_version", PASS_PRD.replace("首次创建", "重新渲染文档"), False)
    run_case("template_guidance", PASS_PRD.replace("降低误操作", "<说明目标用户的问题>"), False)
    run_case("proposed_prd_copy", PASS_PRD.replace("用户确认", "拟议"), False)
    run_case("vague_requirement_summary", PASS_PRD.replace("降低误操作", "帮助用户更清楚、更高效地完成当前任务"), False)
    run_case("generic_tracking_event", PASS_PRD.replace("查看成员管理页", "访问"), False)
    run_case(
        "tracking_param_placeholder",
        PASS_PRD.replace(
            "| 查看成员管理页 | member_management_view | 页面完成首屏展示时 | / |",
            "| 查看成员管理页 | member_management_view | 页面完成首屏展示时 | 无 |",
        ),
        False,
    )
    run_case("tracking_prd_position_identifier", PASS_PRD.replace("member_management_view", "prd_5_1_view"), False)
    run_case("tracking_generic_journey_identifier", PASS_PRD.replace("member_management_view", "journey_view"), False)
    run_case(
        "tracking_version_number_timing",
        PASS_PRD.replace(
            "| 点击高危角色变更 | high_risk_role_change_click | 用户点击确认变更角色时 |",
            "| 选择 Seedance 2.5 | seedance_2_5_select | 用户选择 Seedance 2.5 时 |",
        ),
        True,
    )
    run_case(
        "ordinary_waiting_phrase_is_not_a_stale_placeholder",
        PASS_PRD.replace("降低误操作", "不必等待执行结束即可继续整理下一步操作"),
        True,
    )
    run_case("standalone_stale_validation_placeholder", PASS_PRD + "\n待执行\n", False)
    run_case(
        "tracking_duplicate_identifier",
        PASS_PRD.replace("high_risk_role_change_click", "member_management_view"),
        False,
    )
    run_case(
        "missing_localization_usage_checklist",
        PASS_PRD.replace("| 文案 | 使用位置 | 参数 |\n| --- | --- | --- |\n| 确认变更角色 | 5.1 角色变更确认 | / |\n| 取消 | 5.1 角色变更确认 | / |\n\n", ""),
        False,
    )
    run_case(
        "localization_placeholder_parameter",
        PASS_PRD.replace("取消\n```", "操作失败：{reason}\n```").replace(
            "| 取消 | 5.1 角色变更确认 | / |", "| 操作失败：{reason} | 5.1 角色变更确认 | {reason} |"
        ),
        True,
    )
    run_case(
        "chinese_localization_rejects_english_source_copy",
        PASS_PRD.replace("取消\n```", "Cancel\n```").replace(
            "| 取消 | 5.1 角色变更确认 | / |", "| Cancel | 5.1 角色变更确认 | / |"
        ),
        False,
    )


if __name__ == "__main__":
    main()

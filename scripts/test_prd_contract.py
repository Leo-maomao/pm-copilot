#!/usr/bin/env python3
"""Deterministic regression tests for the user-driven Chinese PRD contract."""

from __future__ import annotations

import tempfile
from pathlib import Path

from validate_outputs import check_chinese_prd, check_prd_output_contract, check_stale_validation


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
| 需求详情 | 1. 管理员修改高危角色。2. 系统展示确认信息。3. 管理员确认后完成变更。4. 保存中显示加载，无权限用户不可操作，保存错误时保留原角色并允许重试，成员为空时展示空状态。 |
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


def run_case(name: str, prd: str, should_pass: bool, run_log: str = "source_mode: brief-only\n") -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)
        (folder / "prd.md").write_text(prd, encoding="utf-8")
        (folder / "run-log.yaml").write_text(run_log, encoding="utf-8")
        passed = True
        try:
            check_chinese_prd(folder)
            check_prd_output_contract(folder, language="zh")
            check_stale_validation(folder)
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
    run_case("missing_document_info", PASS_PRD.replace("### 1. 文档信息", "### 1. 说明"), False)
    run_case("missing_user_requirement_field", PASS_PRD.replace("目标用户", "用户群体"), False)
    run_case("missing_matching_detail", PASS_PRD.replace("### 5.1 角色变更确认", "### 5.2 角色变更确认"), False)
    run_case("duplicate_requirement_id", PASS_PRD.replace("### 5.1 角色变更确认", "### 5.1 R1 角色变更确认"), False)
    run_case("missing_detail_field", PASS_PRD.replace("| 需求入口 | 团队管理员在成员页修改高危角色时触发。 |\n", ""), False)
    run_case("explanatory_copy_label", PASS_PRD.replace("## 六、多语言需求", "## 六、多语言需求\n\n### 6.1 新增文案（纯文本）"), False)
    run_case("technical_section", PASS_PRD + "\n## 八、技术方案\n\n说明实现架构。\n", False)
    run_case(
        "technical_field",
        PASS_PRD.replace("| 详情编号 | 需求名称 |", "| 详情编号 | 文件路径 |"),
        False,
    )
    run_case(
        "controlled_screenshot_placeholder",
        PASS_PRD.replace("| 设计与交互 |", "| 图示 | 占位图：成员管理-角色变更.png<br><small>位置：成员管理页的角色编辑区域；用途：展示高危角色变更前的确认信息。</small> |\n| 设计与交互 |"),
        True,
    )
    run_case(
        "invalid_screenshot_placeholder",
        PASS_PRD.replace("| 设计与交互 |", "| 图示 | 占位图：成员管理-角色变更.png |\n| 设计与交互 |"),
        False,
    )
    run_case("operation_only_version", PASS_PRD.replace("首次创建", "重新渲染文档"), False)
    run_case("template_guidance", PASS_PRD.replace("降低误操作", "<说明目标用户的问题>"), False)
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


if __name__ == "__main__":
    main()

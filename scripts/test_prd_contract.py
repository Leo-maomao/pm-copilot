#!/usr/bin/env python3
"""Deterministic regression tests for the user-driven Chinese PRD contract."""

from __future__ import annotations

import tempfile
from pathlib import Path

from validate_outputs import check_chinese_prd


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
| 图示 | 无需补充图示。 |

## 六、多语言需求

```text
确认变更角色
取消
```
"""


def run_case(name: str, prd: str, should_pass: bool, run_log: str = "source_mode: brief-only\n") -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)
        (folder / "prd.md").write_text(prd, encoding="utf-8")
        (folder / "run-log.yaml").write_text(run_log, encoding="utf-8")
        passed = True
        try:
            check_chinese_prd(folder)
        except SystemExit:
            passed = False
        if passed != should_pass:
            expectation = "pass" if should_pass else "fail"
            raise SystemExit(f"FAIL {name}: expected {expectation}")
        print(f"PASS {name}: {'accepted' if passed else 'rejected'}")


def main() -> None:
    run_case("user_driven_prd", PASS_PRD, True)
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


if __name__ == "__main__":
    main()

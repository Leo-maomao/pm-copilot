#!/usr/bin/env python3
"""Deterministic regression tests for the decision-first Chinese PRD contract."""

from __future__ import annotations

import tempfile
from pathlib import Path

from validate_outputs import check_chinese_prd


PASS_PRD = """# 优化团队权限变更的安全性与可追溯性 - 2026-07-10

## 1. 产品决策摘要

| 决策项 | 当前判断 |
| --- | --- |
| 推荐方案 | 预设角色、高危变更二次确认和全量审计 |
| 置信度 | 中高；已有角色模型、成员页和审计接口证据 |
| PRD 状态 | 可评审 |
| 研发交接状态 | 有条件就绪 |
| 上线状态 | 阻塞 |
| 关键阻塞 | 安全负责人确认审计保留周期 |
| 下一检查点 | 安全评审；完成证据为审批记录 |

## 2. 背景与证据

管理员需要安全调整成员权限。当前产品已有成员页、角色模型和审计接口，但缺少高危操作确认。未登录和无权限用户必须被拦截。

## 3. 目标与成功标准

| ID | 产品目标 | 可观察信号 |
| --- | --- | --- |
| G1 | 降低误操作 | 高危权限误变更率下降 |

## 4. 范围与非目标

| 范围层级 | 内容 |
| --- | --- |
| MVP | 邀请选角色、角色变更确认、审计记录 |
| 可选 | 批量变更 |
| 未来 | 组织继承规则 |
| 非目标 | 自定义权限编辑器 |

## 5. 需求详情

### 5.1 R1 角色变更

| 维度 | 需求说明 |
| --- | --- |
| 用户场景与价值 | 管理员安全调整成员角色 |
| 入口 / 触发 | 成员页角色操作 |
| 主流程与业务规则 | 展示变更前后权限，高危角色必须二次确认 |
| 数据与状态 | 保存中显示加载，成员为空时显示空状态 |
| 权限与边界 | 无权限用户不可操作，接口错误时保留原值 |
| 加载 / 空 / 错误 / 恢复 | 支持重试并防止重复提交 |
| 关联目标 / 验收 | G1, AC1, AC2 |

## 6. 交付设计

### 6.1 测试重点

覆盖权限校验、重复提交、接口错误和审计写入。

## 7. 风险、决策与待确认

| ID | 风险 / 阻塞 | 负责人 |
| --- | --- | --- |
| SEC-1 | 审计保留周期未确认 | Security Owner |

## 8. 验收与就绪度

| ID | 关联需求 | 可验证结果 | 验证方法 |
| --- | --- | --- | --- |
| AC1 | R1 | 高危角色变更必须二次确认 | UI 测试 |
| AC2 | R1 | 保存期间按钮不可重复提交 | 集成测试 |
| AC3 | R1 | 接口错误后保留原角色并可重试 | 错误注入 |
| AC4 | R1 | 无权限用户无法提交变更 | 权限测试 |
"""


def run_case(name: str, prd: str, should_pass: bool) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)
        (folder / "prd.md").write_text(prd, encoding="utf-8")
        (folder / "run-log.yaml").write_text("source_mode: brief-only\n", encoding="utf-8")
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
    run_case("decision_first_prd", PASS_PRD, True)
    run_case(
        "missing_confidence",
        PASS_PRD.replace("| 置信度 | 中高；已有角色模型、成员页和审计接口证据 |\n", ""),
        False,
    )
    run_case(
        "missing_next_checkpoint",
        PASS_PRD.replace("| 下一检查点 | 安全评审；完成证据为审批记录 |\n", ""),
        False,
    )
    run_case(
        "duplicate_requirement_list",
        PASS_PRD.replace("## 5. 需求详情", "## 5. 需求列表"),
        False,
    )
    run_case(
        "missing_acceptance",
        PASS_PRD.replace("| AC1 |", "| X1 |").replace("| AC2 |", "| X2 |").replace("| AC3 |", "| X3 |").replace("| AC4 |", "| X4 |"),
        False,
    )


if __name__ == "__main__":
    main()

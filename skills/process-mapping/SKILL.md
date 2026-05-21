---
name: process-mapping
description: Use when documenting business or product operations workflows, handoffs, cycle time, bottlenecks, approvals, rework loops, or internal service processes.
---

# Process Mapping

## Goal

Map how work actually flows through people, systems, queues, approvals, and exceptions so PM decisions account for operational reality.

## Workflow

1. Define the process boundary: trigger, start state, end state, customer or internal user, and owner.
2. Capture stages with owner, system, input, output, queue time, processing time, SLA, approval, failure mode, and handoff.
3. Separate value-add work, waiting, rework, review, compliance gate, and notification steps.
4. Identify bottlenecks using cycle time, wait ratio, rework frequency, owner load, dependency concentration, and escalation count.
5. Capture exception paths, rollback, cancellation, manual override, audit logging, and customer-visible status.
6. Convert bottlenecks into product implications: automate, simplify, expose status, add guardrail, change policy, add tooling, or leave manual.
7. Link product requirements to affected process stages and operational owners.
8. State what data is estimated versus measured.

## Boundary

Use this skill for the flow of work across people, systems, queues, approvals, and exceptions. Use `skills/knowledge-ops/SKILL.md` for the documents operators read to execute that flow. Do not create separate BPMN, bottleneck, cycle-time, or handoff-analysis skills; extend this one.

## Output

- Process boundary and owner
- Stage map or swimlane-ready table
- Cycle-time and bottleneck notes
- Exception and rollback paths
- Product implications and non-goals
- Instrumentation or reporting gaps

## Quality Bar

- The map includes owners and systems, not only user-facing screens.
- Wait, rework, and approval time are visible.
- The recommendation targets the constraint instead of optimizing a non-bottleneck step.
- Manual operations and customer-visible status stay consistent.
- Estimated process data is labeled as such.

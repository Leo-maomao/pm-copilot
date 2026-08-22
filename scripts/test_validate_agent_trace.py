#!/usr/bin/env python3
"""Regression tests for YAML block-list handling in trace validation helpers."""

import unittest

from validate_agent_trace import field_has_list_item, list_field_values, mapping_item_blocks, nested_section_text, scalar_value


class TraceBlockListTests(unittest.TestCase):
    def test_same_indent_sequence_is_a_mapping_value(self) -> None:
        text = "agent_strategy:\n  success_criteria:\n  - complete delivery\n  goal: keep scope bounded\n"
        self.assertTrue(field_has_list_item(text, "success_criteria"))

    def test_nested_section_keeps_same_indent_sequence(self) -> None:
        text = "review_loop:\n  finding_closures:\n  - finding: safety\n    disposition: fixed\n  final_recommendation: blocked\n"
        closures = nested_section_text(text, "finding_closures")
        self.assertEqual(len(mapping_item_blocks(closures, "finding")), 1)

    def test_root_sequence_mapping_blocks_are_all_found(self) -> None:
        text = "- id: DEC-ONE\n  decision: first\n- id: DEC-TWO\n  decision: second\n"
        self.assertEqual(len(mapping_item_blocks(text, "id")), 2)

    def test_folded_plain_scalars_preserve_exact_review_finding(self) -> None:
        text = (
            "critical_or_high_findings:\n"
            "- Required product, engineering, privacy, security, legal, payment, launch, and\n"
            "  independent validation decisions remain unapproved.\n"
            "finding_closures:\n"
            "- finding: Required product, engineering, privacy, security, legal, payment, launch,\n"
            "    and independent validation decisions remain unapproved.\n"
        )
        expected = "Required product, engineering, privacy, security, legal, payment, launch, and independent validation decisions remain unapproved."
        self.assertEqual(list_field_values(text, "critical_or_high_findings"), [expected])
        self.assertEqual(scalar_value(mapping_item_blocks(text, "finding")[0], "finding"), expected)


if __name__ == "__main__":
    unittest.main()

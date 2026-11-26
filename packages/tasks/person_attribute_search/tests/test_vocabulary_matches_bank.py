# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from person_attribute_search.schema import ATTRIBUTE_VOCABULARY

BANK = (
    Path(__file__).resolve().parents[4]
    / "cookbooks"
    / "visual_attribute_search"
    / "question_bank.person_attributes.json"
)


def test_every_bank_option_is_in_the_pas_vocabulary() -> None:
    """A value the bank lets the VLM choose must never be reported as vocabulary drift."""
    missing = {}
    for question in json.loads(BANK.read_text(encoding="utf-8"))["questions"]:
        slot = question["id"].replace(" ", "_").replace("-", "_")
        if slot in ATTRIBUTE_VOCABULARY and question.get("options"):
            absent = [o for o in question["options"] if o not in ATTRIBUTE_VOCABULARY[slot]]
            if absent:
                missing[slot] = absent
    assert missing == {}

"""Synthetic PRODUCT LINE key for selftest_all.py (R68 line state). Not a real tenant's key.

A tenant's `PL key: <file.py>:<function>` pointer names a function like this one: one Catalog row in, one line key
out. This one reads Category and Brand only, so a fixture check can tell it from the skill's default
(intake_common.pl_key_default, which also reads the dose).
"""


def pl_of(row):
    return f"{row['Category']} | {row['Brand']}"

"""Connectivity + sanity probe for the TypeSafe (Jev) integration.

Run:  python ops/typesafe/probe.py

Proves four things, in order, and stops at the first failure:
  1. a key is resolvable (fingerprint only, never the key)
  2. GET /v1/models succeeds  -> auth works
  3. a Choice question returns a label inside the criteria we supplied
  4. a Noul question returns a probability in [0, 1]

Steps 3 and 4 use a deliberately unambiguous state, so a wrong answer means
the wiring is wrong, not that the model is uncertain.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typesafe_sdk import Choice, Noul, NoulCriteria  # noqa: E402

from jev import client, load_api_key, redact  # noqa: E402


def main() -> int:
    key = load_api_key()
    print(f"1. key resolved: {redact(key)}")

    with client() as c:
        models = c.models.list()
        names = [m.name for m in models.models]
        print(f"2. auth OK - {len(names)} model(s): {', '.join(names)}")

        result = c.system_one(
            state={
                "item": "Blueberry Gummies 10mg",
                "record": "Blueberry Gummies | 10mg | 20pk",
            },
            questions={
                "same_product": Noul(
                    instructions="The record describes the same product as the item.",
                    criteria=NoulCriteria(
                        true="The names agree on flavor and dose.",
                        false="They disagree on flavor, dose or form.",
                    ),
                ),
                "form": Choice(
                    instructions="What product form is the item?",
                    criteria={"edible": None, "flower": None, "vaporizer": None},
                ),
            },
        )

        form = result.choices["form"]
        noul = result.nouls["same_product"]
        print(f"3. choice: {form.choice!r} conf={form.confidence:.3f} probs={form.probabilities}")
        print(f"4. noul:   {noul.noul:.3f}")
        print(f"   model={result.model} tokens in/out={result.usage.input_tokens}/{result.usage.output_tokens}")

        ok = form.choice in {"edible", "flower", "vaporizer"} and 0.0 <= noul.noul <= 1.0
        if not ok:
            print("FAIL: answer outside the declared type")
            return 1
        if form.choice != "edible":
            print(f"WARN: expected 'edible' on an unambiguous state, got {form.choice!r}")
        print("\nPROBE GREEN")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

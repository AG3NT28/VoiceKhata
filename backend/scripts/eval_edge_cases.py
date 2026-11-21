"""Run labelled training examples through the deterministic parser and print a scorecard."""
from __future__ import annotations

from app.ai.dataset import NO_COMMIT_DECISIONS, expected_amount_paise, map_intent, training_examples
from app.ai.fallback import parse_text


def main() -> None:
    ok = 0
    rows = training_examples()
    for ex in rows:
        predicted = parse_text(ex["transcript"])
        expected = map_intent(ex["intent"])
        decision = ex.get("decision") or ""
        if decision in NO_COMMIT_DECISIONS and expected not in {
            "CHECK_BALANCE",
            "DAILY_SUMMARY",
            "CORRECT_LAST",
        }:
            expected = "CLARIFY"
        intent_ok = predicted.intent == expected
        want_amt = expected_amount_paise(ex.get("entities"))
        got_amt = None
        ents = predicted.entities or {}
        if ents.get("amount_paise") is not None:
            got_amt = int(ents["amount_paise"])
        elif ents.get("amount_rupees") is not None:
            got_amt = int(float(ents["amount_rupees"]) * 100)
        amt_ok = want_amt is None or "transactions" in (ex.get("entities") or {}) or got_amt == want_amt or (
            want_amt == 0 and predicted.intent == "CLARIFY"
        )
        passed = intent_ok and amt_ok
        ok += int(passed)
        mark = "PASS" if passed else "FAIL"
        print(f"{mark} {ex['example_id']:5} {predicted.intent:16} :: {ex['transcript']}")
    print(f"\nScore: {ok}/{len(rows)}")


if __name__ == "__main__":
    main()

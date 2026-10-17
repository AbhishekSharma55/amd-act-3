"""Score saved extraction predictions against another label file; makes no model calls."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    labels = {label["id"]: label for label in map(json.loads, args.labels.read_text(encoding="utf-8").splitlines())}
    rows = []

    def matches(pred, expected):
        return pred["type"] == expected["type"] and all(pred["params"].get(k) == v for k, v in expected["params"].items())

    for row in predictions["rows"]:
        label, pred = labels[row["id"]], row["predicted"]
        found = [any(matches(p, e) for p in pred) for e in label["expected"]]
        false_ok = [p for p in pred if p["status"] == "ok" and not any(matches(p, e) for e in label["expected"])]
        review = any(p["status"] == "review" for p in pred)
        correct = row["error"] is None and all(found) and not false_ok and (review or not label["expect_review"])
        rows.append({"id": row["id"], "correct": correct, "expected_found": f"{sum(found)}/{len(found)}",
                     "false_acceptances": len(false_ok), "expect_review": label["expect_review"],
                     "review_raised": review, "error": row["error"]})
    needs = [row for row in rows if row["expect_review"]]
    summary = {"labels": str(args.labels), "complete_change_accuracy": f"{sum(r['correct'] for r in rows)}/{len(rows)}",
               "false_acceptances": sum(r["false_acceptances"] for r in rows),
               "useful_review": f"{sum(r['review_raised'] for r in needs)}/{len(needs)}",
               "errors": sum(r["error"] is not None for r in rows)}
    result = {"note": "Same saved predictions and matching rule; no new AMD requests or label changes. Labels remain provisional until reconciled.",
              "predictions_source": str(args.predictions), "labels_source": str(args.labels), "summary": summary, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

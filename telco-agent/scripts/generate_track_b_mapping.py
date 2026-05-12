"""Build Phase_2/test_official_track_b.json: UUIDs from official_sample_submission.csv x Phase_2/test.json."""
from __future__ import annotations

import csv
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    sample = _ROOT / "data" / "official_sample_submission.csv"
    phase2 = _ROOT / "data" / "Phase_2" / "test.json"
    out_path = _ROOT / "data" / "Phase_2" / "test_official_track_b.json"

    with open(phase2, encoding="utf-8") as f:
        scenarios = json.load(f)
    tb_scenarios = [x for x in scenarios if x.get("track") == "B"]
    if len(tb_scenarios) != 100:
        raise SystemExit(f"Expected 100 Track B scenarios, got {len(tb_scenarios)}")

    uuids: list[str] = []
    with open(sample, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ta = (row.get("Track A") or "").strip()
            if not ta:
                uuids.append(str(row["ID"]).strip())

    if len(uuids) != 100:
        raise SystemExit(f"Expected 100 empty-Track-A rows, got {len(uuids)}")

    merged = [
        {"id": u, "track": "B", "question": tb_scenarios[i]["question"]}
        for i, u in enumerate(uuids)
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(merged)} rows -> {out_path}")


if __name__ == "__main__":
    main()

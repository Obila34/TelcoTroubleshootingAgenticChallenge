"""
Validate result.csv against the official Zindi sample before upload.

Usage:
  python check_submission.py path/to/official_sample.csv path/to/result.csv

Reports: missing/extra IDs, empty Track A / Track B cells (common Zindi errors).
"""

from __future__ import annotations

import sys

import pandas as pd


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python check_submission.py <official_template.csv> <your_result.csv>")
        sys.exit(1)
    tmpl_path, res_path = sys.argv[1], sys.argv[2]
    tmpl = pd.read_csv(tmpl_path)
    res = pd.read_csv(res_path)

    def ids(df: pd.DataFrame) -> set[str]:
        return {str(x).strip() for x in df["ID"].tolist()}

    t_ids, r_ids = ids(tmpl), ids(res)
    missing = sorted(t_ids - r_ids)
    extra = sorted(r_ids - t_ids)

    print(f"Template rows: {len(tmpl)} | Your rows: {len(res)}")
    if missing:
        print(f"\n[ERROR] Missing {len(missing)} IDs from your file (first 20): {missing[:20]}")
    if extra:
        print(f"\n[WARN] Extra {len(extra)} IDs not in template (first 20): {extra[:20]}")

    def empties(col: str) -> list[str]:
        out: list[str] = []
        for _, row in res.iterrows():
            qid = str(row["ID"]).strip()
            v = row.get(col, "")
            if pd.isna(v) or str(v).strip() == "" or str(v).strip().lower() == "placeholder":
                out.append(qid)
        return out

    ea, eb = empties("Track A"), empties("Track B")
    print(f"\nEmpty or placeholder Track A: {len(ea)} rows")
    if ea[:25]:
        print(f"  Sample IDs: {ea[:25]}")
    print(f"Empty Track B: {len(eb)} rows")
    if eb[:25]:
        print(f"  Sample IDs: {eb[:25]}")

    if not missing and not extra and len(tmpl) == len(res):
        print("\n[OK] Row count and ID sets match template.")
    sys.exit(1 if missing or len(tmpl) != len(res) else 0)


if __name__ == "__main__":
    main()

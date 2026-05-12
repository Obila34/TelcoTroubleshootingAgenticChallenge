import csv
import json
import os
from pathlib import Path

import pandas as pd

from agent import solve_question

# Official Zindi template + questions path (override via env when submitting).
_ROOT = Path(__file__).resolve().parent
# Defaults align official Zindi sample (Downloads copy → data/official_sample_submission.csv) + UUID-keyed Track B list.
SUBMISSION_CSV = os.getenv(
    "SUBMISSION_CSV",
    str(_ROOT / "data" / "official_sample_submission.csv"),
)
TEST_JSON = os.getenv(
    "TEST_JSON",
    str(_ROOT / "data" / "Phase_2" / "test_official_track_b.json"),
)
# Optional: CSV with columns ID,Track A — fills Track A for leaderboard rows (main.py only solves Track B).
TRACK_A_CSV = os.getenv("TRACK_A_CSV", "").strip()


def load_track_b_questions(test_data: list) -> dict[int | str, str]:
    """
    Supports:
    - Hugging Face / challenge format: {"scenario_id", "task": {"id", "question"}}
    - Legacy flat rows: {"id", "track": "B", "question"}
    """
    out: dict[int | str, str] = {}
    for item in test_data:
        task = item.get("task")
        if isinstance(task, dict) and "question" in task:
            qid = task.get("id")
            if qid is not None:
                out[qid] = task["question"]
            continue
        if item.get("track") == "B":
            out[item["id"]] = item["question"]
    return out


def main() -> None:
    with open(TEST_JSON, encoding="utf-8") as f:
        test_data = json.load(f)

    sample_df = pd.read_csv(SUBMISSION_CSV)
    print(f"[INFO] Submission template: {SUBMISSION_CSV}")
    print(f"[INFO] Questions JSON: {TEST_JSON}")

    track_a_overrides: dict[str, str] = {}
    if TRACK_A_CSV and Path(TRACK_A_CSV).exists():
        ta_df = pd.read_csv(TRACK_A_CSV)
        if "ID" not in ta_df.columns or "Track A" not in ta_df.columns:
            raise ValueError(f"{TRACK_A_CSV} must have columns: ID, Track A")
        for _, r in ta_df.iterrows():
            tid = str(r["ID"]).strip()
            v = r["Track A"]
            track_a_overrides[tid] = "" if pd.isna(v) else str(v).strip()
        print(f"[INFO] Loaded Track A overrides: {len(track_a_overrides)} rows from {TRACK_A_CSV}")

    track_b_questions = load_track_b_questions(test_data)

    print(f"[INFO] Found {len(track_b_questions)} Track B questions to solve")
    q_keys = {str(k) for k in track_b_questions.keys()}
    sub_ids = {str(x) for x in sample_df["ID"].tolist()}
    orphan_q = q_keys - sub_ids
    orphan_rows = sub_ids - q_keys
    if orphan_q:
        print(f"[WARN] test.json has IDs not in submission CSV ({len(orphan_q)}); they will not appear in result.csv rows.")
    if orphan_rows:
        print(
            f"[WARN] Submission has {len(orphan_rows)} IDs with no question in test.json; "
            "Track B will stay empty unless already filled in the template."
        )

    track_b_answers: dict[int | str, str] = {}
    for idx, (q_id, question) in enumerate(track_b_questions.items()):
        print(f"\n[Q {idx + 1}/{len(track_b_questions)}] ID: {q_id}")
        print(f"Question: {question[:120]}")
        answer = solve_question(question, question_number=str(q_id))
        track_b_answers[q_id] = answer

    rows: list[dict[str, object]] = []
    for _, row in sample_df.iterrows():
        q_id = row["ID"]
        qid_str = str(q_id).strip()
        track_a = row["Track A"] if pd.notna(row["Track A"]) else ""
        if track_a_overrides and qid_str in track_a_overrides:
            tv = track_a_overrides[qid_str]
            if tv != "":
                track_a = tv
        prev_b = (
            row["Track B"]
            if "Track B" in row.index and pd.notna(row["Track B"])
            else ""
        )
        track_b = (
            track_b_answers.get(q_id)
            or track_b_answers.get(str(q_id))
            or track_b_answers.get(qid_str)
            or prev_b
        )
        rows.append({"ID": q_id, "Track A": track_a, "Track B": track_b})

    with open("result.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Track A", "Track B"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[DONE] result.csv written with {len(rows)} rows")
    print(f"       Track B answers filled: {len(track_b_answers)}")


if __name__ == "__main__":
    main()

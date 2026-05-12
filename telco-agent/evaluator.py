import json
from typing import Any

from agent import solve_question


def _unpack_train_row(item: dict[str, Any]) -> tuple[str, str, str]:
    """Return (question, ground_truth_answer, question_number_str)."""
    if isinstance(item.get("task"), dict):
        t = item["task"]
        q = str(t.get("question", ""))
        qn = str(t.get("id", "others"))
    else:
        q = str(item.get("question", ""))
        qn = str(item.get("id", "others"))
    ans = item.get("answer", "")
    if ans == "" and isinstance(item.get("task"), dict):
        ans = item["task"].get("answer", "")
    return q, str(ans), qn


def evaluate_on_train(train_path: str, max_questions: int = 20) -> float:
    """Run agent on train set and compute exact-match accuracy."""
    with open(train_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("[WARN] Train file is empty; nothing to evaluate.")
        return 0.0

    correct = 0
    total = 0

    for item in data[:max_questions]:
        question, ground_truth, qn = _unpack_train_row(item)

        predicted = solve_question(question, question_number=qn)

        match = predicted.strip() == ground_truth.strip()
        if match:
            correct += 1
        else:
            print(f"\n[MISS] Q: {question[:80]}")
            print(f"  Expected: {ground_truth}")
            print(f"  Got:      {predicted}")
        total += 1

    accuracy = correct / total * 100
    print(f"\n=== Accuracy: {correct}/{total} = {accuracy:.1f}% ===")
    return accuracy


if __name__ == "__main__":
    evaluate_on_train("data/Phase_1/train.json")

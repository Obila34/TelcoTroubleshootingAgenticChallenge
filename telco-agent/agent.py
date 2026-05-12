import json
import time
from typing import Any, Optional

from openai import OpenAI

from config import (
    ANSWER_TIMEOUT,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    MAX_TOOL_CALLS,
)
from formatter import clean_answer, classify_question
from prompts.system_prompt import SYSTEM_PROMPT
from tools import NetworkTools

_client: Optional[OpenAI] = None
tools = NetworkTools()


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _client


def extract_tool_call(text: str) -> Optional[dict[str, Any]]:
    start = text.find("<tool_call>")
    if start == -1:
        return None
    brace = text.find("{", start)
    end_tag = text.find("</tool_call>", brace)
    if brace == -1 or end_tag == -1:
        return None
    blob = text[brace:end_tag].strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def execute_tool(tool_call: dict[str, Any], default_question_number: str) -> str:
    tool_name = tool_call.get("tool")
    params: dict[str, Any] = dict(tool_call.get("params") or {})
    if not isinstance(tool_name, str):
        return "ERROR: missing tool name"

    if tool_name == "execute":
        if not params.get("device_name"):
            return "ERROR: execute requires device_name"
        if not params.get("command"):
            return "ERROR: execute requires command"
        qn = params.get("question_number")
        if qn is None or str(qn).strip() == "":
            params["question_number"] = str(default_question_number)
        try:
            return tools.execute(**params)
        except TypeError as e:
            return f"ERROR: bad params for execute: {e}"

    return (
        f"ERROR: Unknown tool {tool_name}. Use only "
        '`{"tool":"execute","params":{"device_name","command","question_number"}}`.'
    )


def solve_question(question: str, question_number: str = "others") -> str:
    q_type = classify_question(question)
    qn = str(question_number).strip() or "others"
    fmt_tail = ""
    if q_type == "fault_tuple":
        fmt_tail = (
            "\n\nFinal reply must be exactly ONE line: "
            "`fault_type;device_or_port;reason` (plain text, semicolons, no markdown)."
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"<question>\n{question}\n</question>\n\n"
                f"<api_context>\nquestion_number for execute() calls must be: {qn!r}\n"
                f"Tool budget: at most {MAX_TOOL_CALLS} execute calls.\n</api_context>\n\n"
                "Diagnose this and give me ONLY the answer in the format the question specifies."
                f"{fmt_tail}"
            ),
        },
    ]

    start_time = time.time()
    tool_calls_made = 0
    max_rounds = MAX_TOOL_CALLS + 12

    for _ in range(max_rounds):
        if time.time() - start_time > ANSWER_TIMEOUT:
            print(f"[TIMEOUT] Question exceeded {ANSWER_TIMEOUT}s")
            break

        client = get_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.1,
        )
        reply = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": reply})

        tool_call = extract_tool_call(reply)
        if tool_call and tool_calls_made < MAX_TOOL_CALLS:
            tool_calls_made += 1
            print(f"[TOOL {tool_calls_made}] {tool_call.get('tool')} | {tool_call.get('params', {})}")
            tool_result = execute_tool(tool_call, qn)
            preview = tool_result[:200].replace("\n", " ")
            print(f"[RESULT] {preview}")
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<tool_result>\n{tool_result}\n</tool_result>\n\n"
                        "Continue your diagnosis."
                    ),
                }
            )
            continue

        if tool_call:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have reached the tool call budget. "
                        "Do not call tools. Output ONLY the final answer string in the required format, "
                        "with no tags and no explanation."
                    ),
                }
            )
            continue

        answer = clean_answer(reply, q_type)
        print(f"[ANSWER] {answer}")
        return answer

    last = messages[-1]["content"] if messages else ""
    return clean_answer(last, q_type)

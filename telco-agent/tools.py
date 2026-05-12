from __future__ import annotations

import json
import threading
from typing import Any

import requests

from config import AGENT_EXECUTE_URL, AUTH_TOKEN, VERIFY_SSL

if not VERIFY_SSL:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _extract_cli_output(data: Any) -> str:
    """Normalize competition JSON into a single string for the model."""
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return str(data)
    for key in ("output", "result", "cli_output", "echo", "message", "content"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, dict):
            inner = _extract_cli_output(val)
            if inner:
                return inner
    # Some gateways nest under data
    nested = data.get("data")
    if nested is not None:
        return _extract_cli_output(nested)
    return json.dumps(data, ensure_ascii=False)


class NetworkTools:
    """
    Track B sandbox: one POST per call to AGENT_EXECUTE_URL with
    {device_name, command, question_number}. README: only 1 concurrent request per token.
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json",
            }
        )
        self._lock = threading.Lock()

    def execute(self, device_name: str, command: str, question_number: str) -> str:
        payload = {
            "device_name": device_name,
            "command": command,
            "question_number": str(question_number),
        }
        print(f"[TOOL] execute | {payload}")
        try:
            with self._lock:
                resp = self.session.post(
                    AGENT_EXECUTE_URL,
                    json=payload,
                    timeout=60,
                    verify=VERIFY_SSL,
                )
            resp.raise_for_status()
            body = resp.json()
            return _extract_cli_output(body)
        except Exception as e:
            return f"ERROR: {e}"

import json
import os
from datetime import datetime, timezone


class AgentLogger:

    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "agent_calls.jsonl")

    def log(self, query: str, intent: dict, agent_timings: dict,
            total_latency: float, success: bool, error: str = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "agents_called": intent.get("agents", []),
            "routing_reasoning": intent.get("reasoning", ""),
            "agent_timings_sec": {k: round(v, 2) for k, v in agent_timings.items()},
            "total_latency_sec": round(total_latency, 2),
            "success": success,
            "error": error,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_recent(self, n: int = 20) -> list:
        if not os.path.exists(self.log_file):
            return []
        with open(self.log_file, encoding="utf-8") as f:
            lines = f.readlines()
        entries = []
        for line in reversed(lines[-n:]):
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass
        return entries

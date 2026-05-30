from typing import TypedDict, Optional


class RetailState(TypedDict):
    query:         str           # the user's original natural language question
    intent:        dict          # routing decision from the intent classifier
    agent_results: dict          # keyed by agent name, value is validated output
    agent_timings: dict          # keyed by agent name, value is wall-clock seconds
    synthesis:     Optional[str] # final synthesised recommendation from Claude

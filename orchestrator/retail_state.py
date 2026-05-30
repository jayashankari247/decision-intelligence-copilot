from typing import TypedDict, Optional, Annotated


class RetailState(TypedDict):
    query:         str                                        # the user's original natural language question
    intent:        dict                                       # routing decision from the intent classifier
    agent_results: Annotated[dict, lambda x, y: {**x, **y}] # merged as each parallel agent completes
    agent_timings: Annotated[dict, lambda x, y: {**x, **y}] # merged as each parallel agent completes
    synthesis:     Optional[str]                             # final synthesised recommendation from Claude

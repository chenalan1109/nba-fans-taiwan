from dataclasses import dataclass


@dataclass(frozen=True)
class Vote:
    id: int
    poll_id: int
    voter_id: str
    option: str

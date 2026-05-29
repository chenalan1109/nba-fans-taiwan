from dataclasses import dataclass


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    abbreviation: str
    conference: str | None = None

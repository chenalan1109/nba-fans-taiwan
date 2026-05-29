from dataclasses import dataclass


@dataclass(frozen=True)
class Matchup:
    id: int
    title: str
    team_a_name: str
    team_b_name: str

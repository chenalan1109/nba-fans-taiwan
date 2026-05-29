from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    team: str
    position: str
    points: float
    rebounds: float
    assists: float
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    image_url: str | None = None

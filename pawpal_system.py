from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"

    def is_high_priority(self) -> bool:
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    owner: Optional[Owner] = field(default=None, repr=False)

    def get_needs(self) -> list[Task]:
        pass


class Owner:
    def __init__(self, name: str, email: str = "") -> None:
        self.name = name
        self.email = email
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        pass


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task]) -> None:
        self.owner = owner
        self.pet = pet
        self.tasks = tasks

    def generate_schedule(self) -> list[Task]:
        pass

    def explain_plan(self) -> str:
        pass

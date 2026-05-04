"""Služba pro správu exemplářů s filtrováním přes návrhový vzor Strategy.

Návrhový vzor **Strategy** zde umožňuje volajícímu předat různé algoritmy
filtrování, například podle kategorie nebo dostupnosti, aniž by služba musela
znát jejich konkrétní implementaci. Přidání nového filtru tak vyžaduje pouze
novou podtřídu :class:`FilterStrategy`, bez změn ve třídě
:class:`ItemService` (princip Open/Closed).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.entities import Category, Item
from db.repositories import CategoryRepository, ItemRepository


# ── Rozhraní Strategy a konkrétní strategie ──────────────────────────────────


class FilterStrategy(ABC):
    """Abstraktní strategie pro filtrování seznamu exemplářů."""

    @abstractmethod
    def apply(self, items: list[Item]) -> list[Item]:
        """Vrátí vyfiltrovanou podmnožinu zadaných *items*."""
        ...

    @property
    @abstractmethod
    def label(self) -> str:
        """Text filtru zobrazovaný v uživatelském rozhraní."""
        ...


class NoFilter(FilterStrategy):
    """Propustí všechny exempláře beze změny."""

    def apply(self, items: list[Item]) -> list[Item]:
        return items

    @property
    def label(self) -> str:
        return "Vše"


class AvailableOnlyFilter(FilterStrategy):
    """Ponechá pouze exempláře se stavem *Skladem*."""

    def apply(self, items: list[Item]) -> list[Item]:
        return [i for i in items if i.status == "Skladem"]

    @property
    def label(self) -> str:
        return "Pouze dostupné (Skladem)"


class CategoryFilter(FilterStrategy):
    """Ponechá pouze exempláře spadající do vybrané kategorie."""

    def __init__(self, category: Category) -> None:
        self._cat = category

    def apply(self, items: list[Item]) -> list[Item]:
        return [i for i in items if i.category_id == self._cat.id]

    @property
    def label(self) -> str:
        return f"Kategorie: {self._cat.name}"


# ── Služba ────────────────────────────────────────────────────────────────────


class ItemService:
    """Aplikační logika pro prohlížení a úpravu exemplářů techniky."""

    def __init__(self, item_repo: ItemRepository, cat_repo: CategoryRepository) -> None:
        self._items = item_repo
        self._cats = cat_repo

    def get_items(
        self,
        strategy: FilterStrategy | None = None,
        include_retired: bool = False,
    ) -> list[Item]:
        """Vrátí exempláře, případně přefiltrované přes :class:`FilterStrategy`."""
        items = self._items.find_all(include_retired=include_retired)
        if strategy:
            items = strategy.apply(items)
        return items

    def get_item(self, item_id: int) -> Item | None:
        return self._items.find_by_id(item_id)

    def get_categories(self) -> list[Category]:
        return self._cats.find_all()

    def update_status_and_condition(self, item_id: int, status: str, condition: str) -> None:
        """UC16 – uloží nový stav a kondici exempláře."""
        self._items.update_status_and_condition(item_id, status, condition)

"""Item management service with Strategy-pattern filtering.

The **Strategy** design pattern is used here to allow the caller to inject
different filtering algorithms (by category, availability, …) without the
service needing to know the concrete filtering logic.  Adding a new filter
requires only a new :class:`FilterStrategy` subclass – no changes to
:class:`ItemService` are needed (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.entities import Category, Item
from db.repositories import CategoryRepository, ItemRepository


# ── Strategy interface and concrete strategies ────────────────────────────────


class FilterStrategy(ABC):
    """Abstract strategy for filtering a list of items (Strategy pattern)."""

    @abstractmethod
    def apply(self, items: list[Item]) -> list[Item]:
        """Return the filtered subset of *items*."""
        ...

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable description shown next to the filter indicator in the UI."""
        ...


class NoFilter(FilterStrategy):
    """Passes all items through unchanged."""

    def apply(self, items: list[Item]) -> list[Item]:
        return items

    @property
    def label(self) -> str:
        return "Vše"


class AvailableOnlyFilter(FilterStrategy):
    """Keeps only items whose status is *Skladem*."""

    def apply(self, items: list[Item]) -> list[Item]:
        return [i for i in items if i.status == "Skladem"]

    @property
    def label(self) -> str:
        return "Pouze dostupné (Skladem)"


class CategoryFilter(FilterStrategy):
    """Keeps only items belonging to a specific category."""

    def __init__(self, category: Category) -> None:
        self._cat = category

    def apply(self, items: list[Item]) -> list[Item]:
        return [i for i in items if i.category_id == self._cat.id]

    @property
    def label(self) -> str:
        return f"Kategorie: {self._cat.name}"


# ── Service ───────────────────────────────────────────────────────────────────


class ItemService:
    """Business logic for browsing and updating equipment items."""

    def __init__(self, item_repo: ItemRepository, cat_repo: CategoryRepository) -> None:
        self._items = item_repo
        self._cats = cat_repo

    def get_items(
        self,
        strategy: FilterStrategy | None = None,
        include_retired: bool = False,
    ) -> list[Item]:
        """Return items, optionally passed through a :class:`FilterStrategy`."""
        items = self._items.find_all(include_retired=include_retired)
        if strategy:
            items = strategy.apply(items)
        return items

    def get_item(self, item_id: int) -> Item | None:
        return self._items.find_by_id(item_id)

    def get_categories(self) -> list[Category]:
        return self._cats.find_all()

    def update_status_and_condition(self, item_id: int, status: str, condition: str) -> None:
        """UC16 – persist a new status and condition for an item."""
        self._items.update_status_and_condition(item_id, status, condition)

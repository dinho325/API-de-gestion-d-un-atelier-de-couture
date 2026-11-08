"""Briques communes : base Pydantic, page de résultats, pagination."""
from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class SchemaEntree(BaseModel):
    """Base des schémas reçus : supprime les espaces autour des textes."""
    model_config = ConfigDict(str_strip_whitespace=True)


class SchemaLecture(BaseModel):
    """Base des schémas renvoyés : lit directement les objets SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page (max 100)"),
    offset: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)

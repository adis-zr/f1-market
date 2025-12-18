"""Sports data provider interface."""
from .base import DataProvider
from .f1 import F1DataProvider

__all__ = ['DataProvider', 'F1DataProvider']

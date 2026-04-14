"""Shared custom exceptions."""


class StockServiceError(Exception):
    """Base stock service exception."""


class InvalidStockSymbolError(StockServiceError):
    """Raised when stock symbol data is unavailable or invalid."""


class DataFetchError(StockServiceError):
    """Raised when external market data fetch fails."""


class ModelTrainingError(StockServiceError):
    """Raised when model training or inference fails."""


class InputValidationError(StockServiceError):
    """Raised when request input fails custom validation checks."""

"""Domain-specific exceptions."""


class SettlementError(Exception):
    """Base exception for domain errors."""
    pass


class SettlementNotFoundError(SettlementError):
    """Settlement/creditor doesn't exist."""
    pass


class InvalidPaymentError(SettlementError):
    """Payment data is invalid."""
    pass


class InvalidSettlementError(SettlementError):
    """Settlement data is invalid."""
    pass

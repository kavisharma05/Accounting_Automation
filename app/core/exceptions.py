class DomainError(Exception):
    """Base domain exception."""


class ValidationError(DomainError):
    pass


class PostingError(DomainError):
    pass


class IdempotencyConflict(DomainError):
    pass


class TenantIsolationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass

class DomainError(Exception):
    """Base exception for unexpected system/domain errors."""
    pass


class DatabaseIntegrityError(DomainError):
    """Raised when an unrecoverable database constraint or corruption occurs."""
    pass


class AuthenticationError(DomainError):
    """Raised when PIN unlock fails repeatedly or is locked out."""
    pass

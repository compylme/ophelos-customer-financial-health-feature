class DomainError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

class UserNotFound(DomainError):
    pass

class SnapshotAlreadyExists(DomainError):
    pass


class SnapshotNotFound(DomainError):
    pass


class InvalidFinancialItems(DomainError):
    pass


class InvalidHistoryLimit(DomainError):
    pass

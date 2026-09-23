"""Custom application exceptions."""
from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str | None = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "not_found")


class ConflictError(AppException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status.HTTP_409_CONFLICT, detail, "conflict")


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "forbidden")


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "unauthorized")


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail, "validation_error")


class InsufficientBalanceError(AppException):
    def __init__(self, detail: str = "Недостаточно средств"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, "insufficient_balance")


class OutOfStockError(AppException):
    def __init__(self, detail: str = "Этот товар закончился"):
        super().__init__(status.HTTP_409_CONFLICT, detail, "out_of_stock")


class IdempotencyError(AppException):
    def __init__(self, detail: str = "Заявка уже обработана"):
        super().__init__(status.HTTP_409_CONFLICT, detail, "idempotency_conflict")

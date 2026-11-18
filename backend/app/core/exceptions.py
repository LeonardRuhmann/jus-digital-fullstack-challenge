from fastapi import status


class AppException(Exception):
    """Base exception for predictable domain and application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Não autenticado. Faça login novamente.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    def __init__(
        self, message: str = "Você não tem permissão para acessar este recurso."
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Recurso não encontrado.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class ValidationException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
        )


class ExternalServiceException(AppException):
    def __init__(
        self,
        message: str,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
        )

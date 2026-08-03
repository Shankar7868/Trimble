class BaseBusinessException(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundException(BaseBusinessException):
    def __init__(self, message: str):
        super().__init__(message, "RESOURCE_NOT_FOUND", status_code=404)

class InsufficientStockException(BaseBusinessException):
    def __init__(self, message: str):
        super().__init__(message, "INSUFFICIENT_STOCK", status_code=400)

class InvalidStateException(BaseBusinessException):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_STATE", status_code=400)

class UnauthorizedAccessException(BaseBusinessException):
    def __init__(self, message: str):
        super().__init__(message, "UNAUTHORIZED_ACCESS", status_code=403)

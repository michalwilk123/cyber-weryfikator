class BaseCheckError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DomainError(BaseCheckError):
    pass


class CertificateError(BaseCheckError):
    pass


class HTTPError(BaseCheckError):
    pass


class KeyExchangeError(BaseCheckError):
    pass



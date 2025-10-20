"""python-domintell-ecopilot errors."""


class DomintellEcopilotException(Exception):
    """Base error for python-domintell-ecopilot."""


class RequestError(DomintellEcopilotException):
    """Unable to fulfill request.

    Raised when host or API cannot be reached.
    """


class InvalidUserNameError(DomintellEcopilotException):
    """Invalid username.

    Raised when username is not valid, too short or too long.
    """


class ResponseError(DomintellEcopilotException):
    """API responded unexpected."""


class NotFoundError(DomintellEcopilotException):
    """Request not found.

    Raised when API responds with '404'
    """


class InvalidStateError(DomintellEcopilotException):
    """Raised when the device is not in the correct state."""


class UnsupportedError(DomintellEcopilotException):
    """Raised when the device is not supported from this library."""


class UnauthorizedError(DomintellEcopilotException):
    """Raised when request is not authorized."""


class FirmwareUpdateError(Exception):
    """Base error for firmware update operations."""


class MetadataError(FirmwareUpdateError):
    """Error retrieving or parsing metadata."""


class DownloadError(FirmwareUpdateError):
    """Error while downloading the binary."""


class IntegrityError(FirmwareUpdateError):
    """SHA256 verification error.."""


class TransferError(FirmwareUpdateError):
    """Error sending binary over TCP/IP."""

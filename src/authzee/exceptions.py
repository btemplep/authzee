"""Module for Authzee Exceptions
"""


class AuthzeeError(Exception):
    """Base Authzee Exception.
    """
    pass


class AsyncNotAvailableError(AuthzeeError):
    """Async is not available in a class or method
    """
    pass


class GrantDoesNotExistError(AuthzeeError):
    """The Grant Does not exist.
    """
    pass


class GrantUUIDError(AuthzeeError):
    """There was an error associated with a grant UUID
    """
    pass


class IdentityRegistrationError(AuthzeeError):
    """There was an error when registering the Identity Type.
    """
    pass


class InitializationError(AuthzeeError):
    """There was an error during initialization of the Authzee App.
    """
    pass


class InputVerificationError(AuthzeeError):
    """The given inputs could not be verified.
    """
    pass


class MethodNotImplementedError(AuthzeeError):
    """The given method is not implemented for this class.
    """

    def __init__(self, msg: str = "This method is not implemented.", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class ResourceAuthzRegistrationError(AuthzeeError):
    """There was an error when registering the ResourceAuthz.
    """
    pass



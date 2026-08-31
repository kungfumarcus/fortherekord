"""Domain and adapter errors for rekordboxkit."""


class RekordboxKitError(Exception):
    """Base error for rekordboxkit."""


class RekordboxRunningError(RekordboxKitError):
    """Raised when a write is attempted while Rekordbox is running."""


class EntityNotFoundError(RekordboxKitError):
    """Raised when an entity ID does not exist."""


class WrongEntityTypeError(RekordboxKitError):
    """Raised when an ID exists but is a different playlist type."""


class ValidationError(RekordboxKitError):
    """Raised when a query, patch, or create payload is invalid."""


class UnconfirmedFieldError(RekordboxKitError):
    """Raised when writing a track field whose encoding is not confirmed."""


class FolderNotEmptyError(RekordboxKitError):
    """Raised when deleting a folder that still has children."""

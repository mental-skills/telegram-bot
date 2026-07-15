class MentalSkillsError(Exception):
    """Base application error."""


class ContentValidationError(MentalSkillsError):
    """Raised when scenario content cannot be accepted at startup."""


class AssetValidationError(MentalSkillsError):
    """Raised when visual assets do not match the manifest rules."""


class ScenarioStateError(MentalSkillsError):
    """Raised when a session points to an invalid scenario state."""

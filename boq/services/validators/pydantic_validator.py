import logging

from pydantic import ValidationError

from boq.services.validators.schemas import (
    BoQSchema,
)

logger = logging.getLogger(__name__)


class PydanticValidator:
    """
    Validates AI-generated BoQ data against the
    expected schema.
    """

    @staticmethod
    def validate(data: dict) -> BoQSchema:
        """
        Validate AI output.

        Returns:
            BoQSchema

        Raises:
            ValidationError
        """

        try:
            validated = BoQSchema.model_validate(
                data
            )

            logger.info(
                "Pydantic validation successful."
            )

            return validated

        except ValidationError as exc:

            logger.exception(
                "Pydantic validation failed."
            )

            raise exc
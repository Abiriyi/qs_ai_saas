from pydantic import BaseModel, Field, ConfigDict
from typing import List


class BoQItemSchema(BaseModel):
    """
    Represents a single BoQ item returned by the AI.
    """

    model_config = ConfigDict(extra="forbid")

    item_no: str = Field(
        min_length=1,
        max_length=50,
    )

    description: str = Field(
        min_length=1,
    )

    unit: str = Field(
        min_length=1,
        max_length=20,
    )

    quantity: float = Field(
        ge=0,
    )

    rate: float = Field(
        ge=0,
    )

    confidence: float = Field(
        ge=0,
        le=1,
    )


class BoQSectionSchema(BaseModel):
    """
    Represents one BoQ section.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
    )

    items: List[BoQItemSchema]


class BoQSchema(BaseModel):
    """
    Root schema returned by the AI.
    """

    model_config = ConfigDict(extra="forbid")

    sections: List[BoQSectionSchema]
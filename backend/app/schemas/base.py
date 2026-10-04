from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema configuration for all Pydantic schemas.
    Enables ORM attribute loading and serialization.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )

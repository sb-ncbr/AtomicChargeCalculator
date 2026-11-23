from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from pydantic.json_schema import SkipJsonSchema

from models.calculation import CalculationConfigDto
from models.setup import AdvancedSettingsDto


class BaseRequestModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class SuitableMethodsRequest(BaseRequestModel):
    file_hashes: list[str]
    permissive_types: bool = True


class StatsRequest(BaseRequestModel):
    file_hash: str


class BestParametersRequest(BaseRequestModel):
    method_name: str
    file_hash: str
    permissive_types: bool = True


class CalculateChargesRequest(BaseRequestModel):
    configs: list[CalculationConfigDto]
    file_hashes: list[str]
    settings: AdvancedSettingsDto | None = None

    @field_validator("configs")
    @classmethod
    def configs_name_a_method(cls, configs: list[CalculationConfigDto]) -> list[CalculationConfigDto]:
        # An empty list asks ACC to choose; a configuration must name its method.
        if any(not config.method for config in configs):
            raise ValueError("Every configuration must name a method.")
        return configs

    # exclude computation_id from docs
    computation_id: SkipJsonSchema[str | None] = Field(None, exclude=True)


class SetupRequest(BaseRequestModel):
    file_hashes: list[str]
    settings: AdvancedSettingsDto | None

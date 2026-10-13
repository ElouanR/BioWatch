from pydantic import BaseModel, ConfigDict, Field


class TrialInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interventions: list[str] = Field(
        default_factory=list,
        description="Drug or therapy names exactly as written in the text",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Diseases or conditions studied",
    )
    population: str | None = Field(
        None,
        description="Who is enrolled, in a short phrase, only if stated",
    )
    comparator: str | None = Field(
        None,
        description="Placebo, standard of care or other comparator, "
        "only if stated",
    )

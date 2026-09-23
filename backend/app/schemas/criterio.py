from pydantic import BaseModel, ConfigDict, Field


class CriterioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    peso: float = Field(gt=0, le=1_000_000, description="Peso relativo del criterio. No hace falta que sumen 1.0 entre todos.")
    descripcion: str = Field(default="", max_length=2000)
    activo: bool = True
    # La columna es INTEGER: sin tope, un valor como 10**12 hacía caer
    # Postgres con "integer out of range" (500). 10 000 sobra para ordenar.
    orden: int = Field(default=0, ge=0, le=10_000)


class CriterioCreate(CriterioBase):
    pass


class CriterioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    peso: float | None = Field(default=None, gt=0, le=1_000_000)
    descripcion: str | None = Field(default=None, max_length=2000)
    activo: bool | None = None
    orden: int | None = Field(default=None, ge=0, le=10_000)


class CriterioOut(CriterioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

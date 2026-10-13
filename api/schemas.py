from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class MovimientoCreate(BaseModel):
    tipo: str                      # GASTO | INGRESO
    concepto: str = Field(min_length=1, max_length=255)
    categoria: str = Field(default="Otros", max_length=100)
    monto: float = Field(gt=0)
    origen_ingreso: Optional[str] = None


class RecordatorioCreate(BaseModel):
    descripcion: str = Field(min_length=1, max_length=255)
    tipo: str = "PAGO"             # PAGO | ACTIVIDAD
    monto: Optional[float] = Field(default=None, ge=0)
    fecha_vencimiento: Optional[date] = None
    frecuencia: str = "UNICO"      # UNICO|SEMANAL|QUINCENAL|MENSUAL|ANUAL
    dias_anticipacion: int = Field(default=3, ge=0, le=60)


class RecordatorioUpdate(BaseModel):
    descripcion: str = Field(min_length=1, max_length=255)
    tipo: str = "PAGO"
    monto: Optional[float] = Field(default=None, ge=0)
    fecha_vencimiento: Optional[date] = None
    frecuencia: str = "UNICO"
    dias_anticipacion: int = Field(default=3, ge=0, le=60)


class RegistroRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    # Un solo campo: puede ser código de regalo (QUEDA-XXXX-XXXX) o el
    # código de invitación familiar de otra cuenta.
    codigo: Optional[str] = Field(default=None, max_length=40)


class CanjearRequest(BaseModel):
    codigo: str = Field(min_length=3, max_length=40)


class CodigoRegaloCreate(BaseModel):
    dias: int = Field(default=30, ge=1, le=365)
    plan_slug: str = "individual"
    usos_max: int = Field(default=1, ge=1, le=100)
    vence_en_dias: Optional[int] = Field(default=None, ge=1, le=365)
    nota: Optional[str] = Field(default=None, max_length=200)


class RegalarRequest(BaseModel):
    email: str
    dias: int = Field(default=30, ge=1, le=365)
    plan_slug: str = "individual"

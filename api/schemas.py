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

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.reservation import ReservationStatus

class ReservationCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID of the product to reserve")
    quantity: int = Field(..., gt=0, description="Quantity of products to reserve")

class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    user_id: str
    quantity: int
    status: ReservationStatus
    created_at: datetime
    expires_at: datetime

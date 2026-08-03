from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class PurchaseCreate(BaseModel):
    product_id: Optional[int] = Field(None, gt=0, description="Product ID for direct purchases")
    reservation_id: Optional[int] = Field(None, gt=0, description="Reservation ID to finalize hold")
    quantity: Optional[int] = Field(None, gt=0, description="Quantity for direct purchases")

class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    reservation_id: Optional[int]
    user_id: str
    quantity: int
    total_price: float
    created_at: datetime

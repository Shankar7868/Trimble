from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, description="Unique Product SKU code")
    name: str = Field(..., min_length=1, description="Name of the product")
    description: Optional[str] = None
    price: float = Field(..., ge=0.0, description="Product unit price")
    total_quantity: int = Field(..., ge=0, description="Total units in stock")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0.0)
    total_quantity: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    available_quantity: int

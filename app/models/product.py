from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    total_quantity = Column(Integer, default=0, nullable=False)

    reservations = relationship("Reservation", back_populates="product", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="product", cascade="all, delete-orphan")

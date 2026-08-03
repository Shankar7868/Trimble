from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.repositories.product import product_repo
from app.repositories.reservation import reservation_repo
from app.exceptions import InvalidStateException

class ProductService:
    def create_product(self, db: Session, product_in: ProductCreate) -> Product:
        existing = product_repo.get_by_sku(db, sku=product_in.sku)
        if existing:
            raise InvalidStateException(f"Product with SKU '{product_in.sku}' already exists.")
        return product_repo.create(db, obj_in=product_in)

    def get_product_with_available(self, db: Session, product_id: int) -> Optional[Product]:
        product = product_repo.get(db, product_id)
        if not product:
            return None
        
        # Calculate available quantity
        reserved = reservation_repo.get_active_reserved_quantity(db, product.id)
        product.available_quantity = max(0, product.total_quantity - reserved)
        return product

    def get_products_with_available(self, db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
        products = product_repo.get_all(db, skip=skip, limit=limit)
        for prod in products:
            reserved = reservation_repo.get_active_reserved_quantity(db, prod.id)
            prod.available_quantity = max(0, prod.total_quantity - reserved)
        return products

    def update_product(self, db: Session, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
        product = product_repo.get(db, product_id)
        if not product:
            return None
        
        if product_in.sku:
            existing = product_repo.get_by_sku(db, sku=product_in.sku)
            if existing and existing.id != product_id:
                raise InvalidStateException(f"Product with SKU '{product_in.sku}' already exists.")

        updated_product = product_repo.update(db, db_obj=product, obj_in=product_in)
        # Calculate available quantity
        reserved = reservation_repo.get_active_reserved_quantity(db, updated_product.id)
        updated_product.available_quantity = max(0, updated_product.total_quantity - reserved)
        return updated_product

    def delete_product(self, db: Session, product_id: int) -> Optional[Product]:
        return product_repo.delete(db, id=product_id)

product_service = ProductService()

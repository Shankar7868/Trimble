from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.purchase import Purchase
from app.models.reservation import ReservationStatus
from app.schemas.purchase import PurchaseCreate
from app.repositories.purchase import purchase_repo
from app.repositories.product import product_repo
from app.repositories.reservation import reservation_repo
from app.services.reservation import reservation_service
from app.exceptions import (
    ResourceNotFoundException,
    InsufficientStockException,
    InvalidStateException,
    UnauthorizedAccessException
)

class PurchaseService:
    def create_purchase_from_reservation(self, db: Session, reservation_id: int, user_id: str, user_role: str) -> Purchase:
        # Fetch reservation and check ownership
        res = reservation_repo.get(db, reservation_id)
        if not res:
            raise ResourceNotFoundException(f"Reservation with ID {reservation_id} not found.")

        if user_role != "admin" and res.user_id != user_id:
            raise UnauthorizedAccessException("Access denied. You do not own this reservation.")

        # Lock the product row first
        product = product_repo.get_for_update(db, res.product_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {res.product_id} not found.")

        # Validate reservation state
        if res.status == ReservationStatus.CONFIRMED:
            raise InvalidStateException("Reservation has already been confirmed.")

        if res.status != ReservationStatus.RESERVED:
            raise InvalidStateException(f"Cannot confirm reservation in '{res.status.value}' status.")

        # On-the-fly expiration check under product lock
        if res.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            res.status = ReservationStatus.EXPIRED
            db.add(res)
            db.commit()
            raise InvalidStateException("Reservation has expired.")

        # Ensure we have enough total stock to complete the purchase
        if product.total_quantity < res.quantity:
            raise InsufficientStockException("Insufficient total quantity in stock to finalize purchase.")

        # Confirm reservation status in session (not committed yet)
        res.status = ReservationStatus.CONFIRMED
        db.add(res)

        # Decrement product stock permanently
        product.total_quantity -= res.quantity
        db.add(product)

        # Create purchase record
        total_price = res.quantity * product.price
        purchase = Purchase(
            product_id=res.product_id,
            reservation_id=res.id,
            user_id=res.user_id,
            quantity=res.quantity,
            total_price=total_price
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        return purchase

    def create_direct_purchase(self, db: Session, product_id: int, quantity: int, user_id: str) -> Purchase:
        product = product_repo.get_for_update(db, product_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {product_id} not found.")

        # Calculate active reservations to get true available quantity
        reserved = reservation_repo.get_active_reserved_quantity(db, product.id)
        available_stock = product.total_quantity - reserved
        if available_stock < quantity:
            raise InsufficientStockException(f"Insufficient available stock. Requested: {quantity}, Available: {available_stock}")

        # Decrement product stock permanently
        product.total_quantity -= quantity
        db.add(product)

        # Create purchase record
        total_price = quantity * product.price
        purchase = Purchase(
            product_id=product.id,
            reservation_id=None,
            user_id=user_id,
            quantity=quantity,
            total_price=total_price
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        return purchase

    def get_purchase(self, db: Session, purchase_id: int) -> Optional[Purchase]:
        return purchase_repo.get(db, purchase_id)

    def list_purchases(self, db: Session, user_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Purchase]:
        if user_id:
            return purchase_repo.get_by_user(db, user_id, skip=skip, limit=limit)
        return purchase_repo.get_all(db, skip=skip, limit=limit)

purchase_service = PurchaseService()

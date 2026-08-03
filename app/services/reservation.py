from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import ReservationCreate
from app.repositories.reservation import reservation_repo
from app.repositories.product import product_repo
from app.exceptions import (
    ResourceNotFoundException,
    InsufficientStockException,
    InvalidStateException,
    UnauthorizedAccessException
)

class ReservationService:
    def create_reservation(self, db: Session, reservation_in: ReservationCreate, user_id: str) -> Reservation:
        # Fetch the product under lock
        product = product_repo.get_for_update(db, reservation_in.product_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {reservation_in.product_id} not found.")

        # Calculate active reservations
        reserved = reservation_repo.get_active_reserved_quantity(db, product.id)
        available = product.total_quantity - reserved

        if available < reservation_in.quantity:
            raise InsufficientStockException(
                f"Insufficient stock for product ID {product.id}. "
                f"Requested: {reservation_in.quantity}, Available: {available}."
            )

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.RESERVATION_EXPIRY_MINUTES)

        db_obj = Reservation(
            product_id=reservation_in.product_id,
            user_id=user_id,
            quantity=reservation_in.quantity,
            status=ReservationStatus.RESERVED,
            expires_at=expires_at
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def confirm_reservation(self, db: Session, reservation_id: int) -> Reservation:
        res = reservation_repo.get(db, reservation_id)
        if not res:
            raise ResourceNotFoundException(f"Reservation with ID {reservation_id} not found.")

        if res.status == ReservationStatus.CONFIRMED:
            raise InvalidStateException("Reservation has already been confirmed.")

        if res.status != ReservationStatus.RESERVED:
            raise InvalidStateException(f"Cannot confirm reservation in '{res.status.value}' status.")

        # Check for expiry
        if res.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            res.status = ReservationStatus.EXPIRED
            db.add(res)
            db.commit()
            db.refresh(res)
            raise InvalidStateException("Reservation has expired.")

        res.status = ReservationStatus.CONFIRMED
        db.add(res)
        db.commit()
        db.refresh(res)
        return res

    def cancel_reservation(self, db: Session, reservation_id: int, user_id: str, user_role: str) -> Reservation:
        res = reservation_repo.get(db, reservation_id)
        if not res:
            raise ResourceNotFoundException(f"Reservation with ID {reservation_id} not found.")

        if user_role != "admin" and res.user_id != user_id:
            raise UnauthorizedAccessException("Access denied. You do not own this reservation.")

        # Check for on-the-fly expiration
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if res.status == ReservationStatus.RESERVED and res.expires_at <= now:
            res.status = ReservationStatus.EXPIRED
            db.add(res)
            db.commit()
            db.refresh(res)
            raise InvalidStateException("Cannot cancel an expired reservation.")

        if res.status == ReservationStatus.CANCELLED:
            raise InvalidStateException("Reservation has already been cancelled.")

        if res.status == ReservationStatus.CONFIRMED:
            raise InvalidStateException("Cannot cancel a purchased reservation.")

        if res.status == ReservationStatus.EXPIRED:
            raise InvalidStateException("Cannot cancel an expired reservation.")

        res.status = ReservationStatus.CANCELLED
        db.add(res)
        db.commit()
        db.refresh(res)
        return res

    def get_reservation(self, db: Session, reservation_id: int) -> Optional[Reservation]:
        # Before returning, check if it's expired and update status on the fly
        res = reservation_repo.get(db, reservation_id)
        if res and res.status == ReservationStatus.RESERVED and res.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            res.status = ReservationStatus.EXPIRED
            db.add(res)
            db.commit()
            db.refresh(res)
        return res

    def list_reservations(self, db: Session, user_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Reservation]:
        # Run cleanup first
        self.cleanup_expired_reservations(db)
        if user_id:
            return reservation_repo.get_by_user(db, user_id, skip=skip, limit=limit)
        return reservation_repo.get_all(db, skip=skip, limit=limit)

    def cleanup_expired_reservations(self, db: Session) -> int:
        expired = reservation_repo.get_expired_reserved_reservations(db)
        count = 0
        for res in expired:
            res.status = ReservationStatus.EXPIRED
            db.add(res)
            count += 1
        if count > 0:
            db.commit()
        return count

reservation_service = ReservationService()

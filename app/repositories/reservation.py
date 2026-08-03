from typing import List
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.reservation import Reservation, ReservationStatus
from app.repositories.base import BaseRepository

class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self):
        super().__init__(Reservation)

    def get_active_reservations_by_product(self, db: Session, product_id: int) -> List[Reservation]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return db.query(self.model).filter(
            self.model.product_id == product_id,
            self.model.status == ReservationStatus.RESERVED,
            self.model.expires_at > now
        ).all()

    def get_active_reserved_quantity(self, db: Session, product_id: int) -> int:
        reservations = self.get_active_reservations_by_product(db, product_id)
        return sum(res.quantity for res in reservations)

    def get_expired_reserved_reservations(self, db: Session) -> List[Reservation]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return db.query(self.model).filter(
            self.model.status == ReservationStatus.RESERVED,
            self.model.expires_at <= now
        ).all()

    def get_by_user(self, db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Reservation]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

reservation_repo = ReservationRepository()

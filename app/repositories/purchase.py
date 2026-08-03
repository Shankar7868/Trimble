from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.purchase import Purchase
from app.repositories.base import BaseRepository

class PurchaseRepository(BaseRepository[Purchase]):
    def __init__(self):
        super().__init__(Purchase)

    def get_by_reservation(self, db: Session, reservation_id: int) -> Optional[Purchase]:
        return db.query(self.model).filter(self.model.reservation_id == reservation_id).first()

    def get_by_user(self, db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Purchase]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

purchase_repo = PurchaseRepository()

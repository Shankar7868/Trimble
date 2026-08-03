from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservation import reservation_service
from app.dependencies import get_current_user
from app.exceptions import ResourceNotFoundException, UnauthorizedAccessException

router = APIRouter(prefix="/reservations", tags=["reservations"])

@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    reservation_in: ReservationCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return reservation_service.create_reservation(db, reservation_in, user_id=current_user["id"])

@router.get("/", response_model=List[ReservationResponse])
def read_reservations(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Admins list all, customers list only their own
    filter_user_id = None if current_user["role"] == "admin" else current_user["id"]
    return reservation_service.list_reservations(db, user_id=filter_user_id, skip=skip, limit=limit)

@router.get("/{reservation_id}", response_model=ReservationResponse)
def read_reservation(
    reservation_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    res = reservation_service.get_reservation(db, reservation_id)
    if not res:
        raise ResourceNotFoundException("Reservation not found")
    
    # Ownership guard
    if current_user["role"] != "admin" and res.user_id != current_user["id"]:
        raise UnauthorizedAccessException("Access denied. You do not own this reservation.")
    return res

@router.post("/{reservation_id}/confirm", response_model=ReservationResponse)
def confirm_reservation(
    reservation_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Fetch reservation first to check ownership
    res = reservation_service.get_reservation(db, reservation_id)
    if not res:
        raise ResourceNotFoundException("Reservation not found")
    
    if current_user["role"] != "admin" and res.user_id != current_user["id"]:
        raise UnauthorizedAccessException("Access denied. You do not own this reservation.")
        
    return reservation_service.confirm_reservation(db, reservation_id)

@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return reservation_service.cancel_reservation(
        db, 
        reservation_id, 
        user_id=current_user["id"], 
        user_role=current_user["role"]
    )

@router.post("/cleanup", status_code=status.HTTP_200_OK)
def cleanup_expired(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    count = reservation_service.cleanup_expired_reservations(db)
    return {"message": f"Successfully cleaned up {count} expired reservations."}

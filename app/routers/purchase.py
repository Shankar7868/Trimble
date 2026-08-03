from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.purchase import PurchaseCreate, PurchaseResponse
from app.services.purchase import purchase_service
from app.dependencies import get_current_user
from app.exceptions import ResourceNotFoundException, UnauthorizedAccessException

router = APIRouter(prefix="/purchases", tags=["purchases"])

@router.post("/", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
def create_purchase(
    purchase_in: PurchaseCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if purchase_in.reservation_id is not None:
        return purchase_service.create_purchase_from_reservation(
            db, 
            purchase_in.reservation_id, 
            user_id=current_user["id"], 
            user_role=current_user["role"]
        )
    elif purchase_in.product_id is not None and purchase_in.quantity is not None:
        return purchase_service.create_direct_purchase(
            db, 
            purchase_in.product_id, 
            purchase_in.quantity, 
            user_id=current_user["id"]
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'reservation_id' or both 'product_id' and 'quantity' must be provided."
        )

@router.get("/", response_model=List[PurchaseResponse])
def read_purchases(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    filter_user_id = None if current_user["role"] == "admin" else current_user["id"]
    return purchase_service.list_purchases(db, user_id=filter_user_id, skip=skip, limit=limit)

@router.get("/{purchase_id}", response_model=PurchaseResponse)
def read_purchase(
    purchase_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    purchase = purchase_service.get_purchase(db, purchase_id)
    if not purchase:
        raise ResourceNotFoundException("Purchase not found")
    
    if current_user["role"] != "admin" and purchase.user_id != current_user["id"]:
        raise UnauthorizedAccessException("Access denied. You do not own this purchase.")
    return purchase

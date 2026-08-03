from app.routers.product import router as product_router
from app.routers.reservation import router as reservation_router
from app.routers.purchase import router as purchase_router

__all__ = ["product_router", "reservation_router", "purchase_router"]

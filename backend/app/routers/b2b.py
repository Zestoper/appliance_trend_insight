from fastapi import APIRouter
from app.routers.b2b_utils import *

router = APIRouter(prefix="/api/b2b", tags=["b2b"])

from app.routers.b2b_dashboard import router as _dashboard
from app.routers.b2b_price     import router as _price
from app.routers.b2b_ai        import router as _ai
from app.routers.b2b_product   import router as _product

router.include_router(_dashboard)
router.include_router(_price)
router.include_router(_ai)
router.include_router(_product)

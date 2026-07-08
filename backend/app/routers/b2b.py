from fastapi import APIRouter
from app.routers.b2b_utils import *

router = APIRouter(prefix="/api/b2b", tags=["b2b"])

from app.routers.b2b_price           import router as _price
from app.routers.b2b_product         import router as _product
from app.routers.b2b_search_analysis import router as _search_analysis

router.include_router(_price)
router.include_router(_product)
router.include_router(_search_analysis)

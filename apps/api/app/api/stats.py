from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.mongo import get_mongo_client
from app.schemas.stats import SkuStat, SkuStatsResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/sku", response_model=SkuStatsResponse)
async def sku_stats(
    limit: int = 50,
    from_ts: str | None = None,
    to_ts: str | None = None,
    _: dict = Depends(get_current_user),
) -> SkuStatsResponse:
    client = get_mongo_client()
    collection = client["app"]["sku_stats"]
    query: dict = {}
    if from_ts or to_ts:
        window_filter: dict = {}
        if from_ts:
            window_filter["$gte"] = from_ts
        if to_ts:
            window_filter["$lte"] = to_ts
        query["window_start"] = window_filter

    cursor = collection.find(query, {"_id": 0}).sort("window_start", -1).limit(limit)
    items = [SkuStat(**doc) for doc in cursor]
    return SkuStatsResponse(items=items)

from pydantic import BaseModel


class SkuStat(BaseModel):
    sku: str
    window_start: str
    window_end: str
    total_qty: int


class SkuStatsResponse(BaseModel):
    items: list[SkuStat]

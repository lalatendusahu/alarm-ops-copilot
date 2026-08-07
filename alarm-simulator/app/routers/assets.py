from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.auth import require_bearer_token
from app.db import get_session
from app.models import Asset
from app.serializers import asset_dict

router = APIRouter(dependencies=[Depends(require_bearer_token)])


@router.get("/assets/search")
def search_assets(
    query: str = Query(...),
    unit: str | None = None,
    site: str | None = None,
    limit: int = 10,
    session: Session = Depends(get_session),
):
    stmt = select(Asset)
    if unit:
        stmt = stmt.where(Asset.unit == unit)
    if site:
        stmt = stmt.where(Asset.site == site)
    assets = list(session.exec(stmt))

    needle = query.lower()
    matches = [
        a for a in assets
        if needle in a.asset_name.lower() or needle in a.asset_type.lower()
    ]
    matches.sort(key=lambda a: a.asset_name)
    return {"results": [asset_dict(a) for a in matches[:limit]], "count": len(matches)}


@router.get("/assets/{asset_id}/metadata")
def get_asset_metadata(asset_id: str, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"asset not found: {asset_id}")
    return asset_dict(asset)

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tables import UsCnMappingHistory


class MappingService:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(self, limit: int = 200) -> list[UsCnMappingHistory]:
        stmt = select(UsCnMappingHistory).order_by(UsCnMappingHistory.created_at.desc()).limit(min(limit, 500))
        return list(self.db.scalars(stmt).all())

    def search(
        self,
        us_symbol: str | None = None,
        cn_symbol: str | None = None,
        theme: str | None = None,
        report_date_start: date | None = None,
        report_date_end: date | None = None,
        limit: int = 200,
    ) -> list[UsCnMappingHistory]:
        stmt = select(UsCnMappingHistory).order_by(UsCnMappingHistory.created_at.desc())
        if us_symbol:
            stmt = stmt.where(UsCnMappingHistory.us_symbol.contains(us_symbol))
        if cn_symbol:
            stmt = stmt.where(UsCnMappingHistory.cn_symbol.contains(cn_symbol))
        if theme:
            stmt = stmt.where(UsCnMappingHistory.theme.contains(theme))
        if report_date_start:
            stmt = stmt.where(UsCnMappingHistory.report_date >= report_date_start)
        if report_date_end:
            stmt = stmt.where(UsCnMappingHistory.report_date <= report_date_end)
        stmt = stmt.limit(min(limit, 500))
        return list(self.db.scalars(stmt).all())

    def create(self, **kwargs) -> UsCnMappingHistory:
        obj = UsCnMappingHistory(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, mapping_id: int, **kwargs) -> UsCnMappingHistory | None:
        obj = self.db.get(UsCnMappingHistory, mapping_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        self.db.flush()
        return obj

    def delete(self, mapping_id: int) -> bool:
        obj = self.db.get(UsCnMappingHistory, mapping_id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True

from __future__ import annotations

from pydantic import BaseModel


class Screenshot(BaseModel):
    id: str
    filePath: str
    createdAt: str
    sentToModel: bool


class ScreenshotListResponse(BaseModel):
    screenshots: list[Screenshot]


class ScreenshotDeleteAllResponse(BaseModel):
    ok: bool
    deletedCount: int

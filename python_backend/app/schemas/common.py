"""Shared Pydantic models used across multiple API endpoints.

Generic pagination, error envelope, and common field types that don't
belong to a single schema module.
"""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool

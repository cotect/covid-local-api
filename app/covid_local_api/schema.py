from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# Field validation
# https://pydantic-docs.helpmanual.io/usage/schema/#field-customisation


class Hotline(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    geonames_ids: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[str] = None
    sources: Optional[str] = None


class HotlineList(BaseModel):
    hotlines: List[Hotline] = []

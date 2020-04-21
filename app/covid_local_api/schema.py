from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# Field validation
# https://pydantic-docs.helpmanual.io/usage/schema/#field-customisation


class Hotline(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    operation_hours: Optional[str] = None


class HotlineList(BaseModel):
    hotlines: List[Hotline] = []

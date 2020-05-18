from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# Field validation
# https://pydantic-docs.helpmanual.io/usage/schema/#field-customisation

class Place(BaseModel):
    name: str
    search_provider: str
    geonames_id: int
    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class Hotline(BaseModel):
    country_code: Optional[str] = None
    place: Optional[str] = None
    geonames_id: Optional[int] = None

    name: Optional[str] = None
    operator: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    operating_hours: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    sources: Optional[str] = None


class Website(BaseModel):
    country_code: Optional[str] = None
    place: Optional[str] = None
    geonames_id: Optional[int] = None

    name: Optional[str] = None
    operator: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    sources: Optional[str] = None


class TestSite(BaseModel):
    country_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    name: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    address_supplement: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    operating_hours: Optional[str] = None
    appointment_required: Optional[bool] = None
    description: Optional[str] = None
    sources: Optional[str] = None

    distance: Optional[float] = None  # added dynamically


class HealthDepartment(BaseModel):
    country_code: Optional[str] = None
    place: Optional[str] = None
    geonames_id: Optional[int] = None

    name: Optional[str] = None
    department: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    address_supplement: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    sources: Optional[str] = None


class Restriction(BaseModel):
    country_code: Optional[str] = None
    place: Optional[str] = None
    geonames_id: Optional[int] = None

    mask: Optional[str] = None
    events_gatherings: Optional[str] = None
    shops_gastronomy: Optional[str] = None
    schools_kindergarden: Optional[str] = None
    movement: Optional[str] = None
    description: Optional[str] = None
    sources: Optional[str] = None


# TODO: Maybe revert this to individual lists to make it a bit less ambiguous for the user.
class ResultsList(BaseModel):
    hotlines: List[Hotline] = []
    websites: List[Website] = []
    test_sites: List[TestSite] = []
    health_departments: List[HealthDepartment] = []
    restrictions: List[Restriction] = []

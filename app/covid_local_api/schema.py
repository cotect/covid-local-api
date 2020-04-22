from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# Field validation
# https://pydantic-docs.helpmanual.io/usage/schema/#field-customisation


class Hotline(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    geonames_id: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[str] = None
    sources: Optional[str] = None


class Website(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    geonames_id: Optional[int] = None
    
    name: Optional[str] = None
    author: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    
    sources: Optional[str] = None


class TestSite(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    geonames_id: Optional[int] = None
    
    name: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    address_supplement: Optional[str] = None
    phone: Optional[str] = None
    operating_hours: Optional[str] = None
    
    sources: Optional[str] = None


class HealthDepartment(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    geonames_id: Optional[int] = None
    
    name: Optional[str] = None
    code: Optional[str] = None
    department: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    sources: Optional[str] = None


# TODO: Maybe revert this to individual lists to make it a bit less ambiguous for the user.
class ResultsList(BaseModel):
    hotlines: List[Hotline] = []
    websites: List[Website] = []
    test_sites: List[TestSite] = []
    health_departments: List[HealthDepartment] = []


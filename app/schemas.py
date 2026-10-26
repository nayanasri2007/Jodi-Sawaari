from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str
    phone: str
    gender: Literal["male", "female"]

class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    gender: str
    verified: bool
    rating: float
    model_config = {"from_attributes": True}

class RideRequestCreate(BaseModel):
    user_id: int
    pickup_lat: float = Field(ge=-90, le=90)
    pickup_lng: float = Field(ge=-180, le=180)
    drop_lat: float = Field(ge=-90, le=90)
    drop_lng: float = Field(ge=-180, le=180)
    depart_time: datetime
    flexibility_minutes: int = 15
    preference: Literal["women_only", "men_only", "mixed"] = "mixed"

class RideRequestOut(RideRequestCreate):
    id: int
    status: str
    model_config = {"from_attributes": True}
class GroupCreate(BaseModel):
    request_ids: list[int] = Field(min_length=2)
    total_fare: float = Field(gt=0)


class GroupOut(BaseModel):
    id: int
    total_fare: float
    rider_count: int
    fare_per_rider: float
    user_ids: list[int]
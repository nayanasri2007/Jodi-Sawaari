from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String, unique=True)
    gender = Column(String)        # "male" or "female"
    verified = Column(Boolean, default=False)
    rating = Column(Float, default=5.0)


class RideRequest(Base):
    __tablename__ = "ride_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    drop_lat = Column(Float)
    drop_lng = Column(Float)

    depart_time = Column(DateTime)
    flexibility_minutes = Column(Integer, default=15)

    preference = Column(String, default="mixed")        # "women_only", "men_only", "mixed"
    status = Column(String, default="open")             # "open", "matched", "cancelled"


class RideGroup(Base):
    __tablename__ = "ride_groups"

    id = Column(Integer, primary_key=True)
    total_fare = Column(Float)
    status = Column(String, default="confirmed")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("ride_groups.id"))
    request_id = Column(Integer, ForeignKey("ride_requests.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
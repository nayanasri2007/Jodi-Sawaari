from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db, ensure_columns
from app import models, schemas
from app.matching import is_match

app = FastAPI(title="Jodi Sawaari", description="Share the ride, split the fare")

Base.metadata.create_all(bind=engine)
ensure_columns()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Time and waiting rules ----------

IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving
WAIT_LIMIT_MIN = 10          # how long a "leave now" ride waits for a co-rider
IMMEDIATE_WINDOW_MIN = 30    # rides leaving within this many minutes count as "leave now"


def now_ist():
    return datetime.now(IST).replace(tzinfo=None)


def is_immediate(r):
    if r.created_at is None:
        return False
    return (r.depart_time - r.created_at) <= timedelta(minutes=IMMEDIATE_WINDOW_MIN)


def seconds_left(r):
    if r.status != "open" or not is_immediate(r):
        return None
    elapsed = (now_ist() - r.created_at).total_seconds()
    return max(0, int(WAIT_LIMIT_MIN * 60 - elapsed))


def expire_stale(db: Session):
    """Mark open requests as expired if departure has passed or the wait limit ran out."""
    now = now_ist()
    changed = False
    open_requests = db.query(models.RideRequest).filter(models.RideRequest.status == "open").all()
    for r in open_requests:
        departure_passed = now > r.depart_time + timedelta(minutes=r.flexibility_minutes)
        waited_too_long = is_immediate(r) and (now - r.created_at) > timedelta(minutes=WAIT_LIMIT_MIN)
        if departure_passed or waited_too_long:
            r.status = "expired"
            changed = True
    if changed:
        db.commit()


def request_out(r):
    out = schemas.RideRequestOut.model_validate(r)
    out.wait_seconds_left = seconds_left(r)
    return out


def group_out(db: Session, group):
    members = db.query(models.GroupMember).filter(models.GroupMember.group_id == group.id).all()
    count = len(members)
    return schemas.GroupOut(
        id=group.id,
        total_fare=group.total_fare,
        rider_count=count,
        fare_per_rider=round(group.total_fare / count, 2),
        user_ids=[m.user_id for m in members],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Users ----------

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.phone == user.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    new_user = models.User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/users/login", response_model=schemas.UserOut)
def login_or_signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.phone == user.phone).first()
    if existing:
        return existing

    new_user = models.User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ---------- Ride requests ----------

@app.post("/ride-requests", response_model=schemas.RideRequestOut)
def create_ride_request(req: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    user = db.get(models.User, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety rule: you can only pick a gender-only ride that matches your own gender
    if req.preference == "women_only" and user.gender != "female":
        raise HTTPException(status_code=400, detail="Women-only rides are for women")
    if req.preference == "men_only" and user.gender != "male":
        raise HTTPException(status_code=400, detail="Men-only rides are for men")

    # A person can only have one open request: cancel their older ones
    db.query(models.RideRequest).filter(
        models.RideRequest.user_id == req.user_id,
        models.RideRequest.status == "open",
    ).update({"status": "cancelled"})

    new_req = models.RideRequest(**req.model_dump(), created_at=now_ist())
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return request_out(new_req)


@app.get("/ride-requests/{request_id}", response_model=schemas.RideRequestOut)
def get_request_status(request_id: int, db: Session = Depends(get_db)):
    expire_stale(db)
    r = db.get(models.RideRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return request_out(r)


@app.get("/ride-requests/{request_id}/matches", response_model=list[schemas.MatchOut])
def find_matches(request_id: int, db: Session = Depends(get_db)):
    expire_stale(db)
    my_req = db.get(models.RideRequest, request_id)
    if not my_req:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if my_req.status != "open":
        raise HTTPException(status_code=400, detail="This ride request is no longer open")
    me = db.get(models.User, my_req.user_id)

    others = (
        db.query(models.RideRequest)
        .filter(models.RideRequest.status == "open")
        .filter(models.RideRequest.user_id != my_req.user_id)
        .all()
    )

    matches = []
    for other in others:
        other_user = db.get(models.User, other.user_id)
        if is_match(my_req, me.gender, other, other_user.gender):
            matches.append(
                schemas.MatchOut(
                    id=other.id,
                    rider_name=other_user.name,
                    rider_rating=other_user.rating,
                    preference=other.preference,
                    depart_time=other.depart_time,
                    pickup_label=other.pickup_label or "",
                    drop_label=other.drop_label or "",
                )
            )
    return matches


@app.post("/ride-requests/{request_id}/cancel", response_model=schemas.RideRequestOut)
def cancel_request(request_id: int, db: Session = Depends(get_db)):
    r = db.get(models.RideRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if r.status not in ("open", "expired"):
        raise HTTPException(status_code=400, detail="This ride can no longer be cancelled")
    r.status = "cancelled"
    db.commit()
    db.refresh(r)
    return request_out(r)


@app.post("/ride-requests/{request_id}/extend", response_model=schemas.RideRequestOut)
def extend_request(request_id: int, db: Session = Depends(get_db)):
    """Keep waiting: restart the wait timer."""
    r = db.get(models.RideRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if r.status not in ("open", "expired"):
        raise HTTPException(status_code=400, detail="This ride can no longer be extended")
    now = now_ist()
    r.created_at = now
    if r.depart_time < now:
        r.depart_time = now
    r.status = "open"
    db.commit()
    db.refresh(r)
    return request_out(r)


@app.post("/ride-requests/{request_id}/solo", response_model=schemas.GroupOut)
def ride_alone(request_id: int, data: schemas.SoloCreate, db: Session = Depends(get_db)):
    """Confirm a ride for one person only."""
    r = db.get(models.RideRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if r.status not in ("open", "expired"):
        raise HTTPException(status_code=400, detail="This ride can no longer be booked alone")

    group = models.RideGroup(total_fare=data.total_fare)
    db.add(group)
    db.flush()
    db.add(models.GroupMember(group_id=group.id, request_id=r.id, user_id=r.user_id))
    r.status = "solo"
    db.commit()
    return group_out(db, group)


@app.get("/ride-requests/{request_id}/group", response_model=schemas.GroupOut)
def get_group_for_request(request_id: int, db: Session = Depends(get_db)):
    member = db.query(models.GroupMember).filter(models.GroupMember.request_id == request_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="No group for this request yet")
    group = db.get(models.RideGroup, member.group_id)
    return group_out(db, group)


# ---------- Groups and fare split ----------

@app.post("/groups", response_model=schemas.GroupOut)
def create_group(data: schemas.GroupCreate, db: Session = Depends(get_db)):
    expire_stale(db)

    if len(set(data.request_ids)) != len(data.request_ids):
        raise HTTPException(status_code=400, detail="Duplicate request ids")

    requests = []
    for rid in data.request_ids:
        r = db.get(models.RideRequest, rid)
        if not r:
            raise HTTPException(status_code=404, detail=f"Ride request {rid} not found")
        if r.status != "open":
            raise HTTPException(status_code=400, detail="That rider is no longer available")
        requests.append(r)

    if len({r.user_id for r in requests}) != len(requests):
        raise HTTPException(status_code=400, detail="Same person added twice")

    users = [db.get(models.User, r.user_id) for r in requests]

    # Every pair of riders must match each other
    for (r1, u1), (r2, u2) in combinations(zip(requests, users), 2):
        if not is_match(r1, u1.gender, r2, u2.gender):
            raise HTTPException(status_code=400, detail="These requests do not all match each other")

    group = models.RideGroup(total_fare=data.total_fare)
    db.add(group)
    db.flush()  # gives the group an id before we save members

    for r in requests:
        db.add(models.GroupMember(group_id=group.id, request_id=r.id, user_id=r.user_id))
        r.status = "matched"
    db.commit()

    return group_out(db, group)


# ---------- Web page (keep these at the bottom) ----------

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")
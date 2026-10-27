from itertools import combinations
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app import models, schemas
from app.matching import is_match

app = FastAPI(title="Jodi Sawaari", description="Share the ride, split the fare")

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent


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


@app.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


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

    new_req = models.RideRequest(**req.model_dump())
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req


@app.get("/ride-requests", response_model=list[schemas.RideRequestOut])
def list_open_requests(db: Session = Depends(get_db)):
    return db.query(models.RideRequest).filter(models.RideRequest.status == "open").all()


@app.get("/ride-requests/{request_id}/matches", response_model=list[schemas.MatchOut])
def find_matches(request_id: int, db: Session = Depends(get_db)):
    my_req = db.get(models.RideRequest, request_id)
    if not my_req:
        raise HTTPException(status_code=404, detail="Ride request not found")
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
                    **schemas.RideRequestOut.model_validate(other).model_dump(),
                    rider_name=other_user.name,
                    rider_rating=other_user.rating,
                )
            )
    return matches


@app.post("/ride-requests/{request_id}/cancel", response_model=schemas.RideRequestOut)
def cancel_request(request_id: int, db: Session = Depends(get_db)):
    r = db.get(models.RideRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if r.status != "open":
        raise HTTPException(status_code=400, detail="Only open requests can be cancelled")
    r.status = "cancelled"
    db.commit()
    db.refresh(r)
    return r


# ---------- Groups and fare split ----------

@app.post("/groups", response_model=schemas.GroupOut)
def create_group(data: schemas.GroupCreate, db: Session = Depends(get_db)):
    if len(set(data.request_ids)) != len(data.request_ids):
        raise HTTPException(status_code=400, detail="Duplicate request ids")

    requests = []
    for rid in data.request_ids:
        r = db.get(models.RideRequest, rid)
        if not r:
            raise HTTPException(status_code=404, detail=f"Ride request {rid} not found")
        if r.status != "open":
            raise HTTPException(status_code=400, detail=f"Ride request {rid} is not open")
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

    count = len(requests)
    return schemas.GroupOut(
        id=group.id,
        total_fare=group.total_fare,
        rider_count=count,
        fare_per_rider=round(group.total_fare / count, 2),
        user_ids=[r.user_id for r in requests],
    )


# ---------- Web page (keep these at the bottom) ----------

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")
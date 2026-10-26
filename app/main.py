from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.matching import is_match
from app.database import engine, Base, get_db
from app import models, schemas
from itertools import combinations
app = FastAPI(title="Jodi Sawaari", description="Share the ride, split the fare")

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


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

    new_req = models.RideRequest(**req.model_dump())
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req


@app.get("/ride-requests", response_model=list[schemas.RideRequestOut])
def list_open_requests(db: Session = Depends(get_db)):
    return db.query(models.RideRequest).filter(models.RideRequest.status == "open").all()
@app.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
@app.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
@app.get("/ride-requests/{request_id}/matches", response_model=list[schemas.RideRequestOut])
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
            matches.append(other)
    return matches
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
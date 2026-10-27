# Jodi Sawaari

**Share the ride, split the fare.**

Jodi Sawaari helps people going the same way at the same time find fellow passengers, so they can share a cab or auto and split the cost. Riders can choose who they travel with: women only, men only, or mixed.



## Why I built it

Booking a cab on apps like Ola, Uber or Rapido usually means paying the full fare alone, even when someone nearby is heading to the same place. Many women also feel unsafe riding with strangers. This project tackles both problems: it finds co-riders and lets each rider control who they travel with.

## Features

- Sign up with name, phone number and gender
- Pick pickup and drop points on an interactive map (Leaflet + OpenStreetMap)
- Choose a ride preference: **women only**, **men only** or **mixed**
- Automatic matching by pickup distance, drop distance and departure time
- Safety rules enforced on the server:
  - Only women can post women-only rides, and only men can post men-only rides
  - A group can only be created if every pair of riders is compatible
  - A phone number stays tied to the gender it was registered with
- Fare split between group members
- One open request per person, and cancelling a request

## How matching works

Two requests match when all of these are true:

1. Each rider's preference accepts the other rider's gender
2. Pickup points are within 1 km (haversine distance)
3. Drop points are within 2 km
4. Departure times are within the riders' combined flexibility window

The matching logic is a plain Python module with unit tests (`tests/test_matching.py`).

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** HTML, CSS, JavaScript, Leaflet
- **Testing:** pytest

## Run it locally

```
git clone https://github.com/nayanasri2007/Jodi-Sawaari.git
cd Jodi-Sawaari
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --reload-dir app
```

Then open http://127.0.0.1:8000/ for the app, or http://127.0.0.1:8000/docs for the API docs.

Run the tests with `python -m pytest`.

## Known limitations and next steps

- Phone sign-in has no OTP verification yet
- Groups currently have two riders
- Booking happens outside the app: matched riders book in their usual cab app and split the fare
- Planned: ratings, report and block, trip sharing with a trusted contact, mobile app

## Author

NAYANA SRI ARVAPALLY - https://github.com/nayanasri2007

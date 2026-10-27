# Jodi Sawaari

**Share the ride, split the fare.**

**Live demo:** https://jodi-sawaari.onrender.com
*(Hosted on a free plan, so the first load after a quiet period can take about a minute.)*

Jodi Sawaari helps people going the same way at the same time find fellow passengers, so they can share a cab or auto and split the cost. Riders choose who they travel with: women only, men only, or mixed.

## Why I built it

Booking a cab on apps like Ola, Uber or Rapido usually means paying the full fare alone, even when someone nearby is heading to the same place. Many women also feel unsafe riding with strangers. This project tackles both problems: it finds co-riders and lets each rider control who they travel with.

## Try it

Open the live app: **https://jodi-sawaari.onrender.com**

API documentation (interactive): **https://jodi-sawaari.onrender.com/docs**

To see the women-only matching in action, create three riders on the same route and time:

1. A woman choosing **Women only**
2. A second woman choosing **Women only**. She will see the first woman as a match.
3. A man choosing **Mixed**. He will see neither of them.

Use a different phone number for each rider, because each number stays tied to the gender it was first registered with.

## Features

- Sign in with name, phone number and gender
- Pick pickup and drop points on an interactive map (Leaflet and OpenStreetMap)
- Choose a ride preference: **women only**, **men only** or **mixed**
- Automatic matching by pickup distance, drop distance and departure time
- Safety rules enforced on the server:
  - Only women can post women-only rides, and only men can post men-only rides
  - A group can only be created if every pair of riders is compatible
  - A phone number stays tied to the gender it was registered with
- Group creation with an automatic fare split
- One open request per person, and request cancellation

## How matching works

Two requests match when all of these are true:

1. Each rider's preference accepts the other rider's gender
2. Pickup points are within 1 km (haversine distance)
3. Drop points are within 2 km
4. Departure times are within the riders' combined flexibility window

The matching logic is a plain Python module with unit tests in `tests/test_matching.py`.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** PostgreSQL (Neon) in production, SQLite for local development
- **Frontend:** HTML, CSS, JavaScript, Leaflet
- **Hosting:** Render
- **Testing:** pytest

## Project structure

```
Jodi-Sawaari/
├── app/
│   ├── main.py        API endpoints
│   ├── models.py      Database tables
│   ├── schemas.py     Request and response validation
│   ├── matching.py    Matching and distance logic
│   └── database.py    Database connection
├── static/
│   └── index.html     Web page with the map
├── tests/
│   └── test_matching.py
└── requirements.txt
```

## Run the code yourself (optional)

```
git clone https://github.com/nayanasri2007/Jodi-Sawaari.git
cd Jodi-Sawaari
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --reload-dir app
```

The terminal prints the address to open in your browser. Run the tests with `python -m pytest`.

By default the app uses a local SQLite file. To use PostgreSQL instead, set a `DATABASE_URL` environment variable before starting the server.

## Known limitations and next steps

- Phone sign-in has no OTP verification yet
- Groups currently have two riders
- Booking happens outside the app: matched riders book in their usual cab app and split the fare
- Planned: ratings, report and block, trip sharing with a trusted contact, a mobile app

## Author: NAYANA SRI- https://github.com/nayanasri2007

# Air Traffic Management Simulation

A Python simulation focused on the three things that actually matter for basic ATM research:

1. **4D trajectory modeling** — position + altitude + time, with wind affecting the ground track  
2. **Conflict detection & resolution** — CPA-based detection + simple ATC-style manoeuvres  
3. **Weather integration** — background wind, altitude shear, and light turbulence

Built for students who want to understand the concepts without drowning in a 50k-line codebase.

---

## What it does

You drop a handful of aircraft into a piece of airspace.  
The sim advances them with realistic kinematics (heading, speed, vertical rate) under a wind field.  
Every few seconds it checks pairs for loss of separation using a closest-point-of-approach calculation.  
If a conflict is found and auto-resolve is on, it tries a small set of climb / descend / turn / speed-change options and picks the cheapest one that actually works.

At the end you get a summary and two plots: horizontal tracks and altitude profiles.

---

## Quick start

```bash
# clone (or just open the folder)
git clone https://github.com/NihalShore/Air-Traffic-Management-Simulation.git
cd Air-Traffic-Management-Simulation

# optional but recommended
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

python main.py
```

Useful flags:

```bash
python main.py --duration 600          # longer run
python main.py --no-resolve            # only detect, don't fix
python main.py --wind 45               # stronger wind
python main.py --no-plot               # headless
```

---

## Project layout

```
├── main.py                 # demo entry point
├── requirements.txt
├── src/
│   ├── aircraft.py         # state + simple kinematics
│   ├── trajectory.py       # 4D path container + interpolation
│   ├── weather.py          # analytic wind field + turbulence
│   ├── conflict_detection.py
│   ├── conflict_resolution.py
│   ├── simulation.py       # main loop
│   └── utils.py            # lat/lon, unit conversions, etc.
├── config/                 # (for future scenario files)
└── results/                # plots land here
```

---

## How the pieces fit

**Aircraft**  
Just a dataclass with lat/lon/alt, speed, heading, vertical rate.  
`step(dt, wind)` integrates position. History is recorded automatically so we can build trajectories later.

**Weather**  
A constant wind + linear shear with altitude + a bit of time-varying noise and turbulence.  
Easy to replace later with real GRIB data if you want.

**Conflict detection**  
Classic relative CPA in a local Cartesian frame.  
Horizontal + vertical minima are the usual 5 nm / 1000 ft.  
Lookahead is 5 minutes by default.

**Conflict resolution**  
Generates a short list of candidates (heading ±15/20/30°, climb/descend 1500–2000 fpm, ±30–40 kt).  
Each candidate is tested with a quick forward simulation of the pair.  
Cheapest one that clears the conflict wins.

**Simulation**  
Time-stepped loop. Detect → (optionally) resolve → record.  
O(n²) pair checks are fine for the 4–20 aircraft you typically play with in a student project.

---

## Extending it

A few natural next steps:

- Load scenarios from JSON instead of hard-coding them in `main.py`
- Add more realistic aircraft performance models (BADA-style or simple look-up tables)
- Uncertainty / intent: inflate the protected zone based on navigation accuracy
- Multi-aircraft resolution (currently we only move the first aircraft of the pair)
- Real weather from Open-Meteo or NOAA
- Live visualisation with matplotlib animation or pygame
- Sector boundary & capacity metrics

The code is deliberately kept readable so you can open any file and follow the logic without a map.

---

## Requirements

- Python 3.9+
- numpy, matplotlib, scipy (see `requirements.txt`)

No MATLAB, no special toolboxes, no paid data.

---

## License

MIT — same as the original repo.

---

Built as a clean, working foundation for anyone learning avionics / ATM software.  
If you improve it, open a PR or just fork and make it yours.

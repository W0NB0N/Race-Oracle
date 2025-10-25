# F1 Race Simulation Visualizers

This repository provides two Python-based tools for visualizing Formula 1 race data: a retro-themed single-driver lap simulator, and a multi-driver real-time race simulator with a live leaderboard and custom circuit map background.

---

## Files Included

### `90s-sim.py`
**Single-Driver Retro Lap Simulator**

- Simulates an F1 driver driving lap-by-lap on a stylized retro display.
- Animated car position, lap and speed stats, with 90s arcade visual effects (neon colors, scanlines).
- Controls for pausing, seeking laps, and speed adjustment.

### `multi-sim.py`
**Multi-Driver Real-Time Race Simulator**

- Simulates the full race for multiple F1 drivers using real telemetry, mapping car positions to real-time, not lapwise.
- Displays a live leaderboard with gap-to-leader in meters/kilometers, correctly handling differing lap counts.
- Uses a custom track image background (`circuit.png`) for realistic visual context.
- Allows pausing, skipping, and speed adjustments.

---

## Prerequisites

You'll need Python 3.8+ and these libraries:

- `pygame`
- `numpy`
- `pandas`
- `fastf1`

Install dependencies with:

`pip install pygame numpy pandas fastf1`



---

## How to Run

1. Place `90s-sim.py`, `multi-sim.py`, and your desired circuit map image (renamed as `circuit.png`) in the same directory.
2. Edit the script(s) if you want to change the event parameters (driver, year, etc.).
3. Run either script using:

`python 90s-sim.py`


or
`python multi-sim.py`



> The window may show 'Not Responding' while FastF1 downloads and processes the initial data—**this is normal and only happens on first run**. Please wait; the window will become interactive when data loading is complete.

---

## Controls

- `Space`: Pause/Resume
- `Left`/`Right`: Skip laps or skip time (depending on script)
- `Up`/`Down`: Change playback speed
- `R`: Reset playback to start

---

## Credits

- [FastF1](https://theoehrly.github.io/Fast-F1/)
- [pygame](https://www.pygame.org/)
- Custom circuit image (user-supplied)

---

Feel free to fork and extend for more tracks, drivers, or advanced analysis!
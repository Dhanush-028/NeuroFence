# VoltGuard - Native Qt/C++ Dashboard

This is the literal fulfillment of the project PDF's Week 2 line: *"Build
the foundation of a native Qt C++ desktop app to log incoming traffic."*

## How it connects to the Python side

It doesn't call any Python code directly - it **tails
`voltguard_log.csv`**, the same log file `decision_engine.py`,
`gateway.py`, and `main_sim.py` already write to. That's a deliberate
choice: the C++ dashboard is completely decoupled from whichever Python
entry point is generating traffic (`main_sim.py`, `network_demo.py`, or
the real three-terminal `gateway.py` setup) - it just reads verdicts as
they land, the same way a real log-monitoring tool would.

It polls the file every 400ms, reads only the new bytes since last read
(not the whole file each time), and appends new rows to the table live -
color-coded green/red by verdict, with a big status banner and running
counters, matching the same visual language as the Python dashboard.

Built and compile-tested here (Qt 5.15, g++ 13, CMake) - zero errors,
verified against real generated traffic including the CSV's `\r\n` line
ending quirk (Python's `csv` module writes `\r\n` even on Linux/macOS,
which will trip up naive line-splitting if you don't account for it -
this build does).

## Building on your Windows machine

**Easiest path - Qt Creator (recommended):**

1. Install Qt Creator via the official open-source installer:
   https://www.qt.io/download-qt-installer
   During setup, select a Qt version (5.15 LTS or 6.x both work) with
   the **MinGW 64-bit** compiler kit, plus CMake if it's not already
   bundled (it usually is).
2. Open Qt Creator -> **File -> Open File or Project** -> select
   `CMakeLists.txt` in this folder.
3. Qt Creator will detect a Kit automatically (e.g. "Desktop Qt 5.15.2
   MinGW 64-bit"). Accept it and let it configure.
4. Click the hammer icon (Build), then the green play button (Run).

**Working directory matters:** the app looks for `voltguard_log.csv` in
its current working directory. By default Qt Creator runs the app from
its build folder, which won't have the log file. Fix it once:
**Projects (left sidebar) -> Run -> Working directory** -> set it to
your Python project folder (the one with `main_sim.py` etc. in it), or
just copy `voltguard_log.csv` into the build folder after generating
some traffic.

**Command-line alternative (if you have MinGW + CMake on PATH already):**
```
mkdir build && cd build
cmake .. -G "MinGW Makefiles"
cmake --build .
```
Then run `voltguard_qt.exe` from inside your Python project folder (or
copy `voltguard_log.csv` next to the .exe), since it reads the log from
its current directory.

## Try it

1. In one terminal: generate some traffic the usual way -
   `python main_sim.py --count 100 --malicious-ratio 0.2` (or run
   `network_demo.py` for the live network version).
2. Run `voltguard_qt.exe` (from the same folder, or with the working
   directory set as above).
3. Watch the table populate, the banner flip red on a DROP, and the
   counters climb - all reading the exact same log file the Python
   pipeline already produces.

## Scope note

This is the Week 2 **foundation** on purpose - a log viewer, not the
real-time predicted-vs-actual pressure graph. That graph is explicitly a
Week 3 deliverable in the project plan ("Visualizing Physics: Add
real-time graphs to the Qt UI"), so it gets built on top of this same
C++ codebase then, using Qt Charts.

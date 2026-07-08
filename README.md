# JARVIS AI OS -- Core (Python)

Working core: 39 numbered agents + LocationAgent, an orchestrator, the runtime
OS layer, a REST+WebSocket API, and hologram-side reference files (connector +
color-coded agent panels).

## Quick start

```bash
./run_jarvis.sh      # Linux/Mac
run_jarvis.bat        # Windows
```

Then check:
- http://localhost:8000/agents             -- list all agents + capabilities
- http://localhost:8000/health             -- health status of every agent
- ws://localhost:8000/ws                   -- real-time bridge for the hologram

## New in this round

**Location + weather** (`agents/location/agent.py`) -- free, no-API-key:
- `my_location` -- IP geolocation (ip-api.com)
- `geocode` -- place name -> lat/lon (open-meteo.com geocoding)
- `weather` / `weather_here` -- current conditions for any place or your IP location (open-meteo.com)

**Real-time web search** (`agents/browser/agent.py`, action `search`) -- DuckDuckGo
HTML endpoint, no API key, returns title/url/snippet per result.

**Native SAPI5 on Windows** (`agents/voice/agent.py`) -- speak/list_voices use
SAPI5 directly via pywin32 when on Windows, falling back to pyttsx3 (which
itself uses SAPI5 under the hood) everywhere else or if pywin32 isn't installed.

**Progress reporting** -- every agent now tracks call_count, success/failure
counts, avg duration, and last-used time (`BaseAgent.progress()`). Query all
of it at once with `supervisor.progress_report`, which also surfaces the
5 most-used agents and any agent that's never been called.

**Hologram side panels** (`hologram_agent_panels_reference.js`) -- reference
module for your existing hologram project: two fixed panels (left/right)
listing every agent, each with a deterministic color (same hash everywhere,
so an agent's color never changes across reloads), a status dot that flashes
green/red on task completion/failure via the live `/ws` event stream, and a
running call counter.

IMPORTANT -- this project was built in a network-isolated sandbox. Location,
weather, and web search are written correctly and confirmed to reach the
network (the sandbox's proxy returned a clean HTTP 403, proving the request
logic works), but the actual API responses were never seen. Test these three
on your own machine first before relying on them.

## Layout

```
JARVIS_AI_OS/
├── python/
│   ├── agents/
│   │   ├── base_agent.py          # contract every agent implements, now with progress() metrics
│   │   ├── registry.py            # holds live agent instances, progress_all()
│   │   ├── all_agents.py          # single import list: 39 core + EXTRA_AGENT_CLASSES (location)
│   │   ├── location/agent.py      # NEW: IP geolocation + weather, no API key
│   │   └── <1 folder per agent>/agent.py
│   ├── moa/orchestrator.py        # entry point: routes (agent, action, params) -> AgentResult
│   └── api/
│       ├── rest_server/main.py    # FastAPI: /agents /health /execute /ws
│       └── websocket/bridge.py    # powers /ws -- broadcasts every agent event live
├── runtime/                       # event bus, state machine, scheduler, process manager, health monitor
├── hologram_connector_reference.js       # JarvisConnector class -- wire into your hologram's websocket.js
├── hologram_agent_panels_reference.js    # NEW: left/right color-coded agent panels
├── requirements.txt
├── run_jarvis.sh / run_jarvis.bat
└── README.md (this file)
```

## Calling the new features

```python
from moa.orchestrator import Orchestrator
import asyncio

async def main():
    orch = Orchestrator()

    me = await orch.run("location", "my_location", {})
    print(me.data)  # {city, region, country, lat, lon, ...}

    w = await orch.run("location", "weather", {"place": "Tokyo"})
    print(w.data)  # {temperature_c, condition, humidity_pct, ...}

    results = await orch.run("browser", "search", {"query": "latest AI news"})
    print(results.data["results"])  # [{title, url, snippet}, ...]

    progress = await orch.run("supervisor", "progress_report", {})
    print(progress.data["most_used_agents"])

asyncio.run(main())
```

## Adding agent #41

1. Write `python/agents/your_agent/agent.py`, subclassing `BaseAgent`.
2. Add one import + one line to `python/agents/all_agents.py`
   (to `ALL_AGENT_CLASSES` if it's a core numbered agent, or `EXTRA_AGENT_CLASSES`
   if it sits outside the 39, like `location`).
Nothing else needs to change.

## What's real vs. scaffolded

**Fully working, tested end-to-end in this sandbox:** memory (SQLite-persisted),
files, coding, networking, security, learning (SM-2 spaced repetition), ocr
(real tesseract, proved with an actual image), admin, communications, all 14
educator agents, rag, research, debugging, testing, documentation,
windows/linux OS commands, plugins loader, app_controller, supervisor
(including new progress_report), and the entire runtime layer.

**Written correctly, network calls confirmed reaching out but not verified
end-to-end** (sandbox has no open network egress): location (IP geolocation +
weather via open-meteo.com), browser.search (DuckDuckGo HTML), voice
(faster-whisper STT + SAPI5/pyttsx3 TTS -- also no mic/speaker in this sandbox).

**Scaffolded with clear extension points (returns an honest "not wired in"
message, never a fake result):** vision (needs ultralytics/YOLO), translation
(needs a translation API), robotics (needs your board's SDK), iot (needs an
MQTT broker), browser.fetch for JS-heavy sites (needs Playwright).

Not yet built: the 9-layer security stack, Rust/C++/C# performance and
hardware layers, the desktop WPF shell, gRPC servers, and
knowledge_graph/vector_memory backends (chroma/neo4j) -- deliberately
deferred until the core loop above is proven out on real hardware.

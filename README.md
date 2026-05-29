# NEXUS — Personal Intelligence System

A living AI operating system that runs entirely on your local machine.

```
███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

## What it is

NEXUS is not a chatbot. It is a multi-panel terminal cockpit that:

- **Thinks** — multi-agent AI via Ollama with full RAG over all your code and documents
- **Trains** — runs a live neural network in the background, visualizing every weight update
- **Sees** — monitors your local network, tracks devices, flags anomalies
- **Codes** — generates and executes Python autonomously in a sandboxed environment
- **Remembers** — TF-IDF vector search over your entire codebase, CV, and documents
- **Visualizes** — opens a live 3D brain visualization in the browser via WebSocket

## Architecture

```
nexus/
├── nexus.py                # Entry point — boots all systems
├── brain/
│   ├── core.py             # Ollama client, multi-agent coordinator, code executor
│   └── rag.py              # TF-IDF RAG engine — indexes all local documents
├── workers/
│   ├── neural_worker.py    # Runs neuralkit training in background, streams state
│   └── security_worker.py  # Network scanner, device tracker
├── ui/
│   └── terminal.py         # Full-screen ANSI cockpit (raw escape codes, 15fps)
└── web/
    ├── server.py            # WebSocket bridge + HTTP file server
    └── brain_3d.html        # Three.js 3D neural network visualization
```

## Requirements

```bash
pip3 install numpy requests websockets
# For AI: install Ollama — https://ollama.ai
ollama pull llama3.2:1b
```

## Run

```bash
python3 nexus.py
```

NEXUS opens a full-screen terminal cockpit. The 3D brain visualization opens automatically in your browser.

## Terminal Commands

| Command | Description |
|---------|-------------|
| `<any text>` | Ask the AI anything — uses RAG context |
| `/train [dataset]` | Start neural training (spiral/moons/circles/xor) |
| `/scan` | Rescan local network |
| `/code <desc>` | Generate and execute Python code |
| `/3d` | Open 3D visualization |
| `/clear` | Clear chat history |
| `/quit` | Exit NEXUS |

## Panels

```
┌──────────────────────────────┬────────────────────────────────────┐
│  ◈ AI BRAIN                  │  ◈ NEURAL ACTIVITY                  │
│  Multi-agent AI with RAG     │  Live training visualization         │
│  Streams token by token      │  Loss / accuracy / layer activations │
│                              ├────────────────────────────────────┤
│  ▸ _                         │  ◈ SECURITY MONITOR                 │
│                              │  Network devices · Threat assessment │
│                              ├────────────────────────────────────┤
│                              │  ◈ TASKS                            │
│                              │  Boot sequence · Live progress       │
├──────────────────────────────┴────────────────────────────────────┤
│  Commands: /think  /code  /train  /scan  /3d  /clear  /quit       │
└───────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Python** — core runtime, no heavy frameworks
- **Ollama** — local LLM inference (llama3.2:1b or any model)
- **neuralkit** — live neural network training (from scratch, NumPy only)
- **Raw ANSI** — terminal UI (same philosophy as the `tui` project)
- **Three.js r160** — 3D neural visualization with UnrealBloom
- **WebSocket** — live bridge between terminal and browser
- **TF-IDF** — local vector search, zero external dependencies

Zero cloud. Zero API keys. Runs entirely on your machine.

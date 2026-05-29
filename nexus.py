#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║  NEXUS — Personal Intelligence System                         ║
║  Abdul Hadi Khan                                              ║
║                                                               ║
║  RAG · Multi-Agent AI · Live Neural Training · Security       ║
║  Code Execution · Network Monitor · 3D Visualization          ║
╚═══════════════════════════════════════════════════════════════╝

Usage: python3 nexus.py
"""

import sys, os, time, threading

sys.path.insert(0, os.path.dirname(__file__))


def boot_sequence(ui):
    """Staged boot with progress updates."""
    time.sleep(0.3)

    # Stage 1: Check Ollama
    ui.update_task(0, 30)
    time.sleep(0.4)
    available = ui.brain.ollama.available
    ui.update_task(0, 100, done=True)
    if available:
        ui.add_message('nexus', f'Ollama online. Model: {ui.brain.ollama.model}')
    else:
        ui.add_message('nexus', 'Ollama offline. Running in fallback mode. Start with: ollama serve')

    # Stage 2: Index documents
    ui.update_task(1, 10)
    def index_docs():
        ui.rag.index_all()
        ui.update_task(1, 100, done=True)
        ui.add_message('nexus', f'Indexed {len(ui.rag.docs)} documents. RAG memory online.')
    t2 = threading.Thread(target=index_docs, daemon=True)
    t2.start()

    # Stage 3: Start neural trainer
    ui.update_task(2, 50)
    ui.neural.start('spiral')
    ui.update_task(2, 100, done=True)

    # Stage 4: Start security scanner
    ui.update_task(3, 50)
    ui.security.start()
    ui.update_task(3, 100, done=True)

    # Wait for doc indexing
    t2.join(timeout=15)

    # Stage 5: All online
    ui.update_task(4, 100, done=True)
    ui.add_message('nexus',
        'NEXUS fully operational.\n'
        'I know your 7 projects, 3 internships, 19 certifications.\n'
        'Type anything to begin. /help for commands.'
    )


def main():
    # Print boot banner before entering raw mode
    print('\033[2J\033[H')
    print('\033[38;2;200;255;0m')
    print('  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗')
    print('  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝')
    print('  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗')
    print('  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║')
    print('  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║')
    print('  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝')
    print('\033[0m')
    print('\033[2m  Personal Intelligence System — Abdul Hadi Khan\033[0m')
    print('\033[2m  Initializing...\033[0m')
    time.sleep(1.5)

    # Import all components
    from brain.rag  import RAGEngine
    from brain.core import Brain
    from workers.neural_worker   import NeuralWorker
    from workers.security_worker import SecurityWorker
    from ui.terminal import NexusUI

    # Instantiate
    rag      = RAGEngine()
    neural   = NeuralWorker()
    security = SecurityWorker()
    brain    = Brain(rag)
    ui       = NexusUI(brain, rag, neural, security)

    # Start WebSocket + HTTP server for 3D visualization
    from web.server import NexusWSServer, start_http
    ws_server = NexusWSServer(neural, security, brain)
    ws_server.start()
    vis_url = start_http(8766)

    # Boot in background
    threading.Thread(target=boot_sequence, args=(ui,), daemon=True).start()

    # Open 3D brain in browser
    threading.Timer(3.0, lambda: __import__('subprocess').Popen(
        ['xdg-open', vis_url], stdout=__import__('subprocess').DEVNULL,
        stderr=__import__('subprocess').DEVNULL
    )).start()

    # Run (blocks until quit)
    ui.run()


if __name__ == '__main__':
    main()

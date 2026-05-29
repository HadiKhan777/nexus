"""
NEXUS WebSocket Bridge — streams live state to the 3D brain visualization.
Pushes neural training, security, and AI thinking data at 10fps.
"""

import asyncio, json, threading, time
import http.server, socketserver, os
from pathlib import Path


# Simple async WebSocket server using stdlib only
class NexusWSServer:
    def __init__(self, neural, security, brain, port=8765):
        self.neural   = neural
        self.security = security
        self.brain    = brain
        self.port     = port
        self.clients  = set()
        self._thread  = None
        self._loop    = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import websockets
            asyncio.run(self._serve())
        except ImportError:
            pass  # websockets not available, 3D vis won't get live data

    async def _serve(self):
        import websockets
        async def handler(ws, path=None):
            self.clients.add(ws)
            try:
                async for msg in ws:
                    pass  # we only push, not receive
            except:
                pass
            finally:
                self.clients.discard(ws)

        async def broadcaster():
            while True:
                if self.clients:
                    state = self._get_state()
                    msg   = json.dumps(state)
                    dead  = set()
                    for ws in self.clients:
                        try:
                            await ws.send(msg)
                        except:
                            dead.add(ws)
                    self.clients -= dead
                await asyncio.sleep(0.1)  # 10fps

        async with websockets.serve(handler, 'localhost', self.port):
            await broadcaster()

    def _get_state(self):
        n = self.neural
        sec = self.security.get_status()
        return {
            'neural': {
                'epoch':    n.epoch,
                'max':      n.max_epoch,
                'loss':     round(n.loss, 4),
                'val_acc':  round(n.val_acc, 4),
                'lr':       n.lr,
                'status':   n.status,
                'layers':   n.layer_activations,
                'loss_hist': n.loss_history[-50:],
                'acc_hist':  n.acc_history[-50:],
            },
            'security': {
                'devices':   list(sec['devices'].keys()),
                'threat':    sec['threat_lvl'],
                'scan_pct':  sec['scan_pct'],
            },
            'brain': {
                'streaming':  self.brain.ai_streaming if hasattr(self.brain, 'ai_streaming') else False,
                'rag_docs':   self.brain.rag.indexed,
                'ollama_up':  self.brain.ollama.available,
            }
        }


def start_http(port=8766):
    """Serve the 3D visualization HTML over HTTP."""
    web_dir = Path(__file__).parent
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(web_dir), **kw)
        def log_message(self, *a): pass  # silence

    def _serve():
        with socketserver.TCPServer(('', port), Handler) as srv:
            srv.serve_forever()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    return f'http://localhost:{port}/brain_3d.html'

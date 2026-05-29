"""
NEXUS Terminal UI — full-screen ANSI cockpit.
Multi-panel: AI brain, neural training, security, tasks, code output.
Uses raw ANSI escape codes (same philosophy as Hadi's own tui project).
"""

import sys, os, time, threading, textwrap, math
from datetime import datetime


# ── ANSI ─────────────────────────────────────────────────────────────────────

ESC = '\x1b'

def mv(r, c):       return f'{ESC}[{r};{c}H'
def clr():          return f'{ESC}[2J{ESC}[H'
def hide():         return f'{ESC}[?25l'
def show():         return f'{ESC}[?25h'
def alt():          return f'{ESC}[?1049h'
def normal():       return f'{ESC}[?1049l'
def rst():          return f'{ESC}[0m'
def bold():         return f'{ESC}[1m'
def dim():          return f'{ESC}[2m'
def rgb(r,g,b):     return f'{ESC}[38;2;{r};{g};{b}m'
def bgrgb(r,g,b):   return f'{ESC}[48;2;{r};{g};{b}m'

# Brand palette
LIME    = lambda s: f'{rgb(200,255,0)}{s}{rst()}'
CYAN    = lambda s: f'{rgb(0,255,220)}{s}{rst()}'
PINK    = lambda s: f'{rgb(255,50,150)}{s}{rst()}'
ORANGE  = lambda s: f'{rgb(255,140,0)}{s}{rst()}'
PURPLE  = lambda s: f'{rgb(170,50,255)}{s}{rst()}'
RED     = lambda s: f'{rgb(255,60,60)}{s}{rst()}'
GREEN   = lambda s: f'{rgb(50,255,100)}{s}{rst()}'
DIM     = lambda s: f'{dim()}{s}{rst()}'
BOLD    = lambda s: f'{bold()}{s}{rst()}'

# Gradient text
def gradient(text, r1,g1,b1, r2,g2,b2):
    n = max(len(text)-1, 1)
    out = []
    for i, ch in enumerate(text):
        t = i / n
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        out.append(f'{rgb(r,g,b)}{ch}')
    return ''.join(out) + rst()


def bar(pct, w=20, full_col=(200,255,0), empty_col=(40,40,40)):
    filled = int(pct * w / 100)
    f = rgb(*full_col) + '█' * filled + rst()
    e = rgb(*empty_col) + '░' * (w - filled) + rst()
    return f + e


def sparkline(data, w=30):
    chars = '▁▂▃▄▅▆▇█'
    if not data: return ' ' * w
    window = data[-w:]
    mn, mx = min(window), max(window)
    rng = mx - mn or 1
    return ''.join(chars[min(7, int((v-mn)/rng*7.99))] for v in window)


def box_line(w, char='─'):
    return char * w


# ── Dimensions ────────────────────────────────────────────────────────────────

def term_size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except:
        return 120, 40


# ── Spinner ───────────────────────────────────────────────────────────────────

SPINNERS = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']


class NexusUI:
    def __init__(self, brain, rag, neural, security):
        self.brain    = brain
        self.rag      = rag
        self.neural   = neural
        self.security = security

        self.input_buf = ''
        self.messages  = []   # [(role, text)]
        self.tasks     = [
            {'name': 'Load Ollama brain',   'done': False, 'pct': 0},
            {'name': 'Index documents',     'done': False, 'pct': 0},
            {'name': 'Start neural trainer','done': False, 'pct': 0},
            {'name': 'Scan network',        'done': False, 'pct': 0},
            {'name': 'NEXUS online',        'done': False, 'pct': 0},
        ]
        self.code_output  = ''
        self.spin_idx     = 0
        self._buf         = []
        self._lock        = threading.Lock()
        self._running     = False
        self._render_lock = threading.Lock()
        self.ai_streaming = False
        self.current_resp = ''

    # ── Write helpers ─────────────────────────────────────────────────────────

    def w(self, *parts):
        self._buf.append(''.join(str(p) for p in parts))

    def flush(self):
        sys.stdout.write(''.join(self._buf))
        sys.stdout.flush()
        self._buf.clear()

    # ── Layout engine ─────────────────────────────────────────────────────────

    def render(self):
        with self._render_lock:
            cols, rows = term_size()
            self._buf.clear()
            self.w(mv(1,1))  # go home, no full clear (reduces flicker)
            self._draw_header(cols)
            self._draw_body(cols, rows)
            self._draw_footer(cols, rows)
            self.flush()
        self.spin_idx = (self.spin_idx + 1) % len(SPINNERS)

    def _draw_header(self, cols):
        t = datetime.now().strftime('%H:%M:%S')
        ollama_status = GREEN('●') if self.brain.ollama.available else DIM('○')
        docs = self.rag.indexed
        spin = rgb(200,255,0) + SPINNERS[self.spin_idx] + rst() if self.ai_streaming else ' '

        title = gradient('NEXUS', 200,255,0, 0,255,220)
        sub   = DIM('PERSONAL INTELLIGENCE SYSTEM')
        right = f'{spin} {ollama_status}{DIM(" OLLAMA")}  {DIM("DOCS:")} {LIME(str(docs))}  {DIM("TIME:")} {CYAN(t)}'

        # Strip ANSI for length calculation
        import re
        strip = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)
        right_len = len(strip(right))

        self.w(mv(1,1), bgrgb(5,5,10), rgb(200,255,0), bold(), ' NEXUS ', rst(),
               DIM(' // PERSONAL INTELLIGENCE SYSTEM'),
               mv(1, cols - right_len - 1), right, rst())
        self.w(mv(2,1), rgb(30,30,30), '─' * cols, rst())

    def _draw_body(self, cols, rows):
        body_rows = rows - 5  # header=2, footer=3
        left_w  = cols // 2
        right_w = cols - left_w - 1

        # Left column: AI chat + current response
        self._draw_chat(3, 1, left_w, body_rows)

        # Vertical divider
        for r in range(3, 3 + body_rows):
            self.w(mv(r, left_w + 1), DIM('│'))

        # Right column: split into 3 panels
        panel_h = body_rows // 3
        self._draw_neural(3,          left_w+2, right_w, panel_h)
        self._draw_security(3+panel_h, left_w+2, right_w, panel_h)
        self._draw_tasks(3+panel_h*2, left_w+2, right_w, body_rows - panel_h*2)

    def _draw_chat(self, row, col, w, h):
        self.w(mv(row, col), LIME('◈ AI BRAIN'), DIM(f'  ─── {"STREAMING" if self.ai_streaming else "READY"}'))
        self.w(mv(row+1, col), DIM('─' * (w-1)))

        # Messages
        available = h - 5  # lines for messages
        lines = []
        import re
        strip = lambda s: re.sub(r'\x1b\[[0-9;]*m','',s)

        for role, text in self.messages[-12:]:
            prefix = LIME('you › ') if role == 'user' else CYAN('nexus › ')
            wrapped = textwrap.wrap(text, w - 10)
            for i, line in enumerate(wrapped[:3]):
                if i == 0:
                    lines.append(f'{prefix}{line}')
                else:
                    lines.append(f'      {line}')

        # Current streaming response
        if self.current_resp:
            lines.append('')
            prefix = CYAN('nexus › ')
            for line in textwrap.wrap(self.current_resp, w - 10)[-4:]:
                lines.append(f'{prefix}{line}')

        # Display last N lines
        display = lines[-(available):]
        for i, line in enumerate(display):
            self.w(mv(row+2+i, col), ' ' * (w-1))  # clear line
            self.w(mv(row+2+i, col), line[:w*2])    # write (may have ANSI)

        # Clear remaining lines
        for i in range(len(display), available):
            self.w(mv(row+2+i, col), ' ' * (w-1))

        # Input prompt
        self.w(mv(row+h-2, col), DIM('─' * (w-1)))
        cursor = rgb(200,255,0) + '█' + rst() if not self.ai_streaming else ''
        inp_display = self.input_buf[-(w-12):]
        self.w(mv(row+h-1, col), LIME('▸ '), inp_display, cursor, ' ' * max(0, w - len(inp_display) - 4))

    def _draw_neural(self, row, col, w, h):
        n = self.neural
        spin = SPINNERS[self.spin_idx] if n.status == 'training' else ('✓' if n.status == 'done' else '○')
        status_col = LIME if n.status == 'training' else (GREEN if n.status == 'done' else DIM)

        self.w(mv(row, col), PURPLE('◈ NEURAL'), DIM(f'  {n.dataset.upper()}  '),
               status_col(spin + ' ' + n.status.upper()))
        self.w(mv(row+1, col), DIM('─' * (w-1)))

        # Metrics
        ep_pct = int(n.epoch / max(n.max_epoch,1) * 100)
        self.w(mv(row+2, col),
               DIM('epoch '), LIME(f'{n.epoch:3d}/{n.max_epoch}'), '  ',
               bar(ep_pct, 15, (170,50,255), (20,10,30)), f' {ep_pct:3d}%')

        loss_c  = (255,80,80)  if n.loss > 0.3  else (255,180,0) if n.loss > 0.05 else (50,255,100)
        acc_c   = (50,255,100) if n.val_acc > 0.9 else (255,180,0)
        self.w(mv(row+3, col),
               DIM('loss  '), rgb(*loss_c) + f'{n.loss:.4f}' + rst(), '   ',
               DIM('acc  '), rgb(*acc_c) + f'{n.val_acc:.4f}' + rst(), '   ',
               DIM('lr '), CYAN(f'{n.lr:.2e}'))

        # Layer activations
        self.w(mv(row+4, col), DIM('layers  '))
        for i, act in enumerate(n.layer_activations[:6]):
            bar_w = 4
            filled = int(act * bar_w)
            col_act = (int(50 + act*150), int(50 + act*200), int(act*255))
            self.w(rgb(*col_act) + '█'*filled + rst() + dim() + '░'*(bar_w-filled) + rst() + ' ')

        # Loss sparkline
        self.w(mv(row+5, col), DIM('loss  '), rgb(170,50,255))
        self.w(sparkline(n.loss_history, w-8))
        self.w(rst())
        # Acc sparkline
        if h > 6:
            self.w(mv(row+6, col), DIM('acc   '), rgb(50,255,100))
            self.w(sparkline(n.acc_history, w-8))
            self.w(rst())

    def _draw_security(self, row, col, w, h):
        sec = self.security.get_status()
        self.w(mv(row, col), RED('◈ SECURITY'), DIM(f'  THREAT: '),
               GREEN(sec['threat_lvl']) if sec['threat_lvl'] == 'LOW' else RED(sec['threat_lvl']))
        self.w(mv(row+1, col), DIM('─' * (w-1)))

        devices = list(sec['devices'].items())[:h-3]
        for i, (ip, info) in enumerate(devices):
            name = info.get('name', 'Unknown')[:16]
            threat = info.get('threat', '?')
            threat_col = GREEN if threat == 'SAFE' else (ORANGE if 'NO TOKEN' in threat else RED)
            alive = info.get('alive', True)
            dot = GREEN('●') if alive else DIM('○')
            self.w(mv(row+2+i, col),
                   dot, ' ',
                   CYAN(ip.ljust(15)), ' ',
                   DIM(name.ljust(16)), ' ',
                   threat_col(threat))

        # Last scan
        if sec['last_scan']:
            self.w(mv(row+h-1, col), DIM(f'last scan {sec["last_scan"]}  scan {sec["scan_pct"]}%'))

    def _draw_tasks(self, row, col, w, h):
        self.w(mv(row, col), ORANGE('◈ TASKS')),
        self.w(mv(row+1, col), DIM('─' * (w-1)))
        for i, task in enumerate(self.tasks[:h-3]):
            if task['done']:
                indicator = GREEN('✓')
                b = bar(100, 15, (50,255,100), (10,30,10))
            elif task['pct'] > 0:
                spin = rgb(255,140,0) + SPINNERS[self.spin_idx] + rst()
                indicator = spin
                b = bar(task['pct'], 15, (255,140,0), (30,20,5))
            else:
                indicator = DIM('○')
                b = bar(0, 15, (200,255,0), (30,30,30))
            name = task['name'][:w-22]
            self.w(mv(row+2+i, col), indicator, ' ', DIM(name.ljust(w-22)), ' ', b)

    def _draw_footer(self, cols, rows):
        self.w(mv(rows-2, 1), DIM('─' * cols))
        cmds = LIME('/think') + DIM('  ') + LIME('/code') + DIM('  ') + LIME('/train') + DIM('  ') + LIME('/scan') + DIM('  ') + LIME('/3d') + DIM('  ') + LIME('/clear') + DIM('  ') + LIME('/quit')
        self.w(mv(rows-1, 1), DIM('NEXUS › '), cmds, '  ', DIM(f'[{cols}×{rows}]'))

    # ── Input handling ────────────────────────────────────────────────────────

    def handle_key(self, key):
        if key in ('\r', '\n'):
            self._submit()
        elif key in ('\x7f', '\x08'):  # backspace
            self.input_buf = self.input_buf[:-1]
        elif key == '\x03':  # Ctrl+C
            return False
        elif key == '\x15':  # Ctrl+U — clear line
            self.input_buf = ''
        elif len(key) == 1 and ord(key) >= 32:
            self.input_buf += key
        return True

    def _submit(self):
        text = self.input_buf.strip()
        if not text:
            return
        self.input_buf = ''

        if text.startswith('/'):
            self._handle_command(text)
            return

        self.messages.append(('user', text))

        def stream_response():
            self.ai_streaming = True
            self.current_resp = ''
            def on_token(tok):
                self.current_resp += tok
            self.brain.think(text, on_token)
            self.messages.append(('nexus', self.current_resp))
            self.current_resp = ''
            self.ai_streaming = False

        threading.Thread(target=stream_response, daemon=True).start()

    def _handle_command(self, cmd):
        parts = cmd.split()
        c = parts[0].lower()
        if c == '/train':
            dataset = parts[1] if len(parts) > 1 else 'spiral'
            self.neural.stop()
            time.sleep(0.2)
            self.neural.start(dataset)
            self.messages.append(('nexus', f'Neural training started on {dataset} dataset.'))
        elif c == '/scan':
            threading.Thread(target=self.security._scan_subnet, daemon=True).start()
            self.messages.append(('nexus', 'Network scan initiated...'))
        elif c == '/clear':
            self.messages.clear()
        elif c == '/3d':
            import subprocess
            subprocess.Popen(['xdg-open', os.path.expanduser('~/portfolio/singularity/index.html')])
            self.messages.append(('nexus', 'Opening 3D visualization...'))
        elif c == '/quit' or c == '/exit':
            self._running = False
        elif c == '/help':
            self.messages.append(('nexus',
                '/train [dataset] — start neural training (spiral/moons/circles/xor)\n'
                '/scan — rescan network\n'
                '/code <desc> — generate and run code\n'
                '/3d — open 3D visualization\n'
                '/clear — clear chat\n'
                '/quit — exit NEXUS'))
        else:
            self.messages.append(('nexus', f'Unknown command: {cmd}. Try /help'))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Main event loop."""
        import termios, tty

        # Setup terminal
        sys.stdout.write(alt() + hide())
        sys.stdout.flush()

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        self._running = True

        try:
            tty.setraw(fd)

            # Render thread
            def render_loop():
                while self._running:
                    self.render()
                    time.sleep(1/15)  # 15fps

            render_thread = threading.Thread(target=render_loop, daemon=True)
            render_thread.start()

            # Input loop
            while self._running:
                try:
                    key = sys.stdin.read(1)
                    if not self.handle_key(key):
                        break
                except:
                    break

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write(show() + normal())
            sys.stdout.flush()
            print('\nNEXUS offline.')

    def update_task(self, idx, pct, done=False):
        if 0 <= idx < len(self.tasks):
            self.tasks[idx]['pct']  = pct
            self.tasks[idx]['done'] = done

    def add_message(self, role, text):
        self.messages.append((role, text))

"""
NEXUS Neural Worker — runs neuralkit training in background,
streams live weight/loss data for visualization.
"""

import sys, os, threading, time
import numpy as np

sys.path.insert(0, os.path.expanduser('~/neuralkit'))


class NeuralWorker:
    def __init__(self):
        self.running   = False
        self.epoch     = 0
        self.max_epoch = 100
        self.loss      = 1.0
        self.val_acc   = 0.0
        self.lr        = 3e-3
        self.loss_history = []
        self.acc_history  = []
        self.layer_activations = [0.5] * 6  # per-layer activity
        self._thread   = None
        self._stop     = threading.Event()
        self.dataset   = 'spiral'
        self.status    = 'idle'

    def start(self, dataset='spiral'):
        self.dataset = dataset
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        self.status = 'loading'
        try:
            from nn import Sequential, Dense, ReLU, BatchNorm1d, CrossEntropyLoss
            from optim import AdamW, CosineAnnealingLR
            from data import make_spiral, make_moons, make_circles, make_xor, train_val_split, normalize
        except ImportError:
            # Fallback: simulate training
            self._simulate()
            return

        self.status = 'training'

        datasets = {
            'spiral':  lambda: make_spiral(N=200, classes=3),
            'moons':   lambda: make_moons(N=400),
            'circles': lambda: make_circles(N=400),
            'xor':     lambda: make_xor(N=400),
        }
        X, y = datasets.get(self.dataset, datasets['spiral'])()
        X_tr, y_tr, X_val, y_val = train_val_split(X, y, val_ratio=0.2)
        X_tr, X_val = normalize(X_tr, X_val)

        n_classes = len(np.unique(y))
        model = Sequential(
            Dense(X_tr.shape[1], 64), BatchNorm1d(64), ReLU(),
            Dense(64, 64), BatchNorm1d(64), ReLU(),
            Dense(64, n_classes),
        )

        loss_fn   = CrossEntropyLoss()
        optimizer = AdamW(lr=3e-3, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=100)

        N = X_tr.shape[0]
        self.max_epoch = 100

        for epoch in range(1, 101):
            if self._stop.is_set():
                break
            model.train()
            idx = np.random.permutation(N)
            epoch_loss, steps = 0.0, 0

            for start in range(0, N, 32):
                xb = X_tr[idx[start:start+32]]
                yb = y_tr[idx[start:start+32]]
                logits = model(xb)
                loss, grad = loss_fn(logits, yb)
                epoch_loss += loss; steps += 1
                optimizer.zero_grad(model.parameters())
                model.backward(grad)
                optimizer.step(model.parameters())

            scheduler.step()

            model.eval()
            preds   = model(X_val).argmax(axis=1)
            val_acc = (preds == y_val).mean()

            self.epoch   = epoch
            self.loss    = epoch_loss / steps
            self.val_acc = val_acc
            self.lr      = optimizer.lr
            self.loss_history.append(self.loss)
            self.acc_history.append(val_acc)

            # Update per-layer activations for visualization
            for i, layer in enumerate(model.layers):
                if hasattr(layer, 'W'):
                    # Use weight norm as a proxy for "activity"
                    activity = float(np.linalg.norm(layer.W)) / (layer.W.size ** 0.5)
                    self.layer_activations[i % 6] = min(1.0, activity)

            time.sleep(0.05)  # pace the training loop

        self.status = 'done' if not self._stop.is_set() else 'stopped'

    def _simulate(self):
        """Simulate training when neuralkit import fails."""
        self.status = 'training'
        for epoch in range(1, 101):
            if self._stop.is_set():
                break
            t = epoch / 100
            self.epoch   = epoch
            self.loss    = 0.9 * np.exp(-3 * t) + 0.02 + np.random.randn() * 0.005
            self.val_acc = 1 - 0.7 * np.exp(-4 * t) + np.random.randn() * 0.005
            self.val_acc = max(0, min(1, self.val_acc))
            self.lr      = 3e-3 * (1 + np.cos(np.pi * t)) / 2
            self.loss_history.append(self.loss)
            self.acc_history.append(self.val_acc)
            for i in range(6):
                self.layer_activations[i] = 0.3 + 0.7 * t + np.random.rand() * 0.1
            time.sleep(0.08)
        self.status = 'done'

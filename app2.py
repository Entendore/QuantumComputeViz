#!/usr/bin/env python3
"""
Quantum Computer Simulator — PySide6 Application
Build quantum circuits visually and simulate them in real time.
"""

import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QGroupBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QComboBox, QScrollArea, QSizePolicy, QDoubleSpinBox,
    QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QRectF, QSize, QPoint, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QPainterPath, QLinearGradient
)

# ─── Colour Palette ────────────────────────────────────────────────
DARK_BG       = "#1a1a2e"
DARK_SURFACE  = "#16213e"
DARK_SURFACE2 = "#0f3460"
ACCENT        = "#7c3aed"
TEXT_COLOR     = "#e2e8f0"
TEXT_DIM       = "#94a3b8"
WIRE_COLOR     = "#475569"

GATE_COLORS = {
    'H': '#7c3aed', 'X': '#ef4444', 'Y': '#f97316', 'Z': '#3b82f6',
    'S': '#06b6d4', 'T': '#14b8a6', 'RX': '#8b5cf6', 'RY': '#ec4899',
    'RZ': '#6366f1', 'CNOT': '#10b981', 'CZ': '#059669',
    'SWAP': '#f59e0b', 'Toffoli': '#84cc16', 'M': '#f59e0b',
}

# ─── Gate Matrices ─────────────────────────────────────────────────
GATE_MATRICES = {
    'H': np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
    'X': np.array([[0, 1], [1, 0]], dtype=complex),
    'Y': np.array([[0, -1j], [1j, 0]], dtype=complex),
    'Z': np.array([[1, 0], [0, -1]], dtype=complex),
    'S': np.array([[1, 0], [0, 1j]], dtype=complex),
    'T': np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    'CNOT': np.array([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]], dtype=complex),
    'CZ':   np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,-1]], dtype=complex),
    'SWAP': np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,1,0]], dtype=complex),
    'Toffoli': np.array([
        [1,0,0,0,0,0,0,0],[0,1,0,0,0,0,0,0],[0,0,1,0,0,0,0,0],
        [0,0,0,1,0,0,0,0],[0,0,0,0,1,0,0,0],[0,0,0,0,0,1,0,0],
        [0,0,0,0,0,0,0,1],[0,0,0,0,0,0,1,0]], dtype=complex),
}

GATE_QUBIT_COUNT = {
    'I': 1, 'H': 1, 'X': 1, 'Y': 1, 'Z': 1, 'S': 1, 'T': 1,
    'RX': 1, 'RY': 1, 'RZ': 1, 'CNOT': 2, 'CZ': 2, 'SWAP': 2,
    'Toffoli': 3, 'M': 1,
}

# ─── Circuit Presets ───────────────────────────────────────────────
PRESETS = {
    "Bell State (Max Entangle)": {
        "qubits": 2,
        "gates": [("H", [0], 0, {}), ("CNOT", [0, 1], 1, {})]
    },
    "GHZ State (3-Qubit)": {
        "qubits": 3,
        "gates": [("H", [0], 0, {}), ("CNOT", [0, 1], 1, {}), ("CNOT", [0, 2], 2, {})]
    },
    "Full Superposition": {
        "qubits": 2,
        "gates": [("H", [0], 0, {}), ("H", [1], 0, {})]
    },
    "X-Gate Bit Flip": {
        "qubits": 1,
        "gates": [("X", [0], 0, {})]
    },
    "Phase Kickback (H-Z-H)": {
        "qubits": 1,
        "gates": [("H", [0], 0, {}), ("Z", [0], 1, {}), ("H", [0], 2, {})]
    },
    "|+i⟩ State (H-S)": {
        "qubits": 1,
        "gates": [("H", [0], 0, {}), ("S", [0], 1, {})]
    },
    "RX Gate (θ=π/2)": {
        "qubits": 1,
        "gates": [("RX", [0], 0, {"theta": np.pi/2})]
    },
    "SWAP Two Qubits": {
        "qubits": 2,
        "gates": [("X", [0], 0, {}), ("SWAP", [0, 1], 1, {})]
    },
    "CZ (Controlled-Z)": {
        "qubits": 2,
        "gates": [("H", [0], 0, {}), ("H", [1], 0, {}), ("CZ", [0, 1], 1, {})]
    },
    "Bernstein-Vazirani (s=10)": {
        "qubits": 3,
        "gates": [("H", [0], 0, {}), ("H", [1], 0, {}), ("X", [2], 0, {}), ("H", [2], 1, {}), ("CNOT", [1, 2], 2, {}), ("H", [0], 3, {}), ("H", [1], 3, {})]
    },
    "Grover's Search (2-Qubit)": {
        "qubits": 2,
        "gates": [("H", [0], 0, {}), ("H", [1], 0, {}), ("CZ", [0, 1], 1, {}), ("H", [0], 2, {}), ("H", [1], 2, {}), ("X", [0], 3, {}), ("X", [1], 3, {}), ("CZ", [0, 1], 4, {}), ("X", [0], 5, {}), ("X", [1], 5, {}), ("H", [0], 6, {}), ("H", [1], 6, {})]
    }
}


# ═══════════════════════════════════════════════════════════════════
#  Quantum Simulator
# ═══════════════════════════════════════════════════════════════════
class QuantumSimulator:
    """State-vector simulator supporting up to ~10 qubits."""

    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.reset()

    def reset(self):
        self.state_vector = np.zeros(2 ** self.num_qubits, dtype=complex)
        self.state_vector[0] = 1.0

    # ── gate application ────────────────────────────────────────
    def apply_gate(self, gate_name: str, target_qubits: list, params=None):
        if gate_name == 'M':
            return
        if gate_name in ('RX', 'RY', 'RZ'):
            theta = (params or {}).get('theta', 0.0)
            gate = self._rotation_matrix(gate_name, theta)
        else:
            gate = GATE_MATRICES[gate_name]
        if len(target_qubits) == 1:
            self._apply_single(gate, target_qubits[0])
        else:
            self._apply_multi(gate, target_qubits)

    @staticmethod
    def _rotation_matrix(kind, theta):
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        if kind == 'RX':
            return np.array([[c, -1j*s], [-1j*s, c]], dtype=complex)
        if kind == 'RY':
            return np.array([[c, -s], [s, c]], dtype=complex)
        return np.array([[np.exp(-1j*theta/2), 0],
                         [0, np.exp(1j*theta/2)]], dtype=complex)

    def _apply_single(self, gate, qubit):
        n = self.num_qubits
        op = np.array([[1.0 + 0j]])
        for i in range(n):
            op = np.kron(op, gate if i == n - 1 - qubit else np.eye(2, dtype=complex))
        self.state_vector = op @ self.state_vector

    def _apply_multi(self, gate, qubit_indices):
        self.state_vector = self._expand_gate(gate, qubit_indices) @ self.state_vector

    def _expand_gate(self, gate, qubit_indices):
        n, k = self.num_qubits, len(qubit_indices)
        dim, gdim = 2 ** n, 2 ** k
        target_set = set(qubit_indices)
        non_target = [q for q in range(n) if q not in target_set]
        nnt = len(non_target)
        M = np.zeros((dim, dim), dtype=complex)
        for nt in range(1 << nnt):
            base = 0
            for idx, q in enumerate(non_target):
                if (nt >> idx) & 1:
                    base |= 1 << q
            for ti in range(gdim):
                i = base
                for idx, q in enumerate(qubit_indices):
                    if (ti >> (k - 1 - idx)) & 1:
                        i |= 1 << q
                for tj in range(gdim):
                    j = base
                    for idx, q in enumerate(qubit_indices):
                        if (tj >> (k - 1 - idx)) & 1:
                            j |= 1 << q
                    M[i, j] = gate[ti, tj]
        return M

    # ── measurement ─────────────────────────────────────────────
    def measure_qubit(self, qubit):
        p0 = sum(abs(self.state_vector[i]) ** 2
                 for i in range(1 << self.num_qubits) if not (i >> qubit) & 1)
        result = 0 if np.random.random() < p0 else 1
        new = np.zeros_like(self.state_vector)
        norm = 0.0
        for i in range(1 << self.num_qubits):
            if (i >> qubit) & 1 == result:
                new[i] = self.state_vector[i]
                norm += abs(self.state_vector[i]) ** 2
        self.state_vector = new / np.sqrt(norm)
        return result

    def measure_all(self):
        probs = self.get_probabilities()
        idx = np.random.choice(len(probs), p=probs)
        bits = [(idx >> q) & 1 for q in range(self.num_qubits)]
        self.state_vector = np.zeros_like(self.state_vector)
        self.state_vector[idx] = 1.0
        return list(reversed(bits))

    # ── observables ─────────────────────────────────────────────
    def get_probabilities(self):
        p = np.abs(self.state_vector) ** 2
        return p / p.sum()

    def reduced_density_matrix(self, qubit):
        n = self.num_qubits
        rho = np.zeros((2, 2), dtype=complex)
        for a in range(2):
            for b in range(2):
                for i in range(1 << n):
                    if (i >> qubit) & 1 != a:
                        continue
                    rho[a, b] += (np.conj(self.state_vector[i])
                                  * self.state_vector[i ^ ((a ^ b) << qubit)])
        return rho

    def bloch_vector(self, qubit):
        rho = self.reduced_density_matrix(qubit)
        return np.array([2 * rho[0, 1].real,
                         -2 * rho[0, 1].imag,
                         (rho[0, 0] - rho[1, 1]).real])


# ═══════════════════════════════════════════════════════════════════
#  Circuit Model
# ═══════════════════════════════════════════════════════════════════
class CircuitGate:
    def __init__(self, gate_type, qubits, column, params=None):
        self.gate_type = gate_type
        self.qubits = list(qubits)
        self.column = column
        self.params = params or {}


class CircuitModel:
    def __init__(self, num_qubits=3):
        self.num_qubits = num_qubits
        self.num_columns = 10
        self.gates: list[CircuitGate] = []

    def add_gate(self, gate_type, qubits, column, params=None) -> bool:
        for g in self.gates:
            if g.column == column and any(q in g.qubits for q in qubits):
                return False
        self.gates.append(CircuitGate(gate_type, qubits, column, params))
        return True

    def remove_gate_at(self, qubit, column):
        self.gates = [g for g in self.gates
                      if not (g.column == column and qubit in g.qubits)]

    def get_gate_at(self, qubit, column):
        for g in self.gates:
            if g.column == column and qubit in g.qubits:
                return g
        return None

    def get_gates_in_column(self, col):
        return [g for g in self.gates if g.column == col]

    def clear(self):
        self.gates.clear()

    def execute(self, sim: QuantumSimulator):
        sim.num_qubits = self.num_qubits
        sim.reset()
        for col in range(self.num_columns):
            for gate in self.get_gates_in_column(col):
                if gate.gate_type == 'M':
                    for q in gate.qubits:
                        sim.measure_qubit(q)
                else:
                    sim.apply_gate(gate.gate_type, gate.qubits, gate.params)

    def run_shots(self, num_shots=1024) -> dict:
        sim = QuantumSimulator(self.num_qubits)
        for col in range(self.num_columns):
            for gate in self.get_gates_in_column(col):
                if gate.gate_type != 'M':
                    sim.apply_gate(gate.gate_type, gate.qubits, gate.params)
        probs = sim.get_probabilities()
        indices = np.random.choice(len(probs), size=num_shots, p=probs)
        results = {}
        for idx in indices:
            bs = format(idx, f'0{self.num_qubits}b')
            results[bs] = results.get(bs, 0) + 1
        return results


# ═══════════════════════════════════════════════════════════════════
#  Circuit Widget  (visual, interactive)
# ═══════════════════════════════════════════════════════════════════
class CircuitWidget(QWidget):
    circuit_changed = Signal()

    CW, CH = 70, 55
    ML, MT = 70, 35
    GW, GH = 50, 38

    def __init__(self, model: CircuitModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.selected_gate = None
        self.selected_params = None
        self.placing_qubits = []
        self.placing_column = None
        self.hover_cell = None
        self.gate_buttons = []
        self.setMinimumSize(400, 250)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_selected_gate(self, gate_type, params=None):
        self.selected_gate = gate_type
        self.selected_params = params
        self.placing_qubits.clear()
        self.placing_column = None
        self.update()

    def _cell_at(self, pos):
        c = int((pos.x() - self.ML) / self.CW)
        q = int((pos.y() - self.MT) / self.CH)
        if 0 <= q < self.model.num_qubits and 0 <= c < self.model.num_columns:
            return q, c
        return None

    def mousePressEvent(self, ev):
        cell = self._cell_at(ev.position())  # FIXED: Use ev.position() instead of ev.pos()
        if cell is None:
            return
        q, c = cell
        if ev.button() == Qt.RightButton:
            self.model.remove_gate_at(q, c)
            self.circuit_changed.emit()
            self.update()
            return
        if ev.button() == Qt.LeftButton and self.selected_gate:
            nq = GATE_QUBIT_COUNT.get(self.selected_gate, 1)
            if nq == 1:
                p = self.selected_params
                if self.selected_gate in ('RX', 'RY', 'RZ'):
                    # FIXED: Safely find the MainWindow to get theta_spin value
                    main_win = self.parent()
                    while main_win and not isinstance(main_win, MainWindow):
                        main_win = main_win.parent()
                    if main_win:
                        p = {'theta': main_win.theta_spin.value()}
                ok = self.model.add_gate(self.selected_gate, [q], c, p)
                if ok:
                    self.circuit_changed.emit()
                    self.update()
            else:
                if not self.placing_qubits:
                    self.placing_column = c
                self.placing_qubits.append(q)
                if len(self.placing_qubits) == nq:
                    ok = self.model.add_gate(self.selected_gate,
                                             self.placing_qubits,
                                             self.placing_column)
                    self.placing_qubits.clear()
                    self.placing_column = None
                    if ok:
                        self.circuit_changed.emit()
                    self.update()
                else:
                    self.update()

    def mouseMoveEvent(self, ev):
        cell = self._cell_at(ev.position())  # FIXED: Use ev.position() instead of ev.pos()
        if cell != self.hover_cell:
            self.hover_cell = cell
            self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DARK_BG))
        n, nc = self.model.num_qubits, self.model.num_columns
        
        # Draw qubit wires
        p.setPen(QPen(QColor(WIRE_COLOR), 2))
        for q in range(n):
            y = self.MT + q * self.CH + self.CH // 2
            p.drawLine(self.ML, y, self.ML + nc * self.CW, y)
            p.setPen(QPen(QColor(TEXT_COLOR)))
            p.setFont(QFont("Consolas", 11, QFont.Bold))
            p.drawText(5, y + 5, f"|q{q}⟩")
            p.setPen(QPen(QColor(WIRE_COLOR), 2))

        # Draw grid hover highlight
        if self.hover_cell:
            hq, hc = self.hover_cell
            if self.selected_gate:
                cx = self.ML + hc * self.CW + self.CW // 2
                cy = self.MT + hq * self.CH + self.CH // 2
                p.setBrush(QBrush(QColor(255, 255, 255, 20)))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(cx - self.GW//2, cy - self.GH//2, self.GW, self.GH, 5, 5)

        # Draw placed gates
        for gate in self.model.gates:
            self._draw_gate(p, gate)

        p.end()

    def _draw_gate(self, p: QPainter, gate: CircuitGate):
        color = QColor(GATE_COLORS.get(gate.gate_type, '#888888'))
        min_q, max_q = min(gate.qubits), max(gate.qubits)
        
        cx = self.ML + gate.column * self.CW + self.CW // 2
        cy_top = self.MT + min_q * self.CH + self.CH // 2
        cy_bot = self.MT + max_q * self.CH + self.CH // 2

        # Draw connecting lines for multi-qubit gates
        if len(gate.qubits) > 1:
            p.setPen(QPen(color, 2))
            p.drawLine(cx, cy_top, cx, cy_bot)

        # Draw the gate nodes
        for q in gate.qubits:
            cy = self.MT + q * self.CH + self.CH // 2
            rect = QRectF(cx - self.GW/2, cy - self.GH/2, self.GW, self.GH)

            if gate.gate_type == 'M':
                # Measurement symbol
                p.setPen(QPen(color, 2))
                p.setBrush(QBrush(QColor(DARK_BG)))
                p.drawEllipse(rect)
                p.drawArc(QRectF(rect.x()+5, rect.y()+2, rect.width()-10, rect.height()-4), 30*16, 150*16)
                p.drawLine(rect.center().toPoint() + QPoint(0, -2), rect.bottomRight().toPoint() - QPoint(8, 8))
            elif gate.gate_type == 'CNOT' and q == max_q:
                # Target qubit of CNOT
                p.setPen(QPen(color, 2))
                p.setBrush(QBrush(QColor(DARK_BG)))
                p.drawEllipse(rect)
                p.drawLine(int(cx-15), int(cy), int(cx+15), int(cy))
                p.drawLine(int(cx), int(cy-15), int(cx), int(cy+15))
            elif gate.gate_type == 'CNOT' and q == min_q:
                # Control qubit of CNOT
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(color))
                p.drawEllipse(QPointF(cx, cy), 6, 6)  # FIXED: QPointF(cx, cy) instead of two QPoints
            elif gate.gate_type == 'SWAP':
                # SWAP symbol
                p.setPen(QPen(color, 2))
                p.drawLine(int(cx-10), int(cy-10), int(cx+10), int(cy+10))
                p.drawLine(int(cx-10), int(cy+10), int(cx+10), int(cy-10))
            else:
                # Standard box gate
                p.setPen(QPen(color, 2))
                p.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 40)))
                p.drawRoundedRect(rect, 5, 5)
                
                p.setPen(QPen(QColor(TEXT_COLOR)))
                p.setFont(QFont("Consolas", 10, QFont.Bold))
                label = gate.gate_type
                if gate.gate_type in ('RX', 'RY', 'RZ'):
                    theta = gate.params.get('theta', 0)
                    label = f"{gate.gate_type}({theta/np.pi:.1f}π)"
                p.drawText(rect, Qt.AlignCenter, label)


# ═══════════════════════════════════════════════════════════════════
#  Bloch Sphere Widget
# ═══════════════════════════════════════════════════════════════════
class BlochSphereWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bx, self.by, self.bz = 0.0, 0.0, 0.0
        self.setMinimumSize(250, 250)

    def set_vector(self, x, y, z):
        self.bx, self.by, self.bz = x, y, z
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DARK_BG))

        cx, cy = self.width() // 2, self.height() // 2
        r = min(cx, cy) - 30

        # Isometric-like projection functions
        def proj(x3, y3, z3):
            px = cx + (x3 - y3) * r * 0.7
            py = cy - z3 * r + (x3 + y3) * r * 0.2
            return int(px), int(py)

        # Draw sphere outline
        p.setPen(QPen(QColor(WIRE_COLOR), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Draw axes
        p.setPen(QPen(QColor(TEXT_DIM), 1, Qt.DashLine))
        origin = proj(0, 0, 0)
        for vec, label, color in [((1,0,0), "X", "#ef4444"), ((0,1,0), "Y", "#22c55e"), ((0,0,1), "Z", "#3b82f6")]:
            end = proj(*vec)
            p.setPen(QPen(QColor(color), 1, Qt.DashLine))
            p.drawLine(origin[0], origin[1], end[0], end[1])
            p.setPen(QPen(QColor(color), 10))
            p.drawPoint(end[0], end[1])
            p.setFont(QFont("Arial", 9, QFont.Bold))
            p.drawText(end[0] + 5, end[1] - 5, label)

        # Draw vector
        vx, vy = proj(self.bx, self.by, self.bz)
        p.setPen(QPen(QColor(ACCENT), 3))
        p.drawLine(origin[0], origin[1], vx, vy)
        p.setBrush(QBrush(QColor(ACCENT)))
        p.drawEllipse(QPointF(vx, vy), 5, 5)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Histogram Widget
# ═══════════════════════════════════════════════════════════════════
class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.setMinimumSize(300, 200)

    def set_data(self, data: dict):
        self.data = data
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(DARK_BG))
        
        if not self.data:
            p.setPen(QColor(TEXT_DIM))
            p.drawText(self.rect(), Qt.AlignCenter, "Run shots to see measurement results")
            p.end()
            return

        p.setRenderHint(QPainter.Antialiasing)
        max_val = max(self.data.values())
        if max_val == 0: max_val = 1
        
        margin_l, margin_b = 50, 30
        w = self.width() - margin_l - 20
        h = self.height() - margin_b - 20
        n = len(self.data)
        bar_w = min(40, w // max(n, 1))

        # Axes
        p.setPen(QPen(QColor(WIRE_COLOR), 2))
        p.drawLine(margin_l, 20, margin_l, self.height() - margin_b)
        p.drawLine(margin_l, self.height() - margin_b, self.width() - 20, self.height() - margin_b)

        # Bars
        x = margin_l + 10
        for key in sorted(self.data.keys()):
            val = self.data[key]
            bar_h = (val / max_val) * h
            
            p.setPen(Qt.NoPen)
            grad = QLinearGradient(x, self.height() - margin_b - bar_h, x, self.height() - margin_b)
            grad.setColorAt(0, QColor(ACCENT))
            grad.setColorAt(1, QColor(DARK_SURFACE2))
            p.setBrush(QBrush(grad))
            
            p.drawRect(x, int(self.height() - margin_b - bar_h), bar_w, int(bar_h))
            
            p.setPen(QColor(TEXT_COLOR))
            p.setFont(QFont("Consolas", 8))
            p.drawText(x, self.height() - margin_b + 15, key)
            
            p.setPen(QColor(TEXT_DIM))
            p.drawText(x, int(self.height() - margin_b - bar_h - 15), str(val))
            x += bar_w + 5

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Computer Simulator")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_COLOR};")

        # Core Models
        self.circuit = CircuitModel(num_qubits=3)
        self.simulator = QuantumSimulator(self.circuit.num_qubits)

        # UI Setup
        self._build_ui()
        self._connect_signals()
        self.update_results()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(10)

        # --- Left Panel (Controls) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(220)
        left_panel.setStyleSheet(f"background-color: {DARK_SURFACE}; border-radius: 10px;")

        # Preset Examples
        preset_box = QGroupBox("Presets")
        preset_layout = QVBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()))
        preset_layout.addWidget(self.preset_combo)

        self.load_preset_btn = QPushButton("Load Preset")
        self.load_preset_btn.setStyleSheet(f"background-color: {DARK_SURFACE2}; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        preset_layout.addWidget(self.load_preset_btn)
        preset_box.setLayout(preset_layout)
        left_layout.addWidget(preset_box)

        # Qubit Count
        qbox = QGroupBox("System")
        qbox_layout = QHBoxLayout()
        qbox_layout.addWidget(QLabel("Qubits:"))
        self.qubit_spin = QSpinBox()
        self.qubit_spin.setRange(1, 8)
        self.qubit_spin.setValue(3)
        qbox_layout.addWidget(self.qubit_spin)
        qbox.setLayout(qbox_layout)
        left_layout.addWidget(qbox)

        # Gate Palette
        gbox = QGroupBox("Gates")
        gbox_layout = QVBoxLayout()
        
        self.gate_buttons = []
        gates = [
            ('H', 'H'), ('X', 'X'), ('Y', 'Y'), ('Z', 'Z'),
            ('S', 'S'), ('T', 'T'), 
            ('RX', 'RX'), ('RY', 'RY'), ('RZ', 'RZ'),
            ('CNOT', 'CNOT'), ('CZ', 'CZ'), ('SWAP', 'SWAP'),
            ('Measure', 'M')
        ]
        
        grid = QGridLayout()
        for i, (label, gtype) in enumerate(gates):
            btn = QPushButton(label)
            color = GATE_COLORS.get(gtype, '#888')
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}; color: white; 
                    border-radius: 5px; padding: 8px; font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: white; color: {color};
                    border: 2px solid {color};
                }}
            """)
            btn.setCheckable(True)
            btn.setProperty("gate_type", gtype)
            grid.addWidget(btn, i // 3, i % 3)
            self.gate_buttons.append(btn)
            
        gbox_layout.addLayout(grid)

        # Rotation Parameter
        self.theta_widget = QWidget()
        theta_layout = QHBoxLayout(self.theta_widget)
        theta_layout.setContentsMargins(0,0,0,0)
        theta_layout.addWidget(QLabel("θ:"))
        self.theta_spin = QDoubleSpinBox()
        self.theta_spin.setRange(-10.0, 10.0)
        self.theta_spin.setSingleStep(0.25)
        self.theta_spin.setValue(1.0)
        self.theta_spin.setSuffix(" π rad")
        theta_layout.addWidget(self.theta_spin)
        self.theta_widget.hide()
        gbox_layout.addWidget(self.theta_widget)
        
        gbox.setLayout(gbox_layout)
        left_layout.addWidget(gbox)

        # Simulation Controls
        sbox = QGroupBox("Simulation")
        sbox_layout = QVBoxLayout()
        
        self.run_btn = QPushButton("▶ Run State Vector")
        self.run_btn.setStyleSheet(f"background-color: {ACCENT}; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        sbox_layout.addWidget(self.run_btn)

        sbox_layout.addWidget(QLabel("Shots for Measurement:"))
        self.shots_spin = QSpinBox()
        self.shots_spin.setRange(1, 100000)
        self.shots_spin.setValue(1024)
        self.shots_spin.setSingleStep(256)
        sbox_layout.addWidget(self.shots_spin)

        self.shots_btn = QPushButton("⚡ Run Shots")
        self.shots_btn.setStyleSheet(f"background-color: {DARK_SURFACE2}; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        sbox_layout.addWidget(self.shots_btn)

        self.clear_btn = QPushButton("🗑 Clear Circuit")
        self.clear_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        sbox_layout.addWidget(self.clear_btn)
        
        sbox.setLayout(sbox_layout)
        left_layout.addWidget(sbox)
        left_layout.addStretch()

        # --- Right Panel (Circuit & Results) ---
        right_splitter = QSplitter(Qt.Vertical)

        # Circuit View
        circuit_container = QWidget()
        c_layout = QVBoxLayout(circuit_container)
        c_layout.setContentsMargins(0,0,0,0)
        self.circuit_widget = CircuitWidget(self.circuit)
        scroll = QScrollArea()
        scroll.setWidget(self.circuit_widget)
        scroll.setWidgetResizable(True)
        c_layout.addWidget(QLabel("Quantum Circuit (Left Click: Place Gate | Right Click: Remove Gate)"))
        c_layout.addWidget(scroll)

        # Results View
        results_tabs = QTabWidget()
        results_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {WIRE_COLOR}; background: {DARK_BG}; }}
            QTabBar::tab {{ background: {DARK_SURFACE}; color: {TEXT_COLOR}; padding: 8px; border-top-left-radius: 4px; border-top-right-radius: 4px;}}
            QTabBar::tab:selected {{ background: {ACCENT}; }}
        """)

        # State Vector Tab
        self.state_table = QTableWidget()
        self.state_table.setColumnCount(4)
        self.state_table.setHorizontalHeaderLabels(["Basis", "Amplitude (Re, Im)", "Probability", "Phase"])
        self.state_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.state_table.setEditTriggers(QTableWidget.NoEditTriggers)
        results_tabs.addTab(self.state_table, "State Vector")

        # Bloch Sphere Tab
        bloch_container = QWidget()
        bloch_layout = QHBoxLayout(bloch_container)
        self.bloch_widget = BlochSphereWidget()
        self.bloch_qubit_select = QSpinBox()
        self.bloch_qubit_select.setRange(0, self.circuit.num_qubits - 1)
        bloch_layout.addWidget(self.bloch_widget)
        bloch_layout.addWidget(QLabel("View Qubit:"))
        bloch_layout.addWidget(self.bloch_qubit_select)
        bloch_layout.addStretch()
        results_tabs.addTab(bloch_container, "Bloch Sphere")

        # Histogram Tab
        self.histogram_widget = HistogramWidget()
        results_tabs.addTab(self.histogram_widget, "Measurement Histogram")

        right_splitter.addWidget(circuit_container)
        right_splitter.addWidget(results_tabs)
        right_splitter.setSizes([400, 400])

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_splitter, 1)

    def _connect_signals(self):
        self.qubit_spin.valueChanged.connect(self._on_qubits_changed)
        self.run_btn.clicked.connect(self._on_run_simulation)
        self.shots_btn.clicked.connect(self._on_run_shots)
        self.clear_btn.clicked.connect(self._on_clear)
        self.circuit_widget.circuit_changed.connect(self._on_run_simulation)
        self.bloch_qubit_select.valueChanged.connect(self.update_results)

        for btn in self.gate_buttons:
            btn.clicked.connect(self._on_gate_selected)
            
        self.load_preset_btn.clicked.connect(lambda: self._load_preset(self.preset_combo.currentText()))

    def _load_preset(self, name):
        if name not in PRESETS:
            return
        
        data = PRESETS[name]
        
        # Deselect any active gate placement
        self.circuit_widget.set_selected_gate(None)
        for btn in self.gate_buttons:
            btn.setChecked(False)
        self.theta_widget.hide()
        
        # Update qubit count (this auto-clears the circuit via _on_qubits_changed)
        self.qubit_spin.setValue(data["qubits"])
        
        # Add gates from preset
        for gate_info in data["gates"]:
            gtype, qubits, col = gate_info[0], gate_info[1], gate_info[2]
            params = gate_info[3] if len(gate_info) > 3 else {}
            self.circuit.add_gate(gtype, qubits, col, params)
            
        # Refresh UI and simulate
        self.circuit_widget.update()
        self._on_run_simulation()

    def _on_qubits_changed(self, val):
        self.circuit.num_qubits = val
        self.circuit.gates.clear()
        self.bloch_qubit_select.setRange(0, val - 1)
        self.circuit_widget.update()
        self._on_run_simulation()

    def _on_gate_selected(self):
        # Exclusive check logic for gate buttons
        sender = self.sender()
        for btn in self.gate_buttons:
            if btn is not sender:
                btn.setChecked(False)
        
        if sender.isChecked():
            gtype = sender.property("gate_type")
            self.circuit_widget.set_selected_gate(gtype)
            if gtype in ('RX', 'RY', 'RZ'):
                self.theta_widget.show()
            else:
                self.theta_widget.hide()
        else:
            self.circuit_widget.set_selected_gate(None)
            self.theta_widget.hide()

    def _on_run_simulation(self):
        self.circuit.execute(self.simulator)
        self.update_results()

    def _on_run_shots(self):
        shots = self.shots_spin.value()
        results = self.circuit.run_shots(shots)
        self.histogram_widget.set_data(results)

    def _on_clear(self):
        self.circuit.clear()
        self.circuit_widget.update()
        self._on_run_simulation()

    def update_results(self):
        n = self.simulator.num_qubits
        probs = self.simulator.get_probabilities()
        state = self.simulator.state_vector

        # Update State Table
        self.state_table.setRowCount(1 << n)
        for i in range(1 << n):
            basis = f"|{i:0{n}b}⟩"
            amp = state[i]
            prob = probs[i]
            phase = np.angle(amp)

            self.state_table.setItem(i, 0, QTableWidgetItem(basis))
            
            if prob > 1e-6:
                amp_str = f"{amp.real:.4f} + {amp.imag:.4f}i"
            else:
                amp_str = "0"
            self.state_table.setItem(i, 1, QTableWidgetItem(amp_str))
            
            prob_item = QTableWidgetItem(f"{prob*100:.2f}%")
            if prob > 0.5:
                prob_item.setForeground(QColor("#22c55e"))
            elif prob > 1e-6:
                prob_item.setForeground(QColor(TEXT_COLOR))
            else:
                prob_item.setForeground(QColor(TEXT_DIM))
            self.state_table.setItem(i, 2, prob_item)
            
            self.state_table.setItem(i, 3, QTableWidgetItem(f"{phase:.4f} rad"))

        # Update Bloch Sphere
        q = self.bloch_qubit_select.value()
        if q < n:
            bx, by, bz = self.simulator.bloch_vector(q)
            self.bloch_widget.set_vector(bx, by, bz)


# ═══════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set deep link style fallback just in case
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
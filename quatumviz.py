#!/usr/bin/env python3
"""
Quantum Computer Simulator — PySide6 + NumPy (Ultimate Pro Edition)
================================================================
A complete quantum computing development environment combining:
  • SQASM text-based programming IDE with 79 academic example programs
  • Visual click-to-place circuit builder with color-coded gate palette
  • Interactive Angle Slider for real-time rotation gate tuning
  • 3D Interactive Bloch Sphere (drag to rotate, double-click to reset)
  • Real-time state vector table, density matrix, entanglement entropy,
    observables, and measurement histogram
  • Full circuit Unitary matrix calculation
  • Playback controls (Play/Pause/Stop) with speed slider
  • Noise simulation, step-through execution, undo history
  • QASM/PNG export, SQASM generation, gate matrix inspector
  • Supports up to 12 qubits
"""

import sys, math, copy, re
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QPlainTextEdit, QScrollArea, QSplitter,
    QMessageBox, QSizePolicy, QCheckBox, QSlider, QTabWidget, QFileDialog,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMenu
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize, QTimer
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QRadialGradient, QShortcut, QKeySequence,
    QTextCharFormat, QSyntaxHighlighter, QTextDocument, QAction
)

# ═══════════════════════════════════════════════════════════════
#  Gate Definitions
# ═══════════════════════════════════════════════════════════════
GATE_MATRICES = {
    "H":  np.array([[1,1],[1,-1]], dtype=complex) / np.sqrt(2),
    "X":  np.array([[0,1],[1,0]], dtype=complex),
    "Y":  np.array([[0,-1j],[1j,0]], dtype=complex),
    "Z":  np.array([[1,0],[0,-1]], dtype=complex),
    "S":  np.array([[1,0],[0,1j]], dtype=complex),
    "T":  np.array([[1,0],[0,np.exp(1j*np.pi/4)]], dtype=complex),
    "CNOT": np.array([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]], dtype=complex),
    "CZ":   np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,-1]], dtype=complex),
    "SWAP": np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]], dtype=complex),
    "CCX": np.eye(8, dtype=complex),
}
GATE_MATRICES["CCX"][6,6]=0; GATE_MATRICES["CCX"][7,7]=0
GATE_MATRICES["CCX"][6,7]=1; GATE_MATRICES["CCX"][7,6]=1

SINGLE_QUBIT_GATES = ["H","X","Y","Z","S","T","RX","RY","RZ"]
TWO_QUBIT_GATES    = ["CNOT","CZ","SWAP"]
THREE_QUBIT_GATES  = ["CCX"]
ROTATION_GATES     = ["RX","RY","RZ"]
ALL_STANDARD_GATES = SINGLE_QUBIT_GATES + TWO_QUBIT_GATES + THREE_QUBIT_GATES

GATE_COLORS = {
    "H":QColor(124,58,237), "X":QColor(239,68,68), "Y":QColor(249,115,22),
    "Z":QColor(59,130,246), "S":QColor(6,182,212), "T":QColor(20,184,166),
    "RX":QColor(139,92,246), "RY":QColor(236,72,153), "RZ":QColor(99,102,241),
    "CNOT":QColor(16,185,129), "CZ":QColor(5,150,105), "SWAP":QColor(245,158,11),
    "CCX":QColor(132,204,22), "M":QColor(245,158,11),
}

GATE_ALIASES = {
    "h":"H","x":"X","y":"Y","z":"Z","s":"S","t":"T",
    "rx":"RX","ry":"RY","rz":"RZ",
    "cnot":"CNOT","cx":"CNOT","cz":"CZ","swap":"SWAP",
    "ccx":"CCX","toffoli":"CCX",
}

GATE_QUBIT_COUNT = {
    "H":1,"X":1,"Y":1,"Z":1,"S":1,"T":1,
    "RX":1,"RY":1,"RZ":1,
    "CNOT":2,"CZ":2,"SWAP":2,
    "CCX":3,"M":1,
}

def rotation_matrix(gtype, angle):
    c, s = np.cos(angle/2), np.sin(angle/2)
    if gtype == "RX": return np.array([[c,-1j*s],[-1j*s,c]], dtype=complex)
    if gtype == "RY": return np.array([[c,-s],[s,c]], dtype=complex)
    if gtype == "RZ": return np.array([[np.exp(-1j*angle/2),0],[0,np.exp(1j*angle/2)]], dtype=complex)
    raise ValueError(gtype)

def make_controlled(U):
    n = U.shape[0]; C = np.eye(2*n, dtype=complex); C[n:,n:] = U; return C

def get_gate_matrix(gate):
    if gate.gtype in ROTATION_GATES:
        U = rotation_matrix(gate.gtype, gate.angle or 0)
    else:
        U = GATE_MATRICES[gate.gtype]
    return make_controlled(U) if gate.controlled else U

def gate_nqubits(gate):
    if gate.controlled: return 2
    if gate.gtype in THREE_QUBIT_GATES: return 3
    if gate.gtype in TWO_QUBIT_GATES: return 2
    return 1

def gate_label(gate):
    if gate.gtype == "M": return "M"
    if gate.controlled:
        a = f"({gate.angle/np.pi:.2g}π)" if gate.angle else ""
        return f"C-{gate.gtype}{a}"
    if gate.gtype in ROTATION_GATES and gate.angle is not None:
        return f"{gate.gtype}({gate.angle/np.pi:.2g}π)"
    return gate.gtype


class CircuitGate:
    def __init__(self, gtype, qubits, angle=None, controlled=False):
        self.gtype = gtype
        self.qubits = tuple(qubits)
        self.angle = angle
        self.controlled = controlled
    def copy(self):
        return CircuitGate(self.gtype, self.qubits, self.angle, self.controlled)


# ═══════════════════════════════════════════════════════════════
#  Quantum Simulator
# ═══════════════════════════════════════════════════════════════
class QuantumSimulator:
    def __init__(self, n=4):
        self.n = n
        self.reset()

    def reset(self):
        self.state = np.zeros(1 << self.n, dtype=complex)
        self.state[0] = 1.0

    def apply_gate(self, matrix, qubits):
        n, k = self.n, len(qubits)
        t = self.state.reshape([2]*n)
        axes = [n-1-q for q in qubits]
        rest = [i for i in range(n) if i not in axes]
        t = np.transpose(t, axes + rest)
        t = (matrix @ t.reshape(2**k, -1)).reshape([2]*n)
        inv = [0]*n
        for i, p in enumerate(axes + rest):
            inv[p] = i
        t = np.transpose(t, inv)
        self.state = t.reshape(-1)

    def apply_noise(self, prob):
        if prob <= 0: return
        paulis = [GATE_MATRICES["X"], GATE_MATRICES["Y"], GATE_MATRICES["Z"]]
        for q in range(self.n):
            if np.random.random() < prob:
                self.apply_gate(paulis[np.random.randint(3)], (q,))

    def probabilities(self):
        p = np.abs(self.state)**2
        return p / p.sum()

    def measure_all(self, shots=2048):
        p = self.probabilities()
        samples = np.random.choice(len(p), size=shots, p=p)
        counts = {}
        for s in samples:
            k = format(s, f"0{self.n}b")
            counts[k] = counts.get(k, 0) + 1
        return dict(sorted(counts.items()))

    def reduced_density(self, qubit):
        t = self.state.reshape([2]*self.n)
        t = np.moveaxis(t, self.n-1-qubit, 0).reshape(2, -1)
        return t @ t.conj().T

    def bloch_vector(self, qubit):
        r = self.reduced_density(qubit)
        return np.array([2*r[0,1].real, -2*r[0,1].imag, (r[0,0]-r[1,1]).real])

    def expectation_values(self, qubit):
        r = self.reduced_density(qubit)
        x = 2 * r[0, 1].real
        y = -2 * r[0, 1].imag
        z = (r[0, 0] - r[1, 1]).real
        return x, y, z

    def entanglement_entropy(self, qubit):
        r = self.reduced_density(qubit)
        eigs = np.linalg.eigvalsh(r)
        eigs = eigs[eigs > 1e-14]
        return float(-np.sum(eigs * np.log2(eigs)))

    def density_matrix(self):
        return np.outer(self.state, self.state.conj())


# ═══════════════════════════════════════════════════════════════
#  SQASM Example Presets (Academic Algorithms Included)
# ═══════════════════════════════════════════════════════════════
SQASM_EXAMPLES = {
"01. Bit Flip (X Gate)": "# X Gate: Flips |0⟩ → |1⟩ and |1⟩ → |0⟩\nqubits 1\nx 0\nmeasure\n",
"02. Hadamard Superposition": "# Hadamard Gate: Creates |+⟩ = (|0⟩+|1⟩)/√2\nqubits 1\nh 0\nmeasure\n",
"03. Phase Gate Demo": "# Z gate flips phase of |1⟩; H makes it measurable\nqubits 1\nx 0\nz 0\nh 0\nmeasure\n",
"04. Rotation Gate Tour": "# RX, RY, RZ rotate the Bloch vector\nqubits 3\nrx(1.5708) 0\nry(1.0472) 1\nrz(0.7854) 2\nh 2\nmeasure\n",
"05. Bloch Sphere States": "# Prepare qubits at key Bloch sphere points\nqubits 6\nx 1\nh 2\nx 3\nh 3\nry(1.5708) 4\nry(-1.5708) 5\nmeasure\n",
"06. Superposition + Interference": "# Two Hadamards cancel: H·H = I\nqubits 1\nh 0\nh 0\nmeasure\n",
"07. Z-H Phase Detection": "# H·Z·H = X, equivalent to just X\nqubits 1\nh 0\nz 0\nh 0\nmeasure\n",
"08. CNOT Truth Table": "# CNOT: Flips target if control is |1⟩\nqubits 2\nx 0\ncnot 0, 1\nmeasure\n",
"09. CNOT All Basis States": "# Run CNOT on |11⟩ input\nqubits 2\nx 0\nx 1\ncnot 0, 1\nmeasure\n",
"10. SWAP Gate Demo": "# SWAP: Exchanges states of two qubits\nqubits 2\nx 0\nswap 0, 1\nmeasure\n",
"11. SWAP via CNOTs": "# SWAP decomposed into 3 CNOTs\nqubits 2\nx 0\ncnot 0, 1\ncnot 1, 0\ncnot 0, 1\nmeasure\n",
"12. Toffoli (CCX) Gate": "# Toffoli: AND gate — flips target if BOTH controls are |1⟩\nqubits 3\nx 0\nx 1\nccx 0, 1, 2\nmeasure\n",
"13. Controlled Gate Zoo": "# Controlled gates: CH, CS, CRX\nqubits 4\nx 0\nx 1\nx 2\nx 3\nch 0, 1\ncs 0, 2\ncrx(1.5708) 1, 3\nmeasure\n",
"14. Bell |Φ⁺⟩ = (|00⟩+|11⟩)/√2": "# Bell State Φ⁺\nqubits 2\nh 0\ncnot 0, 1\nmeasure\n",
"15. Bell |Φ⁻⟩ = (|00⟩−|11⟩)/√2": "# Bell State Φ⁻\nqubits 2\nh 0\ncnot 0, 1\nz 0\nmeasure\n",
"16. Bell |Ψ⁺⟩ = (|01⟩+|10⟩)/√2": "# Bell State Ψ⁺\nqubits 2\nh 0\ncnot 0, 1\nx 1\nmeasure\n",
"17. Bell |Ψ⁻⟩ = (|01⟩−|10⟩)/√2": "# Bell State Ψ⁻\nqubits 2\nh 0\ncnot 0, 1\nx 1\nz 0\nmeasure\n",
"18. All 4 Bell States": "# Generate any Bell state from 2 classical bits\nqubits 2\nh 0\ncnot 0, 1\nx 0\nz 0\nmeasure\n",
"19. GHZ State (3 qubits)": "# GHZ: (|000⟩ + |111⟩)/√2\nqubits 3\nh 0\ncnot 0, 1\ncnot 0, 2\nmeasure\n",
"20. GHZ State (5 qubits)": "# 5-qubit GHZ: All qubits perfectly correlated\nqubits 5\nh 0\ncnot 0, 1\ncnot 0, 2\ncnot 0, 3\ncnot 0, 4\nmeasure\n",
"21. W-State (3 qubits)": "# W-State: (|100⟩+|010⟩+|001⟩)/√3\nqubits 3\nry(1.911) 0\nh 0\ncnot 0, 1\ncnot 0, 2\nx 0\nh 0\ncnot 0, 1\ncnot 0, 2\nmeasure\n",
"22. Uniform Superposition (4 qubits)": "# Equal superposition over all 16 basis states\nqubits 4\nh 0\nh 1\nh 2\nh 3\nmeasure\n",
"23. Entanglement Chain": "# Chain entanglement: q0→q1→q2→q3\nqubits 4\nh 0\ncnot 0, 1\ncnot 1, 2\ncnot 2, 3\nmeasure\n",
"24. Entanglement Star": "# Star entanglement: q0 entangled with all others\nqubits 5\nh 0\ncnot 0, 1\ncnot 0, 2\ncnot 0, 3\ncnot 0, 4\nmeasure\n",
"25. Quantum Teleportation": "# Teleport quantum state using 2 classical bits + Bell pair\nqubits 3\nry(1.047) 0\nh 1\ncnot 1, 2\ncnot 0, 1\nh 0\ncnot 1, 2\ncz 0, 2\nmeasure\n",
"26. Teleport |1⟩ Verification": "# Teleport |1⟩ and verify it arrives correctly\nqubits 3\nx 0\nh 1\ncnot 1, 2\ncnot 0, 1\nh 0\ncnot 1, 2\ncz 0, 2\nmeasure\n",
"27. Superdense Coding (send 10)": "# Send 2 classical bits via 1 qubit using shared Bell pair\nqubits 2\nh 0\ncnot 0, 1\nz 0\ncnot 0, 1\nh 0\nmeasure\n",
"28. Superdense Coding (all 4)": "# 00→nothing  01→X  10→Z  11→XZ\nqubits 2\nh 0\ncnot 0, 1\nx 0\ncnot 0, 1\nh 0\nmeasure\n",
"29. Entanglement Swapping": "# Entangle particles that never met!\nqubits 4\nh 0\ncnot 0, 1\nh 2\ncnot 2, 3\ncnot 1, 2\nh 1\ncnot 1, 3\ncz 0, 3\nmeasure\n",
"30. Deutsch Algorithm": "# Is f(0)⊕f(1) = 0 or 1? ONE quantum query!\nqubits 2\nx 1\nh 0\nh 1\ncnot 0, 1\nh 0\nmeasure\n",
"31. Deutsch-Jozsa (balanced)": "# Balanced oracle f(x₀,x₁) = x₀⊕x₁\nqubits 3\nx 2\nh 0\nh 1\nh 2\ncnot 0, 2\ncnot 1, 2\nh 0\nh 1\nmeasure\n",
"32. Deutsch-Jozsa (constant)": "# Constant oracle f(x) = 0\nqubits 3\nx 2\nh 0\nh 1\nh 2\nh 0\nh 1\nmeasure\n",
"33. Bernstein-Vazirani (s=101)": "# Find secret string s = \"101\" in ONE query!\nqubits 4\nx 3\nh 0\nh 1\nh 2\nh 3\ncnot 0, 3\ncnot 2, 3\nh 0\nh 1\nh 2\nmeasure\n",
"34. Grover Search 2Q (|11⟩)": "# Grover's Algorithm: Search |11⟩ in 4-item database\nqubits 2\nh 0\nh 1\ncz 0, 1\nh 0\nh 1\nx 0\nx 1\ncz 0, 1\nx 0\nx 1\nh 0\nh 1\nmeasure\n",
"35. Grover Search 3Q (|101⟩)": "# Grover's: Search |101⟩ in 8-item database\nqubits 3\nh 0\nh 1\nh 2\nx 1\nccx 0, 2, 1\nx 1\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nx 1\nccx 0, 2, 1\nx 1\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nmeasure\n",
"36. QFT (3 qubits)": "# Quantum Fourier Transform on |101⟩\nqubits 3\nx 0\nx 2\nh 0\ncrz(1.5708) 1, 0\ncrz(0.7854) 2, 0\nh 1\ncrz(1.5708) 2, 1\nh 2\nswap 0, 2\nmeasure\n",
"37. Inverse QFT (3 qubits)": "# QFT then QFT† = Identity → recovers |101⟩\nqubits 3\nx 0\nx 2\nh 0\ncrz(1.5708) 1, 0\ncrz(0.7854) 2, 0\nh 1\ncrz(1.5708) 2, 1\nh 2\nswap 0, 2\nswap 0, 2\nh 2\ncrz(-1.5708) 2, 1\nh 1\ncrz(-0.7854) 2, 0\ncrz(-1.5708) 1, 0\nh 0\nmeasure\n",
"38. 3-Qubit Bit Flip Code": "# Bit Flip Error Correction\nqubits 3\nh 0\ncnot 0, 1\ncnot 0, 2\nx 1\nccx 0, 2, 1\nx 0\nx 2\nccx 0, 2, 1\nx 0\nx 2\ncnot 0, 2\ncnot 0, 1\nh 0\nmeasure\n",
"39. Phase Flip Code": "# Phase Flip Error Correction\nqubits 3\nh 0\ncnot 0, 1\ncnot 0, 2\nh 0\nh 1\nh 2\nz 1\nh 0\nh 1\nh 2\nccx 0, 2, 1\nx 0\nx 2\nccx 0, 2, 1\nx 0\nx 2\ncnot 0, 2\ncnot 0, 1\nh 0\nmeasure\n",
"40. Quantum Coin Flip": "# Truly random bit using quantum mechanics\nqubits 1\nh 0\nmeasure\n",
"41. Quantum Dice (D6)": "# Quantum dice: 3 qubits → 8 states (discard 7,8)\nqubits 3\nh 0\nh 1\nh 2\nmeasure\n",
"42. Quantum Random Byte": "# Generate a random byte (8 bits)\nqubits 8\nh 0\nh 1\nh 2\nh 3\nh 4\nh 5\nh 6\nh 7\nmeasure\n",
"43. Phase Kickback": "# Phase Kickback: CNOT with |−⟩ control\nqubits 2\nh 0\nx 1\nh 1\ncnot 0, 1\nh 0\nmeasure\n",
"44. Quantum Half Adder": "# Quantum Half Adder: a + b\nqubits 3\nx 0\nx 1\nccx 0, 1, 2\ncnot 0, 1\nmeasure\n",
"45. VQE Ansatz": "# Variational Quantum Eigensolver ansatz\nqubits 4\nh 0\nh 1\nh 2\nh 3\nry(0.5) 0\nry(1.2) 1\nry(0.8) 2\nry(1.5) 3\nrz(0.3) 0\nrz(0.7) 1\nrz(1.1) 2\nrz(0.4) 3\ncnot 0, 1\ncnot 1, 2\ncnot 2, 3\ncnot 3, 0\nry(0.9) 0\nry(0.2) 1\nry(1.4) 2\nry(0.6) 3\nmeasure\n",
"46. Quantum Walk (3 steps)": "# Quantum Random Walk on a line\nqubits 3\nh 0\ncnot 0, 1\nh 0\ncnot 0, 1\ncnot 0, 2\nh 0\ncnot 0, 1\nmeasure\n",
"47. Bell Inequality Test": "# Bell/CHSH inequality test circuit\nqubits 2\nh 0\ncnot 0, 1\nh 0\nry(0.7854) 1\nmeasure\n",
"48. Quantum Fourier Interference": "# QFT on superposition shows interference patterns\nqubits 3\nh 0\nh 0\ncrz(1.5708) 1, 0\ncrz(0.7854) 2, 0\nh 1\ncrz(1.5708) 2, 1\nh 2\nswap 0, 2\nmeasure\n",
"49. Reversible Computing": "# All quantum gates are reversible!\nqubits 3\nx 0\nccx 0, 1, 2\ncnot 2, 1\nccx 0, 1, 2\nmeasure\n",
"50. GHZ vs W Entanglement": "# Compare GHZ and W entanglement side by side\nqubits 6\nh 0\ncnot 0, 1\ncnot 0, 2\nry(1.911) 3\nh 3\ncnot 3, 4\ncnot 3, 5\nx 3\nh 3\ncnot 3, 4\ncnot 3, 5\nmeasure\n",
"51. Quantum Phase Estimation (S)": "# QPE: Estimate phase of S gate (phi=1/4). Result: |01⟩\nqubits 3\nx 2\nh 0\nh 1\ncs 0, 2\ncz 1, 2\nh 1\ncrz(-1.5708) 0, 1\nh 0\nswap 0, 1\nmeasure\n",
"52. Phase Gates Comparison": "# Apply T, S, Z to |+> states. Probabilities remain 50/50, but phases differ!\nqubits 3\nh 0\nh 1\nh 2\nt 0\ns 1\nz 2\nmeasure\n",
"53. Quantum Zeno Effect": "# The Quantum Zeno Effect: frequent measurements freeze evolution.\nqubits 1\nh 0\nmeasure\nh 0\nmeasure\n",
"54. Grover Search 3Q (|000⟩)": "# Grover's: Search |000⟩ in 8-item database\nqubits 3\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nccx 0, 1, 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nmeasure\n",
"55. Shor's 9-Qubit Error Correction Code": "# Shor's Code: Encodes 1 logical qubit into 9 physical qubits\n# Protects against any arbitrary single-qubit error (X or Z)\nqubits 9\nx 0  # Start with logical |1⟩ to protect\ncx 0, 3\ncx 0, 6\nh 0\nh 3\nh 6\ncx 0, 1\ncx 0, 2\ncx 3, 4\ncx 3, 5\ncx 6, 7\ncx 6, 8\nmeasure\n",
"56. Simon's Algorithm (s=11)": "# Simon's Algorithm: Finds secret string s=11 in 1 query\n# Oracle: f(x) = x XOR s, implemented as f(x) = x0 XOR x1\nqubits 4\nh 0\nh 1\n# Oracle: computes f(x) into q2, q3\ncx 0, 2\ncx 1, 2\ncx 0, 3\ncx 1, 3\n# Apply H to input register and measure\nh 0\nh 1\nmeasure\n",
"57. QFT Quantum Adder (3+2)": "# Quantum Addition using QFT\n# Adds 2-qubit number 'a' (q0,q1) to 'b' (q2,q3)\n# Input: a=3 (11), b=2 (10). Expected: a+b = 5 (01) mod 4\nqubits 4\nx 0\nx 1\nx 3\n# QFT on b\nh 3\ncrz(1.5708) 2, 3\nh 2\n# Add a\ncrz(1.5708) 0, 2\ncrz(0.7854) 0, 3\ncrz(0.7854) 1, 2\ncrz(1.5708) 1, 3\n# Inverse QFT on b\nh 2\ncrz(-1.5708) 2, 3\nh 3\nmeasure\n",
"58. Grover Search (2 Solutions)": "# Grover's with 2 marked items out of 8 (|001⟩ and |111⟩)\n# Optimal iterations: 2\nqubits 3\nh 0\nh 1\nh 2\n# Iteration 1\nx 1\nx 2\nccx 0, 1, 2\nx 1\nx 2\nccx 0, 1, 2\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\n# Iteration 2\nx 1\nx 2\nccx 0, 1, 2\nx 1\nx 2\nccx 0, 1, 2\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nmeasure\n",
"59. Swap Test (State Comparison)": "# Swap Test: Estimates |⟨ψ|φ⟩|² overlap between two states.\n# q0=ancilla, q1=|ψ⟩, q2=|φ⟩. \n# If q0 measures 0, states are likely identical.\nqubits 3\nh 0\n# Prepare states (currently both |0⟩)\n# x 2  # Uncomment to make |ψ⟩=|0⟩, |φ⟩=|1⟩\n# CSWAP implementation\nccx 0, 1, 2\nccx 0, 2, 1\nccx 0, 1, 2\nh 0\nmeasure\n# Result: ~50% |0⟩ and ~50% |1⟩ if different, 100% |0⟩ if same.\n",
"60. Hadamard Test (⟨ψ|Z|ψ⟩)": "# Hadamard Test: Measures the real part of ⟨ψ|U|ψ⟩.\n# q0=ancilla, q1=|ψ⟩. U=Z. \n# If |ψ⟩ = |+⟩, ⟨+|Z|+⟩ = 0. P(0) = 0.5\nqubits 2\nh 0\nh 1  # Prepare |+⟩\ncz 0, 1  # Controlled-U (U=Z)\nh 0\nmeasure\n# Result: ~50% |0⟩ and ~50% |1⟩, confirming expectation value is 0.\n",
"61. BB84 QKD (State Preparation)": "# BB84 Quantum Key Distribution: Alice prepares states.\n# We prepare 4 possible states: |0⟩, |1⟩, |+⟩, |-⟩\nqubits 4\n# |0⟩ (default)\nx 1      # |1⟩\nh 2      # |+⟩\nx 3\nh 3      # |-⟩\nmeasure\n",
"62. Quantum Walk (4-Node Cycle)": "# Quantum Random Walk on a 4-node cycle.\n# q0, q1 = Position (0 to 3). q2 = Coin.\nqubits 3\nh 2  # Coin in superposition\n\n# Step 1: Shift\n# If coin=1 (Right), increment. If coin=0 (Left), decrement.\n# Decrement logic (when coin=0):\nx 2\nccx 2, 0, 1\ncnot 2, 0\nx 2\n# Increment logic (when coin=1):\ncnot 2, 0\nccx 2, 0, 1\n\n# Flip coin\nh 2\n\n# Step 2: Shift\nx 2\nccx 2, 0, 1\ncnot 2, 0\nx 2\ncnot 2, 0\nccx 2, 0, 1\n\nmeasure\n# Notice the asymmetric probability distribution compared to classical walk!\n",
"63. Deutsch-Jozsa (3-Qubit Balanced)": "# Deutsch-Jozsa with 3 input qubits.\n# Oracle: f(x) = x0 XOR x1 XOR x2 (Balanced)\nqubits 4\nx 3\nh 0\nh 1\nh 2\nh 3\n\n# Oracle (balanced)\ncnot 0, 3\ncnot 1, 3\ncnot 2, 3\n\nh 0\nh 1\nh 2\nmeasure\n# Result: |111⟩ (since it's balanced, it never measures |000⟩)\n",
"64. Grover Search 4Q (|1101⟩)": "# Grover's Algorithm: Search |1101⟩ in 16-item database.\n# Optimal iterations = 3.\nqubits 5\nh 0\nh 1\nh 2\nh 3\n\n# --- Iteration 1 ---\n# Oracle: |1101⟩\nx 1\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 1\n\n# Diffusion\nh 0\nh 1\nh 2\nh 3\nx 0\nx 1\nx 2\nx 3\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 0\nx 1\nx 2\nx 3\nh 0\nh 1\nh 2\nh 3\n\n# --- Iteration 2 ---\nx 1\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 1\n\nh 0\nh 1\nh 2\nh 3\nx 0\nx 1\nx 2\nx 3\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 0\nx 1\nx 2\nx 3\nh 0\nh 1\nh 2\nh 3\n\n# --- Iteration 3 ---\nx 1\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 1\n\nh 0\nh 1\nh 2\nh 3\nx 0\nx 1\nx 2\nx 3\nh 3\nccx 0, 1, 4\nccx 2, 4, 3\nccx 0, 1, 4\nh 3\nx 0\nx 1\nx 2\nx 3\nh 0\nh 1\nh 2\nh 3\n\nmeasure\n",
"65. Wiesner's Quantum Money": "# Wiesner's Quantum Money: Create a banknote with a serial number\n# and quantum states that cannot be copied perfectly.\n# States: |0⟩, |1⟩, |+⟩, |-⟩\nqubits 4\n# Banknote states (e.g., |0⟩|1⟩|+⟩|-⟩)\nx 1\nh 2\nx 3\nh 3\nmeasure\n# A counterfeiter measuring in Z basis only gets 50% of |+⟩|-⟩ right.\n",
"66. Quantum State Tomography": "# Quantum State Tomography: Reconstructing a state from measurements.\n# To fully reconstruct a single qubit state, we need to measure\n# in 3 bases: X, Y, and Z.\nqubits 3\n# Prepare the same state on all 3 qubits: |+i⟩ = (|0⟩ + i|1⟩)/√2\nrx(1.5708) 0\nrx(1.5708) 1\nrx(1.5708) 2\n\n# Measure q0 in Z basis (default)\n# Measure q1 in X basis\nh 1\n# Measure q2 in Y basis\nrx(-1.5708) 2  # Maps Y basis to Z basis\nmeasure\n",
"67. Quantum Phase Estimation (T-Gate)": "# QPE: Estimate phase of T gate (phi=1/8).\n# T|1> = exp(i pi/4) |1>. Phase = 1/8.\n# Requires 3 counting qubits (q0, q1, q2) and 1 eigenstate (q3).\nqubits 4\nx 3\nh 0\nh 1\nh 2\n# Apply controlled-U^(2^0)\nct 0, 3\n# Apply controlled-U^(2^1) = CS\ns 3\n# Apply controlled-U^(2^2) = CZ (since U^4 = S^2 = Z)\ncz 2, 3\n# Inverse QFT on q0, q1, q2\nh 2\ncrz(-1.5708) 1, 2\ncrz(-0.7854) 0, 2\nh 1\ncrz(-1.5708) 0, 1\nh 0\nswap 0, 2\nmeasure\n# Expected: |001⟩ (which is 1/8 in binary)\n",
"68. Grover Search 3Q (|010⟩ & |101⟩)": "# Grover's with 2 marked items out of 8 (|010⟩ and |101⟩)\n# Optimal iterations: 2\nqubits 3\nh 0\nh 1\nh 2\n\n# Iteration 1\n# Oracle for |010⟩ and |101⟩\nx 0\nx 2\nccx 0, 2, 1\nx 0\nx 2\n# Diffusion\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\n\n# Iteration 2\nx 0\nx 2\nccx 0, 2, 1\nx 0\nx 2\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\n\nmeasure\n",
"69. Bernstein-Vazirani (s=01)": "# Find secret string s = \"01\" in ONE query!\n# Oracle: f(x) = x0\nqubits 3\nx 2\nh 0\nh 1\nh 2\n# Oracle for s=01\ncnot 0, 2\nh 0\nh 1\nmeasure\n# Result: |01⟩\n",
"70. Quantum Repeater (Chain Swap)": "# Quantum Repeater: Entangle q0 and q3 via intermediate nodes q1, q2.\nqubits 4\n# Create Bell pairs (q0,q1) and (q2,q3)\nh 0\ncnot 0, 1\nh 2\ncnot 2, 3\n# Swap q1 and q2\nswap 1, 2\n# Measure intermediate nodes (conceptually, this projects q0,q3 into a Bell state)\nmeasure\n",
"71. Quantum Full Adder (1-Bit)": "# Quantum 1-bit Full Adder: Computes A + B + Cin = Sum + Cout\n# Inputs: A(q0), B(q1), Cin(q2). Outputs: Cout(q3), Sum(q2), B(q1), A(q0)\n# Input: A=1, B=1, Cin=0 => Sum=0, Cout=1\nqubits 4\nx 0\nx 1\n\n# Compute Carry (q3 = A AND B)\nccx 0, 1, 3\n# Compute partial Sum (q1 = A XOR B)\ncnot 0, 1\n# Add Cin (q2) to partial Sum and Carry\nccx 1, 2, 3\ncnot 1, 2\n\nmeasure\n# Result: |1110⟩ (q3=1, q2=0, q1=1, q0=1. Sum=0, Cout=1)\n",
"72. Steane [[7,1,3]] Error Correction Code": "# Steane Code: Encodes 1 logical qubit into 7 physical qubits.\n# Protects against any single-qubit error (X, Y, or Z).\nqubits 7\nx 0  # Logical |1>\n# Encoding circuit (simplified)\ncnot 0, 1\ncnot 0, 2\ncnot 0, 3\ncnot 1, 4\ncnot 1, 5\ncnot 2, 4\ncnot 2, 6\ncnot 3, 5\ncnot 3, 6\nh 0\nh 1\nh 2\nh 3\ncnot 0, 4\ncnot 0, 5\ncnot 0, 6\ncnot 1, 4\ncnot 1, 5\ncnot 1, 6\ncnot 2, 4\ncnot 2, 5\ncnot 2, 6\ncnot 3, 4\ncnot 3, 5\ncnot 3, 6\nmeasure\n",
"73. HHL Algorithm (Conceptual 2x2)": "# HHL Algorithm: Solves Ax = b.\n# Conceptual 2x2 for A = Z, b = |0>.\n# q0: ancilla, q1: clock, q2: data (b)\nqubits 3\n# QPE\ncz 1, 2\nh 1\ncz 1, 2\nh 1\n# Inversion (Controlled Y rotation)\ncry(1.5708) 1, 0\n# Inverse QPE\nh 1\ncz 1, 2\nh 1\ncz 1, 2\nmeasure\n",
"74. Amplitude Amplification (No Oracle)": "# Diffusion operator on an empty database.\n# Reflects around the mean, pushing all amplitude back to |000>.\nqubits 3\nh 0\nh 1\nh 2\n# Diffusion Operator\nh 0\nh 1\nh 2\nx 0\nx 1\nx 2\nh 2\nccx 0, 1, 2\nh 2\nx 0\nx 1\nx 2\nh 0\nh 1\nh 2\nmeasure\n# Result: 100% |000>\n",
"75. Quantum Multiplexer (2-to-1)": "# Quantum Multiplexer: If q0=0, copy q1 to q3. If q0=1, copy q2 to q3.\n# Input: q0=0, q1=1, q2=0. Expected Output: q3=1\nqubits 4\nx 1  # A=1\n# B=0\n# Sel=0\n# Out = (A AND NOT S) OR (B AND S)\n# Invert S\nx 0\nccx 0, 1, 3\n# Restore S, invert for B path\nx 0\nccx 0, 2, 3\nmeasure\n# Result: |0011> (Sel=0, A=1, B=0, Out=1)\n",
"76. QFT Quantum Subtractor (3-1)": "# Quantum Subtraction using QFT: b - a\n# b=3 (11), a=1 (01). Result: b-a = 2 (10)\nqubits 4\nx 2      # b = 3\nx 3      # b = 3\nx 0      # a = 1\n# QFT on b\nh 3\ncrz(1.5708) 2, 3\nh 2\n# Subtract a (invert rotations)\ncrz(-1.5708) 0, 2\ncrz(-0.7854) 0, 3\n# Inverse QFT on b\nh 2\ncrz(-1.5708) 2, 3\nh 3\nmeasure\n# Result: b=2 (10)\n",
"77. Quantum Relay (Teleportation Chain)": "# Quantum Relay: Teleport a state across 3 nodes.\n# Node A (q0) -> Node B (q2) -> Node C (q4)\nqubits 5\nh 0  # Prepare |+> to teleport\n# Bell pair 1 (q1, q2)\nh 1\ncnot 1, 2\n# Teleport q0 to q2\ncnot 0, 1\nh 0\ncnot 1, 2\ncz 0, 2\n# Bell pair 2 (q3, q4)\nh 3\ncnot 3, 4\n# Teleport q2 to q4\ncnot 2, 3\nh 2\ncnot 3, 4\ncz 2, 4\nmeasure\n# q4 ends up with the |+> state.\n",
"78. Quantum Phase Estimation (Z-Gate)": "# QPE: Estimate phase of Z gate (phi=1/2).\n# Z|1> = -|1> = exp(i pi) |1>. Phase = 1/2.\n# Requires 1 counting qubit and 1 eigenstate.\nqubits 2\nx 1\nh 0\ncz 0, 1\nh 0\nmeasure\n# Result: |1> (which is 1/2 in binary)\n",
"79. Deutsch-Jozsa (Constant 1)": "# Deutsch-Jozsa: Constant oracle f(x) = 1\n# Flips the ancilla regardless of input.\nqubits 3\nx 2\nh 0\nh 1\nh 2\n# Oracle f(x) = 1\nx 2\nh 0\nh 1\nmeasure\n# Result: |00> (constant functions always measure |0...0>)\n",
}


class SqasmHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.gate_fmt = QTextCharFormat()
        self.gate_fmt.setForeground(QColor(100, 210, 255))
        self.gate_fmt.setFontWeight(QFont.Bold)
        self.comment_fmt = QTextCharFormat()
        self.comment_fmt.setForeground(QColor(90, 100, 120))
        self.comment_fmt.setFontItalic(True)
        self.cmd_fmt = QTextCharFormat()
        self.cmd_fmt.setForeground(QColor(255, 180, 80))
        self.cmd_fmt.setFontWeight(QFont.Bold)
        self.num_fmt = QTextCharFormat()
        self.num_fmt.setForeground(QColor(200, 120, 255))

    def highlightBlock(self, text):
        for fmt, patterns in [
            (self.comment_fmt, [r'#[^\n]*', r'//[^\n]*']),
            (self.cmd_fmt, [r'\b(qubits|measure|reset|barrier)\b']),
            (self.gate_fmt, [r'\b(h|x|y|z|s|t|rx|ry|rz|cnot|cx|cz|swap|ccx|toffoli|ch|cs|ct|crx|cry|crz)\b']),
            (self.num_fmt, [r'\b\d+\.?\d*\b']),
        ]:
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    self.setFormat(m.start(), m.end()-m.start(), fmt)


# ═══════════════════════════════════════════════════════════════
#  Visual Widgets
# ═══════════════════════════════════════════════════════════════
class CircuitWidget(QWidget):
    gate_selected = Signal(int)
    circuit_changed = Signal()

    ML, MT = 64, 36
    RH, CW = 56, 74

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gates = []
        self.n_qubits = 4
        self.sel = -1
        self.step = -1
        self._cols = []
        self.placing_gate = None
        self.placing_params = None
        self.placing_qubits = []
        self.placing_controlled = False
        self.hover_qubit = -1
        self.setMinimumSize(520, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_n_qubits(self, n):
        self.n_qubits = n
        self.gates.clear()
        self.sel = -1
        self.step = -1
        self.update()

    def add_gate(self, g):
        self.gates.append(g)
        self.update()
        self.circuit_changed.emit()

    def remove_gate(self, idx):
        if 0 <= idx < len(self.gates):
            self.gates.pop(idx)
            self.sel = -1
            self.update()
            self.circuit_changed.emit()

    def set_placing_gate(self, gate_type, params=None, controlled=False):
        self.placing_gate = gate_type
        self.placing_params = params
        self.placing_controlled = controlled
        self.placing_qubits.clear()
        self.update()

    def cancel_placing(self):
        self.placing_gate = None
        self.placing_qubits.clear()
        self.update()

    def _layout(self):
        qc = [0] * self.n_qubits
        cols = []
        for g in self.gates:
            c = max(qc[q] for q in g.qubits) if g.qubits else 0
            for q in g.qubits:
                qc[q] = c + 1
            cols.append(c)
        self._cols = cols
        return cols

    def depth(self):
        cols = self._layout()
        return max(cols) + 1 if cols else 0

    def _pos(self, col, row):
        return self.ML + col * self.CW + self.CW // 2, self.MT + row * self.RH

    def _qubit_at_y(self, y):
        q = int(round((y - self.MT) / self.RH))
        if 0 <= q < self.n_qubits:
            return q
        return -1

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor(20, 22, 34))

        cols = self._layout()
        mc = max(cols) + 1 if cols else 0
        self.setMinimumWidth(max(520, self.ML + mc * self.CW + 50))

        for q in range(self.n_qubits):
            y = self.MT + q * self.RH
            if self.placing_gate and q == self.hover_qubit:
                p.setPen(QPen(QColor(255, 210, 60, 120), 3))
            else:
                p.setPen(QPen(QColor(70, 75, 100), 2))
            p.drawLine(self.ML, y, W, y)
            p.setPen(QColor(170, 180, 210))
            p.setFont(QFont("Consolas", 11, QFont.Bold))
            p.drawText(QRectF(0, y - 14, self.ML - 8, 28), Qt.AlignRight | Qt.AlignVCenter, f"|q{q}⟩")

        for idx, (g, col) in enumerate(zip(self.gates, cols)):
            if not g.qubits: continue
            
            is_dimmed = False
            is_active = False
            if self.step >= 0:
                if idx >= self.step:
                    is_dimmed = True
                if idx == self.step:
                    is_active = True
                    
            self._draw_gate(p, g, col, idx, is_dimmed, is_active)

        if self.placing_gate and self.placing_qubits:
            nq = GATE_QUBIT_COUNT.get(self.placing_gate, 1)
            if self.placing_controlled: nq = 2
            preview_col = max(self._cols) + 1 if self._cols else 0
            for q in self.placing_qubits:
                cx, cy = self._pos(preview_col, q)
                color = GATE_COLORS.get(self.placing_gate, QColor(150, 150, 150))
                p.setBrush(QColor(color.red(), color.green(), color.blue(), 80))
                p.setPen(QPen(color, 2, Qt.DashLine))
                p.drawRoundedRect(QRectF(cx - 22, cy - 22, 44, 44), 8, 8)
        p.end()

    def _draw_gate(self, p, g, col, idx, dim, active):
        nq = gate_nqubits(g)
        color = GATE_COLORS.get(g.gtype, QColor(150, 150, 150))
        label = gate_label(g)
        selected = idx == self.sel
        alpha = 80 if dim else 255
        color = QColor(color.red(), color.green(), color.blue(), alpha)

        qmin, qmax = min(g.qubits), max(g.qubits)
        cx, y1 = self._pos(col, qmin)
        _, y2 = self._pos(col, qmax)

        if active:
            p.setBrush(QColor(255, 255, 100, 40))
            p.setPen(QPen(QColor(255, 255, 100, 200), 2))
            p.drawRoundedRect(QRectF(cx - 30, y1 - 25, 60, y2 - y1 + 50), 10, 10)

        if nq >= 2:
            pen_c = QColor(255, 210, 60, alpha) if selected else QColor(color.red(), color.green(), color.blue(), alpha)
            p.setPen(QPen(pen_c, 2.5))
            p.drawLine(cx, y1, cx, y2)

        if g.controlled or g.gtype == "CNOT":
            ctrl, tgt = g.qubits[0], g.qubits[1]
            _, yc = self._pos(col, ctrl)
            _, yt = self._pos(col, tgt)
            p.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, yc), 7, 7)
            if g.gtype == "CNOT":
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(color, 2.5))
                p.drawEllipse(QPointF(cx, yt), 16, 16)
                p.drawLine(int(cx-16), int(yt), int(cx+16), int(yt))
                p.drawLine(int(cx), int(yt-16), int(cx), int(yt+16))
            else:
                r = QRectF(cx-22, yt-22, 44, 44)
                grad = QLinearGradient(r.topLeft(), r.bottomRight())
                grad.setColorAt(0, QColor(40, 50, 70, alpha))
                grad.setColorAt(1, QColor(28, 34, 52, alpha))
                p.setBrush(grad)
                p.setPen(QPen(color, 2))
                p.drawRoundedRect(r, 8, 8)
                p.setPen(QColor(230, 235, 255, alpha))
                p.setFont(QFont("Consolas", 9, QFont.Bold))
                p.drawText(r, Qt.AlignCenter, label)

        elif g.gtype == "CZ":
            for yy in (y1, y2):
                p.setBrush(color)
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(cx, yy), 7, 7)

        elif g.gtype == "SWAP":
            for yy in (y1, y2):
                p.setPen(QPen(color, 2.5))
                p.drawLine(int(cx-10), int(yy-10), int(cx+10), int(yy+10))
                p.drawLine(int(cx-10), int(yy+10), int(cx+10), int(yy-10))

        elif g.gtype == "CCX":
            q0, q1, q2 = g.qubits
            _, ya = self._pos(col, q0)
            _, yb = self._pos(col, q1)
            _, yc2 = self._pos(col, q2)
            p.setPen(QPen(color, 2.5))
            p.drawLine(cx, ya, cx, yc2)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, ya), 7, 7)
            p.drawEllipse(QPointF(cx, yb), 7, 7)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(color, 2.5))
            p.drawEllipse(QPointF(cx, yc2), 16, 16)
            p.drawLine(int(cx-16), int(yc2), int(cx+16), int(yc2))
            p.drawLine(int(cx), int(yc2-16), int(cx), int(yc2+16))

        elif g.gtype == "M":
            q = g.qubits[0]
            cx2, cy2 = self._pos(col, q)
            r = QRectF(cx2-20, cy2-20, 40, 40)
            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(QColor(20, 22, 34, alpha)))
            p.drawEllipse(r)
            p.drawArc(QRectF(r.x()+4, r.y()+2, r.width()-8, r.height()-4), 30*16, 150*16)
            p.drawLine(r.center().toPoint() + QPointF(0, -2).toPoint(), r.bottomRight().toPoint() - QPointF(8, 8).toPoint())

        else:
            q = g.qubits[0]
            cx2, cy2 = self._pos(col, q)
            r = QRectF(cx2-22, cy2-22, 44, 44)
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0, QColor(40, 50, 70, alpha) if not selected else QColor(60, 60, 40, alpha))
            grad.setColorAt(1, QColor(28, 34, 52, alpha))
            p.setBrush(grad)
            p.setPen(QPen(QColor(255, 210, 60, alpha) if selected else color, 2))
            p.drawRoundedRect(r, 8, 8)
            p.setPen(QColor(230, 235, 255, alpha))
            fsz = 9 if len(label) > 3 else 14
            p.setFont(QFont("Consolas", fsz, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, label)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.placing_gate:
                q = self._qubit_at_y(e.position().y())
                if q < 0: return
                nq = GATE_QUBIT_COUNT.get(self.placing_gate, 1)
                if self.placing_controlled: nq = 2
                if q in self.placing_qubits: return
                self.placing_qubits.append(q)
                if len(self.placing_qubits) == nq:
                    angle = self.placing_params
                    g = CircuitGate(self.placing_gate, list(self.placing_qubits), angle=angle, controlled=self.placing_controlled)
                    self.add_gate(g)
                    self.placing_qubits.clear()
                self.update()
                return

            cols = self._cols
            best = -1
            bd = 32
            for idx, (g, col) in enumerate(zip(self.gates, cols)):
                if not g.qubits: continue
                cx, cy = self._pos(col, sum(g.qubits)/len(g.qubits))
                d = math.hypot(e.position().x()-cx, e.position().y()-cy)
                if d < bd:
                    best = idx
                    bd = d
            self.sel = best
            self.gate_selected.emit(best)
            self.update()

    def contextMenuEvent(self, event):
        cols = self._cols
        best = -1
        bd = 32
        pos = event.pos()
        for idx, (g, col) in enumerate(zip(self.gates, cols)):
            if not g.qubits: continue
            cx, cy = self._pos(col, sum(g.qubits)/len(g.qubits))
            d = math.hypot(pos.x()-cx, pos.y()-cy)
            if d < bd:
                best = idx
                bd = d
        
        menu = QMenu(self)
        if best >= 0:
            act_delete = menu.addAction(f"Delete {gate_label(self.gates[best])}")
            menu.addSeparator()
            act_info = menu.addAction("Inspect Gate Matrix")
            action = menu.exec(event.globalPos())
            if action == act_delete:
                self.remove_gate(best)
            elif action == act_info:
                self.sel = best
                self.gate_selected.emit(best)
                self.update()
        else:
            if self.placing_gate:
                act_cancel = menu.addAction("Cancel Placement")
                action = menu.exec(event.globalPos())
                if action == act_cancel:
                    self.cancel_placing()

    def mouseMoveEvent(self, e):
        if self.placing_gate:
            q = self._qubit_at_y(e.position().y())
            if q != self.hover_qubit:
                self.hover_qubit = q
                self.update()

    def leaveEvent(self, _):
        self.hover_qubit = -1
        self.update()


class BlochWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bv = np.array([0., 0., 1.])
        self.setMinimumSize(250, 250)
        self.theta = 0.55
        self.phi = 0.35
        self.drag_start = None
        self.setCursor(Qt.OpenHandCursor)

    def set_vector(self, v):
        self.bv = v
        self.update()

    def _proj(self, x, y, z):
        ct, st = math.cos(self.theta), math.sin(self.theta)
        cp, sp = math.cos(self.phi), math.sin(self.phi)
        x1 = x*ct + z*st
        z1 = -x*st + z*ct
        return x1, y*cp - z1*sp, y*sp + z1*cp

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        R = min(w, h) // 2 - 34
        p.fillRect(self.rect(), QColor(20, 22, 34))

        p.setPen(QPen(QColor(60, 65, 90), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(cx-R, cy-R, 2*R, 2*R)

        def gcirc(a1, a2, n=72):
            front, back = [], []
            for i in range(n+1):
                a = 2 * math.pi * i / n
                c = [0., 0., 0.]
                c[a1] = math.cos(a)
                c[a2] = math.sin(a)
                sx, sy, sz = self._proj(*c)
                pt = QPointF(cx + sx*R, cy - sy*R)
                (front if sz >= 0 else back).append(pt)
            if len(back) > 1:
                p.setPen(QPen(QColor(40, 44, 65), 1, Qt.DotLine))
                for i in range(len(back)-1):
                    p.drawLine(back[i], back[i+1])
            if len(front) > 1:
                p.setPen(QPen(QColor(80, 88, 120), 1))
                for i in range(len(front)-1):
                    p.drawLine(front[i], front[i+1])

        gcirc(0, 1)
        gcirc(0, 2)
        gcirc(1, 2)

        for lbl, v, col in [("|0⟩", (0,0,1), QColor(100,150,255)),
                            ("|1⟩", (0,0,-1), QColor(100,150,255)),
                            ("x", (1,0,0), QColor(255,100,100)),
                            ("y", (0,1,0), QColor(100,255,100))]:
            sx, sy, _ = self._proj(*v)
            ex, ey = cx + sx*R, cy - sy*R
            p.setPen(QPen(col, 1.5, Qt.DashLine))
            p.drawLine(QPointF(cx, cy), QPointF(ex, ey))
            p.setPen(col)
            p.setFont(QFont("Consolas", 10, QFont.Bold))
            p.drawText(QPointF(ex+4, ey-4), lbl)

        vx, vy, vz = self.bv
        sx, sy, _ = self._proj(vx, vy, vz)
        ex, ey = cx + sx*R, cy - sy*R
        p.setPen(QPen(QColor(255, 70, 70), 3))
        p.drawLine(QPointF(cx, cy), QPointF(ex, ey))
        grad = QRadialGradient(ex, ey, 8)
        grad.setColorAt(0, QColor(255, 120, 120))
        grad.setColorAt(1, QColor(180, 40, 40))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(ex, ey), 7, 7)

        p.setPen(QColor(190, 200, 220))
        p.setFont(QFont("Consolas", 9))
        p.drawText(6, h - 8, f"({vx:+.2f}, {vy:+.2f}, {vz:+.2f})")
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_start = e.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self.drag_start is not None:
            dx = e.position().x() - self.drag_start.x()
            dy = e.position().y() - self.drag_start.y()
            self.theta -= dx * 0.01
            self.phi += dy * 0.01
            self.drag_start = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        self.drag_start = None
        self.setCursor(Qt.OpenHandCursor)
        
    def mouseDoubleClickEvent(self, e):
        self.theta = 0.55
        self.phi = 0.35
        self.update()


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = {}
        self.meas = {}
        self.setMinimumSize(300, 170)

    def set_probabilities(self, probs, n):
        self.bars = {format(i, f"0{n}b"): float(pr) for i, pr in enumerate(probs) if pr > 1e-4}
        self.meas = {}
        self.update()

    def set_measurements(self, counts, shots):
        self.meas = {k: v/shots for k, v in counts.items()}
        self.update()

    def clear_measurements(self):
        self.meas = {}
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor(20, 22, 34))

        keys = sorted(set(list(self.bars) + list(self.meas)))
        if not keys:
            p.setPen(QColor(120, 130, 160))
            p.setFont(QFont("Consolas", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "Run circuit to see probabilities")
            p.end()
            return

        n = len(keys)
        bw = max(18, min(54, (W - 60) // max(n, 1)))
        tw = n * bw
        x0 = (W - tw) // 2
        top, bot = 28, 36
        mh = H - top - bot

        p.setPen(QColor(170, 180, 210))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(8, 16, "Probability Histogram")

        p.setPen(QPen(QColor(45, 50, 70), 1, Qt.DotLine))
        for f in (.25, .5, .75, 1.):
            yy = int(H - bot - f * mh)
            p.drawLine(x0, yy, x0 + tw, yy)

        for i, k in enumerate(keys):
            x = x0 + i * bw
            prob = self.bars.get(k, 0)
            bh = int(prob * mh)
            if bh > 0:
                grad = QLinearGradient(x, H-bot-bh, x, H-bot)
                grad.setColorAt(0, QColor(60, 160, 240))
                grad.setColorAt(1, QColor(30, 80, 160))
                p.setBrush(grad)
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(x+2, H-bot-bh, bw-4, bh, 3, 3)

            mp = self.meas.get(k, 0)
            mb = int(mp * mh)
            if mb > 0:
                p.setBrush(QColor(240, 130, 60, 160))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(x+2, H-bot-mb, bw-4, mb, 3, 3)

            p.setPen(QColor(170, 180, 210))
            p.setFont(QFont("Consolas", max(7, min(10, bw//4))))
            p.drawText(QRectF(x, H-bot+2, bw, bot-4), Qt.AlignCenter, k)
            if prob > .03:
                p.setPen(QColor(200, 210, 230))
                p.setFont(QFont("Consolas", 8))
                p.drawText(QRectF(x, H-bot-bh-16, bw, 14), Qt.AlignCenter, f"{prob:.2f}")

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 160, 240))
        p.drawRect(W-130, 6, 12, 12)
        p.setBrush(QColor(240, 130, 60, 160))
        p.drawRect(W-130, 22, 12, 12)
        p.setPen(QColor(180, 190, 210))
        p.setFont(QFont("Consolas", 9))
        p.drawText(W-114, 16, "Theory")
        p.drawText(W-114, 32, "Measured")
        p.end()


class DensityMatrixWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rho = None
        self.setMinimumSize(200, 200)

    def set_matrix(self, rho):
        self.rho = rho
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor(20, 22, 34))

        if self.rho is None or self.rho.shape[0] > 64:
            p.setPen(QColor(120, 130, 160))
            p.setFont(QFont("Consolas", 10))
            msg = ("Density matrix (≤6 qubits)" if self.rho is None else "Too large (>6 qubits)")
            p.drawText(self.rect(), Qt.AlignCenter, msg)
            p.end()
            return

        n = self.rho.shape[0]
        sz = min(W - 60, H - 60)
        cs = max(2, sz // n)
        gw = cs * n
        x0 = (W - gw) // 2
        y0 = 30

        p.setPen(QColor(170, 180, 210))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(QRectF(0, 4, W, 20), Qt.AlignCenter, "Density Matrix |ρᵢⱼ|")

        for i in range(n):
            for j in range(n):
                v = self.rho[i, j]
                mag = abs(v)
                hue = int((np.angle(v) / (2*math.pi)) * 360) if mag > 1e-6 else 0
                hue = (hue % 360 + 360) % 360
                col = QColor.fromHsv(hue, min(255, int(mag*255)), min(255, 60 + int(mag*195)))
                p.setPen(Qt.NoPen)
                p.setBrush(col)
                p.drawRect(x0 + j*cs, y0 + i*cs, cs-1, cs-1)

        lx = x0 + gw + 8
        ly = y0
        lh = gw
        lw = 14
        if lx + lw + 30 < W:
            for iy in range(lh):
                frac = 1 - iy / lh
                col = QColor.fromHsv(0, min(255, int(frac*255)), min(255, 60 + int(frac*195)))
                p.setPen(col)
                p.drawLine(lx, ly+iy, lx+lw, ly+iy)
            p.setPen(QColor(160, 170, 200))
            p.setFont(QFont("Consolas", 8))
            p.drawText(lx+lw+2, ly+8, "1.0")
            p.drawText(lx+lw+2, ly+lh, "0.0")
        p.end()


class EntropyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entropies = []
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

    def set_entropies(self, ents):
        self.entropies = ents
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor(20, 22, 34))

        p.setPen(QColor(170, 180, 210))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(6, 14, "Entanglement Entropy (von Neumann)")

        if not self.entropies:
            p.setPen(QColor(120, 130, 160))
            p.setFont(QFont("Consolas", 9))
            p.drawText(self.rect(), Qt.AlignCenter, "—")
            p.end()
            return

        n = len(self.entropies)
        top = 22
        bot = H - 8
        bh = bot - top
        bw = max(20, min(60, (W - 40) // max(n, 1)))
        x0 = (W - n * bw) // 2
        maxe = 1.0

        for i, e in enumerate(self.entropies):
            x = x0 + i * bw
            h = int(min(e / maxe, 1.0) * bh)
            hue = max(0, 120 - int(e / maxe * 120))
            col = QColor.fromHsv(hue, 200, 180)
            grad = QLinearGradient(x, bot-h, x, bot)
            grad.setColorAt(0, col)
            grad.setColorAt(1, col.darker(160))
            p.setBrush(grad)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x+3, bot-h, bw-6, h, 3, 3)
            p.setPen(QColor(200, 210, 230))
            p.setFont(QFont("Consolas", 9, QFont.Bold))
            p.drawText(QRectF(x, bot+1, bw, 14), Qt.AlignCenter, f"q{i}")
            p.setFont(QFont("Consolas", 8))
            p.drawText(QRectF(x, bot-h-14, bw, 13), Qt.AlignCenter, f"{e:.2f}")
        p.end()


# ═══════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚛  QubitLab  —  Quantum Computer Simulator  (Ultimate Pro Edition)")
        self.resize(1550, 980)
        self.sim = QuantumSimulator(4)
        self.n_qubits = 4
        self.history = []
        self.step_idx = -1

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(500)
        self.playback_timer.timeout.connect(self._playback_step)

        self._build_ui()
        self._apply_style()
        self._setup_shortcuts()
        self._gate_changed(self.combo_gate.currentText())
        self._update_displays()
        self._deselect_palette()

    def _build_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        act_open = QAction("Open SQASM...", self)
        act_open.triggered.connect(self._open_sqasm)
        file_menu.addAction(act_open)
        
        act_save = QAction("Save SQASM...", self)
        act_save.triggered.connect(self._save_sqasm_file)
        file_menu.addAction(act_save)
        
        file_menu.addSeparator()
        
        act_export_png = QAction("Export Circuit to PNG", self)
        act_export_png.triggered.connect(self._export_png)
        file_menu.addAction(act_export_png)
        
        act_export_qasm = QAction("Export to QASM 2.0", self)
        act_export_qasm.triggered.connect(self._export_qasm)
        file_menu.addAction(act_export_qasm)
        
        file_menu.addSeparator()
        
        act_copy = QAction("Copy SQASM to Clipboard", self)
        act_copy.triggered.connect(self._copy_sqasm)
        file_menu.addAction(act_copy)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ─── LEFT PANEL ───
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.setSpacing(6)

        palette_box = QGroupBox("Gate Palette  (click to select, then click on circuit)")
        pl = QGridLayout(palette_box)
        pl.setSpacing(4)
        self.gate_buttons = []
        palette_gates = [
            ("H", "H"), ("X", "X"), ("Y", "Y"), ("Z", "Z"),
            ("S", "S"), ("T", "T"),
            ("RX", "RX"), ("RY", "RY"), ("RZ", "RZ"),
            ("CNOT", "CNOT"), ("CZ", "CZ"), ("SWAP", "SWAP"),
            ("CCX", "CCX"), ("M", "M"),
        ]
        for i, (label, gtype) in enumerate(palette_gates):
            btn = QPushButton(label)
            color = GATE_COLORS.get(gtype, QColor(150,150,150))
            hex_color = color.name()
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color}; color: white;
                    border-radius: 5px; padding: 8px; font-weight: bold;
                    min-width: 40px;
                }}
                QPushButton:checked {{
                    background-color: white; color: {hex_color};
                    border: 2px solid {hex_color};
                }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn.setCheckable(True)
            btn.setProperty("gate_type", gtype)
            btn.clicked.connect(self._on_palette_gate)
            pl.addWidget(btn, i // 4, i % 4)
            self.gate_buttons.append(btn)

        self.theta_widget = QWidget()
        tl = QHBoxLayout(self.theta_widget)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(QLabel("θ:"))
        self.theta_spin = QDoubleSpinBox()
        self.theta_spin.setRange(-10.0, 10.0)
        self.theta_spin.setSingleStep(0.25)
        self.theta_spin.setValue(0.5)
        self.theta_spin.setSuffix(" π rad")
        self.theta_spin.valueChanged.connect(
            lambda: self._on_palette_gate() if any(b.isChecked() for b in self.gate_buttons) else None)
        tl.addWidget(self.theta_spin)
        self.theta_widget.hide()
        pl.addWidget(self.theta_widget, 4, 0, 1, 4)
        ll.addWidget(palette_box)

        ctrl = QGroupBox("Precise Gate Controls")
        cg = QGridLayout(ctrl)
        cg.addWidget(QLabel("Qubits:"), 0, 0)
        self.spin_nq = QSpinBox()
        self.spin_nq.setRange(1, 12)
        self.spin_nq.setValue(4)
        self.spin_nq.valueChanged.connect(self._change_nq)
        cg.addWidget(self.spin_nq, 0, 1)
        cg.addWidget(QLabel("Gate:"), 0, 2)
        self.combo_gate = QComboBox()
        self.combo_gate.addItems(SINGLE_QUBIT_GATES + TWO_QUBIT_GATES + THREE_QUBIT_GATES)
        self.combo_gate.currentTextChanged.connect(self._gate_changed)
        cg.addWidget(self.combo_gate, 0, 3, 1, 2)
        self.lbl_angle = QLabel("Angle (×π):")
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(-4, 4)
        self.spin_angle.setSingleStep(0.25)
        self.spin_angle.setValue(0.5)
        self.spin_angle.setDecimals(4)
        cg.addWidget(self.lbl_angle, 1, 0)
        cg.addWidget(self.spin_angle, 1, 1)
        self.chk_ctrl = QCheckBox("Controlled")
        cg.addWidget(self.chk_ctrl, 1, 2)
        self.lbl_q1 = QLabel("Qubit:")
        self.spin_q1 = QSpinBox()
        self.spin_q1.setRange(0, 11)
        self.lbl_q2 = QLabel("Ctrl:")
        self.spin_q2 = QSpinBox()
        self.spin_q2.setRange(0, 11)
        self.lbl_q3 = QLabel("Tgt:")
        self.spin_q3 = QSpinBox()
        self.spin_q3.setRange(0, 11)
        self.lbl_q4 = QLabel("C2:")
        self.spin_q4 = QSpinBox()
        self.spin_q4.setRange(0, 11)
        cg.addWidget(self.lbl_q1, 2, 0)
        cg.addWidget(self.spin_q1, 2, 1)
        cg.addWidget(self.lbl_q2, 2, 2)
        cg.addWidget(self.spin_q2, 2, 3)
        cg.addWidget(self.lbl_q3, 2, 4)
        cg.addWidget(self.spin_q3, 2, 4)
        cg.addWidget(self.lbl_q4, 3, 2)
        cg.addWidget(self.spin_q4, 3, 3)
        btn_add = QPushButton("➕ Add Gate")
        btn_add.setStyleSheet(self._accent("#238636"))
        btn_add.clicked.connect(self._add_gate)
        btn_undo = QPushButton("↩ Undo")
        btn_undo.setStyleSheet(self._accent("#2d5a8e"))
        btn_undo.clicked.connect(self._undo)
        cg.addWidget(btn_add, 3, 0, 1, 2)
        cg.addWidget(btn_undo, 3, 4, 1, 2)
        cg.addWidget(QLabel("Example:"), 4, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(SQASM_EXAMPLES.keys()))
        cg.addWidget(self.combo_preset, 4, 1, 1, 2)
        btn_preset = QPushButton("📥 Load Program")
        btn_preset.setStyleSheet(self._accent("#6a4c93"))
        btn_preset.clicked.connect(self._load_example)
        cg.addWidget(btn_preset, 4, 3, 1, 2)
        self.chk_auto = QCheckBox("Auto-run")
        self.chk_noise = QCheckBox("Noise")
        self.sld_noise = QSlider(Qt.Horizontal)
        self.sld_noise.setRange(0, 50)
        self.sld_noise.setValue(5)
        self.lbl_noise_val = QLabel("0.05")
        self.sld_noise.valueChanged.connect(lambda v: self.lbl_noise_val.setText(f"{v/100:.2f}"))
        cg.addWidget(self.chk_auto, 5, 0, 1, 2)
        cg.addWidget(self.chk_noise, 5, 2)
        cg.addWidget(self.sld_noise, 5, 3, 1, 2)
        cg.addWidget(self.lbl_noise_val, 5, 5)
        self.lbl_metrics = QLabel("Gates: 0 | Depth: 0")
        self.lbl_metrics.setStyleSheet("color:#8be9fd; font-family:Consolas;")
        cg.addWidget(self.lbl_metrics, 6, 0, 1, 6)
        ll.addWidget(ctrl)

        self.angle_box = QGroupBox("Interactive Angle (×π rad)")
        al = QGridLayout(self.angle_box)
        self.lbl_active_gate = QLabel("Editing: None")
        self.lbl_active_gate.setStyleSheet("color: #8be9fd; font-weight: bold;")
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(-400, 400)
        self.angle_slider.setValue(50)
        self.angle_slider.valueChanged.connect(self._on_angle_slider_changed)
        
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-4.0, 4.0)
        self.angle_spin.setSingleStep(0.05)
        self.angle_spin.setDecimals(4)
        self.angle_spin.valueChanged.connect(self._on_angle_spin_changed)
        
        al.addWidget(self.lbl_active_gate, 0, 0, 1, 3)
        al.addWidget(QLabel("θ:"), 1, 0)
        al.addWidget(self.angle_slider, 1, 1)
        al.addWidget(self.angle_spin, 1, 2)
        ll.addWidget(self.angle_box)

        self.circuit = CircuitWidget()
        self.circuit.gate_selected.connect(self._gate_sel)
        self.circuit.circuit_changed.connect(self._on_circuit_changed)
        scroll = QScrollArea()
        scroll.setWidget(self.circuit)
        scroll.setWidgetResizable(False)
        ll.addWidget(scroll, 1)

        a1 = QHBoxLayout()
        self.btn_run = QPushButton("▶  Run")
        self.btn_run.setStyleSheet(self._accent("#238636"))
        self.btn_run.clicked.connect(self._run)
        a1.addWidget(self.btn_run)
        self.btn_step_b = QPushButton("⏮ Step◀")
        self.btn_step_b.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_step_b.clicked.connect(self._step_back)
        a1.addWidget(self.btn_step_b)
        self.btn_step_f = QPushButton("Step▶ ⏭")
        self.btn_step_f.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_step_f.clicked.connect(self._step_fwd)
        a1.addWidget(self.btn_step_f)
        self.btn_meas = QPushButton("🎲 Measure")
        self.btn_meas.setStyleSheet(self._accent("#8b3a3a"))
        self.btn_meas.clicked.connect(self._measure)
        a1.addWidget(self.btn_meas)
        ll.addLayout(a1)

        a3 = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setStyleSheet(self._accent("#8b3a3a"))
        self.btn_play.clicked.connect(self._toggle_playback)
        a3.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet(self._accent("#555"))
        self.btn_stop.clicked.connect(self._stop_playback)
        a3.addWidget(self.btn_stop)
        
        a3.addWidget(QLabel("Speed:"))
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(100, 2000)
        self.sld_speed.setValue(500)
        self.sld_speed.setInvertedAppearance(True)
        self.sld_speed.valueChanged.connect(lambda v: self.playback_timer.setInterval(v))
        a3.addWidget(self.sld_speed)
        ll.addLayout(a3)

        a2 = QHBoxLayout()
        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_reset.clicked.connect(self._reset_state)
        a2.addWidget(self.btn_reset)
        self.btn_clear = QPushButton("✖ Clear")
        self.btn_clear.setStyleSheet(self._accent("#555"))
        self.btn_clear.clicked.connect(self._clear_circuit)
        a2.addWidget(self.btn_clear)
        self.btn_qasm = QPushButton("📤 QASM")
        self.btn_qasm.setStyleSheet(self._accent("#6a4c93"))
        self.btn_qasm.clicked.connect(self._export_qasm)
        a2.addWidget(self.btn_qasm)
        self.btn_del = QPushButton("🗑 Remove")
        self.btn_del.setStyleSheet(self._accent("#555"))
        self.btn_del.clicked.connect(self._del_gate)
        a2.addWidget(self.btn_del)
        ll.addLayout(a2)

        main_layout.addWidget(left, 3)

        # ─── RIGHT PANEL (Tabs) ───
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        self.tabs = QTabWidget()

        self.tab_prog = QWidget()
        tpl = QVBoxLayout(self.tab_prog)
        eh = QHBoxLayout()
        eh.addWidget(QLabel("<b>SQASM Program:</b>"))
        self.btn_run_prog = QPushButton("▶  Run Program  (Ctrl+Enter)")
        self.btn_run_prog.setStyleSheet(self._accent("#238636"))
        self.btn_run_prog.clicked.connect(self._run_program)
        eh.addWidget(self.btn_run_prog)
        btn_clear_ed = QPushButton("🗑 Clear Editor")
        btn_clear_ed.setStyleSheet(self._accent("#555"))
        btn_clear_ed.clicked.connect(lambda: self.editor.clear())
        eh.addWidget(btn_clear_ed)
        tpl.addLayout(eh)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setPlaceholderText("# Write your quantum program here\nqubits 2\nh 0\ncnot 0, 1\nmeasure\n")
        self.highlighter = SqasmHighlighter(self.editor.document())
        tpl.addWidget(self.editor, 1)

        cg2 = QGroupBox("Output Console")
        cl = QVBoxLayout(cg2)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console.setMaximumHeight(180)
        cl.addWidget(self.console)
        tpl.addWidget(cg2)

        ref = QGroupBox("SQASM Quick Reference")
        rl2 = QVBoxLayout(ref)
        ref_txt = QLabel(
            "<b>Commands:</b> <code>qubits N</code> · <code>measure</code> · <code>reset</code> · <code>barrier</code><br>"
            "<b>Gates:</b> <code>h x y z s t</code> · <code>cnot/cx cz swap ccx/toffoli</code><br>"
            "<b>Rotation:</b> <code>rx(angle) ry(angle) rz(angle) qubit</code><br>"
            "<b>Controlled:</b> <code>ch cs ct crx cry crz ctrl, tgt</code><br>"
            "<b>Syntax:</b> <code>gate q1, q2, ...</code> · Angles in radians · <code>#</code> comments"
        )
        ref_txt.setWordWrap(True)
        ref_txt.setStyleSheet("color:#bac2de; font-size:11px;")
        rl2.addWidget(ref_txt)
        tpl.addWidget(ref)
        self.tabs.addTab(self.tab_prog, "💻 Program")

        tab_vis = QWidget()
        tvl = QVBoxLayout(tab_vis)
        bloch_box = QGroupBox("Bloch Sphere  (Drag to rotate, Double-click to reset)")
        bl = QVBoxLayout(bloch_box)
        bh2 = QHBoxLayout()
        bh2.addWidget(QLabel("Qubit:"))
        self.spin_bloch = QSpinBox()
        self.spin_bloch.setRange(0, 11)
        self.spin_bloch.valueChanged.connect(self._update_bloch)
        bh2.addWidget(self.spin_bloch)
        bh2.addStretch()
        bl.addLayout(bh2)
        self.bloch = BlochWidget()
        bl.addWidget(self.bloch)
        tvl.addWidget(bloch_box)
        self.hist = HistogramWidget()
        tvl.addWidget(self.hist, 1)
        self.tabs.addTab(tab_vis, "🎨 Visual")

        tab_state = QWidget()
        tsl = QVBoxLayout(tab_state)
        sv_box = QGroupBox("State Vector  |ψ⟩")
        sl = QVBoxLayout(sv_box)
        self.state_table = QTableWidget()
        self.state_table.setColumnCount(4)
        self.state_table.setHorizontalHeaderLabels(["Basis", "Amplitude (a + bi)", "Probability", "Phase (rad)"])
        self.state_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.state_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.state_table.setAlternatingRowColors(True)
        self.state_table.setMaximumHeight(180)
        sl.addWidget(self.state_table)
        tsl.addWidget(sv_box)

        exp_box = QGroupBox("Qubit Observables  ⟨X⟩, ⟨Y⟩, ⟨Z⟩")
        el = QVBoxLayout(exp_box)
        self.exp_table = QTableWidget()
        self.exp_table.setColumnCount(4)
        self.exp_table.setHorizontalHeaderLabels(["Qubit", "⟨X⟩", "⟨Y⟩", "⟨Z⟩"])
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.exp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.exp_table.setMaximumHeight(120)
        el.addWidget(self.exp_table)
        tsl.addWidget(exp_box)

        self.entropy_w = EntropyWidget()
        tsl.addWidget(self.entropy_w)
        self.density_w = DensityMatrixWidget()
        tsl.addWidget(self.density_w, 1)
        self.tabs.addTab(tab_state, "📊 State")

        tab_unit = QWidget()
        tul = QVBoxLayout(tab_unit)
        u_box = QGroupBox("Full Circuit Unitary (U)")
        ul = QVBoxLayout(u_box)
        self.unitary_text = QTextEdit()
        self.unitary_text.setReadOnly(True)
        self.unitary_text.setFont(QFont("Consolas", 10))
        ul.addWidget(self.unitary_text)
        tul.addWidget(u_box)
        self.tabs.addTab(tab_unit, "🧮 Unitary")

        tab_gate = QWidget()
        tgl = QVBoxLayout(tab_gate)
        gi_box = QGroupBox("Gate Matrix")
        gil = QVBoxLayout(gi_box)
        self.gate_info_text = QTextEdit()
        self.gate_info_text.setReadOnly(True)
        self.gate_info_text.setFont(QFont("Consolas", 10))
        gil.addWidget(self.gate_info_text)
        tgl.addWidget(gi_box)
        self.tabs.addTab(tab_gate, "🔬 Gate Info")

        tab_meas = QWidget()
        tml = QVBoxLayout(tab_meas)
        m_box = QGroupBox("Measurement Counts")
        ml = QVBoxLayout(m_box)
        self.meas_text = QTextEdit()
        self.meas_text.setReadOnly(True)
        self.meas_text.setFont(QFont("Consolas", 10))
        ml.addWidget(self.meas_text)
        tml.addWidget(m_box)
        self.tabs.addTab(tab_meas, "🎲 Measure")

        rl.addWidget(self.tabs)
        main_layout.addWidget(right, 2)

        self.statusBar().showMessage("Ready — Load an example or write a program")
        self.statusBar().setStyleSheet("color:#8be9fd; background:#1a1c2a;")

    @staticmethod
    def _accent(bg):
        return (f"QPushButton{{background:{bg};color:#fff;font-weight:bold;padding:7px 10px;border-radius:4px;}}"
                f"QPushButton:hover{{opacity:0.85;}}")

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #1a1c2a; color: #cdd6f4; }
            QMenuBar { background: #12131e; color: #cdd6f4; }
            QMenuBar::item:selected { background: #3a3d52; }
            QMenu { background: #12131e; color: #cdd6f4; border: 1px solid #3a3d52; }
            QMenu::item:selected { background: #3a3d52; }
            QGroupBox { border: 1px solid #3a3d52; border-radius: 6px; margin-top: 12px; padding-top: 16px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { background: #2a2d40; border: 1px solid #3a3d52; border-radius: 4px; padding: 5px 8px; color: #cdd6f4; }
            QPushButton:hover { background: #3a3d52; }
            QComboBox, QSpinBox, QDoubleSpinBox { background: #2a2d40; border: 1px solid #3a3d52; border-radius: 4px; padding: 3px; color: #cdd6f4; }
            QTextEdit, QPlainTextEdit { background: #12131e; border: 1px solid #3a3d52; color: #cdd6f4; }
            QTableWidget { background: #12131e; border: 1px solid #3a3d52; color: #cdd6f4; gridline-color: #2a2d40; }
            QTableWidget::item:selected { background: #3a3d52; }
            QHeaderView::section { background: #2a2d40; color: #cdd6f4; border: 1px solid #3a3d52; padding: 4px; font-weight: bold; }
            QScrollArea { border: none; }
            QLabel { color: #cdd6f4; }
            QSplitter::handle { background: #3a3d52; width: 3px; }
            QTabWidget::pane { border: 1px solid #3a3d52; }
            QTabBar::tab { background: #2a2d40; color: #cdd6f4; padding: 6px 14px; border: 1px solid #3a3d52; border-bottom: none; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: #3a3d52; color: #fff; }
            QCheckBox { color: #cdd6f4; }
            QSlider::groove:horizontal { height: 6px; background: #2a2d40; border-radius: 3px; }
            QSlider::handle:horizontal { background: #607090; width: 14px; margin: -4px 0; border-radius: 7px; }
        """)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Delete"), self, self._del_gate)
        QShortcut(QKeySequence("Escape"), self, self._deselect_palette)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo)
        QShortcut(QKeySequence("Ctrl+R"), self, self._run)
        QShortcut(QKeySequence("Ctrl+M"), self, self._measure)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self._reset_state)
        QShortcut(QKeySequence("Right"), self, self._step_fwd)
        QShortcut(QKeySequence("Left"), self, self._step_back)
        QShortcut(QKeySequence("Space"), self, self._toggle_playback)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._run_program)

    # ───────────────────────────────────────────────────────────
    #  Playback & File I/O
    # ───────────────────────────────────────────────────────────
    def _toggle_playback(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            self.btn_play.setText("▶ Play")
        else:
            if self.step_idx < 0 or self.step_idx >= len(self.circuit.gates):
                self.step_idx = 0
            self.playback_timer.start()
            self.btn_play.setText("⏸ Pause")

    def _stop_playback(self):
        self.playback_timer.stop()
        self.btn_play.setText("▶ Play")
        self.step_idx = -1
        self._run()

    def _playback_step(self):
        if self.step_idx < len(self.circuit.gates):
            self.step_idx += 1
            self._run()
            if self.step_idx >= len(self.circuit.gates):
                self.playback_timer.stop()
                self.btn_play.setText("▶ Play")
        else:
            self.playback_timer.stop()
            self.btn_play.setText("▶ Play")

    def _open_sqasm(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open SQASM", "", "SQASM (*.qasm *.txt);;All (*)")
        if path:
            with open(path, 'r') as f:
                self.editor.setPlainText(f.read())
            self.console.setText(f"📥 Loaded SQASM from {path}")
            self.tabs.setCurrentWidget(self.tab_prog)

    def _save_sqasm_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save SQASM", "circuit.qasm", "SQASM (*.qasm);;All (*)")
        if path:
            with open(path, 'w') as f:
                f.write(self.editor.toPlainText())
            self.statusBar().showMessage(f"Saved SQASM to {path}")

    def _copy_sqasm(self):
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.statusBar().showMessage("SQASM copied to clipboard!")

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Circuit as PNG", "circuit.png", "PNG Image (*.png)")
        if path:
            cols = self.circuit.depth()
            min_w = self.circuit.ML + cols * self.circuit.CW + 50
            self.circuit.setMinimumWidth(min_w)
            pixmap = self.circuit.grab()
            pixmap.save(path, "PNG")
            self.statusBar().showMessage(f"Saved PNG to {path}")

    def _export_to_sqasm(self):
        lines = [f"qubits {self.n_qubits}", ""]
        for g in self.circuit.gates:
            if g.gtype == "M": continue
            name = g.gtype.lower()
            if g.controlled: name = "c" + name
            qubits_str = ", ".join(map(str, g.qubits))
            if g.angle is not None:
                lines.append(f"{name}({g.angle/np.pi:.4f}*pi) {qubits_str}")
            else:
                lines.append(f"{name} {qubits_str}")
        lines.append("measure")
        self.editor.setPlainText("\n".join(lines))
        self.tabs.setCurrentWidget(self.tab_prog)
        self.console.setText("✅ Exported visual circuit to SQASM editor.")

    def _parse_sqasm(self, text):
        n_qubits = None
        gates = []
        do_measure = False
        errors = []
        for lineno, raw_line in enumerate(text.split('\n'), 1):
            line = raw_line.strip()
            if not line or line.startswith('#') or line.startswith('//'): continue
            if '#' in line: line = line[:line.index('#')].strip()
            if '//' in line: line = line[:line.index('//')].strip()
            if not line: continue
            m = re.match(r'^qubits\s+(\d+)$', line, re.I)
            if m: n_qubits = int(m.group(1)); continue
            if re.match(r'^measure$', line, re.I): do_measure = True; continue
            if re.match(r'^reset$', line, re.I): gates.append(CircuitGate("__reset__", ())); continue
            if re.match(r'^barrier$', line, re.I): continue
            m = re.match(r'^([a-zA-Z]+)(?:\(([^)]+)\))?\s+(.+)$', line)
            if not m:
                errors.append(f"Line {lineno}: Syntax error: '{raw_line.strip()}'")
                continue
            raw_gate = m.group(1).lower()
            angle_str = m.group(2)
            qubits_str = m.group(3)
            controlled = False
            gate_key = raw_gate
            base_map = {'ch': 'H', 'cs': 'S', 'ct': 'T', 'crx': 'RX', 'cry': 'RY', 'crz': 'RZ'}
            if gate_key in base_map:
                controlled = True
                resolved = base_map[gate_key]
            elif gate_key in GATE_ALIASES:
                resolved = GATE_ALIASES[gate_key]
            else:
                resolved = None
                for g in ALL_STANDARD_GATES:
                    if g.lower() == gate_key:
                        resolved = g
                        break
                if not resolved:
                    errors.append(f"Line {lineno}: Unknown gate '{raw_gate}'")
                    continue
            angle = None
            if angle_str is not None:
                try:
                    a = angle_str.strip().replace('pi', str(np.pi)).replace('π', str(np.pi))
                    angle = float(eval(a, {"__builtins__": {}}, {"pi": np.pi}))
                except Exception:
                    errors.append(f"Line {lineno}: Invalid angle '{angle_str}'")
                    continue
            elif resolved in ROTATION_GATES:
                errors.append(f"Line {lineno}: {resolved} requires angle")
                continue
            try:
                qubits = tuple(int(q.strip()) for q in qubits_str.split(','))
            except Exception:
                errors.append(f"Line {lineno}: Invalid qubits '{qubits_str}'")
                continue
            expected_nq = (3 if resolved in THREE_QUBIT_GATES else (2 if (resolved in TWO_QUBIT_GATES or controlled) else 1))
            if len(qubits) != expected_nq:
                errors.append(f"Line {lineno}: {resolved} expects {expected_nq} qubit(s), got {len(qubits)}")
                continue
            if len(qubits) != len(set(qubits)):
                errors.append(f"Line {lineno}: Duplicate qubit")
                continue
            gates.append(CircuitGate(resolved, qubits, angle=angle, controlled=controlled))
        return n_qubits, gates, do_measure, errors

    def _run_program(self):
        text = self.editor.toPlainText()
        if not text.strip():
            self.console.setText("⚠ No program to run.")
            return
        n_qubits, gates, do_measure, errors = self._parse_sqasm(text)
        if errors:
            self.console.setText("❌ Parse Errors:\n\n" + "\n".join(errors))
            return
        if n_qubits is None:
            max_q = 0
            for g in gates:
                if g.qubits: max_q = max(max_q, max(g.qubits))
            n_qubits = max_q + 1 if gates else 2
        if n_qubits != self.n_qubits:
            self.spin_nq.setValue(n_qubits)
        self.circuit.gates.clear()
        self.circuit.sel = -1
        self.circuit.step = -1
        visual_gates = [g for g in gates if g.gtype != "__reset__"]
        for g in visual_gates:
            self.circuit.add_gate(g)
        self._update_metrics()
        self.sim = QuantumSimulator(self.n_qubits)
        noise_p = self.sld_noise.value() / 100 if self.chk_noise.isChecked() else 0
        output_lines = [f"▶ Running program with {self.n_qubits} qubits...", f"  Gates: {len(visual_gates)}  |  Depth: {self.circuit.depth()}"]
        for g in gates:
            if g.gtype == "__reset__":
                self.sim.reset()
                output_lines.append("  ⏮ State reset to |0...0⟩")
                continue
            try:
                mat = get_gate_matrix(g)
                self.sim.apply_gate(mat, g.qubits)
                self.sim.apply_noise(noise_p)
            except Exception as e:
                output_lines.append(f"❌ Error: {gate_label(g)}: {e}")
                self.console.setText("\n".join(output_lines))
                return
        self._update_displays()
        if do_measure:
            shots = 2048
            counts = self.sim.measure_all(shots)
            self.hist.set_measurements(counts, shots)
            output_lines.append(f"\n🎲 Measurement ({shots} shots):")
            output_lines.append("─" * 45)
            for k, v in sorted(counts.items(), key=lambda x: -x[1]):
                bar = "█" * (v * 30 // shots)
                output_lines.append(f"  |{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}")
            txt = f"Measurement ({shots} shots)\n{'─'*40}\n"
            for k, v in sorted(counts.items(), key=lambda x: -x[1]):
                bar = "█" * (v * 30 // shots)
                txt += f"|{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}\n"
            self.meas_text.setText(txt)
        else:
            output_lines.append("\n✅ Program executed (no measurement).")
            output_lines.append("  Add 'measure' to your program or click 🎲 Measure.")
        self.console.setText("\n".join(output_lines))
        self.statusBar().showMessage(f"Program executed — {len(visual_gates)} gates")

    def _load_example(self):
        name = self.combo_preset.currentText()
        if name in SQASM_EXAMPLES:
            self.editor.setPlainText(SQASM_EXAMPLES[name])
            self.console.setText(f"📥 Loaded: {name}")

    # ───────────────────────────────────────────────────────────
    #  Interactive Angle & Palette
    # ───────────────────────────────────────────────────────────
    def _on_palette_gate(self):
        sender = self.sender()
        if not sender.isChecked():
            self.circuit.cancel_placing()
            self.theta_widget.hide()
            self.lbl_active_gate.setText("Editing: None")
            return
        for btn in self.gate_buttons:
            if btn is not sender:
                btn.setChecked(False)
        gtype = sender.property("gate_type")
        params = None
        if gtype in ROTATION_GATES:
            self.theta_widget.show()
            params = self.theta_spin.value() * np.pi
            self.lbl_active_gate.setText(f"Placing: {gtype}")
            val = int(self.theta_spin.value() * 100)
            self.angle_slider.blockSignals(True)
            self.angle_slider.setValue(val)
            self.angle_spin.blockSignals(True)
            self.angle_spin.setValue(val / 100.0)
            self.angle_slider.blockSignals(False)
            self.angle_spin.blockSignals(False)
        else:
            self.theta_widget.hide()
            self.lbl_active_gate.setText("Placing: (Non-rotation)")
        self.circuit.set_placing_gate(gtype, params=params)
        self.statusBar().showMessage(f"Placing {gtype} — click on qubit wire(s) in the circuit. Press Esc to cancel.")

    def _deselect_palette(self):
        for btn in self.gate_buttons:
            btn.setChecked(False)
        self.circuit.cancel_placing()
        self.theta_widget.hide()
        self.lbl_active_gate.setText("Editing: None")

    def _on_angle_slider_changed(self, v):
        self.angle_spin.blockSignals(True)
        self.angle_spin.setValue(v / 100.0)
        self.angle_spin.blockSignals(False)
        self._apply_interactive_angle(v / 100.0)

    def _on_angle_spin_changed(self, v):
        self.angle_slider.blockSignals(True)
        self.angle_slider.setValue(int(v * 100))
        self.angle_slider.blockSignals(False)
        self._apply_interactive_angle(v)

    def _apply_interactive_angle(self, angle_frac_pi):
        angle = angle_frac_pi * np.pi
        if self.circuit.placing_gate in ROTATION_GATES:
            self.circuit.placing_params = angle
            self.theta_spin.blockSignals(True)
            self.theta_spin.setValue(angle_frac_pi)
            self.theta_spin.blockSignals(False)
            self.circuit.update()
        if 0 <= self.circuit.sel < len(self.circuit.gates):
            g = self.circuit.gates[self.circuit.sel]
            if g.gtype in ROTATION_GATES:
                g.angle = angle
                self.circuit.update()
                if self.chk_auto.isChecked():
                    self._run()
                self._show_gate_info(g)

    # ───────────────────────────────────────────────────────────
    #  Circuit Controls
    # ───────────────────────────────────────────────────────────
    def _on_circuit_changed(self):
        self._update_metrics()
        if self.chk_auto.isChecked():
            self._run()

    def _change_nq(self, n):
        self.n_qubits = n
        self.sim = QuantumSimulator(n)
        self.circuit.set_n_qubits(n)
        for s in (self.spin_q1, self.spin_q2, self.spin_q3, self.spin_q4, self.spin_bloch):
            s.setRange(0, n - 1)
        self._update_displays()

    def _gate_changed(self, name):
        is_rot = name in ROTATION_GATES
        is_3q = name in THREE_QUBIT_GATES
        is_2q = name in TWO_QUBIT_GATES
        is_1q = name in SINGLE_QUBIT_GATES and not is_rot
        self.lbl_angle.setVisible(is_rot)
        self.spin_angle.setVisible(is_rot)
        self.chk_ctrl.setVisible(is_1q or is_rot)
        self.lbl_q1.setVisible(not is_2q and not is_3q)
        self.spin_q1.setVisible(not is_2q and not is_3q)
        show2 = is_2q or is_3q or is_rot
        self.lbl_q2.setVisible(show2)
        self.spin_q2.setVisible(show2)
        self.lbl_q3.setVisible(show2)
        self.spin_q3.setVisible(show2)
        self.lbl_q4.setVisible(is_3q)
        self.spin_q4.setVisible(is_3q)
        if is_2q:
            self.lbl_q2.setText("Ctrl:")
            self.lbl_q3.setText("Tgt:")
        elif is_3q:
            self.lbl_q2.setText("C1:")
            self.lbl_q3.setText("C2:")
            self.lbl_q4.setText("Tgt:")
        else:
            self.lbl_q2.setText("Ctrl:")
            self.lbl_q3.setText("Tgt:")

    def _add_gate(self):
        name = self.combo_gate.currentText()
        ctrl = self.chk_ctrl.isChecked()
        angle = self.spin_angle.value() * np.pi if name in ROTATION_GATES else None
        if name in THREE_QUBIT_GATES:
            c1, c2, t = self.spin_q2.value(), self.spin_q4.value(), self.spin_q3.value()
            if len({c1, c2, t}) < 3:
                QMessageBox.warning(self, "Error", "Qubits must differ")
                return
            g = CircuitGate(name, (c1, c2, t))
        elif name in TWO_QUBIT_GATES:
            c, t = self.spin_q2.value(), self.spin_q3.value()
            if c == t:
                QMessageBox.warning(self, "Error", "Qubits must differ")
                return
            g = CircuitGate(name, (c, t))
        elif ctrl:
            c, t = self.spin_q2.value(), self.spin_q3.value()
            if c == t:
                QMessageBox.warning(self, "Error", "Qubits must differ")
                return
            g = CircuitGate(name, (c, t), angle=angle, controlled=True)
        else:
            g = CircuitGate(name, (self.spin_q1.value(),), angle=angle)
        self.history.append([x.copy() for x in self.circuit.gates])
        self.circuit.add_gate(g)
        self._update_metrics()

    def _del_gate(self):
        idx = self.circuit.sel
        if idx >= 0:
            self.history.append([x.copy() for x in self.circuit.gates])
            self.circuit.remove_gate(idx)
            self._update_metrics()

    def _undo(self):
        if self.history:
            self.circuit.gates = self.history.pop()
            self.circuit.sel = -1
            self.circuit.update()
            self._update_metrics()
            if self.chk_auto.isChecked():
                self._run()

    def _gate_sel(self, idx):
        if 0 <= idx < len(self.circuit.gates):
            g = self.circuit.gates[idx]
            self._show_gate_info(g)
            if g.gtype in ROTATION_GATES:
                self.lbl_active_gate.setText(f"Editing: {g.gtype} (q{g.qubits[0]})")
                val = int((g.angle or 0) / np.pi * 100)
                self.angle_slider.blockSignals(True)
                self.angle_slider.setValue(val)
                self.angle_spin.blockSignals(True)
                self.angle_spin.setValue(val / 100.0)
                self.angle_slider.blockSignals(False)
                self.angle_spin.blockSignals(False)
            else:
                self.lbl_active_gate.setText("Editing: Non-rotation gate")
        else:
            self.lbl_active_gate.setText("Editing: None")

    def _run(self):
        self.sim = QuantumSimulator(self.n_qubits)
        noise_p = self.sld_noise.value() / 100 if self.chk_noise.isChecked() else 0
        limit = len(self.circuit.gates) if self.step_idx < 0 else self.step_idx
        self.circuit.step = self.step_idx
        self.circuit.update()
        for i, g in enumerate(self.circuit.gates[:limit]):
            try:
                mat = get_gate_matrix(g)
                self.sim.apply_gate(mat, g.qubits)
                self.sim.apply_noise(noise_p)
            except Exception as e:
                self.console.setText(f"Error: {gate_label(g)}: {e}")
                return
        self._update_displays()
        self.statusBar().showMessage(f"Simulated {min(limit, len(self.circuit.gates))}/{len(self.circuit.gates)} gates | Dim={2**self.n_qubits} | Noise={'ON' if noise_p else 'OFF'}")

    def _step_fwd(self):
        if self.step_idx < 0:
            self.step_idx = 1
        elif self.step_idx < len(self.circuit.gates):
            self.step_idx += 1
        if self.step_idx > len(self.circuit.gates):
            self.step_idx = len(self.circuit.gates)
        self._run()

    def _step_back(self):
        if self.step_idx < 0:
            self.step_idx = len(self.circuit.gates) - 1
        elif self.step_idx > 0:
            self.step_idx -= 1
        else:
            self.step_idx = 0
        self._run()

    def _measure(self):
        self._run()
        shots = 2048
        counts = self.sim.measure_all(shots)
        self.hist.set_measurements(counts, shots)
        txt = f"Measurement ({shots} shots)\n{'─'*40}\n"
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            bar = "█" * (v * 30 // shots)
            txt += f"|{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}\n"
        self.meas_text.setText(txt)

    def _reset_state(self):
        self.sim.reset()
        self.step_idx = -1
        self.circuit.step = -1
        self.circuit.update()
        self.hist.clear_measurements()
        self.meas_text.clear()
        self._update_displays()

    def _clear_circuit(self):
        self.history.append([x.copy() for x in self.circuit.gates])
        self.circuit.gates.clear()
        self.circuit.sel = -1
        self.circuit.step = -1
        self.circuit.update()
        self._reset_state()
        self._update_metrics()

    def _export_qasm(self):
        lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', "", f"qreg q[{self.n_qubits}];", f"creg c[{self.n_qubits}];", ""]
        qasm_gate = {"H": "h", "X": "x", "Y": "y", "Z": "z", "S": "s", "T": "t", "RX": "rx", "RY": "ry", "RZ": "rz", "CNOT": "cx", "CZ": "cz", "SWAP": "swap", "CCX": "ccx"}
        for g in self.circuit.gates:
            gn = qasm_gate.get(g.gtype, g.gtype.lower())
            if g.controlled and g.gtype not in TWO_QUBIT_GATES:
                gn = "c" + gn
            qs = ",".join(f"q[{q}]" for q in g.qubits)
            if g.gtype in ROTATION_GATES and g.angle is not None:
                lines.append(f"{gn}({g.angle/np.pi:.4f}*pi) {qs};")
            else:
                lines.append(f"{gn} {qs};")
        lines.append("")
        for q in range(self.n_qubits):
            lines.append(f"measure q[{q}] -> c[{q}];")
        text = "\n".join(lines)

        dlg = QDialog(self)
        dlg.setWindowTitle("QASM Export")
        dlg.resize(600, 500)
        dl = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setFont(QFont("Consolas", 11))
        te.setPlainText(text)
        dl.addWidget(te)
        bb = QHBoxLayout()
        btnSave = QPushButton("💾 Save")
        btnSave.setStyleSheet(self._accent("#238636"))
        btnSave.clicked.connect(lambda: self._save_qasm(text, dlg))
        btnClose = QPushButton("Close")
        btnClose.setStyleSheet(self._accent("#555"))
        btnClose.clicked.connect(dlg.close)
        bb.addWidget(btnSave)
        bb.addWidget(btnClose)
        dl.addLayout(bb)
        dlg.exec()

    def _save_qasm(self, text, parent):
        path, _ = QFileDialog.getSaveFileName(parent, "Save QASM", "circuit.qasm", "QASM (*.qasm);;All (*)")
        if path:
            with open(path, 'w') as f:
                f.write(text)
            self.statusBar().showMessage(f"Saved QASM to {path}")

    def _update_bloch(self):
        q = self.spin_bloch.value()
        if q < self.n_qubits:
            self.bloch.set_vector(self.sim.bloch_vector(q))

    def _show_gate_info(self, gate):
        try:
            mat = get_gate_matrix(gate)
            lines = [f"Gate: {gate_label(gate)}", f"Qubits: {gate.qubits}  |  Size: {mat.shape[0]}×{mat.shape[1]}"]
            if gate.angle is not None:
                lines.append(f"Angle: {gate.angle/np.pi:.4g}π rad")
            lines.append("─" * 50)
            for i in range(mat.shape[0]):
                row = "  ".join(f"{mat[i,j].real:+.4f}{mat[i,j].imag:+.4f}j" for j in range(mat.shape[1]))
                lines.append(row)
            self.gate_info_text.setText("\n".join(lines))
        except Exception as e:
            self.gate_info_text.setText(f"Error: {e}")

    def _update_metrics(self):
        n = len(self.circuit.gates)
        d = self.circuit.depth()
        n1 = sum(1 for g in self.circuit.gates if gate_nqubits(g) == 1)
        n2 = sum(1 for g in self.circuit.gates if gate_nqubits(g) == 2)
        n3 = sum(1 for g in self.circuit.gates if gate_nqubits(g) == 3)
        self.lbl_metrics.setText(f"Gates: {n} | Depth: {d} | 1q: {n1}  2q: {n2}  3q: {n3}")

    def _update_unitary(self):
        if self.n_qubits > 5:
            self.unitary_text.setText("Circuit unitary calculation limited to ≤5 qubits for performance.")
            return
        dim = 1 << self.n_qubits
        U = np.zeros((dim, dim), dtype=complex)
        for i in range(dim):
            sim = QuantumSimulator(self.n_qubits)
            sim.state = np.zeros(dim, dtype=complex)
            sim.state[i] = 1.0
            for g in self.circuit.gates:
                if g.gtype == "M": continue
                mat = get_gate_matrix(g)
                sim.apply_gate(mat, g.qubits)
            U[:, i] = sim.state
        
        lines = [f"Full Circuit Unitary Matrix ({dim}×{dim}):", "─" * 60]
        for r in range(dim):
            row_str = "  ".join(f"{U[r,c].real:+.3f}{U[r,c].imag:+.3f}i" for c in range(dim))
            lines.append(f"|{r:0{self.n_qubits}b}⟩ " + row_str)
        self.unitary_text.setText("\n".join(lines))

    def _update_displays(self):
        n = self.n_qubits
        dim = 1 << n
        self.state_table.setRowCount(dim)
        probs = self.sim.probabilities()
        for i in range(dim):
            basis = f"|{i:0{n}b}⟩"
            amp = self.sim.state[i]
            prob = probs[i]
            phase = np.angle(amp) if abs(amp) > 1e-10 else 0.0
            if abs(amp) > 1e-10:
                re_s = f"{amp.real:+.4f}"
                im_s = f"{abs(amp.imag):.4f}"
                sign = "+" if amp.imag >= 0 else "-"
                amp_str = f"{re_s} {sign} {im_s}i"
            else:
                amp_str = "0"
            prob_str = f"{prob*100:.2f}%"
            phase_str = f"{phase:.4f}" if abs(amp) > 1e-10 else "—"

            self.state_table.setItem(i, 0, QTableWidgetItem(basis))
            self.state_table.setItem(i, 1, QTableWidgetItem(amp_str))
            prob_item = QTableWidgetItem(prob_str)
            if prob > 0.5:
                prob_item.setForeground(QColor("#22c55e"))
            elif prob > 1e-6:
                prob_item.setForeground(QColor("#e2e8f0"))
            else:
                prob_item.setForeground(QColor("#64748b"))
            self.state_table.setItem(i, 2, prob_item)
            self.state_table.setItem(i, 3, QTableWidgetItem(phase_str))

            if abs(amp) > 1e-6:
                hue = int((phase + np.pi) / (2 * np.pi) * 360) % 360
                tint = QColor.fromHsv(hue, 60, 40, 80)
                for col in range(4):
                    item = self.state_table.item(i, col)
                    if item: item.setBackground(tint)

        self.exp_table.setRowCount(n)
        for q in range(n):
            x, y, z = self.sim.expectation_values(q)
            self.exp_table.setItem(q, 0, QTableWidgetItem(f"q{q}"))
            self.exp_table.setItem(q, 1, QTableWidgetItem(f"{x:+.4f}"))
            self.exp_table.setItem(q, 2, QTableWidgetItem(f"{y:+.4f}"))
            self.exp_table.setItem(q, 3, QTableWidgetItem(f"{z:+.4f}"))
            for col, val in [(1, x), (2, y), (3, z)]:
                item = self.exp_table.item(q, col)
                if abs(val) > 0.99:
                    item.setForeground(QColor("#22c55e"))
                elif abs(val) > 1e-6:
                    item.setForeground(QColor("#e2e8f0"))
                else:
                    item.setForeground(QColor("#64748b"))

        self.hist.set_probabilities(probs, n)
        self._update_bloch()
        self.entropy_w.set_entropies([self.sim.entanglement_entropy(q) for q in range(n)])
        if n <= 6:
            self.density_w.set_matrix(self.sim.density_matrix())
        else:
            self.density_w.set_matrix(None)

        if 0 <= self.circuit.sel < len(self.circuit.gates):
            self._show_gate_info(self.circuit.gates[self.circuit.sel])
        
        self._update_unitary()
        self._update_metrics()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
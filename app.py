#!/usr/bin/env python3
"""
Quantum Computer Simulator — PySide6 + NumPy  (40 Presets Edition)
Full SQASM Program IDE with 40 example programs covering basics,
gates, entanglement, algorithms, communication, error correction, and more.
"""

import sys, math, copy, re
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QPlainTextEdit, QScrollArea, QSplitter,
    QMessageBox, QSizePolicy, QCheckBox, QSlider, QTabWidget, QFileDialog,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QRadialGradient, QShortcut, QKeySequence,
    QTextCharFormat, QSyntaxHighlighter, QTextDocument,
)

# ═══════════════════════════════════════════════════════════════
#  Gate definitions
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
    "H":QColor(70,140,200), "X":QColor(220,80,80), "Y":QColor(80,200,100),
    "Z":QColor(220,200,60), "S":QColor(180,100,220), "T":QColor(210,150,80),
    "RX":QColor(220,100,100), "RY":QColor(100,200,100), "RZ":QColor(100,150,255),
    "CNOT":QColor(100,210,255), "CZ":QColor(220,220,60), "SWAP":QColor(220,140,60),
    "CCX":QColor(255,180,80),
}

GATE_ALIASES = {
    "h":"H","x":"X","y":"Y","z":"Z","s":"S","t":"T",
    "rx":"RX","ry":"RY","rz":"RZ",
    "cnot":"CNOT","cx":"CNOT","cz":"CZ","swap":"SWAP",
    "ccx":"CCX","toffoli":"CCX",
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
    if gate.controlled:
        a = f"({gate.angle/np.pi:.2g}π)" if gate.angle else ""
        return f"C-{gate.gtype}{a}"
    if gate.gtype in ROTATION_GATES and gate.angle is not None:
        return f"{gate.gtype}({gate.angle/np.pi:.2g}π)"
    return gate.gtype

class CircuitGate:
    def __init__(self, gtype, qubits, angle=None, controlled=False):
        self.gtype=gtype; self.qubits=tuple(qubits)
        self.angle=angle; self.controlled=controlled
    def copy(self):
        return CircuitGate(self.gtype, self.qubits, self.angle, self.controlled)

class QuantumSimulator:
    def __init__(self, n=4): self.n=n; self.reset()
    def reset(self): self.state=np.zeros(1<<self.n,dtype=complex); self.state[0]=1.0
    def apply_gate(self, matrix, qubits):
        n,k=self.n,len(qubits); t=self.state.reshape([2]*n)
        axes=[n-1-q for q in qubits]; rest=[i for i in range(n) if i not in axes]
        t=np.transpose(t,axes+rest); t=(matrix@t.reshape(2**k,-1)).reshape([2]*n)
        inv=[0]*n
        for i,p in enumerate(axes+rest): inv[p]=i
        t=np.transpose(t,inv); self.state=t.reshape(-1)
    def apply_noise(self, prob):
        if prob<=0: return
        paulis=[GATE_MATRICES["X"],GATE_MATRICES["Y"],GATE_MATRICES["Z"]]
        for q in range(self.n):
            if np.random.random()<prob: self.apply_gate(paulis[np.random.randint(3)],(q,))
    def probabilities(self): p=np.abs(self.state)**2; return p/p.sum()
    def measure_all(self, shots=2048):
        p=self.probabilities(); samples=np.random.choice(len(p),size=shots,p=p)
        counts={}
        for s in samples: k=format(s,f"0{self.n}b"); counts[k]=counts.get(k,0)+1
        return dict(sorted(counts.items()))
    def reduced_density(self, qubit):
        t=self.state.reshape([2]*self.n); t=np.moveaxis(t,self.n-1-qubit,0).reshape(2,-1)
        return t@t.conj().T
    def bloch_vector(self, qubit):
        r=self.reduced_density(qubit)
        return np.array([2*r[0,1].real,-2*r[0,1].imag,(r[0,0]-r[1,1]).real])
    def entanglement_entropy(self, qubit):
        r=self.reduced_density(qubit); eigs=np.linalg.eigvalsh(r)
        eigs=eigs[eigs>1e-14]; return float(-np.sum(eigs*np.log2(eigs)))
    def density_matrix(self): return np.outer(self.state,self.state.conj())

# ═══════════════════════════════════════════════════════════════
#  40 SQASM Example Presets
# ═══════════════════════════════════════════════════════════════
SQASM_EXAMPLES = {

# ── SINGLE-QUBIT BASICS ──────────────────────────────────────

"01. Bit Flip (X Gate)": """\
# X Gate: Flips |0⟩ → |1⟩ and |1⟩ → |0⟩
# The quantum NOT gate (Pauli-X)
qubits 1
x 0
measure
""",

"02. Hadamard Superposition": """\
# Hadamard Gate: Creates |+⟩ = (|0⟩+|1⟩)/√2
# 50/50 probability — quantum coin flip
qubits 1
h 0
measure
""",

"03. Phase Gate Demo": """\
# Z gate flips the phase of |1⟩
# H converts phase difference → measurement difference
# This circuit: H-X-Z-H measures |1⟩ (phase flip visible)
qubits 1
x 0
z 0
h 0
measure
""",

"04. Rotation Gate Tour": """\
# Rotation gates rotate the Bloch vector by an angle
# RX(θ) = around X-axis, RY(θ) = around Y, RZ(θ) = around Z
qubits 3
# Q0: rotate around X by π/2
rx(1.5708) 0
# Q1: rotate around Y by π/3
ry(1.0472) 1
# Q2: rotate around Z by π/4 (invisible without H)
rz(0.7854) 2
h 2
measure
""",

"05. Bloch Sphere States": """\
# Prepare qubits at 6 key points on the Bloch sphere
# Check the Bloch Sphere tab after running!
qubits 6

# |0⟩ — North pole (qubit 0, default)

# |1⟩ — South pole
x 1

# |+⟩ — +X equator
h 2

# |−⟩ — -X equator  
x 3
h 3

# |+i⟩ — +Y equator
ry(1.5708) 4

# |−i⟩ — -Y equator
ry(-1.5708) 5

measure
""",

"06. Superposition + Interference": """\
# Two Hadamards cancel out: H·H = I
# Quantum interference makes the state return to |0⟩
qubits 1
h 0
h 0
measure
# Result: always |0⟩ — constructive interference on |0⟩
# destructive interference on |1⟩
""",

"07. Z-H Phase Detection": """\
# Z-H trick: Z gate changes phase, H makes it measurable
# H·Z·H = X, so this is equivalent to just X
qubits 1
h 0
z 0
h 0
measure
# Result: always |1⟩
""",

# ── TWO-QUBIT GATES ──────────────────────────────────────────

"08. CNOT Truth Table": """\
# CNOT: Flips target if control is |1⟩
# Default input |10⟩ → output |11⟩ (target flipped)
# Uncomment lines to try other inputs
qubits 2

# Input |10⟩ (control=1)
x 0

cnot 0, 1
measure
""",

"09. CNOT All Basis States": """\
# Run CNOT on all 4 computational basis states
# Shows the full truth table
qubits 2

# Uncomment ONE input:
# |00⟩ → |00⟩  (no lines needed)
# |01⟩ → |01⟩  x 1
# |10⟩ → |11⟩  x 0
# |11⟩ → |10⟩  x 0
#                x 1

x 0
x 1

cnot 0, 1
measure
""",

"10. SWAP Gate Demo": """\
# SWAP: Exchanges states of two qubits
# |10⟩ → |01⟩ after SWAP
qubits 2
x 0
swap 0, 1
measure
""",

"11. SWAP via CNOTs": """\
# SWAP decomposed into 3 CNOTs
# Equivalent to SWAP but uses only CNOT
qubits 2
x 0
cnot 0, 1
cnot 1, 0
cnot 0, 1
measure
""",

"12. Toffoli (CCX) Gate": """\
# Toffoli: AND gate for quantum computing
# Flips target only if BOTH controls are |1⟩
qubits 3
x 0
x 1
ccx 0, 1, 2
measure
# Expected: |111⟩ (target q2 flipped)
""",

"13. Controlled Gate Zoo": """\
# Controlled gates: CH, CS, CRX
# Gate only activates when control qubit is |1⟩
qubits 4
# Set controls to |1⟩
x 0
x 1
x 2
x 3

# Controlled-H: H on q1 when q0=|1⟩
ch 0, 1

# Controlled-S: S on q2 when q0=|1⟩
cs 0, 2

# Controlled-RX: RX(π/2) on q3 when q1=|1⟩
crx(1.5708) 1, 3

measure
""",

# ── BELL STATES ───────────────────────────────────────────────

"14. Bell |Φ⁺⟩ = (|00⟩+|11⟩)/√2": """\
# Bell State Φ⁺: The most famous entangled pair
# Measuring one qubit instantly determines the other
qubits 2
h 0
cnot 0, 1
measure
# 50% |00⟩, 50% |11⟩ — never |01⟩ or |10⟩
""",

"15. Bell |Φ⁻⟩ = (|00⟩−|11⟩)/√2": """\
# Bell State Φ⁻: Phase-flipped entangled pair
qubits 2
h 0
cnot 0, 1
z 0
measure
# Same measurement stats as Φ⁺, but different phase
""",

"16. Bell |Ψ⁺⟩ = (|01⟩+|10⟩)/√2": """\
# Bell State Ψ⁺: Anti-correlated entangled pair
qubits 2
h 0
cnot 0, 1
x 1
measure
# 50% |01⟩, 50% |10⟩ — always opposite
""",

"17. Bell |Ψ⁻⟩ = (|01⟩−|10⟩)/√2": """\
# Bell State Ψ⁻: Singlet state
# The only antisymmetric Bell state
qubits 2
h 0
cnot 0, 1
x 1
z 0
measure
""",

"18. All 4 Bell States": """\
# Generate any Bell state from 2 classical bits
# Bits (0,0)→Φ⁺  (0,1)→Ψ⁺  (1,0)→Φ⁻  (1,1)→Ψ⁻
# Change the X and Z gates below to select which one
qubits 2

h 0
cnot 0, 1

# Encode classical bits:
# bit1=1 → apply X to q0
x 0
# bit2=1 → apply Z to q0
z 0

measure
# Currently: bits=(1,1) → produces Ψ⁻
""",

# ── MULTI-QUBIT STATES ───────────────────────────────────────

"19. GHZ State (3 qubits)": """\
# GHZ: Greenberger-Horne-Zeilinger
# (|000⟩ + |111⟩)/√2 — strongest quantum correlation
qubits 3
h 0
cnot 0, 1
cnot 0, 2
measure
# 50% |000⟩, 50% |111⟩
""",

"20. GHZ State (5 qubits)": """\
# 5-qubit GHZ: All qubits perfectly correlated
# (|00000⟩ + |11111⟩)/√2
qubits 5
h 0
cnot 0, 1
cnot 0, 2
cnot 0, 3
cnot 0, 4
measure
""",

"21. W-State (3 qubits)": """\
# W-State: (|100⟩+|010⟩+|001⟩)/√3
# Exactly one qubit is |1⟩, but we don't know which
# Different entanglement structure than GHZ
qubits 3
ry(1.911) 0
h 0
cnot 0, 1
cnot 0, 2
x 0
h 0
cnot 0, 1
cnot 0, 2
measure
# ~33% each: |100⟩, |010⟩, |001⟩
""",

"22. Uniform Superposition (4 qubits)": """\
# Equal superposition over all 16 basis states
# Each of the 16 states has probability 1/16 = 6.25%
qubits 4
h 0
h 1
h 2
h 3
measure
""",

"23. Entanglement Chain": """\
# Chain entanglement: q0→q1→q2→q3
# Each CNOT spreads entanglement further
qubits 4
h 0
cnot 0, 1
cnot 1, 2
cnot 2, 3
measure
# Check Entropy tab — all qubits entangled!
""",

"24. Entanglement Star": """\
# Star entanglement: q0 entangled with all others
# Central qubit controls the rest
qubits 5
h 0
cnot 0, 1
cnot 0, 2
cnot 0, 3
cnot 0, 4
measure
""",

# ── QUANTUM COMMUNICATION ────────────────────────────────────

"25. Quantum Teleportation": """\
# Teleportation: Send quantum state using 2 classical bits
# and shared entanglement (Bell pair)
qubits 3

# Step 1: Prepare secret state on q0
ry(1.047) 0

# Step 2: Create Bell pair (q1, q2) shared resource
h 1
cnot 1, 2

# Step 3: Alice's Bell measurement (q0, q1)
cnot 0, 1
h 0

# Step 4: Bob's classically-controlled corrections on q2
cnot 1, 2
cz 0, 2

# q2 now has the original state! Check Bloch sphere for q2
measure
""",

"26. Teleport |1⟩ Verification": """\
# Teleport |1⟩ and verify it arrives correctly
# Simplest teleportation verification
qubits 3

# Prepare |1⟩ on q0 (state to teleport)
x 0

# Bell pair
h 1
cnot 1, 2

# Bell measurement
cnot 0, 1
h 0

# Corrections
cnot 1, 2
cz 0, 2

# q2 should be |1⟩ with certainty
measure
""",

"27. Superdense Coding (send 10)": """\
# Superdense Coding: Send 2 classical bits via 1 qubit
# Alice and Bob share a Bell pair
# Alice encodes "10" by applying Z to her qubit
qubits 2

# Create shared Bell pair
h 0
cnot 0, 1

# Alice encodes "10": apply Z gate
z 0

# Bob decodes: reverse Bell pair creation
cnot 0, 1
h 0

# Bob measures "10" with certainty!
measure
""",

"28. Superdense Coding (all 4)": """\
# Superdense Coding: Change encoding to send different bits
# 00→nothing  01→X  10→Z  11→XZ
qubits 2

h 0
cnot 0, 1

# Change these 2 lines to encode different bits:
# bit1=1 → X,  bit2=1 → Z
x 0
# z 0

cnot 0, 1
h 0
measure
# Currently encodes "01" via X gate
""",

"29. Entanglement Swapping": """\
# Entanglement Swapping: Entangle particles that never met!
# Pair1: (q0,q1), Pair2: (q2,q3)
# After Bell measurement on (q1,q2), q0 & q3 become entangled
qubits 4

# Two independent Bell pairs
h 0
cnot 0, 1
h 2
cnot 2, 3

# Bell measurement on q1, q2
cnot 1, 2
h 1

# Corrections make q0 and q3 entangled
cnot 1, 3
cz 0, 3

# Check Entropy tab: q0 and q3 are now entangled!
measure
""",

# ── QUANTUM ALGORITHMS ───────────────────────────────────────

"30. Deutsch Algorithm": """\
# Deutsch: Is f(0)⊕f(1) = 0 or 1? ONE quantum query!
# Classical needs TWO queries
# Oracle here: balanced (CNOT) → answer = 1
qubits 2
x 1
h 0
h 1

# Oracle (balanced: CNOT)
cnot 0, 1

h 0
measure
# q0 = |1⟩ means balanced, |0⟩ means constant
""",

"31. Deutsch-Jozsa (balanced)": """\
# Deutsch-Jozsa: Balanced oracle f(x₀,x₁) = x₀⊕x₁
# Quantum solves with ONE query, classical needs 2^(n-1)+1
qubits 3
x 2
h 0
h 1
h 2

# Balanced oracle
cnot 0, 2
cnot 1, 2

h 0
h 1
measure
# Input qubits ≠ |00⟩ → balanced
""",

"32. Deutsch-Jozsa (constant)": """\
# Deutsch-Jozsa: Constant oracle f(x) = 0 (do nothing)
qubits 3
x 2
h 0
h 1
h 2

# Constant oracle: f(x) = 0 → no gates needed!

h 0
h 1
measure
# Input qubits = |00⟩ → constant
""",

"33. Bernstein-Vazirani (s=101)": """\
# Find secret string s = "101" in ONE query!
# Classical needs n=3 queries
# Oracle: f(x) = s·x mod 2
qubits 4
x 3
h 0
h 1
h 2
h 3

# Oracle for s=101: CNOT from q0,q2 → q3
cnot 0, 3
cnot 2, 3

h 0
h 1
h 2
measure
# Measure "101" on q0,q1,q2!
""",

"34. Grover Search 2Q (|11⟩)": """\
# Grover's Algorithm: Search |11⟩ in 4-item database
# Quantum: 1 iteration. Classical: up to 4 checks
qubits 2

h 0
h 1

# Oracle: mark |11⟩ with phase flip
cz 0, 1

# Diffusion operator
h 0
h 1
x 0
x 1
cz 0, 1
x 0
x 1
h 0
h 1

measure
# ~100% |11⟩
""",

"35. Grover Search 3Q (|101⟩)": """\
# Grover's: Search |101⟩ in 8-item database
# 2 iterations needed for 3 qubits
qubits 3

h 0
h 1
h 2

# === Iteration 1 ===
# Oracle: phase flip |101⟩
x 1
ccx 0, 2, 1
x 1

# Diffusion
h 0
h 1
h 2
x 0
x 1
x 2
h 2
ccx 0, 1, 2
h 2
x 0
x 1
x 2
h 0
h 1
h 2

# === Iteration 2 ===
x 1
ccx 0, 2, 1
x 1

h 0
h 1
h 2
x 0
x 1
x 2
h 2
ccx 0, 1, 2
h 2
x 0
x 1
x 2
h 0
h 1
h 2

measure
# ~95% |101⟩
""",

# ── QUANTUM FOURIER TRANSFORM ────────────────────────────────

"36. QFT (3 qubits)": """\
# Quantum Fourier Transform on 3 qubits
# Maps computational basis → Fourier basis
# Input: |5⟩ = |101⟩
qubits 3
x 0
x 2

# QFT circuit
h 0
crz(1.5708) 1, 0
crz(0.7854) 2, 0

h 1
crz(1.5708) 2, 1

h 2

# Bit reversal
swap 0, 2

measure
""",

"37. Inverse QFT (3 qubits)": """\
# Inverse QFT undoes the QFT
# QFT then QFT† = Identity → should recover |101⟩
qubits 3
x 0
x 2

# Forward QFT
h 0
crz(1.5708) 1, 0
crz(0.7854) 2, 0
h 1
crz(1.5708) 2, 1
h 2
swap 0, 2

# Inverse QFT (reverse order, negative angles)
swap 0, 2
h 2
crz(-1.5708) 2, 1
h 1
crz(-0.7854) 2, 0
crz(-1.5708) 1, 0
h 0

measure
# Should recover |101⟩
""",

# ── ERROR CORRECTION ─────────────────────────────────────────

"38. 3-Qubit Bit Flip Code": """\
# Bit Flip Error Correction
# Encode 1 logical qubit → 3 physical qubits
# Correct any single bit-flip error
qubits 3

# Prepare state |+⟩ (the data we protect)
h 0

# ENCODE: |ψ⟩|00⟩ → α|000⟩ + β|111⟩
cnot 0, 1
cnot 0, 2

# SIMULATE ERROR on qubit 1
x 1

# CORRECT: Majority vote via Toffoli gates
# Correct q1 if it disagrees with both q0 and q2
ccx 0, 2, 1
x 0
x 2
ccx 0, 2, 1
x 0
x 2

# DECODE
cnot 0, 2
cnot 0, 1
h 0

# q0 should be |+⟩ again (error corrected!)
measure
""",

"39. Phase Flip Code": """\
# Phase Flip Error Correction
# Phase flip = bit flip in Hadamard basis
# Encode |+⟩ → |+++⟩, detect and correct Z errors
qubits 3

# Prepare |+⟩
h 0

# Encode in computational basis
cnot 0, 1
cnot 0, 2

# Switch to Hadamard basis (phase flips → bit flips)
h 0
h 1
h 2

# Simulate phase error on qubit 1
z 1

# In Hadamard basis, Z error is now an X error!
# (H·Z·H = X)

# Switch back and correct as bit flip
h 0
h 1
h 2

# Same majority correction as bit flip code
ccx 0, 2, 1
x 0
x 2
ccx 0, 2, 1
x 0
x 2

# Decode
cnot 0, 2
cnot 0, 1
h 0

measure
""",

# ── FUN & UTILITY ────────────────────────────────────────────

"40. Quantum Coin Flip": """\
# Truly random bit using quantum mechanics
# 50/50 — no classical RNG can prove true randomness
qubits 1
h 0
measure
""",

"41. Quantum Dice (D6)": """\
# Quantum dice: 3 qubits → 8 states
# 000→1  001→2  010→3  011→4  100→5  101→6
# Discard 110→7 and 111→8 (re-roll)
qubits 3
h 0
h 1
h 2
measure
""",

"42. Quantum Random Byte": """\
# Generate a random byte (8 bits) using quantum superposition
# Each bit is independently 50/50
qubits 8
h 0
h 1
h 2
h 3
h 4
h 5
h 6
h 7
measure
""",

"43. Phase Kickback": """\
# Phase Kickback: CNOT with |−⟩ control
# Phase "kicks back" from target to control
# Key mechanism in Deutsch-Jozsa & Grover's algorithms
qubits 2

# Prepare |+⟩|−⟩
h 0
x 1
h 1

# CNOT: phase kickback occurs
cnot 0, 1

# H on q0 to verify state
h 0
measure
# q0 = |0⟩ (kickback preserved the phase relationship)
""",

"44. Quantum Half Adder": """\
# Quantum Half Adder: a + b
# q1 = sum (XOR), q2 = carry (AND)
# Input: a=1 (q0), b=1 (q1)
qubits 3
x 0
x 1

# Carry: q2 = q0 AND q1
ccx 0, 1, 2

# Sum: q1 = q0 XOR q1
cnot 0, 1

# q2=carry, q1=sum → 1+1 = 10₂
measure
# Expected: |110⟩ → carry=1, sum=0 → 2
""",

"45. VQE Ansatz": """\
# Variational Quantum Eigensolver ansatz
# Parameterized circuit — classical optimizer tunes angles
# Used to find ground state energies of molecules
qubits 4

h 0
h 1
h 2
h 3

ry(0.5) 0
ry(1.2) 1
ry(0.8) 2
ry(1.5) 3

rz(0.3) 0
rz(0.7) 1
rz(1.1) 2
rz(0.4) 3

# Entangling layer
cnot 0, 1
cnot 1, 2
cnot 2, 3
cnot 3, 0

# Second parameterized layer
ry(0.9) 0
ry(0.2) 1
ry(1.4) 2
ry(0.6) 3

measure
""",

"46. Quantum Walk (3 steps)": """\
# Quantum Random Walk on a line
# Spreads quadratically faster than classical walk
# Coin qubit: q0, Position: q1,q2
qubits 3

# Step 1
h 0
cnot 0, 1

# Step 2
h 0
cnot 0, 1
cnot 0, 2

# Step 3
h 0
cnot 0, 1

measure
""",

"47. Bell Inequality Test": """\
# Bell/CHSH inequality test circuit
# Produces correlated outcomes that violate
# classical limits — proof of quantum entanglement
qubits 2

# Create Bell state
h 0
cnot 0, 1

# Measurement basis choice:
# Observer A: measure in X basis (H then Z-measure)
h 0

# Observer B: measure in rotated basis
ry(0.7854) 1

measure
# Classical limit: |correlation| ≤ 0.5
# Quantum: up to ~0.71 (violates Bell inequality!)
""",

"48. Quantum Fourier Interference": """\
# QFT on superposition shows interference patterns
# Uniform superposition → peaked at one frequency
qubits 3

# Create |+⟩|0⟩|0⟩ state
h 0

# QFT
h 0
crz(1.5708) 1, 0
crz(0.7854) 2, 0
h 1
crz(1.5708) 2, 1
h 2
swap 0, 2

measure
""",

"49. Reversible Computing": """\
# All quantum gates are reversible!
# Demonstrate: compute, copy (CNOT), uncompute
qubits 3

# Input
x 0

# Compute: AND via Toffoli
ccx 0, 1, 2

# Copy result (for demonstration)
cnot 2, 1

# Uncompute: restore ancilla
ccx 0, 1, 2

measure
""",

"50. GHZ vs W Entanglement": """\
# Compare GHZ and W entanglement side by side
# GHZ: q0,q1,q2 — W: q3,q4,q5
# Check Entropy tab to see different structures
qubits 6

# GHZ: (|000⟩+|111⟩)/√2
h 0
cnot 0, 1
cnot 0, 2

# W: (|100⟩+|010⟩+|001⟩)/√3
ry(1.911) 3
h 3
cnot 3, 4
cnot 3, 5
x 3
h 3
cnot 3, 4
cnot 3, 5

measure
# GHZ: all same bit. W: exactly one |1⟩
""",
}

# ═══════════════════════════════════════════════════════════════
#  SQASM Syntax Highlighter
# ═══════════════════════════════════════════════════════════════
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
#  Visual Widgets (same as before)
# ═══════════════════════════════════════════════════════════════
class CircuitWidget(QWidget):
    gate_selected = Signal(int)
    ML, MT = 64, 36; RH, CW = 56, 74

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gates=[]; self.n_qubits=4; self.sel=-1; self.step=-1; self._cols=[]
        self.setMinimumSize(520,260); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

    def set_n_qubits(self,n): self.n_qubits=n; self.gates.clear(); self.sel=-1; self.step=-1; self.update()
    def add_gate(self,g): self.gates.append(g); self.update()
    def remove_gate(self,idx):
        if 0<=idx<len(self.gates): self.gates.pop(idx); self.sel=-1; self.update()

    def _layout(self):
        qc=[0]*self.n_qubits; cols=[]
        for g in self.gates:
            c=max(qc[q] for q in g.qubits) if g.qubits else 0
            for q in g.qubits: qc[q]=c+1
            cols.append(c)
        self._cols=cols; return cols

    def depth(self): cols=self._layout(); return max(cols)+1 if cols else 0
    def _pos(self,col,row): return self.ML+col*self.CW+self.CW//2, self.MT+row*self.RH

    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); p.fillRect(self.rect(),QColor(24,26,36))
        cols=self._layout(); mc=max(cols)+1 if cols else 0
        self.setMinimumWidth(max(520,self.ML+mc*self.CW+50))
        for q in range(self.n_qubits):
            y=self.MT+q*self.RH
            p.setPen(QColor(170,180,210)); p.setFont(QFont("Consolas",11,QFont.Bold))
            p.drawText(QRectF(0,y-14,self.ML-8,28),Qt.AlignRight|Qt.AlignVCenter,f"|q{q}⟩")
            p.setPen(QPen(QColor(70,75,100),2)); p.drawLine(self.ML,y,W,y)
        for idx,(g,col) in enumerate(zip(self.gates,cols)):
            if not g.qubits: continue
            dim=0<=self.step<=idx; self._draw_gate(p,g,col,idx,dim)
        p.end()

    def _draw_gate(self,p,g,col,idx,dim):
        nq=gate_nqubits(g); color=GATE_COLORS.get(g.gtype,QColor(150,150,150))
        label=gate_label(g); selected=idx==self.sel; alpha=80 if dim else 255
        color=QColor(color.red(),color.green(),color.blue(),alpha)
        qmin,qmax=min(g.qubits),max(g.qubits)
        cx,y1=self._pos(col,qmin); _,y2=self._pos(col,qmax)
        if nq>=2:
            pen_c=QColor(255,210,60,alpha) if selected else QColor(color.red(),color.green(),color.blue(),alpha)
            p.setPen(QPen(pen_c,2.5)); p.drawLine(cx,y1,cx,y2)
        if g.controlled or g.gtype=="CNOT":
            ctrl,tgt=g.qubits[0],g.qubits[1]; _,yc=self._pos(col,ctrl); _,yt=self._pos(col,tgt)
            p.setBrush(QColor(color.red(),color.green(),color.blue(),alpha)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx,yc),7,7)
            if g.gtype=="CNOT":
                p.setBrush(Qt.NoBrush); p.setPen(QPen(color,2.5))
                p.drawEllipse(QPointF(cx,yt),16,16); p.drawLine(cx-16,yt,cx+16,yt); p.drawLine(cx,yt-16,cx,yt+16)
            else:
                r=QRectF(cx-22,yt-22,44,44)
                grad=QLinearGradient(r.topLeft(),r.bottomRight())
                grad.setColorAt(0,QColor(40,50,70,alpha)); grad.setColorAt(1,QColor(28,34,52,alpha))
                p.setBrush(grad); p.setPen(QPen(color,2)); p.drawRoundedRect(r,8,8)
                p.setPen(QColor(230,235,255,alpha)); p.setFont(QFont("Consolas",9,QFont.Bold)); p.drawText(r,Qt.AlignCenter,label)
        elif g.gtype=="CZ":
            for yy in (y1,y2): p.setBrush(color); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(cx,yy),7,7)
        elif g.gtype=="SWAP":
            for yy in (y1,y2):
                p.setPen(QPen(color,2.5)); p.drawLine(cx-10,yy-10,cx+10,yy+10); p.drawLine(cx-10,yy+10,cx+10,yy-10)
        elif g.gtype=="CCX":
            q0,q1,q2=g.qubits; _,ya=self._pos(col,q0); _,yb=self._pos(col,q1); _,yc2=self._pos(col,q2)
            p.setPen(QPen(color,2.5)); p.drawLine(cx,ya,cx,yc2)
            p.setBrush(color); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx,ya),7,7); p.drawEllipse(QPointF(cx,yb),7,7)
            p.setBrush(Qt.NoBrush); p.setPen(QPen(color,2.5))
            p.drawEllipse(QPointF(cx,yc2),16,16); p.drawLine(cx-16,yc2,cx+16,yc2); p.drawLine(cx,yc2-16,cx,yc2+16)
        else:
            q=g.qubits[0]; cx2,cy2=self._pos(col,q); r=QRectF(cx2-22,cy2-22,44,44)
            grad=QLinearGradient(r.topLeft(),r.bottomRight())
            grad.setColorAt(0,QColor(40,50,70,alpha) if not selected else QColor(60,60,40,alpha))
            grad.setColorAt(1,QColor(28,34,52,alpha))
            p.setBrush(grad); p.setPen(QPen(QColor(255,210,60,alpha) if selected else color,2))
            p.drawRoundedRect(r,8,8)
            p.setPen(QColor(230,235,255,alpha)); fsz=9 if len(label)>3 else 14
            p.setFont(QFont("Consolas",fsz,QFont.Bold)); p.drawText(r,Qt.AlignCenter,label)

    def mousePressEvent(self,e):
        cols=self._cols; best=-1; bd=32
        for idx,(g,col) in enumerate(zip(self.gates,cols)):
            if not g.qubits: continue
            cx,cy=self._pos(col,sum(g.qubits)/len(g.qubits))
            d=math.hypot(e.position().x()-cx,e.position().y()-cy)
            if d<bd: best=idx; bd=d
        self.sel=best; self.gate_selected.emit(best); self.update()


class BlochWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.bv=np.array([0.,0.,1.]); self.setMinimumSize(250,250)
        self.theta=0.55; self.phi=0.35
    def set_vector(self,v): self.bv=v; self.update()
    def _proj(self,x,y,z):
        ct,st=math.cos(self.theta),math.sin(self.theta)
        cp,sp=math.cos(self.phi),math.sin(self.phi)
        x1=x*ct+z*st; z1=-x*st+z*ct; return x1,y*cp-z1*sp,y*sp+z1*cp
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); cx,cy=w//2,h//2; R=min(w,h)//2-34
        p.fillRect(self.rect(),QColor(20,22,34))
        p.setPen(QPen(QColor(60,65,90),1)); p.setBrush(Qt.NoBrush); p.drawEllipse(cx-R,cy-R,2*R,2*R)
        def gcirc(a1,a2,a3v,n=72):
            front,back=[],[]
            for i in range(n+1):
                a=2*math.pi*i/n; c=[0.,0.,0.]; c[a1]=math.cos(a); c[a2]=math.sin(a)
                sx,sy,sz=self._proj(*c); pt=QPointF(cx+sx*R,cy-sy*R)
                (front if sz>=0 else back).append(pt)
            if len(back)>1:
                p.setPen(QPen(QColor(40,44,65),1,Qt.DotLine))
                for i in range(len(back)-1): p.drawLine(back[i],back[i+1])
            if len(front)>1:
                p.setPen(QPen(QColor(80,88,120),1))
                for i in range(len(front)-1): p.drawLine(front[i],front[i+1])
        gcirc(0,1,2); gcirc(0,2,1); gcirc(1,2,0)
        for lbl,v,col in [("x",(1,0,0),QColor(255,100,100)),("y",(0,1,0),QColor(100,255,100)),("z",(0,0,1),QColor(100,150,255))]:
            sx,sy,_=self._proj(*v); ex,ey=cx+sx*R,cy-sy*R
            p.setPen(QPen(col,1.5,Qt.DashLine)); p.drawLine(QPointF(cx-sx*R*.1,cy+sy*R*.1),QPointF(ex,ey))
            p.setPen(col); p.setFont(QFont("Consolas",10,QFont.Bold)); p.drawText(QPointF(ex+4,ey-4),lbl)
        vx,vy,vz=self.bv; sx,sy,_=self._proj(vx,vy,vz); ex,ey=cx+sx*R,cy-sy*R
        p.setPen(QPen(QColor(255,70,70),3)); p.drawLine(QPointF(cx,cy),QPointF(ex,ey))
        grad=QRadialGradient(ex,ey,8); grad.setColorAt(0,QColor(255,120,120)); grad.setColorAt(1,QColor(180,40,40))
        p.setBrush(grad); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(ex,ey),7,7)
        p.setPen(QColor(190,200,220)); p.setFont(QFont("Consolas",9))
        p.drawText(6,h-8,f"({vx:+.2f}, {vy:+.2f}, {vz:+.2f})"); p.end()


class HistogramWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.bars={}; self.meas={}; self.setMinimumSize(300,170)
    def set_probabilities(self,probs,n):
        self.bars={format(i,f"0{n}b"):float(pr) for i,pr in enumerate(probs) if pr>1e-4}
        self.meas={}; self.update()
    def set_measurements(self,counts,shots): self.meas={k:v/shots for k,v in counts.items()}; self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); p.fillRect(self.rect(),QColor(20,22,34))
        keys=sorted(set(list(self.bars)+list(self.meas)))
        if not keys:
            p.setPen(QColor(120,130,160)); p.setFont(QFont("Consolas",11))
            p.drawText(self.rect(),Qt.AlignCenter,"Run circuit to see probabilities"); p.end(); return
        n=len(keys); bw=max(18,min(54,(W-60)//max(n,1))); tw=n*bw; x0=(W-tw)//2
        top,bot=28,36; mh=H-top-bot
        p.setPen(QColor(170,180,210)); p.setFont(QFont("Consolas",10,QFont.Bold)); p.drawText(8,16,"Probability Histogram")
        p.setPen(QPen(QColor(45,50,70),1,Qt.DotLine))
        for f in (.25,.5,.75,1.): yy=int(H-bot-f*mh); p.drawLine(x0,yy,x0+tw,yy)
        for i,k in enumerate(keys):
            x=x0+i*bw; prob=self.bars.get(k,0); bh=int(prob*mh)
            if bh>0:
                grad=QLinearGradient(x,H-bot-bh,x,H-bot)
                grad.setColorAt(0,QColor(60,160,240)); grad.setColorAt(1,QColor(30,80,160))
                p.setBrush(grad); p.setPen(Qt.NoPen); p.drawRoundedRect(x+2,H-bot-bh,bw-4,bh,3,3)
            mp=self.meas.get(k,0); mb=int(mp*mh)
            if mb>0: p.setBrush(QColor(240,130,60,160)); p.setPen(Qt.NoPen); p.drawRoundedRect(x+2,H-bot-mb,bw-4,mb,3,3)
            p.setPen(QColor(170,180,210)); p.setFont(QFont("Consolas",max(7,min(10,bw//4))))
            p.drawText(QRectF(x,H-bot+2,bw,bot-4),Qt.AlignCenter,k)
            if prob>.03: p.setPen(QColor(200,210,230)); p.setFont(QFont("Consolas",8)); p.drawText(QRectF(x,H-bot-bh-16,bw,14),Qt.AlignCenter,f"{prob:.2f}")
        p.setPen(Qt.NoPen); p.setBrush(QColor(60,160,240)); p.drawRect(W-130,6,12,12)
        p.setBrush(QColor(240,130,60,160)); p.drawRect(W-130,22,12,12)
        p.setPen(QColor(180,190,210)); p.setFont(QFont("Consolas",9))
        p.drawText(W-114,16,"Theory"); p.drawText(W-114,32,"Measured"); p.end()


class DensityMatrixWidget(QWidget):
    def __init__(self,parent=None): super().__init__(parent); self.rho=None; self.setMinimumSize(200,200)
    def set_matrix(self,rho): self.rho=rho; self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); p.fillRect(self.rect(),QColor(20,22,34))
        if self.rho is None or self.rho.shape[0]>64:
            p.setPen(QColor(120,130,160)); p.setFont(QFont("Consolas",10))
            msg="Density matrix (≤6 qubits)" if self.rho is None else "Too large (>6 qubits)"
            p.drawText(self.rect(),Qt.AlignCenter,msg); p.end(); return
        n=self.rho.shape[0]; sz=min(W-60,H-60); cs=max(2,sz//n); gw=cs*n; x0=(W-gw)//2; y0=30
        p.setPen(QColor(170,180,210)); p.setFont(QFont("Consolas",10,QFont.Bold))
        p.drawText(QRectF(0,4,W,20),Qt.AlignCenter,"Density Matrix |ρᵢⱼ|")
        for i in range(n):
            for j in range(n):
                v=self.rho[i,j]; mag=abs(v)
                hue=int((np.angle(v)/(2*math.pi))*360) if mag>1e-6 else 0; hue=(hue%360+360)%360
                col=QColor.fromHsv(hue,min(255,int(mag*255)),min(255,60+int(mag*195)))
                p.setPen(Qt.NoPen); p.setBrush(col); p.drawRect(x0+j*cs,y0+i*cs,cs-1,cs-1)
        lx=x0+gw+8; ly=y0; lh=gw; lw=14
        if lx+lw+30<W:
            for iy in range(lh):
                frac=1-iy/lh; col=QColor.fromHsv(0,min(255,int(frac*255)),min(255,60+int(frac*195)))
                p.setPen(col); p.drawLine(lx,ly+iy,lx+lw,ly+iy)
            p.setPen(QColor(160,170,200)); p.setFont(QFont("Consolas",8))
            p.drawText(lx+lw+2,ly+8,"1.0"); p.drawText(lx+lw+2,ly+lh,"0.0")
        p.end()


class EntropyWidget(QWidget):
    def __init__(self,parent=None): super().__init__(parent); self.entropies=[]; self.setMinimumHeight(80); self.setMaximumHeight(120)
    def set_entropies(self,ents): self.entropies=ents; self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); p.fillRect(self.rect(),QColor(20,22,34))
        p.setPen(QColor(170,180,210)); p.setFont(QFont("Consolas",10,QFont.Bold))
        p.drawText(6,14,"Entanglement Entropy (von Neumann)")
        if not self.entropies: p.setPen(QColor(120,130,160)); p.setFont(QFont("Consolas",9)); p.drawText(self.rect(),Qt.AlignCenter,"—"); p.end(); return
        n=len(self.entropies); top=22; bot=H-8; bh=bot-top; bw=max(20,min(60,(W-40)//max(n,1))); x0=(W-n*bw)//2; maxe=1.0
        for i,e in enumerate(self.entropies):
            x=x0+i*bw; h=int(min(e/maxe,1.0)*bh); hue=max(0,120-int(e/maxe*120))
            col=QColor.fromHsv(hue,200,180); grad=QLinearGradient(x,bot-h,x,bot)
            grad.setColorAt(0,col); grad.setColorAt(1,col.darker(160))
            p.setBrush(grad); p.setPen(Qt.NoPen); p.drawRoundedRect(x+3,bot-h,bw-6,h,3,3)
            p.setPen(QColor(200,210,230)); p.setFont(QFont("Consolas",9,QFont.Bold)); p.drawText(QRectF(x,bot+1,bw,14),Qt.AlignCenter,f"q{i}")
            p.setFont(QFont("Consolas",8)); p.drawText(QRectF(x,bot-h-14,bw,13),Qt.AlignCenter,f"{e:.2f}")
        p.end()


# ═══════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚛  QubitLab  —  Quantum Computer Simulator  (50 Presets)")
        self.resize(1450,920)
        self.sim=QuantumSimulator(4); self.n_qubits=4; self.history=[]; self.step_idx=-1

        left=QWidget(); ll=QVBoxLayout(left); ll.setContentsMargins(4,4,4,4)
        ctrl=QGroupBox("Gate Controls"); cg=QGridLayout(ctrl)
        cg.addWidget(QLabel("Qubits:"),0,0)
        self.spin_nq=QSpinBox(); self.spin_nq.setRange(1,8); self.spin_nq.setValue(4)
        self.spin_nq.valueChanged.connect(self._change_nq); cg.addWidget(self.spin_nq,0,1)
        cg.addWidget(QLabel("Gate:"),0,2)
        self.combo_gate=QComboBox(); self.combo_gate.addItems(SINGLE_QUBIT_GATES+TWO_QUBIT_GATES+THREE_QUBIT_GATES)
        self.combo_gate.currentTextChanged.connect(self._gate_changed); cg.addWidget(self.combo_gate,0,3,1,2)
        self.lbl_angle=QLabel("Angle (×π):"); self.spin_angle=QDoubleSpinBox()
        self.spin_angle.setRange(-4,4); self.spin_angle.setSingleStep(0.25); self.spin_angle.setValue(0.5); self.spin_angle.setDecimals(4)
        cg.addWidget(self.lbl_angle,1,0); cg.addWidget(self.spin_angle,1,1)
        self.chk_ctrl=QCheckBox("Controlled"); cg.addWidget(self.chk_ctrl,1,2)
        self.lbl_q1=QLabel("Qubit:"); self.spin_q1=QSpinBox(); self.spin_q1.setRange(0,3)
        self.lbl_q2=QLabel("Ctrl:");  self.spin_q2=QSpinBox(); self.spin_q2.setRange(0,3)
        self.lbl_q3=QLabel("Tgt:");   self.spin_q3=QSpinBox(); self.spin_q3.setRange(0,3)
        self.lbl_q4=QLabel("C2:");    self.spin_q4=QSpinBox(); self.spin_q4.setRange(0,3)
        cg.addWidget(self.lbl_q1,2,0); cg.addWidget(self.spin_q1,2,1)
        cg.addWidget(self.lbl_q2,2,2); cg.addWidget(self.spin_q2,2,3)
        cg.addWidget(self.lbl_q3,2,4); cg.addWidget(self.spin_q3,2,5)
        cg.addWidget(self.lbl_q4,3,2); cg.addWidget(self.spin_q4,3,3)
        btn_add=QPushButton("➕ Add Gate"); btn_add.clicked.connect(self._add_gate)
        btn_undo=QPushButton("↩ Undo"); btn_undo.clicked.connect(self._undo)
        cg.addWidget(btn_add,3,0,1,2); cg.addWidget(btn_undo,3,4,1,2)
        cg.addWidget(QLabel("Example:"),4,0)
        self.combo_preset=QComboBox(); self.combo_preset.addItems(list(SQASM_EXAMPLES.keys()))
        cg.addWidget(self.combo_preset,4,1,1,2)
        btn_preset=QPushButton("📥 Load Program"); btn_preset.setStyleSheet(self._accent("#6a4c93"))
        btn_preset.clicked.connect(self._load_example); cg.addWidget(btn_preset,4,3,1,2)
        self.chk_auto=QCheckBox("Auto-run"); self.chk_noise=QCheckBox("Noise")
        self.sld_noise=QSlider(Qt.Horizontal); self.sld_noise.setRange(0,50); self.sld_noise.setValue(5)
        self.lbl_noise_val=QLabel("0.05")
        self.sld_noise.valueChanged.connect(lambda v: self.lbl_noise_val.setText(f"{v/100:.2f}"))
        cg.addWidget(self.chk_auto,5,0,1,2)
        cg.addWidget(self.chk_noise,5,2); cg.addWidget(self.sld_noise,5,3,1,2); cg.addWidget(self.lbl_noise_val,5,5)
        self.lbl_metrics=QLabel("Gates: 0 | Depth: 0")
        self.lbl_metrics.setStyleSheet("color:#8be9fd; font-family:Consolas;"); cg.addWidget(self.lbl_metrics,6,0,1,6)
        ll.addWidget(ctrl)

        self.circuit=CircuitWidget(); self.circuit.gate_selected.connect(self._gate_sel)
        scroll=QScrollArea(); scroll.setWidget(self.circuit); scroll.setWidgetResizable(False)
        ll.addWidget(scroll,1)

        a1=QHBoxLayout()
        self.btn_run=QPushButton("▶  Run"); self.btn_run.setStyleSheet(self._accent("#238636"))
        self.btn_run.clicked.connect(self._run); a1.addWidget(self.btn_run)
        self.btn_step_b=QPushButton("⏮ Step◀"); self.btn_step_b.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_step_b.clicked.connect(self._step_back); a1.addWidget(self.btn_step_b)
        self.btn_step_f=QPushButton("Step▶ ⏭"); self.btn_step_f.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_step_f.clicked.connect(self._step_fwd); a1.addWidget(self.btn_step_f)
        self.btn_meas=QPushButton("🎲 Measure"); self.btn_meas.setStyleSheet(self._accent("#8b3a3a"))
        self.btn_meas.clicked.connect(self._measure); a1.addWidget(self.btn_meas)
        ll.addLayout(a1)
        a2=QHBoxLayout()
        self.btn_reset=QPushButton("🔄 Reset"); self.btn_reset.setStyleSheet(self._accent("#2d5a8e"))
        self.btn_reset.clicked.connect(self._reset_state); a2.addWidget(self.btn_reset)
        self.btn_clear=QPushButton("✖ Clear"); self.btn_clear.setStyleSheet(self._accent("#555"))
        self.btn_clear.clicked.connect(self._clear_circuit); a2.addWidget(self.btn_clear)
        self.btn_qasm=QPushButton("📤 QASM"); self.btn_qasm.setStyleSheet(self._accent("#6a4c93"))
        self.btn_qasm.clicked.connect(self._export_qasm); a2.addWidget(self.btn_qasm)
        self.btn_del=QPushButton("🗑 Remove"); self.btn_del.setStyleSheet(self._accent("#555"))
        self.btn_del.clicked.connect(self._del_gate); a2.addWidget(self.btn_del)
        ll.addLayout(a2)

        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(4,4,4,4)
        tabs=QTabWidget()

        # Program tab
        tab_prog=QWidget(); tpl=QVBoxLayout(tab_prog)
        eh=QHBoxLayout(); eh.addWidget(QLabel("SQASM Program:"))
        self.btn_run_prog=QPushButton("▶  Run Program  (Ctrl+Enter)")
        self.btn_run_prog.setStyleSheet(self._accent("#238636"))
        self.btn_run_prog.clicked.connect(self._run_program); eh.addWidget(self.btn_run_prog)
        btn_clear_ed=QPushButton("🗑 Clear Editor"); btn_clear_ed.setStyleSheet(self._accent("#555"))
        btn_clear_ed.clicked.connect(lambda: self.editor.clear()); eh.addWidget(btn_clear_ed)
        tpl.addLayout(eh)
        self.editor=QPlainTextEdit(); self.editor.setFont(QFont("Consolas",12))
        self.editor.setPlaceholderText("# Write your quantum program here\nqubits 2\nh 0\ncnot 0, 1\nmeasure\n")
        self.highlighter=SqasmHighlighter(self.editor.document())
        tpl.addWidget(self.editor,1)
        cg2=QGroupBox("Output Console"); cl=QVBoxLayout(cg2)
        self.console=QTextEdit(); self.console.setReadOnly(True); self.console.setFont(QFont("Consolas",11))
        self.console.setMaximumHeight(180); cl.addWidget(self.console); tpl.addWidget(cg2)
        ref=QGroupBox("SQASM Quick Reference"); rl2=QVBoxLayout(ref)
        ref_txt=QLabel(
            "<b>Commands:</b> <code>qubits N</code> · <code>measure</code> · <code>reset</code> · <code>barrier</code><br>"
            "<b>Gates:</b> <code>h x y z s t</code> · <code>cnot/cx cz swap ccx/toffoli</code><br>"
            "<b>Rotation:</b> <code>rx(angle) ry(angle) rz(angle) qubit</code><br>"
            "<b>Controlled:</b> <code>ch cs ct crx cry crz ctrl, tgt</code><br>"
            "<b>Syntax:</b> <code>gate q1, q2, ...</code> · Angles in radians · <code>#</code> comments"
        )
        ref_txt.setWordWrap(True); ref_txt.setStyleSheet("color:#bac2de; font-size:11px;"); rl2.addWidget(ref_txt)
        tpl.addWidget(ref)
        tabs.addTab(tab_prog,"💻 Program")

        # Visual tab
        tab_vis=QWidget(); tvl=QVBoxLayout(tab_vis)
        bloch_box=QGroupBox("Bloch Sphere"); bl=QVBoxLayout(bloch_box)
        bh2=QHBoxLayout(); bh2.addWidget(QLabel("Qubit:"))
        self.spin_bloch=QSpinBox(); self.spin_bloch.setRange(0,3)
        self.spin_bloch.valueChanged.connect(self._update_bloch); bh2.addWidget(self.spin_bloch)
        bl.addLayout(bh2); self.bloch=BlochWidget(); bl.addWidget(self.bloch)
        tvl.addWidget(bloch_box); self.hist=HistogramWidget(); tvl.addWidget(self.hist,1)
        tabs.addTab(tab_vis,"🎨 Visual")

        # State tab
        tab_state=QWidget(); tsl=QVBoxLayout(tab_state)
        sv_box=QGroupBox("State Vector  |ψ⟩"); sl=QVBoxLayout(sv_box)
        self.state_text=QTextEdit(); self.state_text.setReadOnly(True)
        self.state_text.setFont(QFont("Consolas",10)); self.state_text.setMaximumHeight(200)
        sl.addWidget(self.state_text); tsl.addWidget(sv_box)
        self.entropy_w=EntropyWidget(); tsl.addWidget(self.entropy_w)
        self.density_w=DensityMatrixWidget(); tsl.addWidget(self.density_w,1)
        tabs.addTab(tab_state,"📊 State")

        # Gate Info tab
        tab_gate=QWidget(); tgl=QVBoxLayout(tab_gate)
        gi_box=QGroupBox("Gate Matrix"); gil=QVBoxLayout(gi_box)
        self.gate_info_text=QTextEdit(); self.gate_info_text.setReadOnly(True)
        self.gate_info_text.setFont(QFont("Consolas",10)); gil.addWidget(self.gate_info_text); tgl.addWidget(gi_box)
        tabs.addTab(tab_gate,"🔬 Gate Info")

        # Measure tab
        tab_meas=QWidget(); tml=QVBoxLayout(tab_meas)
        m_box=QGroupBox("Measurement Counts"); ml=QVBoxLayout(m_box)
        self.meas_text=QTextEdit(); self.meas_text.setReadOnly(True)
        self.meas_text.setFont(QFont("Consolas",10)); ml.addWidget(self.meas_text); tml.addWidget(m_box)
        tabs.addTab(tab_meas,"🎲 Measure")

        rl.addWidget(tabs)
        splitter=QSplitter(Qt.Horizontal); splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(0,3); splitter.setStretchFactor(1,2)
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Ready — Load an example or write a program")
        self.statusBar().setStyleSheet("color:#8be9fd; background:#1a1c2a;")
        self._gate_changed(self.combo_gate.currentText()); self._update_displays()
        self._apply_style(); self._setup_shortcuts()

    @staticmethod
    def _accent(bg):
        return f"QPushButton{{background:{bg};color:#fff;font-weight:bold;padding:7px 10px;border-radius:4px;}}QPushButton:hover{{opacity:0.85;}}"

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow,QWidget{background:#1a1c2a;color:#cdd6f4;}
            QGroupBox{border:1px solid #3a3d52;border-radius:6px;margin-top:12px;padding-top:16px;font-weight:bold;}
            QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}
            QPushButton{background:#2a2d40;border:1px solid #3a3d52;border-radius:4px;padding:5px 8px;color:#cdd6f4;}
            QPushButton:hover{background:#3a3d52;}
            QComboBox,QSpinBox,QDoubleSpinBox{background:#2a2d40;border:1px solid #3a3d52;border-radius:4px;padding:3px;color:#cdd6f4;}
            QTextEdit,QPlainTextEdit{background:#12131e;border:1px solid #3a3d52;color:#cdd6f4;}
            QScrollArea{border:none;}
            QLabel{color:#cdd6f4;}
            QSplitter::handle{background:#3a3d52;width:3px;}
            QTabWidget::pane{border:1px solid #3a3d52;}
            QTabBar::tab{background:#2a2d40;color:#cdd6f4;padding:6px 14px;border:1px solid #3a3d52;border-bottom:none;border-radius:4px 4px 0 0;}
            QTabBar::tab:selected{background:#3a3d52;color:#fff;}
            QCheckBox{color:#cdd6f4;}
            QSlider::groove:horizontal{height:6px;background:#2a2d40;border-radius:3px;}
            QSlider::handle:horizontal{background:#607090;width:14px;margin:-4px 0;border-radius:7px;}
        """)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Delete"),self,self._del_gate)
        QShortcut(QKeySequence("Ctrl+Z"),self,self._undo)
        QShortcut(QKeySequence("Ctrl+R"),self,self._run)
        QShortcut(QKeySequence("Ctrl+M"),self,self._measure)
        QShortcut(QKeySequence("Ctrl+Shift+R"),self,self._reset_state)
        QShortcut(QKeySequence("Right"),self,self._step_fwd)
        QShortcut(QKeySequence("Left"),self,self._step_back)
        QShortcut(QKeySequence("Ctrl+Return"),self,self._run_program)

    # ── SQASM PARSER ──
    def _parse_sqasm(self,text):
        n_qubits=None; gates=[]; do_measure=False; errors=[]
        for lineno,raw_line in enumerate(text.split('\n'),1):
            line=raw_line.strip()
            if not line or line.startswith('#') or line.startswith('//'): continue
            if '#' in line: line=line[:line.index('#')].strip()
            if '//' in line: line=line[:line.index('//')].strip()
            if not line: continue
            m=re.match(r'^qubits\s+(\d+)$',line,re.I)
            if m: n_qubits=int(m.group(1)); continue
            if re.match(r'^measure$',line,re.I): do_measure=True; continue
            if re.match(r'^reset$',line,re.I): gates.append(CircuitGate("__reset__",())); continue
            if re.match(r'^barrier$',line,re.I): continue
            m=re.match(r'^([a-zA-Z]+)(?:\(([^)]+)\))?\s+(.+)$',line)
            if not m: errors.append(f"Line {lineno}: Syntax error: '{raw_line.strip()}'"); continue
            raw_gate=m.group(1).lower(); angle_str=m.group(2); qubits_str=m.group(3)
            controlled=False; gate_key=raw_gate
            base_map={'ch':'H','cs':'S','ct':'T','crx':'RX','cry':'RY','crz':'RZ'}
            if gate_key in base_map: controlled=True; resolved=base_map[gate_key]
            elif gate_key in GATE_ALIASES: resolved=GATE_ALIASES[gate_key]
            else:
                for g in ALL_STANDARD_GATES:
                    if g.lower()==gate_key: resolved=g; break
                else: errors.append(f"Line {lineno}: Unknown gate '{raw_gate}'"); continue
            angle=None
            if angle_str is not None:
                try:
                    a=angle_str.strip().replace('pi',str(np.pi)).replace('π',str(np.pi))
                    angle=float(eval(a,{"__builtins__":{}},{"pi":np.pi}))
                except: errors.append(f"Line {lineno}: Invalid angle '{angle_str}'"); continue
            elif resolved in ROTATION_GATES: errors.append(f"Line {lineno}: {resolved} requires angle"); continue
            try: qubits=tuple(int(q.strip()) for q in qubits_str.split(','))
            except: errors.append(f"Line {lineno}: Invalid qubits '{qubits_str}'"); continue
            expected_nq=3 if resolved in THREE_QUBIT_GATES else (2 if (resolved in TWO_QUBIT_GATES or controlled) else 1)
            if len(qubits)!=expected_nq:
                errors.append(f"Line {lineno}: {resolved} expects {expected_nq} qubit(s), got {len(qubits)}"); continue
            if len(qubits)!=len(set(qubits)): errors.append(f"Line {lineno}: Duplicate qubit"); continue
            gates.append(CircuitGate(resolved,qubits,angle=angle,controlled=controlled))
        return n_qubits,gates,do_measure,errors

    def _run_program(self):
        text=self.editor.toPlainText()
        if not text.strip(): self.console.setText("⚠ No program to run."); return
        n_qubits,gates,do_measure,errors=self._parse_sqasm(text)
        if errors: self.console.setText("❌ Parse Errors:\n\n"+"\n".join(errors)); return
        if n_qubits is None:
            max_q=0
            for g in gates:
                if g.qubits: max_q=max(max_q,max(g.qubits))
            n_qubits=max_q+1 if gates else 2
        if n_qubits!=self.n_qubits: self.spin_nq.setValue(n_qubits)
        self.circuit.gates.clear(); self.circuit.sel=-1; self.circuit.step=-1
        visual_gates=[g for g in gates if g.gtype!="__reset__"]
        for g in visual_gates: self.circuit.add_gate(g)
        self._update_metrics()
        self.sim=QuantumSimulator(self.n_qubits)
        noise_p=self.sld_noise.value()/100 if self.chk_noise.isChecked() else 0
        output_lines=[f"▶ Running program with {self.n_qubits} qubits...",f"  Gates: {len(visual_gates)}  |  Depth: {self.circuit.depth()}"]
        for g in gates:
            if g.gtype=="__reset__": self.sim.reset(); output_lines.append("  ⏮ State reset to |0...0⟩"); continue
            try:
                mat=get_gate_matrix(g); self.sim.apply_gate(mat,g.qubits); self.sim.apply_noise(noise_p)
            except Exception as e:
                output_lines.append(f"❌ Error: {gate_label(g)}: {e}"); self.console.setText("\n".join(output_lines)); return
        self._update_displays()
        if do_measure:
            shots=2048; counts=self.sim.measure_all(shots); self.hist.set_measurements(counts,shots)
            output_lines.append(f"\n🎲 Measurement ({shots} shots):"); output_lines.append("─"*45)
            for k,v in sorted(counts.items(),key=lambda x:-x[1]):
                bar="█"*(v*30//shots); output_lines.append(f"  |{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}")
            txt=f"Measurement ({shots} shots)\n{'─'*40}\n"
            for k,v in sorted(counts.items(),key=lambda x:-x[1]):
                bar="█"*(v*30//shots); txt+=f"|{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}\n"
            self.meas_text.setText(txt)
        else:
            output_lines.append("\n✅ Program executed (no measurement).")
            output_lines.append("  Add 'measure' to your program or click 🎲 Measure.")
        self.console.setText("\n".join(output_lines))
        self.statusBar().showMessage(f"Program executed — {len(visual_gates)} gates")

    def _load_example(self):
        name=self.combo_preset.currentText()
        if name in SQASM_EXAMPLES:
            self.editor.setPlainText(SQASM_EXAMPLES[name])
            self.console.setText(f"📥 Loaded: {name}")

    # ── GUI methods ──
    def _change_nq(self,n):
        self.n_qubits=n; self.sim=QuantumSimulator(n); self.circuit.set_n_qubits(n)
        for s in (self.spin_q1,self.spin_q2,self.spin_q3,self.spin_q4,self.spin_bloch): s.setRange(0,n-1)
        self._update_displays()

    def _gate_changed(self,name):
        is_rot=name in ROTATION_GATES; is_3q=name in THREE_QUBIT_GATES
        is_2q=name in TWO_QUBIT_GATES; is_1q=name in SINGLE_QUBIT_GATES and not is_rot
        self.lbl_angle.setVisible(is_rot); self.spin_angle.setVisible(is_rot)
        self.chk_ctrl.setVisible(is_1q or is_rot)
        self.lbl_q1.setVisible(not is_2q and not is_3q); self.spin_q1.setVisible(not is_2q and not is_3q)
        show2=is_2q or is_3q or is_rot; self.lbl_q2.setVisible(show2); self.spin_q2.setVisible(show2)
        self.lbl_q3.setVisible(show2); self.spin_q3.setVisible(show2)
        self.lbl_q4.setVisible(is_3q); self.spin_q4.setVisible(is_3q)
        if is_2q: self.lbl_q2.setText("Ctrl:"); self.lbl_q3.setText("Tgt:")
        elif is_3q: self.lbl_q2.setText("C1:"); self.lbl_q3.setText("C2:"); self.lbl_q4.setText("Tgt:")
        else: self.lbl_q2.setText("Ctrl:"); self.lbl_q3.setText("Tgt:")

    def _add_gate(self):
        name=self.combo_gate.currentText(); ctrl=self.chk_ctrl.isChecked()
        angle=self.spin_angle.value()*np.pi if name in ROTATION_GATES else None
        if name in THREE_QUBIT_GATES:
            c1,c2,t=self.spin_q2.value(),self.spin_q4.value(),self.spin_q3.value()
            if len({c1,c2,t})<3: QMessageBox.warning(self,"Error","Qubits must differ"); return
            g=CircuitGate(name,(c1,c2,t))
        elif name in TWO_QUBIT_GATES:
            c,t=self.spin_q2.value(),self.spin_q3.value()
            if c==t: QMessageBox.warning(self,"Error","Qubits must differ"); return
            g=CircuitGate(name,(c,t))
        elif ctrl:
            c,t=self.spin_q2.value(),self.spin_q3.value()
            if c==t: QMessageBox.warning(self,"Error","Qubits must differ"); return
            g=CircuitGate(name,(c,t),angle=angle,controlled=True)
        else: g=CircuitGate(name,(self.spin_q1.value(),),angle=angle)
        self.history.append([x.copy() for x in self.circuit.gates])
        self.circuit.add_gate(g); self._update_metrics()
        if self.chk_auto.isChecked(): self._run()

    def _del_gate(self):
        idx=self.circuit.sel
        if idx>=0:
            self.history.append([x.copy() for x in self.circuit.gates])
            self.circuit.remove_gate(idx); self._update_metrics()
            if self.chk_auto.isChecked(): self._run()

    def _undo(self):
        if self.history:
            self.circuit.gates=self.history.pop(); self.circuit.sel=-1; self.circuit.update(); self._update_metrics()
            if self.chk_auto.isChecked(): self._run()

    def _gate_sel(self,idx):
        if 0<=idx<len(self.circuit.gates): self._show_gate_info(self.circuit.gates[idx])

    def _run(self):
        self.sim=QuantumSimulator(self.n_qubits)
        noise_p=self.sld_noise.value()/100 if self.chk_noise.isChecked() else 0
        limit=len(self.circuit.gates) if self.step_idx<0 else self.step_idx
        self.circuit.step=self.step_idx; self.circuit.update()
        for i,g in enumerate(self.circuit.gates[:limit]):
            try: mat=get_gate_matrix(g); self.sim.apply_gate(mat,g.qubits); self.sim.apply_noise(noise_p)
            except Exception as e: self.console.setText(f"Error: {gate_label(g)}: {e}"); return
        self._update_displays()
        self.statusBar().showMessage(f"Simulated {min(limit,len(self.circuit.gates))}/{len(self.circuit.gates)} gates | Dim={2**self.n_qubits} | Noise={'ON' if noise_p else 'OFF'}")

    def _step_fwd(self):
        if self.step_idx<0: self.step_idx=1
        elif self.step_idx<len(self.circuit.gates): self.step_idx+=1
        if self.step_idx>len(self.circuit.gates): self.step_idx=len(self.circuit.gates)
        self._run()

    def _step_back(self):
        if self.step_idx<0: self.step_idx=len(self.circuit.gates)-1
        elif self.step_idx>0: self.step_idx-=1
        else: self.step_idx=0
        self._run()

    def _measure(self):
        self._run(); shots=2048; counts=self.sim.measure_all(shots)
        self.hist.set_measurements(counts,shots)
        txt=f"Measurement ({shots} shots)\n{'─'*40}\n"
        for k,v in sorted(counts.items(),key=lambda x:-x[1]):
            bar="█"*(v*30//shots); txt+=f"|{k}⟩  {v:5d}  ({v/shots*100:5.1f}%)  {bar}\n"
        self.meas_text.setText(txt)

    def _reset_state(self):
        self.sim.reset(); self.step_idx=-1; self.circuit.step=-1; self.circuit.update()
        self.hist.meas={}; self.meas_text.clear(); self._update_displays()

    def _clear_circuit(self):
        self.history.append([x.copy() for x in self.circuit.gates])
        self.circuit.gates.clear(); self.circuit.sel=-1; self.circuit.step=-1
        self.circuit.update(); self._reset_state(); self._update_metrics()

    def _export_qasm(self):
        lines=["OPENQASM 2.0;","include \"qelib1.inc\";","",f"qreg q[{self.n_qubits}];",f"creg c[{self.n_qubits}];",""]
        qasm_gate={"H":"h","X":"x","Y":"y","Z":"z","S":"s","T":"t","RX":"rx","RY":"ry","RZ":"rz","CNOT":"cx","CZ":"cz","SWAP":"swap","CCX":"ccx"}
        for g in self.circuit.gates:
            gn=qasm_gate.get(g.gtype,g.gtype.lower())
            if g.controlled and g.gtype not in TWO_QUBIT_GATES: gn="c"+gn
            qs=",".join(f"q[{q}]" for q in g.qubits)
            if g.gtype in ROTATION_GATES and g.angle is not None: lines.append(f"{gn}({g.angle/np.pi:.4f}*pi) {qs};")
            else: lines.append(f"{gn} {qs};")
        lines.append("")
        for q in range(self.n_qubits): lines.append(f"measure q[{q}] -> c[{q}];")
        text="\n".join(lines)
        dlg=QDialog(self); dlg.setWindowTitle("QASM Export"); dlg.resize(600,500)
        dl=QVBoxLayout(dlg); te=QTextEdit(); te.setFont(QFont("Consolas",11)); te.setPlainText(text); dl.addWidget(te)
        bb=QHBoxLayout()
        btnSave=QPushButton("💾 Save"); btnSave.clicked.connect(lambda:self._save_qasm(text,dlg))
        btnClose=QPushButton("Close"); btnClose.clicked.connect(dlg.close)
        bb.addWidget(btnSave); bb.addWidget(btnClose); dl.addLayout(bb); dlg.exec()

    def _save_qasm(self,text,parent):
        path,_=QFileDialog.getSaveFileName(parent,"Save QASM","circuit.qasm","QASM (*.qasm);;All (*)")
        if path:
            with open(path,'w') as f: f.write(text)
            self.statusBar().showMessage(f"Saved QASM to {path}")

    def _update_bloch(self):
        q=self.spin_bloch.value()
        if q<self.n_qubits: self.bloch.set_vector(self.sim.bloch_vector(q))

    def _show_gate_info(self,gate):
        try:
            mat=get_gate_matrix(gate); lines=[f"Gate: {gate_label(gate)}",f"Qubits: {gate.qubits}  |  Size: {mat.shape[0]}×{mat.shape[1]}"]
            if gate.angle is not None: lines.append(f"Angle: {gate.angle/np.pi:.4g}π rad")
            lines.append("─"*50)
            for i in range(mat.shape[0]):
                row="  ".join(f"{mat[i,j].real:+.4f}{mat[i,j].imag:+.4f}j" for j in range(mat.shape[1])); lines.append(row)
            self.gate_info_text.setText("\n".join(lines))
        except Exception as e: self.gate_info_text.setText(f"Error: {e}")

    def _update_metrics(self):
        n=len(self.circuit.gates); d=self.circuit.depth()
        n1=sum(1 for g in self.circuit.gates if gate_nqubits(g)==1)
        n2=sum(1 for g in self.circuit.gates if gate_nqubits(g)==2)
        n3=sum(1 for g in self.circuit.gates if gate_nqubits(g)==3)
        self.lbl_metrics.setText(f"Gates: {n} | Depth: {d} | 1q: {n1}  2q: {n2}  3q: {n3}")

    def _update_displays(self):
        lines=[]
        for i,a in enumerate(self.sim.state):
            if abs(a)>1e-6:
                ket=format(i,f"0{self.n_qubits}b"); re,im=a.real,a.imag; phase=np.angle(a)
                hue=int((phase+np.pi)/(2*np.pi)*360)%360; pcol=QColor.fromHsv(hue,200,220).name()
                sign="+" if im>=0 else "-"
                lines.append(f"<span style='color:{pcol}'>|{ket}⟩</span>  {re:+.4f} {sign} {abs(im):.4f}i   p={abs(a)**2:.4f}  φ={phase:.3f}")
        self.state_text.setHtml("<br>".join(lines) if lines else "|0…0⟩  1.0000 + 0.0000i   p=1.0000")
        self.hist.set_probabilities(self.sim.probabilities(),self.n_qubits)
        self._update_bloch()
        self.entropy_w.set_entropies([self.sim.entanglement_entropy(q) for q in range(self.n_qubits)])
        if self.n_qubits<=6: self.density_w.set_matrix(self.sim.density_matrix())
        else: self.density_w.set_matrix(None)
        if 0<=self.circuit.sel<len(self.circuit.gates): self._show_gate_info(self.circuit.gates[self.circuit.sel])
        self._update_metrics()


if __name__=="__main__":
    app=QApplication(sys.argv); app.setStyle("Fusion")
    win=MainWindow(); win.show()
    sys.exit(app.exec())
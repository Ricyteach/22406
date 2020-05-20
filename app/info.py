import itertools
from pathlib import Path

from app.common import *


CANDE_FOLDER = Path(__file__).parents[2] / 'cande'
MSH_FILE = CANDE_FOLDER / r"mesh.msh"
CANDE_FILE = CANDE_FOLDER / r"result.cid._partial"

N_STRUCTS = 3

KEEP_INDEXES = [
    [],
    [],
    [],
]

# user input
INTERF_STRUCT_NODES = [
    range(0),
    range(0),
    range(0),
]

N_BEAMS = [
    len(KEEP_INDEXES[0]),
    len(KEEP_INDEXES[1]),
    len(KEEP_INDEXES[2]),
]

STRUCT_STEPS = [1, 1, 2]
STRUCT_MATS = [1, 2, 3]
CONNECTIVITY = [
    Connectivity.noncontiguous,
    Connectivity.noncontiguous,
    Connectivity.noncontiguous,
]

# sanity check
assert len(KEEP_INDEXES) == N_STRUCTS
assert len(INTERF_STRUCT_NODES) == N_STRUCTS
assert len(N_BEAMS) == N_STRUCTS
assert len(CONNECTIVITY) == N_STRUCTS

N_LL_STEPS = 1

N_MATERIALS = 3
# material boundaries
MAT_BOUNDS = {
    1: [(-530.0, -120.0), (530.0, -120.0), (530.0, 0.0), (-530.0, 0.0)],
    2: [(-530.0, 0.0), (530.0, 0.0), (-530.0, 118.0), (-530.0, 118.0)],
    3: [(-169.75, 0.0), (169.75, 0.0), (169.75, 118.0), (-169.75, 118.0)],
}
# sanity check
assert len(MAT_BOUNDS) == N_MATERIALS
# TODO: add sanity check to visually check MAT_BOUNDS

N_DL_STEPS = 1
# step boundaries: {mat_num_range: {step_num: y_value}}
# each element center with mat_num in the mat_num_range greater than y_value will be applied current step_num
DL_STEP_BOUNDS = {
    range(1,4): {1: -120.0},
}
# sanity check
assert sorted({v for d in DL_STEP_BOUNDS.values() for v in d.keys()}) == list(range(1, N_DL_STEPS+1))
assert sorted({mat for mat in itertools.chain(*DL_STEP_BOUNDS.keys())}) == list(range(1, N_MATERIALS+1))

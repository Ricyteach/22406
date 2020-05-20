from msh2cande.format import c3, c4, c5, c2
from msh2cande.msh_load import _load_msh, _extents
from msh2cande.structure_build import Structure

from app.info import *
from app.common import *


def build_struct_and_kept_indexes(*, show=True):
    """Load msh into a Structure for the purpose of display.

    Clean it up and edit KEEP_INDEXES.
    """
    struct = Structure(msh_b_df, msh_n_df, msh_e_df, msh_ext_df)
    if show:
        struct.show_candidates()
    struct.candidates_df = struct.candidates_df.loc[
        [idx for indexes in KEEP_INDEXES for idx in indexes], :
    ]
    if show:
        struct.show_candidates()
    return struct


def gen_struct_elements(struct, *, show=True):
    """Produces a structure/beam element df for each structure."""
    for keeps, interfaces, struct_step, struct_mat, n_beams, connectivity_int in zip(
        KEEP_INDEXES,
        INTERF_STRUCT_NODES,
        STRUCT_STEPS,
        STRUCT_MATS,
        N_BEAMS,
        CONNECTIVITY,
    ):
        # TODO: handle the case of multiple beam groups within a structure
        # define structure nodes
        structx_nodes = struct.candidates_df.loc[[*keeps], :]
        structx_nodes.index = range(1, len(structx_nodes) + 1)
        # define i,j interface nodes on structure
        # TODO: correctly show currently specified struct nodes for choosing interfaces
        # TODO: correctly show current structure and beam groups, not all structures
        if show:
            struct.show_candidates()
        n_interf = len(interfaces)
        structx_nodes.loc[interfaces, "interf_num"] = range(1, n_interf + 1)
        if show:
            struct.show_candidates()

        # define struct element df; assume left-to-right connectivity
        structx_elements = pd.DataFrame(
            # if contiguous, the number of elements = number of nodes
            # if noncontiguous, number of elements = number of nodes -1
            index=range(1, len(structx_nodes) + 1 - connectivity_int),
            columns=ELEMENT_COLUMNS,
        )
        structx_elements.k = 0
        structx_elements.l = 0
        structx_elements.mat = struct_mat
        structx_elements.step = struct_step
        last_i = {
            Connectivity.contiguous: structx_nodes.index[0],
            Connectivity.noncontiguous: structx_nodes.index[-1],
        }[connectivity_int]
        last_j = len(structx_nodes) - connectivity_int
        structx_elements.i = structx_nodes.loc[
            [*range(2, last_j + 1), last_i], "n"
        ].values
        structx_elements.j = structx_nodes.loc[range(1, last_j + 1), "n"].values
        # sanity check
        assert n_beams == len(structx_elements)
        # TODO: potentially use SeqNumberView objects for element i and j numbers
        yield structx_elements


if __name__ == "__main__":

    # load msh and get nodes, elements, boundaries, and extents
    msh = _load_msh(MSH_FILE)
    msh_n_df, msh_e_df, msh_b_df = msh.nodes, msh.elements, msh.boundaries

    # define quad, tria, and extents portions of msh
    msh_quad_df = msh_e_df.loc[msh_e_df.i != msh_e_df.l]
    msh_tria_df = msh_e_df.loc[(msh_e_df.i == msh_e_df.l)]
    msh_ext_df = _extents(msh_n_df, msh_b_df)

    # TODO: resolve l node numbering depending on TRIA or QUAD element type

    # load msh into a Structure and clean it up in order to display and edit KEEP_INDEXES
    struct = build_struct_and_kept_indexes(show=False)

    # define structure/beam element df for each structure
    struct_elements = list(gen_struct_elements(struct, show=False))

    # define soil element dfs: quad and tria
    quad_elements = pd.DataFrame(index=msh_quad_df.index, columns=ELEMENT_COLUMNS)
    quad_elements.loc[:, "i":"l"] = msh_quad_df.values

    tria_elements = pd.DataFrame(index=msh_tria_df.index, columns=ELEMENT_COLUMNS)
    tria_elements.loc[:, "i":"l"] = msh_tria_df.values
    tria_elements.loc[:, "l"] = 0

    # define soil material and step zones
    mat_zones = region_containers(MAT_BOUNDS)
    dl_step_zones = region_containers(DL_STEP_BOUNDS)

    # set materials and steps for QUAD elements and TRIA elements
    for continuum_elements, continuum_type in zip(
        (quad_elements, tria_elements), (SoilElementType.quad, SoilElementType.tria)
    ):
        regionally_assign_continuum_type(
            continuum_elements, msh_n_df, continuum_type, mat_zones, dl_step_zones
        )

    # TODO: produce interfaces BEFORE concating structure elements with others (node numbering change)
    interf_elements = []
    for interfaces in INTERF_STRUCT_NODES:
        n_interf = len(interfaces)
        interf_index = range(1, n_interf + 1)
        interf_elements.append(
            pd.DataFrame(index=interf_index, columns=ELEMENT_COLUMNS)
        )
        # interf_elements["i"] = interf_nodes.index + msh_n_df.index[-1]
        # interf_elements["j"] = interf_nodes["n"]
        # interf_elements["k"] =
        # interf_elements["l"] = 0
        # interf_elements["mat"] = interf_nodes.index
        # interf_elements["step"] = 1
        # interf_elements["interf"] = 1

    # sanity check:
    assert len(interf_elements) == N_STRUCTS

    # combine QUAD and TRIA, into a single soil df
    soil_elements_no_interf = pd.concat([quad_elements, tria_elements]).sort_index()

    # combine, structure and soil into a single df, renumber to place beams first
    soil_elements_no_interf.index += sum(
        len(structx_elements) for structx_elements in struct_elements
    )
    # TODO: renumber struct elements to be sequential instead of starting over at 1
    elements_no_interf = pd.concat([*struct_elements, soil_elements_no_interf])
    elements_no_interf.index.name = "e"
    elements_no_interf["interf"] = 0

    # concat elements with interf elements
    elements = pd.concat([elements_no_interf, *interf_elements])
    elements.index.name = "e"

    # TODO: concat nodes with interf nodes
    nodes = msh_n_df.copy()

    # define boundaries df; use extends as starting point
    # TODO: add more options/user interaction/LL boundaries
    # TODO: handle correct steps for boundaries
    boundaries = msh_ext_df
    # sanity check
    assert boundaries.step.le(N_LL_STEPS if N_LL_STEPS else N_DL_STEPS).all()

    # prepare output lines
    C2 = C2_FMT.format(
        c2(
            elements.step.max() + N_LL_STEPS,
            nodes.index[-1],
            elements.index[-1],
            len(boundaries),
            elements.mat.max(),
            0,
        )
    )
    C3 = nodes.reset_index().apply(
        lambda s: C3_FMT.format(c3(**s)), axis=1, result_type="reduce"
    )
    C3[C3.index[-1]] = lastify(C3[C3.index[-1]])
    C4 = elements.reset_index().apply(
        lambda s: C4_FMT.format(c4(**s)), axis=1, result_type="reduce"
    )
    C4[C4.index[-1]] = lastify(C4[C4.index[-1]])
    # NOTE: boundaries df need not have reset_index() applied
    C5 = boundaries.apply(
        lambda s: C5_FMT.format(c5(**s)), axis=1, result_type="reduce"
    )
    C5[C5.index[-1]] = lastify(C5[C5.index[-1]])

    # TODO: prompt user for output path
    out = CANDE_FILE
    with out.open("w") as f:
        f.write(C2)
        f.write("\n")
        f.write("\n".join(C3))
        f.write("\n")
        f.write("\n".join(C4))
        f.write("\n")
        f.write("\n".join(C5))
        f.write("\n")

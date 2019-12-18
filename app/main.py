from pathlib import Path

import pandas as pd
from msh2cande.msh_load import _load_msh, _extents
from msh2cande.structure_build import Structure

element_columns = ("i", "j", "k", "l", "mat", "step")

KEEP_INDEXES = range(30, 119)

N_MATERIALS = 3
# material boundaries
MAT_BOUNDS = dict(
    minx=[-393.6, -393.6, -33.6],
    maxx=[702.88, 702.88, 342.88],
    miny=[-316.14, -196.14, -196.14],
    maxy=[-63.79, -63.79, -63.79],
)
# sanity check
for bound in MAT_BOUNDS.values():
    assert len(bound) == N_MATERIALS

N_DL_STEPS = 1
# material boundaries
DL_STEP_BOUNDS = dict(minx=[-393.6,], maxx=[702.88,], miny=[-316.14,], maxy=[-63.79,],)
# sanity check
for bound in DL_STEP_BOUNDS.values():
    assert len(bound) == N_DL_STEPS


if __name__ == "__main__":

    # load msh and get nodes, elements, boundaries, and extents
    msh = _load_msh(Path("mesh2.msh"))
    msh_n_df, msh_e_df, msh_b_df = msh.nodes, msh.elements, msh.boundaries

    # define quad, tria, and extents portions of msh
    msh_quad_df = msh_e_df.loc[msh_e_df.l != 0]
    msh_tria_df = msh_e_df.loc[(msh_e_df.l == 0) & (msh_e_df.k != 0)]
    msh_ext_df = _extents(msh_n_df, msh_b_df)

    # TODO: resolve l node numbering depending on TRIA or QUAD element type

    # load msh into a Structure and clean it up
    struct = Structure(msh_b_df, msh_n_df, msh_e_df, msh_ext_df)
    # USER INPUT: struct.show_candidates()
    struct.candidates_df = struct.candidates_df.loc[[*KEEP_INDEXES], :]

    # define structure nodes
    struct_nodes = struct.candidates_df
    struct_nodes.index = range(1, len(struct_nodes) + 1)
    # USER INPUT: struct.show_candidates()

    # define struct element df; assume non-contiguous structure, load step 1, material 1, left to right connectivity
    struct_elements = pd.DataFrame(
        index=range(1, len(struct_nodes)), columns=element_columns
    )
    struct_elements.k = 0
    struct_elements.l = 0
    struct_elements.mat = 1
    struct_elements.step = 1
    struct_elements.i = struct_nodes.loc[2:, "n"].values
    struct_elements.j = struct_nodes.loc[: len(struct_nodes) - 1, "n"].values

    # define quad soil element dfs: quad and tria
    quad_elements = pd.DataFrame(index=msh_quad_df.index, columns=element_columns)
    quad_elements.loc[:, "i":"l"] = msh_quad_df.values
    tria_elements = pd.DataFrame(index=msh_tria_df.index, columns=element_columns)
    tria_elements.loc[:, "i":"l"] = msh_tria_df.values

    # define soil material and step zones
    mat_zones = pd.DataFrame(MAT_BOUNDS, index=range(1, N_MATERIALS + 1))
    dl_step_zones = pd.DataFrame(DL_STEP_BOUNDS, index=range(1, N_DL_STEPS + 1))

    # set materials for QUAD elements
    m_indexes = quad_elements.index, list("ijkl")
    quad_mat_multi_e_ijkl = pd.DataFrame(
        index=pd.MultiIndex.from_product(m_indexes), columns=["x", "y"]
    )
    quad_mat_multi_e_ijkl.loc[(slice(None), "i"), :] = msh_n_df.loc[
        quad_elements.loc[:, "i"]
    ].values
    quad_mat_multi_e_ijkl.loc[(slice(None), "j"), :] = msh_n_df.loc[
        quad_elements.loc[:, "j"]
    ].values
    quad_mat_multi_e_ijkl.loc[(slice(None), "k"), :] = msh_n_df.loc[
        quad_elements.loc[:, "k"]
    ].values
    quad_mat_multi_e_ijkl.loc[(slice(None), "l"), :] = msh_n_df.loc[
        quad_elements.loc[:, "l"]
    ].values
    quad_center = pd.DataFrame(index=quad_elements.index, columns=["cx", "cy"])
    quad_center.loc[:, :] = (
        quad_mat_multi_e_ijkl.sum(level=0) / len(m_indexes[1])
    ).values
    for mat_num, mat_zone in mat_zones.transpose().iteritems():
        idx = (
            (quad_center.cx.gt(mat_zone["minx"]))
            & (quad_center.cx.lt(mat_zone["maxx"]))
            & (quad_center.cy.gt(mat_zone["miny"]))
            & (quad_center.cy.lt(mat_zone["maxy"]))
        )
        quad_elements.loc[idx, "mat"] = mat_num

    # set steps for QUAD elements
    quad_elements.loc[:, "step"] = 1

    # TODO: set materials and steps for TRIA elements

    # TODO: produce interfaces BEFORE concating structure elements with others (node numbering change)

    # combine, structure, QUAD, TRIA, into a single soil df, renumber to place beams first
    soil_elements = pd.concat([quad_elements, tria_elements]).sort_index()
    soil_elements.index += len(struct_elements)
    elements_no_interf = pd.concat([struct_elements, soil_elements])

    # TODO: concat elements with interf elements

    # TODO: concat nodes with interf nodes

    # TODO: fill out columns for boundaries

    # TODO: save formatted output
    ...

import pandas as pd
from enum import IntEnum, Enum, auto
import shapely.geometry as sg

ELEMENT_COLUMNS = ("i", "j", "k", "l", "mat", "step")
BOUNDARY_COLUMNS = ("n", "xcode", "xvalue", "ycode", "yvalue", "angle", "step")

CANDE_PREFIX_FMT = "{: >25s}!!"
C2_FMT = f"{CANDE_PREFIX_FMT.format('C-2.L3')}{{}}"
C3_FMT = f"{CANDE_PREFIX_FMT.format('C-3.L3')} {{}}"
C4_FMT = f"{CANDE_PREFIX_FMT.format('C-4.L3')} {{}}"
C5_FMT = f"{CANDE_PREFIX_FMT.format('C-5.L3')} {{}}"


def lastify(s, idx=27):
    """Add the L at the end of applicable CANDE sections."""
    return s[:idx] + "L" + s[idx + 1 :]


class Connectivity(IntEnum):
    """Used to indicate whether a structure's connectivity is:
        A. continuous (like a pipe) or
        B. noncontinguous (like an arch).
    """

    contiguous = 0
    noncontiguous = 1


class SoilElementType(Enum):
    """Differentiate between QUAD (4-sided) elements and TRIA (3-sided) elements."""

    quad = auto()
    tria = auto()


def region_containers(source):
    """Build the container sequences using the source file (DXF format, probably)."""

    # TODO: change function over to DXF2SHAPELY
    return pd.DataFrame(source)

def regionally_assign_continuum_type(
    continuum_df, nodes_df, continuum_element_type, mat_zones, dl_step_zones
):
    """Assign the per-record value of a column based on the geometry of the element record.

    NOTE: all of the continuum elements in the supplied df must be either QUAD or TRIA elements. No mixing.

    If the center of an element is in a region, it's column will be assigned the corresponding value. If a element
    record is in multiple regions, it will be assigned to them in the order they were supplied and the final
    assignment wins.
    """

    # TODO: change function to use POLYGONTAGGER
    node_names = {
        SoilElementType.quad: list("ijkl"),
        SoilElementType.tria: list("ijk"),
    }.get(continuum_element_type, None)

    multi_indexes = continuum_df.index, node_names
    multi_e_df = pd.DataFrame(
        index=pd.MultiIndex.from_product(multi_indexes), columns=["x", "y"]
    )

    for node_name in node_names:
        multi_e_df.loc[(slice(None), node_name), :] = nodes_df.loc[
            continuum_df.loc[:, node_name]
        ].values

    center_df = pd.DataFrame(index=continuum_df.index, columns=["cx", "cy"])

    center_df.loc[:, :] = (multi_e_df.sum(level=0) / len(multi_indexes[1])).values
    center_df['sg_point'] = [sg.Point(x,y) for x,y in zip(center_df['cx'], center_df['cy'])]

    for mat_num in mat_zones:
        mat_polygon = sg.Polygon(mat_zones[mat_num].dropna())
        mat_idx = center_df['sg_point'].apply(mat_polygon.contains)
        continuum_df.loc[mat_idx, 'mat'] = mat_num

        for mat_range in dl_step_zones:
            if mat_num in mat_range:
                dl_y_values = dl_step_zones[mat_range].dropna()
                for step_num, y_value in dl_y_values.iteritems():
                    step_idx = mat_idx & (center_df['cy'] > y_value)
                    continuum_df.loc[step_idx, 'step'] = step_num

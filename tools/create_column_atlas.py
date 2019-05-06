#!/usr/bin/env python
"""
Build artificial atlas.
"""
import os
import json
import logging
import itertools
from collections import OrderedDict

import click
import numpy as np

from six import iteritems

from voxcell import build, math_utils, VoxelData


L = logging.getLogger(__name__)


def _compact(mask):
    """ Trim zero values on mask borders. """
    aabb = math_utils.minimum_aabb(mask)
    return math_utils.clip(mask, aabb)


def _build_2D_mosaic(width, hex_side, voxel_side):
    """ Build 2D matrix representing O<K> mosaic. """
    hexagon = _compact(build.regular_convex_polygon_mask_from_side(hex_side, 6, voxel_side))
    w, h = hexagon.shape

    hex_center = {
        0: [
            [0, 0]
        ],
        1: [
            [1, 1],
            [0, 2],
            [1, 3],
            [2, 2],
            [0, 4],
            [1, 5],
            [2, 4],
        ]
    }[width]

    shift = np.array(hex_center) * (3 * w // 4, h // 2)

    shape = np.max(shift, axis=0) + (w, h)
    mosaic = np.full(shape, -1, dtype=np.int16)
    for column, (dx, dz) in enumerate(shift):
        mosaic[dx:dx + w, dz:dz + h][hexagon] = column

    offset = -0.5 * np.array([w, h]) * voxel_side
    return mosaic, offset


def _build_brain_regions(width, hex_side, layers, voxel_side):
    """ Build 'brain_regions' VoxelData. """
    mosaic_2D, offset_2D = _build_2D_mosaic(width, hex_side, voxel_side)
    mosaic_3d_layers = []

    columns = np.unique(mosaic_2D[mosaic_2D >= 0])

    region_ids = OrderedDict(
        ((column, None), k) for k, column in enumerate(columns, 1)
    )

    for name, thickness in iteritems(layers):
        pattern = np.zeros_like(mosaic_2D, dtype=np.uint16)
        for column in columns:
            region_id = max(region_ids.values()) + 1
            region_ids[(column, name)] = region_id
            pattern[mosaic_2D == column] = region_id
        mosaic_3d_layers.append(
            np.repeat([pattern], thickness // voxel_side, axis=0)
        )

    mosaic_3D = np.swapaxes(
        np.vstack(mosaic_3d_layers),
        0, 1
    )
    offset_3D = np.array([offset_2D[0], 0, offset_2D[1]])

    brain_regions = VoxelData(mosaic_3D, 3 * (voxel_side,), offset_3D).compact()

    # Add zero-voxel margin for better rendering
    margin = 1
    brain_regions = VoxelData(
        np.pad(brain_regions.raw, margin, 'constant', constant_values=0),
        brain_regions.voxel_dimensions,
        brain_regions.offset - margin * brain_regions.voxel_dimensions
    )

    return brain_regions, region_ids


def _initialize_raw(brain_regions, dtype, value, add_dim=0):
    """Initialize a np array that will contain atlas raw """
    if add_dim > 0:
        shape = brain_regions.shape + (add_dim,)
    else:
        shape = brain_regions.shape
    layer_array = np.full(shape, value, dtype=dtype)
    return layer_array


def _build_orientation(brain_regions):
    """ Build 'orientation' VoxelData. """
    raw = _initialize_raw(brain_regions, np.int8, 0, add_dim=4)
    raw[:, :, :, 0] = 127
    return brain_regions.with_data(raw)


def _build_layer_profil(brain_regions, boundaries):
    """ Build '[PH]<layer>' VoxelData. """
    raw = _initialize_raw(brain_regions, np.float32, np.nan, add_dim=2)
    for j in range(brain_regions.raw.shape[1]):
        raw[:, j, :] = list(boundaries)
    return brain_regions.with_data(raw)


def _build_y(brain_regions):
    """ Build '[PH]y' VoxelData. """
    raw = _initialize_raw(brain_regions, np.float32, np.nan)
    voxel_side = brain_regions.voxel_dimensions[1]
    for j in range(brain_regions.raw.shape[1]):
        raw[:, j, :] = brain_regions.offset[1] + voxel_side * (0.5 + j)
    return brain_regions.with_data(raw)


def _normalize_hierarchy(hierarchy):
    """ Sort keys in hierarchy dict. """
    result = OrderedDict((key, hierarchy[key]) for key in ['id', 'acronym', 'name'])
    if 'children' in hierarchy:
        result['children'] = [_normalize_hierarchy(c) for c in hierarchy['children']]
    return result


def _column_hierarchy(column, layers, region_ids):
    """ Build 'hierarchy' dict for single hypercolumn. """
    return OrderedDict([
        ('id', region_ids[(column, None)]),
        ('acronym', "mc{}_Column".format(column)),
        ('name', "hypercolumn {}".format(column)),
        ('children', [OrderedDict([
            ('id', region_ids[(column, layer)]),
            ('acronym', 'mc{};{}'.format(column, layer)),
            ('name', "hypercolumn {}, {}".format(column, layer))
        ]) for layer in layers])
    ])


def _mosaic_hierarchy(width, layers, region_ids):
    """ Build 'hierarchy' dict for 'mosaic' atlas. """
    COLUMNS = sorted(set(column for column, _ in region_ids))
    return OrderedDict([
        ('id', 65535),
        ('acronym', "O{}".format(width)),
        ('name', "O{} mosaic".format(width)),
        ('children', [_column_hierarchy(c, layers, region_ids) for c in COLUMNS])
    ])


def _align_thickness(thickness, voxel_side):
    """ Align layer boundaries along voxel grid. """
    result = []
    y0 = 0
    for y1 in np.cumsum(thickness):
        dy = voxel_side * max(1, np.round(y1) // voxel_side - y0 // voxel_side)
        y0 = y0 + dy
        result.append(dy)
    return result


def _add_layers_datasets(datasets, layers, brain_regions):
    """ Update the layer dataset with layer profiles """
    def _pairwise(iterable):
        """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    thickness_cumsum = [0.] + list(np.cumsum(list(layers.values())))
    boundaries = np.array(list(_pairwise(thickness_cumsum)))
    for (name, _), bounds in zip(layers.items(), boundaries):
        datasets.update({'[PH]' + name: _build_layer_profil(brain_regions, bounds)})


@click.command()
@click.option('-w', '--width', type=int, help="Mosaic width (0 for single column)", default=0)
@click.option('-a', '--hex-side', type=float, help="Hexagon side (um)", required=True)
@click.option('-n', '--layer-names',
              help="Layer's names as they appear going from 'bottom' to 'top'", required=True)
@click.option('-t', '--thickness', help="Layer thickness (um)", required=True)
@click.option('-d', '--voxel-side', type=float, help="Voxel side (um)", required=True)
@click.option('-o', '--output-dir', help="Path to output folder", required=True)
def app(width, hex_side, layer_names, thickness, voxel_side, output_dir):
    """ Build hexagonal column mosaic atlas """

    logging.basicConfig(level=logging.WARN)
    L.setLevel(logging.INFO)

    assert width in (0, 1)

    names = layer_names.split(",")
    raw_thickness = list(map(float, thickness.split(",")))
    assert len(names) == len(raw_thickness)

    aligned_thickness = _align_thickness(raw_thickness, voxel_side)
    L.info("Layer thickness aligned to voxel grid: %s", ",".join(map(str, aligned_thickness)))
    L.info("Total thickness before aligment: %s", sum(raw_thickness))
    L.info("Total thickness after aligment: %s", sum(aligned_thickness))

    layers = OrderedDict(zip(names, aligned_thickness))

    output_dir = os.path.abspath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    brain_regions, region_ids = _build_brain_regions(width, hex_side, layers, voxel_side)

    datasets = {
        'brain_regions': brain_regions,
        'orientation': _build_orientation(brain_regions),
        '[PH]y': _build_y(brain_regions),
    }
    _add_layers_datasets(datasets, layers, brain_regions)

    hierarchy = _mosaic_hierarchy(width, names, region_ids)

    for name, data in iteritems(datasets):
        L.info("Write '%s.nrrd'...", name)
        data.save_nrrd(os.path.join(output_dir, name + ".nrrd"))

    L.info("Write 'hierarchy.json'...")
    with open(os.path.join(output_dir, "hierarchy.json"), "w") as f:
        json.dump(_normalize_hierarchy(hierarchy), f, indent=2)

    L.info("Done!")


if __name__ == '__main__':
    app()

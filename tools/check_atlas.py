#!/usr/bin/env python3

"""
Smoke test if VoxelBrain atlas can be used for circuit building.

Checks implemented:

 - load 'brain_regions'
 - load 'hierarchy'
 - ensure 'hierarchy' does not contain region ID = 0 (this value is treated as "no region")
 - check if all values in 'brain_regions' are found in 'hierarchy'
 - load 'orientation' as OrientationField
 - if placement rules XML specified, check that '[PH]y' and '[PH]<layer>' datasets are available
 - if cell composition YAML specified, check that all datasets used there are available

Passing these checks does give 100% guarantee circuit building will run successfully.
"""

import argparse
import shutil
import sys
import tempfile
import traceback

from xml.etree import ElementTree as ET

import warnings
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import yaml

from numpy.testing import assert_equal as eq_

from voxcell import OrientationField
from voxcell.nexus.voxelbrain import Atlas


def require(cond, msg):
    if not cond:
        raise Exception(msg)


def check_aligned(vd, ref_vd):
    eq_(vd.shape, ref_vd.shape, "Space shape")
    eq_(vd.voxel_dimensions, ref_vd.voxel_dimensions, "Spacings")
    eq_(vd.offset, ref_vd.offset, "Offset")


class CheckHierarchy:
    def __init__(self):
        self.title = "hierarchy"

    def __call__(self, atlas, brain_regions):
        hierarchy = atlas.load_hierarchy()
        require(
            not hierarchy.find('id', 0),
            "Hierarchy contains region ID = 0"
        )
        for rid in np.unique(brain_regions.raw):
            if rid == 0:
                continue
            require(
                hierarchy.find('id', rid),
                "Region ID = %d not found in hierarchy" % rid
            )


class CheckVoxelData:
    def __init__(self, name, payload_shape=()):
        self.name = name
        self.payload_shape = payload_shape

    @property
    def title(self):
        return self.name

    def __call__(self, atlas, brain_regions):
        data = atlas.load_data(self.name)
        eq_(data.payload_shape, self.payload_shape, "Payload shape")
        check_aligned(data, brain_regions)
        del data


class CheckOrientationField:
    def __init__(self):
        self.title = "orientation"

    def __call__(self, atlas, brain_regions):
        data = atlas.load_data('orientation', cls=OrientationField)
        check_aligned(data, brain_regions)
        del data


def collect_layer_names(rules_path):
    result = set()
    for elem in ET.parse(rules_path).iter('rule'):
        for name in ('y_layer', 'y_min_layer', 'y_max_layer'):
            attr = elem.attrib.get(name)
            if attr is not None:
                result.add(attr)
    return result


def collect_mtype_densities(composition_path):
    with open(composition_path, 'r') as f:
        composition = yaml.load(f)['composition']

    result = set()
    for region, region_group in composition.iteritems():
        for mtype, mtype_group in region_group.iteritems():
            value = str(mtype_group['density'])
            if value.startswith("{"):
                assert value.endswith("}")
                result.add(value[1:-1])

    return result


def run_checks(checks, atlas):
    brain_regions = atlas.load_data('brain_regions')

    result = True
    for check in checks:
        message = check.title + "... "
        try:
            check(atlas, brain_regions)
            message += "\033[92mPASS\033[0m"
        except Exception:
            traceback.print_exc()
            message += "\033[91mFAIL\033[0m"
            result = False
        print(message)

    return result


def main(args):
    checks = [
        CheckHierarchy(),
        CheckOrientationField(),
    ]

    if args.placement_rules:
        layers = collect_layer_names(args.placement_rules)
        assert 'y' not in layers
        checks.append(CheckVoxelData('[PH]y'))
        for layer in layers:
            checks.append(CheckVoxelData('[PH]%s' % layer, payload_shape=(2,)))

    if args.cell_composition:
        mtype_densities = collect_mtype_densities(args.cell_composition)
        for name in mtype_densities:
            checks.append(CheckVoxelData(name))

    tmpdir = tempfile.mkdtemp()
    try:
        atlas = Atlas.open(args.url, cache_dir=tmpdir)
        all_pass = run_checks(checks, atlas)
    finally:
        shutil.rmtree(tmpdir)

    if not all_pass:
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Check atlas for compatibility with circuit-build pipeline."
    )
    parser.add_argument(
        "url",
        help="Atlas folder / URL"
    )
    parser.add_argument(
        "--cell-composition",
        default=None,
        help="Path to cell composition file (YAML)"
    )
    parser.add_argument(
        "--placement-rules",
        default=None,
        help="Path to placement rules file (XML)"
    )
    main(parser.parse_args())

#!/usr/bin/env python

import sys

import numpy as np

from voxcell.nexus.voxelbrain import Atlas


if __name__ == "__main__":
    atlas = Atlas.open(sys.argv[1])
    y = atlas.load_data("[PH]y")
    y.with_data(y.raw).save_nrrd("depth.nrrd")
    for k in range(1, 7):
        ll = atlas.load_data("[PH]%d" % k)
        assert np.all(ll.raw[..., 1] >= ll.raw[..., 0])
        ll.with_data(ll.raw[..., 1] - ll.raw[..., 0]).save_nrrd("thickness:L%d.nrrd" % k)

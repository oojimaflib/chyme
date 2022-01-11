"""
 Summary:

    Contains classes for Flood Modeller River Section units

 Author:

    Gerald Morgan

 Created:

    11 Jan 2022

"""

from ..units import ReachFormingUnit

from chyme.sections import XZCrossSection
from chyme.utils.series import Series

class RiverSectionUnitCrossSection(XZCrossSection):
    """Class representing a cross-section from a Flood Modeller network.
    """
    def __init__(self, io_xs):
        xz = Series([[xsp.x, xsp.z] for xsp in io_xs])
        super().__init__(xz)
        self.n_series = Series([[xsp.x, xsp.n] for xsp in io_xs],
                               interpolate_method='stepwise')
        self.rpl_series = Series([[xsp.x, xsp.rpl] for xsp in io_xs])
        self.loc_series = Series([[xsp.x, xsp.easting, xsp.northing]
                                  for xsp in io_xs])

        self.panel_boundaries = []
        if not io_xs[0].panel == '*':
            self.panel_boundaries.append(io_xs[0].x)
        for xsp in io_xs:
            if xsp.panel == '*':
                self.panel_boundaries.append(xsp.x)
        if not io_xs[-1].panel == '*':
            self.panel_boundaries.append(io_xs[-1].x)

        self.left_bank_x = io_xs[0].x
        self.right_bank_x = io_xs[-1].x
        self.bed_x = io_xs[0].x
        self.active_from = io_xs[0].x
        self.active_to = io_xs[-1].x
        
        bed_z = max([xsp.z for xsp in io_xs]) + 10.0
        for xsp in io_xs:
            if xsp.bank_marker == 'LEFT':
                self.left_bank_x = xsp.x
            if xsp.bank_marker == 'RIGHT':
                self.right_bank_x = xsp.x
            if xsp.bank_marker == 'BED':
                self.bed_x = xsp.x
                bed_z = min([xsp.z for xsp in io_xs]) - 10.0
            if xsp.z < bed_z:
                bed_z = xsp.z
                self.bed_x = xsp.x
            if xsp.deactivation_marker == 'LEFT':
                self.active_from = xsp.x
            if xsp.deactivation_marker == 'RIGHT':
                self.active_to = xsp.x

class RiverSectionUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.cross_section = RiverSectionUnitCrossSection(io.xs)
        


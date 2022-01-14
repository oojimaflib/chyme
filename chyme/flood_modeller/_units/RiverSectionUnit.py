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
    def __init__(self, io_xs = None, *args,
                 xz_series = None, thalweg = None, **kwargs):
        if io_xs is not None:
            xz = Series([[xsp['x'], xsp['z']] for xsp in io_xs])
            super().__init__(xz)
            self.n_series = Series([[xsp['x'], xsp['n']] for xsp in io_xs],
                                   interpolate_method='stepwise')
            self.rpl_series = Series([[xsp['x'], xsp['rpl']] for xsp in io_xs])
            self.loc_series = Series([[xsp['x'],
                                       xsp['easting'], xsp['northing']]
                                      for xsp in io_xs])

            self.panel_boundaries = []
            if not io_xs[0]['panel'] == '*':
                self.panel_boundaries.append(io_xs[0]['x'])
            for xsp in io_xs:
                if xsp['panel'] == '*':
                    self.panel_boundaries.append(xsp['x'])
            if not io_xs[-1]['panel'] == '*':
                self.panel_boundaries.append(io_xs[-1]['x'])

            self.left_bank_x = io_xs[0]['x']
            self.right_bank_x = io_xs[-1]['x']
            self.bed_x = io_xs[0]['x']
            self.active_from = io_xs[0]['x']
            self.active_to = io_xs[-1]['x']
        
            bed_z = max([xsp['z'] for xsp in io_xs]) + 10.0
            for xsp in io_xs:
                if xsp['bank_marker'] == 'LEFT':
                    self.left_bank_x = xsp['x']
                if xsp['bank_marker'] == 'RIGHT':
                    self.right_bank_x = xsp['x']
                if xsp['bank_marker'] == 'BED':
                    self.bed_x = xsp['x']
                    bed_z = min([xsp['z'] for xsp in io_xs]) - 10.0
                if xsp['z'] < bed_z:
                    bed_z = xsp['z']
                    self.bed_x = xsp['x']
                if xsp['deactivation_marker'] == 'LEFT':
                    self.active_from = xsp['x']
                if xsp['deactivation_marker'] == 'RIGHT':
                    self.active_to = xsp['x']
        else:
            super().__init__(xz_series, thalweg=thalweg)

    def active_section(self):
        active_xh = Series(list(filter(lambda pt: pt[0] >= self.active_from and pt[0] <= self.active_to, self.xh_series)))
        active_n = Series(list(filter(lambda pt: pt[0] >= self.active_from and pt[0] <= self.active_to, self.n_series)))
        active_rpl = Series(list(filter(lambda pt: pt[0] >= self.active_from and pt[0] <= self.active_to, self.rpl_series)))
        active_loc = Series(list(filter(lambda pt: pt[0] >= self.active_from and pt[0] <= self.active_to, self.loc_series)))
        
        panel_boundaries = [self.active_from]
        for opb in filter(lambda x: x > self.active_from and x < self.active_to, self.panel_boundaries):
            panel_boundaries.append(opb)
        panel_boundaries.append(self.active_to)
        
        left_bank_x = self.active_from
        if self.left_bank_x > self.active_from and self.left_bank_x < self.active_to:
            left_bank_x = self.left_bank_x
        right_bank_x = self.active_to
        if self.right_bank_x > self.active_from and self.right_bank_x < self.active_to:
            right_bank_x = self.right_bank_x
            
        min_x = 0.0
        min_z = max([pt[1] for pt in active_xh]) + 10.0
        for pt in active_xh:
            if pt[1] < min_z:
                min_x = pt[0]
                min_z = pt[1]
        if self.bed_x > self.active_from and self.bed_x < self.active_to:
            bed_x = self.bed_x
        else:
            bed_x = min_x
        
        active_sec = RiverSectionUnitCrossSection(xz_series = active_xh,
                                                  thalweg = min_z + self.thalweg)
        active_sec.n_series = active_n
        active_sec.rpl_series = active_rpl
        active_sec.loc_series = active_loc
        active_sec.panel_boundaries = panel_boundaries
        active_sec.left_bank_x = left_bank_x
        active_sec.right_bank_x = right_bank_x
        active_sec.bed_x = bed_x
        active_sec.active_from = active_xh[0][0]
        active_sec.active_to = active_xh[-1][0]

        return active_sec
                
    def num_panels(self):
        return len(self.panel_boundaries) - 1

class RiverSectionUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.cross_section = RiverSectionUnitCrossSection(io.values['xs'])
        


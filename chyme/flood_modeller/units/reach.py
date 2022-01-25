"""
 Summary:

    Contains classes for Flood Modeller Reach-Forming units

 Author:

    Gerald Morgan

 Created:

    11 Jan 2022

"""

from chyme.sections import XZCrossSection
from chyme.utils.series import Series

from .core import FloodModellerUnit

class ReachFormingUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.chainage = io.values['chainage']

    def is_reach_component(self):
        return True


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

            rpl_points = list(filter(lambda x: x[1] is not None,
                                     [[xsp['x'], xsp['rpl']] for xsp in io_xs]))
            if len(rpl_points) > 1:
                self.rpl_series = Series(rpl_points)
            else:
                self.rpl_series = None

            loc_points = list(filter(lambda x: x[1] is not None and x[2] is not None,
                                     [[xsp['x'],
                                       xsp['easting'], xsp['northing']]
                                      for xsp in io_xs]))
            if len(loc_points) > 1:
                self.loc_series = Series(loc_points)
            else:
                self.loc_series = None

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

    def sub_section(self, from_x, to_x):
        within_range = lambda pt: pt[0] >= from_x and pt[0] <= to_x

        sub_xh = Series(list(filter(within_range, self.xh_series)))
        sub_n = Series(list(filter(within_range, self.n_series)))
        sub_rpl = Series(list(filter(within_range, self.rpl_series)))
        sub_loc = Series(list(filter(within_range, self.loc_series)))

        panel_boundaries = [from_x]
        for opb in filter(lambda x: x > from_x and x < to_x,
                          self.panel_boundaries):
            panel_boundaries.append(opb)
        panel_boundaries.append(self.active_to)

        left_bank_x = from_x
        if self.left_bank_x > from_x and self.left_bank_x < to_x:
            left_bank_x = self.left_bank_x
        right_bank_x = to_x
        if self.right_bank_x > from_x and self.right_bank_x < to_x:
            right_bank_x = self.right_bank_x
        
        min_x = 0.0
        min_z = max([pt[1] for pt in sub_xh]) + 10.0
        for pt in sub_xh:
            if pt[1] < min_z:
                min_x = pt[0]
                min_z = pt[1]
        if self.bed_x > from_x and self.bed_x < to_x:
            bed_x = self.bed_x
        else:
            bed_x = min_x
        
        active_from = from_x
        if self.active_from > from_x and self.active_from < to_x:
            active_from = self.active_from
        active_to = to_x
        if self.active_to > from_x and self.active_to < to_x:
            active_to = self.active_to
        
        subsec = RiverSectionUnitCrossSection(xz_series = sub_xh,
                                              thalweg = min_z + self.thalweg)
        subsec.n_series = sub_n
        subsec.rpl_series = sub_rpl
        subsec.loc_series = sub_loc
        subsec.panel_boundaries = panel_boundaries
        subsec.left_bank_x = left_bank_x
        subsec.right_bank_x = right_bank_x
        subsec.bed_x = bed_x
        subsec.active_from = active_from
        subsec.active_to = active_to

        return subsec
            
    def active_section(self):
        return self.sub_section(self.active_from, self.active_to)
                
    def num_panels(self):
        return len(self.panel_boundaries) - 1

    def panel(self, index):
        return self.sub_section(self.panel_boundaries[index],
                                self.panel_boundaries[index + 1])

    def mean_n_between(self, x0, x1):
        nwtot = 0.0
        wtot = 0.0
        for pt0, pt1 in self.n_series.pairwise():
            if pt0[0] >= x0 and pt0[0] < x1:
                if pt1[0] >= x0 and pt1[0] < x1:
                    # This manning n segment is entirely contained
                    # within the range
                    wtot += pt1[0] - pt0[0]
                    nwtot += (pt1[0] - pt0[0]) * pt0[1]
                else:
                    # This manning n segment starts within the range
                    # and ends outside it
                    wtot += x1 - pt0[0]
                    nwtot += (x1 - pt0[0]) * pt0[1]
                    # This must be the last segment
                    break
            else:
                if pt1[0] >= x0 and pt1[0] < x1:
                    # This manning n segment starts outside the range
                    # and ends inside it
                    wtot += pt1[0] - x0
                    nwtot += (pt1[0] - x0) * pt0[1]
                else:
                    # This n segment is entirely outside the range
                    pass
        return nwtot / wtot
    
    def mean_n(self, depth = None):
        nptot = 0.0
        ptot = 0.0
        if depth is None:
            for pt0, pt1 in self.xh_series.pairwise():
                dx = pt1[0] - pt0[0]
                dy = pt1[1] - pt0[1]
                p = math.sqrt(dx*dx + dy*dy)
                n = self.mean_n_between(pt0[0], pt1[0])
                nptot += n*p
                ptot += p
            return np/p
        else:
            for pt0, pt1 in self.xh_series.pairwise():
                dx = 0.0
                dy = 0.0
                n = 0.0
                if p0[1] <= depth and p1[1] <= depth:
                    # If both points are below the water level, then the
                    # full length of this segment is added
                    dx = p1[0] - p0[0]
                    dy = p1[1] - p0[1]
                    n = self.mean_n_between(p0[0], p1[0])
                elif p0[1] <= depth:
                    # If only the first point is below, use linear
                    # interpolation to get the width below the waterline
                    dy = depth - p0[1]
                    ratio = dy / (p1[1] - p0[1])
                    dx = ratio * (p1[0] - p0[0])
                    n = self.mean_n_between(p0[0], p0[0] + dx)
                elif p1[1] <= depth:
                    # And similarly if only the second point is below
                    dy = depth - p1[1]
                    ratio = dy / (p0[1] - p1[1])
                    dx = ratio * (p1[0] - p0[0])
                    n = self.mean_n_between(p1[0] - dx, p1[0])
                # If neither point was below we do nothing.
                if n > 0.0:
                    p = math.sqrt(dx*dx + dy*dy)
                    ptot += p
                    nptot += n*p
        return nptot / ptot

    
    
    
class RiverSectionUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.cross_section = RiverSectionUnitCrossSection(io.values['xs'])
        
class RegularConduitUnit(ReachFormingUnit):
    friction_methods = ['MANNING', 'COLEBROOK-']
    
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.friction_method = self.friction_methods.index(io.values['friction_method'])
        self.invert = io.values['invert']
        
        if io.values['bottom_slot_flag'] == 'ON':
            self.bottom_slot = ( io.values['bottom_slot_height'],
                                 io.values['bottom_slot_depth'] )
        elif io.values['bottom_slot_flag'] == 'GLOBAL':
            self.bottom_slot = ( None, None )
        elif io.values['bottom_slot_flag'] == 'OFF':
            self.bottom_slot = None
        else:
            raise RuntimeError("Invalid value for bottom slot flag: {}".format(io.values['bottom_slot_flag']))
        if io.values['top_slot_flag'] == 'ON':
            self.top_slot = ( io.values['top_slot_height'],
                                 io.values['top_slot_depth'] )
        elif io.values['top_slot_flag'] == 'GLOBAL':
            self.top_slot = ( None, None )
        elif io.values['top_slot_flag'] == 'OFF':
            self.top_slot = None
        else:
            raise RuntimeError("Invalid value for top slot flag.")

class CircularConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.diameter = io.values['diameter']
        self.bottom_friction = io.values['bottom_friction']
        self.top_friction = io.values['top_friction']
        
class RectangularConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.height = io.values['height']
        self.bottom_friction = io.values['bottom_friction']
        self.side_friction = io.values['side_friction']
        self.top_friction = io.values['top_friction']
        
class FullArchConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.height = io.values['height']
        self.bottom_friction = io.values['bottom_friction']
        self.arch_friction = io.values['arch_friction']
        
class SprungArchConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.springing_height = io.values['springing_height']
        self.arch_height = io.values['arch_height']
        self.bottom_friction = io.values['bottom_friction']
        self.side_friction = io.values['side_friction']
        self.arch_friction = io.values['arch_friction']
        
class InterpolateUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.easting = io.values['easting']
        self.northing = io.values['northing']

class ReplicateUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.bed_drop = io.values['bed_drop']
        self.easting = io.values['easting']
        self.northing = io.values['northing']

class MuskinghamVPMCUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CESSectionUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)



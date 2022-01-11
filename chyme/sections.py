"""
 Summary:

    Contains classes for representing cross-sections

 Author:

    Gerald Morgan

 Created:

    10 Jan 2022

"""

from .utils.series import Series
from copy import deepcopy
import math

class CrossSection:
    """Generic class representing a cross-section through a watercourse.

    Attributes:
        thalweg: bottom bed level of the cross-section.
    """
    def __init__(self, thalweg):
        """Constructor.

        Args:
            thalweg: the bottom bed level of the cross-section.
        """
        self.thalweg = thalweg

    def depth(self, water_level):
        return water_level - self.thalweg

    def water_level(self, depth):
        return self.thalweg + depth

    def top_width(self, depth):
        raise NotImplementedError()

    def wetted_perimeter(self, depth):
        raise NotImplementedError()

    def wetted_area(self, depth):
        raise NotImplementedError()

    def hydraulic_radius(self, depth):
        return self.wetted_area(depth) / self.wetted_perimeter(depth)

class XZCrossSection(CrossSection):
    """Class representing a cross-section as an X-Z series.

    Attributes:
        xh_series: a utils.Series object containing the cross-chainage and 
            elevation data relative to the section thalweg
    """
    def __init__(self,
                 xz_series,
                 *args,
                 thalweg = None):
        """Constructor.

        Args:
            xz_series: a utils.Series object expected to contain at
                least 2 dimensions with dimension 0 being the
                cross-chainage and dimension 1 being the elevation.
            thalweg: optional. The value of the bed level. If this is
                specified the series will be shifted vertically to
                force the lowest bed level to be this value.

        """
        data_minz = min([x[1] for x in xz_series])
        if thalweg is None:
            super().__init__(data_minz)
        else:
            super().__init__(thalweg)

        # We make a deep copy of our series so we can edit it at our
        # leisure
        self.xh_series = deepcopy(xz_series)
        # We adjust the series vertically so that the bottom of the
        # series is always at zero (the bed level is stored already in
        # self.thalweg)
        self.xh_series.datum[1] -= data_minz

    def top_width(self, depth):
        width = 0.0
        for p0, p1 in self.xh_series.pairwise():
            # Loop over pairs of points in the cross-section
            if p0[1] <= depth and p1[1] <= depth:
                # If both points are below the water level, then the
                # full width of this segment is added
                width += (p1[0] - p0[0])
            elif p0[1] <= depth:
                # If only the first point is below, use linear
                # interpolation to get the width below the waterline
                ratio = (depth - p0[1]) / (p1[1] - p0[1])
                width += ratio * (p1[0] - p0[0])
            elif p1[1] <= depth:
                # And similarly if only the second point is below
                ratio = (depth - p1[1]) / (p0[1] - p1[1])
                width += ratio * (p1[0] - p0[0])
            # If neither point was below we do nothing.
        return width

    def wetted_perimeter(self, depth):
        wp = 0.0
        for p0, p1 in self.xh_series.pairwise():
            # Loop over pairs of points in the cross-section
            dx = 0.0
            dy = 0.0
            if p0[1] <= depth and p1[1] <= depth:
                # If both points are below the water level, then the
                # full length of this segment is added
                dx = p1[0] - p0[0]
                dy = p1[1] - p0[1]
            elif p0[1] <= depth:
                # If only the first point is below, use linear
                # interpolation to get the width below the waterline
                dy = depth - p0[1]
                ratio = dy / (p1[1] - p0[1])
                dx = ratio * (p1[0] - p0[0])
            elif p1[1] <= depth:
                # And similarly if only the second point is below
                dy = depth - p1[1]
                ratio = dy / (p0[1] - p1[1])
                dx = ratio * (p1[0] - p0[0])
            # If neither point was below we do nothing.
            wp += math.sqrt(dx*dx + dy*dy)
        return wp
            
    def wetted_area(self, depth):
        wa = 0.0
        for p0, p1 in self.xh_series.pairwise():
            # Loop over pairs of points in the cross-section
            if p0[1] <= depth and p1[1] <= depth:
                # If both points are below the water level, then the
                # full area of this segment is added
                dx = p1[0] - p0[0]
                dy = depth - 0.5 * (p1[1] + p0[1])
                wa += dx * dy
            elif p0[1] <= depth:
                # If only the first point is below, use linear
                # interpolation to get the width below the waterline
                dy = depth - p0[1]
                ratio = dy / (p1[1] - p0[1])
                dx = ratio * (p1[0] - p0[0])
                wa += 0.5 * dy * dx
            elif p1[1] <= depth:
                # And similarly if only the second point is below
                dy = depth - p1[1]
                ratio = dy / (p0[1] - p1[1])
                dx = ratio * (p1[0] - p0[0])
                wa += 0.5 * dy * dx
            # If neither point was below we do nothing.
        return wa
            
class HWCrossSection(CrossSection):
    """Class representing a cross-section as a head-width series.

    Attributes:
        hw_series: a utils.Series object containing the head and width data.
    """

    def __init__(self,
                 hw_series,
                 thalweg):
        """Constructor.

        Args:

            hw_series: a utils.Series object expected to contain at
                least 2 dimensions with dimension 0 being the water
                depth and dimension 1 being the top-width of the
                channel.
            thalweg: the bed level of the cross-section
        """
        assert(hw_series[0][0] == 0.0)
        super().__init__(thalweg)
        self.hw_series = deepcopy(hw_series)

    def top_width(self, depth):
        return self.hw_series.at(depth)[1]

    def wetted_perimeter(self, depth):
        wp = 0.0
        for p0, p1 in self.hw_series.pairwise():
            dx = 0.0
            dy = 0.0
            if p1[0] <= depth:
                dx = 0.5 * (p1[1] - p0[1])
                dy = p1[0] - p0[0]
            elif p0[0] <= depth:
                dy = depth - p0[0]
                ratio = dy / (p1[0] - p0[0])
                dx = 0.5 * ratio * (p1[1] - p0[1])
            else:
                break
            wp += 2.0 * math.sqrt(dx*dx + dy*dy)
        return wp

    def wetted_area(self, depth):
        wa = 0.0
        for p0, p1 in self.hw_series.pairwise():
            dx = 0.0
            dy = 0.0
            if p1[0] <= depth:
                dx = 0.5 * (p1[1] + p0[1])
                dy = p1[0] - p0[0]
            elif p0[0] <= depth:
                dy = depth - p0[0]
                ratio = dy / (p1[0] - p0[0])
                dx = 0.5 * (ratio * (p1[1] - p0[1]) + p0[1])
            else:
                break
            wa += dx * dy
        return wa

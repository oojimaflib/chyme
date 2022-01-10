"""
 Summary:

    Contains classes for representing a one-dimensional branched network.

 Author:

    Gerald Morgan

 Created:

    10 Jan 2022

"""

from .utils.series import Series

class CrossSection:
    """Generic class representing a cross-section through a watercourse.

    Attributes:
        xz_series: Series object representing the cross-section data in 
            (cross-chainage, elevation) format.
        hw_series: Series object representing the cross-section data in 
            (water-level, width) format.
        thalweg: bottom bed level of the cross-section.
    """
    def __init__(self,
                 *args,
                 xz_series = None,
                 hw_series = None,
                 thalweg = None):
        self.xz_series = xz_series
        self.hw_series = hw_series

        if self.xz_series is None and self.hw_series is None:
            raise RuntimeError("Must specify one of XZ or HW series.")

        data_thalweg = 0.0
        if self.xz_series is not None:
            data_thalweg = min([x[0] for x in self.xz_series])
        elif self.hw_series is not None:
            data_thalweg = self.hw_series[0][0]

        if thalweg is None:
            self.thalweg = data_thalweg
        else:
            self.thalweg = thalweg
            thalweg_dz = self.thalweg - data_thalweg
            if self.xz_series is not None:
                self.xz_series.datum[0] += thalweg_dz
            elif self.hw_series is not None:
                self.hw_series.datum[1] += thalweg_dz


        

    


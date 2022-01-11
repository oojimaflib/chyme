"""
 Summary:

    Contains classes for representing a data series.

 Author:

    Gerald Morgan

 Created:

    10 Jan 2022

"""

from collections.abc import MutableSequence

class SeriesError(LookupError):
    """Exception to be raised if data in a sequence is invalid.
    """
    def __init__(self, msg, pt0=None, pt1=None):
        self.msg = msg
        self.pt0 = pt0
        self.pt1 = pt1

class Series(MutableSequence):
    """Class representing a series of data.
    """
    def __init__(self,
                 points,
                 datum=None,
                 scale=None,
                 *args,
                 dimensions=None,
                 allow_reverse=None,
                 allow_repeats=None,
                 interpolate_method='linear'):
        """Constructor.

        Construct a series from a list of X-Y points.

        Args:
            points: a list of points. Each point, pt, in the list is 
                expected to return an X value from pt[0] and further values 
                from pt[X].
            datum: a list of offsets by which all the values should be 
                shifted.
            scale: a list of multiplication factors by which the data 
                should be scaled.
            dimensions: the number of dimensions (columns) in the series. 
                If omitted this is inferred from the first entry in the 
                points list.
            allow_reverse: list of booleans indicating whether values in 
                this dimension may reverse direction.
            allow_repeats: list of booleans indicating whether values in 
                this dimension may repeat.
            interpolate_method: approach that should be used for interpolating
                by the at() method. One of 'linear' (default), or 'stepwise'...

        """
        self.points = points
        self.datum = datum
        self.scale = scale

        self.dimensions = dimensions
        self.allow_reverse = allow_reverse
        self.allow_repeats = allow_repeats

        if interpolate_method == 'linear':
            self.at = self.linear_interpolate
        elif interpolate_method == 'stepwise':
            self.at = self.stepwise_interpolate
        else:
            raise SeriesError("Unknown interpolation method.")

        if len(self.points) > 0:
            if self.dimensions is None:
                self.dimensions = len(self.points[0])
            if self.dimensions != len(self.points[0]):
                raise SeriesError("User-specified dimensionality does not match the dimensionality of the data.")
        elif self.dimensions is None:
            raise SeriesError("No user-specified dimensionality and no initial data to infer this from.")

        if self.datum is None:
            self.datum = [0.0] * self.dimensions
        if self.scale is None:
            self.scale = [1.0] * self.dimensions
        
        if self.allow_reverse is None:
            self.allow_reverse = [False] + [True] * (self.dimensions - 1)
        if len(self.allow_reverse) != self.dimensions:
            raise SeriesError("Wrong length for allow_reverse argument.")
        if self.allow_repeats is None:
            self.allow_repeats = [True] * self.dimensions
        if len(self.allow_repeats) != self.dimensions:
            raise SeriesError("Wrong length for allow_repeats argument.")

        for index in range(1, len(self)):
            for dim in range(0, self.dimensions):
                if not self.allow_reverse[dim] and self[index][dim] < self[index-1][dim]:
                    raise SeriesError("Data in column {} must not reverse.".format(dim),
                                      self[index], self[index-1])
                elif not self.allow_repeats[dim] and self[index][dim] == self[index-1][dim]:
                    raise SeriesError("Data in column {} must not be duplicate.".format(dim),
                                      self[index], self[index-1])

    def __repr__(self):
        return 'Series([' + \
            ', '.join([str(x) for x in self.points]) + '], ' + \
            repr(self.datum) + ', ' + repr(self.scale) + \
            ', dimensions=' + repr(self.dimensions) + \
            ', allow_reverse=' + repr(self.allow_reverse) + \
            ', allow_repeats=' + repr(self.allow_repeats) + ')'

    def stepwise_interpolate(self, xval):
        """Get the value of the series at an arbitrary x coordinate with a
        stepwise interpolation.

        Requires that self.allow_reverse[0] is False. Values below the
        series range return self[0]. Values above the series range
        return self[-1].

        """
        if self.allow_reverse[0]:
            raise SeriesError("Can only do at() look-up when x-dimension is increasing.")
        old_value = None
        for i in range(0, len(self)):
            value = self[i]
            if value[0] == xval:
                return value
            elif value[0] > xval:
                if i > 0:
                    return [xval] + old_value[1:]
                else:
                    return value
            old_value = value
        return self[-1]
    
    def linear_interpolate(self, xval):
        """Get the value of the series at an arbitrary x coordinate with a
        linear interpolation.

        Requires that self.allow_reverse[0] is False. Values below the
        series range return self[0]. Values above the series range
        return self[-1].

        """
        if self.allow_reverse[0]:
            raise SeriesError("Can only do at() look-up when x-dimension is increasing.")
        old_value = None
        for i in range(0, len(self)):
            value = self[i]

            if value[0] == xval:
                return value
            elif value[0] > xval:
                if i > 0:
                    dx1 = value[0] - old_value[0]
                    dx0 = xval - old_value[0]
                    ratio = dx0 / dx1
                    return [ (value[i] - old_value[i]) * ratio + old_value[i]
                             for i in range(0, self.dimensions) ]
                else:
                    return value
            
            old_value = value

        return self[-1]
                
    def __len__(self):
        return len(self.points)

    def __getitem__(self, index):
        if isinstance(index, slice):
            result = []
            for pt in self.points[index]:
                result.append([ pt[i] * self.scale[i] + self.datum[i]
                               for i in range(0,self.dimensions) ])
            return result
        else:
            pt = self.points[index]
            return [ pt[i] * self.scale[i] + self.datum[i]
                     for i in range(0,self.dimensions) ]

    def __setitem__(self, index, pt):
        values = [ (pt[i] - self.datum[i]) / self.scale[i]
                   for i in range(0, self.dimensions) ]
        if index > 0:
            before = self.points[index-1]
            for i in range(0, self.dimensions):
                if not allow_reverse[i] and values[i] < before[i]:
                    raise SeriesError("Data in column {} must not reverse.".format(i),
                                      before, values)
                if not allow_repeats[i] and values[i] == before[i]:
                    raise SeriesError("Data in column {} must not repeat.".format(i),
                                      before, values)
        if index < len(self) - 1:
            after = self.points[index+1]
            for i in range(0, self.dimensions):
                if not allow_reverse[i] and after[i] < values[i]:
                    raise SeriesError("Data in column {} must not reverse.".format(i),
                                      values, after)
                if not allow_repeats[i] and after[i] == values[i]:
                    raise SeriesError("Data in column {} must not repeat.".format(i),
                                      values, after)
                
        for i in range(0, self.dimensions):
            self.points[index][i] = values[i]

    def __delitem__(self, index):
        del self.points[index]

    def __iter__(self):
        for i in range(0, len(self)):
            yield self[i]

    # TODO: we can implement __contains__ faster for objects that
    # prohibit reversing

    def append(self, pt):
        values = [ (pt[i] - self.datum[i]) / self.scale[i]
                   for i in range(0, self.dimensions) ]
        if len(self) > 0:
            for i in range(0, self.dimensions):
                if not allow_reverse[i] and values[i] < self.points[-1][i]:
                    raise SeriesError("Data in column {} must not reverse.".format(i), self[-1], values)
                if not allow_repeats[i] and values[i] == self.points[-1][i]:
                    raise SeriesError("Data in column {} must not repeat.".format(i), self[-1], values)
        self.points.append(values)

    def insert(self, index, pt):
        values = [ (pt[i] - self.datum[i]) / self.scale[i]
                   for i in range(0, self.dimensions) ]
        if index > 0:
            before = self.points[index-1]
            for i in range(0, self.dimensions):
                if not allow_reverse[i] and values[i] < before[i]:
                    raise SeriesError("Data in column {} must not reverse.".format(i),
                                      before, values)
                if not allow_repeats[i] and values[i] == before[i]:
                    raise SeriesError("Data in column {} must not repeat.".format(i),
                                      before, values)
        if index < len(self):
            after = self.points[index]
            for i in range(0, self.dimensions):
                if not allow_reverse[i] and after[i] < values[i]:
                    raise SeriesError("Data in column {} must not reverse.".format(i),
                                      values, after)
                if not allow_repeats[i] and after[i] == values[i]:
                    raise SeriesError("Data in column {} must not repeat.".format(i),
                                      values, after)
        self.points.insert(index, values)

    def pairwise(self):
        it = iter(self)
        a = next(it, None)
        for b in it:
            yield (a,b)
            a = b


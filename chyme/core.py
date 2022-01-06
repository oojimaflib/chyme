"""
 Summary:

    Contains the base API classes. Most of these exist primarily to be
    sub-classed by sub-modules to do useful things.

 Author:

    Gerald Morgan

 Created:

    10 Dec 2021

"""

class Model:
    """Class representing a hydraulic model.

    Each hydraulic model is composed of one or more Domains, each
    representing a model domain in 0, 1 or 2 dimensions. Domains are
    linked to each other, either dynamically or manually, with
    boundaries.
    """
    def __init__(self):
        self.domains = dict()

class Domain:
    """Base class representing a single hydraulic model domain.

    Each sub-model, e.g. ReFH, ESTRY, TUFLOW, Flood Modeller, that is
    used in the Model will contribute one or more domains.
    """
    def __init__(self):
        pass

    def dimensions(self):
        raise NotImplementedError()

class Field:
    """Base class representing spatially-distributed data in a domain.
    """
    def __init__(self):
        pass

class Feature:
    def __init__(self):
        pass

class Boundary:
    def __init__(self):
        pass

"""
 Summary:

    Contains classes for Flood Modeller (nee ISIS, nee
    Onda) units

 Author:

    Gerald Morgan

 Created:

    8 Jan 2022

"""

class FloodModellerUnit:
    def __init__(self, *args, io, auto_implement=False, **kwargs):
        self.line1_comment = io.line1_comment
        # self.line2_comment = io.line2_comment
        if auto_implement:
            for k, v in io.values.items():
                setattr(self, k, v)
        else:
            self.node_labels = io.values['node_labels']

    def __str__(self):
        return self.__repr__() + " " + str(self.node_labels)
            
    def name(self):
        return self.node_labels[0]

    def is_reach_component(self):
        return False

    def is_structure(self):
        return False

    def is_boundary(self):
        return False

    def is_junction(self):
        return False

    def connections(self):
        return list(filter(None, self.node_labels))

    def is_upstream_node_label(self, nl):
        return False

    def is_downstream_node_label(self, nl):
        return False

class GeneralUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        self.node_labels = []

class InitialConditions(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        self.node_labels = []

class GISInfo(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        self.node_labels = []


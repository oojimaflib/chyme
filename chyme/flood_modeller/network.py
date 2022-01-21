"""
 Summary:

    Contains overloads of the 1D network API classes relevant to Flood
    Modeller

 Author:

    Gerald Morgan

 Created:

    5 Jan 2022

"""

import logging
logger = logging.getLogger(__name__)

from . import files
from .. import network
from . import units
from chyme.utils.message import Message

from itertools import accumulate

class FloodModellerNode(network.Node):
    """1D node class representing a node in a Flood Modeller network.
    """
    def __init__(self, unit, *args, **kwargs):
        super().__init__(name=unit.name(), *args, **kwargs)
        self.unit = unit
    #     self.units = []
    #     self.append_unit(unit)

    # def append_unit(self, unit):
    #     self.units.append(unit)
    #     for node_label in unit.node_labels:
    #         if node_label is not None:
    #             self.add_alias(node_label)
        
    # def merge_with(self, other):
    #     super().merge_with(other)
    #     for unit in other.units:
    #         if unit not in self.units:
    #             self.units.append(unit)

class FloodModellerBoundaryNode(FloodModellerNode):
    """A location in a Flood Modeller network where an external boundary
    is applied.
    """
    def __init__(self, unit, *args, **kwargs):
        super().__init__(unit, *args, **kwargs)
        self.node_label = unit.node_labels[0]
    
class FloodModellerBranch(network.Branch):

    """1D reach class representing a branch in a Flood Modeller network.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class FloodModellerStructure(network.Structure):
    """1D reach class representing a structure in a Flood Modeller network.
    """
    def __init__(self, unit, *args, **kwargs):
        self.us_name = unit.us_node_label()
        self.ds_name = unit.ds_node_label()
        name = "{} → {}".format(self.us_name, self.ds_name)
        super().__init__(name, *args, **kwargs)

class FloodModellerReachSection(network.ReachSection):
    """1D reach section class in a Flood Modeller network.
    """
    def __init__(self, x, unit, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = x
        self.unit = unit

class FloodModellerReach(network.Reach):
    """1D reach class representing a reach in a Flood Modeller network.
    """
    def __init__(self,
                 reach_units,
                 *args,
                 partial = False,
                 **kwargs):
        self.reach_units = reach_units
        self.partial = partial
        unit_names = [x.name() for x in self.reach_units]
        self.us_name = unit_names[0]
        self.ds_name = unit_names[-1]
        reach_name = "{} → {}".format(self.us_name, self.ds_name)
        super().__init__(reach_name, *args,
                         aliases = unit_names, **kwargs)
        self.locations = list(accumulate(reach_units,
                                         lambda x, unit: x + unit.chainage,
                                         initial = 0.0))
        self.length = self.locations[-1]
        self.sections = [FloodModellerReachSection(x, unit)
                         for x,unit in zip(self.locations, self.reach_units)]

class FloodModellerNetwork(network.Network):
    """1D network class representing a Flood Modeller model.
    """
    def __init__(self,
                 dat_filename,
                 ied_filenames = []):
        """Constructor.
        """
        super().__init__()

        init_messages = []
        
        # Read and validate the data file
        dat_file_messages = []
        logger.info("Reading Flood Modeller network from %s", dat_filename)
        self.dat_file = files.DataFile(dat_filename)
        
        read_msg = self.dat_file.read()
        if read_msg is not None:
            init_messages.append(read_msg)
            
        validation_msg = self.dat_file.validate()
        if validation_msg is not None:
            init_messages.append(validation_msg)
            
        if len(init_messages) > 0:
            self.messages = [
                Message("Messages encountered while creating flood modeller network",
                        children = init_messages,
                        logger_name = __name__)
            ]
        else:
            self.messages = [
                Message("Flood modeller network created with no messages!",
                        Message.SUCCESS)
            ]

        if self.dat_file:
            self.units = self.dat_file.create_units()


        # Build the network
        reaches = list(self.reaches())
        structures = list(self.structures())
        boundaries = list(self.boundaries())

        branch_structures = []
        for bdy in boundaries:
            # Find a reach or structure downstream of this boundary
            for r in reaches:
                if bdy.name == r.us_name:
                    # We are connected to a reach
                    branch_structures = [r]
                    break
            if len(branch_structures) == 0:
                for s in structures:
                    if bdy.name == s.us_name:
                        branch_structures = [s]
                        break
            
            

    def reaches(self):
        reach_units = []
        for unit in self.units:
            if unit.is_reach_component():
                reach_units.append(unit)
                if unit.chainage == 0.0:
                    # This unit marks the end of a reach
                    yield FloodModellerReach(reach_units)
                    reach_units = []
            elif len(reach_units) > 0:
                # We have arrived at a non-reach unit with reach units
                # in hand
                msg = Message("Sequence of reach units does not end with zero chainage.", message.ERROR)
                self.messages.append(msg)
                yield FloodModellerReach(reach_units, partial = True)
                reach_units = []

    def structures(self):
        for unit in self.units:
            if unit.is_structure():
                yield FloodModellerStructure(unit)

    def boundaries(self):
        for unit in self.units:
            if unit.is_boundary():
                yield FloodModellerBoundaryNode(unit)
    
        # Loop through the units in the dat file to build the network
    #     history = []
    #     chainage = 0.0
    #     us_node = None
    #     ds_node = None
    #     for unit in self.units:
    #         if isinstance(unit, units.ReachFormingUnit):
    #             # This is a type of unit that can form part of a reach
    #             history.append(unit)
    #             chainage += unit.chainage
    #             if len(history) == 1:
    #                 # This is the first unit in the reach
    #                 us_node = self.get_matching_node(unit)
    #                 if us_node is None:
    #                     us_node = Node(unit)
    #                     self.nodes.append(us_node)
    #             else:
    #                 if unit.chainage == 0.0:
    #                     # This is the last unit in the reach
    #                     ds_node = self.get_matching_node(unit)
    #                     if ds_node is None:
    #                         ds_node = Node(unit)
    #                         self.nodes.append(ds_node)
    #                     reach = Reach(us=us_node, ds=ds_node, chainage=chainage)
    #                     local_chainage = 0.0
    #                     for cpu in history:
    #                         cp = CalcPoint(name=cpu.name(),
    #                                        reach=reach,
    #                                        chainage=local_chainage)
    #                         local_chainage += cpu.chainage
    #                         self.icps.append(cp)
                                                       
    #                     self.reaches.append(reach)

    #                     history = []
    #                     #us_node = ds_node
    #                     #ds_node = None
    #                 else:
    #                     # Intermediate unit in a reach
    #                     pass
    #         else:
    #             # Not a type of unit that can form part of a reach
                
    #             # Zero or more nodes might already exist that are
    #             # attached in some way to this unit. Get the list.
    #             associated_nodes = []
    #             for node_label in unit.node_labels:
    #                 match = self.get_matching_node(node_label)
    #                 if match is not None:
    #                     associated_nodes.append(match)

    #             print([n for n in unit.node_labels], '→', associated_nodes)
                        
    #             if len(associated_nodes) == 0:
    #                 self.nodes.append(Node(unit))
    #             elif len(associated_nodes) == 1:
    #                 associated_nodes[0].append_unit(unit)
    #             else:
    #                 associated_nodes[0].append_unit(unit)
    #                 self.merge_nodes(associated_nodes)

    # def get_matching_node(self, obj=None, *, match_name=True):
    #     name = None
    #     if isinstance(obj, units.FloodModellerUnit):
    #         for node in self.nodes:
    #             if hasattr(node, "unit") and node.unit == obj:
    #                 return node
    #         if match_name:
    #             name = obj.name()
    #     elif isinstance(obj, str):
    #         name = obj

    #     if name is not None:
    #         for node in self.nodes:
    #             if node.name == name:
    #                 return node
    #             for alias in node.aliases:
    #                 if alias == name:
    #                     return node
                    
    #     return None

    # def merge_nodes(self, node_list):
    #     for node in node_list[1:]:
    #         node_list[0].merge_with(node)
    #         self.nodes.remove(node)


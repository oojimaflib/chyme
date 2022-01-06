"""
 Summary:

    Contains overloads of the 1D network API classes relevant to Flood
    Modeller

 Author:

    Gerald Morgan

 Created:

    5 Jan 2022

"""

from . import io
from .. import network

class Node(network.Node):
    """1D node class representing a node in a Flood Modeller network.
    """
    def __init__(self, unit):
        super().__init__(name=unit.name())
        self.units = []
        self.append_unit(unit)

    def append_unit(self, unit):
        self.units.append(unit)
        for node_label in unit.node_labels():
            self.add_alias(node_label)
        
    def merge_with(self, other):
        super().merge_with(other)
        for unit in other.units:
            if unit not in self.units:
                self.units.append(unit)
        
class Reach(network.Reach):
    """1D reach class representing a reach in a Flood Modeller network.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CalcPoint(network.CalcPoint):
    """1D calculation point along a reach in a Flood Modeller network.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Network(network.Network):
    """1D network class representing a Flood Modeller model.
    """
    def __init__(self,
                 dat_filename,
                 ied_filenames = []):
        """Constructor.
        """
        super().__init__()
        
        # Read and validate the data file
        self.dat_file = io.DataFile(dat_filename)
        self.dat_file.read()
        self.dat_file.validate()
        if self.dat_file:
            self.dat_file.apply()

        # Loop through the units in the dat file to build the network
        history = []
        chainage = 0.0
        us_node = None
        ds_node = None
        for unit in self.dat_file.units:
            if unit.reach_unit:
                # This is a type of unit that can form part of a reach
                history.append(unit)
                chainage += unit.chainage
                if len(history) == 1:
                    # This is the first unit in the reach
                    us_node = self.get_matching_node(unit)
                    if us_node is None:
                        us_node = Node(unit)
                        self.nodes.append(us_node)
                else:
                    if unit.chainage == 0.0:
                        # This is the last unit in the reach
                        ds_node = self.get_matching_node(unit)
                        if ds_node is None:
                            ds_node = Node(unit)
                            self.nodes.append(ds_node)
                        reach = Reach(us=us_node, ds=ds_node, chainage=chainage)
                        local_chainage = 0.0
                        for cpu in history:
                            cp = CalcPoint(name=cpu.name(),
                                           reach=reach,
                                           chainage=local_chainage)
                            local_chainage += cpu.chainage
                            self.icps.append(cp)
                                                       
                        self.reaches.append(reach)

                        history = []
                        #us_node = ds_node
                        #ds_node = None
                    else:
                        # Intermediate unit in a reach
                        pass
            else:
                # Not a type of unit that can form part of a reach
                
                # Zero or more nodes might already exist that are
                # attached in some way to this unit. Get the list.
                associated_nodes = []
                for node_label in unit.node_labels():
                    match = self.get_matching_node(node_label)
                    if match is not None:
                        associated_nodes.append(match)

                print([n for n in unit.node_labels()], '→', associated_nodes)
                        
                if len(associated_nodes) == 0:
                    self.nodes.append(Node(unit))
                elif len(associated_nodes) == 1:
                    associated_nodes[0].append_unit(unit)
                else:
                    associated_nodes[0].append_unit(unit)
                    self.merge_nodes(associated_nodes)

    def get_matching_node(self, obj=None, *, match_name=True):
        name = None
        if isinstance(obj, io.DataFileUnit):
            for node in self.nodes:
                if hasattr(node, "unit") and node.unit == obj:
                    return node
            if match_name:
                name = obj.name()
        elif isinstance(obj, str):
            name = obj

        if name is not None:
            for node in self.nodes:
                if node.name == name:
                    return node
                for alias in node.aliases:
                    if alias == name:
                        return node
                    
        return None

    def merge_nodes(self, node_list):
        for node in node_list[1:]:
            node_list[0].merge_with(node)
            self.nodes.remove(node)


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

from itertools import accumulate, chain

class FloodModellerNode(network.Node):
    """1D node class representing a node in a Flood Modeller network.
    """
    def __init__(self, *args,
                 junction_unit = None,
                 node_label = None, **kwargs):
        if junction_unit:
            name = ' ↔ '.join(junction_unit.connections())
        elif node_label:
            name = node_label
        else:
            raise RuntimeError("Cannot construct flood modeller node without either junction unit or node label.")
        super().__init__(name=name, *args, **kwargs)
        self.unit = junction_unit

class FloodModellerBranch(network.Branch):
    """1D reach class representing a branch in a Flood Modeller network.
    """
    def __init__(self, branch_components,
                 us_node, ds_node, *args, **kwargs):
        name = "{} → {}".format(branch_components[0][0].us_name,
                                branch_components[-1][0].ds_name)
        super().__init__(name, us_node, ds_node, *args,
                         components=branch_components, **kwargs)

class FloodModellerStructure(network.Structure):
    """1D reach class representing a structure in a Flood Modeller network.
    """
    def __init__(self, unit, *args, **kwargs):
        self.us_name = unit.us_node_label()
        self.ds_name = unit.ds_node_label()
        name = "{} → {}".format(self.us_name, self.ds_name)
        super().__init__(name, *args, **kwargs)

    def __str__(self):
        return self.name
        
    def __repr__(self):
        return self.name
        
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

    def __str__(self):
        return self.name
        
    def __repr__(self):
        return self.name
        
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

        # Build an index of node labels to units:
        self.node_label_index = dict()
        for unit in self.units:
            for nl in unit.connections():
                if nl in self.node_label_index:
                    self.node_label_index[nl].append(unit)
                else:
                    self.node_label_index[nl] = [unit]

        # Build the network

        # 1. Build all of the reaches
        reaches = list(self.reaches())
        
        # 2. Combine reaches into simple branches
        branches = []
        for reach in reaches:
            # See if we link to any existing branch
            for b in branches:
                if reach.us_name == b[-1].ds_name:
                    b.append(reach)
                    break
                elif reach.ds_name == b[0].us_name:
                    b.insert(0, reach)
                    break
            else:
                # This reach does not connect to an existing branch
                branches.append([reach])
                
        # 3. We may be able to combine branches end-to-end, depending
        # on how daft the FMP DAT file ordering is.
        num_changes = 1
        while num_changes > 0:
            num_changes = 0
            for b1 in branches:
                for b2 in branches:
                    if b2 == b1:
                        break
                    if b1[-1].ds_name == b2[0].us_name:
                        b1 += b2
                        branches.remove(b2)
                        num_changes += 1
                        break
                    if b2[-1].ds_name == b1[0].us_name:
                        b2 += b1
                        branches.remove(b1)
                        num_changes += 1
                        break

        # 4. Join branches that are linked by junctions with 2 node-labels
        j_units = list(filter(lambda u: (u.is_junction() and
                                         len(u.connections()) == 2),
                              self.units))
        num_changes = 1
        while num_changes > 0:
            num_changes = 0
            for j_unit in j_units:
                connections = j_unit.connections()
                us_branch = None
                ds_branch = None
                for b in branches:
                    if b[-1].ds_name in connections:
                        us_branch = b
                        continue
                    if b[0].us_name in connections:
                        ds_branch = b
                        continue
                    if us_branch and ds_branch:
                        break

                if us_branch and ds_branch:
                    us_branch += ds_branch
                    branches.remove(ds_branch)
                    j_units.remove(j_unit)
                    num_changes += 1
            
        # 5. Upgrade our branches so that each branch component is now
        # a list of reaches:
        branches = [[[r] for r in b] for b in branches]

        # 6. Find junctions with more than two connections and add to
        # our list of junctions.
        j_units += list(filter(lambda u: (u.is_junction() and
                                          len(u.connections()) > 2), self.units))
        # 7. Find pairs of junctions that bracket an identical list of
        # single-reach branches. Merge these branches together and, if
        # the result is a two-noded junction on either end, merge
        # upstream and/or downstream
        num_changes = 1
        while num_changes > 0:
            num_changes = 0

            # Update each junction with lists of branches that are
            # either upstream, downstream or external to the model. We
            # need to re-do this each time we pass over the data as
            # branches can be updated and merged, rendering these
            # lists out-of-date
            for j1 in j_units:
                j1_cons = j1.connections()
                j1.us_cons = []
                j1.ds_cons = []
                j1.bdy_cons = []
                for nl in j1_cons:
                    for b in branches:
                        if nl in [r.ds_name for r in b[-1]]:
                            j1.us_cons.append(b)
                            continue
                        elif nl in [r.us_name for r in b[0]]:
                            j1.ds_cons.append(b)
                            continue
                        else:
                            j1.bdy_cons.append(nl)
                            continue
                        raise RuntimeError("What does this connect to? {} {}".format(j1, nl))
                j1.us_cons.sort(key = id)
                j1.ds_cons.sort(key = id)

            # Find parallel single-item branches that can be merged
            # together
            for j1 in j_units:
                if (len(j1.ds_cons) > 1 and
                    sum([len(r) for r in j1.ds_cons]) == len(j1.ds_cons)):
                    # This junction has multiple downstream branches, all
                    # of which are of length 1. Search for it's counterpart:
                    for j2 in j_units:
                        if j1.ds_cons == j2.us_cons:
                            # j1 and j2 bracket a set of parallel
                            # single-item branches that could be merged.
                            b1 = j1.ds_cons[0]
                            for b in j1.ds_cons[1:]:
                                b1[0] += b[0]
                                branches.remove(b)
                            j1.ds_cons = [b1]
                            j2.us_cons = [b1]

                            # Merge complete.
                            # If j1 has only one upstream connection we
                            # should be able to merge it to the end of
                            # another branch:
                            if len(j1.us_cons) == 1:
                                j1.us_cons[0] += b1
                                branches.remove(b1)
                                b1 = branches[branches.index(j1.us_cons[0])]
                                j_units.remove(j1)
                                num_changes += 1
                            
                            # And similarly if j2 has only one downstream
                            # connection:
                            if len(j2.ds_cons) == 1:
                                b1 += j2.ds_cons[0]
                                branches.remove(j2.ds_cons[0])
                                j_units.remove(j2)
                                num_changes += 1

                            break

        # 8. Create node objects
        self.nodes = [FloodModellerNode(junction_unit = j_unit)
                      for j_unit in j_units]

        # 9. Create branch objects and link with nodes
        self.branches = []
        for b in branches:
            # Find the upstream and downstream nodes for this branch
            us_node = None
            ds_node = None
            for node in self.nodes:
                if not node.unit:
                    continue
                if b in node.unit.ds_cons:
                    us_node = node
                    continue
                if b in node.unit.us_cons:
                    ds_node = node
                    continue
                if us_node and ds_node:
                    break

            if not us_node:
                # There is no existing (created from junction unit)
                # node at the end of this branch. Make one.
                us_node = FloodModellerNode(node_label = b[0][0].us_name)
                self.nodes.append(us_node)
                
            if not ds_node:
                ds_node = FloodModellerNode(node_label = b[-1][0].ds_name)
                self.nodes.append(ds_node)

            self.branches.append(FloodModellerBranch(b, us_node, ds_node))
            

    def get_other_unit(self, node_label, unit):
        for nl_unit in self.node_label_index[node_label]:
            if nl_unit != unit:
                return nl_unit
        return None

    def reaches(self):
        reach_units = []
        for unit in self.units:
            if unit.is_reach_component():
                reach_units.append(unit)
                if unit.chainage == 0.0:
                    # This unit marks the end of a reach
                    yield FloodModellerReach(reach_units)
                    reach_units = []
                continue
            elif len(reach_units) > 0:
                # We have arrived at a non-reach unit with reach units
                # in hand
                msg = Message("Sequence of reach units does not end with zero chainage.", message.ERROR)
                self.messages.append(msg)
                yield FloodModellerReach(reach_units, partial=True)
                reach_units = []
            if unit.is_structure():
                yield FloodModellerStructure(unit)
                continue


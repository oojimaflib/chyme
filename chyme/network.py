"""
 Summary:

    Contains classes for representing a one-dimensional branched network.

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

import uuid

class Node:
    """A 'point' between two reaches.

    This might be a junction between several branches or a hydraulic
    structure that separates two reaches.
    """
    def __init__(self, *, name=None, location=None, aliases=[]):
        self.name = name
        if self.name is None:
            self.name = str(uuid.uuid4())

        self.aliases = aliases
            
        self.location = location
        self.us_reaches = []
        self.ds_reaches = []

    def add_alias(self, alias):
        if alias not in self.aliases and alias != self.name:
            self.aliases.append(alias)        
        
    def add_us_reach(self, reach):
        if reach not in self.us_reaches:
            self.us_reaches.append(reach)

    def add_ds_reach(self, reach):
        if reach not in self.ds_reaches:
            self.ds_reaches.append(reach)

    def merge_with(self, other):
        for r in other.us_reaches:
            self.add_us_reach(r)
        for r in other.ds_reaches:
            self.add_ds_reach(r)

        self.add_alias(other.name)
        for alias in other.aliases:
            self.add_alias(alias)
        
class Reach:
    """A stretch of watercourse between two nodes with a known length

    This is any stretch of open channel or culverted watercourse with
    a non-zero computational length between two nodes.
    """
    def __init__(self, *, name=None, us, ds,
                 route=None, chainage=None):
        self.name = name
        if self.name is None:
            self.name = "{} → {}".format(us.name, ds.name)
            
        self.us_node = us
        self.us_node.add_ds_reach(self)
        self.ds_node = ds
        self.ds_node.add_us_reach(self)
            
        self.route = route
        self.chainage = chainage
        self.icps = []

    def add_icp(self, icp):
        self.icps.append(icp)
        # TODO: maybe keep ICPs sorted?

class CalcPoint:
    """A location along a reach where hydraulic calculations are performed
    or reported.
    """
    def __init__(self, *, name=None, reach, chainage):
        self.name = name
        if self.name is None:
            self.name = str(uuid.uuid4())
        
        self.reach = reach
        self.chainage = chainage
        reach.add_icp(self)
        
class Network:
    """A one-dimensional branched network
    """
    def __init__(self, nodes=None, reaches=None, icps=None):
        self.nodes = nodes
        if self.nodes is None:
            self.nodes = []
        self.reaches = reaches
        if self.reaches is None:
            self.reaches = []
        self.icps = icps
        if self.icps is None:
            self.icps = []

    def nodes(self):
        # TODO: actually test this and see if it works.
        us_nodes = list(filter(lambda x: len(x.us_reaches)==0, self.nodes))
        yielded = []
        for us_n in us_nodes:
            n = us_n
            while len(n.ds_reaches) > 0:
                if len(n.ds_reaches) == 1:
                    if n in yielded:
                        break
                    yielded.append(n)
                    yield n
                    n = n.ds_reaches[0]
                else:
                    us_nodes.insert(0, n)
                    break
            if n in yielded:
                continue
            yielded.append(n)
            yield n
            

    

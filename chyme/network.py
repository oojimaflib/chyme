"""
 Summary:

    Contains classes for representing a one-dimensional branched network.

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

import uuid

class NetworkObject:
    """An object that is part of a network.

    Attributes:
        name: the canonical name of the network object
        aliases: list of other names by which the object can be known
    """
    def __init__(self, name, *args, aliases=[], **kwargs):
        """Constructor.

        Args:
            name: the canonical name of the object
            aliases: a list of aliases byt which the object can be
                known. This does not need to include the canonical name.
        """
        self.name = name
        if self.name is None:
            self.name = str(uuid.uuid4())
        self.aliases = aliases

    def add_alias(self, alias):
        """Add an alias to the list of aliases.

        Checks to see if the supplied new alias is already in the list
        or is the name of the object, and if not, adds the alias to
        the list.
        """
        if alias not in self.aliases and alias != self.name:
            self.aliases.append(alias)        

    def merge_with(self, other):
        """Merge this object with another object.

        Adds the other object's name and aliases to this objects list
        of aliases (if they are not already present).

        """
        self.add_alias(other.name)
        for alias in other.aliases:
            self.add_alias(alias)

            
class Node(NetworkObject):
    """A 'point' between two branches.

    Attributes:
        location: an object defining the location of this node.
        us_branches: a list of branches that are upstream of this node
             (i.e. this node is at the downstream end of the branch)
        ds_branches: a list of branches that are downstream of this node
             (i.e. this node is at the upstream end of the branch)
    """
    def __init__(self, name=None,
                 *args,
                 aliases=[],
                 location=None,
                 us_branches=[],
                 ds_branches=[],
                 **kwargs):
        """Constructor.

        Args:
            name: the canonical name of this node
            aliases: a list of alternative names for this node
            location: an object defining the location of this node
            us_branches: a list of branches that end at this node
            ds_branches: a list of branches that start from this node
        """
        super().__init__(name, *args, aliases=aliases, **kwargs)

        self.location = location
        self.us_branches = us_branches
        self.ds_branches = ds_branches

    def add_us_branch(self, branch):
        """Connect a branch upstream of this node.
        """
        if branch not in self.us_branches:
            self.us_branches.append(branch)
        if branch.ds_node != self:
            if branch.ds_node is not None:
                # We should issue some sort of warning here
                branch.ds_node.remove_us_branch(branch)
            branch.ds_node = self

    def add_ds_branch(self, branch):
        """Connect a branch downstream of this node.
        """
        if branch not in self.ds_branches:
            self.ds_branches.append(branch)
        if branch.us_node != self:
            if branch.us_node is not None:
                # We should issue some sort of warning here
                branch.us_node.remove_ds_branch(branch)
            branch.us_node = self

    def remove_us_branch(self, branch):
        """Disconnect a branch upstream of this node.
        """
        if branch in self.us_branches:
            branch.ds_node = None
            self.us_branches.remove(branch)

    def remove_ds_branch(self, branch):
        """Disconnect a branch downstream of this node.
        """
        if branch in self.ds_branches:
            branch.us_node = None
            self.ds_branches.remove(branch)

    def merge_with(self, other):
        """Merge this node with another node.
        """
        super().merge_with(other)
        for b in other.us_branches:
            self.add_us_branches(b)
        for b in other.ds_branches:
            self.add_ds_branch(b)

class Branch(NetworkObject):
    """A stretch of watercourse between tributaries and confluences.

    Attributes:
        name: the canonical name of this branch of the watercourse.
        us_node: the node at the upstream end of this branch.
        ds_node: the node at the downstream end of this branch.
        aliases: a list of other names that can be used to refer to this branch.
        route: an object describing the route of this branch of the watercourse.
        components: a list of component (BranchObject) objects that form 
            this branch.
    """
    def __init__(self, name=None,
                 us_node=None,
                 ds_node=None,
                 *args,
                 aliases=[],
                 route=None,
                 components=[],
                 **kwargs):
        super().__init__(name, *args, aliases=aliases, **kwargs)
        
        self.us_node = us_node
        self.ds_node = ds_node
        self.route = route

        self.components = []

class BranchObject(NetworkObject):
    """A component of a branch.
    """
    def __init__(self, name=None,
                 *args,
                 aliases = [],
                 **kwargs):
        super().__init__(name, *args, aliases=aliases, **kwargs)
        
        
class Structure(BranchObject):
    """A hydraulic structure linking two reaches within a branch.
    """
    def __init__(self, name=None,
                 *args,
                 aliases = [],
                 location = None,
                 **kwargs):
        super().__init__(name, *args, aliases=aliases, **kwargs)

        self.location = location
        
class Reach(BranchObject):
    """A stretch of watercourse between two structures within a branch

    This is any stretch of open channel or culverted watercourse with
    a non-zero computational length between two nodes.
    """
    def __init__(self, name=None,
                 *args,
                 aliases=[],
                 **kwargs):
        super().__init__(name, *args, aliases=aliases, **kwargs)
        
class ReachSection(NetworkObject):
    """A location along a reach where data is defined
    """
    def __init__(self, name=None,
                 *args,
                 aliases = [],
                 location = None,
                 **kwargs):
        super().__init__(name, *args, aliases=aliases, **kwargs)

class Network:
    """A one-dimensional, branched network
    """
    def __init__(self):
        self.nodes = []
        self.branches = []
        

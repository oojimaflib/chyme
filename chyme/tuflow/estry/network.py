"""
 Summary:
    Subclasses the 1D Network API classes for ESTRY specific behaviour
    
 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""
import uuid

from .. import files
from chyme import network

from chyme.tuflow import GDAL_AVAILABLE, OGR_DRIVERS
from chyme.tuflow.estry import (
    NWK_ATTR_FIELDS, NWK_ATTR_TYPES, NWK_NODE_ATTR_FIELDS, NWK_NODE_ATTR_TYPES, 
    XS_ATTR_FIELDS, XS_ATTR_TYPES
)

if GDAL_AVAILABLE: # Setting import status is handled in tuflow.__init__
    from osgeo import gdal
    from osgeo import ogr
    from osgeo import osr
    from osgeo_utils import ogrmerge
    from osgeo_utils.samples import ogr_layer_algebra as lyralg

DEFAULT_SNAPPING_DIST = 0.01
SECTION_TYPES = ('s', 'c', 'r', 'i')

        
class Point():
    
    def __init__(self, x, y, z=None, snapping_dist=DEFAULT_SNAPPING_DIST):
        self.x = x
        self.y = y
        self.snapping_distance = snapping_dist
        self.bounds = {
            'x_upper': self.x + self.snapping_distance, 'x_lower': self.x - self.snapping_distance,
            'y_upper': self.y + self.snapping_distance, 'y_lower': self.y - self.snapping_distance,
        }
        
    # Consider using functools.isdispatch() for method overloading
    # https://docs.python.org/3/library/functools.html#functools.singledispatch
    def is_snapped_point(self, point):
        return self.is_snapped_xy(point.x, point.y)

    def is_snapped_xy(self, x, y):
        if x < self.bounds['x_upper'] and x > self.bounds['x_lower']:
            if y < self.bounds['y_upper'] and y > self.bounds['y_lower']:
                return True
        return False
    
    
class Line():
    
    def __init__(self, points, snapping_dist=DEFAULT_SNAPPING_DIST):
        self.points = points
        self.snapping_dist = snapping_dist
        self.is_reversed = False
        
    @property
    def vertex_count(self):
        return len(self.points)
    
    @property
    def us_vertex(self):
        return self.points[0]

    @property
    def ds_vertex(self):
        return self.points[-1]
    
    @property
    def middle_vertex(self):
        return self.points[self.middle_vertex_index]

    @property
    def middle_vertex_index(self):
        if self.vertex_count < 3:
            raise AttributeError('Cannot find middle vertex - len < 3')
        
        # If it's odd we can get the actual middle index
        if self.vertex_count % 2 != 0:
            mid = (self.vertex_count - 1) / 2
        # If not we find the one after the middle and take one away to get the 
        # 'first' of the two middle points. Arbitrary, but consistent
        else:
            mid = (self.vertex_count / 2) - 1
        return int(mid)
    
    def reverse_line(self):
        self.points.reverse()
        self.is_reversed = not(self.is_reversed)
    
    def is_snapped(self, point, ends_only=True):
        """Check if x and y are within snapping distance of vertices.
        """
        if ends_only:
            if self.check_snapped_us(point): return True
            if self.check_snapped_ds(point): return True
        else:
            for p in self.points:
                if p.is_snapped(point): return True
        return False
    
    def is_snapped_us(self, point):
        if isinstance(point, list):
            for p in point:
                if self.points[0].is_snapped_point(p):
                    return True
            return False
        else:
            return self.points[0].is_snapped_point(point)

    def is_snapped_ds(self, point):
        if isinstance(point, list):
            for p in point:
                if self.points[-1].is_snapped_point(p):
                    return True
            return False
        else:
            return self.points[-1].is_snapped_point(point)

    def is_snapped_middle(self, point):
        mid = self.middle_vertex_index
        if isinstance(point, list):
            for p in point:
                if self.points[mid].is_snapped_point(p):
                    return True
            return False
        else:
            return self.points[mid].is_snapped_point(point)
    
        
class EstryBranch():
    
    def __init__(self, reaches, is_reversed=True):
        self.reaches = reaches
        self._us_index = 0
        self._ds_index = -1
        if is_reversed:
            self._us_index = -1
            self._ds_index = 0
        self.us_node = reaches[self._us_index].node_us
        self.ds_node = reaches[self._ds_index].node_ds
        
    def __repr__(self):
        return self.name
        
    @property
    def name(self):
        return '{} - {}'.format(self.reaches[self._us_index].us_name, self.reaches[self._ds_index].ds_name)
    
    def merge_branches(self, branch, add_to_end=True):
        if add_to_end:
            self.reaches += branch.reaches
            self.us_node = self.reaches[self._us_index].node_us
        else:
            self.reaches = branch.reaches + self.reaches
            self.ds_node = self.reaches[self._ds_index].node_ds
        

class EstryReach():
    
    def __init__(self, sections, is_reversed=True):
        self.sections = sections
        self._us_index = 0
        self._ds_index = -1
        if is_reversed:
            self._us_index = -1
            self._ds_index = 0
        if self.sections:
            self.us_name = sections[self._us_index].id
            self.ds_name = sections[self._ds_index].id
            self.reach_name = "{} → {}".format(self.us_name, self.ds_name)
        self.nodes = []
        self.node_us = self.sections[self._us_index].node_us if self.sections else None
        self.node_ds = self.sections[self._ds_index].node_ds if self.sections else None
            
        self.branch_internal_us = None
        self.branch_internal_ds = None

    def __repr__(self):
        return self.reach_name
    

class EstryBranchObject():

    def __init__(self, attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs):
        EstryBranchObject.create_section(
            attributes, geometry, attr_lookup, snapping_dist=snapping_dist, **kwargs
        )
        
    @classmethod
    def create_section(
            cls, attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs
        ):
        if attributes[NWK_ATTR_FIELDS.index('type')].lower() in SECTION_TYPES:
            return EstryReachSection(
                attributes, geometry, attr_lookup, 
                snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs
            )
        else:
            return EstryStructure(
                attributes, geometry, attr_lookup, 
                snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs
            )
        

class EstryReachSection():
    
    def __init__(self, attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs):
        self.attributes = attributes
        self.attr_lookup = attr_lookup
        self.geometry = geometry
        self.snapping_dist = snapping_dist
        self.gis_type = kwargs.pop('gis_type', '')
        self.original_row = kwargs.pop('original_row', -1)
        self.nwk_line = None
        self.node_us = None
        self.node_ds = None
        self.section_us = None
        self.section_ds = None
        self.xs_us = []
        self.xs_ds = []
        self.xs_central = []
        self.is_reversed = False

        # Get WKT geometry previously loaded and create geom
        geom = ogr.CreateGeometryFromWkt(self.geometry)
        vertices = []
        for i in range(0, geom.GetPointCount()):
            x, y, z = geom.GetPoint(i)
            vertices.append(Point(x, y, z=z, snapping_dist=self.snapping_dist))
        self.nwk_line = Line(vertices, snapping_dist=self.snapping_dist)

        self._id = self._create_id()

    def __repr__(self):
        return self.id
        
    @property
    def id(self):
        return self._id

    @property
    def us_id(self):
        return '{}.{}'.format(self._id, 1)

    @property
    def ds_id(self):
        return '{}.{}'.format(self._id, 2)
        
    @property
    def section_type(self):
        return self.attributes[NWK_ATTR_FIELDS.index('type')].lower()
    
    def _create_id(self):
        id = self.attributes[NWK_ATTR_FIELDS.index('id')]
        if id is None:
            id = '{}_{}'.format(self.section_type, uuid.uuid4())
        return id
    
    def add_us_node(self, node):
        self.node_us = node

    def add_ds_node(self, node):
        self.node_ds = node
    
    def reverse_section(self):
        self.nwk_line.reverse_line()
        temp = self.node_us
        temp_aliases = self.node_us.aliases if self.node_us else []
        if self.node_us:
            self.node_us.aliases = self.node_ds_aliases if self.node_ds else []
        self.node_us = self.node_ds
        self.node_ds = temp
        if self.node_ds:
            self.node_ds.aliases = temp_aliases
        self.is_reversed = not(self.is_reversed)


class EstryStructure(EstryReachSection):
    x_count = 0
    
    def __init__(self, attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs):
        super().__init__(attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs)

    def _create_id(self):
        id = self.attributes[NWK_ATTR_FIELDS.index('id')]
        if id is None:
            id = '{}_{}'.format(self.section_type, EstryStructure.x_count)
            EstryStructure.x_count += 1
            self.attributes[NWK_ATTR_FIELDS.index('id')] = id
        return id
        

# class EstryNode(network.Node):
class EstryNode():
    """Top level network nodes for nodes at us/ds of branches.
    
    TODO: Can't inherit from networks.Node class at the moment because of the list
          assignment in the constructor messing with mutable memory allocations.
    """
    
    def __init__(self, esn, us_branches=None, ds_branches=None):
        self.name = esn.id
        self.location = esn.geometry
        self.aliases = esn.aliases
        self.us_branches = us_branches if us_branches is not None else []
        self.ds_branches = ds_branches if ds_branches is not None else []
        
    def __repr__(self):
        return self.name
        
                
class EstrySectionNode():

    def __init__(self, id, geometry, **kwargs):
        self.id = id
        self.geometry = geometry
        self.aliases = kwargs.get('aliases', [])
        
    def __repr__(self):
        return self.id
    
    def __eq__(self, estry_section_node):
        return self.aliases == estry_section_node.aliases
    
    def us_node_count(self):
        us = [a for a in self.aliases if a[-1] == '2']
        return len(us)

    def ds_node_count(self):
        ds = [a for a in self.aliases if a[-1] == '1']
        return len(ds)


class ConnectionNode():
    """Node connection loader.
    
    Only used when building the network to store connection information for identifying
    the links between 1d_nwk lines and 1d_nd nodes.
    """
    
    def __init__(self, id, geometry):
        self.id = id
        self.geometry = geometry
        self.aliases = []
        self.sections_us = []
        self.sections_ds = []
        self.connection_ids = []
        geom = ogr.CreateGeometryFromWkt(self.geometry)
        self.point = Point(geom.GetX(), geom.GetY())
        geom = None
        self.estry_section_node = None

    def __repr__(self):
        return '{} - {}'.format(
            '|'.join([s.id for s in self.sections_us]), 
            '|'.join([s.id for s in self.sections_ds]), 
        )
        
    @property
    def name(self):
        return '-'.join(self.aliases)
    
    def add_connection(self, section):
        success = False
        if section.nwk_line.is_snapped_us(self.point):
            self.sections_ds.append(section)
            self.connection_ids.append(section.id)
            self.aliases.append(section.us_id)
            success = True
        elif section.nwk_line.is_snapped_ds(self.point):
            self.sections_us.append(section)
            self.connection_ids.append(section.id)
            self.aliases.append(section.ds_id)
            success = True
        return success
            
    def remove_connection(self, section_id):
        ds = [i for i, n in enumerate(self.sections_ds) if n.id == section_id]
        us = [i for i, n in enumerate(self.sections_us) if n.id == section_id]
        
        success = False
        if len(us) == 1:
            del self.sections_us[us[0]]
            del self.connection_ids[self.connection_ids.index(section_id)]
            for i, a in enumerate(self.aliases):
                if a.startswith(section_id):
                    del self.aliases[i]
                    break
            success = True
        elif len(ds) == 1:
            del self.sections_ds[ds[0]]
            del self.connection_ids[self.connection_ids.index(section_id)]
            for i, a in enumerate(self.aliases):
                if a.startswith(section_id):
                    del self.aliases[i]
                    break
            success = True
        return success
        
        
class EstryNetwork():
    
    def __init__(self):
        self.raw_nwks = []
        self.raw_sections = []
        self.snapping_dist = DEFAULT_SNAPPING_DIST
        
    def setup(self, nwks, sections, snapping_dist=DEFAULT_SNAPPING_DIST):
        if not GDAL_AVAILABLE:
            raise ImportError('Unable to use GDAL to load data. Is it installed?')
        self.raw_nwks = nwks
        self.raw_sections = sections
        self.snapping_dist = snapping_dist
        
        self.build_network()
        i=0
        # Load the nwk data
        # self._build_channels()
        
    def build_network(self):
        """Pull all of the river network components together.
        
        Builds and associates all of the branches, nodes, reaches and sections.
        
        Structure::
            EstryNetwork ->
                EstryBranch ->
                    reaches ->
                        EstryReach ->
                            sections ->
                                EstryReachSection ->
                                    - Contains all of the section data
                                EstryReachSection...
                            nodes ->
                                EstryNode
                                    - Contains all of the geometry and section associations
                                EstryNode...
                        EstryReach...
                            
                EstryBranch...
        """
        # Merge the nwk files, create nodes, and run an intersection on the layers
        reaches, reach_lookup, nwk_merge_fname, node_fname = self.snap_nwk_nodes()

        # Merge xs files, intersect with nwks, and update nwks with cross section data
        reaches = self._find_xs(reaches, reach_lookup, nwk_merge_fname)
        
        # Build the network associations and find the connections between nodes and sections
        # node_lookup, point_lookup = self.build_connections(reaches, reach_lookup, node_fname)
        nodes, node_lookup = self.build_connections(reaches, reach_lookup, node_fname)

        # Get the upstream and downstream nodes (those with only one-way connections
        us_nodes = []
        ds_nodes = []
        for n in nodes:
            if not len(n.sections_ds):
                ds_nodes.append(n.id)
            elif not len(n.sections_us):
                us_nodes.append(n.id)

        # Create the branches, starting from each ds node
        processed_nwks = []
        branches = []
        self.nodes = []
        self.node_lookup = {}
        for dsn in ds_nodes:
            bs, processed_nwks = self.build_branches(
                dsn, nodes, node_lookup, processed_nwks
            )
            branches += bs

        # Final merge of the branches
        branches = self.merge_branches(branches)
        branch_nodes = {}
        # node_ids = {}
        for b in branches:
            if b.us_node.id in branch_nodes:
                branch_nodes[b.us_node.id].ds_branches.append(b)
            else:
                branch_nodes[b.us_node.id] = EstryNode(b.us_node)
                branch_nodes[b.us_node.id].ds_branches.append(b)
                
            if b.ds_node.id in branch_nodes:
                branch_nodes[b.ds_node.id].us_branches.append(b)
            else:
                branch_nodes[b.ds_node.id] = EstryNode(b.ds_node)
                branch_nodes[b.ds_node.id].us_branches.append(b)
        self.nodes = [*branch_nodes.values()]
        self.branches = branches

    def build_reaches(self, ds_node, sect, processed_nwks, nodes, node_lookup):
        """Create all of the reaches associated with a single branch.

        Create one or more EstryReach objects. There may be multiple reaches if
        there is a single structure (weir, bridge, etc... not culvert). These will
        all be part of the same branch, but require a new reach.
        
        Will return when it find more than one connection at the node, i.e. a
        junction, which indicates the end of the branch.
        """
        reaches = []
        sections = [sect]
        processed_nwks.append(sect.id)
        prev_type = sect.section_type
        
        while True:
            us_node = nodes[node_lookup[sect.us_id]]
            ds_node = nodes[node_lookup[sect.ds_id]]
            if us_node.estry_section_node:
                sect.node_us = us_node.estry_section_node
            else:
                us_snode = EstrySectionNode(us_node.id, us_node.geometry, aliases=us_node.aliases)
                us_node.estry_section_node = us_snode
                sect.node_us = us_node.estry_section_node

            if ds_node.estry_section_node:
                sect.node_ds = ds_node.estry_section_node
            else:
                ds_snode = EstrySectionNode(ds_node.id, ds_node.geometry, aliases=ds_node.aliases)
                ds_node.estry_section_node = ds_snode
                sect.node_ds = ds_node.estry_section_node

            us_sections = us_node.sections_us
        
            # Junction
            if len(us_node.connection_ids) > 2:
                break
        
            # I think this will only happen if one of nwk lines has been
            # digitized the wrong way around.
            # Reverse the line and swap the node references. The EstryReachSection
            # will have the reversed flag set to True
            # TODO: If it's an 'x' connector it's probably correct, if it's
            #       anything else it probably isn't and we should raise a warning.
            # if sect.id in 
            if len(us_sections) == 0 and len(us_node.connection_ids) > 1 and len(us_node.sections_ds) == 2:
                
                    # Find the downstream section and node
                    fake_ds = [i for i, n in enumerate(us_node.sections_ds) if n.id != sect.id][0]
                    new_sect = us_node.sections_ds[fake_ds]
                    temp_dsnode = nodes[node_lookup[new_sect.ds_id]]
                    
                    # Remove the existing node connections
                    us_node.remove_connection(new_sect.id)
                    temp_dsnode.remove_connection(new_sect.id)
                    
                    # Reverse the section and setup the new connections
                    new_sect.reverse_section()
                    us_node.add_connection(new_sect)
                    temp_dsnode.add_connection(new_sect)
                    
                    # Update the lookup tables to reference the correct nodes
                    us_sections = us_node.sections_us
                    temp = node_lookup[new_sect.us_id]
                    node_lookup[new_sect.us_id] = node_lookup[new_sect.ds_id]
                    node_lookup[new_sect.ds_id] = temp

            # The upstream node of the river network has been found
            if len(us_sections) == 0:
                break
        
            # Otherwise, there's a single upstream section connected and the branch
            # can continue
            else:
                sect = us_sections[0]
                
                # If it's a different type of 1d_nwk the reach is finished and a
                # new one started
                if (sect.section_type != 'x' and prev_type != 'x') and sect.section_type != prev_type:
                    reaches.append(EstryReach(sections))
                    sections = [sect]
        
                else:
                    sections.append(sect)
                processed_nwks.append(sect.id)
                prev_type = sect.section_type

        # Loop finished - finalise reach data
        node = nodes[node_lookup[sect.us_id]]
        reaches.append(EstryReach(sections))
        
        return reaches, node, processed_nwks
    
        
    def build_branches(self, ds_node, nodes, node_lookup, processed_nwks=[]):
        """Create EstryBranch objects from this node upstream.
        
        Creates branches leading up from this downstream node by lookup upstream
        for all connecting EstryReachSection objects and following them up the
        network until a junction is found (3 connecting sections). 
        Once a junction is found it creates an EstryBranch from connected reaches, 
        adds all of the upstream sections to a stack, pops another node/section
        item off the stack and continues the process.
        
        Keeps track of the EstryReachSection ids that have been process to avoid
        inadvertently building the same reach/branch twice (there are a lot of edge
        cases that can cause this, so it's easier to just validate it).
        
        Once the stack is exhausted, there are not more EstryReachSections connected
        in anyway to this downstream node. The branches and the ids of the processed
        sections are returned.                
        """
        section_stack = []
        branches = []
        
        # Add the first node, and associated sections, to the stack
        node = nodes[node_lookup[ds_node]]
        us_sections = node.sections_us
        for u in us_sections:
            section_stack.append([node, u])
        
        # Loop the section_stack until we run out of [node,section] to process
        branch_nodes = {}
        while len(section_stack) > 0:
            stack_item = section_stack.pop()
            if stack_item[1] in processed_nwks: continue

            # Create a branch by building reaches up to the next node containing
            # multiple connections (a junction)
            reaches, us_node, processed_nwks = self.build_reaches(
                stack_item[0], stack_item[1], processed_nwks, nodes, node_lookup,
            )
            branch = EstryBranch(reaches)
            ds_node = us_node
            
            # Check whether we have parallel branches/channels
            # If we do they should be treated as a single branch, so merge them
            branch_check = '{}{}'.format(branch.us_node, branch.ds_node)
            if branch_check in branch_nodes:
                branches[branch_nodes[branch_check]].merge_branches(branch)
            else:
                branch_nodes[branch_check] = len(branches)
                branches.append(branch)

            # If there are more sections upstream to process, add the node
            # and upstream section to the stack
            if us_node.sections_us:
                for u in us_node.sections_us:
                    if not u.id in processed_nwks:
                        section_stack.append([ds_node, u])
        
        return branches, processed_nwks
            
    def merge_branches(self, branches):
            
        # Merge branches together if they share a node connected to a single upstream
        # or downstream network
        i = 0
        while i < len(branches):
            found = [None, None]
            # If there's only 1 upstream nwk and 1 downstream nwk
            if branches[i].us_node.us_node_count() == 1 and branches[i].ds_node.ds_node_count() == 1:
                for j, branch in enumerate(branches):
                    if branches[i].us_node == branch.ds_node:
                        found[0] = j
                    elif branches[i].ds_node == branch.us_node:
                        found[1] = j
                    if found[0] is not None and found[1] is not None:
                        break
                
                if found[0] is not None and found[1] is not None:
                    branches[i].merge_branches(branches[found[0]])
                    del branches[found[0]]
                    branches[i].merge_branches(branches[found[1]], add_to_end=False)
                    del_index = found[1]
                    if found[0] < found[1]:
                        del_index = found[1] - 1
                    del branches[del_index]
                    i = -1
            i += 1

        return branches
            
    def build_connections(self, reaches, reach_lookup, node_fname):
        """Associate the nodes with the nwk lines.
        
        The intersection has created a layer containing a node id referencing a nwk line id
        There can (in most cases will be) mutiple matching node ids referencing different
        nwk lines (not a problem). But, there will be multiple nodes created in exactly the
        same location, because one node was created for each u/s and d/s nwk line vertex.
        Use the xy_lookup to store the xy coordinate string (same for snapped nodes) and 
        ensure that the connections from the different snapped nodes get saved into a 
        single node.
        
        xy_lookup stores the xy str (key) and a reference to the node id
        node_lookup stores the node_id (key) and the index of the EstryNode object in the nodes list
        nodes stores the EstryNodes
        
        Process:
        1) Check if the xy str exists in xy_lookup:
           a) If not:
               i)   Create EstryNode
               ii)  Set xy_lookup key as node id
               iii) Add id to the node lookup and reference the index of the EstryNode in nodes
           b) If yes:
               i)   If the nwk line id is not in the EstryNode connections, add it
               ii)  Add id to the node lookup and reference the index of the EstryNode in nodes
        
        Output:
           A list of nodes containing all of the EstryNodes (containing connections and
           aliases, etc)
           A dictionary of node ids referencing the index of the associated node in the
           nodes list
        """

        def process_geometry(geom):
            """Get the different geometry components required.
            
            This doesn't really need to be a separate function, but it doesn't make any
            difference, and having it in the loop was crashing the debugger - which is
            a pain!
            """
            x = geom.GetX()
            y = geom.GetY()
            combo = '{}{}'.format(x, y)
            wkt = geom.ExportToWkt()
            return x, y, combo, wkt
        
        node_lookup = {}
        xy_lookup = {}
        nodes = []
        section_lookup = {}
        data = ogr.Open(node_fname)

        if data is not None:
            lyr = data.GetLayer()
            node_id = lyr.schema[0].name
            nwk_id = lyr.schema[1].name
            for feat in lyr:
                
                node_attr = feat.GetField(node_id)
                nwk_attr = feat.GetField(nwk_id)

                # Very 'round-about' way to set the geometry, but loading the geometry
                # ref in the loop was crashing the debugger. 
                # TODO: Perhaps set up an is_debug flag to handle this differently?
                __, __, xy_str, geom_wkt = process_geometry(feat.GetGeometryRef())
                
                # if not xy_str in xy_lookup:
                #     en = EstrySectionNode(node_attr, geom_wkt)
                #     node_lookup[xy_str] = en
                
                if not xy_str in xy_lookup:
                    en = ConnectionNode(node_attr, geom_wkt)
                    en.add_connection(reaches[reach_lookup[nwk_attr]])
                    nodes.append(en)
                    xy_lookup[xy_str] = node_attr
                    node_lookup[node_attr] = len(nodes) - 1
                else:
                    if not nwk_attr in nodes[node_lookup[xy_lookup[xy_str]]].connection_ids:
                        nodes[node_lookup[xy_lookup[xy_str]]].add_connection(reaches[reach_lookup[nwk_attr]])
                    node_lookup[node_attr] = node_lookup[xy_lookup[xy_str]]
        data = None
        
        return nodes, node_lookup
        
    def snap_nwk_nodes(self):
        """Create a node at the upstream and downstream vertex of each nwk line.
        
        Merges all of the 1d_nwk files into a single file, then creates a point node
        for the upstream and downstream vertices of the line.
        
        Uses the gdal vsimem memory file store to process files in memory, rather than
        having to write out to temporary files. My understanding is that the data will
        remain in memory until the calling process ends:
        https://gdal.org/user/virtual_file_systems.html#vsimem-in-memory-files
        
        unlink:
        https://lists.osgeo.org/pipermail/gdal-dev/2011-November/030916.html
        
        Snapping is done with the gdal ogr_layer_algebra.py script:
        GDAL -> osgeo_utils -> samples -> ogr_layer_algebra.py
        Possibly a better idea to keep it in a "scripts" folder in the codebase instead?
        It's in "samples", so may move or be updated in later versions?
        
        Return:
            tuple( reaches(list), reach_lookup(dict), nwk_merge_fname(str) node_fname(str) )
        """
    
        def create_nd_point(fdata, vertex, feat_def, sublabel):
            """Create upstream and downstream point nodes for nwk line
            
            An additional field (id_copy) is required, replicating the 'id' field due to a
            weird bug in the intersect tool that will write 'Null' attributes to the 'id'
            field for the intersected layer. Duplicating the field with a different name
            gets around this issue.
            """
            us_point = ogr.Geometry(ogr.wkbPoint)
            us_point.AddPoint(vertex.x, vertex.y)
            node_feat = ogr.Feature(feat_def)
            node_feat.SetGeometry(us_point)
            node_feat.SetField('id', '{}.{}'.format(
                fdata['fields'][NWK_ATTR_FIELDS.index('id')], sublabel
            ))
            node_feat.SetField('id_copy', '{}.{}'.format(
                fdata['fields'][NWK_ATTR_FIELDS.index('id')], sublabel
            ))
            return node_feat
    
        # Create a memory layer to store the output in 
        drv = ogr.GetDriverByName('ESRI Shapefile')
        # nwk_nodes = "C:/Users/ermev/Desktop/TEMP/Chyme/output_files/1d_nwk_nodes.shp"
        nwk_merge_fname = "/vsimem/1d_nwk_merge.shp"
        nwk_nodes = "/vsimem/1d_nwk_nodes.shp"
        ds = drv.CreateDataSource(nwk_merge_fname)
        ds_nodes = drv.CreateDataSource(nwk_nodes)
        
        # Set spatial reference system
        # Not a great approach. Need to setup reading the projection from the tgc file
        # and expect everything to have that projection (could also add a check
        # or warning to validate on file load?).
        wkt_crs = self.raw_nwks[0].files.files[0].data.crs
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt_crs)
        
        nwk_layer = ds.CreateLayer("nwk_merge_fname", srs, ogr.wkbLineString)
        node_layer = ds_nodes.CreateLayer("nwk_nodes", srs, ogr.wkbPoint)
        
        # Add fields to nwk and nodes layers
        for i, f in enumerate(NWK_ATTR_FIELDS):
            new_field = ogr.FieldDefn(f, NWK_ATTR_TYPES[i])
            nwk_layer.CreateField(new_field)
        for i, f in enumerate(NWK_NODE_ATTR_FIELDS):
            new_field = ogr.FieldDefn(f, NWK_NODE_ATTR_TYPES[i])
            node_layer.CreateField(new_field)
        
        # Add the 
        new_field = ogr.FieldDefn('id_copy', NWK_NODE_ATTR_TYPES[i])
        node_layer.CreateField(new_field)
        
        feat_def = nwk_layer.GetLayerDefn()
        node_feat_def = node_layer.GetLayerDefn()
        nwk_attr_len = len(NWK_ATTR_FIELDS)

        
        reaches = []
        reach_lookup = {}
        count = 0
        for nwk in self.raw_nwks:
            nwk_file = nwk.files.files[0]
            
            for i, fdata in enumerate(nwk_file.data.field_data):

                # Create the reach sections
                reach_section = EstryBranchObject.create_section(
                    fdata['fields'], fdata['geometry'], attr_lookup=nwk_file.data.attribute_lookup, 
                    snapping_dist=self.snapping_dist, gis_type=nwk.files.file_type, original_row=i
                )
                us_vertex = reach_section.nwk_line.us_vertex
                ds_vertex = reach_section.nwk_line.ds_vertex
                reach_lookup[reach_section.id] = count
                reaches.append(reach_section)
                count += 1
                
                # Create the 1d_nd features
                # Nwk us point
                node_feat = create_nd_point(fdata, us_vertex, node_feat_def, 1)
                node_layer.CreateFeature(node_feat)
                node_feat = None

                # Nwk ds point
                node_feat = create_nd_point(fdata, ds_vertex, node_feat_def, 2)
                node_layer.CreateFeature(node_feat)
                node_feat = None
            
                # Create the 1d_nwk line feature
                geom = ogr.CreateGeometryFromWkt(fdata['geometry'])
                new_feat = ogr.Feature(feat_def)
                new_feat.SetGeometry(geom)
                for j, f in enumerate(fdata['fields']):
                    if j < nwk_attr_len:
                        new_feat.SetField(NWK_ATTR_FIELDS[j], f)
                nwk_layer.CreateFeature(new_feat)
                new_feat = None
        
        nwk_layer.ResetReading()
        node_layer.ResetReading()
        ds = None
        ds_nodes = None
        
        # # Create a memory layer to store the output in 
        # node_output = "C:/Users/ermev/Desktop/TEMP/Chyme/output_files/1d_nd_intersect_nwk.shp"
        node_fname = "/vsimem/1d_nd_intersect_nwk.shp"
        ds = drv.CreateDataSource(node_fname)

        # Run the intersect tool to find nodes snapped to nwk lines
        # The nwk is snapped to the nodes so that we can use the node as a lookup to find
        # the nwk line ids. Only id (method_fields) and id_copy (input_fields) are kept,
        # as none of the other attributes are needed here
        lyralg.main([
            '','Intersection', '-q', '-method_fields', 'id', '-input_fields', 'id_copy', '-input_ds', 
            nwk_nodes, '-method_ds', nwk_merge_fname, '-output_ds', node_fname
        ])
        ds = None
        
        return reaches, reach_lookup, nwk_merge_fname, node_fname
        
    def _find_xs(self, networks, network_lookup, nwk_lyr=None):
        """Load the cross section data and associate it with the EstrySection objects.
        
        Snapping is done with the gdal ogr_layer_algebra.py script:
        GDAL -> osgeo_utils -> samples -> ogr_layer_algebra.py
        Possibly a better idea to keep it in a "scripts" folder in the codebase instead?
        It's in "samples", so may move or be updated in later versions?
        """
        
        class CrossSection():
            """Store the data loaded from 1d_xs layers."""
            
            def __init__(self, attributes, geometry, attr_lookup, snapping_dist=DEFAULT_SNAPPING_DIST, **kwargs):
                self.attributes = attributes
                self.attr_lookup = attr_lookup
                self.geometry = geometry
                self.snapping_dist = snapping_dist
                self.gis_type = kwargs.pop('gis_type', '')
                self.original_row = kwargs.pop('original_row', -1)
                self.xs_line = None
                self._id = self.attributes[XS_ATTR_FIELDS.index('source')]
                self.section_data = kwargs.pop('section_data', None)

                # Get WKT geometry previously loaded and create geom
                geom = ogr.CreateGeometryFromWkt(self.geometry)
                vertices = []
                for i in range(0, geom.GetPointCount()):
                    x, y, z = geom.GetPoint(i)
                    vertices.append(Point(x, y, z=z, snapping_dist=self.snapping_dist))
                self.xs_line = Line(vertices, snapping_dist=self.snapping_dist)
                
            def __repr__(self):
                return self.id
            
            @property
            def id(self):
                return self._id


        # Merge the cross section files
        # Create a memory layer to store the output in 
        drv = ogr.GetDriverByName('ESRI Shapefile')
        # nwk_nodes = "C:/Users/ermev/Desktop/TEMP/Chyme/output_files/1d_nwk_nodes.shp"
        xs_merge = "/vsimem/1d_xs_merge.shp"
        ds = drv.CreateDataSource(xs_merge)
        
        # Set spatial reference system
        # Not a great approach. Need to setup reading the projection from the tgc file
        # and expect everything to have that projection (could also add a check
        # or warning to validate on file load?).
        wkt_crs = self.raw_sections[0].files.files[0].data.crs
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt_crs)
        
        # create one layer 
        xs_layer = ds.CreateLayer("xs_merge", srs, ogr.wkbLineString)
        
        # Add fields to nwk layer
        for i, f in enumerate(XS_ATTR_FIELDS):
            new_field = ogr.FieldDefn(f, XS_ATTR_TYPES[i])
            xs_layer.CreateField(new_field)

        feat_def = xs_layer.GetLayerDefn()
        xs_attr_len = len(NWK_ATTR_FIELDS)

            
        # Load the CrossSection data
        sections = []       # The CrossSection objects
        xs_lookup = {}      # A quick lookup to find cross section by "source" id
        count = 0
        for i, sect in enumerate(self.raw_sections):
            xs_file = sect.files.files[0] # only ever a single line file for cross sections
            for j, fdata in enumerate(xs_file.data.field_data):
                
                # Build the cross section objects
                section_data = xs_file.data.associated_data['source'][j]
                cross_section = CrossSection(
                    fdata['fields'], fdata['geometry'], attr_lookup=xs_file.data.attribute_lookup, 
                    snapping_dist=self.snapping_dist, gis_type=sect.files.file_type, original_row=j,
                    section_data=section_data
                )
                xs_lookup[cross_section.id] = count
                sections.append(cross_section)
                count += 1
                
                # Create the 1d_xs line feature
                geom = ogr.CreateGeometryFromWkt(fdata['geometry'])
                new_feat = ogr.Feature(feat_def)
                new_feat.SetGeometry(geom)
                for j, f in enumerate(fdata['fields']):
                    if j < xs_attr_len:
                        new_feat.SetField(XS_ATTR_FIELDS[j], f)
                xs_layer.CreateFeature(new_feat)
                new_feat = None

        xs_layer.ResetReading()
        ds = None
        
        #
        # Intersect nwk lines and cross section lines
        #
        # Get the paths for the 1d_nwk and 1d_xs layers
        # TODO: join all layers together into single file
        if nwk_lyr is None:
            nwk_lyr = self.raw_nwks[1].files.files[0].file.absolute_path
        
        # Create a memory layer to store the output in 
        drv = ogr.GetDriverByName('ESRI Shapefile')
        output = "/vsimem/nwk_xs_intersect_v1.shp"
        drv.CreateDataSource(output)
        
        # Intersect the nodes and the nwks
        lyralg.main([
            '','Intersection', '-q', '-input_ds', nwk_lyr, '-method_ds', xs_merge, 
            '-input_fields', 'id', '-method_fields', 'source', '-output_ds', output
        ])
        
        # Get the connecting cross section data
        # (associate the nwk ids with the xs source ids)
        intersects = {}
        data = ogr.Open(output)
        if data is not None:
            lyr = data.GetLayer()
            attrs = {field.name.lower(): [i, field.name] for i, field in enumerate(lyr.schema)}
            id_field = attrs['id'][1]
            source_field = attrs['source'][1]
            for feat in lyr:
                id_attr = feat.GetField(id_field)
                source_attr = feat.GetField(source_field)
                if not id_attr in intersects:
                    intersects[id_attr] = [source_attr]
                else:
                    intersects[id_attr].append(source_attr)
                    
        # Finally, find out how the 1d_nwk and 1d_xs features are intersected.
        # They will either be snapped to the upstream, downstream or middle of the 1d_nwk line
        for nwk, vals in intersects.items():
            # X connectors don't need an ID
            if nwk is None: continue
            
            nwk_obj = networks[network_lookup[nwk]]
            for xs in vals:
                xs_obj = sections[xs_lookup[xs]]
                if nwk_obj.nwk_line.is_snapped_us(xs_obj.xs_line.points):
                    networks[network_lookup[nwk]].xs_us.append(xs_obj)
                elif nwk_obj.nwk_line.is_snapped_ds(xs_obj.xs_line.points):
                    networks[network_lookup[nwk]].xs_ds.append(xs_obj)
                else:
                    networks[network_lookup[nwk]].xs_central.append(xs_obj)
        
        return networks
    
    #
    # End Method 2
    #
    
    #
    # Method 1: Loop the nwks to get connections
    #           Uses the same _find_xs function as method 2
    #
    # class Connections():
    #
    #     def __init__(self, nwk, us_nwks, ds_nwks):
    #         self.nwk = nwk
    #         self.us_nwks = us_nwks
    #         self.ds_nwks = ds_nwks
    #
    #     def __repr__(self):
    #         return self.nwk.id
    #
    #     def is_upstream(self):
    #         return len(self.us_nwks) < 1
    #
    #     def is_downstream(self):
    #         return len(self.ds_nwks) < 1

        
        
    # def _build_sections(self):
    #     """Create EstryReachSections from geometry/attribute data.
    #
    #     """
    #     nwks = []
    #
    #     # Get metadata and geometry from the loaded nwk GIS data and populate the lines list
    #     for i, nwk in enumerate(self.raw_nwks):
    #         nwk_file = nwk.files.files[0] # only ever a single line file for nwks
    #         for j, fdata in enumerate(nwk_file.data.field_data):
    #             reach_section = EstryBranchObject.create_section(
    #                 fdata['fields'], fdata['geometry'], attr_lookup=nwk_file.data.attribute_lookup, 
    #                 snapping_dist=self.snapping_dist, gis_type=nwk.files.file_type, original_row=j
    #             )
    #             nwks.append(reach_section)
    #
    #     # DEBUG: Sort by x and then y
    #     #         This makes no difference in the new setup but it helps with debugging, 
    #     #         because it keeps the list order consistent on load
    #     # lines = sorted(lines, key = lambda x: (x.first_x, x.first_y))
    #     nwks = sorted(nwks, key = lambda x: (x.nwk_line.us_vertex.x, x.nwk_line.us_vertex.y))
    #     return nwks
    #
    # def _find_connections(self, nwks):
    #     """Find connecting/snapped lines.
    #
    #     TODO: Very slow for large models I expect, O(n^2)?
    #           Inner loop runs entire list for each entry in the list!
    #           Potentially could try and order them near to each other by summing the
    #           x and y locations and then only search an 'arbitrary' number of entries
    #           (line2) from the loopup line (line). I'm sure there are some edge cases
    #           here that mean it wouldn't work (like y+x equals anothers x+y?) but on the
    #           scale of model size this shouldn't be an issue (unless there are locations /
    #           projections where x and y values are very similar?).
    #           Only worry about this if large model tests (>1000 or so nwk lines) cause
    #           significant delay in the loader.
    #     """
    #     connections = []        # raw_nwk index and connecting nwk line info
    #     start_nwks = []         # Most downstream networks to start to load from
    #     nwk_lookup = {}
    #
    #     for i, rsect in enumerate(nwks):
    #         us_nwks = []
    #         ds_nwks = []
    #         for j, rsect2 in enumerate(nwks):
    #             if j == i: continue
    #             if rsect.nwk_line.is_snapped_us(rsect2.nwk_line.us_vertex) or rsect.nwk_line.is_snapped_us(rsect2.nwk_line.ds_vertex):
    #                 us_nwks.append(rsect2.id)
    #             if rsect.nwk_line.is_snapped_ds(rsect2.nwk_line.us_vertex) or rsect.nwk_line.is_snapped_ds(rsect2.nwk_line.ds_vertex):
    #                 ds_nwks.append(rsect2.id)
    #
    #         con = Connections(rsect, us_nwks, ds_nwks)
    #         nwk_lookup[con.nwk.id] = i
    #         if con.is_downstream():
    #             start_nwks.append(con.nwk.id)
    #         connections.append(con)
    #     return connections, start_nwks, nwk_lookup
    #
    #
    # def _build_channels(self):
    #     """Build all of the network data.
    #
    #     """
    #
    #     class NwkGraph():
    #         """Network graph containing branches and nodes."""
    #
    #         def __init__(self, ds_nwk_ids):
    #             self.ds_nwk_ids = ds_nwk_ids    # networks list ids for downstream nwks
    #             self.graph_nodes = {}           # All of the NwkGraphNodes created
    #             self.graph_branches = {}        # All of the NwkGraphBranches created
    #             self.found_nwks = []            # Track nwks already processed
    #             self.nodes_to_process = []      # List of GraphNodes to process
    #             self.process_count = 0          # Index of which node to process next
    #
    #         def build_graph(self):
    #             """Process the network for each of the downstream nwk ids.
    #
    #             Start at the downstream end of a channel and work upstream until there
    #             are no more upstream connections to process.
    #             """
    #             for ds_id in self.ds_nwk_ids:
    #                 self.build_node([ds_id], [])
    #                 self.process_nodes()
    #
    #             # Reset, just in case
    #             self.found_nwks = []
    #             self.nodes_to_process = []
    #             self.process_count = 0
    #
    #         def process_nodes(self):
    #             """Process all of the nodes in the nodes_to_process list.
    #
    #             Goes through the list (which will be appended as we progress and the
    #             process_count updated to reflect the current index) and build all
    #             of the branches and nodes, as well as how they connect to each other.
    #
    #             This method is HEAVILY commented, because it's pretty confusing and there
    #             are some weird edge cases to look out for. The complication probably means
    #             that the algorithm is a bit overly complex, so we might want to revisit
    #             this later and see if it can be simplified and made a bit more robust.
    #             """
    #             while self.process_count < len(self.nodes_to_process):
    #                 node_name = self.nodes_to_process[self.process_count]
    #                 node = self.graph_nodes[node_name]
    #
    #                 # Build a branch and add it to the dict
    #                 branches, node_configs = self.build_branches(node.us_nwks)
    #                 branch_connections = []
    #                 for b in branches:
    #                     branch_connections.append({'branch': b, 'node_us': None, 'node_ds': node_name})
    #                     # Add the branch to the nodes us branches
    #                     self.graph_nodes[node_name].branches_us.append(b.name)
    #
    #                 # Build a node at the upstream end of the branch
    #                 # Node configs is a list with the same order as the branches list
    #                 for i, n in enumerate(node_configs):
    #
    #                     # Make sure the list is sorted alphabetically, otherwise we might get
    #                     # the same connections in a different order leading to a different key!
    #                     node_name = '|'.join(sorted(list(set(n[0] + n[1]))))
    #
    #                     # If we've already reached this connection from another branch, the
    #                     # node will have already been built
    #                     if node_name in self.graph_nodes:
    #
    #                         # Edge case for single nwk line branches that have no upstream 
    #                         # or downstream connections. Ensure they get an upstream node
    #                         con = connections[network_lookup[n[1][0]]]
    #                         if not con.us_nwks and not con.ds_nwks:
    #
    #                             # Create the ds branch and node connections
    #                             branch_connections[i]['node_ds'] = node_name
    #
    #                             # Create a new node and set the upstream branch and node connections
    #                             node_name = self.build_node(n[0], n[1], '.1')
    #                             branch_connections[i]['node_us'] = node_name
    #
    #                             # Add branch to the new nodes ds branches
    #                             self.graph_nodes[node_name].branches_ds.append(branch_connections[i]['branch'].name)
    #
    #                         else:
    #                             branch_connections[i]['node_us'] = node_name
    #
    #                             # Add branch to an existing nodes ds branches
    #                             self.graph_nodes[node_name].branches_ds.append(branch_connections[i]['branch'].name)
    #
    #                     else:
    #                         node_name = self.build_node(n[0], n[1])
    #                         branch_connections[i]['node_us'] = node_name
    #
    #                         # Add branch to the new nodes ds branches
    #                         self.graph_nodes[node_name].branches_ds.append(branch_connections[i]['branch'].name)
    #
    #                 # Set the node affiliations for each of the branches
    #                 node_tracker = {}
    #                 for b in branch_connections:
    #                     check = b['node_us'] if b['node_us'] is not None else ''
    #                     check += b['node_ds'] if b['node_ds'] is not None else ''
    #
    #                     # These 'two' branches are actually a single split branch and they
    #                     # should be merged together (they have matching us/ds nodes)
    #                     if check in node_tracker:
    #                         self.graph_branches[node_tracker[check].branch.name].merge_branches(b['branch'])
    #                     else:
    #                         node_tracker[check] = b['branch']
    #                         self.graph_branches[b['branch'].name] = b['branch']
    #                         self.graph_branches[b['branch'].name].node_us = b['node_us']
    #                         self.graph_branches[b['branch'].name].node_ds = b['node_ds']
    #
    #                 self.process_count += 1
    #
    #         def build_node(self, us_nwks, ds_nwks, sub_name=''):
    #             graph_node = NwkGraphNode(us_nwks, ds_nwks, sub_name)
    #             self.graph_nodes[graph_node.name] = graph_node
    #             self.nodes_to_process.append(graph_node.name)
    #             return graph_node.name
    #
    #         def Build_branches(self, us_nwks):
    #             branches = []
    #             node_configs = []
    #
    #             # Build a new branch starting at each upstream nwk
    #             for n in us_nwks:
    #                 if n in self.found_nwks: continue
    #
    #                 graph_branch = NwkGraphBranch(n)
    #                 us_con_ids, usds_names = graph_branch.build_branch()
    #
    #                 # Add us nwk names and the name of the us nwk of the current branch
    #                 # i.e. all of the connections to a node at this location
    #                 node_configs.append([us_con_ids, [usds_names['us']]])
    #                 branches.append(graph_branch)
    #
    #                 # Track all of the nwks that we've already handled so that we don't
    #                 # process them more than once. This can get tricky when lines are
    #                 # digitised the wrong way, so we track ds nwks as well
    #                 # self.found_nwks += [v for v in usds_names.values() if not v in self.found_nwks]
    #                 for v in usds_names.values():
    #                     if not v in self.found_nwks: self.found_nwks.append(v)
    #             return branches, node_configs
    #
    #
    #     class NwkGraphNode():
    #
    #         def __init__(self, us_nwks, ds_nwks, sub_name=''):
    #             self.name = '{}{}'.format('|'.join(set(us_nwks + ds_nwks)), sub_name)
    #             self.us_nwks = us_nwks if us_nwks else []
    #             self.ds_nwks = ds_nwks if ds_nwks else []
    #             self.branches_us = []
    #             self.branches_ds = []
    #
    #
    #     class NwkGraphBranch():
    #
    #         def __init__(self, us_nwk_id):
    #             self.us_nwk_id = us_nwk_id
    #             self.connection_id = network_lookup[us_nwk_id]
    #             self.branch = None
    #             self.node_us = None
    #             self.node_ds = None
    #
    #         def merge_branches(self, branch):
    #             if self.branch is None: 
    #                 self.branch = branch
    #             else:
    #                 self.branch.merge_branches(branch.branch)
    #
    #         def build_reaches(self, con_id):
    #             reaches = []                        # Temp store for all the reaches in this branch
    #             sections = []                       # Temp store for all the sections in a reach
    #             next_con_ids = []                   # Upstream connections for this branch
    #             con = connections[con_id]           # Connection data (us/ds connection names)
    #             prev_type = con.nwk.section_type    # The section_type of the previous EstrySection
    #             prev_id = ''                        # The EstrySection.id of the previous section
    #             while True:
    #
    #                 # There's a change of channel type, the start or end of
    #                 # a structure, so start a new reach    
    #                 if con.nwk.section_type != prev_type:
    #                     reaches.append(EstryReach(sections))
    #                     # if len(reaches) > 1:
    #                     #     reaches[-1].branch_internal_ds = reaches[-2].us_name
    #                     #     reaches[-2].branch_internal_us = reaches[-1].ds_name
    #                     sections = [con.nwk]
    #                 else:
    #                     sections.append(con.nwk)
    #
    #                 # More than one us channel (or no more channels), so finish branch
    #                 if len(con.us_nwks) != 1:
    #                     # if len(reaches) > 1:
    #                     #     reaches[-1].branch_internal_ds = reaches[-2].us_name
    #                     next_con_ids = con.us_nwks
    #                     break
    #
    #                 # The line is digitised against the direction of flow (the wrong way)
    #                 # When this happens we switch to use ds nwks instead of us
    #                 if con.us_nwks[0] == prev_id:
    #
    #                     # More than one channel, so finish branch
    #                     if len(con.ds_nwks) != 1:
    #                         next_con_ids = con.ds_nwks
    #                         break
    #
    #                     # Swtich to us ds_nwks instead
    #                     con_lookup = network_lookup[con.ds_nwks[0]]
    #                     next_con_ids = con.ds_nwks
    #                 else:
    #                     # Find us_nwks
    #                     con_lookup = network_lookup[con.us_nwks[0]]
    #
    #                 prev_type = con.nwk.section_type
    #                 prev_id = connections[con_id].nwk.id
    #                 con_id = con_lookup
    #                 con = connections[con_id]
    #
    #             if sections:
    #                 reaches.append(EstryReach(sections))
    #
    #             # Set the us and ds internal lookups for reaches internal to a branch.
    #             # i.e. for a change in reach within a branch, let the reaches know
    #             # which EstrySection they are attached to
    #             for i in range(0, len(reaches)):
    #                 if i > 0:
    #                     reaches[i].branch_internal_ds = reaches[i-1].us_name
    #                 if i < len(reaches) - 1: 
    #                     reaches[i].branch_internal_us = reaches[i+1].ds_name
    #
    #             return reaches, next_con_ids
    #
    #         def build_branch(self):
    #             reaches, us_con_ids  = self.build_reaches(self.connection_id)
    #             self.branch = EstryBranch(reaches)
    #             self.name = self.branch.name
    #             return us_con_ids, {'us': reaches[-1].us_name, 'ds': reaches[0].ds_name}
    #
    #
    #     # Create the EstrySection objects and find all of the connections between them
    #     # (snapped us/ds vertices) and identify the downstream nwk lines
    #     networks = self._build_sections()
    #     connections, ds_networks, network_lookup = self._find_connections(networks)
    #
    #     # Associate cross sections with EstrySection data
    #     networks = self._find_xs(networks, network_lookup)
    #
    #     # Build the network, join everything up and make all the associations
    #     branch_graph = NwkGraph(ds_networks)
    #     branch_graph.build_graph()
    #
    #
    #
    #     pass
    #
    #

            
            
            
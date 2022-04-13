"""
 Summary:
    Subclasses the 1D Network API classes for ESTRY specific behaviour
    
 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""

from .. import files
from chyme import network

from chyme.tuflow import GDAL_AVAILABLE, OGR_DRIVERS
if GDAL_AVAILABLE: # Setting import status is handled in tuflow.__init__
    from osgeo import gdal
    from osgeo import ogr



class EstryNetwork(network.Network):
    """1D ESTRY model Network class."""
    
    def __init__(self, contents):
        super().__init__()
        
        
class EstryReachSection(network.ReachSection):
    
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        
        
class EstryTempNetwork():
    
    def __init__(self):
        self.raw_nwks = []
        self.raw_sections = []

    def build_reaches(self, nwks, sections, snapping_dist=0.01):
        """
        """
        if not GDAL_AVAILABLE:
            raise ImportError('Unable to use GDAL to load data.')
        self.snapping_dist = snapping_dist
        self.raw_nwks = nwks
        self.raw_sections = sections
        self._build_networks()
        
        
    def _build_networks(self):
        
        class NwkLine():
            
            def __init__(self, tuflow_id, feat_order, snapping_dist=0.01):
                self.tuflow_id = tuflow_id
                if self.tuflow_id is None:
                    self.tuflow_id = 'NoID_{}'.format(feat_order)
                self.feat_order = feat_order 
                self.snapping_dist = snapping_dist
                self.first_x = -99999
                self.last_x = -99999
                self.first_y = -99999
                self.last_y = -99999
                
                self.bounds = {
                    'x': {'upper': -99999, 'lower': -99999},
                    'y': {'upper': -99999, 'lower': -99999},             
                }

            def fetch_vertices(self, geometry):
                """Find the vertices at the start and end of the line feature.
                """
                # Get WKT geometry previously loaded and create geom
                geom = ogr.CreateGeometryFromWkt(fdata['geometry'])
                self.first_x, self.first_y, _ = geom.GetPoint(0)
                self.last_x, self.last_y, _ = geom.GetPoint(geom.GetPointCount() - 1)
                self.calc_bounds()
                
            def calc_bounds(self):
                # Calc line snapping bounds box
                if self.first_x < self.last_x:
                    self.bounds['x']['upper'] = self.last_x + self.snapping_dist
                    self.bounds['x']['lower'] = self.first_x - self.snapping_dist
                else:
                    self.bounds['x']['upper'] = self.first_x + self.snapping_dist
                    self.bounds['x']['lower'] = self.last_x - self.snapping_dist
                
                if self.first_y < self.last_y:
                    self.bounds['y']['upper'] = self.last_y + self.snapping_dist
                    self.bounds['y']['lower'] = self.first_y - self.snapping_dist
                else:
                    self.bounds['y']['upper'] = self.first_y + self.snapping_dist
                    self.bounds['y']['lower'] = self.last_y - self.snapping_dist
                    
            def check_snapped(self, x, y):
                """Check if x and y are within snapping distance of vertices.
                """
                if self.check_snapped_us(x, y): return True
                if self.check_snapped_ds(x, y): return True
                return False
            
            def check_snapped_us(self, x, y):
                if x < self.first_x + self.snapping_dist and x > self.first_x - self.snapping_dist:
                    if y < self.first_y + self.snapping_dist and y > self.first_y - self.snapping_dist:
                        return True
                return False

            def check_snapped_ds(self, x, y):
                if x < self.last_x + self.snapping_dist and x > self.last_x - self.snapping_dist:
                    if y < self.last_y + self.snapping_dist and y > self.last_y - self.snapping_dist:
                        return True
                return False
            
        
        class EstryBranch():
            
            def __init__(self):
                self.reaches = []
                self.us_node = None
                self.ds_node = None
            
        class EstryReach():
            
            def __init__(self):
                self.nwks = []
                self.us_reaches = {}
                self.ds_reaches = {}
                self._is_start_reach = False
                self._is_end_reach = False
                self._is_singlenwk_reach = False
                
        class EstryNode():
            
            def __init__(self):
                self.nodes = []

            
        lines = []
        for nwk in self.raw_nwks:
            nwk_file = nwk.files.files[0]
            for i, fdata in enumerate(nwk_file.data.field_data):
                id_attr_pos = nwk_file.data.attribute_lookup['ID']
                nwk_line = NwkLine(fdata['fields'][id_attr_pos], i, snapping_dist=self.snapping_dist)
                nwk_line.fetch_vertices(fdata['geometry'])
                lines.append(nwk_line)
        
        # Sort by x and then y to help speedup lookups
        # DEBUG: This makes no difference in the new setup, but it helps with debuggin for
        # now because it keeps the list order consistent on load
        lines = sorted(lines, key = lambda x: (x.first_x, x.first_y))
        
        
        # Find connecting/snapped lines
        # TODO: Very slow for large models I expect, O(n^2)?
        #       Inner loop runs entire list for each entry in the list!
        #       Potentially could try and order them near to each other by summing the
        #       x and y locations and then only search an 'arbitrary' number of entries
        #       (line2) from the loopup line (line). I'm sure there are some edge cases
        #       here that mean it wouldn't work (like y+x equals anothers x+y?) but on the
        #       scale of model size this shouldn't be an issue (unless there are locations /
        #       projections where x and y values are very similar?).
        connections = []
        for i, line in enumerate(lines):
            connections.append([])
            for j, line2 in enumerate(lines):
                if j == i: continue

                snapped_us = snapped_ds = False
                us_start = line.check_snapped_us(line2.first_x, line2.first_y) #or
                us_end =line.check_snapped_us(line2.last_x, line2.last_y)
                ds_start = line.check_snapped_ds(line2.first_x, line2.first_y) #or
                ds_end = line.check_snapped_ds(line2.last_x, line2.last_y)

                if us_start: snapped_us = 'start'
                elif us_end: snapped_us = 'end'

                if ds_start: snapped_ds = 'start'
                elif ds_end: snapped_ds = 'end'
                
                if snapped_us or snapped_ds:
                    connections[i].append({'index': j, 'us': snapped_us, 'ds': snapped_ds})
                    
        # TODO: Need to handle the weird edge case in the tutorial model where there is a weir
        # connected to 2 x connectors that point in opposite directions (there's not really
        # an upstream and downstream end, it goes from the middle out). 
        start_nwks = []
        twoway_nwks = []
        for i, c in enumerate(connections):
            # Most upstream nwk (start of reach)
            if len(c) == 1 and not c[0]['us']:
                start_nwks.append(i)
                
            # Network goes in two directions from line.
            # Normally this is probably a misconfigured line (digitized the wrong way around),
            # but it could be a weir/spill connecting a 1D overflow
            elif len(c) == 2:
                if (
                    c[0]['us'] == 'start' and c[1]['ds'] == 'start' or
                    c[1]['us'] == 'start' and c[0]['ds'] == 'start'
                ):
                    twoway_nwks.append(i)

            # Single nwk reach (not connected to any others, e.g. isolated culvert)
            elif len(c) == 0:
                start_nwks.append(i)
                
            
        reaches = []
        found_nodes = []
        nwk_stack = []        # nwk stack with us nodes

        def build_reach(nwk, index):
            reach = []
            while True:
                reach.append(nwk)
                found_nodes.append(index)
                conn = connections[index]

                ds_nwks_start = []
                ds_nwks_end = []
                for c in conn:
                    # Find connected nwks that start (not end!) downstream
                    if c['ds'] == 'start': ds_nwks_start.append(c)
                    # Find connected nwks that finish (end) downstream
                    if c['ds'] == 'end': ds_nwks_end.append(c)
                
                # Nothing else downstream, reach ends
                if len(ds_nwks_start) == 0:
                    break

                # There's another reach ending here (junction)
                elif len(ds_nwks_end) > 0:
                    for n in ds_nwks_start:
                        con_index = n['index']
                        if not con_index in found_nodes:
                            nwk_stack.append([n['index'], connections[n['index']]])
                    break
                
                # Multiple downstream nwks, so end reach and add to stack
                elif len(ds_nwks_start) > 1:
                    for n in ds_nwks_start:
                        con_index = n['index']
                        if not con_index in found_nodes:
                            nwk_stack.append([n['index'], connections[n['index']]]) 
                    break
                     
                # len == 1, so single downstream node and reach continues   
                else:
                    index = ds_nwks_start[0]['index']
                    if index in found_nodes:
                        break
                    nwk = lines[index]

            if reach:
                reaches.append(reach)
                    

        # Add upstream nodes (no others upstream) to stack            
        for nwk in start_nwks:
            nwk_stack.append([nwk, connections[nwk]])
            i=0
        # nwk_stack.append([0, connections[0]]) # DEBUG: Simplify it 
            
        # Loop the stack of upstream reach nodes
        # TODO: Not handling twoway_nwks yet. Need to consider the best way to do this!
        while len(nwk_stack) > 0:
            nwk = nwk_stack.pop()
            build_reach(lines[nwk[0]], nwk[0])

        
        #
        # DEBUG print some connections to check
        #
        for i, c in enumerate(connections):
            print('{}: {}'.format(i, c))
        print(start_nwks)
        
        # for reach in reaches:
        #     for r in reach:
        #         print(r)

        
        
        


            
            
            
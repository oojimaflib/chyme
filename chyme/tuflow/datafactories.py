"""
 Summary:
    Class data factories for TUFLOW models.
    
    Can be used to construct validated data for the different class types.
    For example, it could include loading, validating and storing the data in the
    attribute table of a GIS file, or a TMF file.
    Likely to be very object specific and should be passed in using the 'factories'
    keyword arg in the TuflowPartTypes builder.

 Author:
    Duncan Runnacles

 Created:
    27 Feb 2022
"""
import logging
logger = logging.getLogger(__name__)

import os
import uuid

from chyme.tuflow import GDAL_AVAILABLE, OGR_DRIVERS
from chyme.tuflow.estry import files as estry_files

# Simple DBF file reader used for testing
# Could be a fallback option when GDAL not available?
# from dbfread import DBF
if GDAL_AVAILABLE: # Setting import status is handled in tuflow.__init__
    from osgeo import gdal, ogr, osr

# try:
#     from osgeo import gdal
#     from osgeo import ogr
# except ImportError as e:
#     GDAL_AVAILABLE = False
#     logger.warning('GDAL Import Failed!')
    
# OGR_DRIVERS = {
#     'shp': 'ESRI Shapefile',
#     'mif': 'MapInfo File',
#     'mid': 'MapInfo File',
#     'sqlite': 'SQLite',
#     'sqlite3': 'SQLite',
# }

class GisData():
    
    def __init__(self):
        self.attributes = []
        self.attribute_lookup = {}
        self.field_data = []
        self.associated_data = {}
        self.crs = None
        
    def add_attributes(self, attributes):
        for i, a in enumerate(attributes):
            self.attributes.append(a)
            self.attribute_lookup[a] = i
            
    def add_new_associated_data(self, name, data_type, overwrite=False):
        if not name in self.associated_data.keys() or overwrite == True:
            self.associated_data[name] = data_type
            

class GisDataFactory():
    
    def __init__(self, file, file_variables, *args, **kwargs):
        self.file = file
        self.file_variables = file_variables
        
    def build_data(self, *args, **kwargs):
        gis_data = GisData()
        if not GDAL_AVAILABLE: return False
        success = False
        abs_path = self.file.absolute_path
        
        # Try and find a driver based on file extension and fall back on OGR if not found
        extension = self.file.extension
        if extension in OGR_DRIVERS:
            driver = ogr.GetDriverByName(OGR_DRIVERS[extension])
            data = driver.Open(abs_path, 0)
        else:
            data = ogr.Open(abs_path)

        if data is not None:
            success = True
            lyr = data.GetLayer()
            gis_data.crs = lyr.GetSpatialRef().ExportToWkt()
            gis_data.add_attributes([field.name for field in lyr.schema]) 
            new_associated_data = self.add_associated_gis_data()
            
            # Get any additional entries needed for gis_data from the subclass
            if new_associated_data is not None:
                gis_data.add_new_associated_data(new_associated_data['name'], new_associated_data['type'])

            # Loop the attribute table and store the field data and feature geometry (WKT)
            for feat in lyr:
                field_data = [feat.GetField(a) for a in gis_data.attributes]
                gis_data.field_data.append({
                    'fields': field_data,
                    'geometry': feat.GetGeometryRef().ExportToWkt()
                })
                # Let the subclass do any processing it wants on the data
                gis_data = self.process_fields(field_data, gis_data)
        return success, gis_data
    
    def add_associated_gis_data(self):
        return None
    
    def process_fields(self, field_data, gis_data):
        # Assume ID is always the first index of the list.
        # Not always true, but safer than using the field name which can be anything
        # if field_data[0] is None or not field_data[0].strip():
        #     gis_data.field_data[-1][0] = '{}'.format(uuid.uuid4())
        return gis_data
        

class TuflowGisNetworkDataFactory(GisDataFactory):
    
    def __init__(self, files, file_variables, *args, **kwargs):
        super().__init__(files, file_variables, *args, **kwargs)

    # def process_fields(self, field_data, gis_data):
    #     gis_data = super().process_fields(field_data, gis_data)
    #     if field_data[0] is None or not field_data[0].strip():
    #         if field_data[1].lower() == 'x':
    #             gis_data.field_data[-1][0] = 'X_{}'.format(uuid.uuid4())
    #         else:
    #             gis_data = super().process_fields(field_data, gis_data)
    #     return gis_data
        
    # def build_data(self, *args, **kwargs):
    #     """
    #     """
    #     return super().build_data(*args, **kwargs)

class TuflowTableLinksDataFactory(GisDataFactory):
    
    def __init__(self, file, file_variables, *args, **kwargs):
        super().__init__(file, file_variables, *args, **kwargs)
        
    # def build_data(self, *args, **kwargs):
    #     return super().build_data(*args, **kwargs)
    
    def add_associated_gis_data(self):
        return {'name': 'source', 'type': []}
    
    def process_fields(self, field_data, gis_data):
        reach_section = estry_files.EstryCrossSection(self.file.absolute_path)
        reach_section.setup_metadata(field_data)
        reach_section.load_rowdata()
        gis_data.associated_data['source'].append(reach_section)
        return gis_data

        
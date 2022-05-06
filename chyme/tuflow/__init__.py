
import logging
logger = logging.getLogger(__name__)

# Global variable for tuflow package to check gdal availability
# Should be set to False if an import fails
GDAL_AVAILABLE = True
try:
    from osgeo import gdal
    from osgeo import ogr
except ImportError as e:
    GDAL_AVAILABLE = False
    logger.warning('GDAL/OGR Import Failed!')
    logger.warning('Cannot use GDAL for geometry loading')
    
OGR_DRIVERS = {
    'shp': 'ESRI Shapefile',
    'mif': 'MapInfo File',
    'mid': 'MapInfo File',
    'sqlite': 'SQLite',
    'sqlite3': 'SQLite',
}

# Static variables for model OS type
# The model format is not dependent on the OS reading the model, but on the format that
# the model was built in or should be written out in.
# We will need to make sure that we handle the read and write of paths correctly for the
# model OS type, which can be independent of the OS being used
MODEL_OS_WINDOWS    = 0
MODEL_OS_LINUX      = 1
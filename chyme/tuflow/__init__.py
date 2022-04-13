
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
from chyme.tuflow import GDAL_AVAILABLE
if GDAL_AVAILABLE:
    from osgeo import ogr

NWK_ATTR_FIELDS = (
    'id', 'type', 'ignore', 'ucs', 'len_or_ana', 'n_nf_cd', 'us_invert',
    'ds_invert', 'form_loss', 'pblockage', 'inlet_type', 'conn_1d_2d',
    'conn_no', 'width_or_d', 'height_or_', 'number_of', 'hconf_or_w',
    'entryc_or_', 'exitc_or_w',
)
NWK_NODE_ATTR_FIELDS = (
    'id',
)
XS_ATTR_FIELDS = (
    'source', 'type', 'flags', 'column_1', 'column_2', 'column_3', 'column_4',
    'column_5', 'column_6', 'z_incremen', 'z_maximum',
)

if GDAL_AVAILABLE:
    NWK_ATTR_TYPES = (
        ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTReal, ogr.OFTReal, ogr.OFTReal, 
        ogr.OFTReal, ogr.OFTReal, ogr.OFTReal, ogr.OFTString, ogr.OFTString,
        ogr.OFTInteger, ogr.OFTReal, ogr.OFTReal, ogr.OFTInteger, ogr.OFTReal,
        ogr.OFTReal, ogr.OFTReal,
    )
    NWK_NODE_ATTR_TYPES = (
        ogr.OFTString,
    )
    XS_ATTR_TYPES = (
        ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTString, ogr.OFTString, 
        ogr.OFTString, ogr.OFTString, ogr.OFTReal, ogr.OFTReal,
    )
else:
    NWK_ATTR_TYPES = ()
    NWK_NODE_ATTR_TYPES = ()
    XS_ATTR_TYPES = ()

"""
 Summary:
    Simple integration tests are utility functions for loading ESTRY models.
    
    Contains some tests and checks for high level, full scope integration tests
    for loading data from the "data/estry_tuflow" test data folder and running
    some sanity checks on the data loaded into Chyme format.
    
    Also includes some sandbox functions for using while developing the codebase.
    I.e. standard load calls and utilities for debugging the ESTRY API.

 Author:
    Duncan Runnacles

 Created:
    15 Jan 2022
""" 
import logging

import os

from tests import CHYME_DIR, TESTS_DIR, DATA_DIR

"""
SANDBOX FUNCTIONS
"""

from chyme.tuflow import core as tuflow_core

LOG_LEVEL = logging.WARNING
# LOG_LEVEL = logging.DEBUG
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARN)
logging.getLogger().setLevel(LOG_LEVEL)
print('\nLOGGING LEVEL SET TO: {}\n'.format(logging.getLevelName(LOG_LEVEL)))

# level = logging.WARNING
# # logger = logging.getLogger()
# logger = logging.getLogger(__name__)
# logger.setLevel(level)
# for handler in logger.handlers:
#     handler.setLevel(level)
# logger = logging.getLogger(__name__)

def check_variables(filepath, test_vals):
    loader = tuflow_core.TuflowLoader(filepath, se_vals=test_vals[0])
    se_and_variables = loader.load()
    print('SE Vals: {}'.format(loader.se_vals))
    print('Variables:')
    variables = se_and_variables['variables']
    print('   1D Timestep = {}'.format(variables['timestep_1d']))
    print('   2D Timestep = {}'.format(variables['timestep_2d']))
    print('   Cell Size = {}'.format(variables['cell_size']))
    del(loader)
    if (variables['timestep_1d'] == test_vals[1]['timestep_1d'] and 
        variables['timestep_2d'] == test_vals[1]['timestep_2d'] and 
        variables['cell_size'] == test_vals[1]['cell_size']
        ):
        return 'PASSED'
    else:
        return 'FAILED!!'
    
def load_tuflow():

    fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D.tcf')
    # fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D_WithECF.tcf')
    # fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D_WithAutoECF.tcf')
    # model = tuflow_core.TuflowModel(fpath)
    # model.read()
    

    se_vals_tests = [
        # ['s NON s1   BAS s2 12m s3 Block e1   Q0100 e2 6hr', {'timestep_1d': '3.0', 'timestep_2d': '6.0', 'cell_size': '12'}],
        ['s NON s1   DEV s2 10m s3 Block e1   Q0100 e2 6hr', {'timestep_1d': '2.5', 'timestep_2d': '5.0', 'cell_size': '10', 'end_time': '5'}],
        ['s NON s1   DEV s2 2m s3 Block e1   Q0100 e2 12hr', {'timestep_1d': '0.5', 'timestep_2d': '1.0', 'cell_size': '2', 'end_time': '5'}],
        ['s NON s1   DEV s2 1m s3 Block e1   Q50 e2 12hr', {'timestep_1d': '0.75', 'timestep_2d': '1.5', 'cell_size': '5', 'end_time': '5'}],
        ['s NON s1   BAS s2 5m s3 Block e1   Q50 e2 6hr', {'timestep_1d': '0.25', 'timestep_2d': '0.5', 'cell_size': '1', 'end_time': '3'}],
    ]
    print('VARIABLES TEST...')
    results = []
    for i, test in enumerate(se_vals_tests):
        print('\nTest: {}...'.format(i))
        results.append(check_variables(fpath, test))
        
    print('\nResults Summary:')
    for i, r in enumerate(results):
        print('Test {}: {}\t({})'.format(i, r, se_vals_tests[i][0]))

    

if __name__ == '__main__':
    load_tuflow()
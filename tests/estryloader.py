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
import sys

from tests import CHYME_DIR, TESTS_DIR, DATA_DIR

"""
SANDBOX FUNCTIONS
"""

from chyme.tuflow import loader as tuflow_loader
from chyme.api.model import Filter
from chyme.api.estrymodel import EstryModel

# LOG_LEVEL = logging.WARNING
LOG_LEVEL = logging.DEBUG
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
logger = logging.getLogger(__name__)

def check_variables(filepath, test_vals):
    loader = tuflow_loader.TuflowLoader(filepath, se_vals=test_vals[0])
    se_and_variables = loader.load()
    print('SE Vals: {}'.format(loader.se_vals))
    print('Variables:')
    variables = se_and_variables['variables']
    print('   1D Timestep = {}'.format(variables['timestep_1d']))
    print('   2D Timestep = {}'.format(variables['timestep_2d']))
    print('   Cell Size = {}'.format(variables['cell_size']))
    response = 'PASSED'
    if (variables['timestep_1d'] == test_vals[1]['timestep_1d'] and 
        variables['timestep_2d'] == test_vals[1]['timestep_2d'] and 
        variables['cell_size'] == test_vals[1]['cell_size']
        ):
        if 'output_interval' in test_vals[1]:
            print('   Output Interval = {}'.format(loader.components['control_1d'].parts[3].load_data.raw_variable))
            if loader.components['control_1d'].parts[4].load_data.raw_variable != test_vals[1]['output_interval']:
                response = 'FAILED'
    else:
        response = 'FAILED!!'
    del(loader)
    return response
    
def tuflow_logic_test(break_on_fail=False):

    fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D.tcf')
    # fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D_WithECF.tcf')
    # fpath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D_WithAutoECF.tcf')
    # model = tuflow_loader.TuflowModel(fpath)
    # model.read()
    

    se_vals_tests = [
        # Test a range of scenario logic
        ['s NON s1   DEV s2 10m s3 Block e1   Q0100 e2 6hr', {'timestep_1d': '2.5', 'timestep_2d': '5.0', 'cell_size': '10', 'end_time': '5'}],
        ['s NON s1   DEV s2 2m s3 Block e1   Q0100 e2 12hr', {'timestep_1d': '0.5', 'timestep_2d': '1.0', 'cell_size': '2', 'end_time': '5'}],
        ['s NON s1   DEV s2 1m s3 Block e1   Q50 e2 12hr', {'timestep_1d': '0.75', 'timestep_2d': '1.5', 'cell_size': '5', 'end_time': '5'}],
        ['s NON s1   BAS s2 5m s3 Block e1   Q50 e2 6hr', {'timestep_1d': '0.25', 'timestep_2d': '0.5', 'cell_size': '1', 'end_time': '3'}],
        
        # Test some weird inputs
        ['-s NON -s1   DEV -s2 2m -s3 Block e1   Q0100 -e2 12hr', {'timestep_1d': '0.5', 'timestep_2d': '1.0', 'cell_size': '2', 'end_time': '5'}],
        ['s NON s1   DEV s2 2m s3 "Space Block" -e1   Q0100 e2 12hr', {'timestep_1d': '0.5', 'timestep_2d': '1.0', 'cell_size': '2', 'end_time': '5', 'output_interval': '180'}],

        # Default (empty) scenario/event inputs
        ['', {'timestep_1d': '0.5', 'timestep_2d': '1.0', 'cell_size': '2', 'end_time': '3'}],
    ]
    print('VARIABLES TEST...')
    results = []
    for i, test in enumerate(se_vals_tests):
        print('\nTest: {}...'.format(i))
        results.append(check_variables(fpath, test))
        
    print('\nResults Summary:')
    for i, r in enumerate(results):
        print('Test {}: {}\t({})'.format(i, r, se_vals_tests[i][0]))
        if break_on_fail and 'FAIL' in r:
            raise AttributeError
        
    print('\n\n')
    
def estry_channels():
    # Setup chyme messaging listener
    import threading
    from chyme.utils import logsettings
    
    class MyListener(logsettings.ChymeProgressListener):
        
        def progress(self, percentage, **kwargs):
            print('Progress = {}%'.format(percentage))
        
        def notify(self, msg, **kwargs):
            print('MyListener: {}'.format(msg))
    
    my_listener = MyListener() 
    logsettings.add_progress_listener(my_listener)

    # Works for multi and single threaded calls
    # MULTI THREADED
    # load_thread = threading.Thread(target=estry_channels, name='estry_channels')
    # load_thread.daemon = True
    # load_thread.start()
    # load_thread.join()
    # SINGLE THREADED
    
    error_logs = my_listener.get_logs()
    filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_1D2D.tcf')
    se_vals = 's NON s1   DEV s2 10m s3 Block e1   Q0100 e2 6hr'
    loader = tuflow_loader.TuflowLoader(filepath, se_vals=se_vals)
    loader.load()
    network = loader.build_estry_reaches()
    # filter = Filter(file_and=['ds5', 'csv'])
    filter = Filter(f_or=['ds'], f_not=['3', '2', 'weir'])
    estry_model = EstryModel(network, filter=filter)
    # xs = estry_model.cross_sections(name_filter='ds5')
    xs = estry_model.cross_sections()
    
    error_logs = my_listener.get_logs()
    i=0
    

def tuflow_fileresolver_test():
    from chyme.tuflow import tuflow_utils as tu
    from chyme.tuflow.components import SEStore

    se_str = '-s1 BAS -s2 10m -e1 Q100'
    filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'runs', 'Model_~s1~_~e1~_1D2D_Logic.tcf')
    loader = tuflow_loader.TuflowLoader(filepath, se_vals=se_str)
    loader.load()

    q=0
    

    
def test_all():
    estry_channels()
    # tuflow_fileresolver_test()
    tuflow_logic_test(break_on_fail=True)

if __name__ == '__main__':
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    if args and args[0] == '-test_all':
        test_all()
        sys.exit()

    tuflow_fileresolver_test()
    # tuflow_logic_test()
    # estry_channels()
    
    q=0
    
    
    
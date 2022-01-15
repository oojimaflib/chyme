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
import os


"""
SANDBOX FUNCTIONS
"""

from chyme.tuflow import core as tuflow_core

def load_estry_only():
    print('start')
#     fpath = os.path.join('data', 'estry_tuflow', 'M04_5m_001.tcf')
    fpath = "C:/Users/ermev/Documents/Main/Company/3_Technical/Dev/Chyme/chyme/tests/data/estry_tuflow/runs/Model_1D2D.tcf"
#     fpath = "C:/Users/ermev/Documents/Main/Company/3_Technical/Dev/Chyme/chyme/tests/data/estry_tuflow/runs/Model_1D2D_WithECF.tcf"
    model = tuflow_core.TuflowModel(fpath)
    model.read()
    
    print('done')
    i=0
    

if __name__ == '__main__':
    load_estry_only()
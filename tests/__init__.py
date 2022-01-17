import os

# Static vars for accessing the main folders in the API
# CHYME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..')
CHYME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(CHYME_DIR, 'tests')
DATA_DIR = os.path.join(TESTS_DIR, 'data')
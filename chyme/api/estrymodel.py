"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    23 Apr 2022
"""
from chyme.api.model import Model1D
from chyme.api.model import Filter



class EstryModel(Model1D):
    
    def gis_files(self):
        raise NotImplementedError

    def csv_files(self):
        raise NotImplementedError
    
    def cross_sections(self):
        xs = []
        for b in self.network.branches:
            for r in b.reaches:
                for s in r.sections:
                    xs += [x for x in s.xs_us if x not in xs]
                    xs += [x for x in s.xs_ds if x not in xs]
                    xs += [x for x in s.xs_central if x not in xs]
        
        if self.filter.f_and:
            xs = [x for x in xs if self.filter.f_re_and.search(x.id)]
        if self.filter.f_or:
            xs = [x for x in xs if self.filter.f_re_or.search(x.id)]
        if self.filter.f_not:
            xs = [x for x in xs if self.filter.f_re_not.search(x.id)]
        return xs

    
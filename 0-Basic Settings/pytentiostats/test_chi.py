from pstat import *

folder = 'C:/Users/oliverrz/Desktop/Oliver/Data/220214_potentiostats-library'
path_pstat = 'C:/Users/oliverrz/Desktop/chi760e'
pstat_model = 'chi760e'

Potentiostat(folder_save=folder, pstat_model=pstat_model, path_pstat=path_pstat, verbose=1)
tech = CV()
tech.bipot(E=1)
tech.run()

tech = OCP()
tech.run()


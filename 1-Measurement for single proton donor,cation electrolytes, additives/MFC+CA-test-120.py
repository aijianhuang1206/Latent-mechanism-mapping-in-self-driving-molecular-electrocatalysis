import glob, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from tqdm import tqdm
from Hardwaretesting.MFC import control_MFC
from Hardwaretesting.stir import stirring
from scipy.signal import find_peaks, savgol_filter
import pytentiostats as pstat
import datetime, time
from alicat import FlowController

print('Ar purging')
flow_controller2 = FlowController(port='COM9')   #change
flow_controller3 = FlowController(port='COM10')   #change
flow_controller4 = FlowController(port='COM11')   #change
def control_MFC2 (flow_controller=None, operation='open'):
    if operation=='open':
        flow_controller2.set_flow_rate(50)
    elif operation=='close':
        flow_controller2.set_flow_rate(0)
    elif operation=='inject':
        flow_controller2.set_pressure(50)
    else:
        raise AssertionError('Please provide valid command to MFC.')

def control_MFC3(flow_controller=None, operation='open'):
    if operation=='open':
        flow_controller3.set_flow_rate(10)
    elif operation=='close':
        flow_controller3.set_flow_rate(0)
    elif operation=='inject':
        flow_controller3.set_pressure(10)
    else:
        raise AssertionError('Please provide valid command to MFC.')

def control_MFC4(flow_controller=None, operation='open'):
    if operation=='open':
        flow_controller4.set_flow_rate(40)
    elif operation=='close':
        flow_controller4.set_flow_rate(0)
    elif operation=='test':
        flow_controller4.set_pressure(50)
    else:
        raise AssertionError('Please provide valid command to MFC.')

control_MFC2(flow_controller2, 'open')
control_MFC4(flow_controller4, 'open')
control_MFC3(flow_controller3, 'open')
time.sleep(300)
control_MFC3(flow_controller3, 'close')
control_MFC4(flow_controller4, 'test')

model = 'chi760e'
path = 'C:\python-Setup\CO2-Setup\pytentiostats'  # Folder where the chi760e.exe is located
file_title = 'CV-data-2024-0528'  # File name

file_path = 'C:\python-Setup\CV-data-2024-0528' # the path where you want to save the test data
pstat.Setup(model=model, path_exe=path, folder=file_path)



def run_ca(time=30, Hz=1, sensitivity=1e-4):

    caname = f"CA_{str(datetime.datetime.now().isoformat(timespec='seconds')).replace(' ', '_').replace(':', '_')}"
    caheader = f'CA'
    ca = pstat.CA(Estep=0.1, Ehigh=0.1, Elow=-0.3, dt=0.1, ttot=1/Hz, sens=sensitivity, fileName=caname, header=caheader, tstep=time+1)
    ca.run()
    return caname

file_ca=run_ca(179, sensitivity=1e-4)

control_MFC2(flow_controller2, 'close')
control_MFC4(flow_controller4, 'close')
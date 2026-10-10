import pytentiostats as pstat
import datetime, time
import numpy as np
from alicat import FlowController
import time
from ika.magnetic_stirrer import MagneticStirrer

#port = 'COM14'
#plate = MagneticStirrer(device_port=port)

print('N2 purging')
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

#plate.start_stirring()
#plate.target_stir_rate = 400
control_MFC2(flow_controller2, 'open')
control_MFC4(flow_controller4, 'open')
control_MFC3(flow_controller3, 'open')
time.sleep(300)
control_MFC3(flow_controller3, 'close')
control_MFC4(flow_controller4, 'test')
#plate.stop_stirring()

#CV measurement
print('stop Ar purging and start CV measurement')
model = 'chi760e'
path = 'C:\python-Setup\CO2-Setup\pytentiostats'  # Folder where the chi760e.exe is located
file_title = 'CV-data-2024-0528'  # File name

def run_ocp(filepath):
    print('Measuring OCP')
    filename = f"OCP_{str(datetime.datetime.now().isoformat(timespec='seconds')).replace(' ', '_').replace(':', '_')}"
    ocp = pstat.OCP(ttot=10, dt=0.01, fileName=filename)
    ocp.run()
    ocp_data = pstat.LoadOCP(filename, folder=filepath, model=model)
    print('Finished measuring OCP')
    print('Waiting 5 s')
    time.sleep(5)
    print('Finished waiting\n')
    Eini = np.mean(ocp_data.E)  # which will be used in EIS
    return Eini


def run_eis(filepath, Eini):
    print('Measuring EIS at OCP and get Ru')
    filename=f"EIS_{str(datetime.datetime.now().isoformat(timespec='seconds')).replace(' ', '_').replace(':', '_')}"
    eis = pstat.EIS(Eini=Eini, fl=10, fh=1e6, amp=0.005, fileName=filename, header='EIS for Ru')
    eis.run()
    time.sleep(5)
    eis_data = pstat.LoadEIS(filename, folder=filepath, model=model)
    Ru = eis_data.rZ[np.argmax(eis_data.iZ)]  # get the Ru for IR compensation
    print(f'Finished measuring EIS at OCP and get Ru: {round(Ru,2)} Ohm\n')
    print('Waiting 5 s')
    time.sleep(5)
    print('Finished waiting\n')
    return Ru

def run_cv(E_window_a, E_window_length, scan_rate, filetitle, scan_rate_idx, Ru_test_idx, Ru_test):
     # define anything you want to include in the title
    Eini_cv = -0.7  # V, initial potential vs Ag/AgCl
    Ev1_cv = -0.7  # V, first vertex potential
    Ev2_cv = Eini_cv - E_window_length  # V, second vertex potential
    Efin_cv = Eini_cv  # V, final potential
    nSweeps_cv = 5  # number of sweeps
    dE_cv = 0.001  # V, potential increment

    if scan_rate >= 0.07:
        sens_cv = 1e-4
    elif scan_rate >= 0.010:
        sens_cv = 1e-5
    elif scan_rate >= 0.001:
        sens_cv = 1e-6  # V/A, current sensitivity
    elif scan_rate <=0.00005:
        sens_cv = 1e-6
    else:
        sens_cv = 1e-6
    fileName = f"{filetitle}_{scan_rate_idx}{str(Ru_test_idx).zfill(3)}_{int(1000 * scan_rate)}mVs_{round(Ru_test)} Ohm_{str(datetime.datetime.now().isoformat(timespec='seconds')).replace(' ', '_').replace(':', '_')}"
    header = f'CVof{filetitle}_{scan_rate}Vs_{Ru_test}_Ohm'

    cv = pstat.CV(Eini=Eini_cv, Ev1=Ev1_cv, Ev2=Ev2_cv, Efin=Efin_cv, nSweeps=nSweeps_cv, dE=dE_cv, sr=scan_rate,
                  sens=sens_cv, fileName=fileName, header=header)
    #start_stirring(plate, 400)
    cv.ircomp(Ru=Ru_test)  # Ru get from EIS
    cv.run()
    return fileName, sens_cv  # the returned value can be any value of interest


#def run_ca(time=30, Hz=1, sensitivity=1e-5):

    #caname = f"CA_{str(datetime.datetime.now().isoformat(timespec='seconds')).replace(' ', '_').replace(':', '_')}"
    #caheader = f'CA'
    #ca = pstat.CA(Estep=1, Ehigh=1, Elow=-1.5, dt=0.1, ttot=1/Hz, sens=sensitivity, fileName=caname, header=caheader, tstep=time+1)
    #ca.run()
    #return caname

file_path = 'C:\python-Setup\CV-data-2024-0528' # the path where you want to save the test data
pstat.Setup(model=model, path_exe=path, folder=file_path)
E_ocp=run_ocp(file_path) # run OCP to get the open circuit potential
Ru=run_eis(file_path, E_ocp) # run EIS at E=E_ocp, to estimate Ru

#  technical params for CV
E_window_a = 1.2 #V
E_window_length = 1.2 #V
scan_rate = 0.1 #V/s
filetitle = 'CV-data-2024-0528' # filename
scan_rate_idx = 0 # this is for me to have a better record of measured scan rate and Ru
Ru_test_idx = 0
Ru_test = Ru
fileName, sens_cv = run_cv(E_window_a, E_window_length, scan_rate, file_title, scan_rate_idx, Ru_test_idx, Ru,)

control_MFC2(flow_controller2, 'close')
control_MFC4(flow_controller4, 'close')

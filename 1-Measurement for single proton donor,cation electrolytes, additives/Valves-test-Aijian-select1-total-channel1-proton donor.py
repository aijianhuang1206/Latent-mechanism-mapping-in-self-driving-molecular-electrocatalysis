import MXII_valve as mxii
from ismatec.peristaltic_pump import RegloICCFourChannel, ChannelStatus
import ismatec.errors
import time
import numpy as np
from alicat import FlowController
import time
from tqdm import tqdm

valve_switch = mxii.MX_valve('COM12', ports=2, name='Switching', verbose=True)
valve_select1 = mxii.MX_valve('COM4', ports=6, name='Selection', verbose=True)
icc2 = RegloICCFourChannel('COM7')
flow_controller5 = FlowController(port='COM3')

def control_MFC5(flow_controller5=None, operation='close'):

    if operation == 'open':
        flow_controller5.set_flow_rate(50)
    elif operation == 'close':
        flow_controller5.set_flow_rate(0)

#loading the solvent
valve_select1.change_port(1)
valve_switch.change_port(1)
icc2.set_clockwise(3)
icc2.set_mode_pump_rpm(3, 100)
icc2.start(3)
time.sleep(15)
icc2.stop(3)

#3s per titration
control_MFC5(flow_controller5, 'open')
icc2.set_mode_pump_rpm(3, 20)
icc2.start(3)
time.sleep(3)
icc2.stop(3)
valve_switch.change_port(2)
time.sleep(20)
valve_switch.change_port(1)
control_MFC5(flow_controller5, 'close')





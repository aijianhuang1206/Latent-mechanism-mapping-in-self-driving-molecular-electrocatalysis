from ismatec.peristaltic_pump import RegloICCFourChannel, ChannelStatus
import ismatec.errors
import time
import numpy as np
#port_pump = 'COM8'
global icc2
global icc1
icc2 = RegloICCFourChannel('COM3')
icc2.set_counter_clockwise(4)
icc2.set_mode_pump_rpm(4, 100)
icc1 = RegloICCFourChannel('COM7')

global c_buffer_stock
c_buffer_stock = 0.2
global c_complex_stock
c_complex_stock = 5
def initialize_pump():
    for i in range(4):
        icc2.set_counter_clockwise(i + 1)
        icc2.start(i+1)
    icc1.set_counter_clockwise(4)
    icc1.set_clockwise(1)
    icc1.set_clockwise(3)  # 2 is discarded because of interference with 3.
    time.sleep(20)
    for i in range(4):
        icc2.stop(i+1)

#%% pump calibration, for pump 1, calibrate the flow rate rpm vs mL/min
def calibrate():
    m1=[]
    for i in range(4):
       icc2.set_counter_clockwise(i + 1)
       icc2.set_mode_pump_rpm(i+1, 100)
    m1.append(float(input(f"Weighing the mass for calibrating channels.\n please enter the initial mass to continue: ")))
    for i in range(3):
        icc2.start(i+1)
        channel=[1,2,3,4]
        channel.pop(i)
        for k in channel:
            icc2.stop(k)
        time.sleep(5)
        icc2.stop(i+1)
        m1.append(float(input(f"Weighing the mass for calibrating channel {i+1}.\n please enter the mass to continue: ")))
    real_fr = np.diff(m1)/5  # in ml/s
    return {index[0]+1: v for index, v in np.ndenumerate(real_fr)}  # in a dictionary
#%% deal with the values
def volume_ratio_correction(real_fr, setted_fr):
    corrected_volume_ratio = [x * y / sum([x * y for x, y in zip(real_fr.values(), setted_fr.values())]) *100 for x, y in zip(real_fr.values(), setted_fr.values())]
    return {index[0]+1: v for index, v in np.ndenumerate(corrected_volume_ratio)}

#%% deal with the actual concentration
def corrected_concentration(corrected_volume_ratio):
    c_complex = c_complex_stock * corrected_volume_ratio[1]/sum(corrected_volume_ratio.values())
    c_buffer = c_buffer_stock * corrected_volume_ratio[2]/sum(corrected_volume_ratio.values())
    return c_complex, c_buffer
#%% for calibrating the volumes
# the stock solution: 5 mM Ferricyanide, 2 M R-B buffer, H2O
# the target solution: 2 mM Ferricyanide, 0.1 M R-B buffer, 2 ml
# pump 2, channel 1: complex; channel 2: buffer, channel 3: solvent, channel 4: for pH titration
# pump 1, channel 4: waste
# set the pump rate 1 as complex, set pump rate 2 as buffer, set pump rate 3 as solvent



def calculate_flow_rate(c_complex=2, c_buffer=0.1):
    #c_complex = 2
    #c_buffer = 0.1  # 0.1 M of R-B buffer
    # params
    #c_buffer_stock = 2  #  2 M for now
    #c_complex_stock = 5  # mM
    tot_flow_rate = 100  # rpm
    # pump settings
    # def get flow rate
    channel_complex = 1
    channel_buffer = 2
    channel_solvent = 3
    complex_rate = np.around(c_complex / c_complex_stock * tot_flow_rate, 2)
    buffer_rate = np.around(c_buffer / c_buffer_stock * tot_flow_rate, 2)
    svt_rate = np.around(tot_flow_rate - complex_rate - buffer_rate, 2)
    print(f'Complex: {complex_rate} rpm, Buffer: {buffer_rate} rpm, Solvent: {svt_rate} rpm')
    flow_rate = {
        channel_complex: complex_rate,
        channel_buffer: buffer_rate,
        channel_solvent: svt_rate,
    }
    return flow_rate
# def set flow rate


def flow_rate_setting(flow_rate1=None):
    print('Assigning flow rates...\n')
    flow_rate2 = {1: 100, 4: 100}
    if flow_rate1 is None:
        flow_rate1 = {1: 33, 2: 33, 3: 33}

    for key, value in flow_rate1.items():
        icc2.set_counter_clockwise(key)
        icc2.set_mode_pump_rpm(key, value)
        print(f'Setting flow rate for pump 1 channel {key} as {value} rpm')
    for key, value in flow_rate2.items():
        icc1.set_clockwise(key)
        icc1.set_mode_pump_rpm(key, value)
    print('\n')
    return flow_rate1

# channel flushing


def pumping_waste_out(flow_rate=100, cleaning_time=30):
    for i in range(4):
        icc2.set_counter_clockwise(i + 1)
    try:
        icc1.set_clockwise(4)
        icc1.set_mode_pump_rpm(4, 100)
        icc1.start(4)
        print(f'\nStarting channel 4 at 100 rpm to pump waste out')
    except ismatec.errors.PumpError:
        icc1.stop(4)
        print(f'\nChannel 4 keeps stopped because 0 rpm assigned.')
    time.sleep(cleaning_time)
    icc1.stop(4)


# rinsing_cleaning including initially rinsing the cell and tubings and rinsing between changing the solution
def rinsing_cleaning(with_B=True, initial=True, repeats=None, flow_rate=None, cleaning_time=40):
    for i in range(4):
        icc2.set_counter_clockwise(i + 1)
        icc1.set_clockwise(i + 1)
    if initial:
        assert repeats is None, 'Cannot assgin initial flushing and rinsing at the same time'
        print('Channel initial flushing started.\n')
    else:
        assert repeats is not None, 'Rinsing times are needed'
        print('Channel cleaning started')
    flow_rate=flow_rate_setting(flow_rate)
    pumping_waste_out()
    time.sleep(5)
    if initial:
        repeats=1
    for times in range(repeats):
        print(f'Starting rinsing: {times+1}')
        if with_B:
            cnl_idx = 0
        else:
            cnl_idx = 1
        for k in range(cnl_idx,3):
            try:
                icc2.start(k + 1)
                print(f'Starting channel {k + 1} at {flow_rate[k + 1]} rpm')
            except ismatec.errors.PumpError:
                icc2.stop(k + 1)
                print(f'Channel {k + 1} keeps stopped because 0 rpm assigned.')
            time.sleep(0.1)
        time.sleep(cleaning_time * 0.7)
        for k in range(cnl_idx,3):
            icc2.stop(k + 1)
        time.sleep(5)
        pumping_waste_out()
    if initial:
        print('Channel initial flushing finished.\n')
    else:
        print('Channel cleaning finished\n.')


def making_solution(with_B=True, flow_rate=None, flow_time=10, cali_rate=None):  # note, the flow time needs to be calibrated to ensure 2 ml solution was added.
    for i in range(4):
        icc2.set_counter_clockwise(i + 1)
        icc1.set_clockwise(i + 1)
    flow_rate_setting(flow_rate)
    print('Start making the solution...\n')
    assert with_B==True, "The complex solution is missing"
    for k in range(3):
        try:
            icc2.start(k + 1)
            print(f'Starting channel {k + 1} at {flow_rate[k + 1]} rpm')
        except ismatec.errors.PumpError:
            icc2.stop(k + 1)
            print(f'Channel {k + 1} keeps stopped because of assigned 0 rpm.')
        time.sleep(0.1)
    time.sleep(flow_time)
    for k in range(3):
        icc2.stop(k + 1)
        time.sleep(0.1)
    time.sleep(5)
    print('Solution made.\n')
    corrected_volume_r=volume_ratio_correction(cali_rate, flow_rate)
    c_complex, c_buffer = corrected_concentration(corrected_volume_r)
    corrected_volume= (0.1+flow_time)*sum(cali_rate[key]*flow_rate.get(key, 0) for key in cali_rate)/100
    return corrected_volume, c_complex, c_buffer







def cleaning_all_channels():
    for i in range(3):
        icc2.set_mode_pump_rpm(i+1,100)
        icc2.start(i+1)
    time.sleep(20)
    for i in range(3):
        icc2.stop(i+1)

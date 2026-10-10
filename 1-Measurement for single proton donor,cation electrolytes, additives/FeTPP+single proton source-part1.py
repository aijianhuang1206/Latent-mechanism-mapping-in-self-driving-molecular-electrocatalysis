from ismatec.peristaltic_pump import RegloICCFourChannel, ChannelStatus
import ismatec.errors
import time
import numpy as np
import pytentiostats as pstat
import datetime, time
from alicat import FlowController
from ika.magnetic_stirrer import MagneticStirrer
import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])
#pump control COM
#pump 1: channel 1: 0.5 mM FeTPP; channel 2: DMF; channel 3: PBS; channel 4: H2O
#pump 2: channel 1: Waste;

icc1 = RegloICCFourChannel('COM6')
icc2 = RegloICCFourChannel('COM7')

port = 'COM14'
plate = MagneticStirrer(device_port=port)

#pump the 4 ml phosphate buffer in
print('pumping in with 4 ml phosphate buffer first time')
icc1.set_clockwise(3)
icc1.set_mode_pump_rpm(3, 63)
icc1.start(3)
time.sleep(30)
icc1.stop(3)

exec(open('MFC+CA-test-120.py').read())

#pumping the 4ml phosphate buffer out
print('pumping out with 4 ml phosphate buffer')
icc2.set_counter_clockwise(1)
icc2.set_mode_pump_rpm(1, 100)
icc2.start(1)
time.sleep(60)
icc2.stop(1)
print('Waiting 10 s')
time.sleep(10)

#rinsing with 5 ml H20 for 2 times
print('rinsing with 5 ml H2O')
print('rinsing in first time')
icc1.set_clockwise(4)
icc1.set_mode_pump_rpm(4, 79)
icc1.start(4)
time.sleep(30)
icc1.stop(4)
print('Waiting 30 s')

plate.start_stirring()
plate.target_stir_rate = 400
time.sleep(40)
plate.stop_stirring()
time.sleep(10)

print('rinsing out first time')
icc2.set_counter_clockwise(1)
icc2.set_mode_pump_rpm(1, 100)
icc2.start(1)
time.sleep(60)
icc2.stop(1)
print('Waiting 10 s')
time.sleep(10)
#rinsing in second time
print('rinsing in second time')
icc1.set_clockwise(4)
icc1.set_mode_pump_rpm(4, 79)
icc1.start(4)
time.sleep(30)
icc1.stop(4)
print('Waiting 30 s')

plate.start_stirring()
plate.target_stir_rate = 400
time.sleep(40)
plate.stop_stirring()
time.sleep(10)

print('rinsing out second time')
icc2.set_counter_clockwise(1)
icc2.set_mode_pump_rpm(1, 100)
icc2.start(1)
time.sleep(60)
icc2.stop(1)
print('Waiting 10 s')
time.sleep(10)

#rinsing with 6 ml DMF for 2 times
print('rinsing with 6 ml DMF in and out for 2 times')
print('rinsing in first time')
icc1.set_clockwise(2)
icc1.set_mode_pump_rpm(2, 95)
icc1.start(2)
time.sleep(30)
icc1.stop(2)
print('Waiting 30 s')

plate.start_stirring()
plate.target_stir_rate = 400
time.sleep(40)
plate.stop_stirring()
time.sleep(10)

print('rinsing out first time')
icc2.set_counter_clockwise(1)
icc2.set_mode_pump_rpm(1, 100)
icc2.start(1)
time.sleep(60)
icc2.stop(1)
print('Waiting 10 s')
time.sleep(10)

print('rinsing in second time')
icc1.set_clockwise(2)
icc1.set_mode_pump_rpm(2, 95)
icc1.start(2)
time.sleep(30)
icc1.stop(2)
print('Waiting 30 s')

plate.start_stirring()
plate.target_stir_rate = 400
time.sleep(40)
plate.stop_stirring()
time.sleep(10)

print('rinsing out second time')
icc2.set_counter_clockwise(1)
icc2.set_mode_pump_rpm(1, 100)
icc2.start(1)
time.sleep(60)
icc2.stop(1)
print('Waiting 10 s')
time.sleep(10)

#pumping_2 ml FeTPP solvent_in
print('pumping 2ml FeTPP solvent in')
icc1.set_clockwise(1)
icc1.set_mode_pump_rpm(1, 32)
icc1.start(1)
time.sleep(30)
icc1.stop(1)


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

#titratioin 2 ml proton source in
print('titrate 2 ml 750mM proton source solvent in')
run_script("Valves-test-Aijian-select1-total-channel1.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 29)
run_script("Valves-test-Aijian-select1-total-channel6.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 9)


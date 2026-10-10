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
print('titrate 3-FeTPP+12-6-20-1-19-0-10-2.py solvent in')
run_script("Valves-test-Aijian-select1-total-channel1-Phenol.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 11)
run_script("Valves-test-Aijian-select1-total-channel3-TFE.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 5)
run_script("Valves-test-Aijian-select1-total-channel4-111333-Hexafluoro.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 19)
run_script("Valves-test-Aijian-select1-total-channel5-TBAPF6.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 0)
run_script("Valves-test-Aijian-select1-total-channel6-CsPF6.py", 1)
run_script("Valves-test-Aijian-select1-inject.py", 18)

run_script("Valves-test-Aijian-select2-total-channel4-TMAPF6.py", 0)
run_script("Valves-test-Aijian-select2-inject.py", 0)
run_script("Valves-test-Aijian-select2-total-channel2-Perylene.py", 1)
run_script("Valves-test-Aijian-select2-inject.py", 9)
run_script("Valves-test-Aijian-select2-total-channel3-Blank.py", 1)
run_script("Valves-test-Aijian-select2-inject.py", 1)
import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])


run_script("FeTPP+single proton source-part1.py", 1)
run_script("4-FeTPP+0-22-12-11-0-9-10-6.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)




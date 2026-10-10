import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+0-0-36-16-4-0-10-4.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)


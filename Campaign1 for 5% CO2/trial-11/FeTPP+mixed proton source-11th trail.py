import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+22-0-18-9-11-0-9-1.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+22-0-18-10-10-0-9-1.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)










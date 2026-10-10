import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+0-28-12-9-0-11-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+16-0-24-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)




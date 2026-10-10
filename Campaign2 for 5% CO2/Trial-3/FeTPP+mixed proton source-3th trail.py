import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+34-0-6-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+4-8-0-0-0-20-0-38.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)




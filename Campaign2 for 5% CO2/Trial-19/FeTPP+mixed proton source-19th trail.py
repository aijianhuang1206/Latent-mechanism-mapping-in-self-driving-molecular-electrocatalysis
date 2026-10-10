import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+10-2-0-0-0-20-0-38.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+16-8-0-0-0-20-0-26.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+16-0-24-0-20-0-9-1.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)
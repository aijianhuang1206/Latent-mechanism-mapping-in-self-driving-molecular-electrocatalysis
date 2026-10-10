import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+18-2-20-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+24-12-2-0-20-0-10-2.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("4-FeTPP+26-12-2-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("5-FeTPP+12-28-0-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("6-FeTPP+18-22-0-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)
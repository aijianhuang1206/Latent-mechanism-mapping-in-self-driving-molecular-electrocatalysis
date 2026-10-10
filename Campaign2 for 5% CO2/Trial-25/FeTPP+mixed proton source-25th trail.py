import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+10-6-24-0-19-1-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+10-4-24-0-19-1-10-2.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+10-4-26-0-19-1-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)


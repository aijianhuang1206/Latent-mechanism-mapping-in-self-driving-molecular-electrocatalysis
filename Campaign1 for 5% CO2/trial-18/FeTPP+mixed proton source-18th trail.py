import subprocess

def run_script(script_name, num_runs):
    for _ in range(num_runs):
        subprocess.run(["C:\python\python-code\CO2 Setup\Scripts\python", script_name])

run_script("FeTPP+single proton source-part1.py", 1)
run_script("1-FeTPP+32-0-6-0-20-0-10-2.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("2-FeTPP+2-8-30-0-20-0-10-0.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)

run_script("FeTPP+single proton source-part1.py", 1)
run_script("3-FeTPP+0-8-30-0-20-0-10-2.py", 1)
run_script("FeTPP+single proton source-part2.py", 1)








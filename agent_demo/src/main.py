import sys

if __name__ == "__main__":
    print('''
    The Semantic Governance Agent has been upgraded to a manual-trigger pipeline execution model!
    
    Instead of running a simulated 30-day loop, you now trigger the pipeline and agent day-by-day to watch the learning behavior in action:
    
    1. Run Day 1 Pipeline (Generates data & DB schemas natively):
       python3 src/pipeline.py 1
       
    2. Run Day 1 Agent (Investigates risks & raises Pull Request):
       python3 src/agent.py 1
       
    3. Run Day 2 Pipeline (Agent's PR is "merged", improving specific DQ scores):
       python3 src/pipeline.py 2
       
    4. Run Day 2 Agent (Agent identifies score improvement & emits learning outcome):
       python3 src/agent.py 2
    ''')
    sys.exit(0)

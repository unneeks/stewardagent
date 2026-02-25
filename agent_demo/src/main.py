from src.db import init_db
from src.mock_data import populate_mock_data
from src.agent_loop import run_simulation
import os

def main():
    print("=" * 50)
    print("Initializing Semantic Governance Agent Demo...")
    print("=" * 50)
    
    # Ensure fresh state
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "governance.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("\n[+] Setting up Database Schema...")
    init_db()
    
    print("\n[+] Populating Mock Data (Terms, Rules, Lineage, Models)...")
    populate_mock_data()
    
    print("\n[+] Starting 30-Day Agent Simulation Loop...")
    print("=" * 50)
    run_simulation(30)
    
    print("=" * 50)
    print("Simulation Complete. Events written to EVENT_LOG table.")

if __name__ == "__main__":
    main()

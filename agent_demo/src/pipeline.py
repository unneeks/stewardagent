import random
import sqlite3
import os
from datetime import datetime, timedelta
from src.db import get_connection, init_db
from src.mock_data import populate_mock_data

def generate_bronze_data(conn, day: int, date_str: str):
    """
    Simulates daily ingestion of raw application data.
    """
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ext_application_source (
            application_id TEXT,
            income_reported TEXT,
            requested_amount REAL,
            app_status TEXT,
            ingest_date TEXT
        )
    ''')
    
    # Generate 100 rows per day. Over time, we might inject data quality issues loosely based on the day to allow for improvement.
    rows = []
    
    # Check AGENT_MEMORY for manually 'merged' PRs via the UI to simulate the 'pipeline behavior' changing.
    cursor.execute("SELECT tde_id FROM AGENT_MEMORY WHERE status = 'merged'")
    merged_prs = [r['tde_id'] for r in cursor.fetchall()]
    
    # Base error rates
    income_null_rate = 0.15 
    amount_error_rate = 0.10
    status_error_rate = 0.05
    
    # If PRs were merged, reduce error rate heavily
    if 'TDE_001' in merged_prs or 'TDE_002' in merged_prs: # Income 
        income_null_rate = 0.01 
    if 'TDE_003' in merged_prs: # Amount
        amount_error_rate = 0.01
    if 'TDE_004' in merged_prs: # Status
        status_error_rate = 0.01

    for i in range(100):
        app_id = f"APP_{date_str}_{i:03d}"
        
        # Income (Bronze keeps it as string, might be null)
        income = str(random.randint(30000, 150000))
        if random.random() < income_null_rate:
            income = None
            
        # Amount
        amount = random.randint(100000, 500000)
        if random.random() < amount_error_rate:
            amount = -100 # Invalid amount
            
        # Status
        status = random.choice(['APPROVED', 'REJECTED', 'PENDING'])
        if random.random() < status_error_rate:
            status = 'UNKNOWN_STATE'
            
        rows.append((app_id, income, amount, status, date_str))
        
    cursor.executemany("INSERT INTO ext_application_source VALUES (?, ?, ?, ?, ?)", rows)
    
    # Add a reference table for the gold join if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reference_decisions (
            app_id TEXT,
            status TEXT
        )
    ''')
    # For simplicity, sync the reference table
    cursor.execute("DELETE FROM reference_decisions")
    ref_rows = [(r[0], r[3]) for r in rows]
    cursor.executemany("INSERT INTO reference_decisions VALUES (?, ?)", ref_rows)
    
    conn.commit()

def run_dbt_models(conn):
    """
    Executes the SQL content of the dbt models directly against the SQLite DB.
    """
    cursor = conn.cursor()
    
    # Read models from DB to execute in order: Bronze -> Silver -> Gold
    models = ['bronze_raw_loans', 'silver_stg_loans', 'gold_fct_approvals']
    
    for model in models:
        cursor.execute("SELECT sql_text FROM DBT_SQL_MODELS WHERE model_name = ?", (model,))
        row = cursor.fetchone()
        if not row:
            continue
            
        sql = row['sql_text']
        # We need to wrap it into a CREATE TABLE AS statement to simulate dbt materialization
        cursor.execute(f"DROP TABLE IF EXISTS {model}")
        cursor.execute(f"CREATE TABLE {model} AS {sql}")
        
    conn.commit()

def assess_actual_dq_scores(conn, date_str: str):
    """
    Compute real DQ scores by executing aggregate queries on the materialized tables.
    """
    cursor = conn.cursor()
    scores = []
    
    # RULES:
    # R_001 (TDE_001 / bronze_raw_loans.income_str): must be positive and explicitly numeric.
    # R_002 (TDE_002 / silver_stg_loans.verified_income): Applicant income must be positive and implicitly numeric
    # R_003 (TDE_003 / gold_fct_approvals.loan_amount): strictly numeric within approved range (> 0)
    # R_004 (TDE_004 / gold_fct_approvals.final_status): allowed values (APPROVED, REJECTED, PENDING)
    
    # Bronze Income Score
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN income_str IS NOT NULL AND income_str != '0' THEN 1 ELSE 0 END) as valid FROM bronze_raw_loans")
    row = cursor.fetchone()
    score_tde_1 = row['valid'] / row['total'] if row['total'] > 0 else 1.0
    scores.append((date_str, 'TDE_001', score_tde_1))
    
    # Silver Income Score
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN verified_income > 0 THEN 1 ELSE 0 END) as valid FROM silver_stg_loans")
    row = cursor.fetchone()
    score_tde_2 = row['valid'] / row['total'] if row['total'] > 0 else 1.0
    scores.append((date_str, 'TDE_002', score_tde_2))
    
    # Gold Amount Score
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN loan_amount > 0 THEN 1 ELSE 0 END) as valid FROM gold_fct_approvals")
    row = cursor.fetchone()
    score_tde_3 = row['valid'] / row['total'] if row['total'] > 0 else 1.0
    scores.append((date_str, 'TDE_003', score_tde_3))
    
    # Gold Status Score
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN final_status IN ('APPROVED', 'REJECTED', 'PENDING') THEN 1 ELSE 0 END) as valid FROM gold_fct_approvals")
    row = cursor.fetchone()
    score_tde_4 = row['valid'] / row['total'] if row['total'] > 0 else 1.0
    scores.append((date_str, 'TDE_004', score_tde_4))

    # Insert
    for s in scores:
        cursor.execute('''
            INSERT OR REPLACE INTO DQ_SCORES (date, tde_id, score) 
            VALUES (?, ?, ?)
        ''', s)
        
    conn.commit()
    return scores

def run_pipeline(day: int):
    base_date = datetime(2026, 1, 1)
    current_date = base_date + timedelta(days=day)
    date_str = current_date.strftime("%Y-%m-%d")
    
    print(f"\n[{date_str}] --- PIPELINE STARTING ---")
    conn = get_connection()
    
    # Generate data
    generate_bronze_data(conn, day, date_str)
    print(f"[{date_str}] Bronze data ingested.")
    
    # Run dbt logic natively
    run_dbt_models(conn)
    print(f"[{date_str}] DBT models executed natively.")
    
    # Compute real scores
    scores = assess_actual_dq_scores(conn, date_str)
    print(f"[{date_str}] Computed Actual DQ Scores:")
    for s in scores:
         print(f"   {s[1]}: {s[2]:.3f}")
    
    conn.close()
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python src/pipeline.py <day_number>")
        sys.exit(1)
        
    day_num = int(sys.argv[1])
    # Setup if this is Day 1
    if day_num == 1:
        init_db()
        populate_mock_data()
        
    run_pipeline(day_num)

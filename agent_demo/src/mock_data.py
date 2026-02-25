from src.db import get_connection, init_db
import os

def populate_mock_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Business Terms
    terms = [
        ('BT_001', 'Applicant Income', 0.95),
        ('BT_002', 'Requested Loan Amount', 0.98),
        ('BT_003', 'Application Status', 0.9)
    ]
    cursor.executemany("INSERT OR REPLACE INTO BUSINESS_TERMS VALUES (?, ?, ?)", terms)
    
    # 2. Rules
    rules = [
        ('R_001', 'BT_001', 'Applicant income must be positive and explicitly numeric', 0.99),
        ('R_002', 'BT_002', 'Loan amount strictly numeric within approved range', 0.995),
        ('R_003', 'BT_003', 'Application status must be one of allowed values and not null', 1.0)
    ]
    cursor.executemany("INSERT OR REPLACE INTO RULES VALUES (?, ?, ?, ?)", rules)
    
    # 3. TDEs (mapped to medallion layers)
    tdes = [
        ('TDE_001', 'raw_loan_applications.income_str', 'BT_001'),       # Bronze
        ('TDE_002', 'stg_loan_applications.verified_income', 'BT_001'),    # Silver
        ('TDE_003', 'fct_loan_approvals.loan_amount', 'BT_002'),         # Gold
        ('TDE_004', 'fct_loan_approvals.final_status', 'BT_003')            # Gold
    ]
    cursor.executemany("INSERT OR REPLACE INTO TDE VALUES (?, ?, ?)", tdes)
    
    # 4. DBT Column Mappings
    mappings = [
        ('bronze_raw_loans', 'income_str', 'TDE_001'),
        ('silver_stg_loans', 'verified_income', 'TDE_002'),
        ('gold_fct_approvals', 'loan_amount', 'TDE_003'),
        ('gold_fct_approvals', 'final_status', 'TDE_004')
    ]
    cursor.executemany("INSERT OR REPLACE INTO DBT_COLUMN_MAPPING VALUES (?, ?, ?)", mappings)
    
    # 5. Load SQL Models (and save files)
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    sql_models = {
        'bronze_raw_loans': "SELECT application_id, coalesce(income_reported, '0') as income_str FROM ext_application_source", # Risky coalesce
        'silver_stg_loans': "SELECT id, cast(income_str as decimal(18,2)) as verified_income FROM bronze_raw_loans", # Risky cast
        'gold_fct_approvals': "SELECT a.id, a.loan_amount, b.status as final_status FROM silver_stg_loans a LEFT JOIN reference_decisions b ON a.id = b.app_id" # Risky join
    }
    
    for model_name, sql_text in sql_models.items():
        # Save to DB
        cursor.execute("INSERT OR REPLACE INTO DBT_SQL_MODELS VALUES (?, ?)", (model_name, sql_text))
        # Save to File
        with open(os.path.join(models_dir, f"{model_name}.sql"), "w") as f:
            f.write(sql_text)
            
    conn.commit()
    conn.close()
    print("Mock data populated with Medallion Architecture (Home Loan Journey).")

if __name__ == "__main__":
    init_db()
    populate_mock_data()

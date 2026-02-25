import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "governance.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS BUSINESS_TERMS(
            term_id TEXT PRIMARY KEY,
            name TEXT,
            criticality REAL
        );
        
        CREATE TABLE IF NOT EXISTS RULES(
            rule_id TEXT PRIMARY KEY,
            business_term_id TEXT,
            description TEXT,
            threshold REAL,
            FOREIGN KEY (business_term_id) REFERENCES BUSINESS_TERMS(term_id)
        );
        
        CREATE TABLE IF NOT EXISTS TDE(
            tde_id TEXT PRIMARY KEY,
            name TEXT,
            business_term_id TEXT,
            FOREIGN KEY (business_term_id) REFERENCES BUSINESS_TERMS(term_id)
        );
        
        CREATE TABLE IF NOT EXISTS DQ_SCORES(
            date TEXT,
            tde_id TEXT,
            score REAL,
            FOREIGN KEY (tde_id) REFERENCES TDE(tde_id),
            PRIMARY KEY (date, tde_id)
        );
        
        CREATE TABLE IF NOT EXISTS DBT_COLUMN_MAPPING(
            model_name TEXT,
            column_name TEXT,
            tde_id TEXT,
            FOREIGN KEY (tde_id) REFERENCES TDE(tde_id),
            PRIMARY KEY (model_name, column_name)
        );
        
        CREATE TABLE IF NOT EXISTS DBT_SQL_MODELS(
            model_name TEXT PRIMARY KEY,
            sql_text TEXT
        );
        
        CREATE TABLE IF NOT EXISTS EVENT_LOG(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            entity_type TEXT,
            entity_id TEXT,
            entity_name TEXT,
            context TEXT,        -- JSON string
            metrics TEXT,        -- JSON string
            explanation TEXT
        );
        
        CREATE TABLE IF NOT EXISTS AGENT_MEMORY(
            pr_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tde_id TEXT,
            model_name TEXT,
            suggestion TEXT,
            status TEXT,         -- 'open', 'merged'
            FOREIGN KEY (tde_id) REFERENCES TDE(tde_id)
        );
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")

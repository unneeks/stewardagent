import random
import sqlite3
import json
from datetime import datetime, timedelta
from src.db import get_connection
from src.events import emit_event
from src.llm_scanner import LLMScanner
from src.policy_checker import PolicyChecker

class GovernanceAgent:
    def __init__(self, date_str: str):
        self.llm_scanner = LLMScanner()
        self.policy_checker = PolicyChecker()
        self.date_str = date_str
        
    def review_persistent_memory(self):
        """Checks if there are 'merged' PRs from previous runs and evaluates if they improved the score today."""
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM AGENT_MEMORY WHERE status = 'merged'")
        merged_prs = cursor.fetchall()
        
        if not merged_prs:
            return

        # Calculate yesterday's date string
        curr_date = datetime.strptime(self.date_str, "%Y-%m-%d")
        yesterday_str = (curr_date - timedelta(days=1)).strftime("%Y-%m-%d")
        
        for pr in merged_prs:
            # Check today's score
            cursor.execute('''
                SELECT score FROM DQ_SCORES 
                WHERE date = ? AND tde_id = ?
            ''', (self.date_str, pr['tde_id']))
            today_row = cursor.fetchone()
            
            # Check yesterday's score
            cursor.execute('''
                SELECT score FROM DQ_SCORES 
                WHERE date = ? AND tde_id = ?
            ''', (yesterday_str, pr['tde_id']))
            yesterday_row = cursor.fetchone()
            
            if today_row and yesterday_row and today_row['score'] > yesterday_row['score']:
                # Success! The PR improved the score.
                emit_event(
                    "outcome_measured", "tde", pr['tde_id'], pr['tde_id'],
                    {"score_after_fix": today_row['score'], "pr_id": pr['pr_id']},
                    {"score": today_row['score']},
                    f"Measured positive outcome on {pr['tde_id']} post-intervention (Score improved from {yesterday_row['score']:.2f} to {today_row['score']:.2f})."
                )
                emit_event(
                    "learning_updated", "agent_memory", "core", "heuristics",
                    {"reinforced_tde": pr['tde_id'], "suggestion": pr['suggestion']},
                    {},
                    f"Updated learning heuristics: {pr['suggestion']} successfully resolved DQ issues for {pr['tde_id']}."
                )
                
            # Remove from memory regardless, so we don't keep evaluating the same PR daily
            cursor.execute("DELETE FROM AGENT_MEMORY WHERE pr_id = ?", (pr['pr_id'],))
                
        conn.commit()
        conn.close()

    def raise_pull_request(self, tde_id: str, model_name: str, suggestion: str):
        """Persists the agent's suggestion into memory as an Open PR."""
        conn = get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        cursor.execute('''
            INSERT INTO AGENT_MEMORY (timestamp, tde_id, model_name, suggestion, status)
            VALUES (?, ?, ?, ?, 'open')
        ''', (timestamp, tde_id, model_name, suggestion))
        pr_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return pr_id

    def run_daily_agent(self):
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cursor = conn.cursor()
        
        print(f"\n[{self.date_str}] --- AGENT EXECUTION STARTING ---")
        
        # 0. Check memory for outcomes of past merged PRs
        self.review_persistent_memory()
        
        # 1. Detect breached rules
        cursor.execute('''
            SELECT r.rule_id, r.threshold, r.description, d.score, t.tde_id, t.name as tde_name, b.term_id, b.criticality
            FROM RULES r
            JOIN BUSINESS_TERMS b ON r.business_term_id = b.term_id
            JOIN TDE t ON t.business_term_id = b.term_id
            JOIN DQ_SCORES d ON d.tde_id = t.tde_id
            WHERE d.date = ?
        ''', (self.date_str,))
        
        breaches = []
        for r in cursor.fetchall():
            if r['score'] < r['threshold']:
                breaches.append(r)
                emit_event(
                    "rule_breached", "rule", r['rule_id'], r['description'],
                    {"score": r['score'], "threshold": r['threshold']},
                    {"delta": r['threshold'] - r['score']},
                    f"DQ rule breached on {r['tde_name']} (Score: {r['score']:.3f} < {r['threshold']})"
                )

        if not breaches:
            print("No breaches today.")
            return

        # 2. Assess risk
        risks = []
        for b in breaches:
            delta = b['threshold'] - b['score']
            trend_decline_factor = 1.1 
            risk_score = b['criticality'] * delta * trend_decline_factor
            
            risks.append({**b, 'risk_score': risk_score})
            
            emit_event(
                "risk_assessed", "business_term", b['term_id'], b['term_id'],
                {"criticality": b['criticality'], "delta": delta},
                {"risk_score": risk_score},
                f"Assessed risk score of {risk_score:.3f} for term {b['term_id']}"
            )
            
        # 3. Select focus
        risks.sort(key=lambda x: x['risk_score'], reverse=True)
        focus = risks[0]
        
        emit_event(
            "focus_selected", "business_term", focus['term_id'], focus['term_id'],
            {"highest_risk_score": focus['risk_score'], "term": focus['term_id']},
            {},
            f"Agent selected {focus['term_id']} as primary investigation focus based on risk."
        )
        
        # 4. Start investigation
        emit_event(
            "investigation_started", "tde", focus['tde_id'], focus['tde_name'],
            {"rule_id": focus['rule_id']},
            {},
            f"Started investigation targeting TDE {focus['tde_name']}"
        )
        
        # 5. Trace lineage
        cursor.execute('''
            SELECT m.model_name, m.column_name
            FROM DBT_COLUMN_MAPPING m
            WHERE m.tde_id = ?
        ''', (focus['tde_id'],))
        
        lineage = cursor.fetchone()
        if not lineage:
            print("No lineage found, stopping investigation.")
            return
            
        # Read actual dbt code from disk
        import os
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", f"{lineage['model_name']}.sql")
        try:
            with open(model_path, 'r') as f:
                sql_text = f.read()
        except FileNotFoundError:
            print(f"Could not find actual dbt code at {model_path}")
            return
            
        emit_event(
            "lineage_traced", "dbt_model", lineage['model_name'], lineage['model_name'],
            {"column": lineage['column_name']},
            {},
            f"Traced lineage to DBT model {lineage['model_name']}, column {lineage['column_name']}"
        )
        
        # 6. LLM SQL Analysis
        inferred_type = self.llm_scanner.infer_semantic_type(lineage['column_name'], focus['description'])
        sql_risks = self.llm_scanner.analyze_sql_for_risks(sql_text)
        
        emit_event(
            "sql_analysis_completed", "dbt_model", lineage['model_name'], lineage['model_name'],
            {"inferred_semantic_type": inferred_type, "detected_risks": sql_risks},
            {"risk_count": len(sql_risks)},
            f"LLM scanned SQL: interpreted as '{inferred_type}' semantic type. Found risks: {sql_risks}"
        )
        
        # 7. Policy Check
        gaps = self.policy_checker.check_policy_gaps(inferred_type, focus['description'])
        if gaps:
            emit_event(
                "policy_gap_detected", "rule", focus['rule_id'], focus['description'],
                {"semantic_type": inferred_type, "gaps": gaps},
                {"gap_count": len(gaps)},
                f"Detected policy gaps for '{inferred_type}': {gaps}"
            )
            
        # 8. Create recommendation & Raise PR
        if gaps or sql_risks:
            suggestion = "Add rigorous validation upstream."
            fixed_sql = sql_text
            
            if "CAST detected" in str(sql_risks):
                suggestion = f"Perform validation before CAST transformation in model {lineage['model_name']}."
                fixed_sql = fixed_sql.replace("cast(income_str as decimal(18,2))", "income_str")
                if fixed_sql == sql_text:
                    fixed_sql += " -- TODO: Remove unsafe CAST"
                    
            if "COALESCE detected" in str(sql_risks):
                suggestion = f"Address root cause of nulls instead of silencing with COALESCE in {lineage['model_name']}."
                fixed_sql = fixed_sql.replace("coalesce(income_reported, '0')", "income_reported")
                if fixed_sql == sql_text:
                    fixed_sql += " -- TODO: Remove unsafe COALESCE"
                    
            if "JOIN detected" in str(sql_risks):
                suggestion = f"Enforce distinct validation on `{lineage['column_name']}` post-join to guarantee rule isn't broken by duplicates."
                fixed_sql = fixed_sql.replace("LEFT JOIN reference_decisions b", "LEFT JOIN (SELECT app_id, status FROM reference_decisions GROUP BY app_id, status) b")
                if fixed_sql == sql_text:
                    fixed_sql += " -- TODO: Deduplicate JOIN"
                
            import difflib
            diff_lines = list(difflib.unified_diff(
                [sql_text + '\\n'],
                [fixed_sql + '\\n'],
                fromfile=f"a/models/{lineage['model_name']}.sql",
                tofile=f"b/models/{lineage['model_name']}.sql",
                n=3
            ))
            mock_diff = "".join(diff_lines)
                
            # Log action to persistent memory first to get ID
            pr_id = self.raise_pull_request(focus['tde_id'], lineage['model_name'], suggestion)
            print(f"[{self.date_str}] Raised Pull Request against {lineage['model_name']} (PR ID: {pr_id})")
            
            emit_event(
                "recommendation_created", "tde", focus['tde_id'], focus['tde_name'],
                {"suggestion": suggestion, "diff": mock_diff, "pr_id": pr_id},
                {},
                f"Generated pull request: {suggestion}"
            )

        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python src/agent.py <day_number>")
        sys.exit(1)
        
    day_num = int(sys.argv[1])
    base_date = datetime(2026, 1, 1)
    current_date = base_date + timedelta(days=day_num)
    date_str = current_date.strftime("%Y-%m-%d")
    
    agent = GovernanceAgent(date_str)
    agent.run_daily_agent()

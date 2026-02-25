import random
import sqlite3
from datetime import datetime, timedelta
from src.db import get_connection
from src.events import emit_event
from src.llm_scanner import LLMScanner
from src.policy_checker import PolicyChecker

class GovernanceAgent:
    def __init__(self):
        self.llm_scanner = LLMScanner()
        self.policy_checker = PolicyChecker()
        
        # Memory state
        self.active_investigations = {}
        self.recommendations_made = {}
        self.learning_weights = {
            'email': 1.0,
            'amount': 1.0,
            'id': 1.0
        }
        
    def generate_daily_scores(self, current_date_str: str, day: int):
        conn = get_connection()
        cursor = conn.cursor()
        
        # If we made a recommendation for a TDE, the score should jump up.
        cursor.execute("SELECT tde_id, name FROM TDE")
        tdes = cursor.fetchall()
        
        for tde in tdes:
            base_score = 0.85
            # Add improvement if a fix was applied
            recent_fix = self.recommendations_made.get(tde['tde_id'], None)
            
            if recent_fix and day > recent_fix['day']:
                # Score improvement
                score = min(1.0, base_score + 0.12 + random.uniform(0.01, 0.05))
            else:
                # Fluctuate naturally
                score = max(0.0, min(1.0, base_score + random.uniform(-0.1, 0.1)))
                
            cursor.execute('''
                INSERT OR REPLACE INTO DQ_SCORES (date, tde_id, score) 
                VALUES (?, ?, ?)
            ''', (current_date_str, tde['tde_id'], score))
            
        conn.commit()
        conn.close()

    def run_daily_cycle(self, day: int, date_str: str):
        conn = get_connection()
        conn.row_factory = sqlite3.Row if 'sqlite3' in globals() else None
        
        # Need to fix up imports inside file, let's just make it a flat dict approach for rows
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cursor = conn.cursor()
        
        print(f"\n--- Day {day}: {date_str} ---")
        
        # 1. Detect breached rules
        cursor.execute('''
            SELECT r.rule_id, r.threshold, r.description, d.score, t.tde_id, t.name as tde_name, b.term_id, b.criticality
            FROM RULES r
            JOIN BUSINESS_TERMS b ON r.business_term_id = b.term_id
            JOIN TDE t ON t.business_term_id = b.term_id
            JOIN DQ_SCORES d ON d.tde_id = t.tde_id
            WHERE d.date = ?
        ''', (date_str,))
        
        daily_results = cursor.fetchall()
        breaches = []
        for r in daily_results:
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
            trend_decline_factor = 1.1 # Simplification
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
            SELECT m.model_name, m.column_name, sql.sql_text
            FROM DBT_COLUMN_MAPPING m
            JOIN DBT_SQL_MODELS sql ON m.model_name = sql.model_name
            WHERE m.tde_id = ?
        ''', (focus['tde_id'],))
        
        lineage = cursor.fetchone()
        if not lineage:
            print("No lineage found, stopping investigation.")
            return
            
        emit_event(
            "lineage_traced", "dbt_model", lineage['model_name'], lineage['model_name'],
            {"column": lineage['column_name']},
            {},
            f"Traced lineage to DBT model {lineage['model_name']}, column {lineage['column_name']}"
        )
        
        # 6. LLM SQL Analysis
        inferred_type = self.llm_scanner.infer_semantic_type(lineage['column_name'], focus['description'])
        sql_risks = self.llm_scanner.analyze_sql_for_risks(lineage['sql_text'])
        
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
            
        # 8. Create recommendation
        # If we have gaps or risks, recommend a fix
        if gaps or sql_risks:
            suggestion = "Add rigorous validation upstream."
            if "CAST detected" in str(sql_risks):
                suggestion = "Perform validation before CAST transformation."
                
            emit_event(
                "recommendation_created", "tde", focus['tde_id'], focus['tde_name'],
                {"suggestion": suggestion},
                {},
                f"Generated recommendation: {suggestion}"
            )
            # Log action to improve scores
            self.recommendations_made[focus['tde_id']] = {'day': day, 'suggestion': suggestion}
        
        # 9 & 10. Outcome measured & Learning updated
        # Look back at previous recommendations and measure improvement
        cursor.execute("SELECT tde_id, score FROM DQ_SCORES WHERE date = ?", (date_str,))
        today_scores = {r['tde_id']: r['score'] for r in cursor.fetchall()}
        
        for tde_id, fix_info in list(self.recommendations_made.items()):
            if day > fix_info['day']:
                # It's a subsequent day, measure outcome
                # Let's see if the score is actually better now.
                current_score = today_scores.get(tde_id, 0)
                if current_score >= focus['threshold'] or current_score > 0.9:
                    emit_event(
                        "outcome_measured", "tde", tde_id, tde_id,
                        {"score_after_fix": current_score, "fix_day": fix_info['day']},
                        {"score": current_score},
                        f"Measured positive outcome on {tde_id} post-intervention (Score: {current_score:.2f})."
                    )
                    emit_event(
                        "learning_updated", "agent_memory", "core", "heuristics",
                        {"reinforced_tde": tde_id},
                        {},
                        "Updated learning heuristics: interventions on this pattern succeed."
                    )
                    # Remove so we don't spam
                    del self.recommendations_made[tde_id]

        conn.commit()
        conn.close()

def run_simulation(days=30):
    agent = GovernanceAgent()
    base_date = datetime.now()
    
    for i in range(1, days + 1):
        current_date = base_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        agent.generate_daily_scores(date_str, day=i)
        agent.run_daily_cycle(day=i, date_str=date_str)

if __name__ == "__main__":
    from datetime import datetime, timedelta
    run_simulation(30)

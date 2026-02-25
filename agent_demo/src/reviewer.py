import json
import sqlite3
import os
from datetime import datetime
from src.db import get_connection

class CodeReviewer:
    def __init__(self):
        self.conn = get_connection()
        self.conn.row_factory = sqlite3.Row

    def review_changeset(self, pr_title: str, changeset_type: str, changed_entity: str, diff_text: str):
        print(f"\n--- STARTING PR REVIEW: {pr_title} ---")
        
        impacted_paths = []
        
        # 1. Trace Lineage
        if changeset_type == "policy":
            # Policy Rule changed. Trace Rule -> Term -> TDE -> Model
            print(f"Tracing downstream impact for modified policy on '{changed_entity}'...")
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT m.model_name, m.column_name, t.tde_id, b.name as term_name
                FROM BUSINESS_TERMS b
                JOIN TDE t ON t.business_term_id = b.term_id
                JOIN DBT_COLUMN_MAPPING m ON m.tde_id = t.tde_id
                WHERE b.term_id = ? OR b.name = ?
            ''', (changed_entity, changed_entity))
            
            for row in cursor.fetchall():
                impacted_paths.append({
                    "model": row["model_name"],
                    "column": row["column_name"],
                    "tde": row["tde_id"],
                    "term": row["term_name"]
                })
                
        elif changeset_type == "code":
            # DBT Model changed. Trace Model -> TDE -> Term -> Policy Rule
            print(f"Tracing upstream policy impact for modified DBT model '{changed_entity}'...")
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT m.column_name, t.tde_id, b.name as term_name, r.description as rule
                FROM DBT_COLUMN_MAPPING m
                JOIN TDE t ON m.tde_id = t.tde_id
                JOIN BUSINESS_TERMS b ON t.business_term_id = b.term_id
                JOIN RULES r ON r.business_term_id = b.term_id
                WHERE m.model_name = ?
            ''', (changed_entity,))
            
            for row in cursor.fetchall():
                impacted_paths.append({
                    "model": changed_entity,
                    "column": row["column_name"],
                    "tde": row["tde_id"],
                    "term": row["term_name"],
                    "rule": row["rule"]
                })
        
        # 2. Mock LLM Analysis
        print("Analyzing enforcement opportunities using LLM...")
        llm_reasoning = self._mock_llm_analyze(changeset_type, diff_text, impacted_paths)
        
        # 3. Store Enforcement Opportunity in Memory
        print("Saving enforcement opportunities to Persistent AGENT_MEMORY...")
        for rec in llm_reasoning["recommendations"]:
            self._save_to_memory(rec["tde_id"], rec["model"], rec["suggestion"])
            
        # 4. Generate GitHub-style PR Comment (Markdown)
        self._generate_markdown_report(pr_title, changeset_type, changed_entity, diff_text, impacted_paths, llm_reasoning)
        
        print(f"--- PR REVIEW COMPLETE ---")
        return llm_reasoning
        
    def _mock_llm_analyze(self, c_type, diff, paths):
        # Simulated LLM logic interpreting the diff against the lineage paths
        recs = []
        observations = []
        
        if c_type == "code":
            if "LEFT JOIN" in diff.upper() or "JOIN" in diff.upper():
                observations.append("LLM detected a new JOIN introduced in the model. This risks fan-out multiplying rows.")
                for p in paths:
                    recs.append({
                        "tde_id": p["tde"],
                        "model": p["model"],
                        "suggestion": f"Enforce distinct validation on `{p['column']}` post-join to guarantee '{p['rule']}' rule isn't broken by duplicates."
                    })
            if "COALESCE" in diff.upper():
                observations.append("LLM detected COALESCE being used to mask NULLs.")
                for p in paths:
                     recs.append({
                        "tde_id": p["tde"],
                        "model": p["model"],
                        "suggestion": f"Determine root cause of nulls in upstream model instead of relying on COALESCE for `{p['column']}`."
                    })
                    
        elif c_type == "policy":
             observations.append("LLM detected a policy threshold tightening.")
             for p in paths:
                 recs.append({
                     "tde_id": p["tde"],
                     "model": p["model"],
                     "suggestion": f"Add stricter dbt tests on `{p['model']}.{p['column']}` to enforce the new strict threshold for '{p['term']}'."
                 })
                 
        if not recs:
            observations.append("Looks good. No critical policy gaps introduced.")
            
        return {"observations": observations, "recommendations": recs}

    def _save_to_memory(self, tde_id, model, suggestion):
       cursor = self.conn.cursor()
       timestamp = datetime.utcnow().isoformat()
       cursor.execute('''
           INSERT INTO AGENT_MEMORY (timestamp, tde_id, model_name, suggestion, status)
           VALUES (?, ?, ?, ?, 'open')
       ''', (timestamp, tde_id, model, suggestion))
       self.conn.commit()
       
    def _generate_markdown_report(self, title, c_type, entity, diff, paths, llm_reasoning):
        report_path = "pr_review_report.md"
        with open(report_path, "w") as f:
            f.write(f"## 🤖 Steward Agent Code Review\n\n")
            f.write(f"**PR:** {title}\n")
            f.write(f"**Type:** {c_type.capitalize()} Update on `{entity}`\n\n")
            
            f.write("### 🔍 Lineage Impact Analysis\n")
            if not paths:
                f.write("No direct lineage impact found to regulated Business Terms.\n\n")
            else:
                f.write("I traced this change through our data semantic graph and found the following impacted paths:\n")
                for p in paths:
                    if c_type == "code":
                         f.write(f"- DB Model `{p['model']}.{p['column']}` -> TDE `{p['tde']}` -> Business Term **{p['term']}** (governed by rule: _{p['rule']}_)\n")
                    else:
                         f.write(f"- Policy **{p['term']}** -> TDE `{p['tde']}` -> downstream DB Model `{p['model']}.{p['column']}`\n")
                f.write("\n")
                
            f.write("### 🧠 LLM Reasoning & Observations\n")
            for obs in llm_reasoning["observations"]:
                f.write(f"- {obs}\n")
            f.write("\n")
            
            f.write("### 💡 Enforcement Opportunities\n")
            if llm_reasoning["recommendations"]:
                f.write("I have noted the following recommendations into `AGENT_MEMORY` so that they can be tracked during our daily governance pipeline runs:\n")
                for r in llm_reasoning["recommendations"]:
                    f.write(f"- [Tracked] For `{r['model']}`: {r['suggestion']}\n")
            else:
                f.write("No specific enforcement actions required.\n")
                
        print(f"Generated PR Comment Markdown Document: {report_path}")

# --- Example usages ---
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/reviewer.py <demo1|demo2>")
        sys.exit(1)
        
    action = sys.argv[1]
    reviewer = CodeReviewer()
    
    if action == "demo1":
        # Simulate an engineer adding a risky JOIN to a DBT Model
        reviewer.review_changeset(
            pr_title="Feat: Add external enrichment join to Gold layer",
            changeset_type="code",
            changed_entity="gold_fct_approvals",
            diff_text="+ LEFT JOIN external_credit_bureau c ON a.ssn = c.ssn"
        )
    elif action == "demo2":
        # Simulate a Data Steward changing a policy definition
        reviewer.review_changeset(
            pr_title="Policy: Tighten validation on Applicant Income",
            changeset_type="policy",
            changed_entity="BT_001",
            diff_text="threshold: changed from 0.95 to 0.99"
        )

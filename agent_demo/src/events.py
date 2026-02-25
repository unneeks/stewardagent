import json
from datetime import datetime
from src.db import get_connection

ALLOWED_EVENTS = {
    "rule_breached",
    "risk_assessed",
    "focus_selected",
    "investigation_started",
    "lineage_traced",
    "sql_analysis_completed",
    "policy_gap_detected",
    "recommendation_created",
    "outcome_measured",
    "learning_updated"
}

def emit_event(
    event_type: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    context_dict: dict,
    metrics_dict: dict,
    explanation_text: str
):
    if event_type not in ALLOWED_EVENTS:
        raise ValueError(f"Event type '{event_type}' is not allowed.")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().isoformat()
    
    cursor.execute('''
        INSERT INTO EVENT_LOG (
            timestamp, event_type, entity_type, entity_id, entity_name,
            context, metrics, explanation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        event_type,
        entity_type,
        entity_id,
        entity_name,
        json.dumps(context_dict),
        json.dumps(metrics_dict),
        explanation_text
    ))
    
    conn.commit()
    conn.close()
    
    print(f"[{timestamp}] EVENT: {event_type} | {entity_type}: {entity_name} | {explanation_text}")

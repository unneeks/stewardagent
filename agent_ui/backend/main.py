from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json

app = FastAPI(title="Cognition Playback API")

# Setup CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agent_demo", "data", "governance.db")

def get_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found. Please run the simulation first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/events")
def get_events():
    """Returns all events ordered by timestamp."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM EVENT_LOG ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        events.append({
            "event_id": row["event_id"],
            "timestamp": row["timestamp"],
            "event_type": row["event_type"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "entity_name": row["entity_name"],
            "context": json.loads(row["context"]) if row["context"] else {},
            "metrics": json.loads(row["metrics"]) if row["metrics"] else {},
            "explanation": row["explanation"]
        })
    return events

@app.get("/investigations")
def get_investigations():
    """
    Groups events into investigation sessions.
    Chronological playback of events grouped into investigations.
    rule_breached → focus_selected → investigation_started → analysis → recommendation → outcome → learning
    """
    events = get_events()
    
    investigations = []
    current_investigation = None
    
    for event in events:
        evt_type = event["event_type"]
        
        # We start a cycle when a rule breaches and risk is assessed. Let's group by "daily cycle" or "focus"
        # The agent selects a focus, starts investigation.
        # However, the loop emits: rule_breached -> risk_assessed -> focus_selected -> investigation_started ...
        
        if evt_type == "focus_selected":
             if current_investigation:
                 investigations.append(current_investigation)
             current_investigation = {
                 "id": event["event_id"],
                 "focus_term": event["entity_id"],
                 "start_time": event["timestamp"],
                 "events": [event],
                 "recommendation": None,
                 "outcomes": []
             }
        elif current_investigation:
             current_investigation["events"].append(event)
             if evt_type == "recommendation_created":
                 current_investigation["recommendation"] = event
             elif evt_type == "outcome_measured":
                 current_investigation["outcomes"].append(event)
    
    if current_investigation:
        investigations.append(current_investigation)
        
    return investigations

@app.get("/latest_state")
def get_latest_state():
    """
    Latest status per business term.
    Aggregate latest events per business term.
    Color states derived from: rule_breached, risk_assessed, focus_selected, outcome_measured
    """
    events = get_events()
    
    # Track the state per business term
    term_states = {}
    
    for event in events:
        evt_type = event["event_type"]
        term_id = None
        
        # Figure out the related business term for the state
        if evt_type in ["risk_assessed", "focus_selected"]:
            term_id = event["entity_id"]
            if term_id not in term_states:
                term_states[term_id] = {"status": "stable", "last_update": event["timestamp"]}
                
            term_states[term_id]["last_update"] = event["timestamp"]
            
            if evt_type == "risk_assessed":
                risk_score = event["metrics"].get("risk_score", 0)
                delta = event["context"].get("delta", 0)
                if risk_score > 0.1:
                    term_states[term_id]["status"] = "breached"
                elif delta > 0:
                    term_states[term_id]["status"] = "declining"
                else:
                    term_states[term_id]["status"] = "stable"
                    
            elif evt_type == "focus_selected":
                term_states[term_id]["status"] = "under_investigation"
                
    return term_states

@app.get("/learning_summary")
def get_learning_summary():
    """Aggregated learning effectiveness based on outcomes."""
    events = get_events()
    
    improvements = []
    
    for event in events:
        if event["event_type"] == "outcome_measured":
            improvements.append({
                "tde": event["entity_id"],
                "score_after": event["metrics"].get("score", 0),
                "timestamp": event["timestamp"]
            })
            
    return {"improvements": improvements}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

const API_BASE = 'http://localhost:8000';

export async function fetchEvents() {
    const res = await fetch(`${API_BASE}/events`);
    if (!res.ok) throw new Error("Failed to fetch events");
    return res.json();
}

export async function fetchInvestigations() {
    const res = await fetch(`${API_BASE}/investigations`);
    if (!res.ok) throw new Error("Failed to fetch investigations");
    return res.json();
}

export async function fetchLatestState() {
    const res = await fetch(`${API_BASE}/latest_state`);
    if (!res.ok) throw new Error("Failed to fetch latest state");
    return res.json();
}

export async function fetchLearningSummary() {
    const res = await fetch(`${API_BASE}/learning_summary`);
    if (!res.ok) throw new Error("Failed to fetch learning summary");
    return res.json();
}

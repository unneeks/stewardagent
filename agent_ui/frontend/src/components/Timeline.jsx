import React from 'react';
import { Target, Clock, AlertTriangle } from 'lucide-react';

function Timeline({ investigations, selectedId, onSelect }) {
    if (!investigations || investigations.length === 0) {
        return <div className="timeline-container"><p style={{ color: 'var(--text-muted)' }}>No investigations yet.</p></div>;
    }

    return (
        <div className="timeline-container">
            {investigations.map((inv) => {
                const isActive = inv.id === selectedId;
                const startTime = new Date(inv.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                let riskScore = 0;
                let ruleBreached = "Unknown Rule";

                // Extract basic data for the card
                inv.events.forEach(e => {
                    if (e.event_type === 'risk_assessed' && e.metrics.risk_score) riskScore = e.metrics.risk_score;
                    if (e.event_type === 'rule_breached') ruleBreached = e.entity_name;
                });

                return (
                    <div
                        key={inv.id}
                        className={`investigation-card ${isActive ? 'active' : ''}`}
                        onClick={() => onSelect(inv)}
                    >
                        <div className="card-time">
                            <Clock size={12} /> {startTime} | Focus: {inv.focus_term}
                        </div>
                        <div className="card-title">
                            {ruleBreached}
                        </div>
                        <div className="card-stats">
                            <div className="stat-pill">
                                <AlertTriangle size={12} color="var(--accent-amber)" />
                                Risk: {riskScore.toFixed(3)}
                            </div>
                            <div className="stat-pill">
                                <Target size={12} color={inv.recommendation ? "var(--accent-green)" : "var(--text-muted)"} />
                                {inv.recommendation ? "Actioned" : "Scanning"}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default Timeline;

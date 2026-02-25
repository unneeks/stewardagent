import React from 'react';
import { Layers, Activity } from 'lucide-react';

function Heatmap({ states }) {
    const terms = Object.keys(states);

    if (terms.length === 0) {
        return <div style={{ color: 'var(--text-muted)' }}>Awaiting telemetry...</div>;
    }

    return (
        <div className="heatmap-grid">
            {terms.map(term => {
                const info = states[term];
                return (
                    <div key={term} className={`heatmap-item status-${info.status}`}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Layers size={16} color="var(--text-secondary)" />
                            <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{term}</span>
                        </div>
                        <div className="status-badge">
                            {info.status.replace('_', ' ')}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default Heatmap;

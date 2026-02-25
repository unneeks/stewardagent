import React from 'react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

function LineageGraph({ lineageEvent, focusTerm }) {
    if (!lineageEvent) return null;

    const tde = lineageEvent.entity_id;
    const modelName = lineageEvent.entity_name;
    const colName = lineageEvent.context?.column || "unknown_col";

    const nodes = [
        {
            id: 'term',
            type: 'default',
            position: { x: 250, y: 20 },
            data: { label: <div className="custom-node term">Term: {focusTerm}</div> },
            style: { border: 'none', background: 'transparent' }
        },
        {
            id: 'tde',
            type: 'default',
            position: { x: 250, y: 120 },
            data: { label: <div className="custom-node tde">TDE: {tde}</div> },
            style: { border: 'none', background: 'transparent' }
        },
        {
            id: 'model',
            type: 'default',
            position: { x: 250, y: 220 },
            data: { label: <div className="custom-node model">Model: {modelName}</div> },
            style: { border: 'none', background: 'transparent' }
        },
        {
            id: 'column',
            type: 'default',
            position: { x: 250, y: 320 },
            data: { label: <div className="custom-node column">Col: {colName}</div> },
            style: { border: 'none', background: 'transparent' }
        }
    ];

    const edges = [
        { id: 'e1-2', source: 'term', target: 'tde', animated: true, style: { stroke: 'var(--accent-purple)' } },
        { id: 'e2-3', source: 'tde', target: 'model', animated: true, style: { stroke: 'var(--accent-blue)' } },
        { id: 'e3-4', source: 'model', target: 'column', animated: true, style: { stroke: 'var(--accent-cyan)' } }
    ];

    return (
        <div style={{ width: '100%', height: '100%', minHeight: '350px' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                attributionPosition="bottom-left"
                proOptions={{ hideAttribution: true }}
            >
                <Background color="rgba(255,255,255,0.05)" gap={16} />
                <Controls showInteractive={false} />
            </ReactFlow>
        </div>
    );
}

export default LineageGraph;

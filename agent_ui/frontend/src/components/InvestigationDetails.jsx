import React, { useState, useEffect } from 'react';
import LineageGraph from './LineageGraph';
import { AlertCircle, FileSearch, ShieldAlert, Cpu } from 'lucide-react';
import { fetchConfig } from '../api';

function InvestigationDetails({ inv }) {

    const [repoUrl, setRepoUrl] = useState("https://github.com/unknown/repository");

    useEffect(() => {
        const getConfig = async () => {
            try {
                const config = await fetchConfig();
                setRepoUrl(config.github_repo_url);
            } catch (e) {
                console.error("Failed to load repo config", e);
            }
        };
        getConfig();
    }, []);

    let problem = null;
    let reasoning = { lineage: null, analysis: null, gaps: null };
    let decision = null;

    inv.events.forEach(e => {
        if (e.event_type === 'rule_breached') problem = e;
        if (e.event_type === 'lineage_traced') reasoning.lineage = e;
        if (e.event_type === 'sql_analysis_completed') reasoning.analysis = e;
        if (e.event_type === 'policy_gap_detected') reasoning.gaps = e;
        if (e.event_type === 'recommendation_created') decision = e;
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflow: 'hidden' }}>

            {/* Problem Area */}
            {problem && (
                <div className="detail-section">
                    <div className="detail-section-title" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <AlertCircle size={14} color="var(--accent-red)" /> The Problem
                    </div>
                    <div className="detail-row">
                        <span className="detail-label">Breached Rule</span>
                        <span className="detail-value">{problem.entity_name}</span>
                    </div>
                    <div className="detail-row">
                        <span className="detail-label">Score vs Threshold</span>
                        <span className="detail-value" style={{ color: 'var(--accent-red)' }}>
                            {problem.metrics?.score?.toFixed(3)} &lt; {problem.context?.threshold}
                        </span>
                    </div>
                </div>
            )}

            {/* Reasoning Area */}
            <div style={{ display: 'flex', gap: '16px', flex: 1, minHeight: 0 }}>

                {/* Left Side: Logic Steps */}
                <div style={{ flex: 1, overflowY: 'auto', paddingRight: '8px' }}>
                    <div className="detail-section">
                        <div className="detail-section-title" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <Cpu size={14} color="var(--accent-cyan)" /> Agent Reasoning
                        </div>

                        <div className="event-list">
                            {reasoning.lineage && (
                                <div className="event-item">
                                    <strong style={{ color: 'var(--accent-blue)' }}>Lineage Traced:</strong>
                                    Found backing model {reasoning.lineage.entity_name}
                                </div>
                            )}
                            {reasoning.analysis && (
                                <div className="event-item">
                                    <strong style={{ color: 'var(--accent-purple)' }}>SQL Analyzed:</strong>
                                    Inferred '{reasoning.analysis.context?.inferred_semantic_type}' type.
                                    {reasoning.analysis.context?.detected_risks?.length > 0 && (
                                        <div style={{ color: 'var(--accent-amber)', marginTop: '4px' }}>
                                            Risks: {reasoning.analysis.context.detected_risks.join(', ')}
                                        </div>
                                    )}
                                </div>
                            )}
                            {reasoning.gaps && (
                                <div className="event-item" style={{ borderColor: 'var(--accent-red)' }}>
                                    <strong style={{ color: 'var(--accent-red)' }}>Policy Gaps:</strong>
                                    {reasoning.gaps.context?.gaps?.join(', ')}
                                </div>
                            )}
                        </div>
                    </div>

                    {decision && (
                        <div className="detail-section">
                            <div className="detail-section-title" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <ShieldAlert size={14} color="var(--accent-green)" /> Decision & PR Raised
                            </div>
                            <div style={{ color: 'var(--text-primary)', fontSize: '0.9rem', padding: '8px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                                {decision.explanation}

                                {decision.context?.pr_id && (
                                    <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                                        <a
                                            href={`${repoUrl}/pull/${decision.context.pr_id}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                display: 'inline-block',
                                                padding: '6px 12px',
                                                background: 'transparent',
                                                border: '1px solid var(--accent-purple)',
                                                color: 'var(--accent-purple)',
                                                textDecoration: 'none',
                                                borderRadius: '4px',
                                                fontSize: '0.85rem',
                                                fontWeight: '500'
                                            }}
                                        >
                                            View Pull Request #{decision.context.pr_id} on GitHub
                                        </a>

                                        {(!inv.outcomes || inv.outcomes.length === 0) && (
                                            <div className="animate-pulse" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-amber)', fontSize: '0.85rem', fontWeight: '500', background: 'rgba(245, 158, 11, 0.1)', padding: '6px 12px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                                                <AlertCircle size={14} />
                                                Waiting for Human in the loop: Please review and Merge the Pull Request
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            {decision.context?.diff && (
                                <div style={{ marginTop: '12px' }}>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Git Code Diff</div>
                                    <pre style={{
                                        background: '#0d1117',
                                        padding: '12px',
                                        borderRadius: '6px',
                                        fontSize: '0.8rem',
                                        overflowX: 'auto',
                                        border: '1px solid #30363d',
                                        color: '#c9d1d9',
                                        fontFamily: 'monospace',
                                        whiteSpace: 'pre-wrap'
                                    }}>
                                        <code>
                                            {decision.context.diff.split('\n').map((line, i) => {
                                                let color = '#c9d1d9';
                                                let bg = 'transparent';
                                                if (line.startsWith('+') && !line.startsWith('+++')) { color = '#3fb950'; bg = 'rgba(63, 185, 80, 0.1)'; }
                                                else if (line.startsWith('-') && !line.startsWith('---')) { color = '#ff7b72'; bg = 'rgba(255, 123, 114, 0.1)'; }
                                                else if (line.startsWith('@@')) color = '#d2a8ff';
                                                return <div key={i} style={{ color, backgroundColor: bg, padding: '0 4px' }}>{line}</div>;
                                            })}
                                        </code>
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}

                    {inv.outcomes && inv.outcomes.length > 0 && (
                        <div className="detail-section">
                            <div className="detail-section-title">Outcome Measured</div>
                            {inv.outcomes.map(o => (
                                <div key={o.event_id} style={{ fontSize: '0.85rem', color: 'var(--accent-green)' }}>
                                    ✅ Score rose to {o.metrics?.score?.toFixed(2)} on day {o.context?.fix_day + 1}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Right Side: Graph */}
                <div style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '12px', fontSize: '0.8rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--glass-border)' }}>
                        <FileSearch size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '6px' }} />
                        Lineage Map
                    </div>
                    <div style={{ flex: 1 }}>
                        {reasoning.lineage ? (
                            <LineageGraph lineageEvent={reasoning.lineage} focusTerm={inv.focus_term} />
                        ) : (
                            <div style={{ padding: '20px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>No lineage graph available.</div>
                        )}
                    </div>
                </div>

            </div>

        </div>
    );
}

export default InvestigationDetails;

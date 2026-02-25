import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

function LearningView({ data }) {
    const imp = data?.improvements || [];

    if (imp.length === 0) {
        return <div style={{ color: 'var(--text-muted)' }}>No learning iterations yet.</div>;
    }

    // Pre-process improvements, simply group by TDE for chart 
    const chartDataMap = {};
    imp.forEach(i => {
        chartDataMap[i.tde] = i.score_after * 100;
    });

    const chartData = Object.keys(chartDataMap).map(k => ({
        name: k.split('.')[1] || k, // truncate name 
        score: parseFloat(chartDataMap[k].toFixed(1))
    }));

    return (
        <div style={{ width: '100%', height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip
                        contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--glass-border)', color: 'var(--text-primary)' }}
                        itemStyle={{ color: 'var(--accent-green)' }}
                        formatter={(value) => [`${value}%`, 'Score After Setup']}
                    />
                    <Bar dataKey="score" fill="var(--accent-green)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

export default LearningView;

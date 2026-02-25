import React, { useState, useEffect, useRef } from 'react';
import { fetchInvestigations, fetchLatestState, fetchLearningSummary } from './api';
import Timeline from './components/Timeline';
import InvestigationDetails from './components/InvestigationDetails';
import Heatmap from './components/Heatmap';
import LearningView from './components/LearningView';
import { BrainCircuit, Activity, LineChart, Target, Play, Pause, SkipForward } from 'lucide-react';

function App() {
  const [investigations, setInvestigations] = useState([]);
  const [latestState, setLatestState] = useState({});
  const [learningSummary, setLearningSummary] = useState({ improvements: [] });
  const [selectedInvestigation, setSelectedInvestigation] = useState(null);
  const [loading, setLoading] = useState(true);

  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(2000); // 2 seconds per event
  const playIntervalRef = useRef(null);

  useEffect(() => {
    async function loadData() {
      try {
        const invs = await fetchInvestigations();
        const state = await fetchLatestState();
        const learning = await fetchLearningSummary();

        setInvestigations(invs);
        setLatestState(state);
        setLearningSummary(learning);

        if (invs.length > 0) {
          setSelectedInvestigation(invs[invs.length - 1]); // Select latest by default
        }
      } catch (err) {
        console.error("Failed to load data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Playback Logic
  useEffect(() => {
    if (isPlaying && investigations.length > 0) {
      playIntervalRef.current = setInterval(() => {
        setSelectedInvestigation((prev) => {
          if (!prev) return investigations[0];
          const currentIndex = investigations.findIndex(inv => inv.id === prev.id);
          if (currentIndex < investigations.length - 1) {
            return investigations[currentIndex + 1];
          } else {
            // Reached the end, pause playback
            setIsPlaying(false);
            return prev;
          }
        });
      }, playbackSpeed);
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    }

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, investigations, playbackSpeed]);


  if (loading) {
    return <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
      <BrainCircuit className="animate-pulse" size={48} color="var(--accent-purple)" />
    </div>;
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <header className="sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BrainCircuit size={24} color="var(--accent-purple)" />
            <h1>Cognition_Play</h1>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              style={{
                background: isPlaying ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                border: isPlaying ? '1px solid var(--accent-red)' : '1px solid var(--accent-green)',
                color: isPlaying ? 'var(--accent-red)' : 'var(--accent-green)',
                borderRadius: '100%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
              }}
              title={isPlaying ? "Pause Playback" : "Replay Agent Cognition"}
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} style={{ marginLeft: '2px' }} />}
            </button>
          </div>
        </header>
        <Timeline
          investigations={investigations}
          selectedId={selectedInvestigation?.id}
          onSelect={setSelectedInvestigation}
        />
      </aside>

      <main className="main-content">
        <div className="dashboard-grid">
          <div className="panel">
            <h2 className="panel-header">
              <Activity size={20} color="var(--accent-cyan)" />
              Business Term Risk State
            </h2>
            <Heatmap states={latestState} />
          </div>
          <div className="panel">
            <h2 className="panel-header">
              <LineChart size={20} color="var(--accent-green)" />
              Agent Learning Outcomes
            </h2>
            <LearningView data={learningSummary} />
          </div>
        </div>

        <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h2 className="panel-header">
            <Target size={20} color="var(--accent-purple)" />
            Investigation Reasoning
          </h2>
          {selectedInvestigation ? (
            <InvestigationDetails inv={selectedInvestigation} />
          ) : (
            <div style={{ color: 'var(--text-muted)' }}>Select an investigation from the timeline.</div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;

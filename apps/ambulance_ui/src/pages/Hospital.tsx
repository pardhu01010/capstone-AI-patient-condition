import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity, ShieldAlert, Cpu } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

const Hospital = () => {
    const [cases, setCases] = useState<any[]>([]);

    useEffect(() => {
        const fetchCases = async () => {
            try {
                const res = await axios.get(`${API_BASE}/cases`);
                setCases(res.data);
            } catch (err) {
                console.error("Failed to load cases", err);
            }
        };
        fetchCases();
        const interval = setInterval(fetchCases, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ padding: '2rem', display: 'flex', gap: '2rem' }}>
            <div className="sidebar">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#ff8c00', marginBottom: '1.5rem', fontWeight: 600 }}>
                    <ShieldAlert /> Priority Triage Queue
                </div>

                {cases.length === 0 ? (
                    <div style={{ color: '#8b949e', fontSize: '0.85rem' }}>No incoming ambulances at the moment.</div>
                ) : (
                    cases.map((c, i) => (
                        <div key={i} className="card" style={{ padding: '1rem', cursor: 'pointer', borderLeft: `4px solid ${c.risk_level === 'critical' ? '#ff4b4b' : c.risk_level === 'high' ? '#ff8c00' : '#00c48c'}` }}>
                            <div style={{ fontWeight: 600, color: '#e6edf3', display: 'flex', justifyContent: 'space-between' }}>
                                {c.patient.name || 'Unknown Protocol'} 
                                <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>{(c.survival_probability * 100).toFixed(0)}% Surv.</span>
                            </div>
                            <div style={{ fontSize: '0.8rem', color: '#8b949e', marginTop: '4px' }}>
                                HR: {c.vitals.heart_rate} | SpO2: {c.vitals.spo2}%
                            </div>
                        </div>
                    ))
                )}
            </div>

            <div style={{ flex: 1, padding: '1rem' }} className="glass-panel card">
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', flexDirection: 'column', color: '#8b949e' }}>
                    <Cpu size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                    <h2 style={{ fontSize: '1.2rem', fontWeight: 500 }}>Select a case from the queue</h2>
                    <p style={{ fontSize: '0.9rem', maxWidth: '400px', textAlign: 'center', marginTop: '0.5rem' }}>
                        View live telemetry, read AI-generated clinical summaries, and coordinate preparation pipelines.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Hospital;

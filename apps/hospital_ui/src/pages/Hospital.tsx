import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, FileText, User, Info, CheckCircle2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import gsap from 'gsap';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export default function Hospital() {
  const [progress, setProgress] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const heroRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<{ val: number }>({ val: 0 });

  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [activeCase, setActiveCase] = useState<any>(null);
  
  const [suggestionText, setSuggestionText] = useState("");
  const [suggestionName, setSuggestionName] = useState("");
  const [suggestionPriority, setSuggestionPriority] = useState("Normal");

  const getRiskColor = (risk: string) => {
    if (risk === 'critical') return '#D13619';
    if (risk === 'high') return '#f59e0b';
    return '#00c48c';
  };

  const getRiskBgColor = (risk: string) => {
    if (risk === 'critical') return 'rgba(209, 54, 25, 0.1)';
    if (risk === 'high') return 'rgba(245, 158, 11, 0.1)';
    return 'rgba(0, 196, 140, 0.1)';
  };

  // GSAP Boot Sequence
  useEffect(() => {
      let ctx = gsap.context(() => {
          gsap.to(progressRef.current, {
              val: 100,
              duration: 4,
              ease: "power2.inOut",
              onUpdate: function() {
                  setProgress(Math.floor(progressRef.current.val));
              },
              onComplete: () => {
                  setIsReady(true);
              }
          });
      });
      return () => ctx.revert();
  }, []);

  useEffect(() => {
      if (isReady && heroRef.current && formRef.current) {
          let tl = gsap.timeline();
          tl.to({}, { duration: 0.8 });
          tl.to(heroRef.current, { 
              opacity: 0, 
              duration: 1, 
              ease: 'power3.inOut',
              onComplete: () => {
                  if (heroRef.current) heroRef.current.style.display = 'none';
              }
          });
          tl.to(formRef.current, { 
              opacity: 1, 
              display: 'flex', 
              y: 0, 
              duration: 1, 
              ease: 'power2.out' 
          }, "-=0.6");
      }
  }, [isReady]);

  // Data Fetching
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await axios.get(`${API_BASE}/cases`);
        setCases(response.data);
      } catch (err) {
        console.error("Failed to fetch cases", err);
      }
    };
    fetchCases();
    const interval = setInterval(fetchCases, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDetail = async () => {
    if (!selectedCaseId) return;
    try {
      const response = await axios.get(`${API_BASE}/cases/${selectedCaseId}`);
      setActiveCase(response.data);
    } catch (err) {
      console.error("Failed to fetch case detail", err);
    }
  };

  useEffect(() => {
    fetchDetail();
    const detailInterval = setInterval(fetchDetail, 5000);
    return () => clearInterval(detailInterval);
  }, [selectedCaseId]);

  const sendSuggestion = async () => {
    if (!suggestionText) return;
    try {
      await axios.post(`${API_BASE}/cases/${selectedCaseId}/suggestions`, {
        text: suggestionText,
        posted_by: suggestionName || "Hospital Staff",
        priority: suggestionPriority
      });
      setSuggestionText("");
      fetchDetail();
    } catch (err) {
      console.error("Failed to send suggestion", err);
    }
  };

  const chartData = activeCase?.vitals_history?.map((h: any) => {
    const date = new Date(h.timestamp);
    return {
      time: `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`,
      gbm: Number((h.survival_probability * 100).toFixed(1)),
      lr: Number((activeCase.lr_survival_probability * 100).toFixed(1))
    };
  }) || [];

  return (
    <div style={{ 
        height: '100vh', 
        width: '100vw', 
        backgroundColor: '#111111', 
        backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
        backgroundSize: '50px 50px',
        position: 'relative',
        overflow: 'hidden', 
        margin: 0, 
        padding: 0 
    }}>
      
      {/* BOOT SEQUENCE HERO */}
      <div ref={heroRef} style={{ 
          height: '100vh', 
          width: '100%', 
          position: 'absolute',
          top: 0, left: 0,
          display: 'flex',
          backgroundColor: '#111111', 
          backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          pointerEvents: isReady ? 'none' : 'auto',
          zIndex: 100
      }}>
          <div style={{
              position: 'absolute',
              top: '50px',
              left: '60px',
              fontSize: '14rem',
              fontWeight: 900,
              color: '#D13619',
              fontFamily: '"Impact", "Arial Black", sans-serif',
              lineHeight: 0.8,
              letterSpacing: '-0.02em',
              transition: 'color 0.5s ease',
              textShadow: isReady ? '0 0 40px rgba(209, 54, 25, 0.6)' : 'none'
          }}>
              {progress}
          </div>
          <div style={{
              position: 'absolute',
              top: '60px',
              right: '70px',
              fontSize: '1.8rem',
              fontWeight: 600,
              color: '#777777',
              letterSpacing: '0.5em',
              fontFamily: 'sans-serif'
          }}>
              HOSPITAL COMMAND
          </div>

          <div style={{
              position: 'absolute',
              top: '65%',
              left: '55%',
              transform: 'translate(-50%, -50%)',
              width: '85%',
              maxWidth: '1000px',
              mixBlendMode: 'screen',
              pointerEvents: 'none',
              display: 'flex'
          }}>
              <img 
                  src="/wireframe_hospital.png" 
                  alt="Wireframe Hospital" 
                  style={{
                      width: '100%',
                      objectFit: 'contain',
                      filter: 'contrast(1.2) brightness(1.2)',
                  }}
              />
              <div style={{
                  position: 'absolute',
                  bottom: '0',
                  right: '0',
                  width: '8%',
                  height: '12%',
                  backgroundColor: '#000000'
              }}></div>
          </div>
      </div>

      {/* DASHBOARD UI */}
      <div ref={formRef} style={{ 
          opacity: 0, 
          display: 'none', 
          height: '100vh',
          width: '100vw',
          flexDirection: 'row',
          position: 'absolute',
          top: 0, left: 0
      }}>
        
        {/* SIDEBAR */}
        <div style={{ width: '320px', borderRight: '2px solid #333', display: 'flex', flexDirection: 'column', background: 'transparent' }}>
          <div style={{ padding: '2rem', borderBottom: '2px solid #333' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: 0, letterSpacing: '0.05em' }}>INCOMING CASES</h2>
          </div>
          <div style={{ overflowY: 'auto', flex: 1, padding: '1rem' }}>
            {cases.map((c) => (
              <div 
                key={c.case_id} 
                onClick={() => setSelectedCaseId(c.case_id)}
                style={{ 
                  padding: '1.2rem', 
                  marginBottom: '1rem',
                  cursor: 'pointer',
                  background: selectedCaseId === c.case_id ? '#1a1a1a' : '#050505',
                  border: '1px solid #1a1a1a',
                  borderLeft: `4px solid ${getRiskColor(c.risk_level)}`,
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#fff', marginBottom: '0.5rem', fontFamily: 'monospace' }}>{c.patient?.name || 'UNKNOWN'}</div>
                <div style={{ fontSize: '1rem', fontWeight: 'bold', color: getRiskColor(c.risk_level), textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  {c.risk_level} RISK
                </div>
                <div style={{ fontSize: '0.85rem', color: '#777', fontFamily: 'monospace' }}>
                  SURVIVAL: {(c.survival_probability * 100).toFixed(0)}% • ID: {c.case_id.substring(0, 8)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* MAIN VIEW */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '2rem 3rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid #333', paddingBottom: '1rem', marginBottom: '2rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: 0, letterSpacing: '0.05em' }}>
                      <Activity color="#D13619" size={32} />
                      COMMAND DASHBOARD
                  </h2>
                  <span style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontFamily: 'monospace' }}>REAL-TIME AMBULANCE INTAKE • XGBOOST GBM + LR</span>
              </div>
              <span style={{ color: '#777777', letterSpacing: '0.3em', fontSize: '0.8rem', fontWeight: 600 }}>UNIT-HOSP 01</span>
          </div>

          <div style={{ border: '1px solid #D13619', padding: '1rem', background: 'rgba(209, 54, 25, 0.05)', color: '#D13619', display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '2rem' }}>
              <AlertTriangle size={20} />
              <span style={{ fontSize: '0.9rem', fontFamily: 'monospace' }}>AI DECISION SUPPORT — USE WITH CAUTION. Risk scores and recommendations are generated by AI models. Always apply clinical judgement.</span>
          </div>

          {!selectedCaseId || !activeCase ? (
            <div style={{ padding: '3rem', color: '#777', fontFamily: 'monospace', fontSize: '1.2rem' }}>AWAITING TELEMETRY SELECTION...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              
              {/* PATIENT PROFILE HEADER */}
              <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                 <div style={{ border: `2px solid ${getRiskColor(activeCase.risk_level)}`, borderRadius: '50%', padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <User color={getRiskColor(activeCase.risk_level)} size={32} />
                 </div>
                 <div style={{ flex: 1 }}>
                   <h3 style={{ fontSize: '1.8rem', color: '#fff', margin: '0 0 0.5rem 0', fontFamily: '"Impact", "Arial Black", sans-serif', letterSpacing: '0.05em' }}>{activeCase.patient?.name || 'UNKNOWN PATIENT'}</h3>
                   <div style={{ color: '#777', fontFamily: 'monospace', fontSize: '1rem' }}>
                     AGE: {activeCase.patient?.age || '--'} • SEX: {activeCase.patient?.sex || '--'} • BLOOD: {activeCase.patient?.blood_group || '--'} • LOC: {activeCase.location || '--'}
                   </div>
                 </div>
                 <div style={{ background: getRiskBgColor(activeCase.risk_level), border: `2px solid ${getRiskColor(activeCase.risk_level)}`, color: getRiskColor(activeCase.risk_level), padding: '1rem 2rem', fontFamily: '"Impact", "Arial Black", sans-serif', fontSize: '1.5rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                   {activeCase.risk_level} RISK
                 </div>
              </div>

              {/* METRICS ROW */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1.5rem' }}>
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem', textAlign: 'center' }}>
                   <div style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '1rem' }}>RISK LEVEL</div>
                   <div style={{ color: getRiskColor(activeCase.risk_level), fontSize: '2rem', fontFamily: '"Impact", "Arial Black", sans-serif', textTransform: 'uppercase' }}>{activeCase.risk_level}</div>
                 </div>
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem', textAlign: 'center' }}>
                   <div style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '1rem' }}>SURVIVAL (GBM)</div>
                   <div style={{ color: '#fff', fontSize: '2.5rem', fontFamily: 'monospace' }}>{(activeCase.survival_probability * 100).toFixed(1)}%</div>
                 </div>
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem', textAlign: 'center' }}>
                   <div style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '1rem' }}>SURVIVAL (LR)</div>
                   <div style={{ color: '#fff', fontSize: '2.5rem', fontFamily: 'monospace' }}>{(activeCase.lr_survival_probability * 100).toFixed(1)}%</div>
                 </div>
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem', textAlign: 'center' }}>
                   <div style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '1rem' }}>CARDIAC SCORE</div>
                   <div style={{ color: '#fff', fontSize: '2.5rem', fontFamily: 'monospace' }}>{activeCase.cardiac_risk_score.toFixed(1)}<span style={{ fontSize: '1rem', color: '#777' }}>/10</span></div>
                 </div>
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem', textAlign: 'center' }}>
                   <div style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '1rem' }}>AGE</div>
                   <div style={{ color: '#fff', fontSize: '2.5rem', fontFamily: 'monospace' }}>{activeCase.patient?.age || '--'}</div>
                 </div>
              </div>

              {/* VITALS & RECS GRID */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                 
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <Activity color="#D13619" size={20} /> VITALS SNAPSHOT
                   </h3>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontFamily: 'monospace', fontSize: '1.1rem' }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>Heart Rate (bpm)</span>
                       <span style={{ color: '#fff' }}>{activeCase.vitals?.heart_rate || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>Systolic BP (mmHg)</span>
                       <span style={{ color: '#D13619' }}>{activeCase.vitals?.blood_pressure_systolic || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>Diastolic BP (mmHg)</span>
                       <span style={{ color: '#fff' }}>{activeCase.vitals?.blood_pressure_diastolic || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>SpO₂ (%)</span>
                       <span style={{ color: '#D13619' }}>{activeCase.vitals?.spo2 || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>Resp. Rate (/min)</span>
                       <span style={{ color: '#fff' }}>{activeCase.vitals?.respiratory_rate || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: '0.5rem' }}>
                       <span style={{ color: '#777' }}>Temperature (°C)</span>
                       <span style={{ color: '#fff' }}>{activeCase.vitals?.temperature_c || '--'}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                       <span style={{ color: '#777' }}>Consciousness</span>
                       <span style={{ color: '#fff' }}>{activeCase.vitals?.consciousness_level || '--'}</span>
                     </div>
                   </div>
                 </div>

                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <Info color="#D13619" size={20} /> AI RECOMMENDATIONS
                   </h3>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                     {activeCase.recommendations?.map((rec: any, idx: number) => (
                        <div key={idx} style={{ background: '#111', border: '1px solid #1a1a1a', borderLeft: '4px solid #3b82f6', padding: '1rem', fontFamily: 'monospace' }}>
                          <div style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>{rec.title}</div>
                          <div style={{ color: '#777', fontSize: '0.9rem', lineHeight: 1.4 }}>{rec.detail}</div>
                        </div>
                     ))}
                   </div>
                 </div>

              </div>

              {/* DETAILS ROW 2 */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '2rem' }}>
                 
                 {/* DETAILS */}
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <FileText color="#D13619" size={20} /> CLINICAL DETAILS
                   </h3>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontFamily: 'monospace', fontSize: '1rem' }}>
                     <div><span style={{color: '#777'}}>ALLERGIES:</span><br/><span style={{color: '#fff'}}>{activeCase.patient?.allergies || 'NONE'}</span></div>
                     <div><span style={{color: '#777'}}>CHRONIC:</span><br/><span style={{color: '#fff'}}>{activeCase.patient?.chronic_conditions || 'NONE'}</span></div>
                     <div><span style={{color: '#777'}}>SYMPTOMS:</span><br/><span style={{color: '#fff'}}>{activeCase.symptoms?.join(', ') || 'NONE'}</span></div>
                     <div><span style={{color: '#777'}}>MEDS GIVEN:</span><br/><span style={{color: '#fff'}}>{activeCase.meds_administered?.join(', ') || 'NONE'}</span></div>
                     <div><span style={{color: '#777'}}>O2 SUPPORT:</span><br/><span style={{color: '#fff'}}>{activeCase.oxygen_support || 'NONE'}</span></div>
                   </div>
                 </div>

                 {/* MEDS PREP */}
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <Activity color="#D13619" size={20} /> MEDICATION PREP
                   </h3>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontFamily: 'monospace' }}>
                     {activeCase.medication_plan?.map((med: any, idx: number) => (
                         <div key={idx} style={{ background: '#111', border: '1px solid #1a1a1a', padding: '1rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.5rem' }}>
                            <div style={{ width: '12px', height: '12px', background: med.priority === 'immediate' ? '#D13619' : '#3b82f6' }}></div>
                            <span style={{ color: '#fff', fontSize: '1.1rem' }}>{med.medication}</span>
                          </div>
                          <div style={{ color: '#777', fontSize: '0.9rem' }}>{med.purpose}</div>
                        </div>
                     ))}
                   </div>
                 </div>

                 {/* SHAP BARS */}
                 <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 0.5rem 0', letterSpacing: '0.05em' }}>
                     <Activity color="#D13619" size={20} /> TOP RISK DRIVERS
                   </h3>
                   <div style={{ color: '#777', fontFamily: 'monospace', fontSize: '0.85rem', marginBottom: '1.5rem' }}>RED ↑ INCREASES RISK • GREEN ↓ DECREASES RISK</div>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', fontFamily: 'monospace' }}>
                     {activeCase.top_shap_features?.map((f: any, idx: number) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: '#fff', fontSize: '1rem' }}>{f.feature}</span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div style={{ width: '80px', height: '10px', background: '#111', border: '1px solid #1a1a1a', position: 'relative' }}>
                              <div style={{ position: 'absolute', right: 0, top: 0, height: '100%', width: `${Math.min(100, Math.abs(f.shap_value) * 30)}%`, background: f.shap_value > 0 ? '#D13619' : '#00c48c' }}></div>
                            </div>
                            <span style={{ color: f.shap_value > 0 ? '#D13619' : '#00c48c', fontSize: '1rem', width: '50px', textAlign: 'right' }}>
                              {f.shap_value > 0 ? '↑' : '↓'} {Math.abs(f.shap_value).toFixed(2)}
                            </span>
                          </div>
                        </div>
                     ))}
                   </div>
                 </div>

              </div>

              {/* NARRATIVE SUMMARY */}
              <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <FileText color="#D13619" size={20} /> CLINICAL NARRATIVE SUMMARY
                   </h3>
                   <p style={{ color: '#777', fontSize: '1.1rem', lineHeight: 1.6, fontFamily: 'monospace', margin: 0 }}>
                     {activeCase.llm_summary || "NO NARRATIVE PROVIDED."}
                   </p>
              </div>

              {/* HOSPITAL SUGGESTIONS */}
              <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <FileText color="#D13619" size={20} /> SEND SUGGESTIONS TO AMBULANCE
                   </h3>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
                     {activeCase.hospital_suggestions?.map((s: any, idx: number) => (
                        <div key={idx} style={{ background: s.acknowledged ? '#111' : 'rgba(209, 54, 25, 0.1)', border: `1px solid ${s.acknowledged ? '#1a1a1a' : '#D13619'}`, padding: '1rem', fontFamily: 'monospace', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>{s.text}</div>
                            <div style={{ color: '#777', fontSize: '0.9rem' }}>{s.posted_by} • {s.priority}</div>
                          </div>
                          {s.acknowledged && <span style={{ color: '#00c48c', display: 'flex', alignItems: 'center', gap: '5px' }}><CheckCircle2 size={16} /> SEEN</span>}
                        </div>
                     ))}
                   </div>
                   
                   <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                     <textarea 
                        value={suggestionText}
                        onChange={e => setSuggestionText(e.target.value)}
                        placeholder="MESSAGE PAYLOAD..."
                        style={{ flex: 1, background: '#111', border: '1px solid #1a1a1a', color: '#fff', fontSize: '1.1rem', fontFamily: 'monospace', padding: '1rem', minHeight: '100px', resize: 'none', outline: 'none' }}
                     />
                     <div style={{ width: '250px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <input 
                          type="text" 
                          placeholder="AUTHOR IDENTIFIER"
                          value={suggestionName}
                          onChange={e => setSuggestionName(e.target.value)}
                          style={{ width: '100%', background: '#111', border: '1px solid #1a1a1a', color: '#fff', fontSize: '1.1rem', fontFamily: 'monospace', padding: '1rem', outline: 'none' }}
                        />
                        <select 
                          value={suggestionPriority}
                          onChange={e => setSuggestionPriority(e.target.value)}
                          style={{ width: '100%', background: '#111', border: '1px solid #1a1a1a', color: '#fff', fontSize: '1.1rem', fontFamily: 'monospace', padding: '1rem', outline: 'none' }}
                        >
                          <option>Normal</option>
                          <option>Urgent</option>
                        </select>
                     </div>
                   </div>
                   <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                     <button onClick={sendSuggestion} style={{ background: '#D13619', color: '#fff', border: 'none', padding: '1rem 2rem', fontFamily: '"Impact", "Arial Black", sans-serif', fontSize: '1.2rem', letterSpacing: '0.1em', cursor: 'pointer' }}>TRANSMIT</button>
                     <button onClick={() => setSuggestionText(p => p + "PREPARE OT ROOM. ")} style={{ background: 'transparent', color: '#777', border: '1px solid #1a1a1a', padding: '1rem 2rem', fontFamily: 'monospace', fontSize: '1rem', cursor: 'pointer' }}>+ OT</button>
                     <button onClick={() => setSuggestionText(p => p + "ALERT CARDIOLOGIST. ")} style={{ background: 'transparent', color: '#777', border: '1px solid #1a1a1a', padding: '1rem 2rem', fontFamily: 'monospace', fontSize: '1rem', cursor: 'pointer' }}>+ CARDIOLOGIST</button>
                   </div>
              </div>

              {/* XAI PLOTS */}
              <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <Activity color="#D13619" size={20} /> XAI EXPLORER
                   </h3>
                   <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', fontFamily: 'monospace' }}>
                     <div>
                       <div style={{ color: '#fff', marginBottom: '1rem', fontSize: '1.1rem' }}>LOCAL SHAP — THIS PATIENT</div>
                       {activeCase.shap_local_plot_b64 ? (
                         <img src={`data:image/png;base64,${activeCase.shap_local_plot_b64}`} style={{ width: '100%', filter: 'invert(0.9) hue-rotate(180deg)' }} alt="SHAP" />
                       ) : <div style={{ color: '#777' }}>NO DATA</div>}
                     </div>
                     <div>
                       <div style={{ color: '#fff', marginBottom: '1rem', fontSize: '1.1rem' }}>LIME — SANITY CHECK</div>
                       {activeCase.lime_local_plot_b64 ? (
                         <img src={`data:image/png;base64,${activeCase.lime_local_plot_b64}`} style={{ width: '100%', filter: 'invert(0.9) hue-rotate(180deg)' }} alt="LIME" />
                       ) : <div style={{ color: '#777' }}>NO DATA</div>}
                     </div>
                   </div>
                   <div style={{ marginTop: '2rem', width: '50%', fontFamily: 'monospace' }}>
                       <div style={{ color: '#fff', marginBottom: '1rem', fontSize: '1.1rem' }}>GLOBAL FEATURE IMPORTANCE</div>
                       {activeCase.shap_global_plot_b64 ? (
                         <img src={`data:image/png;base64,${activeCase.shap_global_plot_b64}`} style={{ width: '100%', filter: 'invert(0.9) hue-rotate(180deg)' }} alt="SHAP Global" />
                       ) : <div style={{ color: '#777' }}>NO DATA</div>}
                   </div>
              </div>

              {/* HISTORICAL TREND */}
              <div style={{ background: '#050505', border: '1px solid #1a1a1a', padding: '1.5rem' }}>
                   <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '0 0 1.5rem 0', letterSpacing: '0.05em' }}>
                     <Activity color="#D13619" size={20} /> SURVIVAL TELEMETRY TREND
                   </h3>
                   <div style={{ height: '300px', width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" vertical={false} />
                          <XAxis dataKey="time" stroke="#777" tick={{fontSize: 12, fill: '#777', fontFamily: 'monospace'}} tickLine={false} axisLine={false} />
                          <YAxis stroke="#777" tick={{fontSize: 12, fill: '#777', fontFamily: 'monospace'}} tickLine={false} axisLine={false} domain={[0, 100]} />
                          <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#1a1a1a', color: '#fff', borderRadius: '0', fontFamily: 'monospace' }} />
                          <Legend wrapperStyle={{ fontSize: '12px', color: '#777', fontFamily: 'monospace' }} />
                          <Line type="monotone" dataKey="gbm" name="GBM SURVIVAL %" stroke="#D13619" strokeWidth={3} dot={{r: 4, fill: '#111', strokeWidth: 2}} activeDot={{r: 6}} />
                          <Line type="monotone" dataKey="lr" name="LR SURVIVAL %" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, fill: '#111', strokeWidth: 2}} />
                        </LineChart>
                      </ResponsiveContainer>
                   </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, HeartPulse, Wind, Thermometer, Brain, Send } from 'lucide-react';
import gsap from 'gsap';

const API_BASE = "http://localhost:8000/api";

const Ambulance = () => {
    const [progress, setProgress] = useState(0);
    const [isReady, setIsReady] = useState(false);
    
    const heroRef = useRef<HTMLDivElement>(null);
    const formRef = useRef<HTMLDivElement>(null);
    const progressRef = useRef<{ val: number }>({ val: 0 });

    const [vitals, setVitals] = useState({
        heart_rate: 124,
        blood_pressure_systolic: 120,
        blood_pressure_diastolic: 80,
        spo2: 98,
        respiratory_rate: 16,
        temperature_c: 37.0,
        consciousness_level: "Alert"
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<any>(null);

    // Boot Animation Sequence
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

    // Layout Transition Sequence
    useEffect(() => {
        if (isReady && heroRef.current && formRef.current) {
            let tl = gsap.timeline();
            
            // Wait slightly after 100
            tl.to({}, { duration: 0.8 });
            
            // Fade out the entire hero strictly
            tl.to(heroRef.current, { 
                opacity: 0, 
                duration: 1, 
                ease: 'power3.inOut',
                onComplete: () => {
                    if (heroRef.current) heroRef.current.style.display = 'none';
                }
            });
            
            // Slide up the Vitals form
            tl.to(formRef.current, { 
                opacity: 1, 
                display: 'block', 
                y: 0, 
                duration: 1, 
                ease: 'power2.out' 
            }, "-=0.6");
        }
    }, [isReady]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            const payload = {
                patient: { name: "System Intake", age: 0, sex: "Unknown", blood_group: "Unknown", allergies: [], chronic_conditions: [] },
                vitals: vitals,
                symptoms: ["context-upload"],
                meds_administered: [],
                labs: [],
                attachments: []  
            };
            const response = await axios.post(`${API_BASE}/intake`, payload);
            setResult(response.data);
        } catch (error) {
            console.error("API Error", error);
        } finally {
            setIsSubmitting(false);
        }
    };

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
            
            {/* GSAP Revealed Form Section - Unified Theme */}
            <div ref={formRef} style={{ 
                opacity: 0, 
                display: 'none', 
                position: 'absolute', 
                top: 0, left: 0, 
                width: '100%', height: '100vh', 
                overflowY: 'auto'
            }}>
                <div style={{ padding: '4rem 2rem', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
                
                {result && (
                    <div style={{ marginBottom: '2rem', background: 'rgba(209, 54, 25, 0.1)', padding: '2rem', border: '2px solid #D13619' }}>
                        <h4 style={{ color: '#D13619', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', fontFamily: '"Impact", "Arial Black", sans-serif' }}>
                            <Activity size={24} />
                            TRANSMISSION SUCCESSFUL
                        </h4>
                        <p style={{ fontSize: '1rem', color: '#777777', lineHeight: 1.6, fontFamily: 'monospace' }}>{result.llm_summary || 'Triage summary and prediction arrays stored to primary hospital databases.'}</p>
                    </div>
                )}
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid #333', paddingBottom: '1rem', marginBottom: '3rem' }}>
                    <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: 0, letterSpacing: '0.05em' }}>
                        <Activity color="#D13619" size={32} />
                        CONTEXT CAPTURE
                    </h2>
                    <span style={{ color: '#777777', letterSpacing: '0.3em', fontSize: '0.8rem', fontWeight: 600 }}>UNIT-Alpha 04</span>
                </div>
                
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    <div className="layout-grid" style={{ gap: '2rem' }}>
                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                                <HeartPulse size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> HEART RATE
                            </label>
                            <input type="number" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none' }} value={vitals.heart_rate} onChange={e => setVitals({...vitals, heart_rate: parseInt(e.target.value)})} />
                        </div>

                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                                <Activity size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> BLOOD PRESSURE
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <input type="number" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none', textAlign: 'center' }} value={vitals.blood_pressure_systolic} onChange={e => setVitals({...vitals, blood_pressure_systolic: parseInt(e.target.value)})} />
                                <span style={{ color: '#D13619', fontSize: '2rem', padding: '0 0.5rem' }}>/</span>
                                <input type="number" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none', textAlign: 'center' }} value={vitals.blood_pressure_diastolic} onChange={e => setVitals({...vitals, blood_pressure_diastolic: parseInt(e.target.value)})} />
                            </div>
                        </div>

                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                                <Wind size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> BLOOD OXYGEN (SpO2)
                            </label>
                            <input type="number" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: vitals.spo2 < 92 ? '2px solid #D13619' : '2px solid #333', color: vitals.spo2 < 92 ? '#D13619' : '#fff', fontSize: '2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none' }} value={vitals.spo2} onChange={e => setVitals({...vitals, spo2: parseInt(e.target.value)})} />
                        </div>

                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                                <Thermometer size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> CORE TEMP (°C)
                            </label>
                            <input type="number" step="0.1" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none' }} value={vitals.temperature_c} onChange={e => setVitals({...vitals, temperature_c: parseFloat(e.target.value)})} />
                        </div>
                    </div>

                    <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                        <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                            <Brain size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> NEUROLOGICAL CONSCIOUSNESS
                        </label>
                        <select style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#D13619', fontSize: '1.5rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none', appearance: 'none', cursor: 'pointer' }} value={vitals.consciousness_level} onChange={e => setVitals({...vitals, consciousness_level: e.target.value})}>
                            <option style={{ background: '#111', color: '#fff' }}>Alert</option>
                            <option style={{ background: '#111', color: '#fff' }}>Verbal</option>
                            <option style={{ background: '#111', color: '#fff' }}>Pain</option>
                            <option style={{ background: '#111', color: '#D13619' }}>Unresponsive</option>
                        </select>
                    </div>

                    <button type="submit" disabled={isSubmitting} style={{ 
                        background: '#D13619', 
                        color: '#fff', 
                        border: 'none', 
                        padding: '1.5rem', 
                        fontSize: '1.2rem', 
                        letterSpacing: '0.2em', 
                        fontWeight: 900, 
                        fontFamily: 'sans-serif',
                        cursor: 'pointer',
                        marginTop: '1rem',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: '10px'
                    }}>
                        <Send size={20} />
                        {isSubmitting ? "TRANSMITTING..." : "FINALIZE PROTOCOL"}
                    </button>
                </form>
                </div>
            </div>

            {/* Minimal Vector Card Hero Sequence */}
            <div ref={heroRef} style={{ 
                height: '100vh', 
                width: '100%', 
                position: 'absolute',
                top: 0, left: 0,
                display: 'flex',
                backgroundColor: '#111111', 
                backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
                backgroundSize: '50px 50px',
                pointerEvents: isReady ? 'none' : 'auto'
            }}>
                    
                {/* Top Left Number */}
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

                {/* Top Right Text */}
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
                    AMBULANCE
                </div>

                {/* Center Ambulance Image */}
                <img 
                    src="/wireframe_ambulance.png" 
                    alt="Wireframe Ambulance" 
                    style={{
                        position: 'absolute',
                        top: '65%',
                        left: '55%',
                        transform: 'translate(-50%, -50%)',
                        width: '85%',
                        maxWidth: '1000px',
                        objectFit: 'contain',
                        mixBlendMode: 'screen',
                        filter: 'contrast(2) brightness(1.2) grayscale(1)',
                        pointerEvents: 'none'
                    }}
                />
            </div>
            
        </div>
    );
};

export default Ambulance;

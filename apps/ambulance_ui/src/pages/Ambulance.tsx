import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, HeartPulse, Wind, Thermometer, Brain, Send, User, Stethoscope, Droplet, FileText, AlertTriangle, Upload } from 'lucide-react';
import gsap from 'gsap';

const API_BASE = "http://localhost:8000/api";

const Ambulance = () => {
    const [progress, setProgress] = useState(0);
    const [isReady, setIsReady] = useState(false);
    
    const heroRef = useRef<HTMLDivElement>(null);
    const formRef = useRef<HTMLDivElement>(null);
    const progressRef = useRef<{ val: number }>({ val: 0 });

    // --- Expanded Form State ---
    const [patient, setPatient] = useState({
        name: '',
        age: 0,
        sex: 'Unknown',
        blood_group: '',
        allergies: '',
        chronic_conditions: ''
    });

    const [vitals, setVitals] = useState({
        heart_rate: 0,
        blood_pressure_systolic: 0,
        blood_pressure_diastolic: 0,
        spo2: 0,
        respiratory_rate: 0,
        temperature_c: 0,
        consciousness_level: "Alert"
    });

    const [clinical, setClinical] = useState({
        symptoms: '',
        medications: '',
        oxygen: '',
        location: '',
        notes: ''
    });

    const [labs, setLabs] = useState({
        results: ''
    });

    const [attachments, setAttachments] = useState<any[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files) return;
        const files = Array.from(e.target.files);
        
        files.forEach(file => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64String = (reader.result as string).split(',')[1];
                setAttachments(prev => [...prev, {
                    filename: file.name,
                    content_type: file.type,
                    data_b64: base64String
                }]);
            };
            reader.readAsDataURL(file);
        });
    };

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
                patient: { 
                    name: patient.name || "Unknown", 
                    age: patient.age, 
                    sex: patient.sex, 
                    blood_group: patient.blood_group || "Unknown", 
                    allergies: patient.allergies ? patient.allergies.split(',').map(s => s.trim()) : [], 
                    chronic_conditions: patient.chronic_conditions ? patient.chronic_conditions.split(',').map(s => s.trim()) : [] 
                },
                vitals: vitals,
                symptoms: clinical.symptoms ? clinical.symptoms.split(',').map(s => s.trim()) : ["context-upload"],
                meds_administered: clinical.medications ? clinical.medications.split(',').map(s => s.trim()) : [],
                labs: labs.results ? [{ name: "Lab Report", value: labs.results }] : [],
                attachments: attachments  
            };
            const response = await axios.post(`${API_BASE}/intake`, payload);
            setResult(response.data);
        } catch (error) {
            console.error("API Error", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Helper Components for Brutalist Form Elements
    const InputBlock = ({ label, icon: Icon, value, onChange, type = "text", placeholder = "", colSpan = 1, required = false }: any) => (
        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a', gridColumn: `span ${colSpan}` }}>
            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                {Icon && <Icon size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/>} {label} {required && <span style={{ color: '#D13619' }}>*</span>}
            </label>
            <input 
                type={type} 
                value={value} 
                onChange={onChange} 
                placeholder={placeholder}
                required={required}
                style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: type === 'number' ? '2rem' : '1.2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none' }} 
            />
        </div>
    );

    const TextAreaBlock = ({ label, icon: Icon, value, onChange, placeholder = "", required = false }: any) => (
        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                {Icon && <Icon size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/>} {label} {required && <span style={{ color: '#D13619' }}>*</span>}
            </label>
            <textarea 
                value={value} 
                onChange={onChange} 
                placeholder={placeholder}
                required={required}
                rows={3}
                style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '1.1rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none', resize: 'vertical' }} 
            />
        </div>
    );

    const SectionHeader = ({ title, icon: Icon }: any) => (
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: '3rem 0 1rem 0', letterSpacing: '0.05em' }}>
            <Icon color="#D13619" size={20} />
            {title}
        </h3>
    );

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
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid #333', paddingBottom: '1rem', marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '2rem', color: '#D13619', fontFamily: '"Impact", "Arial Black", sans-serif', margin: 0, letterSpacing: '0.05em' }}>
                            <Activity color="#D13619" size={32} />
                            CONTEXT CAPTURE
                        </h2>
                        <span style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontFamily: 'monospace' }}><span style={{color: '#D13619'}}>*</span> INDICATES REQUIRED FIELD FOR AI TRIAGE</span>
                    </div>
                    <span style={{ color: '#777777', letterSpacing: '0.3em', fontSize: '0.8rem', fontWeight: 600 }}>UNIT-Alpha 04</span>
                </div>
                
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    
                    {/* WARNING BANNER */}
                    <div style={{ border: '1px solid #D13619', padding: '1rem', background: 'rgba(209, 54, 25, 0.05)', color: '#D13619', display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <AlertTriangle size={20} />
                        <span style={{ fontSize: '0.9rem', fontFamily: 'monospace' }}>AI DECISION SUPPORT — USE WITH CAUTION. Risk scores and recommendations are generated by AI models. Always apply clinical judgement.</span>
                    </div>

                    {/* PATIENT PROFILE */}
                    <SectionHeader title="PATIENT PROFILE" icon={User} />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
                        <InputBlock label="FULL NAME" icon={User} value={patient.name} onChange={(e: any) => setPatient({...patient, name: e.target.value})} placeholder="e.g. John Smith" colSpan={3} />
                        <InputBlock label="AGE (YEARS)" icon={User} type="number" value={patient.age || ''} onChange={(e: any) => setPatient({...patient, age: parseInt(e.target.value) || 0})} colSpan={1} />
                        
                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a', gridColumn: 'span 2' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>SEX</label>
                            <select style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #333', color: '#fff', fontSize: '1.2rem', fontFamily: 'monospace', padding: '0.5rem 0', outline: 'none' }} value={patient.sex} onChange={e => setPatient({...patient, sex: e.target.value})}>
                                <option style={{ background: '#111' }}>Unknown</option>
                                <option style={{ background: '#111' }}>Male</option>
                                <option style={{ background: '#111' }}>Female</option>
                            </select>
                        </div>

                        <InputBlock label="BLOOD GROUP" icon={Droplet} value={patient.blood_group} onChange={(e: any) => setPatient({...patient, blood_group: e.target.value})} placeholder="e.g. O+" colSpan={1} />
                        <InputBlock label="ALLERGIES" icon={AlertTriangle} value={patient.allergies} onChange={(e: any) => setPatient({...patient, allergies: e.target.value})} placeholder="e.g. Penicillin (comma separated)" colSpan={2} />
                        <InputBlock label="CHRONIC CONDITIONS" icon={Activity} value={patient.chronic_conditions} onChange={(e: any) => setPatient({...patient, chronic_conditions: e.target.value})} placeholder="e.g. Diabetes, Hypertension" colSpan={3} />
                    </div>

                    {/* VITAL SIGNS */}
                    <SectionHeader title="VITAL SIGNS" icon={Activity} />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
                        <InputBlock label="HEART RATE (bpm)" icon={HeartPulse} type="number" required={true} value={vitals.heart_rate || ''} onChange={(e: any) => setVitals({...vitals, heart_rate: parseInt(e.target.value) || 0})} />
                        <InputBlock label="SPO2 (%)" icon={Wind} type="number" required={true} value={vitals.spo2 || ''} onChange={(e: any) => setVitals({...vitals, spo2: parseInt(e.target.value) || 0})} />
                        <InputBlock label="RESP. RATE (/min)" icon={Wind} type="number" required={true} value={vitals.respiratory_rate || ''} onChange={(e: any) => setVitals({...vitals, respiratory_rate: parseInt(e.target.value) || 0})} />
                        <InputBlock label="SYSTOLIC BP (mmHg)" icon={Activity} type="number" required={true} value={vitals.blood_pressure_systolic || ''} onChange={(e: any) => setVitals({...vitals, blood_pressure_systolic: parseInt(e.target.value) || 0})} />
                        <InputBlock label="DIASTOLIC BP (mmHg)" icon={Activity} type="number" required={true} value={vitals.blood_pressure_diastolic || ''} onChange={(e: any) => setVitals({...vitals, blood_pressure_diastolic: parseInt(e.target.value) || 0})} />
                        <InputBlock label="TEMPERATURE (°C)" icon={Thermometer} type="number" required={true} value={vitals.temperature_c || ''} onChange={(e: any) => setVitals({...vitals, temperature_c: parseFloat(e.target.value) || 0})} />
                    </div>

                    {/* CONSCIOUSNESS LEVEL */}
                    <SectionHeader title="CONSCIOUSNESS LEVEL" icon={Brain} />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                        {['Alert', 'Verbal', 'Pain', 'Unresponsive'].map((level) => (
                            <div 
                                key={level}
                                onClick={() => setVitals({...vitals, consciousness_level: level})}
                                style={{
                                    padding: '1.5rem',
                                    textAlign: 'center',
                                    border: vitals.consciousness_level === level ? `2px solid ${level === 'Unresponsive' ? '#D13619' : '#fff'}` : '1px solid #1a1a1a',
                                    background: vitals.consciousness_level === level ? (level === 'Unresponsive' ? 'rgba(209, 54, 25, 0.1)' : 'rgba(255, 255, 255, 0.05)') : '#050505',
                                    color: vitals.consciousness_level === level ? (level === 'Unresponsive' ? '#D13619' : '#fff') : '#777',
                                    cursor: 'pointer',
                                    fontFamily: '"Impact", "Arial Black", sans-serif',
                                    fontSize: '1.2rem',
                                    letterSpacing: '0.1em'
                                }}
                            >
                                {level.toUpperCase()}
                            </div>
                        ))}
                    </div>

                    {/* CLINICAL DETAILS */}
                    <SectionHeader title="CLINICAL DETAILS" icon={Stethoscope} />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <InputBlock label="PRESENTING SYMPTOMS" icon={Stethoscope} required={true} value={clinical.symptoms} onChange={(e: any) => setClinical({...clinical, symptoms: e.target.value})} placeholder="e.g. chest pain, dizziness (comma separated)" />
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <InputBlock label="MEDICATIONS GIVEN" icon={FileText} value={clinical.medications} onChange={(e: any) => setClinical({...clinical, medications: e.target.value})} placeholder="e.g. Aspirin 325mg" />
                            <InputBlock label="OXYGEN SUPPORT" icon={Wind} value={clinical.oxygen} onChange={(e: any) => setClinical({...clinical, oxygen: e.target.value})} placeholder="e.g. NRB mask @ 12 L/min" />
                        </div>
                        <InputBlock label="LOCATION / GPS" icon={Activity} required={true} value={clinical.location} onChange={(e: any) => setClinical({...clinical, location: e.target.value})} placeholder="e.g. 12.97°N 77.59°E" />
                        <TextAreaBlock label="NARRATIVE NOTES" icon={FileText} value={clinical.notes} onChange={(e: any) => setClinical({...clinical, notes: e.target.value})} placeholder="e.g. Found unresponsive at home, 30min onset" />
                    </div>

                    {/* LABS & ATTACHMENTS */}
                    <SectionHeader title="LABS & ATTACHMENTS" icon={FileText} />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <TextAreaBlock label="LAB RESULTS" icon={FileText} value={labs.results} onChange={(e: any) => setLabs({...labs, results: e.target.value})} placeholder="Name: value, one per line" />
                        
                        <div style={{ background: '#050505', padding: '1.5rem', border: '1px solid #1a1a1a' }}>
                            <label style={{ color: '#777', fontSize: '0.85rem', letterSpacing: '0.1em', fontWeight: 600, display: 'block', marginBottom: '1rem' }}>
                                <Upload size={14} style={{verticalAlign: 'text-bottom', marginRight: '6px', color: '#D13619'}}/> UPLOAD ECG / INJURY PHOTOS
                            </label>
                            
                            <input 
                                type="file" 
                                ref={fileInputRef} 
                                style={{ display: 'none' }} 
                                multiple 
                                accept="image/*,application/pdf"
                                onChange={handleFileUpload}
                            />
                            
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <button 
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    style={{
                                        background: 'transparent',
                                        border: '1px solid #D13619',
                                        color: '#D13619',
                                        padding: '0.8rem 1.5rem',
                                        fontSize: '1rem',
                                        fontFamily: 'monospace',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        transition: 'background 0.2s'
                                    }}
                                >
                                    <Upload size={18} /> SELECT FILES
                                </button>
                                <span style={{ color: '#555', fontSize: '0.9rem', fontFamily: 'monospace' }}>
                                    PNG, JPG, PDF (Auto Base64 Encoded)
                                </span>
                            </div>

                            {attachments.length > 0 && (
                                <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    {attachments.map((file, i) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#111', padding: '0.8rem', border: '1px solid #333' }}>
                                            <FileText size={16} color="#777" />
                                            <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '0.9rem' }}>{file.filename}</span>
                                            <span style={{ color: '#555', fontSize: '0.8rem', marginLeft: 'auto' }}>{(file.data_b64.length * 0.75 / 1024).toFixed(1)} KB</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <button type="submit" disabled={isSubmitting} style={{ 
                        background: '#D13619', 
                        color: '#fff', 
                        border: 'none', 
                        padding: '2rem', 
                        fontSize: '1.5rem', 
                        letterSpacing: '0.2em', 
                        fontWeight: 900, 
                        fontFamily: '"Impact", "Arial Black", sans-serif',
                        cursor: 'pointer',
                        marginTop: '3rem',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: '15px'
                    }}>
                        <Send size={24} />
                        {isSubmitting ? "TRANSMITTING..." : "TRANSMIT TO HOSPITAL"}
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

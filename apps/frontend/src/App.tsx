import { Routes, Route, Link } from 'react-router-dom';
import Ambulance from './pages/Ambulance';
import Hospital from './pages/Hospital';
import { Ambulance as AmbulanceIcon, Activity } from 'lucide-react';

function App() {
  return (
    <>
      <nav style={{ background: 'rgba(21, 27, 35, 0.8)', borderBottom: '1px solid #21262d', padding: '1rem 2rem', display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontWeight: 700, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity color="#388bfd" />
          MedConnect
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <Link to="/ambulance" style={{ color: '#e6edf3', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.8 }} onMouseOver={e => e.currentTarget.style.opacity = "1"} onMouseOut={e => e.currentTarget.style.opacity = "0.8"}>
            <AmbulanceIcon size={18} /> Ambulance Panel
          </Link>
          <Link to="/hospital" style={{ color: '#e6edf3', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.8 }} onMouseOver={e => e.currentTarget.style.opacity = "1"} onMouseOut={e => e.currentTarget.style.opacity = "0.8"}>
            <Activity size={18} /> Hospital Dashboard
          </Link>
        </div>
      </nav>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<Ambulance />} />
          <Route path="/ambulance" element={<Ambulance />} />
          <Route path="/hospital" element={<Hospital />} />
        </Routes>
      </main>
    </>
  );
}

export default App;

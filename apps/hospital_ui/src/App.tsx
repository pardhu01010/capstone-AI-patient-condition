import Hospital from './pages/Hospital';
import { Activity } from 'lucide-react';

function App() {
  return (
    <>
      <nav style={{ background: 'rgba(21, 27, 35, 0.8)', borderBottom: '1px solid #21262d', padding: '1rem 2rem', display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontWeight: 700, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity color="#00c48c" />
          MedConnect - Hospital Dashboard
        </div>
      </nav>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Hospital />
      </main>
    </>
  );
}

export default App;

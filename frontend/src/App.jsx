import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import OptimizerTab from './components/OptimizerTab';
import SessionTab from './components/SessionTab';
import LogsTab from './components/LogsTab';
import { fetchProfile, login } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('optimizer');
  const [profile, setProfile] = useState(null);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadProfile = async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchProfile();
      setProfile(data);
      if (!selectedVehicle && data.activeVehicle) {
        setSelectedVehicle(data.activeVehicle);
      }
    } catch (err) {
      setProfile({ connected: false });
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleLogin = async (phone, pswd) => {
    await login(phone, pswd);
    await loadProfile();
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans">
      
      {/* Top persistent header */}
      <Header
        profile={profile}
        selectedVehicle={selectedVehicle}
        onSelectVehicle={setSelectedVehicle}
        onRefresh={loadProfile}
        onLogin={handleLogin}
        isRefreshing={isRefreshing}
      />

      {/* Main container */}
      <div className="max-w-6xl w-full mx-auto px-6 py-6 space-y-6 flex-1 flex flex-col">
        
        {/* Navigation toolbar */}
        <nav className="flex items-center gap-1 border-b border-zinc-800 pb-2 text-xs font-mono">
          <button
            onClick={() => setActiveTab('optimizer')}
            className={`px-3 py-1.5 rounded transition cursor-pointer ${
              activeTab === 'optimizer'
                ? 'bg-zinc-800 text-zinc-100 font-semibold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
          >
            OPTIMIZER & CHECKOUT
          </button>

          <button
            onClick={() => setActiveTab('session')}
            className={`px-3 py-1.5 rounded transition cursor-pointer ${
              activeTab === 'session'
                ? 'bg-zinc-800 text-zinc-100 font-semibold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
          >
            ACTIVE SESSION
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3 py-1.5 rounded transition cursor-pointer ${
              activeTab === 'logs'
                ? 'bg-zinc-800 text-zinc-100 font-semibold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
          >
            TELEMETRY LOGS
          </button>
        </nav>

        {/* View switch */}
        <main className="flex-1">
          {activeTab === 'optimizer' && (
            <OptimizerTab
              selectedVehicle={selectedVehicle}
              onSchedulerStarted={() => setActiveTab('session')}
            />
          )}

          {activeTab === 'session' && (
            <SessionTab selectedVehicle={selectedVehicle} />
          )}

          {activeTab === 'logs' && <LogsTab />}
        </main>

        {/* Footer */}
        <footer className="pt-6 pb-2 border-t border-zinc-900 text-zinc-600 text-[11px] font-mono flex items-center justify-between">
          <span>PAYBYPHONE BUYER DESK</span>
          <span>FASTAPI + REACT WORKBENCH</span>
        </footer>

      </div>
    </div>
  );
}

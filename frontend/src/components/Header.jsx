import React, { useState, useEffect, useRef } from 'react';
import { RotateCw, SlidersHorizontal, Check, ChevronDown, Car } from 'lucide-react';

export default function Header({
  profile,
  selectedVehicle,
  onSelectVehicle,
  onRefresh,
  onLogin,
  isRefreshing,
}) {
  const [showConfig, setShowConfig] = useState(false);
  const [showVehicles, setShowVehicles] = useState(false);
  const [phone, setPhone] = useState(profile?.phone || '33634182730');
  const [pswd, setPswd] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const vehicleDropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (vehicleDropdownRef.current && !vehicleDropdownRef.current.contains(event.target)) {
        setShowVehicles(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await onLogin(phone, pswd);
      setShowConfig(false);
      setPswd('');
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isConnected = Boolean(profile?.connected);
  const activePlate = selectedVehicle || profile?.activeVehicle || '—';
  const vehiclesList = profile?.vehicles || [];

  return (
    <>
      <header className="border-b border-zinc-800 bg-zinc-950 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* System identity */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold tracking-wider text-zinc-100 uppercase">
              PayByPhone Buyer
            </span>
            <span className="text-[10px] font-mono text-zinc-600">/</span>
            <span className="text-[11px] font-mono text-zinc-500">v1.1</span>
          </div>

          <div className="flex items-center gap-1.5 pl-3 border-l border-zinc-800 text-[11px] font-mono">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
            <span className={isConnected ? 'text-zinc-400' : 'text-amber-400'}>
              {isConnected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
        </div>

        {/* Account metadata bar */}
        <div className="flex items-center gap-4 text-xs font-mono">
          {isConnected ? (
            <div className="hidden sm:flex items-center gap-4 text-zinc-400">
              <div>
                <span className="text-zinc-600 mr-1.5">USR</span>
                <span className="text-zinc-200">+{profile?.phone}</span>
              </div>
              <span className="text-zinc-800">|</span>
              
              {/* Interactive Vehicle Switcher */}
              <div className="relative" ref={vehicleDropdownRef}>
                <button
                  type="button"
                  onClick={() => setShowVehicles(!showVehicles)}
                  className="flex items-center gap-1 hover:text-zinc-100 transition cursor-pointer select-none group"
                  title="Click to switch vehicle for checkout"
                >
                  <span className="text-zinc-600 group-hover:text-zinc-400 transition">VEH</span>
                  <span className="text-zinc-200 font-semibold border-b border-dotted border-zinc-500 group-hover:border-zinc-300 transition">
                    {activePlate}
                  </span>
                  <ChevronDown size={11} className="text-zinc-500 group-hover:text-zinc-300 ml-0.5" />
                </button>

                {showVehicles && (
                  <div className="absolute right-0 top-full mt-2 w-64 bg-zinc-900 border border-zinc-800 rounded-md shadow-2xl p-2 z-50 font-mono text-xs animate-in fade-in zoom-in-95 duration-100">
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 uppercase tracking-wider px-2 py-1 border-b border-zinc-800 mb-1">
                      <span>Select Vehicle</span>
                      <span>{vehiclesList.length} registered</span>
                    </div>

                    {vehiclesList.length > 0 ? (
                      <div className="space-y-1">
                        {vehiclesList.map((v) => {
                          const isSelected = activePlate === v.licensePlate;
                          return (
                            <button
                              key={v.licensePlate}
                              type="button"
                              onClick={() => {
                                onSelectVehicle(v.licensePlate);
                                setShowVehicles(false);
                              }}
                              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded transition text-left cursor-pointer ${
                                isSelected
                                  ? 'bg-zinc-800 text-zinc-100 font-semibold'
                                  : 'hover:bg-zinc-800/60 text-zinc-300'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <Car size={13} className={isSelected ? 'text-zinc-200' : 'text-zinc-500'} />
                                <div>
                                  <div className="font-mono">{v.licensePlate}</div>
                                  <div className="text-[10px] text-zinc-500 font-sans">
                                    {v.type || 'Standard'}
                                  </div>
                                </div>
                              </div>
                              {isSelected && <Check size={13} className="text-emerald-400" />}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="p-2 text-zinc-500 text-[11px]">
                        No vehicles found on account.
                      </div>
                    )}
                  </div>
                )}
              </div>

              <span className="text-zinc-800">|</span>
              <div>
                <span className="text-zinc-600 mr-1.5">PAY</span>
                <span className="text-zinc-200">{profile?.activeCard || '—'}</span>
              </div>
            </div>
          ) : (
            <span className="text-zinc-500 italic">Credentials required</span>
          )}

          <div className="flex items-center gap-1.5 pl-2 border-l border-zinc-800">
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh data"
              className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition disabled:opacity-40 cursor-pointer"
            >
              <RotateCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => setShowConfig(!showConfig)}
              title="Account settings"
              className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
            >
              <SlidersHorizontal size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* Discrete credentials drawer */}
      {showConfig && (
        <div className="border-b border-zinc-800 bg-zinc-900/60 px-6 py-4">
          <div className="max-w-2xl">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-zinc-300">
                PayByPhone Account Configuration
              </span>
              <button
                onClick={() => setShowConfig(false)}
                className="text-[11px] text-zinc-500 hover:text-zinc-300 font-mono cursor-pointer"
              >
                Close
              </button>
            </div>

            {error && (
              <div className="mb-3 p-2 text-xs bg-red-950/40 border border-red-900/50 text-red-300 rounded font-mono">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[180px]">
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="33634182730"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600"
                />
              </div>
              <div className="flex-1 min-w-[180px]">
                <input
                  type="password"
                  value={pswd}
                  onChange={(e) => setPswd(e.target.value)}
                  placeholder="Password"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="bg-zinc-100 hover:bg-zinc-200 text-zinc-950 px-3.5 py-1.5 rounded text-xs font-medium transition disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? 'Connecting...' : 'Save'}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

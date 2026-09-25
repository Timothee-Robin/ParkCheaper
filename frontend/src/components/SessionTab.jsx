import React, { useState, useEffect } from 'react';
import { fetchActiveSession, fetchSchedulerStatus, stopScheduler } from '../services/api';

export default function SessionTab({ selectedVehicle }) {
  const [activeSession, setActiveSession] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [isStopping, setIsStopping] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [session, sched] = await Promise.all([
        fetchActiveSession(undefined, selectedVehicle).catch(() => ({ hasActiveSession: false })),
        fetchSchedulerStatus().catch(() => ({ status: 'IDLE' })),
      ]);
      setActiveSession(session);
      setSchedulerStatus(sched);
      if (session.hasActiveSession && session.secondsRemaining > 0) {
        setSecondsRemaining(session.secondsRemaining);
      } else if (sched.secondsRemaining > 0) {
        setSecondsRemaining(sched.secondsRemaining);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [selectedVehicle]);

  useEffect(() => {
    if (secondsRemaining <= 0) return;
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [secondsRemaining]);

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await stopScheduler();
      await loadData();
    } catch (err) {
      alert('Stop error: ' + err.message);
    } finally {
      setIsStopping(false);
    }
  };

  const formatCountdown = (secs) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const isRunning =
    schedulerStatus?.status === 'RUNNING' || schedulerStatus?.status === 'WAITING_NEXT_TICKET';

  return (
    <div className="space-y-6">
      
      {/* Session telemetry card */}
      <div className="border border-zinc-800 bg-zinc-900/30 rounded-md p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          
          <div className="space-y-2">
            <div className="flex items-center gap-3 text-xs font-mono">
              <span
                className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${
                  activeSession?.hasActiveSession
                    ? 'border-emerald-800/60 bg-emerald-950/20 text-emerald-400'
                    : 'border-zinc-800 bg-zinc-900 text-zinc-500'
                }`}
              >
                {activeSession?.hasActiveSession ? 'PAYBYPHONE SESSION ACTIVE' : 'NO ACTIVE SESSION DETECTED'}
              </span>

              <span className="text-zinc-600">/</span>

              <span className="text-zinc-400">
                SCHEDULER STATUS: <strong className="text-zinc-200">{schedulerStatus?.status || 'IDLE'}</strong>
              </span>

              {selectedVehicle && (
                <>
                  <span className="text-zinc-600">/</span>
                  <span className="text-zinc-500 font-mono">
                    VEH: <strong className="text-zinc-300">{selectedVehicle}</strong>
                  </span>
                </>
              )}
            </div>

            <div className="flex items-baseline gap-4 pt-1">
              <div className="text-4xl font-mono font-bold tracking-tight text-zinc-100">
                {formatCountdown(secondsRemaining)}
              </div>
              <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
                time remaining until expiration
              </span>
            </div>

            <div className="text-xs font-mono text-zinc-400">
              {activeSession?.expireDtUtc ? (
                <span>
                  Server expiration:{' '}
                  <span className="text-zinc-200 font-semibold">
                    {new Date(activeSession.expireDtUtc).toLocaleTimeString()}
                  </span>
                </span>
              ) : (
                <span className="text-zinc-600">No active session recorded for this vehicle.</span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              disabled={isRefreshing}
              className="border border-zinc-800 hover:border-zinc-700 bg-zinc-950 text-zinc-300 px-3 py-1.5 rounded text-xs font-mono transition cursor-pointer disabled:opacity-50"
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>

            {isRunning && (
              <button
                onClick={handleStop}
                disabled={isStopping}
                className="bg-red-950/40 hover:bg-red-900/60 border border-red-800/50 text-red-300 px-3.5 py-1.5 rounded text-xs font-mono font-medium transition cursor-pointer"
              >
                {isStopping ? 'Stopping...' : 'Stop Scheduler'}
              </button>
            )}
          </div>

        </div>
      </div>

      {/* History table */}
      <div className="border border-zinc-800 bg-zinc-900/30 rounded-md p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-300">
            Executed Tickets Log
          </h3>
          <span className="text-[11px] font-mono text-zinc-500">
            {schedulerStatus?.history?.length || 0} transaction(s)
          </span>
        </div>

        {schedulerStatus?.history && schedulerStatus.history.length > 0 ? (
          <div className="border border-zinc-800 rounded overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-zinc-950 text-zinc-500 border-b border-zinc-800 text-[11px]">
                <tr>
                  <th className="py-2 px-3 font-normal">TICKET</th>
                  <th className="py-2 px-3 font-normal">DURATION</th>
                  <th className="py-2 px-3 font-normal">TIMESTAMP</th>
                  <th className="py-2 px-3 font-normal">AMOUNT</th>
                  <th className="py-2 px-3 text-right font-normal">3DS STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 bg-zinc-950/20">
                {schedulerStatus.history.map((item, idx) => (
                  <tr key={idx} className="hover:bg-zinc-850/40 transition">
                    <td className="py-2.5 px-3 text-zinc-300">#{item.ticketIndex}</td>
                    <td className="py-2.5 px-3 text-zinc-100 font-semibold">{item.duration} min</td>
                    <td className="py-2.5 px-3 text-zinc-500">{new Date(item.boughtAt).toLocaleTimeString()}</td>
                    <td className="py-2.5 px-3 text-zinc-300">€{Number(item.cost).toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-right text-emerald-400 text-[11px]">
                      {item.status || 'VALID'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-zinc-600 font-mono text-xs">
            No purchase history available for this session.
          </div>
        )}
      </div>

    </div>
  );
}

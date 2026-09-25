import React, { useState } from 'react';
import { calculateOptimization, buyTicket, startScheduler } from '../services/api';

export default function OptimizerTab({ selectedVehicle, onSchedulerStarted }) {
  const [zone, setZone] = useState('94802');
  const [mode, setMode] = useState('times');
  const [startTime, setStartTime] = useState('14:00');
  const [endTime, setEndTime] = useState('17:30');
  const [durationMinutes, setDurationMinutes] = useState(210);
  const [allowFreeQuota, setAllowFreeQuota] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleCalculate = async (e) => {
    e?.preventDefault();
    setIsLoading(true);
    setError(null);
    setFeedback(null);

    try {
      const data = await calculateOptimization({
        zone,
        startTime: mode === 'times' ? startTime : null,
        endTime: mode === 'times' ? endTime : null,
        durationMinutes: mode === 'duration' ? durationMinutes : null,
        allowFreeQuota,
        licensePlate: selectedVehicle,
      });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Error calculating tariff optimization.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBuySingle = async (dur) => {
    setActionLoading(true);
    setFeedback(null);
    try {
      const res = await buyTicket({ zone, durationMinutes: dur, licensePlate: selectedVehicle });
      setFeedback({
        type: 'success',
        text: `Ticket of ${dur} min purchased for ${selectedVehicle || 'default vehicle'}. 3DS status: ${res.result?.status || 'OK'}.`,
      });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to purchase ticket.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartScheduler = async (tickets) => {
    setActionLoading(true);
    setFeedback(null);
    try {
      await startScheduler({ zone, ticketList: tickets, licensePlate: selectedVehicle });
      if (onSchedulerStarted) onSchedulerStarted();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Could not start scheduler.' });
      setActionLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      
      {/* Parameter sidebar (4 cols) */}
      <div className="lg:col-span-4 border border-zinc-800 bg-zinc-900/30 p-5 rounded-md space-y-5">
        <div>
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-300">
            Calculation Parameters
          </h2>
          <p className="text-[11px] text-zinc-500 mt-0.5">
            Configure parking zone code and target parking duration.
          </p>
        </div>

        <form onSubmit={handleCalculate} className="space-y-4 text-xs font-mono">
          <div>
            <label className="block text-[11px] text-zinc-400 uppercase tracking-wider mb-1.5">
              Active Vehicle
            </label>
            <div className="flex items-center justify-between bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-zinc-200">
              <span className="font-semibold text-zinc-100">{selectedVehicle || 'Default'}</span>
              <span className="text-[10px] text-zinc-500">(Click VEH in header to switch)</span>
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-zinc-400 uppercase tracking-wider mb-1.5">
              Zone Code
            </label>
            <input
              type="text"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              required
              className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-zinc-100 focus:outline-none focus:border-zinc-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between text-[11px] text-zinc-400 uppercase tracking-wider mb-1.5">
              <span>Input Mode</span>
              <div className="flex gap-2 text-zinc-500 font-sans">
                <button
                  type="button"
                  onClick={() => setMode('times')}
                  className={`cursor-pointer ${mode === 'times' ? 'text-zinc-200 underline' : 'hover:text-zinc-400'}`}
                >
                  Time Range
                </button>
                <span>/</span>
                <button
                  type="button"
                  onClick={() => setMode('duration')}
                  className={`cursor-pointer ${mode === 'duration' ? 'text-zinc-200 underline' : 'hover:text-zinc-400'}`}
                >
                  Duration
                </button>
              </div>
            </div>

            {mode === 'times' ? (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="block text-[10px] text-zinc-500 mb-1">FROM</span>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    required
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div>
                  <span className="block text-[10px] text-zinc-500 mb-1">TO</span>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    required
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-500"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-500">Requested Duration</span>
                  <span className="text-zinc-200 font-semibold">{durationMinutes} min</span>
                </div>
                <input
                  type="range"
                  min="15"
                  max="480"
                  step="15"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="w-full accent-zinc-200 bg-zinc-800 cursor-pointer"
                />
              </div>
            )}
          </div>

          <div className="pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={allowFreeQuota}
                onChange={(e) => setAllowFreeQuota(e.target.checked)}
                className="rounded border-zinc-800 bg-zinc-950 text-zinc-100 focus:ring-0 focus:outline-none"
              />
              <span className="text-[11px] text-zinc-400 font-sans">
                Include municipal free quota
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-medium py-2 rounded text-xs transition disabled:opacity-50 cursor-pointer"
          >
            {isLoading ? 'Calculating...' : 'Calculate Optimization'}
          </button>
        </form>

        {error && (
          <div className="p-3 text-xs font-mono bg-red-950/40 border border-red-900/50 text-red-300 rounded">
            {error}
          </div>
        )}
      </div>

      {/* Main Execution Canvas (8 cols) */}
      <div className="lg:col-span-8 space-y-6">
        {result ? (
          <div className="border border-zinc-800 bg-zinc-900/30 rounded-md overflow-hidden">
            
            {/* KPI strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 border-b border-zinc-800 divide-x divide-zinc-800 text-xs font-mono">
              <div className="p-3.5">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Total Duration</div>
                <div className="text-zinc-100 font-semibold mt-1">
                  {Math.floor(result.coveredMinutes / 60)}h {result.coveredMinutes % 60}m
                </div>
              </div>
              <div className="p-3.5">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Single Ticket Cost</div>
                <div className="text-zinc-400 mt-1 line-through">
                  €{(result.singleTicketCost ?? result.standardCost).toFixed(2)}
                </div>
              </div>
              <div className="p-3.5">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Optimized Cost</div>
                <div className="text-emerald-400 font-semibold mt-1">
                  €{result.totalCost.toFixed(2)}
                </div>
              </div>
              <div className="p-3.5">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Total Savings</div>
                <div className="text-emerald-400 font-semibold mt-1">
                  -€{result.savingsAmount.toFixed(2)} ({result.savingsPercent}%)
                </div>
              </div>
            </div>

            {/* Structured Table */}
            <div className="p-4 sm:p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                  Execution Breakdown ({result.tickets.length} sequential tickets)
                </span>
                <span className="text-[11px] font-mono text-zinc-500">
                  Zone {result.zone} &bull; Plate {result.licensePlate || selectedVehicle || '—'}
                </span>
              </div>

              <div className="border border-zinc-800 rounded overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-zinc-950/80 text-zinc-500 border-b border-zinc-800 text-[11px]">
                    <tr>
                      <th className="py-2 px-3 w-12 font-normal">#</th>
                      <th className="py-2 px-3 font-normal">DURATION</th>
                      <th className="py-2 px-3 font-normal">TYPE</th>
                      <th className="py-2 px-3 text-right font-normal">STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 bg-zinc-950/30">
                    {result.tickets.map((dur, idx) => {
                      const isPromo = idx === 0 && result.hasPromo;
                      return (
                        <tr key={idx} className="hover:bg-zinc-850/40 transition">
                          <td className="py-2.5 px-3 text-zinc-500 font-normal">
                            0{idx + 1}
                          </td>
                          <td className="py-2.5 px-3 text-zinc-200 font-medium">
                            {dur} min
                          </td>
                          <td className="py-2.5 px-3">
                            {isPromo ? (
                              <span className="text-emerald-400 font-normal">
                                Municipal free quota (€0.00)
                              </span>
                            ) : (
                              <span className="text-zinc-400 font-normal">
                                Optimized paid ticket
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-500 text-[11px]">
                            Pending
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {feedback && (
                <div
                  className={`p-2.5 text-xs font-mono rounded border ${
                    feedback.type === 'success'
                      ? 'bg-emerald-950/30 border-emerald-900/50 text-emerald-300'
                      : 'bg-red-950/30 border-red-900/50 text-red-300'
                  }`}
                >
                  {feedback.text}
                </div>
              )}

              {/* Action bar */}
              <div className="pt-3 border-t border-zinc-800 flex flex-wrap items-center justify-end gap-3">
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleBuySingle(result.tickets[0])}
                  className="border border-zinc-700 hover:border-zinc-500 text-zinc-200 px-3.5 py-1.5 rounded text-xs font-medium transition disabled:opacity-50 cursor-pointer"
                >
                  Buy Ticket 01 ({result.tickets[0]} min)
                </button>

                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleStartScheduler(result.tickets)}
                  className="bg-zinc-100 hover:bg-zinc-200 text-zinc-950 px-4 py-1.5 rounded text-xs font-semibold transition disabled:opacity-50 cursor-pointer shadow-sm"
                >
                  Start Automatic Scheduler
                </button>
              </div>

            </div>
          </div>
        ) : (
          <div className="border border-zinc-800 border-dashed rounded-md p-12 text-center text-zinc-600 font-mono text-xs">
            Select a zone and duration, then run calculation to generate the optimized tariff plan.
          </div>
        )}
      </div>

    </div>
  );
}

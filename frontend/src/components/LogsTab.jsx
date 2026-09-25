import React, { useState, useEffect, useRef } from 'react';
import { createLogsWebSocket } from '../services/api';

export default function LogsTab() {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const logContainerRef = useRef(null);

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connect = () => {
      ws = createLogsWebSocket(
        (event) => {
          setIsConnected(true);
          if (event.type === 'INITIAL_STATE') {
            setLogs((prev) => [
              ...prev,
              {
                timestamp: new Date().toISOString(),
                level: 'INFO',
                message: `Event telemetry stream initialized. State: ${event.state?.status || 'IDLE'}`,
              },
            ]);
          } else {
            setLogs((prev) => [...prev, event]);
          }
        },
        () => {
          setIsConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        }
      );

      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const getLevelColor = (level) => {
    switch (level) {
      case 'SUCCESS':
        return 'text-emerald-400';
      case 'WARN':
        return 'text-amber-400';
      case 'ERROR':
        return 'text-red-400';
      default:
        return 'text-zinc-500';
    }
  };

  return (
    <div className="border border-zinc-800 bg-zinc-900/30 rounded-md overflow-hidden">
      {/* Terminal toolbar */}
      <div className="border-b border-zinc-800 bg-zinc-950 px-4 py-2.5 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="text-zinc-300 font-semibold uppercase tracking-wider text-[11px]">
            Live Telemetry Stream
          </span>
          <span className="text-zinc-700">|</span>
          <span className={isConnected ? 'text-zinc-500 text-[11px]' : 'text-amber-500 text-[11px]'}>
            {isConnected ? 'WS CONNECTED' : 'RECONNECTING...'}
          </span>
        </div>

        <button
          onClick={() => setLogs([])}
          className="text-zinc-500 hover:text-zinc-300 text-[11px] font-mono cursor-pointer"
        >
          Clear Console
        </button>
      </div>

      {/* Terminal output */}
      <div
        ref={logContainerRef}
        className="bg-zinc-950 p-4 h-[420px] overflow-y-auto font-mono text-xs space-y-1.5 select-text"
      >
        {logs.length > 0 ? (
          logs.map((log, i) => (
            <div key={i} className="flex items-start gap-2.5 leading-relaxed text-zinc-300">
              <span className="text-zinc-600 shrink-0 select-none">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`shrink-0 font-semibold select-none ${getLevelColor(log.level)}`}>
                [{log.level || 'INFO'}]
              </span>
              <span className="break-all">{log.message}</span>
            </div>
          ))
        ) : (
          <div className="h-full flex items-center justify-center text-zinc-700 text-xs">
            Awaiting telemetry events...
          </div>
        )}
      </div>
    </div>
  );
}

const API_BASE = '/api';

export async function fetchProfile() {
  const res = await fetch(`${API_BASE}/auth/profile`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function login(phone, pswd) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, pswd }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new Error(err.detail || 'Authentication failed');
  }
  return res.json();
}

export async function fetchZoneInfo(zoneId, licensePlate) {
  const url = new URL(`${API_BASE}/zones/${zoneId}/info`, window.location.origin);
  if (licensePlate) url.searchParams.set('licensePlate', licensePlate);
  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Zone not found' }));
    throw new Error(err.detail || 'Zone error');
  }
  return res.json();
}

export async function calculateOptimization({ zone, startTime, endTime, durationMinutes, allowFreeQuota, licensePlate }) {
  const payload = { zone, allowFreeQuota, licensePlate };
  if (startTime && endTime) {
    payload.startTime = startTime;
    payload.endTime = endTime;
  } else if (durationMinutes) {
    payload.durationMinutes = Number(durationMinutes);
  }

  const res = await fetch(`${API_BASE}/optimizer/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Optimization error' }));
    throw new Error(err.detail || 'Error calculating tariff optimization');
  }
  return res.json();
}

export async function fetchActiveSession(zone = '94802', licensePlate = null) {
  const url = new URL(`${API_BASE}/session/active`, window.location.origin);
  if (zone) url.searchParams.set('zone', zone);
  if (licensePlate) url.searchParams.set('licensePlate', licensePlate);
  
  const res = await fetch(url.toString());
  if (!res.ok) return { hasActiveSession: false };
  return res.json();
}

export async function buyTicket({ zone, durationMinutes, licensePlate }) {
  const res = await fetch(`${API_BASE}/checkout/ticket`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone, durationMinutes, licensePlate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ticket purchase error' }));
    throw new Error(err.detail || 'Ticket purchase error');
  }
  return res.json();
}

export async function startScheduler({ zone, ticketList, licensePlate }) {
  const res = await fetch(`${API_BASE}/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone, ticketList, licensePlate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Scheduler start error' }));
    throw new Error(err.detail || 'Scheduler start error');
  }
  return res.json();
}

export async function fetchSchedulerStatus() {
  const res = await fetch(`${API_BASE}/session/status`);
  if (!res.ok) return { status: 'IDLE' };
  return res.json();
}

export async function stopScheduler() {
  const res = await fetch(`${API_BASE}/session/stop`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Could not stop scheduler');
  return res.json();
}

export function createLogsWebSocket(onEvent, onError) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host; // Uses Vite proxy
  const socketUrl = `${protocol}//${host}/api/ws/logs`;

  const ws = new WebSocket(socketUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
    } catch (err) {
      console.error('Error parsing WS message:', err);
    }
  };

  ws.onerror = (err) => {
    if (onError) onError(err);
  };

  return ws;
}

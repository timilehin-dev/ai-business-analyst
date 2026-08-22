import { useEffect, useRef, useState } from 'react';

/**
 * Live updates over the backend WebSocket (/ws/updates).
 *
 * The server pushes briefings and connector-sync results, so the dashboard
 * reflects overnight work without the user reloading. Reconnects with
 * exponential backoff because a self-hosted backend restarts routinely
 * (config changes re-initialize the analyst), and a dead socket would
 * otherwise silently stop all proactive updates.
 */

export type LiveMessage =
  | { type: 'connected'; analyst_ready: boolean }
  | { type: 'briefing'; briefing: unknown }
  | { type: 'sync'; results: Record<string, number> };

const INITIAL_RETRY_MS = 1000;
const MAX_RETRY_MS = 30000;
const HEARTBEAT_MS = 25000;

export function useLiveUpdates(onMessage?: (message: LiveMessage) => void) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<LiveMessage | null>(null);

  // Held in refs so reconnection scheduling never re-triggers the effect.
  const handlerRef = useRef(onMessage);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(INITIAL_RETRY_MS);
  const timersRef = useRef<{ retry?: number; heartbeat?: number }>({});
  const closedRef = useRef(false);

  handlerRef.current = onMessage;

  useEffect(() => {
    closedRef.current = false;

    const clearTimers = () => {
      if (timersRef.current.retry) window.clearTimeout(timersRef.current.retry);
      if (timersRef.current.heartbeat) window.clearInterval(timersRef.current.heartbeat);
      timersRef.current = {};
    };

    const connect = () => {
      if (closedRef.current) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      let socket: WebSocket;
      try {
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/updates`);
      } catch {
        scheduleRetry();
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        setConnected(true);
        retryRef.current = INITIAL_RETRY_MS;
        // Keeps intermediaries from dropping an idle connection.
        timersRef.current.heartbeat = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send('ping');
        }, HEARTBEAT_MS);
      };

      socket.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const message = JSON.parse(event.data) as LiveMessage;
          setLastMessage(message);
          handlerRef.current?.(message);
        } catch {
          // Ignore non-JSON frames rather than tearing down the socket.
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (timersRef.current.heartbeat) {
          window.clearInterval(timersRef.current.heartbeat);
          timersRef.current.heartbeat = undefined;
        }
        scheduleRetry();
      };

      socket.onerror = () => socket.close();
    };

    const scheduleRetry = () => {
      if (closedRef.current) return;
      const delay = retryRef.current;
      retryRef.current = Math.min(delay * 2, MAX_RETRY_MS);
      timersRef.current.retry = window.setTimeout(connect, delay);
    };

    connect();

    return () => {
      closedRef.current = true;
      clearTimers();
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  return { connected, lastMessage };
}

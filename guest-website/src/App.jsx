import React, { useEffect, useState } from 'react';

import {
  LiveKitRoom,
  VideoConference
} from '@livekit/components-react';

function App() {
  const parts = window.location.pathname.split('/').filter(Boolean);

  const mode = parts[0];
  const ceremonyId = parts[1];

  const isBroadcaster = mode === 'broadcast';

  const [apiBase, setApiBase] = useState('');
  const [token, setToken] = useState('');
  const [serverUrl, setServerUrl] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [manualToken, setManualToken] = useState('');
  const [manualServer, setManualServer] = useState('');

  useEffect(() => {
    if (isBroadcaster || !apiBase || !ceremonyId) return;

    let cancelled = false;

    async function joinAsViewer() {
      setLoading(true);
      setError('');

      try {
        const response = await fetch(
          `${apiBase.replace(/\/$/, '')}/api/ceremonies/${ceremonyId}/token?role=viewer`,
          { method: 'POST' }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Unable to join ceremony');
        }

        if (!cancelled) {
          setToken(data.token);
          setServerUrl(data.server_url);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    joinAsViewer();

    return () => {
      cancelled = true;
    };
  }, [apiBase, ceremonyId, isBroadcaster]);

  if (!ceremonyId || !['live', 'broadcast'].includes(mode)) {
    return (
      <main className="page">
        <h1>Wedding Live</h1>
        <p>Invalid ceremony link.</p>
      </main>
    );
  }

  if (!isBroadcaster && !apiBase) {
    return (
      <main className="page">
        <h1>Wedding Live</h1>
        <p>Connect to the ceremony server.</p>

        <input
          placeholder="Backend URL (https://...)"
          value={apiBase}
          onChange={e => setApiBase(e.target.value)}
        />
      </main>
    );
  }

  if (isBroadcaster && !token) {
    return (
      <main className="page">
        <h1>Wedding Live</h1>
        <p>Broadcaster access</p>

        <label>LiveKit server URL</label>
        <input
          placeholder="wss://your-project.livekit.cloud"
          value={manualServer}
          onChange={e => setManualServer(e.target.value)}
        />

        <label>Broadcaster token</label>
        <textarea
          placeholder="Paste broadcaster token here"
          value={manualToken}
          onChange={e => setManualToken(e.target.value)}
        />

        <button
          onClick={() => {
            if (!manualToken || !manualServer) {
              setError('Enter both values');
              return;
            }

            setToken(manualToken.trim());
            setServerUrl(manualServer.trim());
            setError('');
          }}
        >
          Start Broadcasting
        </button>

        {error && <p className="error">{error}</p>}

        <p className="hint">
          Generate your broadcaster token through the protected backend API.
          Never put your admin password in this website.
        </p>
      </main>
    );
  }

  if (!token || !serverUrl) {
    return (
      <main className="page">
        <h1>Wedding Live</h1>
        <p>{loading ? 'Connecting...' : error || 'Waiting to connect'}</p>
        {error && (
          <button onClick={() => window.location.reload()}>
            Retry
          </button>
        )}
      </main>
    );
  }

  return (
    <main className="stream-page">
      <header>
        <span className="live-dot"></span>
        {isBroadcaster ? 'BROADCASTER' : 'LIVE CEREMONY'}
      </header>

      <div className="video-container" data-lk-theme="default">
        <LiveKitRoom
          key={token}
          serverUrl={serverUrl}
          token={token}
          connect={true}
          video={isBroadcaster}
          audio={isBroadcaster}
          onError={err => setError(err.message)}
        >
          <VideoConference />
        </LiveKitRoom>
      </div>

      {error && <p className="error">{error}</p>}
    </main>
  );
}

export default App;

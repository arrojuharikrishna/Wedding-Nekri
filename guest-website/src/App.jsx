
import React, { useEffect, useState } from 'react';

import {
  LiveKitRoom,
  VideoConference,
  useRoomContext
} from '@livekit/components-react';

import { Track } from 'livekit-client';

const DEFAULT_API = 'https://scaling-cod-v75q95vrvqgf6p9j-8000.app.github.dev';

function LocalRecorder({ ceremonyId, apiBase, uploadToken }) {
  const room = useRoomContext();

  const [recording, setRecording] = useState(false);
  const [message, setMessage] = useState('Recorder ready');
  const [segmentCount, setSegmentCount] = useState(0);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);

  const recorderRef = React.useRef(null);
  const recordingRef = React.useRef(false);
  const segmentRef = React.useRef(0);
  const uploadQueueRef = React.useRef([]);
  const uploadingRef = React.useRef(false);

  const SEGMENT_DURATION_MS = 30 * 1000;

  const drainUploadQueue = async () => {
    if (uploadingRef.current) return;

    uploadingRef.current = true;

    try {
      while (uploadQueueRef.current.length > 0) {
        const item = uploadQueueRef.current[0];
        let uploaded = false;
        let lastError = '';

        for (let attempt = 1; attempt <= 3; attempt++) {
          try {
            setMessage(
              `Uploading segment ${item.number} (attempt ${attempt}/3)...`
            );

            const formData = new FormData();

            formData.append(
              'file',
              item.blob,
              `segment-${String(item.number).padStart(4, '0')}.webm`
            );

            const response = await fetch(
              `${apiBase.replace(/\/$/, '')}/api/ceremonies/${ceremonyId}/segments/${item.number}`,
              {
                method: 'POST',
                headers: {
                  Authorization: `Bearer ${uploadToken}`
                },
                body: formData
              }
            );

            const result = await response.json();

            if (!response.ok) {
              throw new Error(result.detail || 'Upload failed');
            }

            uploaded = true;
            break;

          } catch (error) {
            lastError = error.message;

            if (attempt < 3) {
              await new Promise(resolve => setTimeout(resolve, 2000));
            }
          }
        }

        if (!uploaded) {
          setMessage(
            `Segment ${item.number} upload failed: ${lastError}. Use Retry Uploads.`
          );
          break;
        }

        uploadQueueRef.current.shift();

        setUploadedCount(count => count + 1);
        setPendingCount(uploadQueueRef.current.length);

        setMessage(`Segment ${item.number} uploaded successfully`);
      }
    } finally {
      uploadingRef.current = false;
      setPendingCount(uploadQueueRef.current.length);
    }
  };

  const startSegment = (stream) => {
    if (!recordingRef.current) return;

    try {
      const mimeType = MediaRecorder.isTypeSupported(
        'video/webm;codecs=vp8,opus'
      )
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      const currentSegment = ++segmentRef.current;
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });

        if (blob.size > 0) {
          uploadQueueRef.current.push({
            number: currentSegment,
            blob
          });

          setPendingCount(uploadQueueRef.current.length);

          drainUploadQueue();
        }

        if (recordingRef.current) {
          setTimeout(() => startSegment(stream), 300);
        } else {
          setRecording(false);
          setMessage(
            `Recording stopped. ${segmentRef.current} segment(s) created.`
          );
        }
      };

      recorderRef.current = recorder;
      recorder.start();

      setSegmentCount(currentSegment);
      setMessage(`Recording segment ${currentSegment}`);

      setTimeout(() => {
        if (
          recordingRef.current &&
          recorder.state === 'recording'
        ) {
          recorder.stop();
        }
      }, SEGMENT_DURATION_MS);

    } catch (error) {
      recordingRef.current = false;
      setRecording(false);
      setMessage(`Recording error: ${error.message}`);
    }
  };

  const startRecording = () => {
    try {
      if (!uploadToken || !apiBase) {
        throw new Error('Upload configuration is missing');
      }

      const camera = room.localParticipant.getTrackPublication(
        Track.Source.Camera
      );

      const microphone = room.localParticipant.getTrackPublication(
        Track.Source.Microphone
      );

      const videoTrack = camera?.track?.mediaStreamTrack;
      const audioTrack = microphone?.track?.mediaStreamTrack;

      if (!videoTrack || !audioTrack) {
        throw new Error('Camera or microphone track unavailable');
      }

      const stream = new MediaStream([
        videoTrack,
        audioTrack
      ]);

      segmentRef.current = 0;
      recordingRef.current = true;

      setSegmentCount(0);
      setUploadedCount(0);
      setRecording(true);

      startSegment(stream);

    } catch (error) {
      setMessage(error.message);
    }
  };

  const stopRecording = () => {
    recordingRef.current = false;

    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop();
    } else {
      setRecording(false);
      setMessage('Recording stopped.');
    }
  };

  return (
    <div style={{
      padding: 16,
      background: '#202020',
      color: 'white',
      textAlign: 'center'
    }}>
      <h3>Wedding Local Recorder</h3>

      <p>Segments created: {segmentCount}</p>
      <p>Successfully uploaded: {uploadedCount}</p>
      <p>Pending uploads: {pendingCount}</p>

      <button
        onClick={startRecording}
        disabled={recording}
      >
        Start Recording
      </button>

      <button
        onClick={stopRecording}
        disabled={!recording}
      >
        Stop Recording
      </button>

      <button
        onClick={drainUploadQueue}
        disabled={pendingCount === 0}
      >
        Retry Uploads
      </button>

      <p>{message}</p>
      <p>Test segment duration: 30 seconds</p>
    </div>
  );
}

function App() {
  const parts = window.location.pathname.split('/').filter(Boolean);

  const mode = parts[0];
  const ceremonyId = parts[1];

  const isBroadcaster = mode === 'broadcast';

  const [apiBase, setApiBase] = useState(DEFAULT_API);
  const [token, setToken] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [uploadToken, setUploadToken] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [manualToken, setManualToken] = useState('');
  const [manualServer, setManualServer] = useState('');
  const [manualUploadToken, setManualUploadToken] = useState('');

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
          placeholder="Backend URL"
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
          placeholder="Paste broadcaster token"
          value={manualToken}
          onChange={e => setManualToken(e.target.value)}
        />

        <label>Backend URL</label>
        <input
          value={apiBase}
          onChange={e => setApiBase(e.target.value)}
        />

        <label>Temporary Azure upload token</label>
        <textarea
          placeholder="Paste temporary upload token"
          value={manualUploadToken}
          onChange={e => setManualUploadToken(e.target.value)}
        />

        <button
          onClick={() => {
            if (
              !manualToken ||
              !manualServer ||
              !apiBase ||
              !manualUploadToken
            ) {
              setError('Fill in all four fields');
              return;
            }

            setToken(manualToken.trim());
            setServerUrl(manualServer.trim());
            setUploadToken(manualUploadToken.trim());
            setError('');
          }}
        >
          Start Broadcasting
        </button>

        {error && <p className="error">{error}</p>}

        <p className="hint">
          Use the temporary upload token generated by your backend.
          Never enter your permanent admin secret here.
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
          {isBroadcaster && (
            <LocalRecorder
              ceremonyId={ceremonyId}
              apiBase={apiBase}
              uploadToken={uploadToken}
            />
          )}

          <VideoConference />
        </LiveKitRoom>
      </div>

      {error && <p className="error">{error}</p>}
    </main>
  );
}

export default App;

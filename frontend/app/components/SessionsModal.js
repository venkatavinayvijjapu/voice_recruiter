'use client';
import { useState, useEffect } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SessionsModal({ token, onClose }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch(API + '/api/auth/sessions', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to fetch sessions');
        setSessions(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, [token]);

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.title}>My Login Sessions</h2>
          <button onClick={onClose} style={styles.closeBtn}>&times;</button>
        </div>
        
        {loading ? (
          <p>Loading sessions...</p>
        ) : error ? (
          <p style={styles.error}>{error}</p>
        ) : (
          <div style={styles.list}>
            {sessions.map(s => (
              <div key={s.id} style={styles.sessionItem}>
                <div>
                  <div style={styles.sessionDate}>
                    {new Date(s.created_at).toLocaleString()}
                  </div>
                  <div style={styles.sessionStatus}>
                    {s.is_active ? (
                      <span style={{color: '#10b981'}}>Active</span>
                    ) : (
                      <span style={{color: '#6b7280'}}>Expired/Logged Out</span>
                    )}
                  </div>
                </div>
                {s.is_current && <span style={styles.currentBadge}>Current Session</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000
  },
  modal: {
    backgroundColor: 'white',
    padding: '2rem',
    borderRadius: '12px',
    width: '90%',
    maxWidth: '500px',
    maxHeight: '80vh',
    overflowY: 'auto'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
    borderBottom: '1px solid #e5e7eb',
    paddingBottom: '1rem'
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
    color: '#111827'
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#6b7280'
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem'
  },
  sessionItem: {
    padding: '1rem',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  sessionDate: {
    fontWeight: '500',
    color: '#374151'
  },
  sessionStatus: {
    fontSize: '0.875rem',
    marginTop: '0.25rem'
  },
  currentBadge: {
    backgroundColor: '#dbeafe',
    color: '#1d4ed8',
    padding: '0.25rem 0.5rem',
    borderRadius: '9999px',
    fontSize: '0.75rem',
    fontWeight: '600'
  },
  error: {
    color: '#ef4444'
  }
};

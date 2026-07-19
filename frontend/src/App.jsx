# frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DocumentUpload from './components/DocumentUpload';
import Auth from './components/Auth';

const BASE_URL = 'http://localhost:8000/api/v1';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')));
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspace, setActiveWorkspace] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);

  // Fetch workspaces
  const fetchWorkspaces = async () => {
    if (!token) return;
    try {
      const response = await fetch(`${BASE_URL}/workspaces/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data);
        if (data.length > 0 && !activeWorkspace) {
          setActiveWorkspace(data[0].id || data[0]._id);
        }
      } else if (response.status === 401) {
        handleLogout();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Fetch chat history sessions
  const fetchSessions = async () => {
    if (!token || !activeWorkspace) return;
    try {
      const response = await fetch(`${BASE_URL}/chat/session/workspace/${activeWorkspace}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        // Normalize IDs
        const normalized = data.map(s => ({ ...s, id: s.id || s._id }));
        setChatSessions(normalized);
        if (normalized.length > 0) {
          setActiveSession(normalized[0].id);
        } else {
          setActiveSession(null);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (token) {
      fetchWorkspaces();
    }
  }, [token]);

  useEffect(() => {
    if (token && activeWorkspace) {
      fetchSessions();
    }
  }, [token, activeWorkspace]);

  const handleLoginSuccess = (newToken, newUser) => {
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setWorkspaces([]);
    setActiveWorkspace(null);
    setChatSessions([]);
    setActiveSession(null);
  };

  const handleCreateWorkspace = async (name) => {
    try {
      const response = await fetch(`${BASE_URL}/workspaces/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name })
      });
      if (response.ok) {
        const newWS = await response.json();
        setWorkspaces(prev => [...prev, newWS]);
        setActiveWorkspace(newWS.id || newWS._id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateSession = async () => {
    if (!activeWorkspace) return;
    try {
      const response = await fetch(`${BASE_URL}/chat/session?workspace_id=${activeWorkspace}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title: `Session #${chatSessions.length + 1}` })
      });
      if (response.ok) {
        const newSession = await response.json();
        setChatSessions(prev => [{ ...newSession, id: newSession.id || newSession._id }, ...prev]);
        setActiveSession(newSession.id || newSession._id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!token) {
    return <Auth BASE_URL={BASE_URL} onSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="w-screen h-screen flex bg-[var(--bg-primary)] overflow-hidden font-sans">
      
      {/* Sidebar */}
      <Sidebar
        workspaces={workspaces.map(w => ({ ...w, id: w.id || w._id }))}
        activeWorkspace={activeWorkspace}
        setActiveWorkspace={setActiveWorkspace}
        chatSessions={chatSessions}
        activeSession={activeSession}
        setActiveSession={setActiveSession}
        onCreateSession={handleCreateSession}
        onCreateWorkspace={handleCreateWorkspace}
        currentUser={user}
        onLogout={handleLogout}
      />

      {/* Main chat center */}
      <main className="flex-1 h-full flex flex-col min-w-0">
        <ChatArea
          activeSession={activeSession}
          activeWorkspace={activeWorkspace}
          authToken={token}
          BASE_URL={BASE_URL}
        />
      </main>

      {/* Right panel - document uploads list */}
      <section className="w-80 h-full border-l border-[var(--border-glass)] bg-[var(--bg-secondary)] shrink-0">
        <DocumentUpload
          activeWorkspace={activeWorkspace}
          authToken={token}
          BASE_URL={BASE_URL}
          onDocumentChange={fetchSessions} // Refresh sessions on document upload/deletion to reflect changes
        />
      </section>

    </div>
  );
}

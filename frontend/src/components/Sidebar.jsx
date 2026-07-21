// frontend/src/components/Sidebar.jsx
import React, { useState } from 'react';
import { Plus, MessageSquare, Folder, LogOut, User, Cpu, ChevronDown, Hash, Sun, Moon } from 'lucide-react';
import DecryptedText from './DecryptedText';

export default function Sidebar({
  workspaces = [],
  activeWorkspace = null,
  setActiveWorkspace = () => {},
  chatSessions = [],
  activeSession = null,
  setActiveSession = () => {},
  onCreateSession = () => {},
  onCreateWorkspace = () => {},
  currentUser = null,
  onLogout = () => {},
  theme = 'dark',
  toggleTheme = () => {}
}) {
  const [showWorkspaceForm, setShowWorkspaceForm] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  const activeWS = workspaces.find(w => w.id === activeWorkspace);

  const handleCreateWorkspace = (e) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    onCreateWorkspace(newWorkspaceName);
    setNewWorkspaceName('');
    setShowWorkspaceForm(false);
  };

  return (
    <aside
      className="flex flex-col h-screen shrink-0 border-r"
      style={{
        width: '260px',
        background: 'var(--bg-sidebar)',
        borderColor: 'var(--border-color)'
      }}
    >
      {/* Brand Header */}
      <div
        className="flex items-center justify-between px-5 py-4 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center rounded-xl shrink-0"
            style={{
              width: 34,
              height: 34,
              background: 'var(--text-primary)',
              color: 'var(--bg-main)',
              boxShadow: '0 0 14px var(--accent-glow)'
            }}
          >
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[15px] font-black tracking-tight leading-none" style={{ color: 'var(--text-primary)' }}>
              <DecryptedText text="KnowledgeOS" speed={50} animateOn="mount" />
            </div>
            <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              Enterprise RAG v1.0
            </div>
          </div>
        </div>

        {/* Theme Switcher Button */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl transition-all hover:opacity-80 cursor-pointer"
          style={{
            background: 'var(--accent-badge)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)'
          }}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-600" />}
        </button>
      </div>

      {/* Workspace Selector */}
      <div className="px-3 py-3 relative border-b" style={{ borderColor: 'var(--border-color)' }}>
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1.5 px-1" style={{ color: 'var(--text-muted)' }}>
          Workspace
        </div>
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-left text-sm font-medium transition-all cursor-pointer"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)'
          }}
        >
          <Folder className="w-4 h-4 shrink-0" style={{ color: 'var(--text-primary)' }} />
          <span className="flex-1 truncate">{activeWS ? activeWS.name : 'Select Workspace'}</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showDropdown ? 'rotate-180' : ''}`} style={{ color: 'var(--text-secondary)' }} />
        </button>

        {showDropdown && (
          <div
            className="absolute left-3 right-3 mt-1.5 rounded-xl p-1.5 z-50 overflow-y-auto max-h-52 shadow-2xl"
            style={{
              background: 'var(--bg-sidebar)',
              border: '1px solid var(--border-color)',
              backdropFilter: 'blur(20px)'
            }}
          >
            {workspaces.map(ws => (
              <button
                key={ws.id}
                onClick={() => {
                  setActiveWorkspace(ws.id);
                  setShowDropdown(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-all cursor-pointer ${
                  activeWorkspace === ws.id ? 'font-bold' : 'hover:opacity-80'
                }`}
                style={
                  activeWorkspace === ws.id
                    ? { background: 'var(--text-primary)', color: 'var(--bg-main)' }
                    : { color: 'var(--text-secondary)' }
                }
              >
                <Folder className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{ws.name}</span>
              </button>
            ))}
            <button
              onClick={() => {
                setShowWorkspaceForm(true);
                setShowDropdown(false);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 mt-1 rounded-lg text-sm font-semibold text-left transition-all cursor-pointer hover:opacity-80"
              style={{ color: 'var(--text-primary)', borderTop: '1px solid var(--border-color)' }}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Workspace</span>
            </button>
          </div>
        )}
      </div>

      {/* Create Workspace Form */}
      {showWorkspaceForm && (
        <form
          onSubmit={handleCreateWorkspace}
          className="px-3 py-3 flex flex-col gap-2 border-b"
          style={{ borderColor: 'var(--border-color)', background: 'var(--accent-badge)' }}
        >
          <input
            type="text"
            placeholder="Workspace name..."
            value={newWorkspaceName}
            onChange={e => setNewWorkspaceName(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg"
            style={{
              background: 'var(--bg-main)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              outline: 'none'
            }}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer hover:opacity-90"
              style={{ background: 'var(--text-primary)', color: 'var(--bg-main)' }}
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowWorkspaceForm(false)}
              className="px-3 py-1.5 rounded-lg text-xs transition-all cursor-pointer hover:opacity-80"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-1">
        <div className="flex items-center justify-between px-1 mb-2">
          <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Chat History
          </span>
          {activeWorkspace && (
            <button
              onClick={onCreateSession}
              className="flex items-center justify-center w-6 h-6 rounded-lg transition-all cursor-pointer hover:opacity-80"
              style={{ background: 'var(--accent-badge)', color: 'var(--text-primary)' }}
              title="New Chat Session"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {chatSessions.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <MessageSquare className="w-7 h-7" style={{ color: 'var(--text-muted)' }} />
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No sessions yet</p>
            {activeWorkspace && (
              <button
                onClick={onCreateSession}
                className="text-xs font-semibold underline underline-offset-2 cursor-pointer bg-transparent border-none"
                style={{ color: 'var(--text-primary)' }}
              >
                Start a session
              </button>
            )}
          </div>
        ) : (
          chatSessions.map(session => (
            <button
              key={session.id}
              onClick={() => setActiveSession(session.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left text-sm transition-all cursor-pointer ${
                activeSession === session.id ? 'font-semibold' : 'hover:opacity-80'
              }`}
              style={
                activeSession === session.id
                  ? {
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-hover)',
                      color: 'var(--text-primary)'
                    }
                  : {
                      background: 'transparent',
                      border: '1px solid transparent',
                      color: 'var(--text-secondary)'
                    }
              }
            >
              <Hash className="w-3.5 h-3.5 shrink-0" style={{ color: activeSession === session.id ? 'var(--text-primary)' : 'var(--text-muted)' }} />
              <span className="truncate">{session.title}</span>
            </button>
          ))
        )}
      </div>

      {/* User Footer */}
      <div
        className="px-3 py-3 flex items-center justify-between gap-2 border-t"
        style={{ borderColor: 'var(--border-color)', background: 'var(--accent-badge)' }}
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border"
            style={{
              background: 'var(--bg-card)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)'
            }}
          >
            <User className="w-4 h-4" />
          </div>
          <div className="overflow-hidden">
            <div className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
              {currentUser?.full_name || 'Guest'}
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
              {currentUser?.role || 'Viewer'}
            </div>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-all cursor-pointer hover:bg-red-500/10 hover:text-red-500"
          style={{ color: 'var(--text-muted)' }}
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
}

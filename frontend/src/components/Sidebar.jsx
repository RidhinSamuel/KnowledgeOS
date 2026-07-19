# frontend/src/components/Sidebar.jsx
import React, { useState } from 'react';
import { Plus, MessageSquare, Folder, LogOut, User, Cpu, ChevronDown } from 'lucide-react';
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
  onLogout = () => {}
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
    <aside className="w-80 h-screen border-r border-[var(--border-glass)] bg-[var(--bg-secondary)] flex flex-col z-20">
      
      {/* Brand Header */}
      <div className="p-6 border-b border-[var(--border-glass)] flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center animate-pulse-glow">
          <Cpu className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-extrabold text-lg text-white leading-none">
            <DecryptedText text="KnowledgeOS" speed={60} animateOn="mount" />
          </h1>
          <span className="text-xs text-[var(--text-muted)] font-medium">Enterprise RAG v1.0</span>
        </div>
      </div>

      {/* Workspace Selector */}
      <div className="p-4 border-b border-[var(--border-glass)] relative">
        <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dark)] block mb-1">
          Active Workspace
        </label>
        
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="w-full flex items-center justify-between p-3 rounded-[var(--radius-sm)] border border-[var(--border-glass)] bg-[rgba(255,255,255,0.02)] text-left hover:bg-[rgba(255,255,255,0.04)] transition-all"
        >
          <div className="flex items-center gap-2 overflow-hidden">
            <Folder className="w-4 h-4 text-[var(--primary)] shrink-0" />
            <span className="text-sm font-semibold truncate text-white">
              {activeWS ? activeWS.name : 'Select a workspace'}
            </span>
          </div>
          <ChevronDown className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
        </button>

        {showDropdown && (
          <div className="absolute left-4 right-4 mt-2 glass-panel p-2 z-30 max-h-60 overflow-y-auto">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => {
                  setActiveWorkspace(ws.id);
                  setShowDropdown(false);
                }}
                className={`w-full flex items-center gap-2 p-2 rounded-[var(--radius-sm)] text-left text-sm transition-all hover:bg-[var(--primary-glow)] ${
                  activeWorkspace === ws.id ? 'bg-[var(--primary-glow)] text-white font-medium' : 'text-[var(--text-muted)]'
                }`}
              >
                <Folder className="w-4 h-4 shrink-0" />
                <span className="truncate">{ws.name}</span>
              </button>
            ))}
            <button
              onClick={() => {
                setShowWorkspaceForm(true);
                setShowDropdown(false);
              }}
              className="w-full flex items-center gap-2 p-2 mt-1 rounded-[var(--radius-sm)] text-left text-sm text-[var(--accent)] hover:bg-[rgba(16,185,129,0.1)] transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Create Workspace</span>
            </button>
          </div>
        )}
      </div>

      {/* Dynamic Create Workspace Popup Form */}
      {showWorkspaceForm && (
        <div className="p-4 border-b border-[var(--border-glass)] bg-[rgba(99,102,241,0.02)]">
          <form onSubmit={handleCreateWorkspace} className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="Workspace name..."
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              className="p-2 text-sm rounded-[var(--radius-sm)] bg-[var(--bg-primary)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)]"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="flex-1 p-2 rounded-[var(--radius-sm)] text-xs font-bold text-white bg-[var(--primary)] hover:bg-indigo-700 transition-all"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => setShowWorkspaceForm(false)}
                className="p-2 rounded-[var(--radius-sm)] text-xs text-[var(--text-muted)] hover:bg-[var(--border-glass)] transition-all"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Chat Sessions list */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
        <div className="flex items-center justify-between px-2 mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dark)]">
            Chat History
          </span>
          {activeWorkspace && (
            <button
              onClick={onCreateSession}
              className="p-1 rounded-[var(--radius-sm)] hover:bg-[var(--border-glass)] text-[var(--primary)] transition-all"
              title="New Chat"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>

        {chatSessions.length === 0 ? (
          <div className="text-center py-8 text-xs text-[var(--text-dark)]">
            No active chat sessions
          </div>
        ) : (
          chatSessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setActiveSession(session.id)}
              className={`w-full flex items-center gap-3 p-3 rounded-[var(--radius-md)] text-left text-sm transition-all ${
                activeSession === session.id
                  ? 'bg-[var(--primary-glow)] border border-[var(--primary)] text-white font-medium'
                  : 'hover:bg-[rgba(255,255,255,0.02)] text-[var(--text-muted)] border border-transparent'
              }`}
            >
              <MessageSquare className="w-4 h-4 shrink-0 text-[var(--primary)]" />
              <span className="truncate">{session.title}</span>
            </button>
          ))
        )}
      </div>

      {/* User Session Footer */}
      <div className="p-4 border-t border-[var(--border-glass)] bg-[rgba(0,0,0,0.2)] flex items-center justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-10 h-10 rounded-full bg-[var(--border-glass)] flex items-center justify-center shrink-0 border border-[var(--border-glass)]">
            <User className="w-5 h-5 text-[var(--text-muted)]" />
          </div>
          <div className="overflow-hidden">
            <div className="text-sm font-semibold text-white truncate">
              {currentUser ? currentUser.full_name : 'Guest User'}
            </div>
            <div className="text-xs text-[var(--text-muted)] truncate">
              {currentUser ? currentUser.role : 'Viewer'}
            </div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="p-2 rounded-[var(--radius-sm)] text-[var(--text-dark)] hover:text-red-400 hover:bg-[rgba(239,68,68,0.1)] transition-all shrink-0"
          title="Logout"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </aside>
  );
}

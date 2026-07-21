// frontend/src/components/Auth.jsx
import React, { useState } from 'react';
import { Cpu, ShieldCheck, Mail, Lock, User, Eye, EyeOff, Sun, Moon } from 'lucide-react';
import DecryptedText from './DecryptedText';

export default function Auth({
  BASE_URL = 'http://localhost:8000/api/v1',
  onSuccess = () => {},
  theme = 'dark',
  toggleTheme = () => {}
}) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('Viewer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPass, setShowPass] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError('');
    try {
      if (isRegister) {
        const res = await fetch(`${BASE_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, full_name: fullName, role }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Registration failed');
        setIsRegister(false);
      } else {
        const res = await fetch(`${BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Login failed');
        const data = await res.json();
        const payload = JSON.parse(atob(data.access_token.split('.')[1]));
        onSuccess(data.access_token, { id: payload.sub, role: payload.role, full_name: fullName || email.split('@')[0] });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen w-screen flex items-center justify-center relative overflow-hidden transition-colors"
      style={{ background: 'var(--bg-main)', color: 'var(--text-primary)' }}
    >
      {/* Theme toggle top-right */}
      <button
        onClick={toggleTheme}
        className="absolute top-6 right-6 p-2.5 rounded-xl border transition-all cursor-pointer hover:opacity-80 z-20"
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
          color: 'var(--text-primary)'
        }}
        title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
      >
        {theme === 'dark' ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-indigo-600" />}
      </button>

      {/* Card */}
      <div className="relative z-10 w-[420px] animate-fade-up p-4">
        <div
          className="rounded-3xl p-10 shadow-2xl glass-panel relative"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            backdropFilter: 'blur(32px)'
          }}
        >
          {/* Logo & Header */}
          <div className="flex flex-col items-center mb-8">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-transform hover:scale-105"
              style={{
                background: 'var(--text-primary)',
                color: 'var(--bg-main)',
                boxShadow: '0 0 24px var(--accent-glow)'
              }}
            >
              <Cpu className="w-7 h-7" />
            </div>
            <h1 className="text-2xl font-black tracking-tight mb-1" style={{ color: 'var(--text-primary)' }}>
              <DecryptedText text="KnowledgeOS" speed={50} animateOn="mount" />
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Multi-Tenant Enterprise RAG Knowledge Base
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div
              className="mb-5 flex items-center gap-2 rounded-xl px-4 py-3 text-xs font-semibold text-red-400"
              style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)' }}
            >
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
            {isRegister && (
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Full Name"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  required
                  className="w-full py-3.5 pl-10 pr-4 text-sm rounded-xl input-monochrome"
                />
              </div>
            )}

            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: 'var(--text-muted)' }} />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full py-3.5 pl-10 pr-4 text-sm rounded-xl input-monochrome"
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPass ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full py-3.5 pl-10 pr-10 text-sm rounded-xl input-monochrome"
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer border-none bg-transparent"
                style={{ color: 'var(--text-muted)' }}
              >
                {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>

            {isRegister && (
              <div>
                <label className="block mb-1.5 text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Tenant Role
                </label>
                <select
                  value={role}
                  onChange={e => setRole(e.target.value)}
                  className="w-full py-3 px-4 text-sm rounded-xl input-monochrome cursor-pointer"
                >
                  <option value="Owner">Owner (Admin)</option>
                  <option value="Editor">Editor (Read/Write)</option>
                  <option value="Viewer">Viewer (Read-only)</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 rounded-xl btn-primary cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In Securely'}
            </button>
          </form>

          {/* Toggle Register/Login */}
          <div className="mt-6 text-center text-xs" style={{ color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account? ' : "Don't have an account? "}
            <button
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="font-bold underline underline-offset-2 cursor-pointer bg-transparent border-none"
              style={{ color: 'var(--text-primary)' }}
            >
              {isRegister ? 'Sign in' : 'Sign up'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

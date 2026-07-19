# frontend/src/components/Auth.jsx
import React, { useState } from 'react';
import { Cpu, ShieldCheck, Mail, Lock, User, Plus } from 'lucide-react';
import DecryptedText from './DecryptedText';

export default function Auth({
  BASE_URL = 'http://localhost:8000/api/v1',
  onSuccess = () => {}
}) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('Viewer'); // Default registration role
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError('');

    try {
      if (isRegister) {
        // Register API flow
        const regResp = await fetch(`${BASE_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            role: role
          })
        });

        if (!regResp.ok) {
          const err = await regResp.json();
          throw new Error(err.detail || 'Registration failed');
        }
        
        // Auto transition to login page after register success
        setIsRegister(false);
        alert('Registration successful! Please login.');
      } else {
        // Login API flow
        const loginResp = await fetch(`${BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        if (!loginResp.ok) {
          const err = await loginResp.json();
          throw new Error(err.detail || 'Login failed');
        }

        const data = await loginResp.json();
        const token = data.access_token;
        
        // Fetch current user payload details by decoding token locally
        // or decoding JWT payload structure (since it's base64 encoded)
        const tokenParts = token.split('.');
        const payload = JSON.parse(atob(tokenParts[1]));
        
        // Pass token and user role/info back to app container
        onSuccess(token, {
          id: payload.sub,
          role: payload.role,
          full_name: fullName || email.split('@')[0]
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-6 relative overflow-hidden">
      
      {/* Decorative background blurs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--primary)] opacity-10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--secondary)] opacity-10 rounded-full blur-[100px] pointer-events-none" />

      {/* Main card */}
      <div className="w-full max-w-md glass-panel p-8 animate-float relative z-10">
        
        {/* Brand */}
        <div className="flex flex-col items-center gap-2 mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center animate-pulse-glow">
            <Cpu className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white mt-2">
            <DecryptedText text="KnowledgeOS" speed={60} animateOn="mount" />
          </h1>
          <p className="text-xs text-[var(--text-muted)]">
            Multi-Tenant Enterprise RAG Knowledge Base
          </p>
        </div>

        {error && (
          <div className="p-3 mb-4 rounded-[var(--radius-sm)] bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          
          {isRegister && (
            <div className="relative">
              <User className="absolute left-3 top-3.5 w-4 h-4 text-[var(--text-dark)]" />
              <input
                type="text"
                placeholder="Full Name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                className="w-full p-3.5 pl-10 text-sm rounded-[var(--radius-md)] bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)] transition-all"
              />
            </div>
          )}

          <div className="relative">
            <Mail className="absolute left-3 top-3.5 w-4 h-4 text-[var(--text-dark)]" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full p-3.5 pl-10 text-sm rounded-[var(--radius-md)] bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)] transition-all"
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-3 top-3.5 w-4 h-4 text-[var(--text-dark)]" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full p-3.5 pl-10 text-sm rounded-[var(--radius-md)] bg-[rgba(255,255,255,0.02)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)] transition-all"
            />
          </div>

          {isRegister && (
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dark)] block mb-1">
                Select Tenant Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full p-3 text-sm rounded-[var(--radius-md)] bg-[var(--bg-secondary)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)] transition-all"
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
            className="w-full p-4 mt-2 rounded-[var(--radius-md)] bg-[var(--primary)] hover:bg-indigo-700 text-white font-extrabold text-sm transition-all shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_4px_25px_rgba(99,102,241,0.4)] disabled:opacity-50"
          >
            {loading ? 'Processing...' : isRegister ? 'Register Account' : 'Secure Login'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="text-xs text-[var(--text-muted)] hover:text-white transition-all font-semibold"
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
          </button>
        </div>

      </div>

    </div>
  );
}

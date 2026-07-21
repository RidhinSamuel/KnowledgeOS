// frontend/src/components/ChatArea.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Send, FileText, Bot, User, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

export default function ChatArea({
  activeSession = null,
  activeWorkspace = null,
  authToken = null,
  BASE_URL = 'http://localhost:8000/api/v1'
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeSources, setActiveSources] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch session message history
  const fetchHistory = async () => {
    if (!activeSession || !authToken) return;
    try {
      const response = await fetch(`${BASE_URL}/chat/session/${activeSession}/messages`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.map(m => ({
          role: m.sender,
          content: m.content,
          id: m.id || m._id
        })));
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    setMessages([]);
    setActiveSources([]);
    fetchHistory();
  }, [activeSession, authToken]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || !activeSession || !authToken) return;

    const userPrompt = input;
    setInput('');
    setActiveSources([]);

    // 1. Add User message instantly
    setMessages(prev => [...prev, { role: 'user', content: userPrompt, id: `user-${Date.now()}` }]);
    
    // 2. Create placeholder for incoming assistant message
    const assistantMsgId = `assistant-${Date.now()}`;
    setMessages(prev => [...prev, { role: 'assistant', content: '', id: assistantMsgId }]);
    
    setIsStreaming(true);

    try {
      // 3. Initiate authorized SSE POST request
      const response = await fetch(`${BASE_URL}/chat/session/${activeSession}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ prompt: userPrompt })
      });

      if (!response.ok) {
        throw new Error(`Failed to initialize stream: ${response.statusText}`);
      }

      // 4. Read the ReadableStream response chunks
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const rawText = decoder.decode(value);
        // Split chunk into separate SSE event lines
        const lines = rawText.split('\n');
        
        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine.startsWith('data: ')) continue;
          
          const rawData = cleanLine.substring(6);
          if (rawData === '[DONE]') {
            break;
          }

          try {
            const parsed = JSON.parse(rawData);
            if (parsed.event === 'sources') {
              setActiveSources(parsed.data);
            } else if (parsed.event === 'token') {
              accumulatedResponse += parsed.data;
              
              // Update assistant message placeholder in real-time
              setMessages(prev => 
                prev.map(m => m.id === assistantMsgId ? { ...m, content: accumulatedResponse } : m)
              );
            } else if (parsed.event === 'error') {
              accumulatedResponse += `\n\n[Error: ${parsed.data}]`;
              setMessages(prev => 
                prev.map(m => m.id === assistantMsgId ? { ...m, content: accumulatedResponse } : m)
              );
            }
          } catch (pe) {
             // Silently handle partial chunk parsing
          }
        }
      }

    } catch (err) {
      setMessages(prev => 
        prev.map(m => m.id === assistantMsgId ? { ...m, content: `Error executing search query: ${err.message}` } : m)
      );
    } finally {
      setIsStreaming(false);
    }
  };

  if (!activeSession) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 relative overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.015)' }}>
        
        {/* Decorative background glow */}
        <div className="w-96 h-96 rounded-full absolute pointer-events-none opacity-20 blur-3xl"
          style={{ background: 'radial-gradient(circle, #6366f1, #8b5cf6)' }} />

        <div className="relative z-10 flex flex-col items-center max-w-md">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 animate-pulse-glow"
            style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2))', border: '1px solid rgba(99,102,241,0.3)' }}>
            <Sparkles className="w-8 h-8 text-indigo-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2 tracking-tight">Enterprise Knowledge Search</h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-6">
            Select or create a chat session in the sidebar to query your ingested documents with real-time vector search & graph retrieval.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative"
      style={{ background: 'rgba(255,255,255,0.015)' }}>
      
      {/* Messages Viewport */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 max-w-4xl w-full mx-auto">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-2xl animate-fade-up ${
              msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'
            }`}
          >
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
              msg.role === 'user' 
                ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400' 
                : 'bg-violet-500/20 border-violet-500/30 text-violet-400'
            }`}>
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'rounded-tr-none text-white'
                : 'rounded-tl-none text-slate-200'
            }`}
            style={msg.role === 'user' ? {
              background: 'rgba(99,102,241,0.18)',
              border: '1px solid rgba(99,102,241,0.3)',
              boxShadow: '0 4px 20px rgba(99,102,241,0.1)'
            } : {
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
              backdropFilter: 'blur(12px)'
            }}>
              {msg.content ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <div className="flex items-center gap-1.5 py-1">
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]" />
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Sources footer for assistant responses */}
      {activeSources.length > 0 && (
        <div className="px-6 py-3 border-t border-white/5 bg-black/20 flex flex-col gap-2 max-w-4xl w-full mx-auto">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-indigo-400" /> Retrieved Citation Sources
          </span>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {activeSources.map((src, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/10 bg-white/5 text-[11px] text-slate-200 shrink-0 hover:border-indigo-500/50 transition-all cursor-default"
                title={`Relevance score: ${(src.score * 100).toFixed(1)}%`}
              >
                <FileText className="w-3.5 h-3.5 text-indigo-400" />
                <span className="font-semibold truncate max-w-[140px]">{src.filename}</span>
                <span className="text-slate-500 font-medium">p. {src.page}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input panel */}
      <div className="p-4 border-t border-white/5 bg-black/30 backdrop-blur-md">
        <form onSubmit={handleSend} className="relative flex items-center max-w-4xl w-full mx-auto">
          <input
            type="text"
            placeholder={isStreaming ? "Generating vector-grounded answer..." : "Ask questions across your workspace knowledge base..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            className="w-full py-4 pl-5 pr-14 text-sm rounded-2xl text-white transition-all disabled:opacity-50"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              outline: 'none'
            }}
            onFocus={e => { e.target.style.borderColor = '#6366f1'; e.target.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.12)'; }}
            onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.08)'; e.target.style.boxShadow = 'none'; }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="absolute right-2.5 p-2.5 rounded-xl text-white transition-all disabled:opacity-30 disabled:hover:scale-100 hover:scale-105 cursor-pointer"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', boxShadow: '0 2px 10px rgba(99,102,241,0.3)' }}
          >
            {isStreaming ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
      </div>

    </div>
  );
}

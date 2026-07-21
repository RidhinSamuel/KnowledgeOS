// frontend/src/components/ChatArea.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Send, FileText, Bot, User, Sparkles, AlertCircle } from 'lucide-react';

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
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-[var(--bg-primary)]">
        <Sparkles className="w-12 h-12 text-[var(--primary)] mb-4 animate-float" />
        <h3 className="text-lg font-bold text-white mb-2">Welcome to KnowledgeOS</h3>
        <p className="text-xs text-[var(--text-muted)] max-w-sm">
          Select or create a chat session in the sidebar to search and verify details within your workspaces.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg-primary)] overflow-hidden">
      
      {/* Messages viewport */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-4 max-w-3xl animate-slide-in ${
              msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'
            }`}
          >
            {/* Avatar */}
            <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 border ${
              msg.role === 'user' 
                ? 'bg-[var(--primary-glow)] border-[var(--primary)] text-white' 
                : 'bg-[rgba(255,255,255,0.02)] border-[var(--border-glass)] text-[var(--secondary)]'
            }`}>
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={`p-4 rounded-[var(--radius-lg)] border ${
              msg.role === 'user'
                ? 'bg-[var(--primary-glow)] border-[var(--primary)] text-white'
                : 'bg-[rgba(255,255,255,0.01)] border-[var(--border-glass)] text-[var(--text-main)]'
            }`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Sources footer for assistant responses */}
      {activeSources.length > 0 && (
        <div className="px-6 py-3 border-t border-[var(--border-glass)] bg-[rgba(0,0,0,0.15)] flex flex-col gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dark)] flex items-center gap-1">
            <FileText className="w-3.5 h-3.5" /> Retrieved Sources
          </span>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {activeSources.map((src, i) => (
              <div
                key={i}
                className="flex items-center gap-2 p-2 rounded-[var(--radius-sm)] border border-[var(--border-glass)] bg-[rgba(255,255,255,0.01)] text-[10px] text-white shrink-0 hover:border-[var(--primary-glow)] transition-all"
                title={`Relevance score: ${(src.score * 100).toFixed(1)}%`}
              >
                <FileText className="w-3 h-3 text-[var(--primary)]" />
                <span className="font-semibold truncate max-w-[120px]">{src.filename}</span>
                <span className="text-[var(--text-muted)] font-medium">p. {src.page}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input panel */}
      <div className="p-6 border-t border-[var(--border-glass)] bg-[rgba(0,0,0,0.2)]">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            placeholder={isStreaming ? "Generating answer..." : "Ask your workspace database..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            className="w-full p-4 pr-16 text-sm rounded-[var(--radius-lg)] bg-[var(--bg-secondary)] border border-[var(--border-glass)] text-white focus:outline-none focus:border-[var(--primary)] focus:shadow-[0_0_15px_rgba(99,102,241,0.1)] transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="absolute right-3 p-2.5 rounded-[var(--radius-md)] bg-[var(--primary)] hover:bg-indigo-700 text-white transition-all disabled:opacity-30 disabled:hover:bg-[var(--primary)]"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}

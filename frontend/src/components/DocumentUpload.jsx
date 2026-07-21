// frontend/src/components/DocumentUpload.jsx
import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, Trash2, ShieldCheck } from 'lucide-react';
import canvasConfetti from 'canvas-confetti';

export default function DocumentUpload({
  activeWorkspace = null,
  authToken = null,
  BASE_URL = 'http://localhost:8000/api/v1',
  onDocumentChange = () => {}
}) {
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [dragOver, setDragOver] = useState(false);

  // Fetch workspace documents
  const fetchDocuments = async () => {
    if (!activeWorkspace || !authToken) return;
    try {
      const response = await fetch(`${BASE_URL}/documents/workspace/${activeWorkspace}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.map(d => ({ ...d, id: d.id || d._id })));
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [activeWorkspace, authToken]);

  // Poller loop checking for processing status changes
  useEffect(() => {
    const activeTasks = documents.filter(d => d.status === 'PENDING' || d.status === 'PROCESSING');
    if (activeTasks.length === 0) return;

    const timer = setInterval(async () => {
      let changed = false;
      const updatedDocs = [...documents];

      for (let i = 0; i < updatedDocs.length; i++) {
        const doc = updatedDocs[i];
        if (doc.status === 'PENDING' || doc.status === 'PROCESSING') {
          try {
            const resp = await fetch(`${BASE_URL}/documents/${doc.id}`, {
              headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (resp.ok) {
              const freshDoc = await resp.json();
              if (freshDoc.status !== doc.status) {
                updatedDocs[i] = { ...freshDoc, id: freshDoc.id || freshDoc._id };
                changed = true;
                if (freshDoc.status === 'COMPLETED') {
                  canvasConfetti({ particleCount: 120, spread: 70, origin: { y: 0.6 } });
                }
              }
            }
          } catch (e) {
            console.error(e);
          }
        }
      }

      if (changed) {
        setDocuments(updatedDocs);
        onDocumentChange();
      }
    }, 4000);

    return () => clearInterval(timer);
  }, [documents, authToken]);

  const handleUpload = async (file) => {
    if (!file || !activeWorkspace) return;
    setIsUploading(true);
    setUploadProgress('Uploading file to GridFS...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${BASE_URL}/documents/upload?workspace_id=${activeWorkspace}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: formData
      });

      if (response.ok) {
        const doc = await response.json();
        setDocuments(prev => [{ ...doc, id: doc.id || doc._id }, ...prev]);
        setUploadProgress('Worker parsing & embedding started!');
        onDocumentChange();
      } else {
        const err = await response.json();
        alert(`Upload error: ${err.detail || 'Failed to upload'}`);
      }
    } catch (e) {
      alert(`Upload failed: ${e.message}`);
    } finally {
      setIsUploading(false);
      setUploadProgress('');
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document? Vectors will be purged from Qdrant.')) return;
    try {
      const response = await fetch(`${BASE_URL}/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (response.ok) {
        setDocuments(prev => prev.filter(d => d.id !== docId));
        onDocumentChange();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <aside className="w-80 h-screen shrink-0 flex flex-col p-5 gap-5 border-l border-white/10 bg-white/[0.02] relative z-10 overflow-hidden">
      
      {/* Header */}
      <div>
        <h2 className="text-base font-extrabold text-white tracking-tight">Knowledge Ingestion</h2>
        <p className="text-xs text-slate-400 mt-0.5">Ingest PDFs for background parsing and vector indexing</p>
      </div>

      {/* Upload Zone */}
      {activeWorkspace ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
          }}
          onClick={() => document.getElementById('file-input').click()}
          className={`border-2 border-dashed rounded-2xl p-6 text-center flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
            dragOver ? 'border-indigo-500 bg-indigo-500/10' : 'border-white/10 hover:border-indigo-500/40 hover:bg-white/[0.02]'
          }`}
          style={{ background: dragOver ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.02)' }}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => { if (e.target.files[0]) handleUpload(e.target.files[0]); }}
          />
          
          {isUploading ? (
            <>
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              <span className="text-xs text-white font-medium">{uploadProgress}</span>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <Upload className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">Drop PDF file here</span>
                <span className="text-[10px] text-slate-500 mt-0.5 block">Up to 50MB per document</span>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-white/10 text-center text-xs text-slate-500 bg-white/[0.01]">
          Select a workspace from sidebar to upload files.
        </div>
      )}

      {/* Documents List */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Workspace Files ({documents.length})
          </span>
        </div>
        
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
          {documents.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-600">
              No files uploaded yet
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-all group"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                  <div className="overflow-hidden">
                    <span className="text-xs font-semibold text-white truncate block">
                      {doc.filename}
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {(doc.size_bytes / 1024).toFixed(1)} KB • {doc.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {doc.status === 'PENDING' && (
                    <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" title="Queued in Redis stream" />
                  )}
                  {doc.status === 'PROCESSING' && (
                    <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" title="Parsing & Vectorizing..." />
                  )}
                  {doc.status === 'COMPLETED' && (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" title="Indexed successfully" />
                  )}
                  {doc.status === 'FAILED' && (
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400" title={doc.error_message || 'Indexing failed'} />
                  )}

                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-60 group-hover:opacity-100"
                    title="Delete document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

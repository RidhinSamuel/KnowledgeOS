# frontend/src/components/DocumentUpload.jsx
import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, Trash2 } from 'lucide-react';
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
        // Normalize IDs
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
                  // Fire visual celebration confetti
                  canvasConfetti({ particleCount: 150, spread: 80, origin: { y: 0.6 } });
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
    setUploadProgress('Uploading file to system GridFS...');

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
        setUploadProgress('File uploaded! Worker processing started.');
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
    if (!confirm('Are you sure you want to delete this document? This will remove all vectors from search.')) return;
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
    <div className="flex flex-col gap-6 h-full overflow-hidden p-6">
      
      <div>
        <h2 className="text-xl font-extrabold text-white mb-1">Knowledge Ingestion</h2>
        <p className="text-xs text-[var(--text-muted)]">Ingest documents to feed your workspace AI search database.</p>
      </div>

      {/* File Drop Area */}
      {activeWorkspace ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
          }}
          className={`border-2 border-dashed rounded-[var(--radius-lg)] p-8 text-center flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
            dragOver ? 'border-[var(--primary)] bg-[var(--primary-glow)]' : 'border-[var(--border-glass)] hover:border-indigo-500/50'
          }`}
          onClick={() => document.getElementById('file-input').click()}
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
              <Loader2 className="w-10 h-10 text-[var(--primary)] animate-spin" />
              <span className="text-sm text-white font-medium">{uploadProgress}</span>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-full bg-[rgba(99,102,241,0.05)] border border-[var(--primary-glow)] flex items-center justify-center">
                <Upload className="w-6 h-6 text-[var(--primary)]" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white block">Drag & drop your PDF here</span>
                <span className="text-xs text-[var(--text-muted)]">Max file size 50MB</span>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="text-center p-6 border border-[var(--border-glass)] rounded-[var(--radius-lg)] text-sm text-[var(--text-muted)]">
          Select a workspace from the sidebar to ingest files.
        </div>
      )}

      {/* Documents List */}
      <div className="flex-1 flex flex-col min-h-0">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-dark)] mb-3">
          Workspace Documents
        </h3>
        
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
          {documents.length === 0 ? (
            <div className="text-center py-12 text-xs text-[var(--text-dark)]">
              No files uploaded to this workspace yet.
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 rounded-[var(--radius-md)] border border-[var(--border-glass)] bg-[rgba(255,255,255,0.01)] hover:bg-[rgba(255,255,255,0.02)] transition-all"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileText className="w-5 h-5 text-[var(--text-muted)] shrink-0" />
                  <div className="overflow-hidden">
                    <span className="text-sm text-white truncate block font-medium">
                      {doc.filename}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] block">
                      {(doc.size_bytes / 1024).toFixed(1)} KB • {doc.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {doc.status === 'PENDING' && (
                    <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" title="Pending worker claim" />
                  )}
                  {doc.status === 'PROCESSING' && (
                    <Loader2 className="w-4 h-4 text-[var(--primary)] animate-spin" title="Processing parser & vector database indexing" />
                  )}
                  {doc.status === 'COMPLETED' && (
                    <CheckCircle className="w-4 h-4 text-[var(--accent)]" title="Indexed successfully" />
                  )}
                  {doc.status === 'FAILED' && (
                    <AlertTriangle className="w-4 h-4 text-red-500" title={doc.error_message || 'Indexing failed'} />
                  )}

                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1 rounded-[var(--radius-sm)] text-[var(--text-dark)] hover:text-red-400 hover:bg-[rgba(239,68,68,0.1)] transition-all"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

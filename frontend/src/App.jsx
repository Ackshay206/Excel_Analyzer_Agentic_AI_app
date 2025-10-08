import React, { useState, useEffect } from 'react';
import './App.css';
import { API_BASE_URL } from './config';

import Header from './components/Header';
import FileManager from './components/FileManager';
import FileSelector from './components/FileSelector';
import QueryInput from './components/QueryInput';
import Results from './components/Results';
import ErrorMessage from './components/ErrorMessage';
import Instructions from './components/Instructions';

export default function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [apiKeyStatus, setApiKeyStatus] = useState(null);
  const sessionId = 'default';

  useEffect(() => {
    loadFiles();
    checkApiKeyStatus();
  }, []);

  const checkApiKeyStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api-key-status?session_id=${sessionId}`);
      const data = await response.json();
      setApiKeyStatus(data);
    } catch (err) {
      console.error('Error checking API key:', err);
    }
  };

  const loadFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files`);
      const data = await response.json();
      if (data.success) {
        setFiles(data.files);
        if (data.files.length > 0) setSelectedFile(data.files[0].filename);
      }
    } catch (err) {
      console.error('Failed to load files', err);
      setError('Failed to load files');
    }
  };

  const handleSetApiKey = async (apiKey) => {
    try {
      const response = await fetch(`${API_BASE_URL}/set-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, session_id: sessionId })
      });
      const data = await response.json();
      if (data.success) {
        await checkApiKeyStatus();
        alert('API key set successfully!');
      } else {
        alert(' Failed to set API key: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      console.error('Failed to set API key', err);
      alert(' Failed to set API key');
    }
  };

  const handleRemoveApiKey = async () => {
    try {
      await fetch(`${API_BASE_URL}/remove-api-key?session_id=${sessionId}`, {
        method: 'DELETE'
      });
      await checkApiKeyStatus();
      alert('API key removed');
    } catch (err) {
      console.error('Failed to remove API key', err);
      alert('Failed to remove API key');
    }
  };

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          file_name: selectedFile || null,
          session_id: sessionId
        })
      });

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        setError(data.answer || 'Query failed');
      }
    } catch (err) {
      console.error('Failed to process query', err);
      setError('Failed to process query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Header 
        apiKeyStatus={apiKeyStatus}
        onSetApiKey={handleSetApiKey}
        onRemoveApiKey={handleRemoveApiKey}
      />
      
      <main className="main-content">
        <FileManager
          files={files}
          onRefresh={loadFiles}
        />
        
        <FileSelector 
          files={files}
          selectedFile={selectedFile}
          onSelectFile={setSelectedFile}
        />
        
        <QueryInput
          query={query}
          onQueryChange={setQuery}
          onSubmit={handleSubmit}
          loading={loading}
        />
        
        <ErrorMessage error={error} />
        
        {result ? <Results result={result} /> : <Instructions />}
      </main>
    </div>
  );
}
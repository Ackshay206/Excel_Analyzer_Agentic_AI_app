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
  const [username, setUsername] = useState(localStorage.getItem('username') || '');
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('username'));
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    if (isLoggedIn && username) {
      loadFiles();
      checkApiKeyStatus();
    }
  }, [isLoggedIn, username]);

  // Cleanup on page unload
  useEffect(() => {
    const handleBeforeUnload = async () => {
      if (username) {
        // Send cleanup request (won't wait for response due to browser limitations)
        navigator.sendBeacon(`${API_BASE_URL}/cleanup-session?username=${username}`, '');
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [username]);

  const checkApiKeyStatus = async () => {
    if (!username) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api-key-status?username=${username}`);
      const data = await response.json();
      setApiKeyStatus(data);
      
      // Update login status based on API response
      if (data.exists) {
        setIsLoggedIn(true);
      }
    } catch (err) {
      console.error('Error checking API key:', err);
      setError('Failed to check session status');
    }
  };

  const loadFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files`);
      const data = await response.json();
      if (data.success) {
        setFiles(data.files);
        if (data.files.length > 0 && !selectedFile) {
          setSelectedFile(data.files[0].filename);
        }
      }
    } catch (err) {
      console.error('Failed to load files', err);
      setError('Failed to load files');
    }
  };

  const handleUsernameChange = (newUsername) => {
    if (!newUsername.trim()) {
      setError('Username cannot be empty');
      return;
    }
    
    setUsername(newUsername);
    localStorage.setItem('username', newUsername);
    setIsLoggedIn(true);
    setShowAuthModal(false);
    setError(null);
    
    // Check if user has API key
    setTimeout(() => checkApiKeyStatus(), 100);
  };

  const handleSetApiKey = async (apiKey) => {
    if (!username) {
      setError('Please enter a username first');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/set-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, username: username })
      });
      const data = await response.json();
      if (data.success) {
        await checkApiKeyStatus();
        localStorage.setItem('username', username);
        setIsLoggedIn(true);
        alert(data.is_new_user ? 'Signed up successfully!' : 'Signed in successfully!');
        // Load files after successful API key setup
        await loadFiles();
      } else {
        alert('Failed to set API key: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      console.error('Failed to set API key', err);
      setError('Failed to set API key');
    }
  };

  const handleRemoveApiKey = async () => {
    try {
      await fetch(`${API_BASE_URL}/remove-api-key?username=${username}`, {
        method: 'DELETE'
      });
      await checkApiKeyStatus();
      alert('API key removed');
    } catch (err) {
      console.error('Failed to remove API key', err);
      setError('Failed to remove API key');
    }
  };

  const handleLogout = async () => {
    // Cleanup backend session first
    if (username) {
      try {
        await fetch(`${API_BASE_URL}/cleanup-session?username=${username}`, {
          method: 'POST'
        });
        logger.info('Session cleaned up on logout');
      } catch (err) {
        console.error('Failed to cleanup session:', err);
      }
    }
    
    // Then clear frontend
    localStorage.removeItem('username');
    setUsername('');
    setIsLoggedIn(false);
    setApiKeyStatus(null);
    setFiles([]);
    setSelectedFile('');
    setResult(null);
    setQuery('');
    setShowAuthModal(false);
  };

  const handleSubmit = async () => {
    if (!isLoggedIn) {
      setError('Please sign in first');
      return;
    }

    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    if (!selectedFile) {
      setError('Please select a file');
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
          file_name: selectedFile,
          username: username
        })
      });

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        setError(data.detail || data.answer || 'Query failed');
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
        username={username}
        onUsernameChange={handleUsernameChange}
        isLoggedIn={isLoggedIn}
        onLogout={handleLogout}
        showAuthModal={showAuthModal}
        setShowAuthModal={setShowAuthModal}
      />
      
      <main className="main-content">
        {isLoggedIn ? (
          <>
            <FileManager
              files={files}
              onRefresh={loadFiles}
              username={username}
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
          </>
        ) : (
          <Instructions />
        )}
      </main>
    </div>
  );
}
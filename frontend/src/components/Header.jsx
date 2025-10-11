import React, { useState } from 'react';

export default function Header({ 
  apiKeyStatus, 
  onSetApiKey, 
  onRemoveApiKey, 
  username, 
  onUsernameChange,
  isLoggedIn,
  onLogout,
  showAuthModal,
  setShowAuthModal
}) {
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [tempUsername, setTempUsername] = useState('');

  const handleUsername = () => {
    if (!tempUsername.trim()) {
      alert('Please enter a username');
      return;
    }
    onUsernameChange(tempUsername);
    setTempUsername('');
  };

  const handleApiKey = async () => {
    if (!apiKey.trim()) {
      alert('Please enter an API key');
      return;
    }
    if (!apiKey.startsWith('sk-')) {
      alert('Invalid API key format. API key must start with sk-');
      return;
    }
    await onSetApiKey(apiKey);
    setApiKey('');
    setShowApiKeyInput(false);
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <div className="logo">$</div>
          <h1 className="title">BillingAnalyzer</h1>
        </div>

        <div className="user-controls">
          {isLoggedIn ? (
            <>
              <span className="user-badge">
                Signed in as: {username}
              </span>
              {apiKeyStatus && (
                <span className={`key-badge ${apiKeyStatus.using_custom_key ? 'custom' : 'default'}`}>
                  {apiKeyStatus.using_custom_key ? 'Custom Key' : 'Default Key'}
                </span>
              )}
              <div className="api-key-controls">
                {apiKeyStatus?.using_custom_key && (
                  <button onClick={onRemoveApiKey} className="btn-remove">Remove Key</button>
                )}
                <button 
                  onClick={() => setShowApiKeyInput(!showApiKeyInput)} 
                  className="btn-primary"
                >
                  {apiKeyStatus?.using_custom_key ? 'Change API Key' : 'Set API Key'}
                </button>
              </div>
              <button onClick={onLogout} className="btn-logout">Logout</button>
            </>
          ) : (
            <button onClick={() => setShowAuthModal(true)} className="btn-primary">
              Sign In
            </button>
          )}
        </div>
      </div>

      <div className="auth-sections">
        {showAuthModal && !isLoggedIn && (
          <div className="auth-section username-section">
            <input
              type="text"
              value={tempUsername}
              onChange={(e) => setTempUsername(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleUsername()}
              placeholder="Enter username..."
              className="input"
              autoFocus
            />
            <button onClick={handleUsername} className="btn-save">Sign In</button>
            <button onClick={() => setShowAuthModal(false)} className="btn-remove">Cancel</button>
          </div>
        )}

        {isLoggedIn && showApiKeyInput && (
          <div className="auth-section apikey-section">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleApiKey()}
              placeholder="Enter API key (sk-...)..."
              className="input"
              autoFocus
            />
            <button onClick={handleApiKey} className="btn-save">Set API Key</button>
            <button onClick={() => setShowApiKeyInput(false)} className="btn-remove">Cancel</button>
          </div>
        )}
      </div>
    </header>
  );
}
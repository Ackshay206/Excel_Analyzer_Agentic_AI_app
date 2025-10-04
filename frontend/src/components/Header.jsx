import React, { useState } from 'react';

export default function Header({ apiKeyStatus, onSetApiKey, onRemoveApiKey }) {
  const [showInput, setShowInput] = useState(false);
  const [apiKey, setApiKey] = useState('');

  const handleSave = async () => {
    await onSetApiKey(apiKey);
    setApiKey('');
    setShowInput(false);
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <div className="logo">$</div>
          <h1 className="title">BillingAnalyzer</h1>
        </div>

        <div className="api-controls">
          {apiKeyStatus && (
            <span className={`key-badge ${apiKeyStatus.using_custom_key ? 'custom' : 'default'}`}>
              {apiKeyStatus.using_custom_key ? 'Custom Key' : 'Default Key'}
            </span>
          )}
          {apiKeyStatus?.using_custom_key && (
            <button onClick={onRemoveApiKey} className="btn-remove">Remove</button>
          )}
          <button onClick={() => setShowInput(!showInput)} className="btn-primary">
            Set API Key
          </button>
        </div>
      </div>

      {showInput && (
        <div className="api-input-section">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk..."
            className="input"
          />
          <button onClick={handleSave} className="btn-save">Save</button>
        </div>
      )}
    </header>
  );
}

import React, { useState } from 'react';
import { API_BASE_URL } from '../config';

export default function FileManager({ files, onRefresh, username }) {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        alert('Please select an Excel file (.xlsx or .xls)');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Add username as query parameter to clear cache for this user
      const uploadUrl = username 
        ? `${API_BASE_URL}/upload?username=${username}`
        : `${API_BASE_URL}/upload`;

      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      
      if (data.success) {
        alert('File uploaded successfully!');
        setSelectedFile(null);
        document.getElementById('file-input').value = '';
        await onRefresh();
      } else {
        alert('Upload failed: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 KB';
    const kb = bytes / 1024;
    return kb < 1024 ? `${kb.toFixed(2)} KB` : `${(kb / 1024).toFixed(2)} MB`;
  };

  return (
    <div className="card file-manager-card">
      <h2 className="card-title">File Management</h2>
      <div className="upload-section">
        <input id="file-input" type="file" accept=".xlsx,.xls" onChange={handleFileSelect} className="file-input" />
        <button onClick={handleUpload} disabled={!selectedFile || uploading} className="btn-upload">
          {uploading ? 'Uploading...' : 'Upload File'}
        </button>
        {selectedFile && <span className="selected-file">Selected: {selectedFile.name}</span>}
      </div>

      <div className="files-list">
        <h3 className="files-list-title">Available Files ({files.length})</h3>
        {files.length === 0 ? (
          <p className="no-files">No files uploaded yet</p>
        ) : (
          <div className="files-grid">
            {files.map((file) => (
              <div key={file.filename} className="file-item">
                <div className="file-info">
                  <span className="file-name">{file.filename}</span>
                  <span className="file-size">{formatFileSize(file.size)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
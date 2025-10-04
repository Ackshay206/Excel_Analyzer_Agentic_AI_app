import React from 'react';

export default function FileSelector({ files, selectedFile, onSelectFile }) {
  return (
    <div className="card">
      <h2 className="card-title">Select File</h2>
      <select value={selectedFile} onChange={(e) => onSelectFile(e.target.value)} className="select">
        <option value="">All Files</option>
        {files.map((file) => (
          <option key={file.filename} value={file.filename}>{file.filename}</option>
        ))}
      </select>
      {files.length === 0 && <p className="help-text">No files available</p>}
    </div>
  );
}

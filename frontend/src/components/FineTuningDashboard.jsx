import React, { useState, useEffect } from 'react';
import '../styles/fine_tuning.css';

const FineTuningDashboard = ({ apiUrl }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    fetchJobs();
    // Poll for status updates every 10 seconds
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${apiUrl}/fine-tuning/jobs`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to fetch jobs');
      const data = await response.json();
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (jobId) => {
    try {
      const response = await fetch(`${apiUrl}/fine-tuning/jobs/${jobId}/activate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to activate job');
      await fetchJobs();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeactivate = async (jobId) => {
    try {
      const response = await fetch(`${apiUrl}/fine-tuning/jobs/${jobId}/deactivate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to deactivate job');
      await fetchJobs();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (jobId) => {
    if (!window.confirm('Delete this fine-tuning job? This cannot be undone.')) return;

    try {
      const response = await fetch(`${apiUrl}/fine-tuning/jobs/${jobId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to delete job');
      await fetchJobs();
    } catch (err) {
      setError(err.message);
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'completed': return '#4caf50';
      case 'training': return '#2196f3';
      case 'pending': return '#ff9800';
      case 'failed': return '#f44336';
      default: return '#666';
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'completed': return '✓';
      case 'training': return '⟳';
      case 'pending': return '⏳';
      case 'failed': return '✕';
      default: return '?';
    }
  };

  if (loading) return <div className="fine-tuning-dashboard loading">Loading fine-tuning jobs...</div>;

  return (
    <div className="fine-tuning-dashboard">
      <div className="dashboard-header">
        <h2>🤖 Fine-tuning Models</h2>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          Create New Job
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {jobs.length === 0 ? (
        <div className="empty-state">
          <p>No fine-tuning jobs yet. Create one to optimize models for your data.</p>
        </div>
      ) : (
        <div className="jobs-grid">
          {jobs.map(job => (
            <div key={job.job_id} className="job-card">
              <div className="job-header">
                <h3>{job.job_name}</h3>
                <span className="status-badge" style={{ backgroundColor: getStatusColor(job.status) }}>
                  <span className="status-icon">{getStatusIcon(job.status)}</span>
                  {job.status}
                </span>
              </div>

              <div className="job-details">
                <div className="detail-row">
                  <label>Model Type:</label>
                  <span>{job.model_type}</span>
                </div>
                <div className="detail-row">
                  <label>Base Model:</label>
                  <span className="model-name">{job.base_model}</span>
                </div>
                <div className="detail-row">
                  <label>Provider:</label>
                  <span>{job.provider}</span>
                </div>
                <div className="detail-row">
                  <label>Created:</label>
                  <span>{new Date(job.created_at).toLocaleDateString()}</span>
                </div>
                {job.metrics && (
                  <div className="detail-row">
                    <label>Loss:</label>
                    <span>{job.metrics.final_loss?.toFixed(4) || 'N/A'}</span>
                  </div>
                )}
              </div>

              <div className="job-actions">
                {job.status === 'completed' && !job.is_active && (
                  <button className="btn-activate" onClick={() => handleActivate(job.job_id)}>
                    Activate
                  </button>
                )}
                {job.is_active && (
                  <>
                    <span className="badge-active">Active</span>
                    <button className="btn-deactivate" onClick={() => handleDeactivate(job.job_id)}>
                      Deactivate
                    </button>
                  </>
                )}
                <button className="btn-delete" onClick={() => handleDelete(job.job_id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateFineTuningJobModal
          apiUrl={apiUrl}
          onClose={() => setShowCreateModal(false)}
          onJobCreated={fetchJobs}
        />
      )}
    </div>
  );
};

const CreateFineTuningJobModal = ({ apiUrl, onClose, onJobCreated }) => {
  const [formData, setFormData] = useState({
    job_name: '',
    model_type: 'llm',
    base_model: 'gpt-3.5-turbo',
    provider: 'openai',
    document_ids: [],
    training_params: {
      epochs: 2,
      learning_rate: 0.0001,
      batch_size: 16
    }
  });

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${apiUrl}/documents`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    try {
      const response = await fetch(`${apiUrl}/fine-tuning/training-data/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          model_type: formData.model_type,
          document_ids: formData.document_ids.length > 0 ? formData.document_ids : null
        })
      });
      if (!response.ok) throw new Error('Failed to preview');
      const data = await response.json();
      setPreview(data);
    } catch (err) {
      console.error(err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${apiUrl}/fine-tuning/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify(formData)
      });
      if (!response.ok) throw new Error('Failed to create job');
      onJobCreated();
      onClose();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const modelsByType = {
    llm: ['gpt-3.5-turbo', 'gpt-4', 'claude-3-sonnet', 'mistral-7b'],
    embedding: ['all-MiniLM-L6-v2', 'all-mpnet-base-v2', 'e5-base'],
    local_llm: ['meta-llama/Llama-2-7b', 'mistralai/Mistral-7B', 'HuggingFaceM4/tiny-random-LlamaForCausalLM']
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Create Fine-tuning Job</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Job Name</label>
            <input
              type="text"
              required
              value={formData.job_name}
              onChange={(e) => setFormData({...formData, job_name: e.target.value})}
              placeholder="e.g., Domain RAG v1"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Model Type</label>
              <select
                value={formData.model_type}
                onChange={(e) => setFormData({...formData, model_type: e.target.value, base_model: ''})}
              >
                <option value="llm">LLM</option>
                <option value="embedding">Embedding</option>
                <option value="local_llm">Local LLM</option>
              </select>
            </div>

            <div className="form-group">
              <label>Base Model</label>
              <select
                value={formData.base_model}
                onChange={(e) => setFormData({...formData, base_model: e.target.value})}
                required
              >
                {modelsByType[formData.model_type]?.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Documents for Training</label>
            {loading ? (
              <p>Loading documents...</p>
            ) : (
              <div className="documents-list">
                {documents.map(doc => (
                  <label key={doc.id} className="checkbox">
                    <input
                      type="checkbox"
                      checked={formData.document_ids.includes(doc.id)}
                      onChange={(e) => {
                        const ids = e.target.checked
                          ? [...formData.document_ids, doc.id]
                          : formData.document_ids.filter(id => id !== doc.id);
                        setFormData({...formData, document_ids: ids});
                      }}
                    />
                    {doc.filename}
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Epochs</label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.training_params.epochs}
                onChange={(e) => setFormData({
                  ...formData,
                  training_params: {...formData.training_params, epochs: parseInt(e.target.value)}
                })}
              />
            </div>

            <div className="form-group">
              <label>Learning Rate</label>
              <input
                type="number"
                step="0.00001"
                value={formData.training_params.learning_rate}
                onChange={(e) => setFormData({
                  ...formData,
                  training_params: {...formData.training_params, learning_rate: parseFloat(e.target.value)}
                })}
              />
            </div>

            <div className="form-group">
              <label>Batch Size</label>
              <input
                type="number"
                min="1"
                max="64"
                value={formData.training_params.batch_size}
                onChange={(e) => setFormData({
                  ...formData,
                  training_params: {...formData.training_params, batch_size: parseInt(e.target.value)}
                })}
              />
            </div>
          </div>

          <div className="preview-section">
            <button type="button" className="btn-secondary" onClick={handlePreview} disabled={previewLoading}>
              {previewLoading ? 'Generating Preview...' : 'Preview Training Data'}
            </button>
            {preview && (
              <div className="preview-result">
                <p><strong>Examples found:</strong> {preview.examples_count}</p>
                <p><strong>Quality Score:</strong> {(preview.quality_score * 100).toFixed(1)}%</p>
                {preview.sample_examples.length > 0 && (
                  <details>
                    <summary>Sample Examples ({preview.sample_examples.length})</summary>
                    <pre>{JSON.stringify(preview.sample_examples, null, 2)}</pre>
                  </details>
                )}
              </div>
            )}
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Create Job</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FineTuningDashboard;

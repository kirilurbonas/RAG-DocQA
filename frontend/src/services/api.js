import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const IS_PROD = import.meta.env.PROD;

if (IS_PROD && API_BASE_URL.startsWith('http://')) {
  throw new Error('VITE_API_URL must use HTTPS in production.');
}

function getBearerToken() {
  if (import.meta.env.VITE_BEARER_TOKEN) {
    return import.meta.env.VITE_BEARER_TOKEN;
  }
  if (typeof sessionStorage === 'undefined') {
    return null;
  }
  const key = import.meta.env.VITE_AUTH_TOKEN_STORAGE_KEY || 'rag_access_token';
  return sessionStorage.getItem(key);
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const bearer = getBearerToken();
  if (bearer) {
    config.headers.Authorization = `Bearer ${bearer}`;
  }
  const apiKey = import.meta.env.VITE_API_KEY;
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

export const documentAPI = {
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async () => {
    const response = await api.get('/documents');
    return response.data;
  },

  get: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  delete: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },
};

export const qaAPI = {
  ask: async (question, documentIds = null, topK = 5) => {
    const response = await api.post('/ask', {
      question,
      document_ids: documentIds,
      top_k: topK,
    });
    return response.data;
  },

  askStream: async (question, documentIds = null, topK = 5, onChunk) => {
    const headers = {
      'Content-Type': 'application/json',
    };
    const bearer = getBearerToken();
    if (bearer) {
      headers.Authorization = `Bearer ${bearer}`;
    }
    const apiKey = import.meta.env.VITE_API_KEY;
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }

    const response = await fetch(`${API_BASE_URL}/ask/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        top_k: topK,
      }),
    });

    if (!response.ok) {
      throw new Error(`Streaming request failed (${response.status})`);
    }
    if (!response.body) {
      throw new Error('Streaming not supported by response body');
    }
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('text/event-stream')) {
      throw new Error('Unexpected streaming content type');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: false });
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          if (jsonStr) {
            try {
              const parsed = JSON.parse(jsonStr);
              if (parsed.error) {
                throw new Error(parsed.error);
              }
              if (parsed.token && onChunk) {
                onChunk(parsed.token);
              }
            } catch (e) {
              throw new Error(`Failed to parse stream response: ${e.message}`);
            }
          }
        }
      }
    }

    // Handle final buffer content if any
    if (buffer && buffer.startsWith('data: ')) {
      const jsonStr = buffer.slice(6);
      if (jsonStr) {
        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.error) {
            throw new Error(parsed.error);
          }
          if (parsed.token && onChunk) {
            onChunk(parsed.token);
          }
        } catch (e) {
          throw new Error(`Failed to parse stream response: ${e.message}`);
        }
      }
    }
  },
};

export const statsAPI = {
  get: async () => {
    const response = await api.get('/stats');
    return response.data;
  },
};

export default api;

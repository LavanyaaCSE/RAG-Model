import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Upload endpoints
export const uploadDocument = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/upload/document', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
            if (onProgress) {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percentCompleted);
            }
        },
    });
};

export const uploadImage = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/upload/image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
            if (onProgress) {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percentCompleted);
            }
        },
    });
};

export const uploadAudio = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/upload/audio', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
            if (onProgress) {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percentCompleted);
            }
        },
    });
};

// Search endpoints
export const searchText = async (query, topK = 5, modalities = ['text', 'image', 'audio']) => {
    return api.post('/search/text', {
        query,
        top_k: topK,
        modalities,
    });
};

export const hybridSearch = async (query, topK = 5, modalities = ['text', 'image', 'audio']) => {
    return api.post('/search/hybrid', {
        query,
        top_k: topK,
        modalities,
    });
};

// Query endpoint
export const queryRAG = async (question, topK = 5, includeModalities = ['text', 'image', 'audio']) => {
    return api.post('/query/', {
        question,
        top_k: topK,
        include_modalities: includeModalities,
    });
};

// Document endpoints
export const getDocuments = async (skip = 0, limit = 100, modality = null) => {
    const params = { skip, limit };
    if (modality) params.modality = modality;

    return api.get('/documents/', { params });
};

export const getDocument = async (documentId) => {
    return api.get(`/documents/${documentId}`);
};

export const getDocumentChunks = async (documentId) => {
    return api.get(`/documents/${documentId}/chunks`);
};

export const deleteDocument = async (documentId) => {
    return api.delete(`/documents/${documentId}`);
};

export const getDownloadUrl = async (documentId) => {
    return api.get(`/documents/${documentId}/download`);
};

export default api;

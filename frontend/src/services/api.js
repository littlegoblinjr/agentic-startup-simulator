import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

export const simulate = async (idea) => {
    const { data } = await api.post('/simulate', { idea });
    return data.run_id;
};

export const getStatus = async (runId) => {
    const { data } = await api.get(`/run/${runId}`);
    return data;
};

export const getLogs = async (runId) => {
    const { data } = await api.get(`/run/${runId}/logs`);
    return data;
};

export const listRuns = async () => {
    const { data } = await api.get('/runs');
    return data;
};

export default api;

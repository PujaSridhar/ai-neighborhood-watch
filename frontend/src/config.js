const API_BASE_URL = import.meta.env.PROD
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://127.0.0.1:5001');

export default API_BASE_URL;

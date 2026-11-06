import axios from 'axios'

// Browser-side base URL for the backend API. NEXT_PUBLIC_ vars are inlined at
// build time. The default matches local dev and docker-compose (the backend
// port is published to the host). The compose-internal hostname 'backend' is
// NOT reachable from the user's browser — pass a browser-reachable URL.
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
})

export default api

/** Shared origin for account resolution, scoring, and public health checks. */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').trim().replace(/\/+$/, '');

import axios from "axios";
import type { Client, Portfolio, Policy } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10_000,
});

export const clientsApi = {
  list: (params?: { name?: string; risk_profile?: string }): Promise<Client[]> =>
    api.get("/api/clients/", { params }).then((r) => r.data),

  get: (clientId: string): Promise<Client> =>
    api.get(`/api/clients/${clientId}`).then((r) => r.data),
};

export const portfolioApi = {
  get: (clientId: string, asOfDate?: string): Promise<Portfolio> =>
    api
      .get(`/api/portfolio/${clientId}`, {
        params: asOfDate ? { as_of_date: asOfDate } : undefined,
      })
      .then((r) => r.data),
};

export const policiesApi = {
  list: (params?: { client_id?: string; days_ahead?: number }): Promise<Policy[]> =>
    api.get("/api/policies/", { params }).then((r) => r.data),
};

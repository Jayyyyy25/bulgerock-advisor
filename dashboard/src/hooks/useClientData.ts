import { useQuery } from "@tanstack/react-query";
import { clientsApi, portfolioApi, policiesApi } from "../api/client";

export function useClientList(filters?: { name?: string; risk_profile?: string }) {
  return useQuery({
    queryKey: ["clients", filters],
    queryFn: () => clientsApi.list(filters),
    staleTime: 60_000,
  });
}

export function useClientData(clientId: string) {
  const client = useQuery({
    queryKey: ["client", clientId],
    queryFn: () => clientsApi.get(clientId),
    enabled: !!clientId,
  });

  const portfolio = useQuery({
    queryKey: ["portfolio", clientId],
    queryFn: () => portfolioApi.get(clientId),
    enabled: !!clientId,
  });

  const policies = useQuery({
    queryKey: ["policies", clientId],
    queryFn: () => policiesApi.list({ client_id: clientId, days_ahead: 90 }),
    enabled: !!clientId,
  });

  return {
    client: client.data,
    portfolio: portfolio.data,
    policies: policies.data ?? [],
    isLoading: client.isLoading || portfolio.isLoading,
    isError: client.isError || portfolio.isError,
    errors: [client.error, portfolio.error, policies.error].filter(Boolean),
  };
}

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ClientSearch } from "./components/ClientSearch";
import { Client360 } from "./components/Client360";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={<ClientSearch />} />
            <Route path="/client/:clientId" element={<Client360 />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

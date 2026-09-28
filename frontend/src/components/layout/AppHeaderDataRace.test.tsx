import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/layout/AppHeader";
import { useAuthStore } from "@/stores/authStore";

// Hallazgo real en produccion: TypeError "Cannot read properties of
// undefined (reading 'equity_eur')". `isLoading` de TanStack Query solo
// cubre la carga INICIAL -- si un refetch posterior falla (p.ej. el access
// token expira y `/auth/refresh` tambien devuelve 401, ver api/client.ts),
// `isLoading` vuelve a `false` pero `data` sigue `undefined`. RootLayout
// redirige a /login al limpiar la sesion, pero esa actualizacion de Zustand
// y la de este query son fuentes reactivas independientes: este componente
// puede renderizar en el hueco, con exactamente esa combinacion.
//
// Reproducirlo vía red+MSW+waitFor no es fiable: `render()` solo atrapa un
// throw SINCRONO de la primera pasada; un throw en un re-render posterior
// (disparado por el asentamiento async del query) no lo capturaria ese
// `expect(...).not.toThrow()`. Se mockea el hook directamente (mismo patron
// que ProvenanceBadge.test.tsx) para que la PRIMERA pasada de render ya
// reciba data=undefined/isLoading=false -- el crash, si existe, es
// sincrono y este test lo detecta con fiabilidad.
const mockUseHeaderSummary = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/queries/useHeaderSummary", () => ({
  HEADER_SUMMARY_QUERY_KEY: ["header-summary"],
  useHeaderSummary: mockUseHeaderSummary,
}));

const FAKE_ACCESS_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJkZXZAc3RyYXRvcy5sb2NhbCIsInJvbGUiOiJvcGVyYXRvciIsImV4cCI6OTk5OTk5OTk5OX0.fake";

function renderAppHeader() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AppHeader />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AppHeader · data=undefined con isLoading=false (sesion expirada, refresh tambien falla)", () => {
  it("no revienta -- muestra los placeholders de la cabecera, no un TypeError", () => {
    useAuthStore.getState().setSession(FAKE_ACCESS_TOKEN, "refresh");
    mockUseHeaderSummary.mockReturnValue({ data: undefined, isLoading: false });

    expect(() => renderAppHeader()).not.toThrow();

    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    const badge = screen.getByTestId("data-stale-badge").firstElementChild as HTMLElement;
    expect(badge).toHaveClass("invisible");
  });
});

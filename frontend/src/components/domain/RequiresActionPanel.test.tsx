import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { RequiresActionPanel } from "@/components/domain/RequiresActionPanel";
import { server } from "@/test/mocks/server";
import { useAuthStore } from "@/stores/authStore";

const PENDING_DECISION = {
  id: 7,
  ts: "2026-08-26T09:00:00Z",
  module: "semaphore",
  title: "Poseidón Trend GER40 en NARANJA sostenido: pasar a PAPER",
  description: "Pasar el bot a PAPER (sin dinero real).",
  instruction_text:
    "En el EA magic 118685: desactivar apertura de nuevas posiciones (modo paper) y dejar cerrar las existentes por sus reglas.",
  evidence: { pf_rolling: "1.18", baseline_pf: "1.94" },
  status: "PENDING",
  decided_at: null,
  decided_by: null,
  postpone_until: null,
};

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <RequiresActionPanel />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useAuthStore.getState().setSession("token", "refresh");
});

describe("RequiresActionPanel", () => {
  it("sin decisiones pendientes muestra el estado vacio", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/decisions`, () => HttpResponse.json([]))
    );
    renderPanel();

    expect(
      await screen.findByText("Sin decisiones pendientes. El sistema está al día.")
    ).toBeInTheDocument();
    expect(screen.getByText("Requiere acción (0)")).toBeInTheDocument();
  });

  it("con una decision pendiente, Confirmar la quita de la lista", async () => {
    let confirmed = false;
    server.use(
      http.get(`${API_BASE_URL}/api/v1/decisions`, () =>
        HttpResponse.json(confirmed ? [] : [PENDING_DECISION])
      ),
      http.post(`${API_BASE_URL}/api/v1/decisions/7/confirm`, () => {
        confirmed = true;
        return HttpResponse.json({ ...PENDING_DECISION, status: "CONFIRMED" });
      })
    );
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText(/Poseidón Trend GER40/)).toBeInTheDocument();
    expect(
      screen.getByText(/desactivar apertura de nuevas posiciones/)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => expect(screen.getByText("Requiere acción (0)")).toBeInTheDocument());
  });

  it("Ver evidencia despliega las claves del objeto evidence", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/decisions`, () => HttpResponse.json([PENDING_DECISION]))
    );
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByText("Ver evidencia"));

    expect(await screen.findByText("1.18")).toBeInTheDocument();
    expect(screen.getByText("1.94")).toBeInTheDocument();
  });
});

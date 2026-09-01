import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProvenanceBadge } from "./ProvenanceBadge";
import type { DataProvenance } from "@/api/endpoints/provenance";

const mockUseDataProvenance = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/queries/useDataProvenance", () => ({
  useDataProvenance: mockUseDataProvenance,
}));

function renderBadge(data: DataProvenance | undefined) {
  mockUseDataProvenance.mockReturnValue({ data });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProvenanceBadge />
    </QueryClientProvider>,
  );
}

describe("ProvenanceBadge", () => {
  it("no afirma nada mientras carga", () => {
    // Una procedencia equivocada es peor que ninguna.
    renderBadge(undefined);
    expect(screen.queryByTestId("provenance")).toBeNull();
  });

  it("declara el origen único cuando sólo hay uno", () => {
    renderBadge({
      accounts: [{ data_origin: "BROKER_REAL", accounts: 2, bots: 40 }],
      is_mixed: false,
    });
    expect(screen.getByTestId("provenance")).toHaveTextContent("Cuenta real");
    expect(screen.getByTestId("provenance")).toHaveTextContent("2 cuenta(s) · 40 bot(s)");
    expect(screen.getByTestId("provenance")).toHaveTextContent(
      "Todos los datos provienen de Cuenta real",
    );
  });

  it("avisa cuando el agregado mezcla universos", () => {
    // El hallazgo abierto de G12: fixture y telemetría real en la misma cifra.
    renderBadge({
      accounts: [
        { data_origin: "BROKER_REAL", accounts: 2, bots: 40 },
        { data_origin: "FIXTURE", accounts: 1, bots: 50 },
      ],
      is_mixed: true,
    });
    expect(screen.getByTestId("provenance")).toHaveTextContent("Cuenta real + Fixture");
    expect(screen.getByTestId("provenance")).toHaveTextContent("mezcla universos distintos");
  });

  it("declara la ausencia en vez de inventar procedencia", () => {
    renderBadge({ accounts: [], is_mixed: false });
    expect(screen.getByTestId("provenance")).toHaveTextContent(
      "Sin cuentas registradas",
    );
  });
});

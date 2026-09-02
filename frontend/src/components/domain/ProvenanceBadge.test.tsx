import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProvenanceBadge } from "./ProvenanceBadge";
import type { DataProvenance } from "@/api/endpoints/provenance";

const mockUseDataProvenance = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/queries/useDataProvenance", () => ({
  useDataProvenance: mockUseDataProvenance,
}));

const SIN_TRADES = {
  total: 0,
  attributed_to_live_bot: 0,
  retired_ea: 0,
  without_ea: 0,
  coverage_pct: null,
};

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
      trade_attribution: SIN_TRADES,
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
      trade_attribution: SIN_TRADES,
    });
    expect(screen.getByTestId("provenance")).toHaveTextContent("Cuenta real + Fixture");
    expect(screen.getByTestId("provenance")).toHaveTextContent("mezcla universos distintos");
  });

  it("declara la ausencia en vez de inventar procedencia", () => {
    renderBadge({ accounts: [], is_mixed: false, trade_attribution: SIN_TRADES });
    expect(screen.getByTestId("provenance")).toHaveTextContent(
      "Sin cuentas registradas",
    );
  });
});

describe("ProvenanceBadge · atribución a bots vivos", () => {
  it("dice cuánto del agregado no es de ningún bot vivo", () => {
    // El caso real del stack operacional: 377 de 8.831 trades.
    renderBadge({
      accounts: [{ data_origin: "BROKER_REAL", accounts: 2, bots: 40 }],
      is_mixed: false,
      trade_attribution: {
        total: 8831,
        attributed_to_live_bot: 377,
        retired_ea: 4081,
        without_ea: 4373,
        coverage_pct: 4.27,
      },
    });
    const texto = screen.getByTestId("attribution").textContent ?? "";
    expect(texto).toContain("4.27 %");
    expect(texto).toContain("4081");
    expect(texto).toContain("4373");
  });

  it("no desglosa nada cuando todo pertenece a un bot vivo", () => {
    renderBadge({
      accounts: [{ data_origin: "BROKER_REAL", accounts: 1, bots: 3 }],
      is_mixed: false,
      trade_attribution: {
        total: 120,
        attributed_to_live_bot: 120,
        retired_ea: 0,
        without_ea: 0,
        coverage_pct: 100,
      },
    });
    expect(screen.getByTestId("attribution")).toHaveTextContent(
      "Los 120 trades pertenecen a bots vivos",
    );
  });

  it("sin trades declara ausencia, no cobertura del 0 %", () => {
    renderBadge({ accounts: [], is_mixed: false, trade_attribution: SIN_TRADES });
    expect(screen.getByTestId("provenance")).toHaveTextContent("Sin cuentas registradas");
  });
});

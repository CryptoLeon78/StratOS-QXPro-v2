import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { BotList } from "@/components/domain/bots/BotList";
import { server } from "@/test/mocks/server";

function renderList(onSelect = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <BotList selectedId={null} onSelect={onSelect} />
    </QueryClientProvider>
  );
  return onSelect;
}

const BOTS = [
  { id: 1, name: "Atlas Trend EURUSD", pipeline_phase: "F7", semaphore_state: "VERDE" },
  { id: 2, name: "Umbra MR USTEC", pipeline_phase: "F2", semaphore_state: "VERDE" },
  { id: 3, name: "Helios Momentum DAX", pipeline_phase: "F7", semaphore_state: "AMARILLO" },
];

describe("BotList", () => {
  it("agrupa por pipeline_phase y filtra por nombre", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/bots`, () => HttpResponse.json(BOTS)));
    const onSelect = renderList();

    expect(await screen.findByText("F7 (2)")).toBeInTheDocument();
    expect(screen.getByText("F2 (1)")).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText("Buscar…"), "helios");

    expect(screen.getByText("F7 (1)")).toBeInTheDocument();
    expect(screen.queryByText("F2 (1)")).not.toBeInTheDocument();
    expect(screen.getByText("Helios Momentum DAX")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Helios Momentum DAX"));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 3 }));
  });

  it("estado vacio cuando la busqueda no encuentra nada", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/bots`, () => HttpResponse.json(BOTS)));
    renderList();

    await userEvent.type(await screen.findByPlaceholderText("Buscar…"), "zzz-inexistente");

    expect(screen.getByText("Sin bots que coincidan con la búsqueda.")).toBeInTheDocument();
  });
});

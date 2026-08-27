import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { ImpulseFormDialog } from "@/components/domain/bots/ImpulseFormDialog";
import { server } from "@/test/mocks/server";

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ImpulseFormDialog botId={42} botName="Atlas Trend EURUSD" open onOpenChange={() => {}} />
    </QueryClientProvider>
  );
}

describe("ImpulseFormDialog", () => {
  it("el submit esta deshabilitado hasta escribir una descripcion, y envia el bot_id correcto", async () => {
    let receivedBody: unknown = null;
    server.use(
      http.post(`${API_BASE_URL}/api/v1/impulses`, async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json(
          {
            id: 1,
            ts: "2026-01-01T00:00:00Z",
            bot_id: 42,
            description: "x",
            desired_action: "PAUSE_BOT",
            executed: false,
            status: "PENDING",
            counterfactual_result_7d_eur: null,
            avoided_cost_eur: null,
            evaluated_at: null,
          },
          { status: 201 }
        );
      })
    );

    renderDialog();

    const submit = screen.getByRole("button", { name: "Registrar impulso" });
    expect(submit).toBeDisabled();

    await userEvent.type(
      screen.getByLabelText("Descripción del impulso"),
      "Quiero pausar por ruido de noticias"
    );
    expect(submit).not.toBeDisabled();

    await userEvent.click(submit);

    expect(await screen.findByText(/se evaluará su contrafactual a 7 días/)).toBeInTheDocument();
    expect(receivedBody).toEqual({
      bot_id: 42,
      description: "Quiero pausar por ruido de noticias",
      desired_action: "PAUSE_BOT",
    });
  });
});

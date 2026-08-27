import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";

function renderLoginForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route path="/" element={<div>pagina protegida</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useAuthStore.getState().clear();
});

describe("LoginForm", () => {
  it("muestra errores de validacion sin llamar a la API", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    await user.click(screen.getByRole("button", { name: uiStrings.login.submit }));

    expect(await screen.findByText(uiStrings.login.emailInvalid)).toBeInTheDocument();
    expect(screen.getByText(uiStrings.login.passwordRequired)).toBeInTheDocument();
  });

  it("con credenciales correctas guarda la sesion y navega a /", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText(uiStrings.login.emailLabel), "operator@stratos.local");
    await user.type(screen.getByLabelText(uiStrings.login.passwordLabel), "ok");
    await user.click(screen.getByRole("button", { name: uiStrings.login.submit }));

    await waitFor(() => expect(screen.getByText("pagina protegida")).toBeInTheDocument());
    expect(useAuthStore.getState().accessToken).toBe("fake.access.token");
  });

  it("con credenciales incorrectas muestra el mensaje de error", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText(uiStrings.login.emailLabel), "operator@stratos.local");
    await user.type(screen.getByLabelText(uiStrings.login.passwordLabel), "wrong");
    await user.click(screen.getByRole("button", { name: uiStrings.login.submit }));

    expect(await screen.findByText(uiStrings.login.credentialsInvalid)).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});

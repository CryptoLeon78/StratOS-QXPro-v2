import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { RouterProvider } from "react-router-dom";

import { startAccountScopeSync } from "@/lib/accountScopeSync";
import { queryClient } from "@/lib/queryClient";
import { router } from "@/routes/router";

startAccountScopeSync(queryClient);

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      {/* navigator.webdriver: Playwright/Selenium lo fijan a true -- oculta
          el boton flotante bajo automatizacion (contamina el screenshot-diff
          de tests/e2e/, PARTE 11.1) sin afectar `npm run dev` normal. */}
      {import.meta.env.DEV && !navigator.webdriver && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

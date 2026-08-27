import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "@/test/mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  // globals:false en vite.config.ts -- @testing-library/react no detecta un
  // afterEach global automatico para su cleanup, hay que registrarlo aqui.
  cleanup();
});
afterAll(() => server.close());

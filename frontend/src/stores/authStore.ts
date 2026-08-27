import { create } from "zustand";
import { persist } from "zustand/middleware";

// Solo {accessToken, refreshToken} persistidos -- no hay cookie httpOnly de
// servidor (core-engine no tiene sesion server-side, PARTE 9.2). user/role
// se DERIVAN decodificando el access token en cada lectura (lib/jwt.ts),
// nunca una segunda fuente de verdad que pueda desincronizarse tras un
// refresh.
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  setSession: (accessToken: string, refreshToken: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      setSession: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      clear: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: "stratos-auth" }
  )
);

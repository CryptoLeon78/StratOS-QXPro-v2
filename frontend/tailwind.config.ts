// Theme generado 1:1 desde doc_app/design_tokens.json (P11, contractual) --
// nunca un color/spacing definido a mano aqui. Se acepta la verbosidad de
// clases resultante (bg-bg-app, text-text-primary, bg-semaphore-naranja) a
// cambio de cero duplicacion/desincronia con el JSON fuente.
import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";
import tokens from "./src/styles/tokens";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: tokens.color,
      fontFamily: {
        sans: [tokens.font.family.sans],
        mono: [tokens.font.family.mono],
      },
      fontSize: tokens.font.size,
      fontWeight: tokens.font.weight,
      spacing: tokens.space,
      borderRadius: tokens.radius,
      boxShadow: tokens.shadow,
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Config;

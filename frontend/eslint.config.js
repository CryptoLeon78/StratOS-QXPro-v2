import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  {
    // shadcn/ui vendorizado (src/components/ui/*): exportar variants/hooks
    // junto al componente (buttonVariants, badgeVariants, useFormField...)
    // es el patron estandar de la libreria, no un error nuestro -- rompe
    // el fast refresh de Vite en dev, pero no afecta produccion.
    files: ["src/components/ui/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // router.tsx (G9, code-splitting): React.lazy(() => import(...)) para
    // las 10 pestanas no-Resumen dispara este aviso porque el modulo no
    // exporta solo componentes -- es config de rutas, no un componente en
    // si, nunca se edita en caliente con Fast Refresh de todos modos.
    files: ["src/routes/router.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  }
);

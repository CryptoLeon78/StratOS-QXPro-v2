// Interpola plantillas de ui_strings.es.json ("Sem: {week} · Mes: {month}")
// -- usado por varias StatCard, evita repetir el mismo .replace() encadenado
// en cada sitio de consumo.
export function interpolate(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match
  );
}

import { isRouteErrorResponse, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import uiStrings from "@/styles/ui_strings.es.json";

// errorElement del router: un fallo de render en una pestaña no debe dejar la
// pantalla por defecto de React Router ("Unexpected Application Error!").
export default function RouteError() {
  const error = useRouteError();
  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : String(error);
  return (
    <div role="alert" className="space-y-3 p-6">
      <h2 className="text-lg font-semibold text-text-primary">{uiStrings.app.routeErrorTitle}</h2>
      <p className="text-sm text-text-secondary">{detail}</p>
      <Button onClick={() => window.location.assign("/")}>{uiStrings.app.routeErrorReload}</Button>
    </div>
  );
}

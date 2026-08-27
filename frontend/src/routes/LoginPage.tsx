import { Navigate } from "react-router-dom";

import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";

export default function LoginPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (accessToken) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-xl font-semibold text-text-primary">{uiStrings.login.title}</h1>
        <LoginForm />
      </div>
    </div>
  );
}

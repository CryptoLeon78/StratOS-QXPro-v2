import { Navigate, Outlet } from "react-router-dom";

import { AppHeader } from "@/components/layout/AppHeader";
import { TabBar } from "@/components/layout/TabBar";
import { useAuthStore } from "@/stores/authStore";

export default function RootLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TabBar />
      <Outlet />
    </div>
  );
}

import { Navigate, Outlet } from "react-router-dom";

import { TabBar } from "@/components/layout/TabBar";
import { useAuthStore } from "@/stores/authStore";

// AppHeader (6 StatCard) se anade en un commit siguiente de G6.
export default function RootLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen">
      <TabBar />
      <Outlet />
    </div>
  );
}

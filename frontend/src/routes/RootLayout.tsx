import { Outlet } from "react-router-dom";

import { TabBar } from "@/components/layout/TabBar";

// AppHeader (6 StatCard) y el guard de autenticacion (redirect a /login sin
// accessToken) se anaden en los commits siguientes de G6.
export default function RootLayout() {
  return (
    <div className="min-h-screen">
      <TabBar />
      <Outlet />
    </div>
  );
}

import { Outlet } from "react-router-dom";

// Esqueleto -- TabBar (navegacion real de las 11 pestanas) y el guard de
// autenticacion (redirect a /login sin accessToken) se anaden en los
// commits siguientes de G6.
export default function RootLayout() {
  return (
    <div className="min-h-screen">
      <Outlet />
    </div>
  );
}

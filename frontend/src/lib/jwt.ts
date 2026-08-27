// Decodifica los claims de un JWT SIN verificar la firma -- solo para leer
// datos de presentacion (email/role) en el cliente. La verificacion real
// (firma, expiracion) la hace siempre core-engine en cada request; un JWT
// decodificado mal aqui como mucho muestra un dato incorrecto en pantalla,
// nunca concede acceso.
export interface AccessTokenClaims {
  sub: string;
  email: string;
  role: string;
  exp: number;
}

export function decodeJwtPayload(token: string): AccessTokenClaims | null {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json) as AccessTokenClaims;
  } catch {
    return null;
  }
}

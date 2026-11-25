import { NextResponse, type NextRequest } from "next/server";

// Só confere se o cookie de sessão existe. Quem valida sessão e assinatura é o backend.
const PUBLICAS = ["/login", "/assinatura"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (PUBLICAS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return NextResponse.next();
  if (request.cookies.has("sinais_sessao")) return NextResponse.next();
  const destino = request.nextUrl.clone();
  destino.pathname = "/login";
  destino.search = "";
  destino.searchParams.set("proximo", `${pathname}${search}`);
  return NextResponse.redirect(destino);
}

export const config = {
  matcher: ["/((?!api/|_next/static|_next/image|favicon\\.ico|icon\\.svg|robots\\.txt).*)"],
};

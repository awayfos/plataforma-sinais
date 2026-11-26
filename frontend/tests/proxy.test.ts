// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { proxy } from "@/proxy";

describe("proxy (só confere se o cookie de sessão existe)", () => {
  it("sem cookie, rota protegida vai para o login com o destino", () => {
    const r = proxy(new NextRequest("http://localhost/terminal?x=1"));
    expect(r.status).toBe(307);
    const destino = new URL(r.headers.get("location")!);
    expect(destino.pathname).toBe("/login");
    expect(destino.searchParams.get("proximo")).toBe("/terminal?x=1");
  });

  it("com cookie, deixa passar", () => {
    const r = proxy(new NextRequest("http://localhost/terminal", { headers: { cookie: "sinais_sessao=abc" } }));
    expect(r.headers.get("location")).toBeNull();
    expect(r.headers.get("x-middleware-next")).toBe("1");
  });

  it("login e assinatura são públicas", () => {
    expect(proxy(new NextRequest("http://localhost/login")).headers.get("location")).toBeNull();
    expect(proxy(new NextRequest("http://localhost/assinatura")).headers.get("location")).toBeNull();
  });
});

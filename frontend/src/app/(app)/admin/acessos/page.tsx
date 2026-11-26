import type { Metadata } from "next";
import { LogAcessos } from "@/components/admin/Logs";

export const metadata: Metadata = { title: "Acessos" };

export default function Pagina() {
  return <LogAcessos />;
}

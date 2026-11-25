import type { Metadata } from "next";
import { LogAuditoria } from "@/components/admin/Logs";

export const metadata: Metadata = { title: "Auditoria" };

export default function Pagina() {
  return <LogAuditoria />;
}

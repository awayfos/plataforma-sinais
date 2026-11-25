import type { Metadata } from "next";
import { TelaAssinatura } from "@/components/auth/TelaAssinatura";

export const metadata: Metadata = { title: "Assinatura" };

export default function PaginaAssinatura() {
  return <TelaAssinatura />;
}

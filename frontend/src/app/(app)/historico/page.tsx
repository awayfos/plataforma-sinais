import type { Metadata } from "next";
import { Historico } from "@/components/historico/Historico";

export const metadata: Metadata = { title: "Histórico" };

export default function PaginaHistorico() {
  return <Historico />;
}

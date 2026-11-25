import type { Metadata } from "next";
import { GestaoPlanos } from "@/components/admin/GestaoPlanos";

export const metadata: Metadata = { title: "Planos" };

export default function Pagina() {
  return <GestaoPlanos />;
}

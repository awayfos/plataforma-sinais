import type { Metadata } from "next";
import { GestaoUsuarios } from "@/components/admin/GestaoUsuarios";

export const metadata: Metadata = { title: "Usuários" };

export default function Pagina() {
  return <GestaoUsuarios />;
}

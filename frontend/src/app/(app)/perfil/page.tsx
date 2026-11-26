import type { Metadata } from "next";
import { Perfil } from "@/components/perfil/Perfil";

export const metadata: Metadata = { title: "Perfil" };

export default function PaginaPerfil() {
  return <Perfil />;
}

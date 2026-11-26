import type { Metadata } from "next";
import { FormAssinatura } from "@/components/admin/FormAssinatura";

export const metadata: Metadata = { title: "Assinaturas" };

export default function Pagina() {
  return <FormAssinatura />;
}

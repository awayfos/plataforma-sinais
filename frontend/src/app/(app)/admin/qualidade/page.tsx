import type { Metadata } from "next";
import { EventosQualidade } from "@/components/admin/Logs";

export const metadata: Metadata = { title: "Qualidade de dados" };

export default function Pagina() {
  return <EventosQualidade />;
}

import type { Metadata } from "next";
import { EditorPayout } from "@/components/admin/EditorPayout";

export const metadata: Metadata = { title: "Payout Exnova" };

export default function Pagina() {
  return <EditorPayout />;
}

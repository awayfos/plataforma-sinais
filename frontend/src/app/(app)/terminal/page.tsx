import type { Metadata } from "next";
import { Terminal } from "@/components/terminal/Terminal";

export const metadata: Metadata = { title: "Terminal" };

export default function PaginaTerminal() {
  return <Terminal />;
}

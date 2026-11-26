import type { Metadata } from "next";
import { LayoutAdmin } from "@/components/admin/LayoutAdmin";

export const metadata: Metadata = { title: { default: "Administração", template: "%s · Admin" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <LayoutAdmin>{children}</LayoutAdmin>;
}

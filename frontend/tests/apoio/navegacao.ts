// Apoio de TESTE: substitui o roteador do Next.
import { vi } from "vitest";

export const roteador = {
  replace: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  prefetch: vi.fn(),
};

export function reiniciarRoteador() {
  for (const fn of Object.values(roteador)) fn.mockReset();
}

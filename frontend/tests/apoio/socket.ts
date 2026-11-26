// Apoio de TESTE: WebSocket falso controlado pelo teste.
import type { SocketMinimo } from "@/lib/ws/cliente";

export class SocketFalso implements SocketMinimo {
  readyState = 0;
  enviados: { acao: string; canal: string }[] = [];
  onopen: (() => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onerror: (() => void) | null = null;
  send(d: string) {
    this.enviados.push(JSON.parse(d));
  }
  close() {
    this.readyState = 3;
  }
  abrir() {
    this.readyState = 1;
    this.onopen?.();
  }
  cair(code: number) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
  receber(obj: unknown) {
    this.onmessage?.({ data: JSON.stringify(obj) });
  }
}

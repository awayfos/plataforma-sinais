/**
 * Junta itens recebidos entre dois quadros de tela e entrega tudo de uma vez no próximo quadro
 * (requestAnimationFrame): no máximo uma atualização do gráfico por quadro, sem re-render do React.
 */
export class AgrupadorQuadros<T> {
  private fila: T[] = [];
  private pendente = false;
  private geracao = 0;

  constructor(
    private readonly aoDescarregar: (itens: T[]) => void,
    private readonly agendar: (fn: () => void) => unknown = (fn) => requestAnimationFrame(() => fn()),
    /** Limite da fila (aba em segundo plano pausa o rAF): guarda só os mais recentes. */
    private readonly limite = 1_000,
  ) {}

  enfileirar(item: T): void {
    this.fila.push(item);
    if (this.fila.length > this.limite) this.fila.splice(0, this.fila.length - this.limite);
    if (this.pendente) return;
    this.pendente = true;
    const geracao = this.geracao;
    this.agendar(() => {
      if (geracao !== this.geracao) return;
      this.descarregar();
    });
  }

  descarregar(): void {
    this.pendente = false;
    const itens = this.fila;
    this.fila = [];
    if (itens.length > 0) this.aoDescarregar(itens);
  }

  descartar(): void {
    this.geracao += 1;
    this.pendente = false;
    this.fila = [];
  }
}

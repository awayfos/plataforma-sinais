"use client";

import { useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { EXPIRACOES, type Expiracao, type PayoutExnova } from "@/lib/api/tipos";
import { formatarPercentual } from "@/lib/formato";
import { ROTULO_EXPIRACAO } from "@/lib/sinais";
import { useDados } from "@/lib/useDados";
import { Dica } from "@/components/ui/Dica";
import { Carregando, ErroEstado } from "@/components/ui/Estado";
import { botao, campoBase, painel, rotulo, tabela } from "@/components/ui/estilos";

const chave = (p: { simbolo: string; expiracao: string }) => `${p.simbolo}:${p.expiracao}`;
const paraPercentual = (fracao: number) => String(Math.round(fracao * 10_000) / 100);

function valido(texto: string): number | null {
  const n = Number(texto.replace(",", "."));
  return texto.trim() !== "" && Number.isFinite(n) && n >= 1 && n <= 100 ? n : null;
}

export function EditorPayout() {
  const dados = useDados("payout", (s) => api.admin.payout(s));
  const [edicoes, setEdicoes] = useState<Record<string, string>>({});
  const [extras, setExtras] = useState<PayoutExnova[]>([]);
  const [novoSimbolo, setNovoSimbolo] = useState("BTCUSDT");
  const [novaExpiracao, setNovaExpiracao] = useState<Expiracao>("1m");
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const base = dados.dados ?? [];
  const linhas = [...base, ...extras.filter((x) => !base.some((b) => chave(b) === chave(x)))];
  const valorDe = (p: PayoutExnova) => edicoes[chave(p)] ?? (Number.isFinite(p.payout) ? paraPercentual(p.payout) : "");

  async function salvar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    setSalvo(false);
    const lista: PayoutExnova[] = [];
    for (const p of linhas) {
      const n = valido(valorDe(p));
      if (n === null) return setErro("Payout deve estar entre 1% e 100%.");
      lista.push({ simbolo: p.simbolo, expiracao: p.expiracao, payout: n / 100 });
    }
    setEnviando(true);
    try {
      await api.admin.salvarPayout(lista);
      setSalvo(true);
      setEdicoes({});
      setExtras([]);
      dados.recarregar();
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível salvar.");
    } finally {
      setEnviando(false);
    }
  }

  if (dados.erro) return <ErroEstado mensagem={dados.erro.message} aoTentarDeNovo={dados.recarregar} />;
  if (!dados.dados) return <Carregando rotulo="Carregando payouts…" />;

  return (
    <form onSubmit={salvar} className="space-y-4" noValidate>
      <p className="max-w-3xl text-xs leading-relaxed text-apagado">
        Payout da Exnova por ativo e expiração, como aparece no painel da corretora. O equilíbrio <span className="num">p* = 1 / (1 + r)</span> é a
        taxa de acerto mínima para não perder dinheiro; a validação só liga um sinal acima dele com margem.
        <Dica termo="payout" />
      </p>
      <section className={`${painel} overflow-x-auto p-1`}>
        <table className={tabela.raiz}>
          <caption className="sr-only">Payout por ativo e expiração</caption>
          <thead className={tabela.cabeca}>
            <tr>
              <th scope="col" className={tabela.th}>Ativo</th>
              <th scope="col" className={tabela.th}>Expiração</th>
              <th scope="col" className={tabela.th}>Payout (%)</th>
              <th scope="col" className={`${tabela.th} text-right`}>Equilíbrio p*</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((p) => {
              const v = valorDe(p);
              const n = valido(v);
              return (
                <tr key={chave(p)} className={tabela.linha}>
                  <td className={`${tabela.td} num`}>{p.simbolo}</td>
                  <td className={`${tabela.td} text-suave`}>{ROTULO_EXPIRACAO[p.expiracao] ?? p.expiracao}</td>
                  <td className={tabela.td}>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      step={0.5}
                      aria-label={`Payout ${p.simbolo} ${ROTULO_EXPIRACAO[p.expiracao] ?? p.expiracao}`}
                      aria-invalid={n === null}
                      value={v}
                      onChange={(e) => setEdicoes((x) => ({ ...x, [chave(p)]: e.target.value }))}
                      className={`${campoBase} num w-28 py-1 ${n === null ? "ring-1 ring-baixa" : ""}`}
                    />
                  </td>
                  <td className={`${tabela.td} num text-right text-suave`}>{n === null ? "—" : formatarPercentual(1 / (1 + n / 100), 2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {linhas.length === 0 && <p className="p-3 text-sm text-apagado">Nenhum payout cadastrado. Adicione abaixo.</p>}
      </section>

      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor="np-simbolo" className={rotulo}>Ativo</label>
          <input id="np-simbolo" value={novoSimbolo} onChange={(e) => setNovoSimbolo(e.target.value.toUpperCase())} className={`${campoBase} num w-32 py-1.5`} />
        </div>
        <div>
          <label htmlFor="np-exp" className={rotulo}>Expiração</label>
          <select id="np-exp" value={novaExpiracao} onChange={(e) => setNovaExpiracao(e.target.value as Expiracao)} className={`${campoBase} w-28 py-1.5`}>
            {EXPIRACOES.map((x) => (
              <option key={x} value={x}>{ROTULO_EXPIRACAO[x]}</option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className={botao.secundario}
          onClick={() => {
            const simbolo = novoSimbolo.trim();
            if (!simbolo) return;
            setExtras((x) => [...x, { simbolo, expiracao: novaExpiracao, payout: Number.NaN }]);
          }}
        >
          Adicionar linha
        </button>
      </div>

      {erro && <p role="alert" className="text-sm text-baixa">{erro}</p>}
      {salvo && <p role="status" className="text-sm text-alta">Payouts salvos.</p>}
      <button type="submit" className={botao.primario} disabled={enviando}>
        {enviando ? "Salvando…" : "Salvar payouts"}
      </button>
    </form>
  );
}

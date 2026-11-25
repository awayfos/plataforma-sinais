"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api/endpoints";
import type { Analise, Candle, Desenho, IndicadoresGrafico, Sinal, TempoGrafico } from "@/lib/api/tipos";
import { mesclarCandle } from "@/lib/candles";
import { useDados } from "@/lib/useDados";
import { useCanal } from "@/lib/ws/ProvedorTempoReal";
import { useSessao } from "@/components/sessao/ProvedorSessao";
import { Carregando, ErroEstado, Vazio } from "@/components/ui/Estado";
import { tituloPainel } from "@/components/ui/estilos";
import { tocarAlerta } from "./alerta";
import { BarraFerramentas } from "./BarraFerramentas";
import { CartaoSinal } from "./CartaoSinal";
import { Grafico, type Ferramenta } from "./Grafico";
import { ListaAtivos } from "./ListaAtivos";
import { PainelAnalise } from "./PainelAnalise";
import { TabelaSinais } from "./TabelaSinais";

const INDICADORES_PADRAO: IndicadoresGrafico = { ema: true, bollinger: false, vwap: false, rsi: true, macd: false };
const LIMITE_CANDLES = 500;

function maisRecente(a: Analise | null | undefined, b: Analise | null | undefined): Analise | null {
  if (!a) return b ?? null;
  if (!b) return a;
  return b.t > a.t ? b : a;
}

export function Terminal() {
  const { usuario, layout, salvarLayout } = useSessao();
  const avancado = usuario?.modo === "avancado";

  const ativosQ = useDados("ativos", (s) => api.ativos(s));
  const ativos = useMemo(() => ativosQ.dados ?? [], [ativosQ.dados]);

  const [simboloEscolhido, setSimboloEscolhido] = useState<string | null>(null);
  const [tempoEscolhido, setTempoEscolhido] = useState<TempoGrafico | null>(null);
  const [ferramenta, setFerramenta] = useState<Ferramenta>("cursor");
  const [som, setSom] = useState(false);
  const [erroSalvar, setErroSalvar] = useState(false);

  const simbolo = useMemo(() => {
    const valido = (s: string | null | undefined) => !!s && ativos.some((a) => a.simbolo === s);
    if (valido(simboloEscolhido)) return simboloEscolhido;
    if (valido(layout.simbolo)) return layout.simbolo!;
    return ativos.find((a) => a.aberto)?.simbolo ?? ativos[0]?.simbolo ?? null;
  }, [ativos, layout.simbolo, simboloEscolhido]);
  const tempo: TempoGrafico = tempoEscolhido ?? layout.tempo ?? "1m";
  const ativo = ativos.find((a) => a.simbolo === simbolo);
  const aberto = ativo?.aberto ?? false;
  const indicadores = useMemo(() => ({ ...INDICADORES_PADRAO, ...layout.indicadores }), [layout.indicadores]);
  const desenhos = useMemo(() => (simbolo ? (layout.desenhos?.[simbolo] ?? []) : []), [layout.desenhos, simbolo]);

  function salvar(parcial: Parameters<typeof salvarLayout>[0]) {
    setErroSalvar(false);
    salvarLayout(parcial).catch(() => setErroSalvar(true));
  }

  // Candles: histórico por REST + candle em formação pelo WebSocket.
  const chaveSerie = simbolo ? `${simbolo}:${tempo}` : null;
  const candlesQ = useDados(chaveSerie, (s) => api.candles({ simbolo: simbolo!, tg: tempo, limite: LIMITE_CANDLES }, s));
  const [aoVivo, setAoVivo] = useState<{ chave: string | null; lista: Candle[] }>({ chave: null, lista: [] });
  useCanal(simbolo ? (`candles:${simbolo}:${tempo}` as const) : null, (c) => {
    const candle: Candle = { t: c.t, o: c.o, h: c.h, l: c.l, c: c.c, v: c.v };
    setAoVivo((prev) => ({
      chave: chaveSerie,
      lista: mesclarCandle(prev.chave === chaveSerie ? prev.lista : [], candle).slice(-60),
    }));
  });
  const candles = useMemo(() => {
    const base = candlesQ.dados ?? [];
    if (aoVivo.chave !== chaveSerie) return base;
    return aoVivo.lista.reduce((acc, c) => mesclarCandle(acc, c), base);
  }, [candlesQ.dados, aoVivo, chaveSerie]);

  // Análise e sinais: REST no início, WebSocket depois.
  const analiseQ = useDados(simbolo && aberto ? `analise:${simbolo}` : null, (s) => api.analise(simbolo!, s));
  const [analiseVivo, setAnaliseVivo] = useState<Analise | null>(null);
  useCanal(simbolo && aberto ? (`analise:${simbolo}` as const) : null, setAnaliseVivo);
  const analise = maisRecente(analiseQ.dados, analiseVivo?.simbolo === simbolo ? analiseVivo : null);

  const sinaisQ = useDados(simbolo && aberto ? `sinais:${simbolo}` : null, (s) => api.sinais(simbolo!, s));
  const [sinaisVivo, setSinaisVivo] = useState<{ simbolo: string; lista: Sinal[] } | null>(null);
  useCanal(simbolo && aberto ? (`sinais:${simbolo}` as const) : null, (lista) => {
    if (simbolo) setSinaisVivo({ simbolo, lista });
  });
  const sinais = sinaisVivo?.simbolo === simbolo ? sinaisVivo.lista : (sinaisQ.dados ?? null);
  const ativosSinal = useMemo(() => (sinais ?? []).filter((s) => s.direcao !== "AGUARDAR"), [sinais]);

  // Alerta sonoro para cada sinal novo (efeito externo, sem estado).
  const vistos = useRef(new Set<string>());
  useEffect(() => {
    let novo = false;
    for (const s of ativosSinal) {
      const chave = `${simbolo}:${s.expiracao}:${s.direcao}:${s.janela_ate}`;
      if (!vistos.current.has(chave)) {
        vistos.current.add(chave);
        novo = true;
      }
    }
    if (novo && som) tocarAlerta();
  }, [ativosSinal, simbolo, som]);

  function adicionarDesenho(d: Desenho) {
    if (!simbolo) return;
    salvar({ desenhos: { ...layout.desenhos, [simbolo]: [...desenhos, d] } });
  }
  function removerDesenho(id: string) {
    if (!simbolo) return;
    salvar({ desenhos: { ...layout.desenhos, [simbolo]: desenhos.filter((d) => d.id !== id) } });
  }

  if (ativosQ.erro) {
    return (
      <main className="p-6">
        <ErroEstado mensagem={ativosQ.erro.message} aoTentarDeNovo={ativosQ.recarregar} />
      </main>
    );
  }

  return (
    <main className="grid min-h-0 flex-1 grid-cols-1 gap-px bg-borda lg:h-[calc(100dvh-3rem-2.6rem)] lg:grid-cols-[200px_minmax(0,1fr)_minmax(340px,400px)] lg:grid-rows-[minmax(0,1fr)]">
      <aside className="bg-painel p-2 lg:overflow-y-auto" aria-label="Lista de ativos">
        <h2 className={`${tituloPainel} hidden px-2 pt-1 pb-2 lg:block`}>Ativos</h2>
        {ativosQ.carregando && ativos.length === 0 ? (
          <Carregando rotulo="Carregando ativos…" />
        ) : ativos.length === 0 ? (
          <Vazio titulo="Nenhum ativo disponível" />
        ) : (
          <div className="overflow-x-auto lg:overflow-visible">
            <ListaAtivos
              ativos={ativos}
              selecionado={simbolo}
              aoSelecionar={(s) => {
                setSimboloEscolhido(s);
                salvar({ simbolo: s });
              }}
            />
          </div>
        )}
      </aside>

      <section className="flex min-h-[460px] min-w-0 flex-col bg-painel" aria-label="Gráfico">
        <div className="flex items-center gap-3 border-b border-borda px-3 py-2">
          <h1 className="num text-sm font-semibold">{simbolo ?? "—"}</h1>
          {ativo && <span className="text-xs text-apagado">{ativo.nome}</span>}
          {ativo && !ativo.aberto && <span className="rounded bg-painel-2 px-1.5 py-0.5 text-[10px] font-semibold text-apagado uppercase">Fechado</span>}
          {erroSalvar && (
            <span role="status" className="ml-auto text-[11px] text-alerta">
              Não foi possível salvar no servidor; mantido neste navegador.
            </span>
          )}
        </div>
        <BarraFerramentas
          tempo={tempo}
          aoMudarTempo={(t) => {
            setTempoEscolhido(t);
            salvar({ tempo: t });
          }}
          ferramenta={ferramenta}
          aoMudarFerramenta={setFerramenta}
          indicadores={indicadores}
          aoMudarIndicador={(k, v) => salvar({ indicadores: { ...indicadores, [k]: v } })}
          avancado={avancado}
          desenhos={desenhos}
          aoRemoverDesenho={removerDesenho}
          aoLimparDesenhos={() => simbolo && salvar({ desenhos: { ...layout.desenhos, [simbolo]: [] } })}
          som={som}
          aoMudarSom={setSom}
        />
        {candlesQ.erro ? (
          <div className="p-4">
            <ErroEstado mensagem={candlesQ.erro.message} aoTentarDeNovo={candlesQ.recarregar} />
          </div>
        ) : (
          <div className="relative flex min-h-0 flex-1 flex-col">
            {candlesQ.carregando && candles.length === 0 && (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-painel/60">
                <span role="status" className="text-xs text-apagado">
                  Carregando candles…
                </span>
              </div>
            )}
            <Grafico
              candles={candles}
              indicadores={indicadores}
              paineis={avancado}
              desenhos={desenhos}
              ferramenta={ferramenta}
              aoCriarDesenho={adicionarDesenho}
              rotulo={`Gráfico de candles de ${simbolo ?? ""} em ${tempo}`}
            />
          </div>
        )}
      </section>

      <aside className="flex min-w-0 flex-col gap-px bg-borda lg:overflow-y-auto" aria-label="Sinais e análise">
        <section className="bg-painel px-4 py-3" aria-labelledby="t-sinais">
          <h2 id="t-sinais" className={`${tituloPainel} mb-2`}>
            Sinais por expiração
          </h2>
          {!aberto && ativo ? (
            <p className="py-3 text-sm text-apagado">Mercado fechado: sem sinais fora do horário do ativo.</p>
          ) : sinaisQ.erro && !sinais ? (
            <ErroEstado mensagem={sinaisQ.erro.message} aoTentarDeNovo={sinaisQ.recarregar} />
          ) : (
            <>
              {ativosSinal.length > 0 && simbolo && (
                <div className="mb-3 space-y-2">
                  {ativosSinal.map((s) => (
                    <CartaoSinal key={`${s.expiracao}:${s.janela_ate}`} sinal={s} simbolo={simbolo} />
                  ))}
                </div>
              )}
              <TabelaSinais sinais={sinais} />
            </>
          )}
        </section>
        <section className="flex-1 bg-painel" aria-labelledby="t-analise">
          <h2 id="t-analise" className={`${tituloPainel} px-4 pt-3`}>
            Análise
          </h2>
          <PainelAnalise
            analise={analise}
            modo={usuario?.modo ?? "essencial"}
            aberto={aberto || !ativo}
            erro={analiseQ.erro && !analise ? analiseQ.erro.message : null}
            aoTentarDeNovo={analiseQ.recarregar}
          />
        </section>
      </aside>
    </main>
  );
}

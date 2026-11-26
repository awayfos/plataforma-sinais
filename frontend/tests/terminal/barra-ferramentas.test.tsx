import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BarraFerramentas } from "@/components/terminal/BarraFerramentas";

function montar(tempo: "1m" | "1d" | "1w") {
  return render(
    <BarraFerramentas
      tempo={tempo}
      aoMudarTempo={() => {}}
      ferramenta="cursor"
      aoMudarFerramenta={() => {}}
      indicadores={{ ema: true, bollinger: false, vwap: true, rsi: false, macd: false }}
      aoMudarIndicador={() => {}}
      avancado
      desenhos={[]}
      aoRemoverDesenho={() => {}}
      aoLimparDesenhos={() => {}}
      som={false}
      aoMudarSom={() => {}}
    />,
  );
}

describe("BarraFerramentas", () => {
  it("VWAP (âncora diária 00:00 UTC) só em tempos intradiários", () => {
    const { unmount } = montar("1d");
    expect(screen.getByRole("checkbox", { name: /VWAP/, hidden: true })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: /VWAP/, hidden: true })).not.toBeChecked();
    unmount();
    montar("1m");
    expect(screen.getByRole("checkbox", { name: /VWAP/, hidden: true })).toBeEnabled();
  });
});

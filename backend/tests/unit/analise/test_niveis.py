from sinais.analise.regioes import Niveis


def test_funde_no_nivel_mais_proximo() -> None:
    n = Niveis(maximo=10, toques_max=10)
    n.adicionar(100.0, tolerancia=0.0, t=0)
    n.adicionar(101.0, tolerancia=0.0, t=1)
    n.adicionar(100.9, tolerancia=0.5, t=2)
    precos = sorted(round(p, 2) for p, _ in n.niveis())
    assert precos == [100.0, 100.95]


def test_toques_limitados() -> None:
    n = Niveis(maximo=10, toques_max=3)
    for t in range(6):
        n.adicionar(100.0, tolerancia=0.1, t=t)
    assert n.niveis() == [(100.0, 3)]


def test_descarta_o_tocado_ha_mais_tempo() -> None:
    n = Niveis(maximo=2, toques_max=10)
    n.adicionar(100.0, tolerancia=0.1, t=0)
    n.adicionar(200.0, tolerancia=0.1, t=1)
    n.adicionar(100.0, tolerancia=0.1, t=2)
    n.adicionar(300.0, tolerancia=0.1, t=3)
    assert sorted(p for p, _ in n.niveis()) == [100.0, 300.0]

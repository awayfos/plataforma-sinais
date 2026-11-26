from sinais.situacoes.zonas import Zonas

M = 60_000
H = 60 * M


def test_pivo_dentro_da_tolerancia_vira_toque_do_mesmo_nivel() -> None:
    z = Zonas()
    z.adicionar(100.0, 0.5, 0)
    z.adicionar(100.4, 0.5, 10 * M)
    z.adicionar(102.0, 0.5, 20 * M)
    niveis = sorted(z.niveis(), key=lambda n: n.preco)
    assert len(niveis) == 2
    assert niveis[0].toques == [0, 10 * M]
    assert abs(niveis[0].preco - 100.2) < 1e-9


def test_toques_mais_velhos_que_a_janela_nao_contam() -> None:
    z = Zonas()
    for t in (0, 2 * H, 3 * H, 5 * H):
        z.adicionar(100.0, 0.5, t)
    (n,) = z.niveis()
    assert z.toques_em(n, 5 * H, 4 * H) == 3  # 0 h fica de fora
    assert z.toques_em(n, 6 * H + 1, 4 * H) == 2


def test_rompidos_de_alta_e_de_baixa() -> None:
    z = Zonas()
    z.adicionar(100.0, 0.5, 0)
    z.adicionar(105.0, 0.5, 0)
    assert [n.preco for n in z.rompidos(99.0, 100.5)] == [100.0]
    assert [n.preco for n in z.rompidos(106.0, 104.0)] == [105.0]
    assert [n.preco for n in z.rompidos(99.0, 106.0)] == [100.0, 105.0]
    assert z.rompidos(100.0, 100.0) == []


def test_minutos_entre_os_dois_ultimos_toques_da_janela() -> None:
    z = Zonas()
    for t in (0, 30 * M, 75 * M):
        z.adicionar(100.0, 0.5, t)
    (n,) = z.niveis()
    assert z.min_entre_toques(n, 80 * M, 4 * H) == 45.0
    z2 = Zonas()
    z2.adicionar(100.0, 0.5, 0)
    assert z2.min_entre_toques(z2.niveis()[0], M, 4 * H) != z2.min_entre_toques(
        z2.niveis()[0], M, 4 * H
    )  # NaN com um toque só


def test_excesso_de_niveis_descarta_o_tocado_ha_mais_tempo() -> None:
    z = Zonas(maximo=2)
    z.adicionar(100.0, 0.1, 0)
    z.adicionar(110.0, 0.1, M)
    z.adicionar(120.0, 0.1, 2 * M)
    assert sorted(n.preco for n in z.niveis()) == [110.0, 120.0]

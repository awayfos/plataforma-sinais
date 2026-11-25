from sinais.dados.provedores.backoff import atraso_backoff


def test_backoff_cresce_e_respeita_teto() -> None:
    sem_jitter = [atraso_backoff(t, aleatorio=lambda: 1.0) for t in range(10)]
    assert sem_jitter[:4] == [1.0, 2.0, 4.0, 8.0]
    assert max(sem_jitter) == 60.0


def test_backoff_com_jitter_entre_metade_e_total() -> None:
    assert atraso_backoff(3, aleatorio=lambda: 0.0) == 4.0
    assert atraso_backoff(3, aleatorio=lambda: 1.0) == 8.0

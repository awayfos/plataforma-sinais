import io
import zipfile

import numpy as np

from sinais.modelos.dados_1s import ler_zip_1s

LINHAS_US = [
    "1735689600000000,100.0,100.5,99.5,100.2,2.0,1735689600999999,200.4,7,1.5,150.3,0",
    "1735689601000000,100.2,100.3,100.1,100.1,0.0,1735689601999999,0.0,0,0.0,0.0,0",
    "1735689602000000,100.1,100.4,100.0,100.3,1.0,1735689602999999,100.3,3,0.25,25.1,0",
]


def _zip(linhas: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("BTCUSDT-1s-2025-01.csv", "\n".join(linhas) + "\n")
    return buf.getvalue()


def test_le_microssegundos_como_ms() -> None:
    df = ler_zip_1s(_zip(LINHAS_US))
    assert df.index.tolist() == [1735689600000, 1735689601000, 1735689602000]
    assert df.index.name == "abertura"
    assert list(df.columns) == ["o", "h", "l", "c", "v", "vb", "n"]
    assert df["n"].tolist() == [7.0, 0.0, 3.0]
    assert df["vb"].tolist() == [1.5, 0.0, 0.25]
    assert df.dtypes.unique().tolist() == [np.dtype("float64")]


def test_le_milissegundos() -> None:
    linhas = [l.replace("000,", ",", 1) for l in LINHAS_US]  # noqa: E741
    df = ler_zip_1s(_zip(linhas))
    assert df.index.tolist() == [1735689600000, 1735689601000, 1735689602000]
    assert df["c"].tolist() == [100.2, 100.1, 100.3]

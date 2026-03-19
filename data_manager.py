import os
from datetime import datetime

import pandas as pd

from utils import converter_para_float


PASTA_DADOS = os.path.join(os.path.dirname(__file__), "data")
ARQUIVO_CONFIG = os.path.join(PASTA_DADOS, "config.xlsx")
ARQUIVO_LANCAMENTOS = os.path.join(PASTA_DADOS, "lancamentos.xlsx")

COLUNAS_LANCAMENTOS = ["id", "tipo", "data", "categoria", "descricao", "valor"]
CATEGORIAS = ["ESSENCIAIS", "VARIAVEIS", "LAZER", "RESERVA", "RECEITA"]
TIPOS = ["DESPESA", "RECEITA"]


def certificar_pasta_e_arquivos() -> None:
    os.makedirs(PASTA_DADOS, exist_ok=True)

    if not os.path.exists(ARQUIVO_CONFIG):
        df = pd.DataFrame(
            [
                {"chave": "salario_mensal", "valor": 0.0},
                {"chave": "valor_nao_utilizavel", "valor": 0.0},
                {"chave": "percentual_essenciais", "valor": 60.0},
                {"chave": "percentual_variaveis", "valor": 20.0},
                {"chave": "percentual_lazer", "valor": 10.0},
                {"chave": "percentual_reserva", "valor": 10.0},
            ]
        )
        df.to_excel(ARQUIVO_CONFIG, index=False, engine="openpyxl")

    if not os.path.exists(ARQUIVO_LANCAMENTOS):
        df = pd.DataFrame(columns=COLUNAS_LANCAMENTOS)
        df.to_excel(ARQUIVO_LANCAMENTOS, index=False, engine="openpyxl")


def carregar_config() -> dict:
    certificar_pasta_e_arquivos()

    try:
        df = pd.read_excel(ARQUIVO_CONFIG, engine="openpyxl")
        config = {row["chave"]: converter_para_float(row["valor"]) for _, row in df.iterrows()}
    except Exception:
        config = {
            "salario_mensal": 0.0,
            "valor_nao_utilizavel": 0.0,
            "percentual_essenciais": 60.0,
            "percentual_variaveis": 20.0,
            "percentual_lazer": 10.0,
            "percentual_reserva": 10.0,
        }
    return config


def salvar_config(config: dict) -> bool:
    certificar_pasta_e_arquivos()

    df = pd.DataFrame(
        [
            {"chave": "salario_mensal", "valor": config.get("salario_mensal", 0.0)},
            {"chave": "valor_nao_utilizavel", "valor": config.get("valor_nao_utilizavel", 0.0)},
            {"chave": "percentual_essenciais", "valor": config.get("percentual_essenciais", 0.0)},
            {"chave": "percentual_variaveis", "valor": config.get("percentual_variaveis", 0.0)},
            {"chave": "percentual_lazer", "valor": config.get("percentual_lazer", 0.0)},
            {"chave": "percentual_reserva", "valor": config.get("percentual_reserva", 0.0)},
        ]
    )
    df.to_excel(ARQUIVO_CONFIG, index=False, engine="openpyxl")
    return True


def carregar_lancamentos() -> pd.DataFrame:
    certificar_pasta_e_arquivos()

    try:
        df = pd.read_excel(ARQUIVO_LANCAMENTOS, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=COLUNAS_LANCAMENTOS)

    if df.empty:
        return df.copy()

    # Conversões seguras
    df = df.copy()
    df["id"] = df["id"].astype(int)
    df["tipo"] = df["tipo"].astype(str)
    df["categoria"] = df["categoria"].astype(str)
    df["descricao"] = df["descricao"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = df["valor"].apply(converter_para_float)

    return df


def salvar_lancamentos(df: pd.DataFrame) -> bool:
    certificar_pasta_e_arquivos()

    df_export = df.copy()
    df_export = df_export[COLUNAS_LANCAMENTOS]
    df_export.to_excel(ARQUIVO_LANCAMENTOS, index=False, engine="openpyxl")
    return True


def gerar_proximo_id(df: pd.DataFrame) -> int:
    if df.empty:
        return 1
    return int(df["id"].max() + 1)

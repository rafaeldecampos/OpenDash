from typing import Dict

import pandas as pd

from utils import converter_para_float

CATEGORIAS_FIXAS = ["ESSENCIAIS", "VARIAVEIS", "LAZER", "RESERVA"]


def calcular_salario_base(salario_mensal: float, valor_nao_utilizavel: float) -> float:
    salario = converter_para_float(salario_mensal)
    nao_utilizavel = converter_para_float(valor_nao_utilizavel)

    salario_base = salario - nao_utilizavel
    if salario_base < 0:
        salario_base = 0.0
    return salario_base


def validar_soma_percentuais(percentuais: Dict[str, float]) -> bool:
    total = sum([converter_para_float(percentuais.get(chave, 0)) for chave in CATEGORIAS_FIXAS])
    return abs(total - 100.0) < 1e-9


def ajustar_percentuais_para_100(percentuais: Dict[str, float]) -> Dict[str, float]:
    percentuais = {k: converter_para_float(v) for k, v in percentuais.items()}
    soma = sum(percentuais.get(f"percentual_{cat.lower()}", 0.0) for cat in CATEGORIAS_FIXAS)
    if abs(soma - 100.0) < 1e-6:
        return percentuais

    diff = 100.0 - soma

    ordenacao = ["percentual_reserva", "percentual_lazer", "percentual_variaveis", "percentual_essenciais"]
    for chave in ordenacao:
        valor = converter_para_float(percentuais.get(chave, 0.0))
        ajuste = valor + diff
        if 0.0 <= ajuste <= 100.0:
            percentuais[chave] = ajuste
            break

    soma_final = sum(percentuais.get(f"percentual_{cat.lower()}", 0.0) for cat in CATEGORIAS_FIXAS)
    if abs(soma_final - 100.0) > 1e-6:
        if soma_final == 0:
            percentuais = {
                "percentual_essenciais": 60.0,
                "percentual_variaveis": 20.0,
                "percentual_lazer": 10.0,
                "percentual_reserva": 10.0,
            }
        else:
            for cat in CATEGORIAS_FIXAS:
                chave = f"percentual_{cat.lower()}"
                percentuais[chave] = converter_para_float(percentuais.get(chave, 0.0)) * (100.0 / soma_final)

    return percentuais


def calcular_distribuicao(salario_base: float, percentuais: Dict[str, float], lancamentos: pd.DataFrame) -> Dict:
    """Retorna o resumo planejado, usado, saldo e percentual usado por categoria."""
    salario_libre = converter_para_float(salario_base)
    percentuais_ = {k: converter_para_float(v) for k, v in percentuais.items()}

    valores_planejados = {}
    usados = {}
    saldos = {}
    percentuais_usados = {}

    # Calcula valores planejados por categoria fixas
    for categoria in CATEGORIAS_FIXAS:
        p = percentuais_.get(f"percentual_{categoria.lower()}", 0.0)
        valores_planejados[categoria] = salario_libre * (p / 100.0)

    # Calcular consumo real de despesas por categoria
    df = lancamentos.copy()
    if df is None or df.empty:
        df = pd.DataFrame(columns=["tipo", "categoria", "valor"])

    df["valor"] = df["valor"].apply(converter_para_float)
    df["tipo"] = df["tipo"].astype(str).str.upper().fillna("")
    df["categoria"] = df["categoria"].astype(str).str.upper().fillna("")

    for categoria in CATEGORIAS_FIXAS:
        filtro = (df["tipo"] == "DESPESA") & (df["categoria"] == categoria)
        usados[categoria] = float(df.loc[filtro, "valor"].sum())

        saldos[categoria] = valores_planejados[categoria] - usados[categoria]

        if valores_planejados[categoria] > 0:
            percentuais_usados[categoria] = (usados[categoria] / valores_planejados[categoria]) * 100.0
        else:
            percentuais_usados[categoria] = 0.0

    total_receitas = float(df.loc[df["tipo"] == "RECEITA", "valor"].sum())
    total_despesas = float(df.loc[df["tipo"] == "DESPESA", "valor"].sum())

    # Saldo global trata receita - despesa
    saldo_global = total_receitas - total_despesas

    # Saldo planejado de categorias
    saldo_planejado = sum(valores_planejados.values()) - total_despesas

    return {
        "salario_base": salario_libre,
        "valores_planejados": valores_planejados,
        "usados": usados,
        "saldos": saldos,
        "percentuais_usados": percentuais_usados,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_global": saldo_global,
        "saldo_planejado": saldo_planejado,
    }

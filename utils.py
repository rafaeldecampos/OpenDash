import decimal
from typing import Any

from babel.numbers import format_currency


def moeda_br(valor: Any) -> str:
    """Formata valor numérico no padrão brasileiro R$ 1.000,00."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"

    # Usa Babel para formato BRL
    return format_currency(numero, "BRL", locale="pt_BR")


def converter_para_float(valor: Any) -> float:
    """Converte texto/float/int para float com segurança e coerência."""
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        texto = str(valor).replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(texto)
    except Exception:
        return 0.0


def validar_percentual(percentual: float) -> float:
    """Normaliza percentual para float em 0..100."""
    try:
        retorno = float(percentual)
    except (TypeError, ValueError):
        retorno = 0.0
    if retorno < 0:
        retorno = 0.0
    if retorno > 100:
        retorno = 100.0
    return retorno

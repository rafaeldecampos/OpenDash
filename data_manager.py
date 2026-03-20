import os
from datetime import datetime
from pathlib import Path
import io

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import gdown

from utils import converter_para_float

# Carrega configurações
ENV_PATH = Path(__file__).parents[0] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

PASTA_DADOS = os.path.join(os.path.dirname(__file__), "data")
ARQUIVO_CONFIG_LOCAL = os.path.join(PASTA_DADOS, "config.xlsx")
ARQUIVO_LANCAMENTOS_LOCAL = os.path.join(PASTA_DADOS, "lancamentos.xlsx")

# IDs do Google Drive (obtidos da senha compartilhada)
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "14K09D1XwWXBDfnDWO89NX8MWb48iSvGR")
ARQUIVO_CONFIG_NOME = "config.xlsx"
ARQUIVO_LANCAMENTOS_NOME = "lancamentos.xlsx"

COLUNAS_LANCAMENTOS = ["id", "tipo", "data", "categoria", "descricao", "valor"]
CATEGORIAS = ["ESSENCIAIS", "VARIAVEIS", "LAZER", "RESERVA", "RECEITA"]
TIPOS = ["DESPESA", "RECEITA"]

# Cache de IDs de arquivos no Drive
_arquivo_ids_cache = {}


def _obter_credenciais_drive():
    """Obtém credenciais para acessar Google Drive usando gdown"""
    try:
        # Tenta carregar com credenciais de serviço se existir
        creds_path = Path(__file__).parents[0] / "service_account.json"
        if creds_path.exists():
            return Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
    except Exception:
        pass
    return None


def _encontrar_arquivo_no_drive(pasta_id: str, nome_arquivo: str) -> str:
    """Encontra o ID de um arquivo dentro de uma pasta no Google Drive"""
    if (pasta_id, nome_arquivo) in _arquivo_ids_cache:
        return _arquivo_ids_cache[(pasta_id, nome_arquivo)]
    
    try:
        creds = _obter_credenciais_drive()
        if creds:
            service = build('drive', 'v3', credentials=creds)
            query = f"'{pasta_id}' in parents and name='{nome_arquivo}' and trashed=false"
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1).execute()
            files = results.get('files', [])
            if files:
                arquivo_id = files[0]['id']
                _arquivo_ids_cache[(pasta_id, nome_arquivo)] = arquivo_id
                return arquivo_id
    except Exception as e:
        print(f"Erro ao buscar arquivo {nome_arquivo}: {e}")
    
    return None


def _baixar_arquivo_do_drive(arquivo_id: str, caminho_local: str) -> bool:
    """Baixa um arquivo do Google Drive para o caminho local"""
    try:
        # URL de download do Google Drive
        url = f"https://drive.google.com/uc?id={arquivo_id}"
        gdown.download(url, caminho_local, quiet=True)
        return os.path.exists(caminho_local)
    except Exception as e:
        print(f"Erro ao baixar arquivo {arquivo_id}: {e}")
        return False


def _fazer_upload_arquivo_drive(caminho_local: str, arquivo_id: str) -> bool:
    """Faz upload de um arquivo para o Google Drive, substituindo o existente"""
    try:
        creds = _obter_credenciais_drive()
        if creds:
            service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {'name': os.path.basename(caminho_local)}
            media = MediaFileUpload(caminho_local, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            # Atualiza o arquivo existente
            service.files().update(fileId=arquivo_id, body=file_metadata, media_body=media, fields='id').execute()
            return True
    except Exception as e:
        print(f"Erro ao fazer upload de arquivo: {e}")
        return False
    
    return False


def certificar_pasta_e_arquivos() -> None:
    """Garante que a pasta local existe e sincroniza com o Google Drive"""
    os.makedirs(PASTA_DADOS, exist_ok=True)

    # Tenta baixar config do Drive
    config_id = _encontrar_arquivo_no_drive(GOOGLE_DRIVE_FOLDER_ID, ARQUIVO_CONFIG_NOME)
    if config_id:
        _baixar_arquivo_do_drive(config_id, ARQUIVO_CONFIG_LOCAL)
    
    # Se arquivo não existe localmente, cria padrão
    if not os.path.exists(ARQUIVO_CONFIG_LOCAL):
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
        df.to_excel(ARQUIVO_CONFIG_LOCAL, index=False, engine="openpyxl")
        
        # Faz upload se credenciais disponíveis
        if config_id:
            _fazer_upload_arquivo_drive(ARQUIVO_CONFIG_LOCAL, config_id)

    # Tenta baixar lancamentos do Drive
    lancamentos_id = _encontrar_arquivo_no_drive(GOOGLE_DRIVE_FOLDER_ID, ARQUIVO_LANCAMENTOS_NOME)
    if lancamentos_id:
        _baixar_arquivo_do_drive(lancamentos_id, ARQUIVO_LANCAMENTOS_LOCAL)
    
    # Se arquivo não existe localmente, cria padrão
    if not os.path.exists(ARQUIVO_LANCAMENTOS_LOCAL):
        df = pd.DataFrame(columns=COLUNAS_LANCAMENTOS)
        df.to_excel(ARQUIVO_LANCAMENTOS_LOCAL, index=False, engine="openpyxl")
        
        # Faz upload se credenciais disponíveis
        if lancamentos_id:
            _fazer_upload_arquivo_drive(ARQUIVO_LANCAMENTOS_LOCAL, lancamentos_id)


def carregar_config() -> dict:
    certificar_pasta_e_arquivos()

    try:
        df = pd.read_excel(ARQUIVO_CONFIG_LOCAL, engine="openpyxl")
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
    df.to_excel(ARQUIVO_CONFIG_LOCAL, index=False, engine="openpyxl")
    
    # Faz upload para o Drive
    config_id = _encontrar_arquivo_no_drive(GOOGLE_DRIVE_FOLDER_ID, ARQUIVO_CONFIG_NOME)
    if config_id:
        _fazer_upload_arquivo_drive(ARQUIVO_CONFIG_LOCAL, config_id)
    
    return True


def carregar_lancamentos() -> pd.DataFrame:
    certificar_pasta_e_arquivos()

    try:
        df = pd.read_excel(ARQUIVO_LANCAMENTOS_LOCAL, engine="openpyxl")
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
    df_export.to_excel(ARQUIVO_LANCAMENTOS_LOCAL, index=False, engine="openpyxl")
    
    # Faz upload para o Drive
    lancamentos_id = _encontrar_arquivo_no_drive(GOOGLE_DRIVE_FOLDER_ID, ARQUIVO_LANCAMENTOS_NOME)
    if lancamentos_id:
        _fazer_upload_arquivo_drive(ARQUIVO_LANCAMENTOS_LOCAL, lancamentos_id)
    
    return True


def gerar_proximo_id(df: pd.DataFrame) -> int:
    if df.empty:
        return 1
    return int(df["id"].max() + 1)

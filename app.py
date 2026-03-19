import os
from pathlib import Path

import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from utils import moeda_br, converter_para_float, validar_percentual
from data_manager import (
    certificar_pasta_e_arquivos,
    carregar_config,
    salvar_config,
    carregar_lancamentos,
    salvar_lancamentos,
    gerar_proximo_id,
    CATEGORIAS,
    TIPOS,
)
from calculos import calcular_salario_base, validar_soma_percentuais, calcular_distribuicao, ajustar_percentuais_para_100

ENV_PATH = Path(__file__).parents[0] / ".env"


def carregar_credenciais():
    if not ENV_PATH.exists():
        ENV_PATH.write_text("USER_APP=admin\nPASS_APP=admin\n", encoding="utf-8")

    load_dotenv(dotenv_path=ENV_PATH)
    usuario = os.getenv("USER_APP", "admin")
    senha = os.getenv("PASS_APP", "admin")

    return usuario, senha


def salvar_credenciais(usuario: str, senha: str):
    ENV_PATH.write_text(f"USER_APP={usuario}\nPASS_APP={senha}\n", encoding="utf-8")
    load_dotenv(dotenv_path=ENV_PATH, override=True)


def pagina_login():
    st.title("Login")
    st.info("Informe as credenciais para acessar o OpenDash.")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        usuario_salvo, senha_salva = carregar_credenciais()
        if usuario == usuario_salvo and senha == senha_salva:
            st.session_state["autenticado"] = True
            st.success("Login efetuado com sucesso!")
            st.rerun()
        else:
            st.error("Credenciais inválidas. Verifique e tente novamente.")
            return False

    return False


def aplicar_ajustes_de_sessao(config):
    if st.session_state.get("restaurar"):
        st.session_state["salario_mensal"] = converter_para_float(config.get("salario_mensal", 0.0))
        st.session_state["valor_nao_utilizavel"] = converter_para_float(config.get("valor_nao_utilizavel", 0.0))
        st.session_state["percentual_essenciais"] = converter_para_float(config.get("percentual_essenciais", 60.0))
        st.session_state["percentual_variaveis"] = converter_para_float(config.get("percentual_variaveis", 20.0))
        st.session_state["percentual_lazer"] = converter_para_float(config.get("percentual_lazer", 10.0))
        st.session_state["percentual_reserva"] = converter_para_float(config.get("percentual_reserva", 10.0))
        st.session_state["mensagem_config"] = "Valores padrão restaurados."
        st.session_state["restaurar"] = False

    if st.session_state.get("ajuste_percentuais"):
        ajuste = st.session_state.pop("ajuste_percentuais")
        st.session_state["percentual_essenciais"] = ajuste["percentual_essenciais"]
        st.session_state["percentual_variaveis"] = ajuste["percentual_variaveis"]
        st.session_state["percentual_lazer"] = ajuste["percentual_lazer"]
        st.session_state["percentual_reserva"] = ajuste["percentual_reserva"]
        st.session_state["mensagem_config"] = "Percentuais ajustados automaticamente para totalizar 100%."


def iniciar_app():
    st.set_page_config(page_title="OpenDash - Controle Financeiro", layout="wide")
    st.title("OpenDash - Controle Financeiro Pessoal")
    st.write("Ferramenta de educação financeira e acompanhamento de despesas e receitas.")

    certificar_pasta_e_arquivos()

    if not st.session_state.get("autenticado", False):
        pagina_login()
        return

    pagina = st.sidebar.selectbox(
        "Navegação",
        ["Visão Geral", "Configurações", "Lançamentos", "Orientação Financeira"],
    )

    config = carregar_config()
    df_lancamentos = carregar_lancamentos()

    if pagina == "Visão Geral":
        pagina_visao_geral(config, df_lancamentos)
    elif pagina == "Configurações":
        pagina_configuracoes(config)
    elif pagina == "Lançamentos":
        pagina_lancamentos(df_lancamentos, config)
    elif pagina == "Orientação Financeira":
        pagina_orientacao(config)


def ajustar_percentual_alterado(chave_alterada: str):
    e = converter_para_float(st.session_state.get("percentual_essenciais", 0.0))
    v = converter_para_float(st.session_state.get("percentual_variaveis", 0.0))
    l = converter_para_float(st.session_state.get("percentual_lazer", 0.0))
    r = converter_para_float(st.session_state.get("percentual_reserva", 0.0))

    soma = e + v + l + r
    if abs(soma - 100.0) < 1e-6:
        st.session_state["mensagem_config"] = ""
        return

    st.session_state["mensagem_config"] = (
        f"Soma atual dos percentuais: {soma:.2f}%. "
        "Ajuste será aplicado automaticamente ao salvar as configurações."
    )


def pagina_visao_geral(config: dict, df_lancamentos: pd.DataFrame):
    st.header("Visão Geral")

    salario_mensal = converter_para_float(config.get("salario_mensal", 0.0))
    valor_nao_utilizavel = converter_para_float(config.get("valor_nao_utilizavel", 0.0))

    percentuais = {
        "percentual_essenciais": converter_para_float(config.get("percentual_essenciais", 0.0)),
        "percentual_variaveis": converter_para_float(config.get("percentual_variaveis", 0.0)),
        "percentual_lazer": converter_para_float(config.get("percentual_lazer", 0.0)),
        "percentual_reserva": converter_para_float(config.get("percentual_reserva", 0.0)),
    }

    soma_val = sum(percentuais.values())
    if not validar_soma_percentuais(percentuais):
        st.error("A soma dos percentuais deve ser exatamente 100%. Ajuste em Configurações.")
        return

    salario_base = calcular_salario_base(salario_mensal, valor_nao_utilizavel)
    resumo = calcular_distribuicao(salario_base, percentuais, df_lancamentos)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Salário mensal", moeda_br(salario_mensal))
    col2.metric("Não utilizável", moeda_br(valor_nao_utilizavel))
    col3.metric("Salário base", moeda_br(resumo["salario_base"]))
    col4.metric("Receitas", moeda_br(resumo["total_receitas"]))
    col5.metric("Despesas", moeda_br(resumo["total_despesas"]))

    st.markdown("---")
    st.subheader("Distribuição planejada e uso por categoria")

    status = []

    for categoria in ["ESSENCIAIS", "VARIAVEIS", "LAZER", "RESERVA"]:
        planejado = resumo["valores_planejados"][categoria]
        usado = resumo["usados"][categoria]
        saldo = resumo["saldos"][categoria]
        pct_usado = resumo["percentuais_usados"][categoria]

        cards = st.columns(4)
        cards[0].metric(f"{categoria} planejado", moeda_br(planejado))
        cards[1].metric(f"{categoria} usado", moeda_br(usado), delta=f"{pct_usado:.1f}%")
        cards[2].metric(f"{categoria} restante", moeda_br(saldo))
        cards[3].metric(f"consumo {categoria}", f"{pct_usado:.2f}%")

        if pct_usado >= 85 and pct_usado < 100:
            status.append(f"Você já usou {pct_usado:.1f}% do valor destinado a {categoria}.")
        if pct_usado >= 100:
            status.append(f"O {categoria} ultrapassou o limite planejado ({pct_usado:.1f}%).")
        if categoria == "RESERVA" and usado > 0:
            status.append("A Reserva foi utilizada este mês. Verifique o motivo do uso.")

    st.markdown("### Alertas")
    if status:
        for alerta in status:
            st.warning(alerta)
    else:
        st.success("Nenhum alerta no momento. Boa gestão!")

    st.markdown("---")
    st.subheader("Saldo geral")
    st.write(f"Saldo no mês (receitas - despesas): **{moeda_br(resumo['saldo_global'])}**")


def pagina_configuracoes(config: dict):
    st.header("Configurações")
    st.write("Cadastre os parâmetros base do sistema, incluindo salário, valor não utilizável e percentuais.")

    if "salario_mensal" not in st.session_state:
        st.session_state["salario_mensal"] = converter_para_float(config.get("salario_mensal", 0.0))
        st.session_state["valor_nao_utilizavel"] = converter_para_float(config.get("valor_nao_utilizavel", 0.0))
        st.session_state["percentual_essenciais"] = converter_para_float(config.get("percentual_essenciais", 60.0))
        st.session_state["percentual_variaveis"] = converter_para_float(config.get("percentual_variaveis", 20.0))
        st.session_state["percentual_lazer"] = converter_para_float(config.get("percentual_lazer", 10.0))
        st.session_state["percentual_reserva"] = converter_para_float(config.get("percentual_reserva", 10.0))
        st.session_state["mensagem_config"] = ""

    aplicar_ajustes_de_sessao(config)

    salario_mensal = st.number_input("Salário mensal (R$)", min_value=0.0, step=100.0, key="salario_mensal")
    valor_nao_utilizavel = st.number_input("Valores não utilizáveis (transporte, benefícios, etc.)", min_value=0.0, step=50.0, key="valor_nao_utilizavel")

    percentual_essenciais = st.number_input(
        "Percentual Essenciais (%)",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="percentual_essenciais",
        on_change=ajustar_percentual_alterado,
        args=("percentual_essenciais",),
    )
    percentual_variaveis = st.number_input(
        "Percentual Variáveis (%)",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="percentual_variaveis",
        on_change=ajustar_percentual_alterado,
        args=("percentual_variaveis",),
    )
    percentual_lazer = st.number_input(
        "Percentual Lazer (%)",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="percentual_lazer",
        on_change=ajustar_percentual_alterado,
        args=("percentual_lazer",),
    )
    percentual_reserva = st.number_input(
        "Percentual Reserva (%)",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="percentual_reserva",
        on_change=ajustar_percentual_alterado,
        args=("percentual_reserva",),
    )

    soma = percentual_essenciais + percentual_variaveis + percentual_lazer + percentual_reserva
    st.info(f"Soma atual dos percentuais: {soma:.2f}%")

    if st.session_state.get("mensagem_config"):
        st.success(st.session_state["mensagem_config"])

    col1, col2 = st.columns(2)
    if col1.button("Salvar Configurações"):
        percentuais = {
            "percentual_essenciais": percentual_essenciais,
            "percentual_variaveis": percentual_variaveis,
            "percentual_lazer": percentual_lazer,
            "percentual_reserva": percentual_reserva,
        }

        if not validar_soma_percentuais(percentuais):
            percentuais_ajustados = ajustar_percentuais_para_100(percentuais)
            salvar_config({
                "salario_mensal": salario_mensal,
                "valor_nao_utilizavel": valor_nao_utilizavel,
                **percentuais_ajustados,
            })

            st.session_state["mensagem_config"] = (
                "A soma dos percentuais foi ajustada automaticamente para 100%. "
                "Verifique os valores abaixo e salve novamente se desejar."
            )
            st.success("Configurações salvas com percentuais ajustados automaticamente.")
            st.rerun()
        else:
            salvar_config({
                "salario_mensal": salario_mensal,
                "valor_nao_utilizavel": valor_nao_utilizavel,
                **percentuais,
            })
            st.session_state["mensagem_config"] = ""
            st.success("Configurações salvas com sucesso.")
            st.rerun()

            st.rerun()

    if col2.button("Restaurar padrões"):  # corresponde aos valores iniciais
        st.session_state["restaurar"] = True
        st.rerun()



def pagina_lancamentos(df_lancamentos: pd.DataFrame, config: dict):
    st.header("Lançamentos")
    st.write("Inclua, filtre, edite e exclua receitas e despesas. Todos os dados são salvos em Excel.")

    st.markdown("---")
    st.subheader("Filtros")
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    tipo_filtro = col_a.selectbox("Filtrar por tipo", ["Todos"] + TIPOS, index=0)
    categoria_filtro = col_b.selectbox("Filtrar por categoria", ["Todos"] + CATEGORIAS, index=0)

    data_min = col_c.date_input(
        "Data início",
        value=df_lancamentos["data"].min().date() if not df_lancamentos.empty else datetime.today().date(),
    )
    data_max = col_d.date_input(
        "Data fim",
        value=df_lancamentos["data"].max().date() if not df_lancamentos.empty else datetime.today().date(),
    )
    descricao_filtro = col_e.text_input("Filtrar descrição")

    df_filtrado = df_lancamentos.copy()

    if tipo_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["tipo"] == tipo_filtro]
    if categoria_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_filtro]

    if not df_filtrado.empty and "data" in df_filtrado.columns:
        df_filtrado = df_filtrado[(df_filtrado["data"] >= pd.to_datetime(data_min)) & (df_filtrado["data"] <= pd.to_datetime(data_max))]

    if descricao_filtro.strip():
        df_filtrado = df_filtrado[df_filtrado["descricao"].str.contains(descricao_filtro, case=False, na=False)]

    if not df_filtrado.empty:
        total_receitas = df_filtrado[df_filtrado["tipo"] == "RECEITA"]["valor"].sum()
        total_despesas = df_filtrado[df_filtrado["tipo"] == "DESPESA"]["valor"].sum()
        saldo_filtrado = total_receitas - total_despesas
    else:
        total_receitas = 0.0
        total_despesas = 0.0
        saldo_filtrado = 0.0

    st.write(f"Receitas filtradas: **{moeda_br(total_receitas)}**")
    st.write(f"Despesas filtradas: **{moeda_br(total_despesas)}**")
    st.write(f"Saldo filtrado: **{moeda_br(saldo_filtrado)}**")

    st.markdown("---")

    salario_mensal = converter_para_float(config.get("salario_mensal", 0.0))
    valor_nao_utilizavel = converter_para_float(config.get("valor_nao_utilizavel", 0.0))
    percentual_essenciais = converter_para_float(config.get("percentual_essenciais", 60.0))
    percentual_variaveis = converter_para_float(config.get("percentual_variaveis", 20.0))
    percentual_lazer = converter_para_float(config.get("percentual_lazer", 10.0))
    percentual_reserva = converter_para_float(config.get("percentual_reserva", 10.0))

    percentuais = {
        "percentual_essenciais": percentual_essenciais,
        "percentual_variaveis": percentual_variaveis,
        "percentual_lazer": percentual_lazer,
        "percentual_reserva": percentual_reserva,
    }

    salario_base = calcular_salario_base(salario_mensal, valor_nao_utilizavel)
    resumo_config = calcular_distribuicao(salario_base, percentuais, df_lancamentos)

    st.markdown("### Configuração atual e valores planejados")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Salário bruto", moeda_br(salario_mensal))
    col2.metric("Não utilizável", moeda_br(valor_nao_utilizavel))
    col3.metric("Salário base (bruto - não utilizável)", moeda_br(salario_base))
    col4.metric("Receita total", moeda_br(resumo_config["total_receitas"]))
    col5.metric("Despesa total", moeda_br(resumo_config["total_despesas"]))

    if salario_mensal <= 0:
        st.warning(
            "Salário bruto está em R$ 0,00. Atualize em Configurações para refletir seus ganhos reais."
        )

    if valor_nao_utilizavel > salario_mensal:
        st.error(
            "O valor não utilizável não pode exceder o salário bruto. Ajuste os valores em Configurações."
        )

    st.markdown("---")
    st.subheader("Tabela de lançamentos")

    if df_filtrado.empty:
        st.info("Nenhum registro encontrado com os filtros aplicados.")
        df_mostra = pd.DataFrame(columns=["id", "tipo", "data", "categoria", "descricao", "valor", "status"])
    else:
        df_mostra = df_filtrado.sort_values(by="data", ascending=False).reset_index(drop=True)
        df_mostra["data"] = pd.to_datetime(df_mostra["data"]).dt.date

        # Validação individual por linha baseada em configurações
        valores_planejados = resumo_config["valores_planejados"]
        warnings = []
        total_por_categoria = df_mostra[df_mostra["tipo"] == "DESPESA"].groupby("categoria")["valor"].sum().to_dict()

        for categoria in ["ESSENCIAIS", "VARIAVEIS", "LAZER", "RESERVA"]:
            gasto = total_por_categoria.get(categoria, 0.0)
            planejado = valores_planejados.get(categoria, 0.0)
            if planejado > 0 and gasto > planejado:
                warnings.append(
                    f"Gasto em {categoria} ({moeda_br(gasto)}) está acima do planejado ({moeda_br(planejado)})."
                )

        if warnings:
            for w in warnings:
                st.warning(w)

        df_mostra["status"] = ""
        for idx, row in df_mostra.iterrows():
            if row["tipo"] == "DESPESA" and row["categoria"] in valores_planejados:
                planejado_cat = valores_planejados[row["categoria"]]
                gasto_cat = total_por_categoria.get(row["categoria"], 0.0)
                if planejado_cat > 0 and gasto_cat > planejado_cat:
                    df_mostra.at[idx, "status"] = "Atenção: categoria ultrapassou limite planejado"

        column_config = None
        if hasattr(st, "column_config"):
            try:
                column_config = {
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS),
                    "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS),
                    "data": st.column_config.DateColumn("Data"),
                    "descricao": st.column_config.TextColumn("Descrição"),
                    "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                }
            except Exception:
                column_config = None

        edicao = None
        if hasattr(st, "data_editor"):
            ad_params = {"num_rows": "dynamic", "use_container_width": True}
            if column_config is not None:
                ad_params["column_config"] = column_config
            edicao = st.data_editor(df_mostra, **ad_params)
        elif hasattr(st, "experimental_data_editor"):
            # experimental_data_editor pode não ter column_config
            if column_config is not None:
                try:
                    edicao = st.experimental_data_editor(df_mostra, column_config=column_config, num_rows="dynamic", use_container_width=True)
                except Exception:
                    edicao = st.experimental_data_editor(df_mostra, num_rows="dynamic", use_container_width=True)
            else:
                edicao = st.experimental_data_editor(df_mostra, num_rows="dynamic", use_container_width=True)
        else:
            st.warning("Seu Streamlit não suporta edição de tabela. Atualize para uma versão mais recente.")
            st.write(df_mostra)

        if edicao is not None:
            salvar_alteracao = st.button("Salvar alterações da tabela")

            if salvar_alteracao:
                try:
                    # Concorda com a edição completa do arquivo, sincroniza IDs e datas
                    edicao["data"] = pd.to_datetime(edicao["data"], errors="coerce")
                    edicao["valor"] = edicao["valor"].apply(converter_para_float)

                    # Remove linhas totalmente vazias que aparecem no editor dinâmico
                    edicao = edicao.dropna(how="all", subset=["tipo", "categoria", "data", "descricao", "valor"])

                    # Força IDs imutáveis para linhas originais e autoincrement para novas
                    id_original = df_mostra["id"].tolist()
                    proximo_id = int(df_lancamentos["id"].max()) if not df_lancamentos.empty else 0

                    for idx in range(len(edicao)):
                        if idx < len(id_original):
                            edicao.at[idx, "id"] = int(id_original[idx])
                        else:
                            proximo_id += 1
                            edicao.at[idx, "id"] = proximo_id

                    edicao["id"] = edicao["id"].astype(int)

                    for _, row in edicao.iterrows():
                        if pd.isna(row["tipo"]) or row["tipo"] not in TIPOS:
                            raise ValueError("Tipo inválido em alguma linha")
                        if pd.isna(row["categoria"]) or row["categoria"] not in CATEGORIAS:
                            raise ValueError("Categoria inválida em alguma linha")
                        if pd.isna(row["data"]):
                            raise ValueError("Data inválida em alguma linha")
                        if pd.isna(row["descricao"]) or str(row["descricao"]).strip() == "":
                            raise ValueError("Descrição obrigatória em alguma linha")
                        if converter_para_float(row["valor"]) <= 0:
                            raise ValueError("Valor deve ser maior que zero em alguma linha")

                    # Verifique limites por categoria a partir da configuração
                    despesas_atualizadas = edicao[edicao["tipo"] == "DESPESA"].groupby("categoria")["valor"].sum().to_dict()
                    for cat, total_desp in despesas_atualizadas.items():
                        planejado_cat = resumo_config["valores_planejados"].get(cat, 0.0)
                        if total_desp > planejado_cat:
                            raise ValueError(
                                f"A despesa total em {cat} ({moeda_br(total_desp)}) excede o planejado ({moeda_br(planejado_cat)})." +
                                " Ajuste o valor da linha antes de salvar."
                            )

                    salvar_lancamentos(edicao)
                    st.success("Alterações salvas com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar alterações: {e}")

    with st.expander("Adicionar novo lançamento", expanded=False):
        with st.form("form_novo_lancamento"):
            tipo = st.selectbox("Tipo", TIPOS)
            data_lancamento = st.date_input("Data", value=datetime.today())
            categoria = st.selectbox("Categoria", [c for c in CATEGORIAS if c != "RECEITA"] if tipo == "DESPESA" else ["RECEITA"])
            descricao = st.text_input("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, value=0.0, step=10.0)
            incluir = st.form_submit_button("Adicionar")

        if incluir:
            if valor <= 0:
                st.error("O valor deve ser maior do que zero.")
            elif descricao.strip() == "":
                st.error("A descrição é obrigatória.")
            else:
                if tipo == "DESPESA":
                    gasto_atual = df_lancamentos[(df_lancamentos["tipo"] == "DESPESA") & (df_lancamentos["categoria"] == categoria)]["valor"].sum()
                    planejado_cat = resumo_config["valores_planejados"].get(categoria, 0.0)
                    if gasto_atual + float(valor) > planejado_cat:
                        st.error(
                            f"Não é possível adicionar: ao somar R$ {moeda_br(valor)} em {categoria}, "
                            f"o total excederia o planejado de {moeda_br(planejado_cat)} (atual {moeda_br(gasto_atual)}). "
                            "Corrija o valor ou selecione outra categoria."
                        )
                        st.warning("Pressione ESC para cancelar a linha temporária no editor e tente novamente.")
                        st.stop()

                novo_id = gerar_proximo_id(df_lancamentos)
                novo_lanc = {
                    "id": novo_id,
                    "tipo": tipo,
                    "data": pd.to_datetime(data_lancamento),
                    "categoria": categoria,
                    "descricao": descricao.strip(),
                    "valor": float(valor),
                }
                df_lancamentos = pd.concat([df_lancamentos, pd.DataFrame([novo_lanc])], ignore_index=True)
                salvar_lancamentos(df_lancamentos)
                st.success("Lançamento adicionado com sucesso.")

        ids_para_excluir = st.multiselect("Selecione IDs para deletar", options=df_mostra["id"].tolist())
        if st.button("Excluir selecionados"):
            if ids_para_excluir:
                df_restante = df_lancamentos[~df_lancamentos["id"].isin(ids_para_excluir)]
                salvar_lancamentos(df_restante)
                st.success(f"{len(ids_para_excluir)} registro(s) excluído(s). Recarregue a página.")
            else:
                st.warning("Nenhum ID selecionado para exclusão.")


def pagina_orientacao(config: dict):
    st.header("Orientação Financeira")
    st.write("Entenda o papel de cada categoria e como usar melhor o seu dinheiro.")

    percentual_essenciais = converter_para_float(config.get("percentual_essenciais", 0.0))
    percentual_variaveis = converter_para_float(config.get("percentual_variaveis", 0.0))
    percentual_lazer = converter_para_float(config.get("percentual_lazer", 0.0))
    percentual_reserva = converter_para_float(config.get("percentual_reserva", 0.0))

    st.markdown("### Percentuais atuais")
    st.write(f"- Essenciais: **{percentual_essenciais:.1f}%**")
    st.write(f"- Variáveis: **{percentual_variaveis:.1f}%**")
    st.write(f"- Lazer: **{percentual_lazer:.1f}%**")
    st.write(f"- Reserva: **{percentual_reserva:.1f}%**")

    st.markdown("### O que significa cada categoria")

    st.subheader("Essenciais")
    st.write("Gastos necessários para viver e funcionar no mês. Ex: aluguel, água, luz, internet, remédio, mercado básico, transporte para trabalho.")

    st.subheader("Variáveis")
    st.write("Gastos do dia a dia que variam e exigem controle. Ex: mercado extra, lanche, gasolina fora do previsto, farmácia eventual, pequenas compras.")

    st.subheader("Lazer")
    st.write("Gastos com prazer e diversão. Ex: sair para comer, cinema, jogos, delivery por vontade, passeio.")

    st.subheader("Reserva")
    st.write("Dinheiro protegido para emergências ou segurança. Ex: imprevistos, problemas de saúde, conserto urgente, mês apertado.")

    st.markdown("---")
    st.write("Use esses percentuais como guia e ajuste sempre que o seu planejamento mudar. Fique atento à categoria Reserva para não perder rastreio de gastos emergenciais.")


if __name__ == "__main__":
    iniciar_app()

import pandas as pd
import streamlit as st
import uuid
import os

ATENDIMENTOS_ARQUIVO = "atendimentos.xlsx"
AVALIACOES_ARQUIVO = "avaliacoes_links.csv"
RESPOSTAS_ARQUIVO = "avaliacoes_respostas.csv"

st.set_page_config(page_title="Avaliação Vavivê", layout="centered")

def carregar_bases():
    # Carrega atendimentos
    if os.path.exists(ATENDIMENTOS_ARQUIVO):
        df_atend = pd.read_excel(ATENDIMENTOS_ARQUIVO)
        df_atend.columns = [col.strip() for col in df_atend.columns]
        df_atend['OS'] = df_atend['OS'].astype(str)
    else:
        df_atend = pd.DataFrame(columns=['OS', 'Status Serviço', 'Cliente', 'Serviço', 'Data 1', 'Prestador'])

    # Carrega links
    if os.path.exists(AVALIACOES_ARQUIVO):
        df_links = pd.read_csv(AVALIACOES_ARQUIVO, dtype={"OS": str, "link_id": str})
        df_links['OS'] = df_links['OS'].astype(str)
        df_links['link_id'] = df_links['link_id'].astype(str)
    else:
        df_links = pd.DataFrame(columns=['OS', 'link_id'])

    # Carrega respostas
    if os.path.exists(RESPOSTAS_ARQUIVO):
        df_resp = pd.read_csv(RESPOSTAS_ARQUIVO, dtype={"link_id": str})
        df_resp['link_id'] = df_resp['link_id'].astype(str)
    else:
        df_resp = pd.DataFrame(columns=['link_id', 'nota', 'observacao'])

    return df_atend, df_links, df_resp

def salvar_links(df_links):
    df_links.to_csv(AVALIACOES_ARQUIVO, index=False)

def salvar_resposta(df_resp):
    df_resp.to_csv(RESPOSTAS_ARQUIVO, index=False)

def gerar_link_para_os(os_num):
    df_atend, df_links, df_resp = carregar_bases()
    os_num = str(os_num)
    # Se já existe e já foi respondido, não gera
    if os_num in df_links['OS'].values:
        link_id = df_links[df_links['OS'] == os_num]['link_id'].values[0]
        if link_id in df_resp['link_id'].values:
            return link_id, False  # Já respondido, não gera novo
    else:
        link_id = str(uuid.uuid4())
        df_links = pd.concat([df_links, pd.DataFrame([{'OS': os_num, 'link_id': link_id}])], ignore_index=True)
        salvar_links(df_links)
        return link_id, True
    return link_id, True

def buscar_dados(link_id):
    if not os.path.exists(AVALIACOES_ARQUIVO):
        return None
    link_id = str(link_id)
    df_links = pd.read_csv(AVALIACOES_ARQUIVO, dtype={"link_id": str, "OS": str})
    df_links['link_id'] = df_links['link_id'].astype(str)
    registro = df_links[df_links['link_id'] == link_id]
    if registro.empty:
        return None
    os_num = registro.iloc[0]['OS']
    df_atend = pd.read_excel(ATENDIMENTOS_ARQUIVO)
    df_atend.columns = [col.strip() for col in df_atend.columns]
    df_atend['OS'] = df_atend['OS'].astype(str)
    dados = df_atend[df_atend['OS'] == os_num]
    if dados.empty:
        return None
    row = dados.iloc[0]
    return {
        "OS": row['OS'],
        "Cliente": row['Cliente'],
        "Serviço": row['Serviço'],
        "Data 1": row['Data 1'],
        "Prestador": row['Prestador']
    }

def registrar_avaliacao(link_id, nota, observacao):
    df_resp = pd.read_csv(RESPOSTAS_ARQUIVO, dtype={"link_id": str}) if os.path.exists(RESPOSTAS_ARQUIVO) else pd.DataFrame(columns=['link_id', 'nota', 'observacao'])
    if link_id in df_resp['link_id'].values:
        return "Avaliação já recebida para esse atendimento."
    nova = pd.DataFrame([{'link_id': link_id, 'nota': nota, 'observacao': observacao}])
    df_resp = pd.concat([df_resp, nova], ignore_index=True)
    salvar_resposta(df_resp)
    return "Obrigado pela sua avaliação!"

def resetar_links_nao_respondidos():
    _, df_links, df_resp = carregar_bases()
    # Remove apenas links que NÃO estão em df_resp
    respondidos = set(df_resp['link_id'])
    df_links_restante = df_links[~df_links['link_id'].isin(respondidos)]
    if not df_links_restante.empty:
        df_links = df_links[df_links['link_id'].isin(respondidos)]  # Fica só os respondidos
        salvar_links(df_links)
    else:
        if os.path.exists(AVALIACOES_ARQUIVO):
            os.remove(AVALIACOES_ARQUIVO)
    st.success("Links NÃO respondidos foram apagados. Respondidos continuam salvos.")

# ===================== UI PRINCIPAL =========================

st.title("Portal de Avaliação Vavivê")

# DASHBOARD DE LINKS
st.header("📊 Dashboard de Links")
df_atend, df_links, df_resp = carregar_bases()

links_criados = len(df_links)
links_respondidos = len(df_resp)
links_nao_resp = max(links_criados - links_respondidos, 0)

st.markdown(f"""
- **Links criados:** {links_criados}
- **Links respondidos:** {links_respondidos}
- **Links aguardando resposta:** {links_nao_resp}
""")

# Botão para resetar somente links NÃO respondidos
if st.button("🔄 Resetar links NÃO respondidos"):
    resetar_links_nao_respondidos()
    st.rerun()


# VISUALIZAÇÃO DE LINKS
st.subheader("Visualização dos Links de Avaliação")
if not df_links.empty:
    # Junta com respostas
    df_dashboard = df_links.copy()
    df_dashboard['Status'] = df_dashboard['link_id'].apply(lambda x: "Respondido" if x in set(df_resp['link_id']) else "Aguardando")
    st.dataframe(df_dashboard[['OS', 'link_id', 'Status']], hide_index=True)
else:
    st.info("Nenhum link gerado ainda.")

# UPLOAD DA PLANILHA
uploaded = st.file_uploader("Faça upload da planilha de atendimentos (.xlsx)", type="xlsx")
if uploaded:
    try:
        df = pd.read_excel(uploaded, sheet_name="Clientes")
        df.columns = [col.strip() for col in df.columns]
        obrigatorias = ['OS', 'Status Serviço', 'Cliente', 'Serviço', 'Data 1', 'Prestador']
        faltando = [col for col in obrigatorias if col not in df.columns]
        if faltando:
            st.error(f"⚠️ Atenção! As seguintes colunas obrigatórias não foram encontradas na sua planilha: {faltando}")
        else:
            df.to_excel(ATENDIMENTOS_ARQUIVO, index=False)
            st.success("Arquivo de atendimentos atualizado.")
            st.rerun()

    except Exception as e:
        st.error(f"Erro ao processar planilha: {e}")

# GERAR LINKS
st.subheader("Gerar links de avaliação (para atendimentos concluídos)")
df_atend, df_links, df_resp = carregar_bases()
if not df_atend.empty and "Status Serviço" in df_atend.columns:
    concluidos = df_atend[df_atend['Status Serviço'].astype(str).str.strip().str.lower() == "concluido"]
    # Exclui atendimentos já respondidos
    atendimentos_possiveis = concluidos[~concluidos['OS'].astype(str).isin(df_links[df_links['link_id'].isin(df_resp['link_id'])]['OS'])]
    if atendimentos_possiveis.empty:
        st.info("Nenhum atendimento 'Concluído' novo para gerar link.")
    else:
        selecao = st.multiselect(
            "Selecione os atendimentos para gerar link:",
            options=atendimentos_possiveis['OS'].astype(str),
            format_func=lambda os_num: f"{os_num} | {atendimentos_possiveis[atendimentos_possiveis['OS'].astype(str)==os_num]['Cliente'].values[0]} | {atendimentos_possiveis[atendimentos_possiveis['OS'].astype(str)==os_num]['Serviço'].values[0]}"
        )
        if st.button("Gerar links"):
            app_url = "https://app-avaliacoes-vavivebh.streamlit.app"
            for os_num in selecao:
                link_id, _ = gerar_link_para_os(os_num)
                st.write(f"OS: {os_num} | Link: {app_url}?link_id={link_id}")

# FORMULÁRIO DE AVALIAÇÃO
query_params = st.query_params
link_id = query_params.get("link_id", [None])[0] if "link_id" in query_params else None

if link_id:
    dados = buscar_dados(link_id)
    if not dados:
        st.error("Link inválido ou não encontrado.")
    else:
        st.header("Avalie seu atendimento")
        st.info(f"""
        **OS:** {dados['OS']}
        **Cliente:** {dados['Cliente']}
        **Serviço:** {dados['Serviço']}
        **Data:** {dados['Data 1']}
        **Prestador:** {dados['Prestador']}
        """)
        nota = st.radio("Avaliação (1=ruim, 5=ótimo)", [1,2,3,4,5], horizontal=True)
        obs = st.text_area("Observações (opcional)")
        if st.button("Enviar avaliação"):
            msg = registrar_avaliacao(link_id, nota, obs)
            st.success(msg)
else:
    st.markdown("""
    > **Para o cliente:** Envie para ele o link gerado!  
    O cliente vai clicar no link e já cair direto no formulário.
    """)


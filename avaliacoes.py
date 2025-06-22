import pandas as pd
import streamlit as st
import uuid
import os

ATENDIMENTOS_ARQUIVO = "atendimentos.xlsx"
AVALIACOES_ARQUIVO = "avaliacoes_links.csv"
RESPOSTAS_ARQUIVO = "avaliacoes_respostas.csv"

st.set_page_config(page_title="Avaliação Vavivê", layout="centered")

def carregar_bases():
    if os.path.exists(ATENDIMENTOS_ARQUIVO):
        df_atend = pd.read_excel(ATENDIMENTOS_ARQUIVO)
        df_atend.columns = [col.strip() for col in df_atend.columns]
    else:
        df_atend = pd.DataFrame()
    if os.path.exists(AVALIACOES_ARQUIVO):
        df_links = pd.read_csv(AVALIACOES_ARQUIVO)
    else:
        df_links = pd.DataFrame(columns=['OS', 'link_id'])
    if os.path.exists(RESPOSTAS_ARQUIVO):
        df_resp = pd.read_csv(RESPOSTAS_ARQUIVO)
    else:
        df_resp = pd.DataFrame(columns=['link_id', 'nota', 'observacao'])
    return df_atend, df_links, df_resp

def salvar_links(df_links):
    df_links.to_csv(AVALIACOES_ARQUIVO, index=False)

def salvar_resposta(df_resp):
    df_resp.to_csv(RESPOSTAS_ARQUIVO, index=False)

def gerar_link_para_os(os_num):
    df_atend, df_links, _ = carregar_bases()
    if os_num in df_links['OS'].astype(str).values:
        link_id = df_links[df_links['OS'].astype(str) == str(os_num)]['link_id'].values[0]
    else:
        link_id = str(uuid.uuid4())
        df_links = pd.concat([df_links, pd.DataFrame([{'OS': os_num, 'link_id': link_id}])], ignore_index=True)
        salvar_links(df_links)
    return link_id

def buscar_dados(link_id):
    # DEBUG APENAS EM LOG
    print("DEBUG: link_id recebido:", link_id)
    if not os.path.exists(AVALIACOES_ARQUIVO):
        print("Arquivo de links não encontrado!")
        return None
    df_links = pd.read_csv(AVALIACOES_ARQUIVO)
    print("DEBUG: df_links head", df_links.head())
    df_atend = pd.read_excel(ATENDIMENTOS_ARQUIVO)
    df_atend.columns = [col.strip() for col in df_atend.columns]
    print("DEBUG: df_atend head", df_atend.head())
    registro = df_links[df_links['link_id'] == link_id]
    print("DEBUG: registro", registro)
    if registro.empty:
        return None
    os_num = registro.iloc[0]['OS']
    dados = df_atend[df_atend['OS'].astype(str) == str(os_num)]
    print("DEBUG: dados", dados)
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
    df_resp = pd.read_csv(RESPOSTAS_ARQUIVO) if os.path.exists(RESPOSTAS_ARQUIVO) else pd.DataFrame(columns=['link_id', 'nota', 'observacao'])
    if link_id in df_resp['link_id'].values:
        return "Avaliação já recebida para esse atendimento."
    nova = pd.DataFrame([{'link_id': link_id, 'nota': nota, 'observacao': observacao}])
    df_resp = pd.concat([df_resp, nova], ignore_index=True)
    salvar_resposta(df_resp)
    return "Obrigado pela sua avaliação!"

# ------------------ UI PRINCIPAL ------------------

st.title("Portal de Avaliação Vavivê")

# ========== DASHBOARD ==========
df_atend, df_links, df_resp = carregar_bases()
total_links = len(df_links)
respondidos = 0
aguardando = 0
if not df_links.empty:
    if not df_resp.empty:
        respondidos = df_links[df_links["link_id"].isin(df_resp["link_id"])].shape[0]
    aguardando = total_links - respondidos

st.markdown(f"""
### 📊 **Dashboard de Links**
- **Links criados:** {total_links}
- **Links respondidos:** {respondidos}
- **Links aguardando resposta:** {aguardando}
""")

# ========== BOTÃO ÚNICO DE RESET ==========
if st.button("🔄 Resetar links NÃO respondidos"):
    if os.path.exists(AVALIACOES_ARQUIVO):
        df_links = pd.read_csv(AVALIACOES_ARQUIVO)
        if os.path.exists(RESPOSTAS_ARQUIVO):
            df_resp = pd.read_csv(RESPOSTAS_ARQUIVO)
            links_respondidos = df_resp["link_id"].unique()
            df_links = df_links[df_links["link_id"].isin(links_respondidos)]
            df_links.to_csv(AVALIACOES_ARQUIVO, index=False)
        else:
            os.remove(AVALIACOES_ARQUIVO)
    st.success("Links não respondidos foram resetados. Respondidos foram mantidos.")
    st.rerun()

# ========== VISUALIZAÇÃO DOS LINKS ==========
if not df_links.empty:
    df_links_show = df_links.copy()
    df_links_show['Status'] = df_links_show['link_id'].apply(
        lambda x: 'Respondido' if not df_resp.empty and x in df_resp['link_id'].values else 'Aguardando'
    )
    st.markdown("#### Visualização dos Links de Avaliação")
    st.dataframe(df_links_show[['OS', 'link_id', 'Status']], hide_index=True)

# ========== UPLOAD DA PLANILHA ==========
uploaded = st.file_uploader("Faça upload da planilha de atendimentos (.xlsx)", type="xlsx")

if uploaded:
    try:
        df = pd.read_excel(uploaded, sheet_name="Clientes")
        df.columns = [col.strip() for col in df.columns]
        st.write("Colunas carregadas:", df.columns.tolist())
        obrigatorias = ['OS', 'Status Serviço', 'Cliente', 'Serviço', 'Data 1', 'Prestador']
        faltando = [col for col in obrigatorias if col not in df.columns]
        if faltando:
            st.error(f"⚠️ Atenção! As seguintes colunas obrigatórias não foram encontradas na sua planilha: {faltando}")
        else:
            df.to_excel(ATENDIMENTOS_ARQUIVO, index=False)
            st.success("Arquivo de atendimentos atualizado.")
    except ValueError as e:
        st.error("⚠️ Não foi encontrada uma aba chamada 'Clientes' no arquivo Excel. Confira e tente novamente.")

# ========== GERAÇÃO DE LINKS ==========
st.subheader("Gerar links de avaliação (para atendimentos concluídos)")
df_atend, df_links, _ = carregar_bases()
if not df_atend.empty and "Status Serviço" in df_atend.columns:
    concluidos = df_atend[df_atend['Status Serviço'].astype(str).str.strip().str.lower() == "concluido"]
    # Apenas os que ainda não possuem link
    concluidos = concluidos[~concluidos['OS'].astype(str).isin(df_links['OS'].astype(str))]
    if concluidos.empty:
        st.info("Nenhum atendimento 'Concluido' novo para gerar link.")
    else:
        selecao = st.multiselect(
            "Selecione os atendimentos para gerar link:",
            options=concluidos['OS'].astype(str),
            format_func=lambda os_num: f"{os_num} | {concluidos[concluidos['OS'].astype(str)==os_num]['Cliente'].values[0]} | {concluidos[concluidos['OS'].astype(str)==os_num]['Serviço'].values[0]}"
        )
        if st.button("Gerar links"):
            app_url = "https://app-avaliacoes-vavivebh.streamlit.app"
            for os_num in selecao:
                link_id = gerar_link_para_os(os_num)
                st.write(f"OS: {os_num} | Link: {app_url}?link_id={link_id}")

# ========== FORMULÁRIO DE AVALIAÇÃO (ACESSO VIA LINK) ==========
query_params = st.query_params
link_id = query_params.get("link_id", [None])[0]

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

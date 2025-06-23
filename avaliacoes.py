import pandas as pd
import streamlit as st
import uuid
import os
from io import BytesIO

ATENDIMENTOS_ARQUIVO = "atendimentos.xlsx"
AVALIACOES_ARQUIVO = "avaliacoes_links.csv"
RESPOSTAS_ARQUIVO = "avaliacoes_respostas.csv"
APP_URL = "https://app-avaliacoes-vavivebh.streamlit.app"

st.set_page_config(page_title="Avaliação Vavivê", layout="wide")

# 1️⃣ FORMULÁRIO DO CLIENTE (acesso por link)
link_id = st.query_params.get("link_id", None)
if link_id:
    def buscar_dados(link_id):
        if not os.path.exists(AVALIACOES_ARQUIVO):
            st.error("Arquivo de links não encontrado!")
            return None
        df_links = pd.read_csv(AVALIACOES_ARQUIVO)
        df_atend = pd.read_excel(ATENDIMENTOS_ARQUIVO)
        df_atend.columns = [col.strip() for col in df_atend.columns]
        registro = df_links[df_links['link_id'] == link_id]
        if registro.empty:
            return None
        os_num = registro.iloc[0]['OS']
        dados = df_atend[df_atend['OS'].astype(str) == str(os_num)]
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
        df_resp.to_csv(RESPOSTAS_ARQUIVO, index=False)
        return "Obrigado pela sua avaliação!"

    dados = buscar_dados(link_id)
    if not dados:
        st.error("Link inválido ou não encontrado.")
    else:
        st.header("Olá, queremos ouvir você! Avalie seu atendimento!")
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
    st.stop()

# 2️⃣ FUNÇÕES AUXILIARES
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

# 3️⃣ INTERFACE ADMIN (2 colunas)
st.title("BELO HORIZONTE || Portal de Avaliação Vavivê")

col_esq, col_dir = st.columns([1, 2])

with col_esq:
    if st.button("🔄 Resetar links NÃO respondidos"):
        df_atend, df_links, df_resp = carregar_bases()
        if not df_links.empty and not df_resp.empty:
            responded_ids = set(df_resp['link_id'])
            df_links = df_links[df_links['link_id'].isin(responded_ids)]
            salvar_links(df_links)
            st.success("Links pendentes foram resetados. Links já respondidos foram mantidos.")
        elif not df_links.empty:
            os.remove(AVALIACOES_ARQUIVO)
            st.success("Todos os links foram resetados.")
        st.rerun()

    uploaded = st.file_uploader("Faça upload da planilha de atendimentos (.xlsx)", type="xlsx")
    if uploaded:
        try:
            df = pd.read_excel(uploaded, sheet_name="Clientes")
            df.columns = [col.strip() for col in df.columns]
            obrigatorias = ['OS', 'Status Serviço', 'Cliente', 'Serviço', 'Data 1', 'Prestador']
            faltando = [col for col in obrigatorias if col not in df.columns]
            if faltando:
                st.error(f"⚠️ Colunas obrigatórias ausentes: {faltando}")
            else:
                df.to_excel(ATENDIMENTOS_ARQUIVO, index=False)
                st.success("Arquivo de atendimentos atualizado.")
        except ValueError:
            st.error("⚠️ Aba 'Clientes' não encontrada no arquivo.")

    st.subheader("Gerar links de avaliação (para atendimentos não cancelados)")
    df_atend, df_links, df_resp = carregar_bases()
    if not df_atend.empty and "Status Serviço" in df_atend.columns:
        concluidos = df_atend[df_atend['Status Serviço'].astype(str).str.strip().str.lower() != "cancelado"]
        concluidos = concluidos[~concluidos['OS'].astype(str).isin(df_links['OS'].astype(str))]
        if concluidos.empty:
            st.info("Nenhum atendimento elegível novo para gerar link.")
        else:
            selecao = st.multiselect(
                "Selecione os atendimentos para gerar link:",
                options=concluidos['OS'].astype(str),
                format_func=lambda os_num: f"{os_num} | {concluidos[concluidos['OS'].astype(str)==os_num]['Cliente'].values[0]} | {concluidos[concluidos['OS'].astype(str)==os_num]['Serviço'].values[0]}"
            )
            if st.button("Gerar links"):
                for os_num in selecao:
                    link_id = gerar_link_para_os(os_num)
                    st.write(f"OS: {os_num} | Link: {APP_URL}?link_id={link_id}")

with col_dir:
    st.subheader("Dashboard dos Links de Avaliação")
    df_atend, df_links, df_resp = carregar_bases()
    if not df_links.empty:
        df_dashboard = df_links.copy()
        df_dashboard['Respondido'] = df_dashboard['link_id'].isin(df_resp['link_id'])
        df_dashboard = df_dashboard.merge(df_atend, on='OS', how='left')
        df_dashboard = df_dashboard.merge(df_resp, on='link_id', how='left')
        df_dashboard["Link Completo"] = df_dashboard["link_id"].apply(lambda x: f"{APP_URL}?link_id={x}")

        total_links = len(df_dashboard)
        total_respondidos = df_dashboard['Respondido'].sum()
        perc_respondidos = (total_respondidos / total_links * 100) if total_links > 0 else 0
        notas_validas = pd.to_numeric(df_dashboard[df_dashboard['Respondido']]['nota'], errors='coerce').dropna()
        media_nota = notas_validas.mean() if not notas_validas.empty else None

        col1, col2, col3 = st.columns(3)
        col1.metric("Links criados", total_links)
        col2.metric("Respondidos", total_respondidos)
        col3.metric("Pendentes", total_links - total_respondidos)
        st.subheader("Métricas de Resposta")
        metrica1, metrica2 = st.columns(2)
        metrica1.metric("% de respondidos", f"{perc_respondidos:.1f}%")
        if media_nota is not None:
            metrica2.metric("Média das notas (respondidos)", f"{media_nota:.2f}")
        else:
            metrica2.metric("Média das notas (respondidos)", "N/A")

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_dashboard.to_excel(writer, index=False, sheet_name='Links')
        xlsx_data = output.getvalue()
        st.download_button(
            label="📥 Baixar tabela Excel completa",
            data=xlsx_data,
            file_name="links_avaliacao_completo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Exibe a tabela final incluindo nota, observacao e link completo
        st.dataframe(
            df_dashboard.rename(columns={
                "link_id": "LinkID",
                "OS": "OS",
                "Cliente": "Cliente",
                "Serviço": "Serviço",
                "Data 1": "Data",
                "Prestador": "Profissional",
                "Link Completo": "Link Completo",
                "nota": "Nota",
                "observacao": "Observação"
            })[[
                "OS", "Cliente", "Serviço", "Data", "Profissional",
                "LinkID", "Link Completo", "Respondido", "Nota", "Observação"
            ]]
        )
    else:
        st.info("Nenhum link gerado ainda.")

st.markdown("""
> **Para o cliente:** Envie para ele o link gerado!  
> O cliente vai clicar no link e já cair direto no formulário.
""")

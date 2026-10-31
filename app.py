"""TaskFlow - organizador de tarefas pessoal, acadêmico e profissional.

Para rodar: streamlit run app.py
"""

import os
from datetime import date

import streamlit as st

import database as db

st.set_page_config(page_title="TaskFlow", page_icon=":material/task_alt:", layout="centered")

CORES_PRIORIDADE = {"Alta": "red", "Média": "orange", "Baixa": "green"}
CORES_STATUS = {"Pendente": "gray", "Em andamento": "blue", "Concluída": "green"}
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# ---------------------------------------------------------------------------
# Configuração e conexão
# ---------------------------------------------------------------------------
def ler_configuracao(nome: str) -> str | None:
    """Lê uma variável do .env (local) ou dos Secrets (Streamlit Cloud)."""
    valor = os.getenv(nome)
    if valor:
        return valor
    try:
        return st.secrets[nome]
    except Exception:
        return None


def obter_cliente():
    """Cada pessoa conectada recebe o seu próprio cliente do Supabase."""
    if "cliente" not in st.session_state:
        try:
            st.session_state.cliente = db.criar_cliente(
                ler_configuracao("SUPABASE_URL"), ler_configuracao("SUPABASE_KEY")
            )
        except ValueError as erro:
            st.error(str(erro))
            st.stop()
    return st.session_state.cliente


def mostrar_aviso() -> None:
    """Mostra uma mensagem guardada antes de recarregar a tela."""
    aviso = st.session_state.pop("aviso", None)
    if aviso:
        st.success(aviso)


def avisar_e_recarregar(mensagem: str) -> None:
    st.session_state.aviso = mensagem
    st.rerun()


def traduzir_erro_login(erro: Exception) -> str:
    texto = str(erro).lower()
    if "invalid login credentials" in texto:
        return "E-mail ou senha incorretos."
    if "email not confirmed" in texto:
        return "Confirme seu e-mail antes de entrar (veja sua caixa de entrada)."
    if "already registered" in texto or "already exists" in texto:
        return "Este e-mail já está cadastrado."
    if "password" in texto:
        return "Senha inválida. Use pelo menos 6 caracteres."
    if "rate limit" in texto:
        return "Muitas tentativas. Aguarde alguns minutos e tente novamente."
    return "Não foi possível concluir. Verifique os dados e tente novamente."


def formatar_data(valor) -> str:
    data = db.converter_data(valor)
    if not data:
        return "Sem data"
    return f"{DIAS_SEMANA[data.weekday()]}, {data:%d/%m/%Y}"


def descrever_prazo(valor) -> str:
    data = db.converter_data(valor)
    dias = (data - date.today()).days
    if dias < 0:
        return f"Atrasada há {-dias} dia(s)"
    if dias == 0:
        return "Vence hoje"
    if dias == 1:
        return "Vence amanhã"
    return f"Vence em {dias} dias"


# ---------------------------------------------------------------------------
# Tela de login e cadastro
# ---------------------------------------------------------------------------
def tela_login(cliente) -> None:
    st.title("TaskFlow")
    st.caption("Organize suas tarefas pessoais, de estudos e de trabalho em um só lugar.")

    aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar conta"])

    with aba_entrar:
        with st.form("form_login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if enviar:
            if not email or not senha:
                st.warning("Preencha e-mail e senha.")
            else:
                try:
                    resposta = db.entrar(cliente, email, senha)
                    st.session_state.usuario = resposta.user.email
                    st.rerun()
                except Exception as erro:
                    st.error(traduzir_erro_login(erro))

    with aba_cadastrar:
        with st.form("form_cadastro"):
            email = st.text_input("E-mail", key="cadastro_email")
            senha = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="cadastro_senha")
            confirmar = st.text_input("Confirme a senha", type="password", key="cadastro_confirmar")
            enviar = st.form_submit_button("Criar conta", type="primary", width="stretch")
        if enviar:
            if not email or not senha:
                st.warning("Preencha e-mail e senha.")
            elif len(senha) < 6:
                st.warning("A senha precisa ter pelo menos 6 caracteres.")
            elif senha != confirmar:
                st.warning("As senhas não são iguais.")
            else:
                try:
                    resposta = db.cadastrar_usuario(cliente, email, senha)
                    if resposta.session:
                        st.session_state.usuario = resposta.user.email
                        avisar_e_recarregar("Conta criada! Bem-vinda(o) ao TaskFlow.")
                    else:
                        st.success("Conta criada! Confirme seu e-mail e depois faça login na aba Entrar.")
                except Exception as erro:
                    st.error(traduzir_erro_login(erro))


# ---------------------------------------------------------------------------
# Formulário de tarefa (usado para criar e para editar)
# ---------------------------------------------------------------------------
def formulario_tarefa(cliente, tarefa: dict | None = None) -> None:
    editando = tarefa is not None
    tarefa = tarefa or {}
    chave = f"form_{tarefa['id']}" if editando else "form_nova"

    with st.form(chave, clear_on_submit=not editando):
        titulo = st.text_input("Título *", value=tarefa.get("titulo", ""), max_chars=200)
        descricao = st.text_area("Descrição", value=tarefa.get("descricao") or "", height=90)
        col1, col2 = st.columns(2)
        categoria = col1.selectbox(
            "Categoria", db.CATEGORIAS,
            index=db.CATEGORIAS.index(tarefa.get("categoria", "Pessoal")),
        )
        prioridade = col2.selectbox(
            "Prioridade", db.PRIORIDADES,
            index=db.PRIORIDADES.index(tarefa.get("prioridade", "Média")),
        )
        col3, col4 = st.columns(2)
        status = col3.selectbox(
            "Status", db.STATUS, index=db.STATUS.index(tarefa.get("status", "Pendente"))
        )
        data_entrega = col4.date_input(
            "Data de entrega",
            value=db.converter_data(tarefa.get("data_entrega")),
            format="DD/MM/YYYY",
        )

        botoes = st.container(horizontal=True)
        salvar = botoes.form_submit_button("Salvar" if editando else "Adicionar tarefa", type="primary")
        cancelar = botoes.form_submit_button("Cancelar") if editando else False

    if cancelar:
        st.session_state.pop("editando", None)
        st.rerun()

    if salvar:
        try:
            if editando:
                db.atualizar_tarefa(
                    cliente, tarefa["id"], titulo, descricao, categoria, prioridade, data_entrega, status
                )
                st.session_state.pop("editando", None)
                avisar_e_recarregar("Tarefa atualizada.")
            else:
                db.criar_tarefa(cliente, titulo, descricao, categoria, prioridade, data_entrega, status)
                avisar_e_recarregar("Tarefa adicionada!")
        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error("Não foi possível salvar a tarefa. Tente novamente.")


# ---------------------------------------------------------------------------
# Cartão de uma tarefa na lista
# ---------------------------------------------------------------------------
def cartao_tarefa(cliente, tarefa: dict) -> None:
    tid = tarefa["id"]
    with st.container(border=True):
        if st.session_state.get("editando") == tid:
            st.markdown("**Editar tarefa**")
            formulario_tarefa(cliente, tarefa)
            return

        concluida = tarefa["status"] == db.STATUS_CONCLUIDA
        titulo = f"~~{tarefa['titulo']}~~" if concluida else tarefa["titulo"]
        st.markdown(f"**{titulo}**")

        etiquetas = st.container(horizontal=True, gap="small")
        etiquetas.badge(tarefa["categoria"], color="violet")
        etiquetas.badge(tarefa["prioridade"], color=CORES_PRIORIDADE[tarefa["prioridade"]])
        etiquetas.badge(tarefa["status"], color=CORES_STATUS[tarefa["status"]])
        etiquetas.badge(formatar_data(tarefa.get("data_entrega")), icon=":material/event:", color="gray")

        if tarefa.get("descricao"):
            st.caption(tarefa["descricao"])

        if st.session_state.get("confirmar_exclusao") == tid:
            st.warning("Tem certeza que deseja excluir esta tarefa?")
            botoes = st.container(horizontal=True)
            if botoes.button("Sim, excluir", key=f"sim_{tid}", type="primary"):
                try:
                    db.excluir_tarefa(cliente, tid)
                    st.session_state.pop("confirmar_exclusao", None)
                    avisar_e_recarregar("Tarefa excluída.")
                except Exception:
                    st.error("Não foi possível excluir a tarefa.")
            if botoes.button("Cancelar", key=f"nao_{tid}"):
                st.session_state.pop("confirmar_exclusao", None)
                st.rerun()
            return

        botoes = st.container(horizontal=True, gap="small")
        if not concluida and botoes.button("Concluir", key=f"ok_{tid}", icon=":material/check:"):
            try:
                db.concluir_tarefa(cliente, tid)
                avisar_e_recarregar("Tarefa concluída. Parabéns!")
            except Exception:
                st.error("Não foi possível concluir a tarefa.")
        if botoes.button("Editar", key=f"ed_{tid}", icon=":material/edit:"):
            st.session_state.editando = tid
            st.session_state.pop("confirmar_exclusao", None)
            st.rerun()
        if botoes.button("Excluir", key=f"ex_{tid}", icon=":material/delete:"):
            st.session_state.confirmar_exclusao = tid
            st.session_state.pop("editando", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def pagina_painel(tarefas: list[dict]) -> None:
    ind = db.calcular_indicadores(tarefas)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", ind["total"], border=True)
    col2.metric("Pendentes", ind["pendentes"], border=True)
    col3.metric("Concluídas", ind["concluidas"], border=True)
    col4.metric("Progresso", f"{ind['progresso']}%", border=True)
    st.progress(ind["progresso"] / 100)
    if ind["em_andamento"]:
        st.caption(f"{ind['em_andamento']} tarefa(s) em andamento.")

    st.subheader("Minha Semana")
    semana = db.tarefas_da_semana(tarefas)
    if not semana:
        st.info("Nenhum prazo para os próximos 7 dias.")
        return
    for tarefa in semana:
        with st.container(border=True):
            st.markdown(f"**{tarefa['titulo']}**")
            linha = st.container(horizontal=True, gap="small")
            atrasada = db.converter_data(tarefa["data_entrega"]) < date.today()
            linha.badge(descrever_prazo(tarefa["data_entrega"]), color="red" if atrasada else "blue")
            linha.badge(formatar_data(tarefa["data_entrega"]), icon=":material/event:", color="gray")
            linha.badge(tarefa["categoria"], color="violet")
            linha.badge(tarefa["prioridade"], color=CORES_PRIORIDADE[tarefa["prioridade"]])


def pagina_tarefas(cliente, tarefas: list[dict]) -> None:
    with st.expander("Filtros", icon=":material/filter_list:", expanded=False):
        categorias = st.pills("Categoria", db.CATEGORIAS, selection_mode="multi", key="f_cat")
        prioridades = st.pills("Prioridade", db.PRIORIDADES, selection_mode="multi", key="f_pri")
        status = st.pills("Status", db.STATUS, selection_mode="multi", key="f_sta")

    filtradas = db.filtrar_tarefas(tarefas, categorias, prioridades, status)
    st.caption(f"{len(filtradas)} de {len(tarefas)} tarefa(s)")

    if not tarefas:
        st.info("Você ainda não tem tarefas. Use a aba **Nova tarefa** para começar.")
    elif not filtradas:
        st.info("Nenhuma tarefa com esses filtros.")
    for tarefa in filtradas:
        cartao_tarefa(cliente, tarefa)


def pagina_nova_tarefa(cliente) -> None:
    formulario_tarefa(cliente)


def tela_principal(cliente) -> None:
    topo = st.container(horizontal=True, vertical_alignment="center")
    topo.title("TaskFlow")
    if topo.button("Sair", icon=":material/logout:"):
        try:
            db.sair(cliente)
        finally:
            st.session_state.clear()
            st.rerun()
    st.caption(f"Conectada(o) como {st.session_state.usuario}")

    pagina = st.segmented_control(
        "Navegação", ["Painel", "Tarefas", "Nova tarefa"],
        default="Painel", key="pagina", label_visibility="collapsed",
    ) or "Painel"

    mostrar_aviso()

    if pagina == "Nova tarefa":
        pagina_nova_tarefa(cliente)
        return

    try:
        tarefas = db.listar_tarefas(cliente)
    except Exception:
        st.error("Não foi possível carregar suas tarefas. Faça login novamente.")
        return

    if pagina == "Painel":
        pagina_painel(tarefas)
    else:
        pagina_tarefas(cliente, tarefas)


def main() -> None:
    cliente = obter_cliente()
    if "usuario" in st.session_state:
        tela_principal(cliente)
    else:
        tela_login(cliente)


main()

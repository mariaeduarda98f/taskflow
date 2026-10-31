"""Camada de dados do TaskFlow.

Aqui ficam todas as conversas com o Supabase (login e tarefas) e algumas
funções simples de cálculo usadas no painel. O app.py só chama estas funções.
"""

import os
from datetime import date, timedelta

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

TABELA = "tarefas"
CATEGORIAS = ["Pessoal", "Estudos", "Trabalho"]
PRIORIDADES = ["Alta", "Média", "Baixa"]
STATUS = ["Pendente", "Em andamento", "Concluída"]
STATUS_CONCLUIDA = "Concluída"


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
def criar_cliente(url: str | None = None, chave: str | None = None) -> Client:
    """Cria um cliente do Supabase usando as variáveis de ambiente."""
    url = url or os.getenv("SUPABASE_URL")
    chave = chave or os.getenv("SUPABASE_KEY")
    if not url or not chave:
        raise ValueError(
            "Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env "
            "(ou nos Secrets do Streamlit Cloud)."
        )
    return create_client(url, chave)


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
def cadastrar_usuario(cliente: Client, email: str, senha: str):
    """Cria uma conta. Retorna a resposta do Supabase (com user e session)."""
    return cliente.auth.sign_up({"email": email.strip(), "password": senha})


def entrar(cliente: Client, email: str, senha: str):
    """Faz login com e-mail e senha."""
    return cliente.auth.sign_in_with_password({"email": email.strip(), "password": senha})


def sair(cliente: Client) -> None:
    """Encerra a sessão do usuário."""
    cliente.auth.sign_out()


# ---------------------------------------------------------------------------
# Tarefas (CRUD)
# O Row Level Security do banco garante que cada usuário só acessa as
# próprias tarefas, e o user_id é preenchido automaticamente pelo banco.
# ---------------------------------------------------------------------------
def validar_tarefa(titulo: str, categoria: str, prioridade: str, status: str) -> None:
    """Confere os dados antes de enviar ao banco."""
    if not titulo or not titulo.strip():
        raise ValueError("O título é obrigatório.")
    if len(titulo.strip()) > 200:
        raise ValueError("O título pode ter no máximo 200 caracteres.")
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoria inválida: {categoria}")
    if prioridade not in PRIORIDADES:
        raise ValueError(f"Prioridade inválida: {prioridade}")
    if status not in STATUS:
        raise ValueError(f"Status inválido: {status}")


def _montar_dados(titulo, descricao, categoria, prioridade, data_entrega, status) -> dict:
    validar_tarefa(titulo, categoria, prioridade, status)
    return {
        "titulo": titulo.strip(),
        "descricao": (descricao or "").strip(),
        "categoria": categoria,
        "prioridade": prioridade,
        "status": status,
        "data_entrega": data_entrega.isoformat() if data_entrega else None,
    }


def listar_tarefas(cliente: Client) -> list[dict]:
    """Busca todas as tarefas do usuário logado."""
    resposta = (
        cliente.table(TABELA)
        .select("*")
        .order("data_entrega", nullsfirst=False)
        .order("criado_em")
        .execute()
    )
    return resposta.data or []


def criar_tarefa(
    cliente: Client,
    titulo: str,
    descricao: str,
    categoria: str,
    prioridade: str,
    data_entrega: date | None,
    status: str = "Pendente",
) -> dict:
    """Cadastra uma nova tarefa e devolve a tarefa salva."""
    dados = _montar_dados(titulo, descricao, categoria, prioridade, data_entrega, status)
    resposta = cliente.table(TABELA).insert(dados).execute()
    return resposta.data[0]


def atualizar_tarefa(
    cliente: Client,
    tarefa_id: str,
    titulo: str,
    descricao: str,
    categoria: str,
    prioridade: str,
    data_entrega: date | None,
    status: str,
) -> dict:
    """Edita uma tarefa existente."""
    dados = _montar_dados(titulo, descricao, categoria, prioridade, data_entrega, status)
    resposta = cliente.table(TABELA).update(dados).eq("id", tarefa_id).execute()
    if not resposta.data:
        raise ValueError("Tarefa não encontrada.")
    return resposta.data[0]


def alterar_status(cliente: Client, tarefa_id: str, status: str) -> dict:
    """Muda só o status da tarefa (ex.: marcar como concluída)."""
    if status not in STATUS:
        raise ValueError(f"Status inválido: {status}")
    resposta = cliente.table(TABELA).update({"status": status}).eq("id", tarefa_id).execute()
    if not resposta.data:
        raise ValueError("Tarefa não encontrada.")
    return resposta.data[0]


def concluir_tarefa(cliente: Client, tarefa_id: str) -> dict:
    """Marca a tarefa como concluída."""
    return alterar_status(cliente, tarefa_id, STATUS_CONCLUIDA)


def excluir_tarefa(cliente: Client, tarefa_id: str) -> None:
    """Apaga uma tarefa."""
    resposta = cliente.table(TABELA).delete().eq("id", tarefa_id).execute()
    if not resposta.data:
        raise ValueError("Tarefa não encontrada.")


# ---------------------------------------------------------------------------
# Funções de cálculo (não acessam o banco)
# ---------------------------------------------------------------------------
def converter_data(valor) -> date | None:
    """Converte o texto 'AAAA-MM-DD' vindo do banco em uma data."""
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def filtrar_tarefas(
    tarefas: list[dict],
    categorias: list[str] | None = None,
    prioridades: list[str] | None = None,
    status: list[str] | None = None,
) -> list[dict]:
    """Filtra as tarefas. Um filtro vazio significa 'mostrar todas'."""
    return [
        t
        for t in tarefas
        if (not categorias or t["categoria"] in categorias)
        and (not prioridades or t["prioridade"] in prioridades)
        and (not status or t["status"] in status)
    ]


def calcular_indicadores(tarefas: list[dict]) -> dict:
    """Calcula os números do painel."""
    total = len(tarefas)
    concluidas = sum(1 for t in tarefas if t["status"] == STATUS_CONCLUIDA)
    pendentes = sum(1 for t in tarefas if t["status"] == "Pendente")
    em_andamento = sum(1 for t in tarefas if t["status"] == "Em andamento")
    progresso = round(concluidas / total * 100) if total else 0
    return {
        "total": total,
        "pendentes": pendentes,
        "em_andamento": em_andamento,
        "concluidas": concluidas,
        "progresso": progresso,
    }


def contar_por(tarefas: list[dict], campo: str, valores: list[str]) -> dict[str, int]:
    """Conta quantas tarefas existem para cada valor de um campo (usado nos gráficos)."""
    return {valor: sum(1 for t in tarefas if t[campo] == valor) for valor in valores}


def tarefas_da_semana(tarefas: list[dict], hoje: date | None = None) -> list[dict]:
    """Tarefas não concluídas que vencem nos próximos 7 dias (incluindo atrasadas)."""
    hoje = hoje or date.today()
    limite = hoje + timedelta(days=6)
    resultado = [
        t
        for t in tarefas
        if t["status"] != STATUS_CONCLUIDA
        and converter_data(t.get("data_entrega")) is not None
        and converter_data(t["data_entrega"]) <= limite
    ]
    return sorted(resultado, key=lambda t: converter_data(t["data_entrega"]))

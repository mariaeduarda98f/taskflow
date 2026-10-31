"""Testes no Supabase de verdade (login + cadastro, edição, conclusão e exclusão).

Só rodam se SUPABASE_URL, SUPABASE_KEY, TEST_EMAIL e TEST_SENHA estiverem no .env.
Use um usuário de teste já cadastrado. As tarefas criadas aqui são apagadas no final.
"""

import os
from datetime import date

import pytest

import database as db

VARIAVEIS = ["SUPABASE_URL", "SUPABASE_KEY", "TEST_EMAIL", "TEST_SENHA"]
pytestmark = pytest.mark.skipif(
    not all(os.getenv(v) for v in VARIAVEIS),
    reason="Defina SUPABASE_URL, SUPABASE_KEY, TEST_EMAIL e TEST_SENHA para rodar",
)


@pytest.fixture
def cliente():
    cliente = db.criar_cliente()
    db.entrar(cliente, os.environ["TEST_EMAIL"], os.environ["TEST_SENHA"])
    yield cliente
    db.sair(cliente)


def test_ciclo_completo(cliente):
    tarefa = db.criar_tarefa(
        cliente, "[teste] Tarefa automática", "criada pelo pytest",
        "Estudos", "Alta", date.today(),
    )
    try:
        assert tarefa["user_id"]
        assert any(t["id"] == tarefa["id"] for t in db.listar_tarefas(cliente))

        editada = db.atualizar_tarefa(
            cliente, tarefa["id"], "[teste] Editada", "ok", "Trabalho", "Baixa",
            date.today(), "Em andamento",
        )
        assert editada["titulo"] == "[teste] Editada"
        assert editada["status"] == "Em andamento"

        assert db.concluir_tarefa(cliente, tarefa["id"])["status"] == "Concluída"
    finally:
        db.excluir_tarefa(cliente, tarefa["id"])

    assert all(t["id"] != tarefa["id"] for t in db.listar_tarefas(cliente))


def test_rls_bloqueia_quem_nao_esta_logado(cliente):
    tarefa = db.criar_tarefa(cliente, "[teste] RLS", "", "Pessoal", "Média", None)
    try:
        anonimo = db.criar_cliente()
        assert db.listar_tarefas(anonimo) == []
        with pytest.raises(ValueError):
            db.excluir_tarefa(anonimo, tarefa["id"])
    finally:
        db.excluir_tarefa(cliente, tarefa["id"])

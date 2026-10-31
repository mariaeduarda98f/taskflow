"""Testes das operações de tarefas usando um banco falso (em memória).

Não precisam de internet nem de Supabase. Rode com: pytest
"""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import database as db


class ConsultaFalsa:
    """Imita o jeito de encadear comandos do Supabase: .table().select().eq().execute()"""

    def __init__(self, linhas: list[dict]):
        self.linhas = linhas
        self.acao = "select"
        self.dados = None
        self.filtros = []

    def select(self, *_):
        self.acao = "select"
        return self

    def order(self, *_, **__):
        return self

    def insert(self, dados):
        self.acao, self.dados = "insert", dados
        return self

    def update(self, dados):
        self.acao, self.dados = "update", dados
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def _combina(self, linha):
        return all(linha.get(c) == v for c, v in self.filtros)

    def execute(self):
        if self.acao == "insert":
            nova = {"id": str(uuid.uuid4()), **self.dados}
            self.linhas.append(nova)
            return SimpleNamespace(data=[nova])
        afetadas = [l for l in self.linhas if self._combina(l)]
        if self.acao == "update":
            for linha in afetadas:
                linha.update(self.dados)
        elif self.acao == "delete":
            for linha in afetadas:
                self.linhas.remove(linha)
        return SimpleNamespace(data=[dict(l) for l in afetadas])


class ClienteFalso:
    def __init__(self):
        self.linhas: list[dict] = []

    def table(self, _nome):
        return ConsultaFalsa(self.linhas)


@pytest.fixture
def cliente():
    return ClienteFalso()


def nova_tarefa(cliente, **extra):
    dados = dict(
        titulo="Estudar Python",
        descricao="Capítulo 3",
        categoria="Estudos",
        prioridade="Alta",
        data_entrega=date(2030, 1, 10),
    )
    dados.update(extra)
    return db.criar_tarefa(cliente, **dados)


# --- Cadastro -------------------------------------------------------------
def test_cadastrar_tarefa(cliente):
    tarefa = nova_tarefa(cliente)
    assert tarefa["titulo"] == "Estudar Python"
    assert tarefa["status"] == "Pendente"
    assert tarefa["data_entrega"] == "2030-01-10"
    assert len(db.listar_tarefas(cliente)) == 1


def test_cadastro_remove_espacos_extras(cliente):
    tarefa = nova_tarefa(cliente, titulo="  Ler livro  ", descricao="  ")
    assert tarefa["titulo"] == "Ler livro"
    assert tarefa["descricao"] == ""


def test_cadastro_sem_data(cliente):
    assert nova_tarefa(cliente, data_entrega=None)["data_entrega"] is None


@pytest.mark.parametrize(
    "campo, valor",
    [("titulo", ""), ("titulo", "   "), ("titulo", "x" * 201),
     ("categoria", "Lazer"), ("prioridade", "Urgente"), ("status", "Feita")],
)
def test_cadastro_invalido(cliente, campo, valor):
    with pytest.raises(ValueError):
        nova_tarefa(cliente, **{campo: valor})
    assert db.listar_tarefas(cliente) == []


# --- Edição ---------------------------------------------------------------
def test_editar_tarefa(cliente):
    tarefa = nova_tarefa(cliente)
    editada = db.atualizar_tarefa(
        cliente, tarefa["id"], "Estudar SQL", "Joins", "Trabalho", "Baixa",
        date(2030, 2, 1), "Em andamento",
    )
    assert editada["titulo"] == "Estudar SQL"
    assert editada["categoria"] == "Trabalho"
    assert editada["prioridade"] == "Baixa"
    assert editada["status"] == "Em andamento"
    assert editada["data_entrega"] == "2030-02-01"


def test_editar_tarefa_inexistente(cliente):
    with pytest.raises(ValueError):
        db.atualizar_tarefa(cliente, "nao-existe", "A", "", "Pessoal", "Alta", None, "Pendente")


# --- Conclusão ------------------------------------------------------------
def test_concluir_tarefa(cliente):
    tarefa = nova_tarefa(cliente)
    assert db.concluir_tarefa(cliente, tarefa["id"])["status"] == "Concluída"
    assert db.listar_tarefas(cliente)[0]["status"] == "Concluída"


def test_alterar_status_invalido(cliente):
    tarefa = nova_tarefa(cliente)
    with pytest.raises(ValueError):
        db.alterar_status(cliente, tarefa["id"], "Arquivada")


# --- Exclusão -------------------------------------------------------------
def test_excluir_tarefa(cliente):
    tarefa = nova_tarefa(cliente)
    outra = nova_tarefa(cliente, titulo="Outra")
    db.excluir_tarefa(cliente, tarefa["id"])
    restantes = db.listar_tarefas(cliente)
    assert [t["id"] for t in restantes] == [outra["id"]]


def test_excluir_tarefa_inexistente(cliente):
    with pytest.raises(ValueError):
        db.excluir_tarefa(cliente, "nao-existe")


# --- Filtros, painel e Minha Semana --------------------------------------
def _t(categoria="Pessoal", prioridade="Média", status="Pendente", data_entrega=None):
    return dict(categoria=categoria, prioridade=prioridade, status=status, data_entrega=data_entrega)


def test_filtrar_tarefas():
    tarefas = [_t("Pessoal", "Alta"), _t("Estudos", "Baixa", "Concluída"), _t("Trabalho", "Alta")]
    assert len(db.filtrar_tarefas(tarefas)) == 3
    assert len(db.filtrar_tarefas(tarefas, categorias=["Estudos"])) == 1
    assert len(db.filtrar_tarefas(tarefas, prioridades=["Alta"])) == 2
    assert len(db.filtrar_tarefas(tarefas, prioridades=["Alta"], categorias=["Trabalho"])) == 1
    assert len(db.filtrar_tarefas(tarefas, status=["Concluída"])) == 1


def test_indicadores():
    tarefas = [_t(status="Pendente"), _t(status="Em andamento"),
               _t(status="Concluída"), _t(status="Concluída")]
    assert db.calcular_indicadores(tarefas) == {
        "total": 4, "pendentes": 1, "em_andamento": 1, "concluidas": 2, "progresso": 50,
    }
    assert db.calcular_indicadores([])["progresso"] == 0


def test_minha_semana():
    hoje = date(2030, 1, 7)
    tarefas = [
        _t(data_entrega=str(hoje + timedelta(days=3))),
        _t(data_entrega=str(hoje - timedelta(days=1))),           # atrasada: aparece
        _t(data_entrega=str(hoje + timedelta(days=6))),           # último dia da semana
        _t(data_entrega=str(hoje + timedelta(days=7))),           # fora da semana
        _t(data_entrega=str(hoje), status="Concluída"),           # concluída: não aparece
        _t(data_entrega=None),                                    # sem data: não aparece
    ]
    semana = db.tarefas_da_semana(tarefas, hoje)
    assert [t["data_entrega"] for t in semana] == ["2030-01-06", "2030-01-10", "2030-01-13"]

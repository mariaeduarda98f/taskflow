"""Testes da interface (app.py) usando o banco falso, sem internet."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_tarefas import ClienteFalso

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "chave-de-teste")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["cliente"] = ClienteFalso()
    at.session_state["usuario"] = "teste@exemplo.com"
    return at.run()


def ir_para(at, pagina):
    at.session_state["pagina"] = pagina
    return at.run()


def botao(at, texto):
    return next(b for b in at.button if b.label == texto)


def test_tela_de_login_sem_usuario(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "chave-de-teste")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["cliente"] = ClienteFalso()
    at.run()
    assert not at.exception
    assert [b.label for b in at.button] == ["Entrar", "Criar conta"]


def test_painel_vazio(app):
    assert not app.exception
    assert [m.value for m in app.metric] == ["0", "0", "0", "0%"]
    assert "Nenhum prazo" in app.info[0].value


def test_fluxo_completo_pela_interface(app):
    cliente = app.session_state["cliente"]

    # Cadastrar
    app = ir_para(app, "Nova tarefa")
    app.text_input[0].input("Entregar trabalho")
    app.selectbox[0].select("Trabalho")
    app.date_input[0].set_value(date.today())
    botao(app, "Adicionar tarefa").click().run()
    assert not app.exception
    assert app.success[0].value == "Tarefa adicionada!"
    assert cliente.linhas[0]["titulo"] == "Entregar trabalho"

    # Painel e Minha Semana mostram a tarefa
    app = ir_para(app, "Painel")
    assert [m.value for m in app.metric] == ["1", "1", "0", "0%"]
    assert any("Entregar trabalho" in m.value for m in app.markdown)

    # Concluir
    app = ir_para(app, "Tarefas")
    botao(app, "Concluir").click().run()
    assert cliente.linhas[0]["status"] == "Concluída"

    # Editar
    botao(app, "Editar").click().run()
    app.text_input[0].input("Trabalho revisado")
    botao(app, "Salvar").click().run()
    assert not app.exception
    assert cliente.linhas[0]["titulo"] == "Trabalho revisado"

    # Excluir (com confirmação)
    botao(app, "Excluir").click().run()
    botao(app, "Sim, excluir").click().run()
    assert cliente.linhas == []
    assert app.success[0].value == "Tarefa excluída."


def test_titulo_obrigatorio(app):
    app = ir_para(app, "Nova tarefa")
    next(b for b in app.button if b.label == "Adicionar tarefa").click().run()
    assert app.error[0].value == "O título é obrigatório."
    assert app.session_state["cliente"].linhas == []


class ErroAuth(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@pytest.mark.parametrize(
    "codigo, trecho",
    [("email_address_invalid", "não é aceito"),
     ("email_address_not_authorized", "SMTP"),
     ("over_email_send_rate_limit", "Limite de envio"),
     ("user_already_exists", "já está cadastrado")],
)
def test_mensagem_de_erro_no_cadastro(monkeypatch, codigo, trecho):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "chave-de-teste")
    monkeypatch.setattr("database.cadastrar_usuario", lambda *a: (_ for _ in ()).throw(ErroAuth(codigo)))
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["cliente"] = ClienteFalso()
    at.run()
    at.text_input(key="cadastro_email").input("pessoa@gmail.com")
    at.text_input(key="cadastro_senha").input("senha123")
    at.text_input(key="cadastro_confirmar").input("senha123")
    next(b for b in at.button if b.label == "Criar conta").click().run()
    assert trecho in at.error[0].value


def test_painel_mostra_graficos(app):
    app = ir_para(app, "Nova tarefa")
    app.text_input[0].input("Estudar Python")
    botao(app, "Adicionar tarefa").click().run()
    app = ir_para(app, "Painel")
    assert not app.exception
    assert len(app.get("vega_lite_chart")) == 2

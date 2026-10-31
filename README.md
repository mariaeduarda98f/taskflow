# TaskFlow

Organizador de tarefas pessoal, acadêmico e profissional, feito com **Python + Streamlit** e dados salvos na nuvem com **Supabase (PostgreSQL)**.

## Funcionalidades

- Cadastro e login com e-mail e senha
- Cadastrar, editar, concluir e excluir tarefas (título, descrição, categoria, prioridade, data de entrega e status)
- Categorias: **Pessoal**, **Estudos**, **Trabalho**
- Prioridades: **Alta**, **Média**, **Baixa**
- Status: **Pendente**, **Em andamento**, **Concluída**
- Filtros por categoria, prioridade e status
- **Painel** com total de tarefas, pendentes, concluídas e percentual de progresso
- **Minha Semana**: prazos dos próximos 7 dias (e tarefas atrasadas)
- Cada usuário vê e altera **somente as próprias tarefas** (Row Level Security)

## Estrutura do projeto

```
taskflow/
├── app.py                 # Interface (telas do Streamlit)
├── database.py            # Conexão com o Supabase, login e operações das tarefas
├── supabase/schema.sql    # Cria a tabela e as regras de segurança (RLS)
├── tests/                 # Testes automáticos
├── .streamlit/config.toml # Cores do tema
├── requirements.txt       # Bibliotecas Python
├── .env.example           # Modelo das variáveis de ambiente (sem valores)
└── .gitignore             # Impede que segredos (.env) vão para o GitHub
```

## 1. Configurar o Supabase

1. Crie uma conta e um projeto em <https://supabase.com>.
2. No menu do projeto, abra **SQL Editor → New query**, cole todo o conteúdo de [`supabase/schema.sql`](supabase/schema.sql) e clique em **Run**.
   Isso cria a tabela `tarefas` e ativa o **RLS** (cada usuário só acessa as próprias linhas).
3. Abra **Project Settings → API** e copie:
   - **Project URL** → será o `SUPABASE_URL`
   - Chave **anon public** → será o `SUPABASE_KEY`

   > Use somente a chave **anon**. Nunca use a chave `service_role` no app: ela ignora o RLS.
4. (Opcional) Em **Authentication → Sign In / Providers → Email**, você pode desligar **Confirm email** para não precisar confirmar o e-mail ao criar conta. Se deixar ligado, o usuário recebe um e-mail e só consegue entrar depois de confirmar.

## 2. Rodar no seu computador

Pré-requisito: Python 3.10 ou mais novo.

```bash
git clone https://github.com/mariaeduarda98f/taskflow.git
cd taskflow

# Criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Instalar as bibliotecas
pip install -r requirements.txt

# Criar o arquivo de segredos a partir do modelo
cp .env.example .env             # Windows: copy .env.example .env
```

Abra o arquivo `.env` e preencha `SUPABASE_URL` e `SUPABASE_KEY`. Depois:

```bash
streamlit run app.py
```

O navegador abre em <http://localhost:8501>. Crie uma conta na aba **Criar conta** e comece a usar.

## 3. Rodar os testes

```bash
pip install pytest
pytest
```

- `tests/test_tarefas.py`: testa cadastro, edição, conclusão, exclusão, filtros, painel e Minha Semana usando um banco falso (não precisa de internet).
- `tests/test_app.py`: testa as telas (cadastrar, concluir, editar e excluir pela interface).
- `tests/test_integracao.py`: testa no Supabase de verdade, incluindo o RLS. Só roda se você preencher `TEST_EMAIL` e `TEST_SENHA` no `.env` com um usuário de teste já cadastrado. Caso contrário, aparece como `skipped`.

## 4. Publicar no Streamlit Community Cloud

1. Confirme que o código está no GitHub e que o arquivo `.env` **não** foi enviado (o `.gitignore` já cuida disso).
2. Acesse <https://share.streamlit.io>, entre com sua conta do GitHub e clique em **Create app**.
3. Escolha o repositório `mariaeduarda98f/taskflow`, a branch `main` e o arquivo `app.py`.
4. Em **Advanced settings → Secrets**, cole (com os seus valores):

   ```toml
   SUPABASE_URL = "https://xxxxxxxx.supabase.co"
   SUPABASE_KEY = "sua-chave-anon"
   ```

5. Clique em **Deploy**. Em alguns minutos o app fica disponível em um endereço `https://....streamlit.app`, que você pode abrir no computador e no celular.
6. Se a confirmação de e-mail estiver ligada, vá ao Supabase em **Authentication → URL Configuration** e coloque o endereço do app em **Site URL**, para que o link do e-mail aponte para o lugar certo.

## Segurança

- Nenhuma senha ou chave fica no código: elas são lidas do `.env` (local) ou dos **Secrets** (Streamlit Cloud).
- O `.gitignore` bloqueia `.env` e `.streamlit/secrets.toml`.
- As senhas são guardadas pelo Supabase Auth (com criptografia), nunca na tabela de tarefas.
- O **Row Level Security** no PostgreSQL garante que, mesmo que alguém tente acessar o banco diretamente com a chave anon, só consegue ver e alterar as tarefas do próprio usuário logado.

## Limitações desta primeira versão

- Ao recarregar a página (F5), é preciso fazer login de novo.
- Não há recuperação de senha pela interface (pode ser feita pelo painel do Supabase).


# 🤖 Bot de Baisco de Monitoramento no Discord

Bot Discord para Windows que monitora recursos do sistema, envia pings automáticos a cada 3 horas e permite testes de estresse de CPU, RAM e disco. Desenvolvido para testar a capacidade de hospedagem de bots em ambientes desktop.


## 📋 Pré‑requisitos

- **Python 3.8+** instalado ([python.org](https://www.python.org/downloads/))
- **discord.py** e **psutil**:
  ```bash
  pip install discord.py psutil
  ```
- Um bot criado no [Discord Developer Portal](https://discord.com/developers/applications) com:
  - Token copiado
  - **Message Content Intent** ativado (em *Bot > Privileged Gateway Intents*)

---

## 🚀 Instalação e configuração

1. Clone ou baixe o arquivo `bot.py` para uma pasta de sua escolha.
2. Abra o arquivo e insira o token do seu bot na linha:
   ```python
   TOKEN = "SEU_TOKEN_AQUI"
   ```
3. (Opcional) Ajuste a senha da sequência especial alterando a variável `SENHA_DESTRUICAO` (a padrão é `"destruir123"`).
4. Execute o bot:
   ```bash
   python bot.py
   ```

---

## ⚙️ Funcionalidades

- **Pings automáticos** a cada 3 horas (08 horários UTC: 00h, 03h, 06h, 09h, 12h, 15h, 18h, 21h)
- **Monitoramento da máquina** com dados de CPU, RAM, disco e uptime
- **Testes de estresse** controlados por comando (CPU, RAM, disco)
- **Comunicação bidirecional** – envie mensagens do Discord para o terminal do servidor
- **Comandos com prefixo `$$`** e suporte a help personalizado
- **Mecanismo de segurança** que ignora pings anteriores à hora de início no primeiro dia
- **Sequência especial oculta** para desligamento do bot (não listada no help)

---


## 📟 Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `$$start` | Ativa o envio de pings automáticos no canal atual |
| `$$stop` | Para os pings automáticos |
| `$$ping` | Exibe latência, status da máquina, consumo do bot e resumo do dia |
| `$$daily` | Funciona como o `$$ping` (compatibilidade) |
| `$$ciclo` | Mostra informações detalhadas dos ciclos de ping do dia |
| `$$terminal [mensagem]` | Envia uma mensagem para o terminal onde o bot está rodando |
| `$$stress <cpu/ram/disk/stop> [valor]` | Testes de estresse: <br> `cpu <segundos>` –     consome CPU por X segundos <br> `ram <MB>` – aloca X MB de RAM <br> `disk <MB>` – cria arquivo temporário de X MB <br> `stop` – interrompe todos os estresses |
| `$$help` | Lista todos os comandos públicos |


---

## 🧪 Exemplos de uso

- Iniciar os pings automáticos:
  ```
  $$start
  ```
- Ver status completo da máquina:
  ```
  $$ping
  ```
- Estressar a CPU por 60 segundos:
  ```
  $$stress cpu 60
  ```
- Alocar 512 MB de RAM:
  ```
  $$stress ram 512
  ```
- Parar todos os estresses:
  ```
  $$stress stop
  ```
- Enviar uma mensagem ao terminal do servidor:
  ```
  $$terminal Servidor está estável
  ```

---

## 🖥️ Execução contínua no Windows

Para manter o bot rodando mesmo após fechar o terminal:

1. Crie um arquivo `iniciar_bot.bat` com o conteúdo:
   ```batch
   @echo off
   cd /d "C:\caminho\para\pasta"
   python bot.py
   pause
   ```
2. Para iniciar sem janela, use `pythonw.exe` ou execute o `.bat` via Agendador de Tarefas.

---

## 📝 Notas importantes

- **Fuso horário**: todos os pings seguem o horário **UTC**. Para ajustar ao horário local, modifique `HORARIOS_PING` no código.
- **Primeiro dia**: se o bot for iniciado após alguns ciclos, os pings já passados são ignorados, começando a contar apenas a partir do próximo ciclo.
- **Consumo de recursos**: o bot é extremamente leve, mas os comandos de estresse (`$$stress`) consumirão recursos intencionalmente para testes.

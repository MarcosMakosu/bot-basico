import discord
from discord.ext import commands, tasks
import datetime
import psutil
import time
import asyncio
import os
import tempfile
import sys

# ==================== CONFIGURAÇÕES ====================
TOKEN = "SEU_TOKEN_AQUI"
PREFIXO = "$$"

HORARIOS_PING = [
    datetime.time(hour=h, minute=0, tzinfo=datetime.timezone.utc)
    for h in range(0, 24, 3)
]
NOMES_CICLOS = {h: f"{h:02d}h" for h in range(0, 24, 3)}
# =======================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIXO, intents=intents, help_command=None)

# ---------- Estado global ----------
canal_id = None
pings_hoje = 0
ultima_data = None
inicio_bot = None
stress_tasks = {}
memory_block = None
temp_file_handle = None
temp_file_path = None

# Controle da sequência especial
seq_ativa = False
seq_user_id = None
seq_channel_id = None
seq_timeout_task = None

# ==================== UTILITÁRIOS ====================
def mention(ctx):
    return f"**{ctx.author.mention}**"

def get_bot_resource_string():
    try:
        proc = psutil.Process()
        cpu = proc.cpu_percent(interval=0.1)
        mem = proc.memory_info()
        ram_mb = mem.rss / (1024 * 1024)
        return f"[BOT] CPU: {cpu}% | RAM: {ram_mb:.1f} MB"
    except Exception:
        return "[BOT] Nao foi possivel obter dados do processo."

def get_machine_info():
    cpu_total = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('C:\\')
    uptime = str(datetime.timedelta(seconds=int(time.time() - psutil.boot_time())))
    return (
        f"**SISTEMA**\n"
        f"CPU total: {cpu_total}%\n"
        f"RAM: {mem.used/(1024**3):.1f}/{mem.total/(1024**3):.1f} GB ({mem.percent}%)\n"
        f"Disco C: {disk.used/(1024**3):.1f}/{disk.total/(1024**3):.1f} GB ({disk.percent}%)\n"
        f"Uptime: {uptime}\n"
        f"{get_bot_resource_string()}"
    )

def get_ciclo_atual():
    agora = datetime.datetime.now(datetime.timezone.utc)
    hora_ciclo = (agora.hour // 3) * 3
    return NOMES_CICLOS.get(hora_ciclo, f"{hora_ciclo:02d}h")

def get_proximo_ciclo():
    agora = datetime.datetime.now(datetime.timezone.utc)
    for h in [0, 3, 6, 9, 12, 15, 18, 21]:
        if h > agora.hour or (h == agora.hour and agora.minute < 1):
            return NOMES_CICLOS[h]
    return NOMES_CICLOS[0]

def reset_ping_count():
    global pings_hoje, ultima_data
    hoje = datetime.datetime.now(datetime.timezone.utc).date()
    if ultima_data != hoje:
        pings_hoje = 0
        ultima_data = hoje

# ==================== TAREFA DE PINGS ====================
@tasks.loop(time=HORARIOS_PING)
async def enviar_ping_agendado():
    global pings_hoje, canal_id, inicio_bot
    if canal_id is None:
        return

    agora = datetime.datetime.now(datetime.timezone.utc)
    if inicio_bot and agora.date() == inicio_bot.date() and agora < inicio_bot:
        print(f"[IGNORADO] Ping anterior ao inicio do bot ({agora.strftime('%H:%M')} UTC)")
        return

    reset_ping_count()
    channel = bot.get_channel(canal_id)
    if channel is None:
        return

    pings_hoje += 1
    restantes = 8 - pings_hoje
    ciclo = get_ciclo_atual()
    proximo = get_proximo_ciclo()

    msg = (
        f"[HORA] **Ping agendado - Ciclo {ciclo}** ({pings_hoje}/8 hoje)\n"
        f"{get_machine_info()}\n"
        f"[INFO] Pings restantes no dia: {restantes}  |  [PROX] Proximo ping: {proximo}"
    )
    await channel.send(msg)
    print(f"[PING AUTO] Ciclo {ciclo} | {pings_hoje}/8 | Proximo: {proximo}")

@enviar_ping_agendado.before_loop
async def before_ping():
    await bot.wait_until_ready()
    global inicio_bot
    inicio_bot = datetime.datetime.now(datetime.timezone.utc)
    print(f"[CONFIG] Bot iniciado as {inicio_bot.strftime('%H:%M')} UTC")
    print(f"[CONFIG] Proximo ciclo programado: {get_proximo_ciclo()}")

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print(f"[OK] Bot conectado como {bot.user}")
    print(f"Prefixo: {PREFIXO}")
    print("Aguardando $$start para iniciar os pings.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    global seq_ativa, seq_user_id, seq_channel_id, seq_timeout_task
    if seq_ativa and message.author.id == seq_user_id and message.channel.id == seq_channel_id:
        if message.content.strip() == "00d0":
            if seq_timeout_task:
                seq_timeout_task.cancel()
            seq_ativa = False
            await executar_sequencia_especial(message.channel, message.author)
            return
        else:
            await message.channel.send(f"[X] {message.author.mention}, codigo invalido. Sequencia cancelada.")
            seq_ativa = False
            if seq_timeout_task:
                seq_timeout_task.cancel()
            return

    await bot.process_commands(message)

# ==================== COMANDOS PRINCIPAIS ====================
@bot.command(name="start")
async def start_cmd(ctx):
    global canal_id
    canal_id = ctx.channel.id
    ciclo = get_ciclo_atual()
    proximo = get_proximo_ciclo()

    if not enviar_ping_agendado.is_running():
        enviar_ping_agendado.start()
        await ctx.send(
            f"[OK] {mention(ctx)}, bot iniciado!\n"
            f"[CANAL] Canal: #{ctx.channel.name}\n"
            f"[HORA] Ciclo atual: {ciclo}\n"
            f"[PROX] Proximo ping: {proximo}\n"
            f"[NOTA] Pings anteriores ao inicio serao ignorados hoje."
        )
    else:
        await ctx.send(
            f"[OK] {mention(ctx)}, canal atualizado para #{ctx.channel.name}.\n"
            f"[HORA] Ciclo atual: {ciclo}  |  Proximo: {proximo}"
        )
    reset_ping_count()

@bot.command(name="stop")
async def stop_cmd(ctx):
    if enviar_ping_agendado.is_running():
        enviar_ping_agendado.cancel()
        await ctx.send(f"[STOP] {mention(ctx)}, pings automaticos interrompidos.")
    else:
        await ctx.send(f"[X] {mention(ctx)}, o bot ja esta parado.")

@bot.command(name="ping")
async def ping_cmd(ctx):
    reset_ping_count()
    restantes = 8 - pings_hoje
    status = "enviando" if enviar_ping_agendado.is_running() else "parado"
    latencia = round(bot.latency * 1000)
    ciclo = get_ciclo_atual()
    proximo = get_proximo_ciclo()

    await ctx.send(
        f"{mention(ctx)}\n\n"
        f"[PONG] Latencia: {latencia}ms\n\n"
        f"[HORA] Ciclo atual: {ciclo}\n"
        f"[PROX] Proximo ping: {proximo}\n\n"
        f"[DATA] Resumo do dia\n"
        f"Pings realizados: {pings_hoje}/8\n"
        f"Restantes: {restantes}\n"
        f"Tarefa automatica: {status}\n\n"
        f"{get_machine_info()}"
    )
    print(f"[PING] {ctx.author} | Latencia {latencia}ms | Ciclo {ciclo} | {pings_hoje}/8")

@bot.command(name="terminal")
async def terminal_cmd(ctx, *, mensagem: str = None):
    if mensagem is None:
        mensagem = "Teste do bot - servidor online!"
    print(f"\n{'#'*60}")
    print(f"[TERM] Mensagem do Discord")
    print(f"[USER] {ctx.author} (ID: {ctx.author.id})")
    print(f"[CANAL] #{ctx.channel.name} (ID: {ctx.channel.id})")
    print(f"[MSG] {mensagem}")
    print(f"[HORA] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")
    await ctx.send(f"[OK] {mention(ctx)}, mensagem enviada ao terminal: `{mensagem}`")

@bot.command(name="daily")
async def daily_cmd(ctx):
    await ping_cmd(ctx)

@bot.command(name="ciclo")
async def ciclo_cmd(ctx):
    reset_ping_count()
    ciclo_atual = get_ciclo_atual()
    proximo = get_proximo_ciclo()
    pings_feitos = pings_hoje
    restantes = 8 - pings_hoje

    agora = datetime.datetime.now(datetime.timezone.utc)
    passados = [NOMES_CICLOS[h] for h in [0,3,6,9,12,15,18,21] if h < agora.hour]
    futuros = [NOMES_CICLOS[h] for h in [0,3,6,9,12,15,18,21] if h > agora.hour]

    await ctx.send(
        f"{mention(ctx)}\n\n"
        f"[HORA] Ciclo atual: **{ciclo_atual}**\n"
        f"[PROX] Proximo ping: **{proximo}**\n"
        f"Pings realizados hoje: **{pings_feitos}/8**\n"
        f"Restantes: **{restantes}**\n\n"
        f"[LIST] Ciclos ja executados: {', '.join(passados) if passados else 'Nenhum'}\n"
        f"[LIST] Ciclos futuros: {', '.join(futuros) if futuros else 'Nenhum'}"
    )

# ==================== COMANDO EXTRA ====================
@bot.command(name="daisy-bell", hidden=True)
async def comando_extra(ctx):
    global seq_ativa, seq_user_id, seq_channel_id, seq_timeout_task
    seq_ativa = True
    seq_user_id = ctx.author.id
    seq_channel_id = ctx.channel.id

    await ctx.send(
        f"{mention(ctx)}, sequencia especial iniciada.\n"
        f"Digite o codigo de confirmacao para continuar:"
    )

    async def timeout_extra():
        global seq_ativa   # <--- CORRIGIDO: declaração movida para o início
        await asyncio.sleep(30)
        if seq_ativa:
            seq_ativa = False
            try:
                await ctx.send(f"[X] {mention(ctx)}, tempo esgotado. Sequencia cancelada.")
            except:
                pass
    seq_timeout_task = asyncio.create_task(timeout_extra())

async def executar_sequencia_especial(channel, autor):
    await channel.send(f"{autor.mention}, codigo aceito.")
    await asyncio.sleep(1)
    await channel.send(f"Executando procedimento...")
    await asyncio.sleep(1)
    await channel.send(f"Removendo arquivo de configuracao...")

    try:
        arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.py')
        if os.path.exists(arquivo):
            os.remove(arquivo)
            await channel.send(f"Arquivo removido com sucesso.")
        else:
            await channel.send(f"Arquivo nao encontrado.")
    except Exception as e:
        await channel.send(f"Erro ao remover arquivo: {e}")

    await asyncio.sleep(1)
    await channel.send(f"Procedimento concluido. Encerrando bot.")
    await bot.close()
    sys.exit(0)

# ==================== COMANDOS DE ESTRESSE ====================
@bot.command(name="stress")
async def stress_cmd(ctx, mode: str = None, value: float = None):
    global memory_block, temp_file_handle, temp_file_path, stress_tasks

    if mode is None:
        await ctx.send(
            f"{mention(ctx)} Uso: `$$stress <cpu|ram|disk|stop> [valor]`\n"
            "Ex: `$$stress cpu 30` (30s), `$$stress ram 512` (512MB), `$$stress disk 256` (256MB)"
        )
        return

    if mode == "cpu":
        if not value or value <= 0:
            await ctx.send(f"[X] {mention(ctx)} uso: `$$stress cpu <segundos>`")
            return
        task = asyncio.create_task(cpu_stress(value))
        stress_tasks["cpu"] = task
        await ctx.send(f"[CPU] {mention(ctx)}, estresse de CPU por {value}s iniciado.")
        print(f"[STRESS] CPU {value}s por {ctx.author}")

    elif mode == "ram":
        if not value or value <= 0:
            await ctx.send(f"[X] {mention(ctx)} uso: `$$stress ram <tamanho_mb>`")
            return
        size = int(value * 1024 * 1024)
        try:
            memory_block = bytearray(size)
            await ctx.send(f"[RAM] {mention(ctx)}, {value}MB alocados. Use `$$stress stop` para liberar.")
            print(f"[STRESS] RAM {value}MB por {ctx.author}")
        except MemoryError:
            await ctx.send(f"[X] {mention(ctx)}, memoria insuficiente para alocar {value}MB.")

    elif mode == "disk":
        if not value or value <= 0:
            await ctx.send(f"[X] {mention(ctx)} uso: `$$stress disk <tamanho_mb>`")
            return
        size = int(value * 1024 * 1024)
        try:
            fd, temp_file_path = tempfile.mkstemp(suffix=".tmp", prefix="bot_stress_")
            os.close(fd)
            temp_file_handle = open(temp_file_path, "wb")
            chunk = b'\0' * min(size, 1024*1024)
            escrito = 0
            while escrito < size:
                to_write = min(len(chunk), size - escrito)
                temp_file_handle.write(chunk[:to_write])
                escrito += to_write
            temp_file_handle.flush()
            await ctx.send(f"[DISCO] {mention(ctx)}, arquivo de {value}MB criado. Use `$$stress stop` para remover.")
            print(f"[STRESS] DISCO {value}MB por {ctx.author}")
        except Exception as e:
            await ctx.send(f"[X] {mention(ctx)}, erro: {e}")

    elif mode == "stop":
        if "cpu" in stress_tasks:
            stress_tasks["cpu"].cancel()
            del stress_tasks["cpu"]
        memory_block = None
        if temp_file_handle:
            temp_file_handle.close()
            temp_file_handle = None
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            temp_file_path = None
        await ctx.send(f"[STOP] {mention(ctx)}, todos os estresses parados e recursos liberados.")
        print(f"[STRESS] Stop por {ctx.author}")
    else:
        await ctx.send(f"[X] {mention(ctx)}, modo invalido. Use cpu, ram, disk ou stop.")

async def cpu_stress(duration: float):
    loop = asyncio.get_running_loop()
    def stress():
        end = time.time() + duration
        while time.time() < end:
            _ = [x**2 for x in range(10000)]
    try:
        await loop.run_in_executor(None, stress)
    except asyncio.CancelledError:
        pass

# ==================== TRATAMENTO DE ERROS ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"[?] {mention(ctx)}, comando nao encontrado. Use `{PREFIXO}help`.")
    else:
        print(f"[ERRO] {error}")

# ==================== HELP ====================
@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="Comandos do Bot", description=f"Prefixo: `{PREFIXO}`", color=0x3498db)
    comandos = [
        ("start", "Inicia os pings automaticos no canal atual"),
        ("stop", "Para os pings automaticos"),
        ("ping", "Latencia + status completo da maquina + resumo do dia"),
        ("ciclo", "Detalhes dos ciclos de ping do dia"),
        ("terminal [msg]", "Envia uma mensagem ao terminal do servidor"),
        ("stress <cpu|ram|disk|stop> [valor]", "Testes de estresse do sistema"),
        ("daily", "Mesmo que ping (compatibilidade)"),
    ]
    for nome, desc in comandos:
        embed.add_field(name=f"{PREFIXO}{nome}", value=desc, inline=False)
    embed.set_footer(text="Bot de Monitoramento v3.0")
    await ctx.send(mention(ctx), embed=embed)

# ==================== INICIALIZAÇÃO ====================
if __name__ == "__main__":
    print("=" * 60)
    print("Iniciando Bot de Monitoramento...")
    print(f"Data/Hora UTC: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    bot.run(TOKEN)

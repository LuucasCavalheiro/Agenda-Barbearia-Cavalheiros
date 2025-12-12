import tkinter as tk 
from tkinter import messagebox, ttk, simpledialog
import json
import os
from datetime import datetime, timedelta
from tkcalendar import Calendar
import shutil
import re
import webbrowser
from urllib.parse import quote
try:
    import holidays
    FERIADOS_BR = holidays.Brazil()  # feriados nacionais do Brasil
except ImportError:
    FERIADOS_BR = None

ARQUIVO_AGENDA = "agenda.json"
ARQUIVO_CLIENTES = "clientes.json"
BACKUP_DIR = "backups"
FERIADOS_FIXOS = {}

HORARIO_INICIO = (9, 0)    # 09:00
HORARIO_FIM = (20, 30)     # 20:30
INTERVALO = 30             # em minutos

SERVICOS = {
    "Cabelo": 30,
    "Barba": 30,
    "Cabelo e Barba": 60,
    "Outro": 30,
}

PRECO_SERVICOS = {
    "Cabelo": 50.00,
    "Barba": 40.00,
    "Cabelo e Barba": 80.0,
    "Outro": 80.0,
    "Oleo para Barba": 60.00,
    "Pomada para Cabelo Seco": 35.00,
    "Pomada para Cabelo Brilhoso": 35.00,
    "Balm para Barba": 35.00,
    "Minoxidil 10%": 70.00,
    "Escova Barba": 20.00,
    "Sabonete Esfoliante": 20.00,
    "Cera em pó p/ cabelo": 60.00,
}

DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

def normalizar_telefone_br(tel: str) -> str:
    """Retorna só dígitos, com DDI 55 (ex: 5549999999999)."""
    if not tel:
        return ""
    dig = re.sub(r"\D", "", tel)

    # se vier com 55 já, ok
    if dig.startswith("55") and len(dig) >= 12:
        return dig

    # se vier com 11 dígitos (DDD + 9 dígitos) ou 10 dígitos (DDD + 8)
    if len(dig) in (10, 11):
        return "55" + dig

    # se vier com 9 ou 8 (sem DDD), não dá pra adivinhar direito -> retorna como está
    return dig

def copiar_para_area_transferencia(texto: str):
    root.clipboard_clear()
    root.clipboard_append(texto)
    root.update()  # garante que ficou no clipboard

def whatsapp_confirmar_agendamento(nome_cliente: str, data_iso: str, hora: str):
    """Copia msg e, se tiver telefone cadastrado, abre WhatsApp com texto pronto."""
    tel = ""
    info = clientes.get(nome_cliente, {})
    if isinstance(info, dict):
        tel = info.get("tel", "")

    msg = f"Olá amigo, só pra confirmar: tudo certo hoje às {hora}?"
    copiar_para_area_transferencia(msg)

    tel_norm = normalizar_telefone_br(tel)

    # se tiver telefone ok, abre WhatsApp; se não, só copia e avisa
    if tel_norm and tel_norm.startswith("55"):
        url = f"https://wa.me/{tel_norm}?text={quote(msg)}"
        webbrowser.open(url)
        messagebox.showinfo("WhatsApp", "Mensagem copiada e WhatsApp aberto ✅")
    else:
        messagebox.showinfo("WhatsApp", "Mensagem copiada ✅\n(Cliente sem telefone válido cadastrado)")


# ---------- LÓGICA DA AGENDA ----------

def carregar_agenda():
    if not os.path.exists(ARQUIVO_AGENDA):
        return {}
    try:
        with open(ARQUIVO_AGENDA, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def salvar_agenda(agenda):
    with open(ARQUIVO_AGENDA, "w", encoding="utf-8") as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)
    
    # Salva o backup
    backup = "agenda_backup.json"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

# ---------- CLIENTES (ANIVERSÁRIOS) ----------

def carregar_clientes():
    if not os.path.exists(ARQUIVO_CLIENTES):
        return {}
    try:
        with open(ARQUIVO_CLIENTES, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def salvar_clientes(clientes):
    with open(ARQUIVO_CLIENTES, "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)
    
    fazer_backup()

def gerar_horarios():
    horarios = []
    hora, minuto = HORARIO_INICIO
    fim_h, fim_m = HORARIO_FIM
    while True:
        horarios.append(f"{hora:02d}:{minuto:02d}")
        if hora == fim_h and minuto == fim_m:
            break
        minuto += INTERVALO
        if minuto >= 60:
            minuto -= 60
            hora += 1
    return horarios

HORARIOS = gerar_horarios()

def garantir_dia_na_agenda(agenda, dia):
    if dia not in agenda:
        agenda[dia] = {h: None for h in HORARIOS}
    else:
        for h in HORARIOS:
            agenda[dia].setdefault(h, None)

def str_data_para_iso(data_str):
    """Converte 'DD/MM/AAAA' -> 'AAAA-MM-DD'."""
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def iso_para_br(data_iso):
    """Converte 'AAAA-MM-DD' -> 'DD/MM/AAAA'."""
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return data_iso

def dia_semana_br(data_iso):
    """Recebe 'AAAA-MM-DD' e retorna o dia da semana em PT-BR."""
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        indice = dt.weekday()  # 0 = segunda, 6 = domingo
        return DIAS_SEMANA[indice]
    except ValueError:
        return ""
    
def fazer_backup():
    """Cria uma cópia de agenda.json e clientes.json na pasta backups/."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    for arquivo in (ARQUIVO_AGENDA, ARQUIVO_CLIENTES):
        if os.path.exists(arquivo):
            nome_base, ext = os.path.splitext(os.path.basename(arquivo))
            destino = os.path.join(
                BACKUP_DIR,
                f"{nome_base}_{timestamp}{ext}"
            )
            shutil.copy2(arquivo, destino)

# ---------- CARREGA DADOS ----------

agenda = carregar_agenda()
clientes = carregar_clientes()

# ---------- INTERFACE GRÁFICA ----------

root = tk.Tk()
root.title("Agenda - Barbearia Cavalheiros")
root.geometry("510x600")

# ----- TOPO: DATA + BOTÕES -----

frame_data = tk.Frame(root)
frame_data.pack(pady=10)

tk.Label(frame_data, text="Data (DD/MM/AAAA): ").pack(side=tk.LEFT)

data_var = tk.StringVar()

def atualizar_campos_de_data():
    """Atualiza agenda, dia da semana e aviso de aniversário."""
    atualizar_lista_agenda()

def set_data_hoje():
    hoje = datetime.now().strftime("%d/%m/%Y")
    data_var.set(hoje)
    atualizar_campos_de_data()

def abrir_calendario():
    # Garante posição/tamanho atual da janela principal
    root.update_idletasks()

    root_x = root.winfo_rootx()
    root_y = root.winfo_rooty()
    root_w = root.winfo_width()

    win = tk.Toplevel(root)
    win.title("Selecionar Data")

    largura = 300
    altura = 300

    x = root_x + root_w + 10
    y = root_y

    win.geometry(f"{largura}x{altura}+{x}+{y}")

    cal = Calendar(
        win,
        selectmode="day",
        date_pattern="dd/mm/yyyy"
    )
    cal.pack(pady=10)

    def confirmar_data():
        data_escolhida = cal.get_date()
        data_var.set(data_escolhida)
        atualizar_campos_de_data()
        win.destroy()

    tk.Button(win, text="Confirmar", command=confirmar_data).pack(pady=10)

data_entry = tk.Entry(frame_data, textvariable=data_var, width=12, justify="center")
data_entry.pack(side=tk.LEFT, padx=5)

btn_hoje = tk.Button(frame_data, text="Hoje", command=set_data_hoje)
btn_hoje.pack(side=tk.LEFT)

btn_calendario = tk.Button(frame_data, text="📅", command=abrir_calendario)
btn_calendario.pack(side=tk.LEFT, padx=5)

# ----- DIA DA SEMANA + AVISO DE ANIVERSÁRIO -----

dia_semana_var = tk.StringVar()
label_dia_semana = tk.Label(root, textvariable=dia_semana_var, font=("Arial", 10))
label_dia_semana.pack()

# 👇 NOVO: aviso de feriado
aviso_feriado_var = tk.StringVar()
label_feriado = tk.Label(root, textvariable=aviso_feriado_var, font=("Arial", 9), fg="red")
label_feriado.pack(pady=(0, 2))

aviso_aniver_var = tk.StringVar()
label_aniver = tk.Label(root, textvariable=aviso_aniver_var, font=("Arial", 9), fg="purple")
label_aniver.pack(pady=(0, 5))

# ----- LISTA DA AGENDA DO DIA -----

frame_lista = tk.Frame(root)
frame_lista.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

label_dia = tk.Label(frame_lista, text="", font=("Arial", 12, "bold"))
label_dia.pack(pady=5)

lista_horarios = tk.Listbox(frame_lista, height=12, width=70)
lista_horarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scroll = tk.Scrollbar(frame_lista, command=lista_horarios.yview)
scroll.pack(side=tk.RIGHT, fill=tk.Y)
lista_horarios.config(yscrollcommand=scroll.set)

# ----- FUNÇÕES DE ATUALIZAÇÃO DA TELA -----

def eh_feriado_data_iso(data_iso):
    """
    Recebe 'AAAA-MM-DD' e diz se é feriado.
    Retorna (eh_feriado: bool, nome_feriado: str ou None)
    """
    # Se tiver biblioteca de feriados
    if FERIADOS_BR is not None:
        try:
            dt = datetime.strptime(data_iso, "%Y-%m-%d").date()
        except ValueError:
            return False, None
        nome = FERIADOS_BR.get(dt)
        if nome:
            return True, str(nome)

    # Fallback opcional se você tiver aquele dicionário FERIADOS_FIXOS
    if "FERIADOS_FIXOS" in globals():
        try:
            dt2 = datetime.strptime(data_iso, "%Y-%m-%d")
            chave = dt2.strftime("%d-%m")
        except ValueError:
            return False, None
        nome2 = FERIADOS_FIXOS.get(chave)
        if nome2:
            return True, nome2

    return False, None

def atualizar_aviso_feriado():
    """Mostra aviso se o dia selecionado for feriado (Brasil)."""
    aviso_feriado_var.set("")

    # se não tiver biblioteca de feriados, não faz nada
    if FERIADOS_BR is None:
        return

    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        return

    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except ValueError:
        return

    nome_feriado = FERIADOS_BR.get(dt)
    if nome_feriado:
        aviso_feriado_var.set(f"📢 FERIADO: {nome_feriado}")
    else:
        aviso_feriado_var.set("")

def atualizar_dia_semana():
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        dia_semana_var.set("")
        return
    nome_dia = dia_semana_br(data_iso)
    if nome_dia:
        dia_semana_var.set(f"Dia da semana: {nome_dia}")
    else:
        dia_semana_var.set("")

def atualizar_aviso_aniversario():
    """Mostra aviso se o dia selecionado for aniversário de alguém."""
    data_str = data_var.get().strip()
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
    except ValueError:
        aviso_aniver_var.set("")
        return

    dia_mes = dt.strftime("%d/%m")
    aniversariantes = []
    for nome, info in clientes.items():
        nasc = info.get("nasc")  # formato 'DD/MM'
        if nasc == dia_mes:
            tel = info.get("tel")
            if tel:
                aniversariantes.append(f"{nome} ({tel})")
            else:
                aniversariantes.append(nome)

    if aniversariantes:
        if len(aniversariantes) == 1:
            texto = f"🎉 Aniversário de {aniversariantes[0]}!"
        else:
            texto = "🎉 Aniversários: " + ", ".join(aniversariantes)
        aviso_aniver_var.set(texto)
    else:
        aviso_aniver_var.set("")

def atualizar_lista_agenda():
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)
    salvar_agenda(agenda)

    atualizar_dia_semana()
    atualizar_aviso_aniversario()
    atualizar_aviso_feriado()

    lista_horarios.delete(0, tk.END)
    label_dia.config(text=f"Agenda do dia {iso_para_br(data_iso)}")

    for h in HORARIOS:
        slot = agenda[data_iso].get(h)
        if slot is None:
            texto = f"{h} - LIVRE"
        else:
            texto = f"{h} - {slot['cliente']} ({slot['servico']})"
        lista_horarios.insert(tk.END, texto)

# ----- JANELA DE NOVO AGENDAMENTO -----

def janela_agendar():
    # Usa a data que está na tela
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    # Janela do agendamento
    win = tk.Toplevel(root)
    win.title("Novo agendamento")
    win.geometry("450x470")

    tk.Label(win, text=f"Data: {iso_para_br(data_iso)}").pack(pady=5)

    # -------------------------------------------
    # NOME DO CLIENTE (COM COMBOBOX + SUGESTÕES)
    # -------------------------------------------
    tk.Label(win, text="Cliente (já cadastrado):").pack()

    nomes_clientes = sorted(clientes.keys())
    nome_var = tk.StringVar()

    combo_nome = ttk.Combobox(
        win,
        textvariable=nome_var,
        values=nomes_clientes,
        state="normal"  # pode digitar e escolher
    )
    combo_nome.pack(pady=5, fill=tk.X, padx=20)

    # label que mostra telefone / aniversário do cliente escolhido
    info_cli_var = tk.StringVar()
    label_info_cli = tk.Label(win, textvariable=info_cli_var,
                              font=("Arial", 9), fg="gray")
    label_info_cli.pack(pady=(0, 5))

    def atualizar_info_cliente(event=None):
        """Atualiza label com telefone/aniversário do cliente escolhido."""
        nome = nome_var.get().strip()
        info = clientes.get(nome)
        if not info:
            info_cli_var.set("")
            return

        nasc = info.get("nasc", "")
        tel = info.get("tel", "")

        partes = []
        if tel:
            partes.append(f"📞 {tel}")
        if nasc:
            partes.append(f"🎂 {nasc}")

        info_cli_var.set("   ".join(partes))

    combo_nome.bind("<<ComboboxSelected>>", atualizar_info_cliente)

    # Listbox de sugestões de nome
    lista_sugestoes = tk.Listbox(win, height=5)
    lista_sugestoes.pack(fill=tk.X, padx=20)

    def atualizar_sugestoes():
        texto = nome_var.get().lower()
        lista_sugestoes.delete(0, tk.END)
        if not texto:
            return
        for n in nomes_clientes:
            if texto in n.lower():
                lista_sugestoes.insert(tk.END, n)

    def escolher_sugestao(event=None):
        if not lista_sugestoes.curselection():
            return
        idx = lista_sugestoes.curselection()[0]
        nome_escolhido = lista_sugestoes.get(idx)
        nome_var.set(nome_escolhido)
        lista_sugestoes.delete(0, tk.END)
        atualizar_info_cliente()
        combo_nome.icursor(tk.END)
        combo_nome.focus()

    lista_sugestoes.bind("<Double-Button-1>", escolher_sugestao)

    def mover_selecao(delta):
        """Move a seleção da listbox para cima/baixo."""
        if lista_sugestoes.size() == 0:
            return
        current = lista_sugestoes.curselection()
        if current:
            idx = current[0] + delta
        else:
            idx = 0 if delta > 0 else lista_sugestoes.size() - 1
        idx = max(0, min(lista_sugestoes.size() - 1, idx))
        lista_sugestoes.select_clear(0, tk.END)
        lista_sugestoes.select_set(idx)
        lista_sugestoes.activate(idx)
        lista_sugestoes.see(idx)

    def on_key_release(event):
        # ignora teclas de navegação aqui
        if event.keysym in ("Up", "Down", "Return"):
            return
        atualizar_sugestoes()
        atualizar_info_cliente()

    def on_down(event):
        mover_selecao(1)
        return "break"

    def on_up(event):
        mover_selecao(-1)
        return "break"

    def on_enter(event):
        if lista_sugestoes.size() > 0:
            escolher_sugestao()
            return "break"

    combo_nome.bind("<KeyRelease>", on_key_release)
    combo_nome.bind("<Down>", on_down)
    combo_nome.bind("<Up>", on_up)
    combo_nome.bind("<Return>", on_enter)

    # -------------------------------------------
    # SERVIÇO
    # -------------------------------------------
    tk.Label(win, text="Serviço:").pack()
    servico_var = tk.StringVar(value="Cabelo")
    for s in SERVICOS.keys():
        tk.Radiobutton(win, text=s, variable=servico_var, value=s).pack(anchor="w")

    # Horário
    tk.Label(win, text="Horário inicial:").pack(pady=(10, 0))
    horario_var = tk.StringVar(value=HORARIOS[0])
    combo_horario = ttk.Combobox(
        win,
        textvariable=horario_var,
        values=HORARIOS,
        state="readonly"
    )
    combo_horario.pack(pady=5)

    # Observações
    tk.Label(win, text="Observações (opcional):").pack()
    obs_entry = tk.Entry(win)
    obs_entry.pack(pady=5, fill=tk.X, padx=20)

    # -------------------------------------------
    # SALVAR AGENDAMENTO
    # -------------------------------------------
    def salvar_agendamento():
        nome = nome_var.get().strip()

        # agora SÓ deixa agendar cliente já cadastrado
        if not nome:
            messagebox.showerror("Erro", "Escolha o nome do cliente.")
            return

        if nome not in clientes:
            messagebox.showerror(
                "Erro",
                "Cliente não cadastrado.\nUse o botão 'Cadastrar Clientes' antes de agendar."
            )
            return

        servico = servico_var.get()
        duracao = SERVICOS[servico]
        hora_inicial = horario_var.get()
        obs = obs_entry.get().strip()

        if hora_inicial not in HORARIOS:
            messagebox.showerror("Erro", "Horário inválido.")
            return

        blocos = duracao // INTERVALO
        indice = HORARIOS.index(hora_inicial)

        blocos_horarios = HORARIOS[indice: indice + blocos]

        # Verificar se todos os blocos estão livres
        if any(agenda[data_iso].get(h) is not None for h in blocos_horarios):
            messagebox.showerror(
                "Erro",
                "Um ou mais horários desse período já estão ocupados."
            )
            return

        # Gravar agendamento
        
        preco = PRECO_SERVICOS.get(servico, 0.0)

        for h in blocos_horarios:
            agenda[data_iso][h] = {
            "cliente": nome,
            "servico": servico,
            "duracao": duracao,
            "obs": obs,
            "inicio": hora_inicial,
            "preco": preco,
            "pago": False,
            "extras": [],
            "pacote": False,            # 👈 normal é NÃO ser pacote
            "pacote_nome": None,
            "pacote_valor_mensal": 0.0,
    }
            

        salvar_agenda(agenda)
        atualizar_lista_agenda()
        messagebox.showinfo("Sucesso", "Agendamento realizado com sucesso!")
        win.destroy()

    tk.Button(win, text="✅ Salvar agendamento", command=salvar_agendamento).pack(pady=15)

# ----- CANCELAR HORÁRIO -----

def cancelar_agendamento_em(data_iso, hora_inicio, parent=None):
    garantir_dia_na_agenda(agenda, data_iso)

    slot = agenda.get(data_iso, {}).get(hora_inicio)
    if not isinstance(slot, dict):
        messagebox.showinfo("Info", "Agendamento não encontrado.", parent=parent)
        return

    # garante que é o bloco inicial
    inicio = slot.get("inicio", hora_inicio)
    if inicio != hora_inicio:
        hora_inicio = inicio
        slot = agenda.get(data_iso, {}).get(hora_inicio)
        if not isinstance(slot, dict):
            messagebox.showinfo("Info", "Agendamento não encontrado.", parent=parent)
            return

    servico = slot.get("servico", "")
    cliente = slot.get("cliente", "")
    duracao = int(slot.get("duracao", 30))

    resp = messagebox.askyesno(
        "Confirmar",
        f"Cancelar {servico} de {cliente} em {iso_para_br(data_iso)} às {hora_inicio}?",
        parent=parent
    )
    if not resp:
        return

    blocos = duracao // INTERVALO
    idx = HORARIOS.index(hora_inicio)
    blocos_h = HORARIOS[idx: idx + blocos]

    for h in blocos_h:
        agenda[data_iso][h] = None

    salvar_agenda(agenda)

    # atualiza a tela principal pra essa data
    data_var.set(iso_para_br(data_iso))
    atualizar_campos_de_data()

    messagebox.showinfo("Sucesso", "Agendamento cancelado ✅", parent=parent)

def cancelar_horario():
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    selecao = lista_horarios.curselection()
    if selecao:
        linha = lista_horarios.get(selecao[0])
        hora = linha.split(" - ")[0]
    else:
        hora = simpledialog.askstring("Cancelar horário", "Digite o horário (ex: 09:00):")
        if not hora:
            return

    if hora not in HORARIOS:
        messagebox.showerror("Erro", "Horário inválido.")
        return

    slot = agenda[data_iso].get(hora)
    if slot is None:
        messagebox.showinfo("Info", "Esse horário já está livre.")
        return

    inicio = slot["inicio"]
    duracao = slot["duracao"]
    blocos = duracao // INTERVALO
    indice_inicio = HORARIOS.index(inicio)
    blocos_horarios = HORARIOS[indice_inicio: indice_inicio + blocos]

    resp = messagebox.askyesno(
        "Confirmar",
        f"Cancelar {slot['servico']} de {slot['cliente']} às {inicio}?"
    )
    if not resp:
        return

    for h in blocos_horarios:
        agenda[data_iso][h] = None

    salvar_agenda(agenda)
    atualizar_lista_agenda()
    messagebox.showinfo("Sucesso", "Horário cancelado com sucesso.")

# ----- ADICIONAR PRODUTOS EM AGENDAMENTOS -----
def adicionar_produto_em_agendamento(data_iso, hora_inicio, parent=None):
    garantir_dia_na_agenda(agenda, data_iso)

    slot = agenda.get(data_iso, {}).get(hora_inicio)
    if not isinstance(slot, dict):
        messagebox.showinfo("Info", "Agendamento não encontrado.", parent=parent)
        return

    # garante bloco inicial
    inicio = slot.get("inicio", hora_inicio)
    if inicio != hora_inicio:
        hora_inicio = inicio
        slot = agenda.get(data_iso, {}).get(hora_inicio)
        if not isinstance(slot, dict):
            messagebox.showinfo("Info", "Agendamento não encontrado.", parent=parent)
            return

    win = tk.Toplevel(parent if parent else root)
    win.title("Adicionar produto ao atendimento")
    win.geometry("380x260")

    tk.Label(win, text=f"{slot.get('cliente','')} - {iso_para_br(data_iso)} {hora_inicio}", font=("Arial", 10, "bold")).pack(pady=5)

    # lista só de produtos (tudo que NÃO é serviço)
    produtos = [k for k in PRECO_SERVICOS.keys() if k not in SERVICOS]
    produtos.sort()

    tk.Label(win, text="Produto:").pack()
    prod_var = tk.StringVar(value=produtos[0] if produtos else "")
    combo_prod = ttk.Combobox(win, textvariable=prod_var, values=produtos, state="readonly")
    combo_prod.pack(pady=5, fill=tk.X, padx=20)

    tk.Label(win, text="Quantidade:").pack()
    qtd_var = tk.StringVar(value="1")
    entry_qtd = tk.Entry(win, textvariable=qtd_var, width=6, justify="center")
    entry_qtd.pack(pady=5)

    tk.Label(win, text="Obs (opcional):").pack()
    obs_var = tk.StringVar(value="")
    entry_obs = tk.Entry(win, textvariable=obs_var)
    entry_obs.pack(pady=5, fill=tk.X, padx=20)

    def salvar_extra():
        produto = prod_var.get().strip()
        if not produto:
            messagebox.showerror("Erro", "Selecione um produto.", parent=win)
            return

        try:
            qtd = int(qtd_var.get())
            if qtd <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida.", parent=win)
            return

        valor_unit = float(PRECO_SERVICOS.get(produto, 0.0))
        valor_total = valor_unit * qtd
        obs = obs_var.get().strip()

        extra = {"nome": produto, "valor": valor_total, "qtd": qtd}
        if obs:
            extra["obs"] = obs

        slot.setdefault("extras", [])
        slot["extras"].append(extra)

        # aplica o mesmo extras em todos os blocos daquele atendimento
        duracao = int(slot.get("duracao", 30))
        blocos = duracao // INTERVALO
        idx = HORARIOS.index(hora_inicio)
        blocos_h = HORARIOS[idx: idx + blocos]
        for h in blocos_h:
            if isinstance(agenda[data_iso].get(h), dict):
                agenda[data_iso][h]["extras"] = slot["extras"]

        salvar_agenda(agenda)
        data_var.set(iso_para_br(data_iso))
        atualizar_campos_de_data()
        messagebox.showinfo("Sucesso", f"Produto adicionado ✅ (R$ {valor_total:.2f})", parent=win)
        win.destroy()

    tk.Button(win, text="➕ Adicionar", command=salvar_extra).pack(pady=10)

# ----- EDITAR AGENDAMENTO (AGORA PODE MUDAR DE DIA E TROCAR) -----

def janela_editar_agendamento_em(data_iso, hora_inicio):
    """Abre edição de um agendamento específico (data ISO e hora inicial)."""
    garantir_dia_na_agenda(agenda, data_iso)

    slot = agenda.get(data_iso, {}).get(hora_inicio)
    if not isinstance(slot, dict):
        messagebox.showinfo("Info", "Agendamento não encontrado.")
        return

    # garante que é o bloco inicial
    inicio = slot.get("inicio", hora_inicio)
    if inicio != hora_inicio:
        hora_inicio = inicio
        slot = agenda.get(data_iso, {}).get(hora_inicio)

    cliente = slot.get("cliente", "")
    servico = slot.get("servico", "")
    obs = slot.get("obs", "")
    inicio = slot.get("inicio", hora_inicio)

    pacote_flag = slot.get("pacote", False)
    pacote_nome = slot.get("pacote_nome")
    pacote_valor = slot.get("pacote_valor_mensal", 0.0)

    extras_orig = slot.get("extras", [])
    pago_original = bool(slot.get("pago", False))

    edit = tk.Toplevel(root)
    edit.title("Editar agendamento")
    edit.geometry("360x360")

    tk.Label(edit, text=f"Data: {iso_para_br(data_iso)}", font=("Arial", 10, "bold")).pack(pady=3)
    tk.Label(edit, text=f"Cliente: {cliente}", font=("Arial", 11, "bold")).pack(pady=5)

    # Serviço
    tk.Label(edit, text="Serviço:").pack()
    servico_var = tk.StringVar(value=servico)
    for s in SERVICOS.keys():
        tk.Radiobutton(edit, text=s, variable=servico_var, value=s).pack(anchor="w")

    # Horário inicial
    tk.Label(edit, text="Novo horário inicial:").pack(pady=(10, 0))
    horario_var = tk.StringVar(value=inicio)
    combo_horario = ttk.Combobox(edit, textvariable=horario_var, values=HORARIOS, state="readonly")
    combo_horario.pack(pady=5)

    # Observações
    tk.Label(edit, text="Observações (opcional):").pack()
    obs_entry = tk.Entry(edit)
    obs_entry.insert(0, obs)
    obs_entry.pack(pady=5, fill=tk.X, padx=20)

    def salvar_edicao():
        novo_servico = servico_var.get()
        nova_obs = obs_entry.get().strip()
        novo_inicio = horario_var.get()

        nova_duracao = SERVICOS[novo_servico]
        blocos = nova_duracao // INTERVALO
        idx = HORARIOS.index(novo_inicio)

        if idx + blocos - 1 >= len(HORARIOS):
            messagebox.showerror("Erro", "Esse serviço não cabe até o fim do expediente.", parent=edit)
            return

        novos_blocos = HORARIOS[idx: idx + blocos]

        # checar disponibilidade (permitindo usar os próprios blocos antigos)
        dur_ant = slot.get("duracao", SERVICOS.get(servico, 30))
        idx_ant = HORARIOS.index(inicio)
        blocos_antigos = HORARIOS[idx_ant: idx_ant + (dur_ant // INTERVALO)]

        for h in novos_blocos:
            ocup = agenda[data_iso].get(h)
            if ocup is not None and h not in blocos_antigos:
                messagebox.showerror("Erro", "Um ou mais horários já estão ocupados.", parent=edit)
                return

        # liberar antigos
        for h in blocos_antigos:
            agenda[data_iso][h] = None

        # aplicar novos
        preco_novo = PRECO_SERVICOS.get(novo_servico, 0.0)
        for h in novos_blocos:
            agenda[data_iso][h] = {
                "cliente": cliente,
                "servico": novo_servico,
                "duracao": nova_duracao,
                "obs": nova_obs,
                "inicio": novo_inicio,
                "preco": preco_novo,
                "pago": pago_original,
                "extras": extras_orig,
                "pacote": pacote_flag,
                "pacote_nome": pacote_nome,
                "pacote_valor_mensal": pacote_valor,
            }

        salvar_agenda(agenda)

        # atualiza a tela principal para a data editada
        data_var.set(iso_para_br(data_iso))
        atualizar_campos_de_data()

        messagebox.showinfo("Sucesso", "Agendamento alterado!", parent=edit)
        edit.destroy()

    tk.Button(edit, text="💾 Salvar alterações", command=salvar_edicao).pack(pady=15)

def janela_editar_agendamento():
    """Abre uma tela para editar o agendamento selecionado (qualquer dia)."""
    # 1) Pega a data atual da tela (data original)
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    # 2) Verifica se algum horário foi selecionado na lista
    selecao = lista_horarios.curselection()
    if not selecao:
        messagebox.showinfo("Info", "Selecione um horário na lista para editar.")
        return

    # 3) Descobre qual horário foi clicado
    linha = lista_horarios.get(selecao[0])
    hora = linha.split(" - ")[0]

    # 4) Pega o slot desse horário na agenda
    slot = agenda.get(data_iso, {}).get(hora)
    if not slot:
        messagebox.showinfo("Info", "Esse horário está livre, não há o que editar.")
        return

    # Dados originais
    cliente = slot.get("cliente", "")
    servico = slot.get("servico", "")
    obs = slot.get("obs", "")
    inicio = slot.get("inicio", hora)
    duracao_original = slot.get("duracao", SERVICOS.get(servico, 30))
    data_original_iso = data_iso
    preco_original = slot.get("preco", PRECO_SERVICOS.get(servico, 0.0))
    pago_original = slot.get("pago", False)
    preco_original = slot.get("preco", PRECO_SERVICOS.get(servico, 0.0))
    extras_orig = slot.get("extras", [])
    pago_original = slot.get("pago", False)
    pacote_flag = slot.get("pacote", False)
    pacote_nome = slot.get("pacote_nome")
    pacote_valor = slot.get("pacote_valor_mensal", 0.0)

    # ---------------------------
    # JANELA DE EDIÇÃO
    # ---------------------------
    edit = tk.Toplevel(root)
    edit.title("Editar agendamento")
    edit.geometry("380x420")

    tk.Label(edit, text=f"Cliente: {cliente}", font=("Arial", 11, "bold")).pack(pady=5)

    # DATA DO AGENDAMENTO (COM BOTÃO PARA MUDAR)
    tk.Label(edit, text="Data do agendamento:").pack()
    data_destino_iso_var = tk.StringVar(value=data_original_iso)
    data_destino_br_var = tk.StringVar(value=iso_para_br(data_original_iso))
    label_data_dest = tk.Label(edit, textvariable=data_destino_br_var, font=("Arial", 10))
    label_data_dest.pack(pady=(0, 5))

    def escolher_nova_data():
        win_data = tk.Toplevel(edit)
        win_data.title("Selecionar nova data")
        win_data.geometry("280x280")

        cal = Calendar(
            win_data,
            selectmode="day",
            date_pattern="dd/mm/yyyy"
        )
        cal.pack(pady=10)

        def confirmar_data():
            data_escolhida_br = cal.get_date()  # dd/mm/yyyy
            data_escolhida_iso = str_data_para_iso(data_escolhida_br)
            if not data_escolhida_iso:
                messagebox.showerror("Erro", "Data inválida.", parent=win_data)
                return
            data_destino_iso_var.set(data_escolhida_iso)
            data_destino_br_var.set(data_escolhida_br)
            win_data.destroy()

        tk.Button(win_data, text="Confirmar", command=confirmar_data).pack(pady=10)

    tk.Button(edit, text="Mudar data", command=escolher_nova_data).pack(pady=(0, 10))

    # Serviço
    tk.Label(edit, text="Serviço:").pack()
    servico_var = tk.StringVar(value=servico)
    for s in SERVICOS.keys():
        tk.Radiobutton(edit, text=s, variable=servico_var, value=s).pack(anchor="w")

    # Horário inicial
    tk.Label(edit, text="Novo horário inicial:").pack(pady=(10, 0))
    horario_var = tk.StringVar(value=inicio)
    combo_horario = ttk.Combobox(
        edit,
        textvariable=horario_var,
        values=HORARIOS,
        state="readonly"
    )
    combo_horario.pack(pady=5)

    # Observações
    tk.Label(edit, text="Observações (opcional):").pack()
    obs_entry = tk.Entry(edit)
    obs_entry.insert(0, obs)
    obs_entry.pack(pady=5, fill=tk.X, padx=20)

    # BOTÃO SALVAR ALTERAÇÕES
    def salvar_edicao():
        novo_servico = servico_var.get()
        nova_obs = obs_entry.get().strip()
        novo_inicio = horario_var.get()
        nova_data_iso = data_destino_iso_var.get()

        if novo_inicio not in HORARIOS:
            messagebox.showerror("Erro", "Horário inválido.", parent=edit)
            return

        if not nova_data_iso:
            messagebox.showerror("Erro", "Data de destino inválida.", parent=edit)
            return

        garantir_dia_na_agenda(agenda, nova_data_iso)

        nova_duracao = SERVICOS[novo_servico]
        blocos = nova_duracao // INTERVALO
        indice = HORARIOS.index(novo_inicio)

        

        novos_blocos = HORARIOS[indice: indice + blocos]

        # Verificar conflitos nos blocos da nova data
        conflito_outro = None
        for h in novos_blocos:
            slot_h = agenda[nova_data_iso].get(h)
            if slot_h is None:
                continue

            # Se for o mesmo agendamento (mesma data original e mesmos blocos), ignorar
            if (nova_data_iso == data_original_iso and
                slot_h.get("cliente") == cliente and
                slot_h.get("inicio") == inicio):
                continue

            if conflito_outro is None:
                conflito_outro = slot_h
            else:
                # Mais de um agendamento diferente nesse intervalo -> conflito não trocável
                if (slot_h.get("cliente") != conflito_outro.get("cliente") or
                    slot_h.get("inicio")  != conflito_outro.get("inicio")  or
                    slot_h.get("duracao") != conflito_outro.get("duracao")):
                    messagebox.showerror(
                        "Erro",
                        "Um ou mais horários desse período já estão ocupados!",
                        parent=edit
                    )
                    return

        # Se não há conflito, apenas mover/editar normalmente
        if conflito_outro is None:
            # Liberar blocos antigos do agendamento original
            blocos_antigos = HORARIOS[
                HORARIOS.index(inicio) : HORARIOS.index(inicio) + (duracao_original // INTERVALO)
            ]
            for h in blocos_antigos:
                agenda[data_original_iso][h] = None

            # Aplicar novos blocos na nova data
            preco_novo = PRECO_SERVICOS.get(novo_servico, 0.0)
            for h in novos_blocos:
                agenda[nova_data_iso][h] = {
                    "cliente": cliente,
                    "servico": novo_servico,
                    "duracao": nova_duracao,
                    "obs": nova_obs,
                    "inicio": novo_inicio,
                    "preco": preco_novo,
                    "pago": pago_original,
                    "extras": extras_orig,
                    "pacote": pacote_flag,
                    "pacote_nome": pacote_nome,
                    "pacote_valor_mensal": pacote_valor,
                }

            salvar_agenda(agenda)
            atualizar_lista_agenda()
            messagebox.showinfo("Sucesso", "Agendamento alterado!", parent=edit)
            edit.destroy()
            return

        # Há um único agendamento de outra pessoa nesse intervalo: tentar TROCA
        outro_cliente = conflito_outro.get("cliente", "Outro cliente")
        outro_servico = conflito_outro.get("servico")
        outro_duracao = conflito_outro.get("duracao", 30)
        outro_inicio = conflito_outro.get("inicio", novo_inicio)
        outro_preco = conflito_outro.get("preco", PRECO_SERVICOS.get(outro_servico, 0.0))
        outro_pago = conflito_outro.get("pago", False)
        outro_extras = conflito_outro.get("extras", [])

        # Blocos atuais do "outro" na nova data
        outro_blocos_nova_data = HORARIOS[
            HORARIOS.index(outro_inicio) : HORARIOS.index(outro_inicio) + (outro_duracao // INTERVALO)
        ]

        # Blocos livres na data original para encaixar o outro cliente
        outro_blocos_na_data_original = HORARIOS[
            HORARIOS.index(inicio) : HORARIOS.index(inicio) + (outro_duracao // INTERVALO)
        ]

        # Verifica se na data original só existe o nosso agendamento nesses blocos,
        # permitindo que o outro venha pra cá.
        for h in outro_blocos_na_data_original:
            slot_old = agenda[data_original_iso].get(h)
            if slot_old is not None and not (
                slot_old.get("cliente") == cliente and
                slot_old.get("inicio") == inicio
            ):
                messagebox.showerror(
                    "Erro",
                    "O horário de origem não comporta uma troca com esse outro agendamento.",
                    parent=edit
                )
                return

        # Pergunta se o usuário quer trocar
        resp = messagebox.askyesno(
            "Trocar horários?",
            f"Já existe um agendamento de {outro_cliente} nesse horário.\n\n"
            f"Deseja TROCAR os horários entre {cliente} e {outro_cliente}?",
            parent=edit
        )

        if not resp:
            return

        # 1) Liberar blocos antigos do nosso agendamento na data original
        blocos_nossos_originais = HORARIOS[
            HORARIOS.index(inicio) : HORARIOS.index(inicio) + (duracao_original // INTERVALO)
        ]
        for h in blocos_nossos_originais:
            agenda[data_original_iso][h] = None

        # 2) Liberar blocos do outro cliente na data nova
        for h in outro_blocos_nova_data:
            agenda[nova_data_iso][h] = None

        # 3) Colocar nosso cliente na nova data/horário
        preco_novo = PRECO_SERVICOS.get(novo_servico, 0.0)
        for h in novos_blocos:
                agenda[nova_data_iso][h] = {
                    "cliente": cliente,
                    "servico": novo_servico,
                    "duracao": nova_duracao,
                    "obs": nova_obs,
                    "inicio": novo_inicio,
                    "preco": preco_novo,
                    "pago": pago_original,
                    "extras": extras_orig,
                    "pacote": pacote_flag,
                    "pacote_nome": pacote_nome,
                    "pacote_valor_mensal": pacote_valor,
                    }

        # 4) Colocar o outro cliente na data original, no horário antigo do nosso
        for h in outro_blocos_na_data_original:
            agenda[data_original_iso][h] = {
                "cliente": outro_cliente,
                "servico": outro_servico,
                "duracao": outro_duracao,
                "obs": conflito_outro.get("obs", ""),
                "inicio": inicio,  # ele passa a começar onde o nosso começava
                "preco": outro_preco,
                "pago": outro_pago,
            }

        salvar_agenda(agenda)
        atualizar_lista_agenda()
        messagebox.showinfo("Sucesso", "Agendamentos trocados com sucesso!", parent=edit)
        edit.destroy()

    tk.Button(edit, text="💾 Salvar alterações", command=salvar_edicao).pack(pady=15)

# ----- DETALHES DO AGENDAMENTO (DUPLO CLIQUE) -----

def ver_detalhes_agendamento(event):
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        return

    selecao = lista_horarios.curselection()
    if not selecao:
        return

    linha = lista_horarios.get(selecao[0])
    hora = linha.split(" - ")[0]

    slot = agenda.get(data_iso, {}).get(hora)
    if not slot:
        return

    cliente = slot.get("cliente", "")
    servico = slot.get("servico", "")
    inicio = slot.get("inicio", hora)
    duracao = slot.get("duracao", 0)
    obs = slot.get("obs", "")
    tel = slot.get("telefone", "")

    fim_idx = HORARIOS.index(inicio) + (duracao // INTERVALO) - 1
    if 0 <= fim_idx < len(HORARIOS):
        hora_fim = HORARIOS[fim_idx]
    else:
        hora_fim = "?"

    msg = (
        f"Cliente: {cliente}\n"
        f"Serviço: {servico}\n"
        f"Horário: {inicio} - {hora_fim}\n"
        f"Duração: {duracao} minutos"
    )
    if tel:
        msg += f"\nTelefone: {tel}"
    if obs:
        msg += f"\nObservações: {obs}"

    win = tk.Toplevel(root)
    win.title("Detalhes do agendamento")
    win.geometry("380x240")

    tk.Label(win, text=msg, justify="left").pack(padx=10, pady=10, anchor="w")

    btns = tk.Frame(win)
    btns.pack(pady=10)

    tk.Button(
        btns,
        text="📲 WhatsApp confirmar",
        command=lambda: whatsapp_confirmar_agendamento(cliente, data_iso, inicio)
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btns,
        text="Fechar",
        command=win.destroy
    ).pack(side=tk.LEFT, padx=5)

lista_horarios.bind("<Double-Button-1>", ver_detalhes_agendamento)

# ----- JANELA DE CLIENTES / ANIVERSÁRIOS -----

def abrir_aniversarios():
    win = tk.Toplevel(root)
    win.title("Aniversários de clientes")
    win.geometry("600x400")

    tk.Label(win, text="Clientes cadastrados", font=("Arial", 12, "bold")).pack(pady=5)

    frame_lista_cli = tk.Frame(win)
    frame_lista_cli.pack(fill=tk.BOTH, expand=True, padx=10)

    lista_cli = tk.Listbox(frame_lista_cli, height=8, width=80)
    lista_cli.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll_cli = tk.Scrollbar(frame_lista_cli, command=lista_cli.yview)
    scroll_cli.pack(side=tk.RIGHT, fill=tk.Y)
    lista_cli.config(yscrollcommand=scroll_cli.set)

    def atualizar_lista_clientes():
        lista_cli.delete(0, tk.END)
        for nome, info in clientes.items():
            nasc = info.get("nasc", "")
            tel = info.get("tel", "")
            linha = f"{nome} - Nasc: {nasc}"
            if tel:
                linha += f" - Tel: {tel}"
            lista_cli.insert(tk.END, linha)

    frame_form = tk.Frame(win)
    frame_form.pack(fill=tk.X, padx=10, pady=10)

    tk.Label(frame_form, text="Nome:").grid(row=0, column=0, sticky="e")
    entry_nome = tk.Entry(frame_form, width=30)
    entry_nome.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_form, text="Aniversário (DD/MM):").grid(row=1, column=0, sticky="e")
    entry_nasc = tk.Entry(frame_form, width=10)
    entry_nasc.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_form, text="Telefone (opcional):").grid(row=2, column=0, sticky="e")
    entry_tel = tk.Entry(frame_form, width=20)
    entry_tel.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    def on_lista_duplo_click(event):
        idxs = lista_cli.curselection()
        if not idxs:
            return
        linha = lista_cli.get(idxs[0])
        nome = linha.split(" - ")[0]
        info = clientes.get(nome, {})
        entry_nome.delete(0, tk.END)
        entry_nome.insert(0, nome)
        entry_nasc.delete(0, tk.END)
        entry_nasc.insert(0, info.get("nasc", ""))
        entry_tel.delete(0, tk.END)
        entry_tel.insert(0, info.get("tel", ""))

    lista_cli.bind("<Double-Button-1>", on_lista_duplo_click)

    def salvar_cliente_cmd():
        nome = entry_nome.get().strip()
        nasc = entry_nasc.get().strip()
        tel = entry_tel.get().strip()

        if not nome or not nasc:
            messagebox.showerror(
                "Erro",
                "Preencha pelo menos nome e aniversário (DD/MM).",
                parent=win,
            )
            return

        # valida aniversário DD/MM usando ano fictício
        try:
            datetime.strptime(nasc + "/2000", "%d/%m/%Y")
        except ValueError:
            messagebox.showerror(
                "Erro",
                "Data de aniversário inválida. Use o formato DD/MM.",
                parent=win,
            )
            return

        clientes[nome] = {"nasc": nasc, "tel": tel}
        salvar_clientes(clientes)
        atualizar_lista_clientes()
        atualizar_aviso_aniversario()
        messagebox.showinfo("Sucesso", "Cliente salvo com sucesso!", parent=win)

        entry_nome.delete(0, tk.END)
        entry_nasc.delete(0, tk.END)
        entry_tel.delete(0, tk.END)

    tk.Button(win, text="💾 Salvar cliente", command=salvar_cliente_cmd).pack(pady=5)

    atualizar_lista_clientes()



# ----- JANELA DE CAIXA -----

def registrar_venda_avulsa():
    """Registra venda de produto sem precisar de agendamento."""
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    win = tk.Toplevel(root)
    win.title(f"Venda de produto - {data_str}")
    win.geometry("350x260")

    tk.Label(win, text=f"Data: {data_str}", font=("Arial", 10, "bold")).pack(pady=5)

    # Cliente (opcional)
    tk.Label(win, text="Cliente (opcional):").pack()
    cliente_var = tk.StringVar()
    entry_cliente = tk.Entry(win, textvariable=cliente_var)
    entry_cliente.pack(pady=5, fill=tk.X, padx=20)

    # Produto
    tk.Label(win, text="Produto:").pack()
    itens_venda = sorted(PRECO_SERVICOS.keys())
    prod_var = tk.StringVar()
    combo_prod = ttk.Combobox(win, textvariable=prod_var, values=itens_venda, state="readonly")
    combo_prod.pack(pady=5, fill=tk.X, padx=20)

    # Valor
    tk.Label(win, text="Valor (R$):").pack()
    valor_var = tk.StringVar()
    entry_valor = tk.Entry(win, textvariable=valor_var)
    entry_valor.pack(pady=5, fill=tk.X, padx=20)

    def on_escolher_produto(event=None):
        nome = prod_var.get()
        if nome:
            valor_padrao = PRECO_SERVICOS.get(nome, 0.0)
            valor_var.set(f"{valor_padrao:.2f}")

    combo_prod.bind("<<ComboboxSelected>>", on_escolher_produto)

    # Pago agora?
    pago_var = tk.BooleanVar(value=True)
    chk_pago = tk.Checkbutton(win, text="Pago agora", variable=pago_var)
    chk_pago.pack(pady=5)

    def confirmar_venda():
        produto = prod_var.get().strip()
        if not produto:
            messagebox.showerror("Erro", "Escolha um produto.", parent=win)
            return
        try:
            valor = float(valor_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Valor inválido.", parent=win)
            return

        cliente = cliente_var.get().strip()
        venda = {
            "cliente": cliente if cliente else "",
            "produto": produto,
            "valor": valor,
            "pago": bool(pago_var.get()),
                }

        vendas = agenda[data_iso].setdefault("_vendas_avulsas", [])
        vendas.append(venda)

        salvar_agenda(agenda)
        messagebox.showinfo("Sucesso", "Venda registrada com sucesso!", parent=win)
        win.destroy()

    tk.Button(win, text="✅ Registrar venda", command=confirmar_venda).pack(pady=10)

def abrir_caixa_dia():
    """Mostra os atendimentos e vendas do dia com valores e status de pagamento."""
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    win = tk.Toplevel(root)
    win.title(f"Caixa do dia - {data_str}")
    win.geometry("700x420")

    tk.Label(
        win,
        text=f"Caixa do dia {data_str}",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    colunas = ("hora", "cliente", "descricao", "valor_servico", "extras", "total", "status")
    tree = ttk.Treeview(win, columns=colunas, show="headings", height=13)
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    tree.heading("hora", text="Hora")
    tree.heading("cliente", text="Cliente")
    tree.heading("descricao", text="Serviço / Produto")
    tree.heading("valor_servico", text="Serviço/Prod (R$)")
    tree.heading("extras", text="Extras (R$)")
    tree.heading("total", text="Total (R$)")
    tree.heading("status", text="Status")

    tree.column("hora", width=60, anchor="center")
    tree.column("cliente", width=150)
    tree.column("descricao", width=170)
    tree.column("valor_servico", width=100, anchor="e")
    tree.column("extras", width=90, anchor="e")
    tree.column("total", width=90, anchor="e")
    tree.column("status", width=80, anchor="center")

    totais_var = tk.StringVar()
    label_totais = tk.Label(win, textvariable=totais_var, font=("Arial", 10, "bold"))
    label_totais.pack(pady=(0, 5))

    # lista em memória; cada item tem 'tipo' e 'iid' da tree
    atendimentos = []

    def atualizar_lista_caixa():
        atendimentos.clear()
        tree.delete(*tree.get_children())

        total_pago = 0.0
        total_pendente = 0.0

        # 1) Agendamentos
        for h in HORARIOS:
            slot = agenda[data_iso].get(h)
            if not slot:
                continue
            if slot.get("inicio") != h:
                continue  # só o bloco inicial

            cliente = slot.get("cliente", "")
            servico = slot.get("servico", "")
            preco_serv = float(slot.get("preco", PRECO_SERVICOS.get(servico, 0.0)))
            extras_list = slot.get("extras", [])
            extras_total = sum(float(e.get("valor", 0.0)) for e in extras_list)
            total = preco_serv + extras_total
            pago = bool(slot.get("pago", False))

            status_txt = "Pago" if pago else "Pendente"
            if pago:
                total_pago += total
            else:
                total_pendente += total

            iid = tree.insert(
                "",
                tk.END,
                values=(
                    h,
                    cliente,
                    servico,
                    f"{preco_serv:.2f}",
                    f"{extras_total:.2f}",
                    f"{total:.2f}",
                    status_txt,
                )
            )

            atendimentos.append({
                "tipo": "agendamento",
                "iid": iid,
                "hora": h,
                "pago": pago,
            })

        # 2) Vendas avulsas
        vendas_avulsas = agenda[data_iso].get("_vendas_avulsas", [])
        for idx, v in enumerate(vendas_avulsas):
            cliente = v.get("cliente", "").strip() or "Venda avulsa"
            produto = v.get("produto", "")
            valor = float(v.get("valor", 0.0))
            pago = bool(v.get("pago", True))
            extras_total = 0.0
            total = valor

            status_txt = "Pago" if pago else "Pendente"
            if pago:
                total_pago += total
            else:
                total_pendente += total

            iid = tree.insert(
                "",
                tk.END,
                values=(
                    "--",                    # sem horário específico
                    cliente,
                    f"(Prod.) {produto}",
                    f"{valor:.2f}",
                    f"{extras_total:.2f}",
                    f"{total:.2f}",
                    status_txt,
                )
            )

            atendimentos.append({
                "tipo": "venda",
                "iid": iid,
                "indice": idx,
                "pago": pago,
            })

        totais_var.set(
            f"Total recebido: R$ {total_pago:.2f}   |   "
            f"Total pendente: R$ {total_pendente:.2f}"
        )

    def encontrar_atendimento_por_iid(iid):
        for a in atendimentos:
            if a["iid"] == iid:
                return a
        return None

    def marcar_como_pago():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Selecione um item para marcar como pago.", parent=win)
            return

        item = sel[0]
        at = encontrar_atendimento_por_iid(item)
        if not at:
            return

        if at["pago"]:
            messagebox.showinfo("Info", "Esse item já está marcado como pago.", parent=win)
            return

        if at["tipo"] == "agendamento":
            hora_inicio = at["hora"]
            slot = agenda[data_iso].get(hora_inicio)
            if not slot:
                return

            dur = slot.get("duracao", 30)
            blocos = dur // INTERVALO
            idx_inicio = HORARIOS.index(hora_inicio)
            blocos_h = HORARIOS[idx_inicio: idx_inicio + blocos]

            for h in blocos_h:
                if agenda[data_iso].get(h):
                    agenda[data_iso][h]["pago"] = True

        elif at["tipo"] == "venda":
            vendas_avulsas = agenda[data_iso].get("_vendas_avulsas", [])
            idx = at["indice"]
            if 0 <= idx < len(vendas_avulsas):
                vendas_avulsas[idx]["pago"] = True

        salvar_agenda(agenda)
        atualizar_lista_caixa()
        messagebox.showinfo("Sucesso", "Item marcado como pago.", parent=win)

    def adicionar_produto():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Selecione um atendimento para adicionar produto.", parent=win)
            return

        item = sel[0]
        at = encontrar_atendimento_por_iid(item)
        if not at:
            return

        if at["tipo"] != "agendamento":
            messagebox.showinfo("Info", "Produtos extras só podem ser adicionados em agendamentos.", parent=win)
            return

        hora_inicio = at["hora"]
        slot = agenda[data_iso].get(hora_inicio)
        if not slot:
            return

        wprod = tk.Toplevel(win)
        wprod.title("Adicionar produto ao atendimento")
        wprod.geometry("320x190")

        tk.Label(wprod, text="Produto:", font=("Arial", 10)).pack(pady=(10, 0))
        itens_venda = sorted(PRECO_SERVICOS.keys())
        prod_var = tk.StringVar()
        combo_prod = ttk.Combobox(wprod, textvariable=prod_var, values=itens_venda, state="readonly")
        combo_prod.pack(pady=5, fill=tk.X, padx=20)

        tk.Label(wprod, text="Valor (R$):").pack()
        valor_var = tk.StringVar()
        entry_valor = tk.Entry(wprod, textvariable=valor_var)
        entry_valor.pack(pady=5, fill=tk.X, padx=20)

        def on_escolher_prod(event=None):
            nome = prod_var.get()
            if nome:
                valor_padrao = PRECO_SERVICOS.get(nome, 0.0)
                valor_var.set(f"{valor_padrao:.2f}")

        combo_prod.bind("<<ComboboxSelected>>", on_escolher_prod)

        def confirmar_produto():
            nome = prod_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "Escolha um produto.", parent=wprod)
                return
            try:
                valor = float(valor_var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido.", parent=wprod)
                return

            dur = slot.get("duracao", 30)
            blocos = dur // INTERVALO
            idx_inicio = HORARIOS.index(hora_inicio)
            blocos_h = HORARIOS[idx_inicio: idx_inicio + blocos]

            for h in blocos_h:
                s = agenda[data_iso].get(h)
                if not s:
                    continue
                lista_extras = s.get("extras", [])
                lista_extras.append({"nome": nome, "valor": valor})
                s["extras"] = lista_extras

            salvar_agenda(agenda)
            atualizar_lista_caixa()
            wprod.destroy()

        tk.Button(wprod, text="✅ Adicionar", command=confirmar_produto).pack(pady=10)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)

    tk.Button(
        btn_frame,
        text="✅ Marcar como pago",
        command=marcar_como_pago
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame,
        text="➕ Produto em atendimento",
        command=adicionar_produto
    ).pack(side=tk.LEFT, padx=5)

    atualizar_lista_caixa()

# ------ JANELA DE RELATORIOS ------
def calcular_resumo_datas(lista_datas_iso):
    """
    Recebe uma lista de datas (ISO) e calcula:
    - total de atendimentos
    - total em serviços
    - total em produtos (extras + vendas avulsas)
    - total recebido / pendente
    - contagem de serviços e produtos
    """
    total_atendimentos = 0

    total_servicos = 0.0      # só corte/barba/etc
    total_produtos = 0.0      # extras + vendas avulsas
    total_pago = 0.0
    total_pendente = 0.0

    contagem_servicos = {}
    contagem_produtos = {}

    for data_iso in lista_datas_iso:
        dia = agenda.get(data_iso, {})

        # 1) Atendimentos (agendamentos)
        for h in HORARIOS:
            slot = dia.get(h)
            if not slot:
                continue
            if slot.get("inicio") != h:
                continue  # só o bloco inicial

            servico = slot.get("servico", "")
            preco_serv = float(slot.get("preco", PRECO_SERVICOS.get(servico, 0.0)))
            extras_list = slot.get("extras", [])
            extras_total = sum(float(e.get("valor", 0.0)) for e in extras_list)
            total = preco_serv + extras_total
            pago = bool(slot.get("pago", False))

            total_atendimentos += 1
            total_servicos += preco_serv
            total_produtos += extras_total

            contagem_servicos[servico] = contagem_servicos.get(servico, 0) + 1
            for e in extras_list:
                nome_prod = e.get("nome", "Produto")
                contagem_produtos[nome_prod] = contagem_produtos.get(nome_prod, 0) + 1

            if pago:
                total_pago += total
            else:
                total_pendente += total

        # 2) Vendas avulsas
        vendas_avulsas = dia.get("_vendas_avulsas", [])
        for v in vendas_avulsas:
            produto = v.get("produto", "Produto")
            valor = float(v.get("valor", 0.0))
            pago = bool(v.get("pago", True))

            total_produtos += valor
            contagem_produtos[produto] = contagem_produtos.get(produto, 0) + 1

            if pago:
                total_pago += valor
            else:
                total_pendente += valor

    total_geral = total_pago + total_pendente

    return {
        "total_atendimentos": total_atendimentos,
        "total_servicos": total_servicos,
        "total_produtos": total_produtos,
        "total_pago": total_pago,
        "total_pendente": total_pendente,
        "total_geral": total_geral,
        "contagem_servicos": contagem_servicos,
        "contagem_produtos": contagem_produtos,
    }

def abrir_relatorio_dia():
    """Relatório do dia atual mostrado na tela."""
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    if data_iso not in agenda:
        messagebox.showinfo("Info", "Não há dados para essa data.")
        return

    resumo = calcular_resumo_datas([data_iso])

    win = tk.Toplevel(root)
    win.title(f"Relatório diário - {data_str}")
    win.geometry("480x420")

    tk.Label(
        win,
        text=f"Relatório do dia {data_str}",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    txt = []

    txt.append(f"Atendimentos: {resumo['total_atendimentos']}")
    txt.append(f"Total em serviços: R$ {resumo['total_servicos']:.2f}")
    txt.append(f"Total em produtos: R$ {resumo['total_produtos']:.2f}")
    txt.append("")
    txt.append(f"Total RECEBIDO: R$ {resumo['total_pago']:.2f}")
    txt.append(f"Total PENDENTE: R$ {resumo['total_pendente']:.2f}")
    txt.append(f"Total GERAL (pago + pendente): R$ {resumo['total_geral']:.2f}")
    txt.append("")
    txt.append("Serviços mais realizados:")

    # top 5 serviços
    servicos = sorted(
        resumo["contagem_servicos"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    if servicos:
        for nome, qtd in servicos[:5]:
            txt.append(f"  - {nome}: {qtd}")
    else:
        txt.append("  (nenhum serviço)")

    txt.append("")
    txt.append("Produtos mais vendidos (extras + avulsos):")

    produtos = sorted(
        resumo["contagem_produtos"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    if produtos:
        for nome, qtd in produtos[:5]:
            txt.append(f"  - {nome}: {qtd}")
    else:
        txt.append("  (nenhum produto)")

    texto_final = "\n".join(txt)

    lbl = tk.Label(
        win,
        text=texto_final,
        justify="left",
        font=("Arial", 10)
    )
    lbl.pack(padx=10, pady=10, anchor="w")

def abrir_relatorio_mes():
    """Abre uma janelinha para escolher o mês e gerar relatório mensal."""
    sel = tk.Toplevel(root)
    sel.title("Escolher mês para relatório")
    sel.geometry("280x300")

    tk.Label(sel, text="Escolha uma data do mês desejado:", font=("Arial", 10)).pack(pady=5)

    cal = Calendar(
        sel,
        selectmode="day",
        date_pattern="dd/mm/yyyy"
    )
    cal.pack(pady=10)

    def confirmar():
        data_br = cal.get_date()  # dd/mm/yyyy
        try:
            dt = datetime.strptime(data_br, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Erro", "Data inválida.", parent=sel)
            return

        mes = dt.month
        ano = dt.year

        # pega todas as datas da agenda que sejam desse mês/ano
        datas_mes = []
        for data_iso in agenda.keys():
            try:
                d = datetime.strptime(data_iso, "%Y-%m-%d")
            except ValueError:
                continue
            if d.year == ano and d.month == mes:
                datas_mes.append(data_iso)

        if not datas_mes:
            messagebox.showinfo(
                "Info",
                f"Não há registros para {mes:02d}/{ano}.",
                parent=sel
            )
            return

        sel.destroy()
        mostrar_relatorio_mes(datas_mes, mes, ano)

    tk.Button(sel, text="Gerar relatório", command=confirmar).pack(pady=10)


def mostrar_relatorio_mes(datas_mes, mes, ano):
    """Mostra o relatório consolidado de um mês."""
    resumo = calcular_resumo_datas(datas_mes)

    win = tk.Toplevel(root)
    win.title(f"Relatório mensal - {mes:02d}/{ano}")
    win.geometry("520x440")

    tk.Label(
        win,
        text=f"Relatório de {mes:02d}/{ano}",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    txt = []

    txt.append(f"Dias com movimento: {len(datas_mes)}")
    txt.append(f"Atendimentos no mês: {resumo['total_atendimentos']}")
    txt.append(f"Total em serviços: R$ {resumo['total_servicos']:.2f}")
    txt.append(f"Total em produtos: R$ {resumo['total_produtos']:.2f}")
    txt.append("")
    txt.append(f"Total RECEBIDO: R$ {resumo['total_pago']:.2f}")
    txt.append(f"Total PENDENTE: R$ {resumo['total_pendente']:.2f}")
    txt.append(f"Total GERAL (pago + pendente): R$ {resumo['total_geral']:.2f}")
    txt.append("")
    txt.append("Serviços mais realizados no mês:")

    servicos = sorted(
        resumo["contagem_servicos"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    if servicos:
        for nome, qtd in servicos[:10]:
            txt.append(f"  - {nome}: {qtd}")
    else:
        txt.append("  (nenhum serviço)")

    txt.append("")
    txt.append("Produtos mais vendidos no mês:")

    produtos = sorted(
        resumo["contagem_produtos"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    if produtos:
        for nome, qtd in produtos[:10]:
            txt.append(f"  - {nome}: {qtd}")
    else:
        txt.append("  (nenhum produto)")

    texto_final = "\n".join(txt)

    lbl = tk.Label(
        win,
        text=texto_final,
        justify="left",
        font=("Arial", 10)
    )
    lbl.pack(padx=10, pady=10, anchor="w")

# ------ JANELA DE CLIENTES FIXOS DE PACOTE ------

def janela_pacote_cliente():
    """Cria agendamentos recorrentes de pacote (cliente fixo) por várias semanas."""
    if not clientes:
        messagebox.showinfo("Info", "Nenhum cliente cadastrado ainda.")
        return

    win = tk.Toplevel(root)
    win.title("Cliente fixo / Pacote")
    win.geometry("420x440")

    tk.Label(win, text="Configurar cliente fixo (pacote)", font=("Arial", 12, "bold")).pack(pady=5)

    # -------------------------
    # DADOS BÁSICOS DO CLIENTE
    # -------------------------
    frame_cli = tk.Frame(win)
    frame_cli.pack(fill=tk.X, padx=10, pady=5)

    tk.Label(frame_cli, text="Cliente:").grid(row=0, column=0, sticky="e")
    nomes_clientes = sorted(clientes.keys())
    cli_var = tk.StringVar()
    combo_cli = ttk.Combobox(frame_cli, textvariable=cli_var, values=nomes_clientes, state="readonly")
    combo_cli.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_cli, text="Dia da semana:").grid(row=1, column=0, sticky="e")
    dia_var = tk.StringVar(value="Segunda-feira")
    combo_dia = ttk.Combobox(frame_cli, textvariable=dia_var, values=DIAS_SEMANA, state="readonly")
    combo_dia.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_cli, text="Horário:").grid(row=2, column=0, sticky="e")
    hora_var = tk.StringVar(value=HORARIOS[0])
    combo_hora = ttk.Combobox(frame_cli, textvariable=hora_var, values=HORARIOS, state="readonly")
    combo_hora.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_cli, text="Data inicial (DD/MM/AAAA):").grid(row=3, column=0, sticky="e")
    data_ini_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
    entry_data_ini = tk.Entry(frame_cli, textvariable=data_ini_var, width=12)
    entry_data_ini.grid(row=3, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_cli, text="Número de semanas:").grid(row=4, column=0, sticky="e")
    semanas_var = tk.StringVar(value="52")
    entry_semanas = tk.Entry(frame_cli, textvariable=semanas_var, width=6)
    entry_semanas.grid(row=4, column=1, padx=5, pady=2, sticky="w")

    # -------------------------
    # SERVIÇOS ALTERNADOS
    # -------------------------
    frame_serv = tk.Frame(win)
    frame_serv.pack(fill=tk.X, padx=10, pady=10)

    servicos_lista = list(SERVICOS.keys())

    tk.Label(frame_serv, text="Semana ímpar:").grid(row=0, column=0, sticky="e")
    serv_impar_var = tk.StringVar(value="Barba")
    combo_impar = ttk.Combobox(frame_serv, textvariable=serv_impar_var, values=servicos_lista, state="readonly")
    combo_impar.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_serv, text="Semana par:").grid(row=1, column=0, sticky="e")
    serv_par_var = tk.StringVar(value="Cabelo e Barba")
    combo_par = ttk.Combobox(frame_serv, textvariable=serv_par_var, values=servicos_lista, state="readonly")
    combo_par.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    # -------------------------
    # DADOS DO PACOTE
    # -------------------------
    frame_pac = tk.Frame(win)
    frame_pac.pack(fill=tk.X, padx=10, pady=10)

    tk.Label(frame_pac, text="Nome do pacote:").grid(row=0, column=0, sticky="e")
    pacote_nome_var = tk.StringVar(value="Pacote Mensal 170")
    entry_pacote_nome = tk.Entry(frame_pac, textvariable=pacote_nome_var, width=22)
    entry_pacote_nome.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_pac, text="Valor mensal (R$):").grid(row=1, column=0, sticky="e")
    pacote_valor_var = tk.StringVar(value="170.00")
    entry_pacote_valor = tk.Entry(frame_pac, textvariable=pacote_valor_var, width=10)
    entry_pacote_valor.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_pac, text="Obs (opcional):").grid(row=2, column=0, sticky="e")
    obs_var = tk.StringVar(value="Cliente fixo - pacote")
    entry_obs = tk.Entry(frame_pac, textvariable=obs_var, width=25)
    entry_obs.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    # -------------------------
    # FUNÇÃO INTERNA: ESCOLHER O QUE FAZER NO FERIADO (MODO DELUXE)
    # -------------------------
    def escolher_acao_feriado(dt_local, nome_feriado, nome_cliente):
        """
        Abre uma janelinha perguntando:
        - Dia anterior
        - Próximo dia útil (simplesmente +1 dia)
        - Pular essa semana
        Retorna (acao, nova_data_datetime)
        """
        resultado = {"acao": "pular", "data": dt_local}

        w = tk.Toplevel(win)
        w.title("Data cai em feriado")
        w.geometry("380x200")
        w.grab_set()  # trava foco nessa janela

        data_br = dt_local.strftime("%d/%m/%Y")

        mensagem = (
            f"{nome_cliente}\n"
            f"A data planejada {data_br} cai em feriado:\n"
            f"{nome_feriado}\n\n"
            f"O que você deseja fazer para ESSA semana?"
        )

        tk.Label(w, text=mensagem, justify="left").pack(pady=10, padx=10)

        btn_frame = tk.Frame(w)
        btn_frame.pack(pady=5)

        def escolher(acao):
            if acao == "anterior":
                resultado["acao"] = "anterior"
                resultado["data"] = dt_local - timedelta(days=1)
            elif acao == "proximo":
                resultado["acao"] = "proximo"
                resultado["data"] = dt_local + timedelta(days=1)
            elif acao == "pular":
                resultado["acao"] = "pular"
                resultado["data"] = dt_local
            w.destroy()

        tk.Button(btn_frame, text="⬅️ Dia anterior", command=lambda: escolher("anterior")).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="➡️ Próximo dia", command=lambda: escolher("proximo")).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="⏭ Pular semana", command=lambda: escolher("pular")).grid(row=0, column=2, padx=5)

        # espera a janela fechar
        win.wait_window(w)
        return resultado["acao"], resultado["data"]

    # -------------------------
    # BOTÃO PRINCIPAL: CRIAR PACOTE
    # -------------------------
    def criar_pacote():
        nome_cli = cli_var.get().strip()
        if not nome_cli:
            messagebox.showerror("Erro", "Selecione um cliente.", parent=win)
            return

        dia_semana_str = dia_var.get()
        if dia_semana_str not in DIAS_SEMANA:
            messagebox.showerror("Erro", "Dia da semana inválido.", parent=win)
            return
        alvo_weekday = DIAS_SEMANA.index(dia_semana_str)  # 0=segunda

        hora_ini = hora_var.get()
        if hora_ini not in HORARIOS:
            messagebox.showerror("Erro", "Horário inválido.", parent=win)
            return

        serv_impar = serv_impar_var.get()
        serv_par = serv_par_var.get()
        if serv_impar not in SERVICOS or serv_par not in SERVICOS:
            messagebox.showerror("Erro", "Serviços inválidos.", parent=win)
            return

        try:
            semanas = int(semanas_var.get())
            if semanas <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Número de semanas inválido.", parent=win)
            return

        try:
            dt_ini = datetime.strptime(data_ini_var.get().strip(), "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Erro", "Data inicial inválida.", parent=win)
            return

        # Ajusta dt_ini para o primeiro dia desejado (da semana)
        delta = (alvo_weekday - dt_ini.weekday()) % 7
        dt = dt_ini + timedelta(days=delta)

        try:
            val_mensal = float(pacote_valor_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Valor mensal inválido.", parent=win)
            return

        obs = obs_var.get().strip()
        pacote_nome = pacote_nome_var.get().strip() or "Pacote"

        criados = 0
        conflitos = 0
        ajustados_por_feriado = 0
        pulados_por_feriado = 0

        for semana_idx in range(semanas):
            # data "base" daquela semana
            dt_base = dt
            data_iso_base = dt_base.strftime("%Y-%m-%d")

            # checa feriado
            eh_fer, nome_fer = eh_feriado_data_iso(data_iso_base)
            dt_slot = dt_base

            if eh_fer:
                acao, dt_escolhida = escolher_acao_feriado(dt_base, nome_fer or "Feriado", nome_cli)
                if acao == "pular":
                    pulados_por_feriado += 1
                    dt += timedelta(days=7)
                    continue
                else:
                    ajustados_por_feriado += 1
                    dt_slot = dt_escolhida

            data_iso_slot = dt_slot.strftime("%Y-%m-%d")
            garantir_dia_na_agenda(agenda, data_iso_slot)

            # escolhe serviço alternando (0 = 1ª semana = ímpar "humana")
            servico = serv_impar if (semana_idx % 2 == 0) else serv_par
            duracao = SERVICOS[servico]
            blocos = duracao // INTERVALO
            idx_hora = HORARIOS.index(hora_ini)

            if idx_hora + blocos - 1 >= len(HORARIOS):
                conflitos += 1
                dt += timedelta(days=7)
                continue

            blocos_h = HORARIOS[idx_hora: idx_hora + blocos]

            # verifica conflito na data escolhida
            if any(agenda[data_iso_slot].get(h) is not None for h in blocos_h):
                conflitos += 1
                dt += timedelta(days=7)
                continue

            preco = PRECO_SERVICOS.get(servico, 0.0)

            for h in blocos_h:
                agenda[data_iso_slot][h] = {
                    "cliente": nome_cli,
                    "servico": servico,
                    "duracao": duracao,
                    "obs": obs,
                    "inicio": hora_ini,
                    "preco": preco,
                    "pago": False,
                    "extras": [],
                    "pacote": True,
                    "pacote_nome": pacote_nome,
                    "pacote_valor_mensal": val_mensal,
                }

            criados += 1
            dt += timedelta(days=7)  # próxima semana

        salvar_agenda(agenda)
        atualizar_lista_agenda()

        msg = f"Foram criados {criados} atendimentos de pacote."
        if ajustados_por_feriado > 0:
            msg += f"\n{ajustados_por_feriado} foram ajustados por caírem em feriado."
        if pulados_por_feriado > 0:
            msg += f"\n{pulados_por_feriado} semanas foram PULADAS por escolha sua nos feriados."
        if conflitos > 0:
            msg += f"\n{conflitos} semanas foram ignoradas por conflito de horário."

        messagebox.showinfo("Concluído", msg, parent=win)
        win.destroy()

    tk.Button(win, text="✅ Criar agendamentos de pacote", command=criar_pacote).pack(pady=15)

# ----- JANELA DE BUSCA POR CLIENTE -----

def janela_buscar_cliente():
    if not clientes:
        messagebox.showinfo("Info", "Nenhum cliente cadastrado ainda.")
        return

    win = tk.Toplevel(root)
    win.title("Buscar agendamentos por cliente")
    win.geometry("720x460")

    tk.Label(win, text="Buscar agendamentos por cliente", font=("Arial", 12, "bold")).pack(pady=5)

    tk.Label(win, text="Cliente:").pack()
    nomes_clientes = sorted(clientes.keys())
    nome_var = tk.StringVar()
    combo_nome = ttk.Combobox(win, textvariable=nome_var, values=nomes_clientes, state="readonly")
    combo_nome.pack(pady=5)

    frame = tk.Frame(win)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    lista_res = tk.Listbox(frame, height=16, width=95)
    lista_res.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll_res = tk.Scrollbar(frame, command=lista_res.yview)
    scroll_res.pack(side=tk.RIGHT, fill=tk.Y)
    lista_res.config(yscrollcommand=scroll_res.set)

    # guardamos objetos com info do item clicado
    mapa_itens = []  # cada item: dict com tipo, data_iso, hora, etc.

    info_var = tk.StringVar(value="Selecione um item para ver detalhes.")
    lbl_info = tk.Label(win, textvariable=info_var, justify="left", font=("Arial", 9), fg="gray")
    lbl_info.pack(pady=(0, 5), padx=10, anchor="w")

    def buscar():
        nonlocal mapa_itens
        nome = nome_var.get().strip()
        lista_res.delete(0, tk.END)
        mapa_itens.clear()
        info_var.set("Selecione um item para ver detalhes.")

        if not nome:
            messagebox.showerror("Erro", "Selecione um cliente.", parent=win)
            return

        resultados = []

        for data_iso, dia in agenda.items():
            if not isinstance(dia, dict):
                continue

            # Agendamentos
            for hora, slot in dia.items():
                if isinstance(hora, str) and hora.startswith("_"):
                    continue
                if not isinstance(slot, dict):
                    continue
                if slot.get("inicio") != hora:
                    continue

                if slot.get("cliente") == nome:
                    resultados.append({
                        "tipo": "AGENDAMENTO",
                        "data_iso": data_iso,
                        "hora": hora,
                        "servico": slot.get("servico", ""),
                        "obs": slot.get("obs", ""),
                        "pago": bool(slot.get("pago", False)),
                        "total": float(slot.get("preco", PRECO_SERVICOS.get(slot.get("servico",""), 0.0))) +
                                 sum(float(e.get("valor", 0.0)) for e in slot.get("extras", [])),
                        "pacote": bool(slot.get("pacote", False)),
                        "pacote_nome": slot.get("pacote_nome"),
                        "extras": slot.get("extras", []),
                    })

            # Vendas avulsas (se tiver cliente preenchido)
            vendas = dia.get("_vendas_avulsas", [])
            if isinstance(vendas, list):
                for idx, v in enumerate(vendas):
                    if not isinstance(v, dict):
                        continue
                    if v.get("cliente", "").strip() == nome:
                        resultados.append({
                            "tipo": "VENDA",
                            "data_iso": data_iso,
                            "indice": idx,
                            "produto": v.get("produto", ""),
                            "valor": float(v.get("valor", 0.0)),
                            "pago": bool(v.get("pago", True)),
                        })

        if not resultados:
            lista_res.insert(tk.END, "Nenhum registro encontrado para esse cliente.")
            return

        # ordena por data/hora (venda vai com hora '--' no display)
        def chave_ord(r):
            h = r.get("hora", "--")
            return (r["data_iso"], h)
        resultados.sort(key=chave_ord)

        for r in resultados:
            data_br = iso_para_br(r["data_iso"])
            if r["tipo"] == "AGENDAMENTO":
                hora = r["hora"]
                serv = r.get("servico", "")
                tag_pac = " (PACOTE)" if r.get("pacote") else ""
                status = "Pago" if r.get("pago") else "Pendente"
                linha = f"{data_br} - {hora} - {serv}{tag_pac} - R$ {r.get('total',0.0):.2f} - {status} [AG]"
            else:
                prod = r.get("produto", "")
                status = "Pago" if r.get("pago") else "Pendente"
                linha = f"{data_br} - -- - (Venda) {prod} - R$ {r.get('valor',0.0):.2f} - {status} [VD]"

            lista_res.insert(tk.END, linha)
            mapa_itens.append(r)

    def item_selecionado(event=None):
        if not lista_res.curselection():
            return
        idx = lista_res.curselection()[0]
        if idx < 0 or idx >= len(mapa_itens):
            return

        r = mapa_itens[idx]
        data_br = iso_para_br(r["data_iso"])

        if r["tipo"] == "AGENDAMENTO":
            extras = r.get("extras", [])
            extras_txt = ", ".join(f"{e.get('nome','')} (R$ {float(e.get('valor',0.0)):.2f})" for e in extras) if extras else "Nenhum"
            pacote_txt = f"Sim ({r.get('pacote_nome')})" if r.get("pacote") else "Não"
            status = "Pago" if r.get("pago") else "Pendente"

            info_var.set(
                f"📅 {data_br} às {r.get('hora')}\n"
                f"✂️ Serviço: {r.get('servico')}\n"
                f"📦 Pacote: {pacote_txt}\n"
                f"🧴 Extras: {extras_txt}\n"
                f"💰 Total: R$ {r.get('total',0.0):.2f} | Status: {status}"
            )
        else:
            status = "Pago" if r.get("pago") else "Pendente"
            info_var.set(
                f"🛒 Venda avulsa em {data_br}\n"
                f"📦 Produto: {r.get('produto')}\n"
                f"💰 Valor: R$ {r.get('valor',0.0):.2f} | Status: {status}"
            )

    lista_res.bind("<<ListboxSelect>>", item_selecionado)

    

    def ir_para_data():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        r = mapa_itens[idx]
        data_var.set(iso_para_br(r["data_iso"]))
        atualizar_campos_de_data()
        win.lift()

    def on_duplo_click(event=None):
        ir_para_data()

    lista_res.bind("<Double-Button-1>", on_duplo_click)

    def editar_selecionado():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        r = mapa_itens[idx]
        if r["tipo"] != "AGENDAMENTO":
            messagebox.showinfo("Info", "Somente agendamentos podem ser editados aqui.", parent=win)
            return
        janela_editar_agendamento_em(r["data_iso"], r["hora"])

    def abrir_caixa_data():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        r = mapa_itens[idx]
        data_var.set(iso_para_br(r["data_iso"]))
        atualizar_campos_de_data()
        abrir_caixa_dia()

    def marcar_venda_paga():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        if idx < 0 or idx >= len(mapa_itens):
            return
        r = mapa_itens[idx]
        if r.get("tipo") != "VENDA":
            messagebox.showinfo("Info", "Selecione uma VENDA avulsa.", parent=win)
            return

        dia = agenda.get(r["data_iso"], {})
        vendas = dia.get("_vendas_avulsas", [])
        i = r.get("indice")
        if not isinstance(vendas, list) or i is None or not (0 <= i < len(vendas)):
            messagebox.showerror("Erro", "Venda não encontrada.", parent=win)
            return

        if bool(vendas[i].get("pago", True)):
            messagebox.showinfo("Info", "Essa venda já está como paga.", parent=win)
            return

        vendas[i]["pago"] = True
        salvar_agenda(agenda)
        buscar()
        info_var.set("Venda marcada como paga ✅")

    # ----- botões deluxe -----
    btns = tk.Frame(win)
    btns.pack(pady=5)

    def cancelar_selecionado():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        if idx < 0 or idx >= len(mapa_itens):
            return
        r = mapa_itens[idx]
        if r.get("tipo") != "AGENDAMENTO":
            messagebox.showinfo("Info", "Selecione um AGENDAMENTO para cancelar.", parent=win)
            return
        cancelar_agendamento_em(r["data_iso"], r.get("hora"), parent=win)
        buscar()

    def adicionar_produto_selecionado():
        if not lista_res.curselection():
            messagebox.showinfo("Info", "Selecione um item.", parent=win)
            return
        idx = lista_res.curselection()[0]
        if idx < 0 or idx >= len(mapa_itens):
            return
        r = mapa_itens[idx]
        if r.get("tipo") != "AGENDAMENTO":
            messagebox.showinfo("Info", "Selecione um AGENDAMENTO para adicionar produto.", parent=win)
            return
        adicionar_produto_em_agendamento(r["data_iso"], r.get("hora"), parent=win)
        buscar()

    tk.Button(btns, text="🔍 Buscar", command=buscar, width=14).grid(row=0, column=0, padx=5, pady=3)
    tk.Button(btns, text="📅 Ir para data", command=ir_para_data, width=14).grid(row=0, column=1, padx=5, pady=3)
    tk.Button(btns, text="✏️ Editar", command=editar_selecionado, width=14).grid(row=0, column=2, padx=5, pady=3)
    tk.Button(btns, text="💰 Caixa do dia", command=abrir_caixa_data, width=14).grid(row=0, column=3, padx=5, pady=3)

    tk.Button(btns, text="❌ Cancelar", command=cancelar_selecionado, width=14).grid(row=1, column=1, padx=5, pady=3)
    tk.Button(btns, text="🧴 Add produto", command=adicionar_produto_selecionado, width=14).grid(row=1, column=2, padx=5, pady=3)
    tk.Button(btns, text="✅ Pagar venda", command=marcar_venda_paga, width=14).grid(row=1, column=3, padx=5, pady=3)

# ----- BOTÕES INFERIORES -----

frame_botoes = tk.Frame(root)
frame_botoes.pack(pady=10)

btn_ver = tk.Button(
    frame_botoes, text="📅 Ver agenda do dia",
    width=20, command=atualizar_lista_agenda
)
btn_ver.grid(row=0, column=0, padx=5, pady=5)

btn_novo = tk.Button(
    frame_botoes, text="➕ Novo agendamento",
    width=20, command=janela_agendar
)
btn_novo.grid(row=0, column=1, padx=5, pady=5)

btn_cancelar = tk.Button(
    frame_botoes, text="❌ Cancelar horário",
    width=20, command=cancelar_horario
)
btn_cancelar.grid(row=1, column=0, padx=5, pady=5)

btn_cli = tk.Button(
    frame_botoes, text="➕ Cadastrar Clientes",
    width=20, command=abrir_aniversarios
)
btn_cli.grid(row=1, column=1, padx=5, pady=5)

btn_editar = tk.Button(
    frame_botoes,
    text="✏️ Editar agendamento",
    width=20,
    command=janela_editar_agendamento
)
btn_editar.grid(row=2, column=0, padx=5, pady=5)

btn_buscar = tk.Button(
    frame_botoes,
    text="🔍 Buscar cliente",
    width=20,
    command=janela_buscar_cliente,
)
btn_buscar.grid(row=2, column=1, columnspan=2, pady=5)

btn_caixa = tk.Button(
    frame_botoes,
    text="💰 Caixa do dia",
    width=20,
    command=abrir_caixa_dia,
)
btn_caixa.grid(row=3, column=0, padx=5, pady=5)

btn_venda_avulsa = tk.Button(
    frame_botoes,
    text="🛒 Venda produto",
    width=20,
    command=registrar_venda_avulsa,
)
btn_venda_avulsa.grid(row=3, column=1, padx=5, pady=5)

btn_rel_dia = tk.Button(
    frame_botoes,
    text="📊 Relatório do dia",
    width=20,
    command=abrir_relatorio_dia,
)
btn_rel_dia.grid(row=4, column=0, padx=5, pady=5)

btn_rel_mes = tk.Button(
    frame_botoes,
    text="📆 Relatório mensal",
    width=20,
    command=abrir_relatorio_mes,
)
btn_rel_mes.grid(row=4, column=1, padx=5, pady=5)

btn_pacote = tk.Button(
    frame_botoes,
    text="📦 Cliente fixo / Pacote",
    width=20,
    command=janela_pacote_cliente,
)
btn_pacote.grid(row=5, column=0, padx=5, pady=5)

# ----- INICIALIZAÇÃO -----

set_data_hoje()  # já chama atualizar_campos_de_data() por dentro

root.mainloop()
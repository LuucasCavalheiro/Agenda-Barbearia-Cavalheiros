import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
from datetime import datetime
from tkcalendar import Calendar
import shutil
from datetime import datetime

ARQUIVO_AGENDA = "agenda.json"
ARQUIVO_CLIENTES = "clientes.json"
BACKUP_DIR = "backups"

HORARIO_INICIO = (9, 0)    # 09:00
HORARIO_FIM = (20, 30)     # 20:30
INTERVALO = 30             # em minutos

SERVICOS = {
    "Cabelo": 30,
    "Barba": 30,
    "Cabelo e Barba": 60,
    "Outro": 30,
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
    
    fazer_backup()

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
root.geometry("520x480")

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

        if indice + blocos - 1 >= len(HORARIOS):
            messagebox.showerror(
                "Erro",
                "Esse serviço não cabe até o fim do expediente nesse horário."
            )
            return

        blocos_horarios = HORARIOS[indice: indice + blocos]

        # Verificar se todos os blocos estão livres
        if any(agenda[data_iso].get(h) is not None for h in blocos_horarios):
            messagebox.showerror(
                "Erro",
                "Um ou mais horários desse período já estão ocupados."
            )
            return

        # Gravar agendamento
        for h in blocos_horarios:
            agenda[data_iso][h] = {
                "cliente": nome,
                "servico": servico,
                "duracao": duracao,
                "obs": obs,
                "inicio": hora_inicial,
            }

        salvar_agenda(agenda)
        atualizar_lista_agenda()
        messagebox.showinfo("Sucesso", "Agendamento realizado com sucesso!")
        win.destroy()

    tk.Button(win, text="✅ Salvar agendamento", command=salvar_agendamento).pack(pady=15)

# ----- CANCELAR HORÁRIO -----

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
        hora = tk.simpledialog.askstring("Cancelar horário", "Digite o horário (ex: 09:00):")
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

    messagebox.showinfo("Detalhes do agendamento", msg)

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

# ----- JANELA DE BUSCA POR CLIENTE -----

def janela_buscar_cliente():
    if not clientes:
        messagebox.showinfo("Info", "Nenhum cliente cadastrado ainda.")
        return

    win = tk.Toplevel(root)
    win.title("Buscar agendamentos por cliente")
    win.geometry("520x420")

    tk.Label(
        win,
        text="Buscar agendamentos por cliente",
        font=("Arial", 12, "bold"),
    ).pack(pady=5)

    # seleção do cliente
    tk.Label(win, text="Cliente:").pack()
    nomes_clientes = sorted(clientes.keys())
    nome_var = tk.StringVar()
    combo_nome = ttk.Combobox(
        win, textvariable=nome_var, values=nomes_clientes, state="readonly"
    )
    combo_nome.pack(pady=5)

    # lista de resultados
    frame_lista_res = tk.Frame(win)
    frame_lista_res.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    lista_res = tk.Listbox(frame_lista_res, height=15, width=70)
    lista_res.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll_res = tk.Scrollbar(frame_lista_res, command=lista_res.yview)
    scroll_res.pack(side=tk.RIGHT, fill=tk.Y)
    lista_res.config(yscrollcommand=scroll_res.set)

    def buscar():
        nome = nome_var.get().strip()
        lista_res.delete(0, tk.END)

        if not nome:
            messagebox.showerror("Erro", "Selecione um cliente.", parent=win)
            return

        resultados = []

        # varre TODA a agenda (todas as datas / horários)
        for data_iso, dia in agenda.items():
            for hora, slot in dia.items():
                if slot and slot.get("cliente") == nome:
                    resultados.append(
                        (
                            data_iso,
                            hora,
                            slot.get("servico", ""),
                            slot.get("obs", ""),
                        )
                    )

        if not resultados:
            lista_res.insert(
                tk.END,
                "Nenhum agendamento encontrado para esse cliente.",
            )
            return

        # ordena por data + hora
        resultados.sort(key=lambda t: (t[0], t[1]))

        for data_iso, hora, servico, obs in resultados:
            data_br = iso_para_br(data_iso)
            linha = f"{data_br} - {hora} - {servico}"
            if obs:
                linha += f" ({obs})"
            lista_res.insert(tk.END, linha)

    tk.Button(win, text="🔍 Buscar", command=buscar).pack(pady=5)

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

btn_buscar = tk.Button(
    frame_botoes,
    text="🔍 Buscar cliente",
    width=20,
    command=janela_buscar_cliente,
)
btn_buscar.grid(row=2, column=0, columnspan=2, pady=5)

# ----- INICIALIZAÇÃO -----

set_data_hoje()  # já chama atualizar_campos_de_data() por dentro

root.mainloop()

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import json
import os
from datetime import datetime
from tkcalendar import Calendar

ARQUIVO_AGENDA = "agenda.json"

HORARIO_INICIO = (9, 0)    # 09:00
HORARIO_FIM = (20, 30)     # 20:30
INTERVALO = 30             # em minutos

SERVICOS = {
    "Cabelo": 30,
    "Barba": 30,
    "Cabelo e Barba": 60,
    "Outro": 30,
}

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

# Lista com os dias da semana em português
DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

def dia_semana_br(data_iso):
    """Recebe 'AAAA-MM-DD' e retorna o nome do dia da semana em português."""
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        indice = dt.weekday()  # 0 = Segunda, 6 = Domingo
        return DIAS_SEMANA[indice]
    except ValueError:
        return ""

# ---------- INTERFACE GRÁFICA ----------

agenda = carregar_agenda()

root = tk.Tk()
root.title("Agenda - Barbearia Cavalheiros")
root.geometry("480x440")

# ---------- TOPO: DATA ----------

frame_data = tk.Frame(root)
frame_data.pack(pady=10)

tk.Label(frame_data, text="Data (DD/MM/AAAA): ").pack(side=tk.LEFT)

data_var = tk.StringVar()

def atualizar_dia_semana():
    """Atualiza o label com o dia da semana baseado em data_var."""
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        dia_semana_var.set("")
        return
    nome = dia_semana_br(data_iso)
    if nome:
        dia_semana_var.set(f"Dia da semana: {nome}")
    else:
        dia_semana_var.set("")

def atualizar_lista_agenda():
    atualizar_dia_semana()

    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)
    salvar_agenda(agenda)

    lista_horarios.delete(0, tk.END)
    label_dia.config(text=f"Agenda do dia {iso_para_br(data_iso)}")

    for h in HORARIOS:
        slot = agenda[data_iso].get(h)
        if slot is None:
            texto = f"{h} - LIVRE"
        else:
            texto = f"{h} - {slot['cliente']} ({slot['servico']})"
        lista_horarios.insert(tk.END, texto)

def set_data_hoje():
    hoje = datetime.now().strftime("%d/%m/%Y")
    data_var.set(hoje)
    atualizar_lista_agenda()

def abrir_calendario():
    # Garante que a janela principal sabe seu tamanho/posição atual
    root.update_idletasks()

    # Pega posição e tamanho da janela principal
    root_x = root.winfo_rootx()
    root_y = root.winfo_rooty()
    root_w = root.winfo_width()

    # Cria a janela do calendário
    win = tk.Toplevel(root)
    win.title("Selecionar Data")

    # Define tamanho da janelinha do calendário
    largura = 300
    altura = 300

    # Calcula posição: à direita da janela principal, com um espacinho de 10px
    x = root_x + root_w + 10
    y = root_y

    # Aplica tamanho + posição (largura x altura + x + y)
    win.geometry(f"{largura}x{altura}+{x}+{y}")

    # Cria o calendário dentro da janelinha
    cal = Calendar(
        win,
        selectmode="day",
        date_pattern="dd/mm/yyyy"
    )
    cal.pack(pady=10)

    # Função chamada quando clicar em "Confirmar"
    def confirmar_data():
        data_escolhida = cal.get_date()   # pega a data
        data_var.set(data_escolhida)      # coloca no campo de data
        atualizar_lista_agenda()          # atualiza a agenda do dia
        win.destroy()                     # fecha a janela do calendário

    tk.Button(win, text="Confirmar", command=confirmar_data).pack(pady=10)

data_entry = tk.Entry(frame_data, textvariable=data_var, width=12, justify="center")
data_entry.pack(side=tk.LEFT, padx=5)

btn_hoje = tk.Button(frame_data, text="Hoje", command=set_data_hoje)
btn_hoje.pack(side=tk.LEFT)

btn_calendario = tk.Button(frame_data, text="📅", command=abrir_calendario)
btn_calendario.pack(side=tk.LEFT, padx=5)

# Label para mostrar o dia da semana
dia_semana_var = tk.StringVar()
label_dia_semana = tk.Label(root, textvariable=dia_semana_var, font=("Arial", 10))
label_dia_semana.pack()

# ---------- LISTA DA AGENDA DO DIA ----------

frame_lista = tk.Frame(root)
frame_lista.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

label_dia = tk.Label(frame_lista, text="", font=("Arial", 12, "bold"))
label_dia.pack(pady=5)

lista_horarios = tk.Listbox(frame_lista, height=12, width=60)
lista_horarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scroll = tk.Scrollbar(frame_lista, command=lista_horarios.yview)
scroll.pack(side=tk.RIGHT, fill=tk.Y)
lista_horarios.config(yscrollcommand=scroll.set)

# ---------- FUNÇÕES DE AGENDAR E CANCELAR ----------

def janela_agendar():
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    win = tk.Toplevel(root)
    win.title("Novo agendamento")
    win.geometry("380x380")

    tk.Label(win, text=f"Data: {iso_para_br(data_iso)}").pack(pady=5)

    # Nome
    tk.Label(win, text="Nome do cliente:").pack()
    nome_entry = tk.Entry(win)
    nome_entry.pack(pady=5)

    # Serviço
    tk.Label(win, text="Serviço:").pack()
    servico_var = tk.StringVar(value="Cabelo")
    for s in SERVICOS.keys():
        tk.Radiobutton(win, text=s, variable=servico_var, value=s).pack(anchor="w")

    # Horário
    tk.Label(win, text="Horário inicial:").pack(pady=(10, 0))
    horario_var = tk.StringVar(value=HORARIOS[0])
    combo_horario = ttk.Combobox(
        win, textvariable=horario_var, values=HORARIOS, state="readonly"
    )
    combo_horario.pack(pady=5)

    # Observações
    tk.Label(win, text="Observações (opcional):").pack()
    obs_entry = tk.Entry(win)
    obs_entry.pack(pady=5, fill=tk.X, padx=20)

    def salvar_agendamento():
        nome = nome_entry.get().strip()
        if not nome:
            messagebox.showerror("Erro", "Informe o nome do cliente.")
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

    tk.Button(win, text="✅ Salvar agendamento",
              command=salvar_agendamento).pack(pady=15)


def cancelar_horario():
    data_str = data_var.get().strip()
    data_iso = str_data_para_iso(data_str)
    if not data_iso:
        messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
        return

    garantir_dia_na_agenda(agenda, data_iso)

    # Pede o horário a partir da seleção na lista ou pergunta
    selecao = lista_horarios.curselection()
    if selecao:
        linha = lista_horarios.get(selecao[0])
        hora = linha.split(" - ")[0]
    else:
        # Se nada selecionado, pergunta
        hora = simpledialog.askstring(
            "Cancelar horário", "Digite o horário (ex: 09:00):"
        )
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

# ---------- BOTÕES INFERIORES ----------

frame_botoes = tk.Frame(root)
frame_botoes.pack(pady=10)

btn_ver = tk.Button(
    frame_botoes,
    text="📅 Ver agenda do dia",
    width=20,
    command=atualizar_lista_agenda
)
btn_ver.grid(row=0, column=0, padx=5, pady=5)

btn_novo = tk.Button(
    frame_botoes,
    text="➕ Novo agendamento",
    width=20,
    command=janela_agendar
)
btn_novo.grid(row=0, column=1, padx=5, pady=5)

btn_cancelar = tk.Button(
    frame_botoes,
    text="❌ Cancelar horário",
    width=20,
    command=cancelar_horario
)
btn_cancelar.grid(row=1, column=0, columnspan=2, pady=5)

# Define data inicial e atualiza a agenda
set_data_hoje()

root.mainloop()

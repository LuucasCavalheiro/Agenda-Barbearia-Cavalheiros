import json
import os
from datetime import datetime

ARQUIVO_AGENDA = "agenda.json"

HORARIO_INICIO = (9, 0)   # 9:00
HORARIO_FIM = (20, 30)    # 20:30
INTERVALO_MINUTOS = 30

# Serviços da barbearia
SERVICOS = {
    "1": ("Cabelo", 30),
    "2": ("Barba", 30),
    "3": ("Cabelo e barba", 60),
    "4": ("Outro", 30),
}

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
    fim_hora, fim_minuto = HORARIO_FIM
    while True:
        horarios.append(f"{hora:02d}:{minuto:02d}")
        if hora == fim_hora and minuto == fim_minuto:
            break
        minuto += INTERVALO_MINUTOS
        if minuto >= 60:
            minuto -= 60
            hora += 1
    return horarios

HORARIOS_DIA = gerar_horarios()

def pegar_data_usuario():
    while True:
        data_str = input("Digite a data (DD/MM/AAAA): ").strip()
        try:
            data = datetime.strptime(data_str, "%d/%m/%Y")
            return data.strftime("%Y-%m-%d")
        except ValueError:
            print("Data inválida. Tente novamente.")

def garantir_dia_na_agenda(agenda, dia):
    if dia not in agenda:
        agenda[dia] = {h: None for h in HORARIOS_DIA}

def mostrar_agenda_dia(agenda, dia):
    garantir_dia_na_agenda(agenda, dia)
    print(f"\nAgenda do dia {datetime.strptime(dia, '%Y-%m-%d').strftime('%d/%m/%Y')}:")
    print("-" * 40)
    for h in HORARIOS_DIA:
        slot = agenda[dia].get(h)
        if slot is None:
            status = "LIVRE"
        else:
            status = f"OCUPADO - {slot['cliente']} ({slot['servico']})"
        print(f"{h} - {status}")
    print("-" * 40)

def escolher_servico():
    print("\nEscolha o serviço:")
    for k, (nome, duracao) in SERVICOS.items():
        print(f"{k} - {nome} ({duracao} min)")
    while True:
        op = input("Opção: ").strip()
        if op in SERVICOS:
            return SERVICOS[op]
        print("Opção inválida.")

def agendar_horario(agenda):
    dia = pegar_data_usuario()
    garantir_dia_na_agenda(agenda, dia)
    mostrar_agenda_dia(agenda, dia)

    cliente = input("Nome do cliente: ").strip()
    servico_nome, duracao = escolher_servico()
    obs = input("Observações (opcional): ").strip()

    # quantos blocos de 30 min o serviço ocupa
    blocos = duracao // INTERVALO_MINUTOS

    while True:
        hora_escolhida = input("Digite o horário inicial (ex: 09:00): ").strip()
        if hora_escolhida not in HORARIOS_DIA:
            print("Horário inválido. Tente novamente.")
            continue

        indice = HORARIOS_DIA.index(hora_escolhida)
        if indice + blocos - 1 >= len(HORARIOS_DIA):
            print("Esse serviço não cabe até o fim do expediente. Escolha outro horário.")
            continue

        blocos_horarios = HORARIOS_DIA[indice : indice + blocos]

        # verifica se todos os blocos estão livres
        if any(agenda[dia][h] is not None for h in blocos_horarios):
            print("Um dos horários desse período já está ocupado. Escolha outro.")
            continue

        # reservar blocos
        for h in blocos_horarios:
            agenda[dia][h] = {
                "cliente": cliente,
                "servico": servico_nome,
                "duracao": duracao,
                "obs": obs,
                "inicio": hora_escolhida,
            }
        salvar_agenda(agenda)
        print(f"\n✅ Agendado {servico_nome} para {cliente} em {hora_escolhida} ({duracao} min).")
        break

def cancelar_horario(agenda):
    dia = pegar_data_usuario()
    garantir_dia_na_agenda(agenda, dia)
    mostrar_agenda_dia(agenda, dia)

    hora = input("Digite o horário a cancelar (ex: 09:00): ").strip()
    if hora not in HORARIOS_DIA:
        print("Horário inválido.")
        return

    slot = agenda[dia].get(hora)
    if slot is None:
        print("Esse horário já está livre.")
        return

    inicio = slot["inicio"]
    duracao = slot["duracao"]
    blocos = duracao // INTERVALO_MINUTOS
    indice_inicio = HORARIOS_DIA.index(inicio)
    blocos_horarios = HORARIOS_DIA[indice_inicio : indice_inicio + blocos]

    confirm = input(f"Confirmar cancelamento de {slot['servico']} de {slot['cliente']} às {inicio}? (s/n) ").strip().lower()
    if confirm != "s":
        print("Cancelamento abortado.")
        return

    for h in blocos_horarios:
        agenda[dia][h] = None
    salvar_agenda(agenda)
    print("✅ Horário cancelado com sucesso.")

def menu():
    agenda = carregar_agenda()
    while True:
        print("\n" + "=" * 40)
        print("   AGENDA - BARBEARIA CAVALHEIROS")
        print("=" * 40)
        print("1 - Ver agenda do dia")
        print("2 - Agendar horário")
        print("3 - Cancelar horário")
        print("4 - Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            dia = pegar_data_usuario()
            garantir_dia_na_agenda(agenda, dia)
            mostrar_agenda_dia(agenda, dia)
        elif opcao == "2":
            agendar_horario(agenda)
        elif opcao == "3":
            cancelar_horario(agenda)
        elif opcao == "4":
            print("Saindo da agenda. Até mais!")
            break
        else:
            print("Opção inválida, tente novamente.")

if __name__ == "__main__":
    menu()

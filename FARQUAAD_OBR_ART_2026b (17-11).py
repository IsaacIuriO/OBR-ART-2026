from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Color
from pybricks.tools import wait

hub = PrimeHub()

# --- CONFIGURAÇÕES ---
POTENCIA_ALVO = 90  
PASSO_RAMPA   = 2   

# MOTORES
motor_fl = Motor(Port.B) # Frente Esq
motor_fr = Motor(Port.A) # Frente Dir
motor_rl = Motor(Port.E) # Trás Esq
motor_rr = Motor(Port.F) # Trás Dir

# --- FUNÇÕES DE SUPORTE ---

def parar():
    motor_fl.stop()
    motor_fr.stop()
    motor_rl.stop()
    motor_rr.stop()
    wait(500)

def aplicar_caranguejo_dir(p):
    """Lógica Mecanum para deslizar à direita"""
    motor_fl.dc(p)
    motor_fr.dc(p)
    motor_rl.dc(-p)
    motor_rr.dc(-p)

def aplicar_caranguejo_esq(p):
    """Lógica Mecanum para deslizar à esquerda"""
    motor_fl.dc(p)
    motor_fr.dc(p)
    motor_rl.dc(-p)
    motor_rr.dc(-p)

def aplicar_re_reto(p):
    """
    Lógica para andar de ré compensando o desvio à direita.
    Ajuste o fator_correcao se ele ainda entortar:
    - Menor que 0.85: Esquerda fica mais fraca.
    - Maior que 0.85: Esquerda fica mais forte.
    """
    fator_correcao = 0.75 
    motor_fl.dc(-(p * fator_correcao)) 
    motor_rl.dc(p * fator_correcao)    
    motor_fr.dc(p)                     
    motor_rr.dc(-p)

def mini_giro(p):
    """Lógica Mecanum para giro anti-horario"""
    motor_fl.dc(p) #i
    motor_fr.dc(p) #n
    motor_rl.dc(p) #i
    motor_rr.dc(p) #n

    # Giro antihorário (normal)
    # fl: -p
    # fr: p
    # rl: -p
    # rr: p          

# --- EXECUÇÃO ---

# PASSO 0: ESPERA INICIAL
print("Aguardando 55 segundos...")
hub.light.on(Color.ORANGE) 
wait(54000)

# Sinal de início
hub.light.on(Color.RED)
wait(1000)

# ==========================================
# FASE 1: CARANGUEJO PARA ESQUERDA (7.5s)
# ==========================================
hub.light.on(Color.CYAN)

# Aceleração
for p in range(20, POTENCIA_ALVO + 1, PASSO_RAMPA):
    aplicar_caranguejo_esq(p)
    wait(30)

wait(2500) 

# Frenagem
for p in range(POTENCIA_ALVO, 19, -PASSO_RAMPA * 2):
    aplicar_caranguejo_esq(p)
    wait(30)

parar()

# ==========================================
# FASE 2: ANDAR DE RÉ (3s - COM CORREÇÃO)
# ==========================================
hub.light.on(Color.BLUE)

# Aceleração
for p in range(20, POTENCIA_ALVO + 1, PASSO_RAMPA):
    aplicar_re_reto(p)
    wait(30)

wait(1500) 

# Frenagem
for p in range(POTENCIA_ALVO, 19, -PASSO_RAMPA * 2):
    aplicar_re_reto(p)
    wait(30)

parar()
wait(5000)

# ==========================================
# FASE 3: ANDAR DE RÉ (3s - COM CORREÇÃO)
# ==========================================
hub.light.on(Color.GREEN)

# Aceleração
for p in range(20, POTENCIA_ALVO + 1, PASSO_RAMPA):
    aplicar_re_reto(p)
    wait(30)

wait(1000) 

# Frenagem
for p in range(POTENCIA_ALVO, 19, -PASSO_RAMPA * 2):
    aplicar_re_reto(p)
    wait(30)

parar()

# ==========================================
# FASE 4: MINI-GIRO (0.3s - COM CORREÇÃO)
# ==========================================

hub.light.on(Color.MAGENTA)

mini_giro(55)
wait(300)

parar()

# FIM
hub.light.on(Color.GREEN)
print("Missão concluída!")

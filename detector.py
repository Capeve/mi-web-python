import cv2
import easyocr
import tkinter as tk
from tkinter import filedialog, Label, Button, Text, Scrollbar, messagebox
from PIL import Image, ImageTk
from datetime import datetime
import sqlite3
import re
import requests  # <--- Agregado para la conexión web

# ===== CONFIGURACIÓN =====
PLACAS_AUTORIZADAS = {
    "JNU540", "RIU532", "XYZ789", "JNU541", "JLY246",
    "VEG388", "WNU046", "BOE074", "FNU046", "MEG386"
}

# URL del Dashboard Web
URL_API = "https://mi-web-python-tuho.onrender.com/api/subir_placa"

# Inicializar EasyOCR
reader = easyocr.Reader(['en'], gpu=False)

# ===== BASE DE DATOS =====
conn = sqlite3.connect('placas.db')
cursor = conn.cursor()

# Crear tabla si no existe (con más campos)
cursor.execute('''
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL,
    placa_original TEXT,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    estado TEXT,
    confianza REAL
)
''')
conn.commit()

# ===== VARIABLES =====
contador_total = 0

# --- FUNCIÓN PARA ENVIAR DATOS A LA WEB ---
def enviar_a_web(placa, confianza):
    try:
        requests.post(URL_API, json={"placa": placa, "confianza": float(confianza)}, timeout=1)
    except:
        pass # Ignorar si la web no está abierta para no trabar el programa

def corregir_placa(texto_ocr):
    texto = texto_ocr.upper().strip()
    texto_original = texto
    
    # Eliminar caracteres no alfanuméricos
    texto = re.sub(r'[^A-Z0-9]', '', texto)
    
    # Mapeos de corrección
    correcciones = {
        'FNU046': 'WNU046',
        'MEG386': 'VEG388',
        'NEG386': 'VEG388',
        'FNU046': 'WNU046',
    }
    
    # Correcciones específicas primero
    if texto in correcciones:
        return correcciones[texto]
    
    # Correcciones generales para formato 3 letras + 3 números
    if len(texto) == 6:
        parte1 = texto[:3]
        parte2 = texto[3:]
        
        # Mapeos
        num_a_letra = {'0':'O', '1':'I', '2':'Z', '3':'E', '4':'A',
                      '5':'S', '6':'G', '7':'T', '8':'B', '9':'J'}
        letra_a_num = {'O':'0', 'I':'1', 'Z':'2', 'E':'3', 'A':'4',
                      'S':'5', 'G':'6', 'T':'7', 'B':'8', 'J':'9'}
        
        # Corregir parte de letras
        parte1_corregida = []
        for c in parte1:
            if c.isdigit() and c in num_a_letra:
                parte1_corregida.append(num_a_letra[c])
            else:
                parte1_corregida.append(c)
        
        # Corregir parte de números
        parte2_corregida = []
        for c in parte2:
            if c.isalpha() and c in letra_a_num:
                parte2_corregida.append(letra_a_num[c])
            else:
                parte2_corregida.append(c)
        
        texto_corregido = ''.join(parte1_corregida + parte2_corregida)
        
        if texto_corregido != texto_original:
            return texto_corregido
    
    return texto

def detectar_placas():
    global contador_total
    
    file_path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg")])
    if not file_path:
        return

    # Procesar imagen
    image = cv2.imread(file_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resultados_ocr = reader.readtext(gray)

    placas_detectadas = []
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    hora_actual = datetime.now().strftime("%H:%M:%S")

    print("\n" + "="*50)
    print("🔍 NUEVA DETECCIÓN:")
    
    for res in resultados_ocr:
        texto_original = res[1]
        confianza = res[2]
        texto_limpio = texto_original.replace(" ", "").upper()
        texto_corregido = corregir_placa(texto_limpio)
        
        print(f"   OCR: '{texto_original}' (conf: {confianza:.2f}) -> '{texto_corregido}'")
        
        # Guardar TODO lo que parezca una placa
        if len(texto_corregido) >= 4:
            placas_detectadas.append({
                'placa': texto_corregido,
                'original': texto_original,
                'confianza': confianza
            })

    # Mostrar imagen
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img.thumbnail((500, 300))
    img = ImageTk.PhotoImage(img)
    label_img.config(image=img)
    label_img.image = img

    # Mostrar resultados
    text_result.delete(1.0, tk.END)

    if placas_detectadas:
        text_result.insert(tk.END, f"📸 {hora_actual}\n", "blue")
        text_result.insert(tk.END, "="*40 + "\n", "blue")
        
        for placa_info in placas_detectadas:
            placa = placa_info['placa']
            original = placa_info['original']
            confianza = placa_info['confianza']
            
            contador_total += 1
            
            if placa in PLACAS_AUTORIZADAS:
                resultado = "ACEPTADO"
                color = "green"
                simbolo = "✅"
            else:
                resultado = "DENEGADO"
                color = "red"
                simbolo = "❌"
            
            text_result.insert(tk.END, f"{simbolo} {placa}\n", color)
            text_result.insert(tk.END, f"   Original: '{original}' (conf: {confianza:.2f})\n", "gray")
            
            # ===== GUARDAR EN BD (UNA POR CADA DETECCIÓN) =====
            cursor.execute('''
                INSERT INTO registros (placa, placa_original, fecha, hora, estado, confianza)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (placa, original, fecha_actual, hora_actual, resultado, confianza))
            conn.commit()

            # ===== ENVIAR A WEB (LÍNEA AGREGADA) =====
            enviar_a_web(placa, confianza)
        
        label_contador.config(text=f"Vehículos: {contador_total}")
        text_result.insert(tk.END, f"\n📊 Total: {len(placas_detectadas)} detecciones\n", "blue")
    else:
        text_result.insert(tk.END, "❌ No se detectaron placas\n", "red")

# ===== VER ESTADÍSTICAS =====
def ver_estadisticas():
    stats_win = tk.Toplevel(root)
    stats_win.title("📊 Estadísticas")
    stats_win.geometry("700x500")
    stats_win.configure(bg="#f0f0f0")
    
    # Obtener datos
    cursor.execute("SELECT COUNT(*) FROM registros")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM registros WHERE estado='ACEPTADO'")
    aceptadas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM registros WHERE estado='DENEGADO'")
    denegadas = cursor.fetchone()[0]
    
    cursor.execute("SELECT * FROM registros ORDER BY id DESC LIMIT 30")
    datos = cursor.fetchall()
    
    # Mostrar
    tk.Label(stats_win, text="📈 ESTADÍSTICAS COMPLETAS", 
             font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)
    
    frame_stats = tk.Frame(stats_win, bg="white", relief="solid", bd=1)
    frame_stats.pack(pady=10, padx=20, fill="x")
    
    tk.Label(frame_stats, text=f"Total registros en BD: {total}", 
             font=("Arial", 12), bg="white").pack(pady=5)
    tk.Label(frame_stats, text=f"✅ Aceptadas: {aceptadas}", 
             font=("Arial", 12), fg="green", bg="white").pack()
    tk.Label(frame_stats, text=f"❌ Denegadas: {denegadas}", 
             font=("Arial", 12), fg="red", bg="white").pack()
    
    # Tabla
    tk.Label(stats_win, text="\n📋 ÚLTIMOS REGISTROS:", 
             font=("Arial", 12, "bold"), bg="#f0f0f0").pack()
    
    frame_tabla = tk.Frame(stats_win)
    frame_tabla.pack(pady=10, padx=20, fill="both", expand=True)
    
    scroll_tabla = Scrollbar(frame_tabla)
    scroll_tabla.pack(side="right", fill="y")
    
    listbox = tk.Listbox(frame_tabla, yscrollcommand=scroll_tabla.set,
                         font=("Consolas", 9), height=15)
    listbox.pack(side="left", fill="both", expand=True)
    
    scroll_tabla.config(command=listbox.yview)
    
    for row in datos:
        listbox.insert(tk.END, f"ID:{row[0]} | {row[3]} {row[4]} | {row[1]} | {row[5]}")

# ===== INTERFAZ =====
root = tk.Tk()
root.title("🚗 Detector de Placas - 30%")
root.geometry("750x700")
root.configure(bg="#f0f0f0")

# Título
tk.Label(root, text="SISTEMA DE DETECCIÓN DE PLACAS", 
         font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

# Botones
frame_btn = tk.Frame(root, bg="#f0f0f0")
frame_btn.pack(pady=10)

btn_select = Button(frame_btn, text="📸 SELECCIONAR IMAGEN",
                    command=detectar_placas, font=("Arial", 11),
                    bg="#27AE60", fg="white", width=20, height=1)
btn_select.pack(side="left", padx=5)

btn_stats = Button(frame_btn, text="📊 VER BD",
                   command=ver_estadisticas, font=("Arial", 11),
                   bg="#3498DB", fg="white", width=15, height=1)
btn_stats.pack(side="left", padx=5)

# Contador
label_contador = Label(root, text="Vehículos: 0", 
                       font=("Arial", 12, "bold"), bg="#f0f0f0")
label_contador.pack(pady=5)

# Imagen
label_img = Label(root, bg="white", relief="solid", bd=1)
label_img.pack(pady=10)

# Resultados
tk.Label(root, text="RESULTADOS", font=("Arial", 11, "bold"), 
         bg="#f0f0f0").pack()

text_result = Text(root, height=10, font=("Consolas", 10))
text_result.pack(pady=10, padx=20, fill="both", expand=True)

text_result.tag_configure("green", foreground="green")
text_result.tag_configure("red", foreground="red")
text_result.tag_configure("blue", foreground="blue")
text_result.tag_configure("gray", foreground="gray")

root.mainloop()
conn.close()
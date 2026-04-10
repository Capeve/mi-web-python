from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import json
import csv
from io import StringIO
from flask import Response
import os

app = Flask(__name__)

# ===== CREAR BASE DE DATOS AUTOMÁTICAMENTE =====
def crear_base_datos():
    # Crear conexión
    conn = sqlite3.connect('placas.db')
    cursor = conn.cursor()
    
    # Crear tabla si no existe
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
    
    # Verificar si hay datos
    cursor.execute("SELECT COUNT(*) FROM registros")
    if cursor.fetchone()[0] == 0:
        # Insertar datos de ejemplo
        ejemplos = [
            ("JNU540", "JNU 540", "2024-03-18", "10:30:25", "ACEPTADO", 0.95),
            ("WNU046", "FNU046", "2024-03-18", "10:31:10", "DENEGADO", 0.82),
            ("VEG388", "MEG386", "2024-03-18", "10:32:05", "DENEGADO", 0.78),
            ("JLY246", "LILY246", "2024-03-18", "10:33:20", "ACEPTADO", 0.91),
            ("RIU532", "RIU532", "2024-03-18", "10:34:15", "ACEPTADO", 0.88),
            ("XYZ789", "XYZ789", "2024-03-18", "10:35:30", "DENEGADO", 0.76),
        ]
        
        for e in ejemplos:
            cursor.execute('''
                INSERT INTO registros (placa, placa_original, fecha, hora, estado, confianza)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', e)
        
        conn.commit()
        print("✅ Datos de ejemplo insertados")
    
    conn.close()
    print("✅ Base de datos lista")

# ===== FUNCIONES DE BASE DE DATOS =====
def get_db():
    conn = sqlite3.connect('placas.db')
    conn.row_factory = sqlite3.Row
    return conn

# ===== CREAR BD AL INICIAR =====
crear_base_datos()

# ===== HTML COMPLETO (el mismo que tienes) =====
HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLACEMASTER PRO </title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background: #f4f7fc;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            height: 100vh;
            width: 280px;
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
            color: white;
            padding: 25px;
            box-shadow: 4px 0 20px rgba(0,0,0,0.1);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 25px;
        }

        .logo i {
            font-size: 2.2em;
            color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
            padding: 10px;
            border-radius: 12px;
        }

        .logo h2 {
            font-size: 1.4em;
            font-weight: 300;
        }

        .logo span {
            font-weight: 700;
            color: #4ade80;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            color: rgba(255,255,255,0.7);
        }

        .nav-item:hover {
            background: rgba(255,255,255,0.1);
            color: white;
        }

        .nav-item.active {
            background: #4ade80;
            color: white;
        }

        .nav-item i {
            width: 25px;
            font-size: 1.2em;
        }

        /* Main Content */
        .main-content {
            margin-left: 280px;
            padding: 30px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            background: white;
            padding: 20px 25px;
            border-radius: 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .header h1 {
            font-size: 1.8em;
            color: #1e293b;
        }

        .header h1 span {
            color: #4ade80;
            font-weight: 700;
        }

        .date-badge {
            background: #f8fafc;
            padding: 10px 20px;
            border-radius: 40px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #64748b;
        }

        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }

        .stat-info h3 {
            color: #64748b;
            font-size: 0.9em;
            font-weight: 500;
            margin-bottom: 8px;
        }

        .stat-info .number {
            font-size: 2.2em;
            font-weight: 700;
            color: #1e293b;
        }

        .stat-icon {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8em;
        }

        .stat-icon.total { background: #e0f2fe; color: #0284c7; }
        .stat-icon.accepted { background: #dcfce7; color: #4ade80; }
        .stat-icon.denied { background: #fee2e2; color: #f87171; }
        .stat-icon.precision { background: #fef9c3; color: #facc15; }

        /* Charts */
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 25px;
            margin-bottom: 30px;
        }

        .chart-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .chart-header h3 {
            color: #1e293b;
            font-size: 1.1em;
            font-weight: 600;
        }

        /* Filtros */
        .filters-bar {
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 25px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .search-box {
            flex: 1;
            display: flex;
            align-items: center;
            background: #f8fafc;
            border-radius: 12px;
            padding: 0 15px;
            border: 1px solid #e2e8f0;
        }

        .search-box i {
            color: #94a3b8;
        }

        .search-box input {
            flex: 1;
            padding: 12px;
            border: none;
            background: transparent;
            outline: none;
        }

        .filter-select {
            padding: 12px 20px;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: #f8fafc;
            cursor: pointer;
        }

        .btn-filter, .btn-export {
            padding: 12px 25px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }

        .btn-filter { background: #4ade80; color: white; }
        .btn-filter:hover { background: #22c55e; }
        .btn-export { background: #3b82f6; color: white; }
        .btn-export:hover { background: #2563eb; }

        /* Tabla */
        .table-container {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 15px 10px;
            color: #64748b;
            font-weight: 600;
            font-size: 0.9em;
            border-bottom: 2px solid #e2e8f0;
        }

        td {
            padding: 15px 10px;
            border-bottom: 1px solid #e2e8f0;
            color: #1e293b;
        }

        .badge {
            padding: 6px 12px;
            border-radius: 40px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .badge.accepted { background: #dcfce7; color: #4ade80; }
        .badge.denied { background: #fee2e2; color: #f87171; }

        /* Secciones */
        .section {
            display: none;
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-top: 20px;
        }

        .section.active {
            display: block;
        }

        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .config-card {
            background: #f8fafc;
            padding: 20px;
            border-radius: 12px;
        }

        .config-card h3 {
            margin-bottom: 15px;
            color: #1e293b;
        }

        .config-card label {
            display: block;
            margin: 10px 0 5px;
            color: #64748b;
        }

        .config-card input, .config-card select {
            width: 100%;
            padding: 10px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }

        .btn-save-config {
            background: #4ade80;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            width: 100%;
            margin-top: 15px;
            cursor: pointer;
        }

        .btn-danger {
            background: #f87171;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
        }

        .footer {
            text-align: center;
            margin-top: 30px;
            color: #64748b;
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="logo">
            <i class="fas fa-car"></i>
            <h2>PLACE<span>MASTER</span></h2>
        </div>
        
        <div class="nav-item active" onclick="showSection('dashboard')">
            <i class="fas fa-chart-pie"></i>
            <span>Dashboard</span>
        </div>
        <div class="nav-item" onclick="showSection('historial')">
            <i class="fas fa-history"></i>
            <span>Historial</span>
        </div>
        <div class="nav-item" onclick="showSection('configuracion')">
            <i class="fas fa-cog"></i>
            <span>Configuración</span>
        </div>
        <div class="nav-item" onclick="showSection('basedatos')">
            <i class="fas fa-database"></i>
            <span>Base de Datos</span>
        </div>
        <div class="nav-item" onclick="showSection('reportes')">
            <i class="fas fa-chart-line"></i>
            <span>Reportes</span>
        </div>
        <div class="nav-item" onclick="showSection('seguridad')">
            <i class="fas fa-shield-alt"></i>
            <span>Seguridad</span>
        </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="header">
            <h1>Bienvenido, <span>Administrador</span></h1>
            <div class="date-badge">
                <i class="far fa-calendar-alt"></i>
                <span>{{ ahora.split()[0] }}</span>
                <i class="far fa-clock"></i>
                <span>{{ ahora.split()[1] }}</span>
            </div>
        </div>

        <!-- Dashboard Section -->
        <div id="dashboard" class="section active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-info">
                        <h3>Total Detecciones</h3>
                        <div class="number">{{ total }}</div>
                    </div>
                    <div class="stat-icon total"><i class="fas fa-car"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-info">
                        <h3>Aceptadas</h3>
                        <div class="number">{{ aceptadas }}</div>
                    </div>
                    <div class="stat-icon accepted"><i class="fas fa-check-circle"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-info">
                        <h3>Denegadas</h3>
                        <div class="number">{{ denegadas }}</div>
                    </div>
                    <div class="stat-icon denied"><i class="fas fa-times-circle"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-info">
                        <h3>Precisión</h3>
                        <div class="number">{{ precision }}%</div>
                    </div>
                    <div class="stat-icon precision"><i class="fas fa-chart-line"></i></div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-header">
                        <h3><i class="fas fa-chart-bar" style="color: #4ade80;"></i> Detecciones por Día</h3>
                    </div>
                    <canvas id="dailyChart" height="200"></canvas>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <h3><i class="fas fa-chart-pie" style="color: #facc15;"></i> Distribución</h3>
                    </div>
                    <canvas id="pieChart" height="200"></canvas>
                </div>
            </div>

            <div class="filters-bar">
                <div class="search-box">
                    <i class="fas fa-search"></i>
                    <input type="text" id="searchInput" placeholder="Buscar por placa...">
                </div>
                <select class="filter-select" id="estadoFilter">
                    <option value="">Todos los estados</option>
                    <option value="ACEPTADO">Aceptados</option>
                    <option value="DENEGADO">Denegados</option>
                </select>
                <button class="btn-filter" onclick="aplicarFiltros()"><i class="fas fa-filter"></i> Filtrar</button>
                <button class="btn-export" onclick="exportarCSV()"><i class="fas fa-download"></i> Exportar</button>
            </div>

            <div class="table-container">
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Placa</th>
                            <th>Original</th>
                            <th>Fecha</th>
                            <th>Hora</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in datos %}
                        <tr>
                            <td>#{{ row[0] }}</td>
                            <td><strong>{{ row[1] }}</strong></td>
                            <td>{{ row[2] or 'N/A' }}</td>
                            <td>{{ row[3] }}</td>
                            <td>{{ row[4] }}</td>
                            <td>
                                <span class="badge {% if row[5] == 'ACEPTADO' %}accepted{% else %}denied{% endif %}">
                                    {{ row[5] }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Historial Section -->
        <div id="historial" class="section">
            <h2 style="margin-bottom: 20px;">📋 Historial Completo</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Placa</th>
                            <th>Original</th>
                            <th>Fecha</th>
                            <th>Hora</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in datos %}
                        <tr>
                            <td>#{{ row[0] }}</td>
                            <td>{{ row[1] }}</td>
                            <td>{{ row[2] or 'N/A' }}</td>
                            <td>{{ row[3] }}</td>
                            <td>{{ row[4] }}</td>
                            <td>{{ row[5] }}</td>
                            <td>
                                <button class="btn-danger" onclick="eliminarRegistro({{ row[0] }})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Configuración Section -->
        <div id="configuracion" class="section">
            <h2 style="margin-bottom: 20px;">⚙️ Configuración del Sistema</h2>
            <div class="config-grid">
                <div class="config-card">
                    <h3>Placas Autorizadas</h3>
                    <label>Lista de placas (separadas por coma)</label>
                    <input type="text" id="placasAutorizadas" value="JNU540, JNU541, RIU532, XYZ789, JLY246, VEG388, WNU046, BOE074">
                    <button class="btn-save-config" onclick="guardarPlacas()">Guardar Cambios</button>
                </div>
                <div class="config-card">
                    <h3>Configuración de OCR</h3>
                    <label>Idioma</label>
                    <select>
                        <option>Español</option>
                        <option>Inglés</option>
                    </select>
                    <label>Precisión mínima</label>
                    <input type="range" min="0" max="100" value="70">
                </div>
                <div class="config-card">
                    <h3>Base de Datos</h3>
                    <p>Total registros: {{ total }}</p>
                    <p>Tamaño: 1.2 MB</p>
                    <button class="btn-danger" onclick="limpiarBD()">
                        <i class="fas fa-trash"></i> Limpiar Base de Datos
                    </button>
                </div>
            </div>
        </div>

        <!-- Base de Datos Section -->
        <div id="basedatos" class="section">
            <h2 style="margin-bottom: 20px;">🗄️ Gestión de Base de Datos</h2>
            <div class="config-grid">
                <div class="config-card">
                    <h3>Estadísticas de BD</h3>
                    <p>📊 Total registros: {{ total }}</p>
                    <p>✅ Aceptados: {{ aceptadas }}</p>
                    <p>❌ Denegados: {{ denegadas }}</p>
                    <p>📅 Primera detección: 2024-01-15</p>
                    <p>📅 Última detección: {{ ahora.split()[0] }}</p>
                </div>
                <div class="config-card">
                    <h3>Respaldos</h3>
                    <button class="btn-filter" style="width: 100%; margin-bottom: 10px;">
                        <i class="fas fa-download"></i> Descargar Backup
                    </button>
                    <button class="btn-filter" style="width: 100%; background: #3b82f6;">
                        <i class="fas fa-upload"></i> Restaurar Backup
                    </button>
                </div>
                <div class="config-card">
                    <h3>Mantenimiento</h3>
                    <button class="btn-filter" style="width: 100%; margin-bottom: 10px; background: #facc15;">
                        <i class="fas fa-compress"></i> Optimizar Base de Datos
                    </button>
                    <button class="btn-danger" style="width: 100%;">
                        <i class="fas fa-trash"></i> Vaciar Base de Datos
                    </button>
                </div>
            </div>
        </div>

        <!-- Reportes Section -->
        <div id="reportes" class="section">
            <h2 style="margin-bottom: 20px;">📈 Generar Reportes</h2>
            <div class="config-grid">
                <div class="config-card">
                    <h3>Reporte Diario</h3>
                    <p>Genera un reporte de las detecciones del día</p>
                    <button class="btn-filter" style="width: 100%;" onclick="generarReporte('dia')">
                        <i class="fas fa-file-pdf"></i> Generar PDF
                    </button>
                </div>
                <div class="config-card">
                    <h3>Reporte Semanal</h3>
                    <p>Estadísticas de la última semana</p>
                    <button class="btn-filter" style="width: 100%;" onclick="generarReporte('semana')">
                        <i class="fas fa-file-excel"></i> Generar Excel
                    </button>
                </div>
                <div class="config-card">
                    <h3>Reporte Mensual</h3>
                    <p>Análisis completo del mes</p>
                    <button class="btn-filter" style="width: 100%;" onclick="generarReporte('mes')">
                        <i class="fas fa-file-csv"></i> Generar CSV
                    </button>
                </div>
            </div>
        </div>

        <!-- Seguridad Section -->
        <div id="seguridad" class="section">
            <h2 style="margin-bottom: 20px;">🔒 Configuración de Seguridad</h2>
            <div class="config-grid">
                <div class="config-card">
                    <h3>Cambiar Contraseña</h3>
                    <input type="password" placeholder="Contraseña actual">
                    <input type="password" placeholder="Nueva contraseña">
                    <button class="btn-save-config">Actualizar</button>
                </div>
                <div class="config-card">
                    <h3>Logs del Sistema</h3>
                    <p>Últimos accesos:</p>
                    <p>• {{ ahora }} - Acceso exitoso</p>
                    <p>• 2024-03-17 15:30:22 - Acceso exitoso</p>
                    <p>• 2024-03-17 10:15:07 - Acceso exitoso</p>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>PlaceMaster Pro - Sistema Completo de Detección de Placas</p>
        </div>
    </div>

    <script>
        // Cambiar secciones
        function showSection(sectionId) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            
            document.getElementById(sectionId).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // Gráficos
        const ctxBar = document.getElementById('dailyChart').getContext('2d');
        new Chart(ctxBar, {
            type: 'line',
            data: {
                labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
                datasets: [{
                    label: 'Detecciones',
                    data: {{ datos_semana|safe }},
                    borderColor: '#4ade80',
                    backgroundColor: 'rgba(74, 222, 128, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            }
        });

        const ctxPie = document.getElementById('pieChart').getContext('2d');
        new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: ['Aceptadas', 'Denegadas'],
                datasets: [{
                    data: [{{ aceptadas }}, {{ denegadas }}],
                    backgroundColor: ['#4ade80', '#f87171'],
                    borderWidth: 0
                }]
            }
        });

        // Funciones
        function aplicarFiltros() {
            const search = document.getElementById('searchInput').value;
            const estado = document.getElementById('estadoFilter').value;
            
            document.querySelectorAll('#dataTable tbody tr').forEach(row => {
                const placa = row.cells[1].innerText;
                const estadoRow = row.cells[5].innerText;
                let mostrar = true;
                
                if (search && !placa.includes(search.toUpperCase())) mostrar = false;
                if (estado && !estadoRow.includes(estado)) mostrar = false;
                
                row.style.display = mostrar ? '' : 'none';
            });
        }

        function exportarCSV() {
            let csv = "ID,Placa,Original,Fecha,Hora,Estado\\n";
            document.querySelectorAll('#dataTable tbody tr').forEach(row => {
                if (row.style.display !== 'none') {
                    const cols = row.querySelectorAll('td');
                    csv += `${cols[0].innerText},${cols[1].innerText},${cols[2].innerText},${cols[3].innerText},${cols[4].innerText},${cols[5].innerText}\\n`;
                }
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'placas_export.csv';
            a.click();
        }

        function eliminarRegistro(id) {
            if (confirm('¿Eliminar este registro?')) {
                fetch(`/eliminar/${id}`, { method: 'POST' })
                    .then(() => location.reload());
            }
        }

        function guardarPlacas() {
            alert('Configuración guardada');
        }

        function limpiarBD() {
            if (confirm('¿Estás seguro de limpiar toda la base de datos?')) {
                fetch('/limpiar', { method: 'POST' })
                    .then(() => location.reload());
            }
        }

        function generarReporte(tipo) {
            alert(`Generando reporte ${tipo}...`);
        }

        document.getElementById('searchInput')?.addEventListener('keyup', aplicarFiltros);
        document.getElementById('estadoFilter')?.addEventListener('change', aplicarFiltros);
    </script>
</body>
</html>
'''

# ===== RUTAS =====
@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM registros ORDER BY id DESC LIMIT 50")
    datos = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM registros")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM registros WHERE estado='ACEPTADO'")
    aceptadas = cursor.fetchone()[0]
    
    denegadas = total - aceptadas
    precision = round((aceptadas / total * 100), 1) if total > 0 else 0
    
    # Datos para gráfico
    datos_semana = []
    for i in range(7):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM registros WHERE fecha=?", (fecha,))
        datos_semana.append(cursor.fetchone()[0])
    datos_semana.reverse()
    
    conn.close()
    
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template_string(HTML, 
                                 datos=[list(row) for row in datos],
                                 total=total,
                                 aceptadas=aceptadas,
                                 denegadas=denegadas,
                                 precision=precision,
                                 datos_semana=datos_semana,
                                 ahora=ahora)

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    conn = get_db()
    conn.execute("DELETE FROM registros WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/limpiar', methods=['POST'])
def limpiar():
    conn = get_db()
    conn.execute("DELETE FROM registros")
    conn.commit()
    conn.close()
    return '', 204

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌟 PLACEMASTER PRO")
    print("="*60)
    print("🌐 http://localhost:5000")
    print("📊 Dashboard con estadísticas")
    print("📋 Historial funcional")
    print("⚙️ Configuración interactiva")
    print("🗄️ Gestión de Base de Datos")
    print("📈 Reportes")
    print("🔒 Seguridad")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)
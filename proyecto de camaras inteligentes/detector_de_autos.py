import cv2
from ultralytics import YOLO
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ==========================================
class CamaraBase:
    def __init__(self, indice_camara=0):
        self.cap = cv2.VideoCapture(indice_camara)
        if not self.cap.isOpened():
            print("Error: No se pudo acceder a la camara.")
        else:
            print(f"Camara {indice_camara} conectada correctamente.")

    def leer_frame(self):
        ret, frame = self.cap.read()
        return ret, frame

    def apagar(self):
        self.cap.release()
        cv2.destroyAllWindows()
        print("Camara apagada y recursos liberados.")

# ==========================================
class CamaraInteligente(CamaraBase):
    def __init__(self, indice_camara=0, modelo_yolo='yolov8s.pt'):
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado con exito!\n")

        self.clases_objetivo = [2]
        self.confianza        = 0.35

        # ── Estadisticas de sesion ──
        self.id_deteccion      = 0
        self.total_detecciones = 0
        self.fiabilidades      = []
        self.tiempo_inicio     = None
        self.registros = []

    # ──────────────────────────────────────────
    # Genera el PDF al cerrar el sistema
    # ──────────────────────────────────────────
    def _generar_pdf(self):
        """Construye un PDF profesional con todos los registros de la sesion."""

        ts     = time.strftime("%Y%m%d_%H%M%S")
        nombre = f"reporte_gts_{ts}.pdf"

        doc = SimpleDocTemplate(
            nombre,
            pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm,   bottomMargin=1.5*cm
        )

        estilos  = getSampleStyleSheet()
        azul_osc = colors.HexColor("#1A56A8")
        azul_med = colors.HexColor("#2E75D4")
        gris_cla = colors.HexColor("#F4F6F9")
        blanco   = colors.white

        # ── Estilos de texto ──
        estilo_titulo = ParagraphStyle(
            "titulo",
            parent=estilos["Title"],
            fontSize=18,
            textColor=blanco,
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName="Helvetica-Bold"
        )
        estilo_subtitulo = ParagraphStyle(
            "subtitulo",
            parent=estilos["Normal"],
            fontSize=10,
            textColor=blanco,
            alignment=TA_CENTER,
            fontName="Helvetica"
        )
        estilo_seccion = ParagraphStyle(
            "seccion",
            parent=estilos["Normal"],
            fontSize=11,
            textColor=azul_osc,
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6
        )
        estilo_normal = ParagraphStyle(
            "normal_custom",
            parent=estilos["Normal"],
            fontSize=9,
            fontName="Helvetica"
        )

        elementos = []

        # ════════════════════════════════
        # ENCABEZADO
        # ════════════════════════════════
        fecha_reporte = time.strftime("%d/%m/%Y  %H:%M:%S")
        duracion      = int(time.time() - self.tiempo_inicio)
        promedio_fiab = (sum(self.fiabilidades) / len(self.fiabilidades)
                         if self.fiabilidades else 0)

        encabezado = Table(
            [[Paragraph("GTS VIAL — Sistema de Detección Vehicular IA", estilo_titulo)],
             [Paragraph(f"Reporte de Sesión  ·  Generado: {fecha_reporte}", estilo_subtitulo)]],
            colWidths=[18*cm]
        )
        encabezado.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), azul_osc),
            ("ROUNDEDCORNERS", [8]),
            ("TOPPADDING",    (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))
        elementos.append(encabezado)
        elementos.append(Spacer(1, 0.5*cm))

        # ════════════════════════════════
        # TARJETAS DE RESUMEN
        # ════════════════════════════════
        elementos.append(Paragraph("Resumen de Sesión", estilo_seccion))

        estilo_val  = ParagraphStyle("val",  parent=estilos["Normal"],
                                     fontSize=20, fontName="Helvetica-Bold",
                                     textColor=azul_osc, alignment=TA_CENTER)
        estilo_etiq = ParagraphStyle("etiq", parent=estilos["Normal"],
                                     fontSize=8,  fontName="Helvetica",
                                     textColor=colors.HexColor("#6B7280"),
                                     alignment=TA_CENTER)

        mins = duracion // 60
        segs = duracion % 60

        tarjetas = Table(
            [[
                Paragraph(str(self.total_detecciones),    estilo_val),
                Paragraph(f"{promedio_fiab:.1f}%",        estilo_val),
                Paragraph(f"{mins:02d}:{segs:02d}",       estilo_val),
                Paragraph(f"#{self.id_deteccion:04d}",    estilo_val),
            ],[
                Paragraph("Autos Detectados",             estilo_etiq),
                Paragraph("Fiabilidad Promedio",          estilo_etiq),
                Paragraph("Duración (min:seg)",           estilo_etiq),
                Paragraph("Último ID",                    estilo_etiq),
            ]],
            colWidths=[4.4*cm, 4.4*cm, 4.4*cm, 4.4*cm]
        )
        tarjetas.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), gris_cla),
            ("LINEBELOW",     (0,0), (-1,0),  0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("RIGHTPADDING",  (0,0), (-1,-1), 6),
            ("ROUNDEDCORNERS",[6]),
            ("LINEAFTER",     (0,0), (2,1),   0.5, colors.HexColor("#D1D5DB")),
        ]))
        elementos.append(tarjetas)
        elementos.append(Spacer(1, 0.5*cm))

        # ════════════════════════════════
        # TABLA DE DETECCIONES
        # ════════════════════════════════
        elementos.append(Paragraph("Registro Detallado de Detecciones", estilo_seccion))

        if not self.registros:
            elementos.append(
                Paragraph("No se registraron detecciones en esta sesión.", estilo_normal)
            )
        else:
            # Encabezado de la tabla
            cabecera = ["ID", "Día", "Fecha", "Hora", "Fiabilidad", "Nivel", "Modelo IA"]

            estilo_cab = ParagraphStyle("cab", parent=estilos["Normal"],
                                        fontSize=9, fontName="Helvetica-Bold",
                                        textColor=blanco, alignment=TA_CENTER)
            cabecera_p = [Paragraph(c, estilo_cab) for c in cabecera]

            # Colores por nivel
            COLOR_ALTA  = colors.HexColor("#D1FAE5")
            COLOR_MEDIA = colors.HexColor("#FEF9C3")
            COLOR_BAJA  = colors.HexColor("#FEE2E2")

            filas = [cabecera_p]
            for r in self.registros:
                estilo_celda = ParagraphStyle(
                    "celda", parent=estilos["Normal"],
                    fontSize=8, fontName="Helvetica", alignment=TA_CENTER
                )
                fila = [Paragraph(str(v), estilo_celda) for v in r]
                filas.append(fila)

            tabla = Table(
                filas,
                colWidths=[1.8*cm, 2.4*cm, 2.6*cm, 2.2*cm, 2.4*cm, 2.4*cm, 2.2*cm],
                repeatRows=1
            )

            # Estilo base
            t_estilo = TableStyle([
                # Encabezado
                ("BACKGROUND",    (0,0), (-1,0),  azul_med),
                ("TEXTCOLOR",     (0,0), (-1,0),  blanco),
                ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,0),  9),
                ("TOPPADDING",    (0,0), (-1,0),  8),
                ("BOTTOMPADDING", (0,0), (-1,0),  8),
                # Filas de datos
                ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
                ("FONTSIZE",      (0,1), (-1,-1), 8),
                ("TOPPADDING",    (0,1), (-1,-1), 5),
                ("BOTTOMPADDING", (0,1), (-1,-1), 5),
                ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                # Bordes
                ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#E5E7EB")),
                ("LINEBELOW",     (0,0), (-1,0),  1,   azul_osc),
            ])

            # Color de fila segun nivel
            for i, registro in enumerate(self.registros, start=1):
                nivel = registro[5]  # columna "Nivel"
                if nivel == "ALTA":
                    color_fila = COLOR_ALTA
                elif nivel == "MEDIA":
                    color_fila = COLOR_MEDIA
                else:
                    color_fila = COLOR_BAJA
                # Filas alternas mas oscuras para legibilidad
                if i % 2 == 0:
                    t_estilo.add("BACKGROUND", (0,i), (-1,i), color_fila)
                else:
                    t_estilo.add("BACKGROUND", (0,i), (-1,i),
                                 colors.HexColor("#FFFFFF"))

            tabla.setStyle(t_estilo)
            elementos.append(tabla)

        elementos.append(Spacer(1, 0.5*cm))

        # ════════════════════════════════
        # PIE DE PÁGINA
        # ════════════════════════════════
        estilo_pie = ParagraphStyle("pie", parent=estilos["Normal"],
                                    fontSize=8, textColor=colors.HexColor("#9CA3AF"),
                                    alignment=TA_CENTER)
        elementos.append(Spacer(1, 0.3*cm))
        elementos.append(Paragraph(
            f"GTS Vial · Nodo de Detección Edge  ·  Modelo YOLOv8s  ·  "
            f"Confianza mínima: {int(self.confianza*100)}%  ·  {fecha_reporte}",
            estilo_pie
        ))

        # ── Construir y guardar ──
        doc.build(elementos)
        print(f"\n  PDF generado: {nombre}")
        print(f"  Abrelo desde la carpeta del script.")
        return nombre

    # ──────────────────────────────────────────
    # Dibuja recuadros personalizados
    # ──────────────────────────────────────────
    def dibujar_recuadros(self, frame, resultados):
        for box in resultados[0].boxes:
            confianza_val = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            if confianza_val >= 0.80:
                color = (0, 220, 0)
            elif confianza_val >= 0.50:
                color = (0, 180, 80)
            else:
                color = (0, 200, 200)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            etiqueta = f"Auto  {confianza_val*100:.1f}%"
            (ancho_txt, alto_txt), _ = cv2.getTextSize(
                etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, y1 - alto_txt - 8),
                          (x1 + ancho_txt + 6, y1), color, -1)
            cv2.putText(frame, etiqueta, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        return frame

    # ──────────────────────────────────────────
    # Panel de estado en pantalla
    # ──────────────────────────────────────────
    def dibujar_panel_estado(self, frame, detecciones_frame, fps):
        tiempo_activo = int(time.time() - self.tiempo_inicio)
        minutos  = tiempo_activo // 60
        segundos = tiempo_activo % 60

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (340, 80), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        cv2.putText(frame,
                    f"Autos en pantalla: {detecciones_frame}   |   Total sesion: {self.total_detecciones}",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        cv2.putText(frame,
                    f"FPS: {fps:.1f}   |   Tiempo activo: {minutos:02d}:{segundos:02d}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame,
                    f"Confianza minima: {int(self.confianza*100)}%   |   ID siguiente: #{self.id_deteccion + 1}",
                    (10, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)
        return frame

    # ──────────────────────────────────────────
    # Bucle principal
    # ──────────────────────────────────────────
    def iniciar_monitoreo(self):
        self.tiempo_inicio = time.time()

        print("=" * 60)
        print("  SISTEMA GTS VIAL - NODO DE DETECCION ACTIVO")
        print("  Detectando: Autos  |  Modelo: YOLOv8s")
        print("  Al presionar Q se generara el PDF automaticamente")
        print("=" * 60)

        tiempo_anterior = time.time()

        while self.cap.isOpened():
            exito, frame = self.leer_frame()
            if not exito:
                print("Se perdio la senal de la camara.")
                break

            resultados = self.modelo(
                frame,
                classes=self.clases_objetivo,
                conf=self.confianza,
                verbose=False
            )

            detecciones_frame = len(resultados[0].boxes)

            if detecciones_frame > 0:
                ahora      = time.localtime()
                dias       = ["Lunes","Martes","Miercoles","Jueves",
                              "Viernes","Sabado","Domingo"]
                dia_semana = dias[ahora.tm_wday]
                fecha      = f"{ahora.tm_mday:02d}/{ahora.tm_mon:02d}/{ahora.tm_year}"
                hora       = f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}:{ahora.tm_sec:02d}"

                for conf_val in resultados[0].boxes.conf.tolist():
                    self.id_deteccion      += 1
                    self.total_detecciones += 1
                    pct = round(conf_val * 100, 1)
                    self.fiabilidades.append(pct)

                    if pct >= 80:
                        nivel = "ALTA"
                    elif pct >= 50:
                        nivel = "MEDIA"
                    else:
                        nivel = "BAJA"

                    # Guardar en lista para el PDF
                    self.registros.append([
                        f"#{self.id_deteccion:04d}",
                        dia_semana, fecha, hora,
                        f"{pct}%", nivel, "YOLOv8s"
                    ])

                    print(f"  [#{self.id_deteccion:04d}] {fecha} {hora}  |  {pct}%  {nivel}")

            frame = self.dibujar_recuadros(frame, resultados)

            tiempo_actual   = time.time()
            fps             = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            frame = self.dibujar_panel_estado(frame, detecciones_frame, fps)
            cv2.imshow('GTS Vial - Nodo de Deteccion', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ── Resumen y generar PDF ──
        duracion_total = int(time.time() - self.tiempo_inicio)
        promedio_fiab  = (sum(self.fiabilidades) / len(self.fiabilidades)
                          if self.fiabilidades else 0)

        print("\n" + "=" * 60)
        print("  RESUMEN DE SESION")
        print(f"  Duracion total         : {duracion_total // 60:02d} min {duracion_total % 60:02d} seg")
        print(f"  Total autos registrados: {self.total_detecciones}")
        print(f"  Fiabilidad promedio    : {promedio_fiab:.1f}%")
        print(f"  Ultimo ID registrado   : #{self.id_deteccion:04d}")
        print("=" * 60)
        print("\n  Generando PDF...")

        self._generar_pdf()
        self.apagar()
# ==========================================
if __name__ == "__main__":
    nodo_edge_01 = CamaraInteligente(indice_camara=0)
    nodo_edge_01.iniciar_monitoreo()

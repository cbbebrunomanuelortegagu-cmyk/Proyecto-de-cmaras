import cv2
from ultralytics import YOLO
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


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


class CamaraInteligente(CamaraBase):
    def __init__(self, indice_camara=0, modelo_yolo='yolov8s.pt'):
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado con exito!\n")

        self.clases_objetivo = [2, 3, 5, 7]
        self.confianza        = 0.35

        self.etiquetas = {2: "Auto", 3: "Moto", 5: "Bus", 7: "Camion"}

        self.colores_tipo = {
            "Auto":   (0, 220, 0),    # Verde
            "Moto":   (0, 180, 255),  # Naranja
            "Bus":    (255, 80, 80),  # Azul
            "Camion": (180, 0, 255),  # Morado
        }

        self.id_deteccion      = 0
        self.total_detecciones = 0
        self.fiabilidades      = []
        self.tiempo_inicio     = None
        self.conteo_por_tipo   = {"Auto": 0, "Moto": 0, "Bus": 0, "Camion": 0}

        self.registros = []


    def _generar_pdf(self):
        ts     = time.strftime("%Y%m%d_%H%M%S")
        nombre = f"reporte_gts_{ts}.pdf"

        doc = SimpleDocTemplate(
            nombre, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm,   bottomMargin=1.5*cm
        )

        estilos  = getSampleStyleSheet()
        azul_osc = colors.HexColor("#1A56A8")
        azul_med = colors.HexColor("#2E75D4")
        gris_cla = colors.HexColor("#F4F6F9")
        blanco   = colors.white

        estilo_titulo = ParagraphStyle(
            "titulo", parent=estilos["Title"],
            fontSize=18, textColor=blanco,
            alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold"
        )
        estilo_subtitulo = ParagraphStyle(
            "subtitulo", parent=estilos["Normal"],
            fontSize=10, textColor=blanco,
            alignment=TA_CENTER, fontName="Helvetica"
        )
        estilo_seccion = ParagraphStyle(
            "seccion", parent=estilos["Normal"],
            fontSize=11, textColor=azul_osc,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6
        )
        estilo_normal = ParagraphStyle(
            "normal_custom", parent=estilos["Normal"],
            fontSize=9, fontName="Helvetica"
        )

        elementos = []
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
            ("BACKGROUND",    (0,0), (-1,-1), azul_osc),
            ("TOPPADDING",    (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))
        elementos.append(encabezado)
        elementos.append(Spacer(1, 0.5*cm))

        elementos.append(Paragraph("Resumen de Sesión", estilo_seccion))
        estilo_val  = ParagraphStyle("val",  parent=estilos["Normal"],
                                     fontSize=20, fontName="Helvetica-Bold",
                                     textColor=azul_osc, alignment=TA_CENTER)
        estilo_etiq = ParagraphStyle("etiq", parent=estilos["Normal"],
                                     fontSize=8, fontName="Helvetica",
                                     textColor=colors.HexColor("#6B7280"),
                                     alignment=TA_CENTER)
        mins = duracion // 60
        segs = duracion % 60

        tarjetas = Table([[
            Paragraph(str(self.total_detecciones), estilo_val),
            Paragraph(f"{promedio_fiab:.1f}%",     estilo_val),
            Paragraph(f"{mins:02d}:{segs:02d}",    estilo_val),
            Paragraph(f"#{self.id_deteccion:04d}", estilo_val),
        ],[
            Paragraph("Vehículos Detectados",      estilo_etiq),
            Paragraph("Fiabilidad Promedio",        estilo_etiq),
            Paragraph("Duración (min:seg)",         estilo_etiq),
            Paragraph("Último ID",                  estilo_etiq),
        ]], colWidths=[4.4*cm]*4)
        tarjetas.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), gris_cla),
            ("LINEBELOW",     (0,0), (-1,0),  0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LINEAFTER",     (0,0), (2,1),   0.5, colors.HexColor("#D1D5DB")),
        ]))
        elementos.append(tarjetas)
        elementos.append(Spacer(1, 0.4*cm))

        # ── Desglose por tipo de vehiculo ──
        elementos.append(Paragraph("Desglose por Tipo de Vehículo", estilo_seccion))

        estilo_tipo_val  = ParagraphStyle("tv", parent=estilos["Normal"],
                                          fontSize=16, fontName="Helvetica-Bold",
                                          alignment=TA_CENTER)
        estilo_tipo_etiq = ParagraphStyle("te", parent=estilos["Normal"],
                                          fontSize=8, fontName="Helvetica",
                                          textColor=colors.HexColor("#6B7280"),
                                          alignment=TA_CENTER)

        COLOR_AUTO   = colors.HexColor("#D1FAE5")
        COLOR_MOTO   = colors.HexColor("#FEF3C7")
        COLOR_BUS    = colors.HexColor("#DBEAFE")
        COLOR_CAMION = colors.HexColor("#EDE9FE")

        desglose = Table([[
            Paragraph(str(self.conteo_por_tipo["Auto"]),   estilo_tipo_val),
            Paragraph(str(self.conteo_por_tipo["Moto"]),   estilo_tipo_val),
            Paragraph(str(self.conteo_por_tipo["Bus"]),    estilo_tipo_val),
            Paragraph(str(self.conteo_por_tipo["Camion"]), estilo_tipo_val),
        ],[
            Paragraph("🚗 Autos",    estilo_tipo_etiq),
            Paragraph("🏍 Motos",    estilo_tipo_etiq),
            Paragraph("🚌 Buses",    estilo_tipo_etiq),
            Paragraph("🚛 Camiones", estilo_tipo_etiq),
        ]], colWidths=[4.4*cm]*4)
        desglose.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,1), COLOR_AUTO),
            ("BACKGROUND",    (1,0), (1,1), COLOR_MOTO),
            ("BACKGROUND",    (2,0), (2,1), COLOR_BUS),
            ("BACKGROUND",    (3,0), (3,1), COLOR_CAMION),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LINEAFTER",     (0,0), (2,1),   0.5, colors.HexColor("#D1D5DB")),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#E5E7EB")),
        ]))
        elementos.append(desglose)
        elementos.append(Spacer(1, 0.4*cm))

        elementos.append(Paragraph("Registro Detallado de Detecciones", estilo_seccion))

        if not self.registros:
            elementos.append(
                Paragraph("No se registraron detecciones en esta sesión.", estilo_normal)
            )
        else:
            cabecera  = ["ID", "Día", "Fecha", "Hora", "Tipo", "Fiabilidad", "Nivel"]
            estilo_cab = ParagraphStyle("cab", parent=estilos["Normal"],
                                        fontSize=9, fontName="Helvetica-Bold",
                                        textColor=blanco, alignment=TA_CENTER)
            cabecera_p = [Paragraph(c, estilo_cab) for c in cabecera]

            filas = [cabecera_p]
            for r in self.registros:
                estilo_celda = ParagraphStyle("celda", parent=estilos["Normal"],
                                              fontSize=8, fontName="Helvetica",
                                              alignment=TA_CENTER)
                filas.append([Paragraph(str(v), estilo_celda) for v in r])

            tabla = Table(
                filas,
                colWidths=[1.6*cm, 2.3*cm, 2.4*cm, 2.0*cm, 2.2*cm, 2.4*cm, 2.1*cm],
                repeatRows=1
            )

            t_estilo = TableStyle([
                ("BACKGROUND",    (0,0), (-1,0),  azul_med),
                ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,0),  9),
                ("TOPPADDING",    (0,0), (-1,0),  8),
                ("BOTTOMPADDING", (0,0), (-1,0),  8),
                ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
                ("FONTSIZE",      (0,1), (-1,-1), 8),
                ("TOPPADDING",    (0,1), (-1,-1), 5),
                ("BOTTOMPADDING", (0,1), (-1,-1), 5),
                ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#E5E7EB")),
                ("LINEBELOW",     (0,0), (-1,0),  1,   azul_osc),
                ("ROWBACKGROUNDS",(0,1), (-1,-1),
                 [colors.white, colors.HexColor("#F8FAFC")]),
            ])
            tabla.setStyle(t_estilo)
            elementos.append(tabla)

        # ── Pie de pagina ──
        elementos.append(Spacer(1, 0.4*cm))
        estilo_pie = ParagraphStyle("pie", parent=estilos["Normal"],
                                    fontSize=8, textColor=colors.HexColor("#9CA3AF"),
                                    alignment=TA_CENTER)
        elementos.append(Paragraph(
            f"GTS Vial  ·  Modelo YOLOv8s  ·  "
            f"Vehículos detectados: Auto / Moto / Bus / Camión  ·  "
            f"Confianza mínima: {int(self.confianza*100)}%  ·  {fecha_reporte}",
            estilo_pie
        ))

        doc.build(elementos)
        print(f"\n  PDF generado: {nombre}")
        return nombre

    def dibujar_recuadros(self, frame, resultados):
        for box in resultados[0].boxes:
            confianza_val = float(box.conf[0])
            clase_id      = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            tipo  = self.etiquetas.get(clase_id, "Vehiculo")
            color = self.colores_tipo.get(tipo, (200, 200, 200))

            # Recuadro mas grueso segun tipo
            grosor = 3 if tipo in ("Bus", "Camion") else 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, grosor)

            etiqueta = f"{tipo}  {confianza_val*100:.1f}%"
            (ancho_txt, alto_txt), _ = cv2.getTextSize(
                etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, y1 - alto_txt - 8),
                          (x1 + ancho_txt + 6, y1), color, -1)
            cv2.putText(frame, etiqueta, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        return frame


    def dibujar_panel_estado(self, frame, detecciones_frame, fps):
        tiempo_activo = int(time.time() - self.tiempo_inicio)
        minutos  = tiempo_activo // 60
        segundos = tiempo_activo % 60

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (420, 95), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        cv2.putText(frame,
                    f"Vehiculos en pantalla: {detecciones_frame}   |   Total sesion: {self.total_detecciones}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        cv2.putText(frame,
                    f"FPS: {fps:.1f}   |   Tiempo activo: {minutos:02d}:{segundos:02d}",
                    (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        # Desglose por tipo en una sola linea
        cv2.putText(frame,
                    f"Autos:{self.conteo_por_tipo['Auto']}  "
                    f"Motos:{self.conteo_por_tipo['Moto']}  "
                    f"Buses:{self.conteo_por_tipo['Bus']}  "
                    f"Camiones:{self.conteo_por_tipo['Camion']}",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 220, 255), 1)
        cv2.putText(frame,
                    f"Confianza minima: {int(self.confianza*100)}%   |   ID siguiente: #{self.id_deteccion + 1}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)
        return frame

    def iniciar_monitoreo(self):
        self.tiempo_inicio = time.time()

        print("=" * 65)
        print("  SISTEMA GTS VIAL - NODO DE DETECCION ACTIVO")
        print("  Detectando: Auto | Moto | Bus | Camion")
        print("  Al presionar Q se generara el PDF automaticamente")
        print("=" * 65)

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

                for box in resultados[0].boxes:
                    conf_val = float(box.conf[0])
                    clase_id = int(box.cls[0])
                    tipo     = self.etiquetas.get(clase_id, "Vehiculo")

                    self.id_deteccion      += 1
                    self.total_detecciones += 1
                    pct = round(conf_val * 100, 1)
                    self.fiabilidades.append(pct)
                    self.conteo_por_tipo[tipo] += 1

                    nivel = "ALTA" if pct >= 80 else ("MEDIA" if pct >= 50 else "BAJA")

                    self.registros.append([
                        f"#{self.id_deteccion:04d}",
                        dia_semana, fecha, hora,
                        tipo, f"{pct}%", nivel
                    ])

                    print(f"  [#{self.id_deteccion:04d}] {fecha} {hora}"
                          f"  |  {tipo:<8}  {pct:5.1f}%  {nivel}")

            frame = self.dibujar_recuadros(frame, resultados)

            tiempo_actual   = time.time()
            fps             = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            frame = self.dibujar_panel_estado(frame, detecciones_frame, fps)
            cv2.imshow('GTS Vial - Nodo de Deteccion', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ── Resumen final ──
        duracion_total = int(time.time() - self.tiempo_inicio)
        promedio_fiab  = (sum(self.fiabilidades) / len(self.fiabilidades)
                          if self.fiabilidades else 0)

        print("\n" + "=" * 65)
        print("  RESUMEN DE SESION")
        print(f"  Duracion total    : {duracion_total // 60:02d} min {duracion_total % 60:02d} seg")
        print(f"  Total vehiculos   : {self.total_detecciones}")
        print(f"  Fiabilidad prom.  : {promedio_fiab:.1f}%")
        print(f"  Autos   : {self.conteo_por_tipo['Auto']:<4}  "
              f"Motos  : {self.conteo_por_tipo['Moto']}")
        print(f"  Buses   : {self.conteo_por_tipo['Bus']:<4}  "
              f"Camiones: {self.conteo_por_tipo['Camion']}")
        print("=" * 65)
        print("\n  Generando PDF...")

        self._generar_pdf()
        self.apagar()

if __name__ == "__main__":
    nodo_edge_01 = CamaraInteligente(indice_camara=0)
    nodo_edge_01.iniciar_monitoreo()

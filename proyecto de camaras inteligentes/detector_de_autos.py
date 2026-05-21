import cv2
from ultralytics import YOLO
import time

# ==========================================
# CLASE PADRE: Manejo basico de hardware
# ==========================================
class CamaraBase:
    def __init__(self, indice_camara=0):
        """Inicializa la conexion fisica con la camara."""
        self.cap = cv2.VideoCapture(indice_camara)
        if not self.cap.isOpened():
            print("Error: No se pudo acceder a la camara.")
        else:
            print(f"Camara {indice_camara} conectada correctamente.")

    def leer_frame(self):
        """Lee un solo fotograma del video."""
        ret, frame = self.cap.read()
        return ret, frame

    def apagar(self):
        """Libera la camara y cierra las ventanas."""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Camara apagada y recursos liberados.")


# ==========================================
# CLASE HIJA: Hereda la camara y le suma IA (YOLO)
# ==========================================
class CamaraInteligente(CamaraBase):
    def __init__(self, indice_camara=0, modelo_yolo='yolov8s.pt'):
        """
        HERENCIA: Llama al constructor del padre y carga el modelo IA.
        Usamos 'yolov8s.pt' (Small) en vez de Nano, detecta mejor objetos
        pequeños como autos de juguete o autos en pantalla de celular.
        """
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado con exito!\n")


        self.clases_objetivo = [2] 

        self.confianza = 0.35

        self.total_detecciones = 0

    def iniciar_monitoreo(self):
        """Bucle principal que captura, procesa y muestra el video."""
        print("=" * 55)
        print("  MONITOREO INICIADO - Solo detectando AUTOS")
        print("  Presiona Q para apagar el sistema")
        print("=" * 55)

        tiempo_anterior = time.time()

        while self.cap.isOpened():
            exito, frame = self.leer_frame()
            if not exito:
                print("Se perdio la senal de la camara.")
                break

            # ── 1. Procesar con YOLO (solo autos, baja confianza para pruebas) ──
            resultados = self.modelo(
                frame,
                classes=self.clases_objetivo,
                conf=self.confianza,
                verbose=False
            )

            # ── 2. Contar cuantos autos detecto en este frame ──
            detecciones_frame = len(resultados[0].boxes)

            # ── 3. Imprimir en terminal con fecha, hora y fiabilidad ──
            if detecciones_frame > 0:
                self.total_detecciones += detecciones_frame

                ahora      = time.localtime()
                dias       = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
                dia_semana = dias[ahora.tm_wday]
                fecha      = f"{ahora.tm_mday:02d}/{ahora.tm_mon:02d}/{ahora.tm_year}"
                hora       = f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}:{ahora.tm_sec:02d}"
                fiabilidad = [f"{round(float(c)*100, 1)}%" for c in resultados[0].boxes.conf.tolist()]

                print(f"[DETECCION]  {dia_semana} {fecha}  {hora}"
                      f"  |  Autos: {detecciones_frame}"
                      f"  |  Fiabilidad: {fiabilidad}")

            # ── 4. Dibujar los recuadros sobre el frame ──
            frame_procesado = resultados[0].plot()

            # ── 5. Calcular FPS para ver si corre fluido ──
            tiempo_actual = time.time()
            fps = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            # ── 6. Agregar texto de estado en la pantalla ──
            overlay = frame_procesado.copy()
            cv2.rectangle(overlay, (0, 0), (320, 70), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame_procesado, 0.5, 0, frame_procesado)

            cv2.putText(frame_procesado,
                        f"Autos detectados: {detecciones_frame}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.putText(frame_procesado,
                        f"FPS: {fps:.1f}  |  Confianza min: {self.confianza}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # ── 7. Mostrar ventana ──
            cv2.imshow('GTS Vial - Detector de Autos (prueba)', frame_procesado)

            # ── 8. Salir con Q ──
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        print("\n" + "=" * 55)
        print(f"  SESION TERMINADA")
        print(f"  Total de detecciones en esta sesion: {self.total_detecciones}")
        print("=" * 55)

        self.apagar()


# ==========================================
# EJECUCION DEL PROGRAMA
# ==========================================
if __name__ == "__main__":
    nodo_edge_01 = CamaraInteligente(indice_camara=0)
    nodo_edge_01.iniciar_monitoreo()

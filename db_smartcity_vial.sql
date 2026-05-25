-- ==============================================================================
-- SISTEMA DE FISCALIZACIÓN VIAL IA (SMART CITY) - BOLIVIA
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS db_smartcity_vial
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE db_smartcity_vial;

-- ==============================================================================
-- BLOQUE 1: SEGURIDAD Y CONTROL DE ACCESOS
-- ==============================================================================

CREATE TABLE usuarios (
    id_usuario       INT AUTO_INCREMENT PRIMARY KEY,
    credencial       VARCHAR(50)  NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,          -- En producción: SHA-256 o bcrypt
    nombre_completo  VARCHAR(100) NOT NULL,
    rol              ENUM('Administrador','Operador') DEFAULT 'Operador',
    estado           ENUM('Activo','Inactivo')        DEFAULT 'Activo',
    ultimo_acceso    DATETIME                         DEFAULT NULL,
    fecha_creacion   TIMESTAMP                        DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='Operadores y administradores del sistema';

-- Índice para login rápido
CREATE INDEX idx_usuarios_credencial ON usuarios(credencial);

-- ==============================================================================
-- BLOQUE 2: INFRAESTRUCTURA EDGE COMPUTING
-- ==============================================================================

CREATE TABLE nodos_edge (
    id_nodo              INT AUTO_INCREMENT PRIMARY KEY,
    nombre_identificador VARCHAR(100) NOT NULL,
    ubicacion_fisica     VARCHAR(255) NOT NULL,
    direccion_ip         VARCHAR(45)  NOT NULL,       -- IPv4 e IPv6
    estado_conexion      ENUM('Online','Offline','Mantenimiento') DEFAULT 'Online',
    umbral_ia            DECIMAL(5,2) DEFAULT 85.00,  -- Confianza mínima para disparar alerta
    ultima_actividad     DATETIME     DEFAULT NULL,   -- Último frame procesado
    fecha_instalacion    DATE         DEFAULT NULL,
    UNIQUE (direccion_ip)
) ENGINE=InnoDB COMMENT='Cámaras y nodos de procesamiento en campo';

-- ==============================================================================
-- BLOQUE 3: PADRÓN AUTOMOTOR
-- ==============================================================================

CREATE TABLE propietarios (
    ci_propietario      VARCHAR(20)  PRIMARY KEY,
    nombre_completo     VARCHAR(150) NOT NULL,
    correo_electronico  VARCHAR(100) DEFAULT NULL,
    telefono            VARCHAR(20)  DEFAULT NULL,
    direccion_domicilio VARCHAR(255) DEFAULT NULL,
    fecha_registro      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='Propietarios registrados en el padrón automotor';

CREATE TABLE vehiculos (
    placa              VARCHAR(15) PRIMARY KEY,
    ci_propietario_fk  VARCHAR(20) NOT NULL,
    marca              VARCHAR(50) NOT NULL,
    modelo             VARCHAR(50) DEFAULT NULL,
    anio               YEAR        DEFAULT NULL,
    color              VARCHAR(30) DEFAULT NULL,
    tipo_vehiculo      ENUM('Auto','Camioneta','Bus','Minibus','Motocicleta','Camión') DEFAULT 'Auto',
    estado_vehiculo    ENUM('Activo','Baja','Robado') DEFAULT 'Activo',
    FOREIGN KEY (ci_propietario_fk)
        REFERENCES propietarios(ci_propietario)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Padrón de vehículos registrados';

CREATE INDEX idx_vehiculos_propietario ON vehiculos(ci_propietario_fk);

-- =============================================================================
-- BLOQUE 4: CATÁLOGO DE FALTAS Y TARIFAS
-- ==============================================================================

CREATE TABLE tipos_falta (
    id_tipo_falta   INT AUTO_INCREMENT PRIMARY KEY,
    nombre_falta    VARCHAR(100)   NOT NULL UNIQUE,  -- Ej: 'Semáforo en Rojo'
    descripcion     TEXT           DEFAULT NULL,
    monto_multa_bs  DECIMAL(10,2)  NOT NULL,          -- Monto en Bolivianos
    gravedad        ENUM('Leve','Grave','Muy Grave')  DEFAULT 'Grave',
    activo          TINYINT(1)     DEFAULT 1
) ENGINE=InnoDB COMMENT='Catálogo oficial de faltas de tránsito y sus multas';


-- ==============================================================================
-- BLOQUE 5: CORE DE INTELIGENCIA ARTIFICIAL Y EVIDENCIAS
-- ==============================================================================

CREATE TABLE infracciones_ia (
    id_infraccion     VARCHAR(20)  PRIMARY KEY,
    id_nodo_fk        INT          NOT NULL,
    id_tipo_falta_fk  INT          NOT NULL,
    placa_detectada   VARCHAR(15)  NOT NULL,
    fecha_hora        DATETIME     NOT NULL,
    confianza_ia      DECIMAL(5,2) NOT NULL,
    ruta_imagen       VARCHAR(255) NOT NULL,
    hash_evidencia    VARCHAR(128) NOT NULL,
    estado_revision   ENUM('Pendiente','Aprobada','Descartada') DEFAULT 'Pendiente',
    fecha_revision    DATETIME     DEFAULT NULL,
    id_revisor_fk     INT          DEFAULT NULL,
    FOREIGN KEY (id_nodo_fk)
        REFERENCES nodos_edge(id_nodo)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_tipo_falta_fk)
        REFERENCES tipos_falta(id_tipo_falta)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_revisor_fk)
        REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Infracciones detectadas automáticamente por la IA';

-- Índices para filtros frecuentes del panel web
CREATE INDEX idx_infracciones_estado   ON infracciones_ia(estado_revision);
CREATE INDEX idx_infracciones_fecha    ON infracciones_ia(fecha_hora);
CREATE INDEX idx_infracciones_placa    ON infracciones_ia(placa_detectada);

-- ==============================================================================
-- BLOQUE 6: EMISIÓN DE BOLETAS OFICIALES
-- ==============================================================================

CREATE TABLE boletas_oficiales (
    id_boleta               INT AUTO_INCREMENT PRIMARY KEY,
    id_infraccion_fk        VARCHAR(20)   NOT NULL UNIQUE,  -- 1 boleta por infracción
    id_usuario_validador_fk INT           NOT NULL,
    fecha_emision           DATETIME      DEFAULT CURRENT_TIMESTAMP,
    monto_multa_bs          DECIMAL(10,2) NOT NULL,
    estado_pago             ENUM('No Pagado','Pagado','Apelación','Anulado') DEFAULT 'No Pagado',
    fecha_vencimiento       DATE          DEFAULT NULL,     -- Plazo límite para pagar
    fecha_pago              DATETIME      DEFAULT NULL,
    ruta_pdf                VARCHAR(255)  DEFAULT NULL,
    FOREIGN KEY (id_infraccion_fk)
        REFERENCES infracciones_ia(id_infraccion)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_usuario_validador_fk)
        REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Boletas de multa oficialmente emitidas';

CREATE INDEX idx_boletas_estado_pago ON boletas_oficiales(estado_pago);

-- ==============================================================================
-- BLOQUE 7: NOTIFICACIONES AL PROPIETARIO
-- ==============================================================================

CREATE TABLE notificaciones (
    id_notificacion  INT AUTO_INCREMENT PRIMARY KEY,
    id_boleta_fk     INT          NOT NULL,
    canal_envio      ENUM('Email','SMS','Ambos') DEFAULT 'Email',
    estado_envio     ENUM('Enviado','Fallido','Pendiente') DEFAULT 'Pendiente',
    fecha_envio      DATETIME     DEFAULT NULL,
    detalle_error    TEXT         DEFAULT NULL,  -- Si fallo, ¿por qué?
    FOREIGN KEY (id_boleta_fk)
        REFERENCES boletas_oficiales(id_boleta)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Historial de notificaciones enviadas a los propietarios';

-- ==============================================================================
-- BLOQUE 8: AUDITORÍA DEL SISTEMA
-- ==============================================================================

CREATE TABLE auditoria (
    id_auditoria  INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_fk INT          DEFAULT NULL,       -- NULL si fue acción automática del sistema
    accion        VARCHAR(100) NOT NULL,            
    tabla_afectada VARCHAR(50) DEFAULT NULL,
    id_registro   VARCHAR(50) DEFAULT NULL,
    detalle       TEXT        DEFAULT NULL,
    ip_origen     VARCHAR(45) DEFAULT NULL,
    fecha_accion  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario_fk)
        REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Log de auditoría — todas las acciones críticas del sistema';

CREATE INDEX idx_auditoria_fecha  ON auditoria(fecha_accion);
CREATE INDEX idx_auditoria_accion ON auditoria(accion);


-- ==============================================================================
-- BLOQUE 9: VISTA PARA EL PANEL WEB
-- ==============================================================================

CREATE VIEW vista_infracciones_panel AS
SELECT
    i.id_infraccion,
    i.fecha_hora,
    i.placa_detectada,
    i.confianza_ia,
    i.estado_revision,
    i.ruta_imagen,

    -- Datos de la falta
    tf.nombre_falta,
    tf.gravedad,
    tf.monto_multa_bs,

    -- Datos del nodo/cámara
    n.nombre_identificador  AS camara_nombre,
    n.ubicacion_fisica      AS camara_ubicacion,

    v.marca,
    v.modelo,
    v.color,
    v.tipo_vehiculo,
    p.nombre_completo       AS propietario_nombre,
    p.correo_electronico    AS propietario_correo,
    p.telefono              AS propietario_telefono

FROM infracciones_ia i
    JOIN  tipos_falta  tf ON i.id_tipo_falta_fk = tf.id_tipo_falta
    JOIN  nodos_edge    n ON i.id_nodo_fk        = n.id_nodo
    LEFT JOIN vehiculos v ON i.placa_detectada   = v.placa
    LEFT JOIN propietarios p ON v.ci_propietario_fk = p.ci_propietario

ORDER BY i.fecha_hora DESC;


-- ==============================================================================
-- DATOS DE PRUEBA
-- ==============================================================================

-- Usuarios
INSERT INTO usuarios (credencial, password_hash, nombre_completo, rol) VALUES
('admin',    '123456789', 'Ing. Bruno Ortega',     'Administrador'),
('operador1','op123456',  'Tec. Carlos Mamani',    'Operador'),
('operador2','op654321',  'Tec. Ana Flores Quispe','Operador');

-- Nodos Edge (Cámaras)
INSERT INTO nodos_edge (nombre_identificador, ubicacion_fisica, direccion_ip, estado_conexion, umbral_ia, fecha_instalacion) VALUES
('Cámara 01 - Centro',  'Av. Ayacucho y Heroínas',    '192.168.1.10', 'Online',       85.00, '2025-01-10'),
('Cámara 02 - Norte',   'Av. Blanco Galindo Km 2',    '192.168.1.11', 'Online',       85.00, '2025-01-15'),
('Cámara 03 - Sur',     'Av. Panamericana y 6 de Ago','192.168.1.12', 'Mantenimiento',85.00, '2025-03-01');

-- Catálogo de faltas y tarifas oficiales
INSERT INTO tipos_falta (nombre_falta, descripcion, monto_multa_bs, gravedad) VALUES
('Semáforo en Rojo',     'Cruce de intersección con semáforo en fase roja',       800.00, 'Muy Grave'),
('Invasión Paso Cebra',  'Detención del vehículo sobre el paso peatonal',         400.00, 'Grave'),
('Exceso de Velocidad',  'Velocidad superior al límite permitido en la vía',      600.00, 'Grave'),
('Estacionamiento Indebido','Vehículo estacionado en zona prohibida o amarilla',  200.00, 'Leve'),
('Giro Indebido',        'Maniobra de giro en zona con señalética restrictiva',   350.00, 'Grave');

-- Propietarios
INSERT INTO propietarios (ci_propietario, nombre_completo, correo_electronico, telefono, direccion_domicilio) VALUES
('8899554', 'Juan Pérez Mamani',   'juan.p@email.com',   '77712345', 'Calle Falsa 123, Zona Sur'),
('5544332', 'María López Rojas',   'm.lopez@email.com',  '76598765', 'Av. Circunvalación 456'),
('3312789', 'Carlos Vargas Torrez','c.vargas@email.com', '71134567', 'Calle Bolívar 789, Centro');

-- Vehículos
INSERT INTO vehiculos (placa, ci_propietario_fk, marca, modelo, anio, color, tipo_vehiculo) VALUES
('4589-HTR', '8899554', 'Toyota',  'Hilux',  2021, 'Blanco',  'Camioneta'),
('1234-XYZ', '5544332', 'Suzuki',  'Swift',  2019, 'Rojo',    'Auto'),
('7890-ABC', '3312789', 'Nissan',  'Sentra', 2020, 'Plateado','Auto');

-- Infracciones detectadas por la IA
INSERT INTO infracciones_ia (id_infraccion, id_nodo_fk, id_tipo_falta_fk, placa_detectada, fecha_hora, confianza_ia, ruta_imagen, hash_evidencia, estado_revision) VALUES
('INF-2026-001', 2, 1, '4589-HTR', '2026-05-16 14:32:10', 98.50, 'evidencias/inf_001.jpg', 'a8f5f167f44b9d3b1c2e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5', 'Pendiente'),
('INF-2026-002', 1, 2, '1234-XYZ', '2026-05-16 14:35:05', 95.20, 'evidencias/inf_002.jpg', 'c7d8e9f0a12b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8', 'Pendiente'),
('INF-2026-003', 1, 3, '7890-ABC', '2026-05-17 09:12:44', 91.80, 'evidencias/inf_003.jpg', 'f1e2d3c4b5a6978869504132b1a09f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1', 'Pendiente');

-- Auditoría: registro del login inicial
INSERT INTO auditoria (id_usuario_fk, accion, tabla_afectada, id_registro, detalle, ip_origen) VALUES
(1, 'LOGIN_EXITOSO', 'usuarios', '1', 'Primer acceso al sistema', '127.0.0.1');

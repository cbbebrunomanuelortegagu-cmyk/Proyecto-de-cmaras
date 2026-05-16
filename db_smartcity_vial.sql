-- SISTEMA DE FISCALIZACIÓN VIAL IA (SMART CITY) - BOLIVIA
-- BASE DE DATOS COMPLETA PARA XAMPP (MySQL/MariaDB)
-- ==============================================================================

-- 1. CREACIÓN DE LA BASE DE DATOS
CREATE DATABASE IF NOT EXISTS db_smartcity_vial
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE db_smartcity_vial;

-- ==============================================================================
-- BLOQUE 1: SEGURIDAD Y CONTROL DE ACCESOS (Cumple RNF4)
-- ==============================================================================

CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    credencial VARCHAR(50) NOT NULL UNIQUE,      -- Ej: 'admin'
    password_hash VARCHAR(255) NOT NULL,         -- Para el prototipo usaremos '123456789'
    nombre_completo VARCHAR(100) NOT NULL,
    rol ENUM('Administrador', 'Operador') DEFAULT 'Operador',
    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ==============================================================================
-- BLOQUE 2: INFRAESTRUCTURA EDGE COMPUTING (Cumple RNF2 y RF6)
-- ==============================================================================

CREATE TABLE nodos_edge (
    id_nodo INT AUTO_INCREMENT PRIMARY KEY,
    nombre_identificador VARCHAR(100) NOT NULL,  -- Ej: 'Cámara 01 - Centro'
    ubicacion_fisica VARCHAR(255) NOT NULL,
    direccion_ip VARCHAR(20) NOT NULL,
    estado_conexion ENUM('Online', 'Offline', 'Mantenimiento') DEFAULT 'Online',
    umbral_ia DECIMAL(5,2) DEFAULT 85.00         -- Configuración de confianza mínima para la IA
) ENGINE=InnoDB;

-- ==============================================================================
-- BLOQUE 3: PADRÓN AUTOMOTOR (Para generar la boleta legal RF8)
-- ==============================================================================

CREATE TABLE propietarios (
    ci_propietario VARCHAR(20) PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    correo_electronico VARCHAR(100),
    telefono VARCHAR(20),
    direccion_domicilio VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE vehiculos (
    placa VARCHAR(15) PRIMARY KEY,
    ci_propietario_fk VARCHAR(20) NOT NULL,
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50),
    color VARCHAR(30),
    FOREIGN KEY (ci_propietario_fk) REFERENCES propietarios(ci_propietario) 
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ==============================================================================
-- BLOQUE 4: CORE DE INTELIGENCIA ARTIFICIAL Y EVIDENCIAS (Cumple RF3, RF4, RNF3)
-- ==============================================================================

CREATE TABLE infracciones_ia (
    id_infraccion VARCHAR(20) PRIMARY KEY,       -- Ej: 'INF-2026-001'
    id_nodo_fk INT NOT NULL,                     -- ¿Qué poste capturó la falta?
    placa_detectada VARCHAR(15) NOT NULL,        -- Lo que leyó el OCR
    fecha_hora DATETIME NOT NULL,
    tipo_falta VARCHAR(100) NOT NULL,            -- Ej: 'Semáforo en Rojo', 'Paso Cebra'
    confianza_ia DECIMAL(5,2) NOT NULL,          -- % de seguridad de YOLO
    ruta_imagen VARCHAR(255) NOT NULL,           -- Dónde se guardó la foto
    hash_evidencia VARCHAR(128) NOT NULL,        -- RNF3: Seguridad Anti-alteración (SHA-256)
    estado_revision ENUM('Pendiente', 'Aprobada', 'Descartada') DEFAULT 'Pendiente',
    FOREIGN KEY (id_nodo_fk) REFERENCES nodos_edge(id_nodo) 
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ==============================================================================
-- BLOQUE 5: EMISIÓN DE BOLETAS OFICIALES (Cumple RF7 y RF8)
-- ==============================================================================

CREATE TABLE boletas_oficiales (
    id_boleta INT AUTO_INCREMENT PRIMARY KEY,
    id_infraccion_fk VARCHAR(20) NOT NULL UNIQUE, -- Relación 1 a 1 con la infracción
    id_usuario_validador_fk INT NOT NULL,         -- Auditoría: ¿Quién aprobó la multa?
    fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
    monto_multa DECIMAL(10,2) NOT NULL,
    estado_pago ENUM('No Pagado', 'Pagado', 'Apelación') DEFAULT 'No Pagado',
    ruta_pdf VARCHAR(255),                        -- El PDF generado de la boleta
    FOREIGN KEY (id_infraccion_fk) REFERENCES infracciones_ia(id_infraccion) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_usuario_validador_fk) REFERENCES usuarios(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;


-- ==============================================================================
-- INSERCIÓN DE DATOS DE PRUEBA (Para que tu HTML tenga datos reales al conectarse)
-- ==============================================================================

-- 1. Insertar el Administrador (Contraseña '123456789' en texto plano para el prototipo PHP)
INSERT INTO usuarios (credencial, password_hash, nombre_completo, rol) 
VALUES ('admin', '123456789', 'Ing. Bruno Ortega (Admin)', 'Administrador');

-- 2. Insertar Nodos Edge (Las cámaras de tu frontend)
INSERT INTO nodos_edge (nombre_identificador, ubicacion_fisica, direccion_ip, estado_conexion) 
VALUES 
('Cámara 01 - Centro', 'Av. Ayacucho y Heroínas', '192.168.1.10', 'Online'),
('Cámara 02 - Norte', 'Av. Blanco Galindo Km 2', '192.168.1.11', 'Online');

-- 3. Insertar Padrón Automotor (Dueños y Autos)
INSERT INTO propietarios (ci_propietario, nombre_completo, correo_electronico, telefono, direccion_domicilio) 
VALUES 
('8899554', 'Juan Pérez Mamani', 'juan.p@email.com', '77712345', 'Calle Falsa 123, Zona Sur'),
('5544332', 'María López Rojas', 'm.lopez@email.com', '76598765', 'Av. Circunvalación 456');

INSERT INTO vehiculos (placa, ci_propietario_fk, marca, modelo, color) 
VALUES 
('4589-HTR', '8899554', 'Toyota', 'Hilux', 'Blanco'),
('1234-XYZ', '5544332', 'Suzuki', 'Swift', 'Rojo');

-- 4. Insertar Infracciones detectadas por la IA (Pendientes de revisión)
INSERT INTO infracciones_ia (id_infraccion, id_nodo_fk, placa_detectada, fecha_hora, tipo_falta, confianza_ia, ruta_imagen, hash_evidencia, estado_revision) 
VALUES 
('INF-2026-001', 2, '4589-HTR', '2026-05-16 14:32:10', 'Semáforo en Rojo', 98.50, 'evidencias/inf_001.jpg', 'a8f5f167f44b9...', 'Pendiente'),
('INF-2026-002', 1, '1234-XYZ', '2026-05-16 14:35:05', 'Invasión Paso Cebra', 95.20, 'evidencias/inf_002.jpg', 'c7d8e9f0a12b3...', 'Pendiente');
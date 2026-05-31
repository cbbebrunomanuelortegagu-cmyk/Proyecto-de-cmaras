<?php
require_once 'config.php';

$conn   = conectar();
$result = $conn->query(
    "SELECT id_nodo, nombre_identificador, ubicacion_fisica,
            direccion_ip, estado_conexion, umbral_ia, fecha_instalacion
     FROM nodos_edge ORDER BY id_nodo"
);
$datos = [];

while ($fila = $result->fetch_assoc()) {
    $datos[] = $fila;
}

echo json_encode(["ok" => true, "data" => $datos]);
$conn->close();
?>
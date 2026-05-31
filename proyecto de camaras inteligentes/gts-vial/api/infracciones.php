<?php
require_once 'config.php';

$conn   = conectar();
$result = $conn->query("SELECT * FROM vista_infracciones_panel");
$datos  = [];

while ($fila = $result->fetch_assoc()) {
    $datos[] = $fila;
}

echo json_encode(["ok" => true, "data" => $datos]);
$conn->close();
?>
<?php
// api/config.php
// Conexión central a db_smartcity_vial
// Todos los demás archivos PHP heredan esta conexión

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

define('DB_HOST', 'localhost');
define('DB_USER', 'root');       // Usuario por defecto de XAMPP
define('DB_PASS', '');           // XAMPP no tiene contraseña por defecto
define('DB_NAME', 'db_smartcity_vial');

function conectar() {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode(["error" => "Conexión fallida: " . $conn->connect_error]);
        exit();
    }
    $conn->set_charset("utf8mb4");
    return $conn;
}
?>
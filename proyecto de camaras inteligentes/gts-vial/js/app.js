/* =============================================
   GTS VIAL - Lógica Principal (app.js)
   Alcaldía Control Vial - Sistema Inteligente
   ============================================= */

// === INSTANCIAS DE MODALES (Bootstrap) ===

const myModal  = new bootstrap.Modal(document.getElementById('modalDetalle'));
const modalAdd = new bootstrap.Modal(document.getElementById('modalAddCamara'));

let contadorCamaras = 1;


// ─────────────────────────────────────────────
// MÓDULO: AUTENTICACIÓN
// ─────────────────────────────────────────────

function validarAcceso(e) {
    e.preventDefault();
    const u = document.getElementById('userAdmin').value.trim();
    const p = document.getElementById('passAdmin').value.trim();

    if (u === "admin" && p === "123456789") {
        Swal.fire({
            icon: 'success',
            title: 'Acceso Autorizado',
            text: 'Bienvenido al panel de control, Operador.',
            timer: 1500,
            showConfirmButton: false
        }).then(() => {
            document.getElementById('login-view').style.setProperty('display', 'none', 'important');
            document.getElementById('dashboard-view').style.display = 'block';
        });
    } else {
        Swal.fire({
            icon: 'error',
            title: 'Acceso Denegado',
            text: 'Credencial o contraseña incorrecta.',
            confirmButtonColor: '#0d6efd'
        });
    }
}

function cerrarSesion() {
    Swal.fire({
        title: '¿Cerrar sesión?',
        text: "Saldrás del sistema de fiscalización.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            document.getElementById('dashboard-view').style.display = 'none';
            document.getElementById('login-view').style.setProperty('display', 'flex', 'important');
            document.getElementById('passAdmin').value = '';
        }
    });
}


// ─────────────────────────────────────────────
// MÓDULO: NAVEGACIÓN (Sidebar)
// ─────────────────────────────────────────────

function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));

    document.getElementById(sectionId).classList.add('active');

    const btnId = 'link-' + sectionId.split('-')[1];
    document.getElementById(btnId).classList.add('active');
}


// ─────────────────────────────────────────────
// MÓDULO: INFRACCIONES
// ─────────────────────────────────────────────

// Guardamos el ID de la infracción que está abierta en el modal
let infraccionActivaId = null;

function revisarInfraccion(id, placa, falta, camara, dueño, auto) {
    // Guardar qué infracción se está revisando ahora mismo
    infraccionActivaId = id;

    document.getElementById('detId').innerText     = id;
    document.getElementById('detPlaca').innerText  = placa;
    document.getElementById('detFalta').innerText  = falta;
    document.getElementById('detCamara').innerText = camara;
    document.getElementById('detDueño').innerText  = dueño;
    document.getElementById('detAuto').innerText   = auto;

    myModal.show();
}

function cambiarEstadoBoton(id, nuevoEstado) {
    // Busca el botón cuyo onclick contiene el ID de la infracción
    const botones = document.querySelectorAll('.btn-revisar');
    botones.forEach(btn => {
        if (btn.getAttribute('onclick').includes(`'${id}'`)) {
            // Limpiar clases de estado anteriores
            btn.classList.remove('emitida', 'rechazada');

            if (nuevoEstado === 'emitida') {
                btn.classList.add('emitida');
                btn.innerHTML = '<i class="fa-solid fa-check-double me-1"></i> Boleta Emitida';
            } else if (nuevoEstado === 'rechazada') {
                btn.classList.add('rechazada');
                btn.innerHTML = '<i class="fa-solid fa-xmark me-1"></i> Rechazada';
            }
        }
    });
}

function finalizarEmision() {
    myModal.hide();

    // Cambiar el botón de esa infracción a VERDE
    cambiarEstadoBoton(infraccionActivaId, 'emitida');

    Swal.fire({
        title: 'Boleta Generada',
        text: 'La multa ha sido registrada en la Base de Datos oficial.',
        icon: 'success',
        confirmButtonColor: '#198754'
    });

    infraccionActivaId = null;
}

function rechazarMulta() {
    myModal.hide();

    // Cambiar el botón de esa infracción a GRIS
    cambiarEstadoBoton(infraccionActivaId, 'rechazada');

    Swal.fire({
        title: 'Infracción Descartada',
        text: 'El registro ha sido marcado como Falso Positivo.',
        icon: 'info',
        confirmButtonColor: '#6c757d'
    });

    infraccionActivaId = null;
}


// ─────────────────────────────────────────────
// MÓDULO: CÁMARAS
// ─────────────────────────────────────────────

function abrirModalAddCamara() {
    document.getElementById('add-cam-name').value = '';
    document.getElementById('add-cam-loc').value  = '';
    document.getElementById('add-cam-ip').value   = '';
    modalAdd.show();
}

function guardarNuevaCamara() {
    const nombre = document.getElementById('add-cam-name').value || 'Equipo Nuevo';
    const loc    = document.getElementById('add-cam-loc').value  || 'Ubicación pendiente';
    const ip     = document.getElementById('add-cam-ip').value   || '0.0.0.0';

    contadorCamaras++;
    const nuevoId = contadorCamaras;

    const nuevaTarjeta = document.createElement('div');
    nuevaTarjeta.className = 'col-md-6 col-lg-4 fade-in';
    nuevaTarjeta.id = `card-cam-${nuevoId}`;

    nuevaTarjeta.innerHTML = `
        <div class="card card-custom p-4 bg-white border-top border-4 border-success">
            <div class="d-flex align-items-start justify-content-between mb-3">
                <div class="cam-icon"><i class="fa-solid fa-camera fa-xl"></i></div>
                <span class="badge bg-success rounded-pill px-3">Conectada</span>
            </div>
            <h5 class="fw-bold mb-1 text-dark" id="name-cam-${nuevoId}">${nombre}</h5>
            <p class="text-muted small mb-3" id="loc-cam-${nuevoId}">
                <i class="fa-solid fa-map-pin me-1"></i> ${loc}
            </p>
            <div class="bg-light p-3 rounded-3 mb-4 border">
                <div class="d-flex justify-content-between small mb-2">
                    <span class="text-muted">Dirección IP:</span>
                    <span class="fw-bold font-monospace" id="ip-cam-${nuevoId}">${ip}</span>
                </div>
                <div class="d-flex justify-content-between small">
                    <span class="text-muted">Estado del Lente:</span>
                    <span class="fw-bold text-success">Óptimo</span>
                </div>
            </div>
            <button class="btn btn-light border w-100 fw-bold text-secondary"
                    onclick="alert('Función de edición en desarrollo')">
                <i class="fa-solid fa-pen-to-square me-2"></i> Editar Configuración
            </button>
        </div>
    `;

    document.getElementById('contenedor-camaras').appendChild(nuevaTarjeta);
    modalAdd.hide();

    Swal.fire({
        icon: 'success',
        title: 'Equipo Añadido',
        text: 'La cámara ha sido registrada y está operando.',
        confirmButtonColor: '#0d6efd'
    });
}


// ─────────────────────────────────────────────
// MÓDULO: CONFIGURACIÓN
// ─────────────────────────────────────────────

function guardarAjustes() {
    Swal.fire({
        title: 'Guardado',
        text: 'Las configuraciones se han aplicado correctamente.',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false
    });
}

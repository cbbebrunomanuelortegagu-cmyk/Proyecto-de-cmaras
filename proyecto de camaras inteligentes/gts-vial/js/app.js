/* =============================================
   GTS VIAL - Lógica Principal (app.js)
   Adaptado a db_smartcity_vial v2.0
   ============================================= */

// ── Instancias de modales Bootstrap ──
const myModal     = new bootstrap.Modal(document.getElementById('modalDetalle'));
const modalAdd    = new bootstrap.Modal(document.getElementById('modalAddCamara'));
const modalEditar = new bootstrap.Modal(document.getElementById('modalEditarCamara'));

// ── Datos de sesión activa ──
let usuarioActivo      = null;
let infraccionActivaId = null;
let contadorCamaras    = 3;

// ── Base de datos local de cámaras (espejo de nodos_edge) ──
// Cuando conectes PHP esto vendrá de api/camaras.php
const CAMARAS_BD = {
    1: { nombre: 'Cámara 01 - Centro', ubicacion: 'Av. Ayacucho y Heroínas',     ip: '192.168.1.10', umbral: 85, estado: 'Online' },
    2: { nombre: 'Cámara 02 - Norte',  ubicacion: 'Av. Blanco Galindo Km 2',     ip: '192.168.1.11', umbral: 85, estado: 'Online' },
    3: { nombre: 'Cámara 03 - Sur',    ubicacion: 'Av. Panamericana y 6 de Ago', ip: '192.168.1.12', umbral: 85, estado: 'Mantenimiento' },
};

// ── Contadores de estadísticas (simulan la BD en frontend) ──
let stats = { pendientes: 3, emitidas: 0, descartadas: 0, montoTotal: 0 };

// ── Datos extraídos de tipos_falta para calcular vencimiento ──
const diasVencimiento = 30;

// ── Registro local de boletas emitidas (tabla boletas_oficiales) ──
let boletasEmitidas = [];
let contadorBoletas = 0;

// ── Usuarios válidos (tabla usuarios de la BD) ──
const USUARIOS_BD = {
    'admin':     { password: '123456789', nombre: 'Ing. Bruno Ortega',      rol: 'Administrador' },
    'operador1': { password: 'op123456',  nombre: 'Tec. Carlos Mamani',     rol: 'Operador' },
    'operador2': { password: 'op654321',  nombre: 'Tec. Ana Flores Quispe', rol: 'Operador' }
};


// ─────────────────────────────────────────────
// MÓDULO: AUTENTICACIÓN (tabla: usuarios)
// ─────────────────────────────────────────────

function validarAcceso(e) {
    e.preventDefault();
    const credencial = document.getElementById('userAdmin').value.trim();
    const password   = document.getElementById('passAdmin').value.trim();
    const usuario    = USUARIOS_BD[credencial];

    if (usuario && usuario.password === password) {
        usuarioActivo = { credencial, ...usuario };

        Swal.fire({
            icon: 'success',
            title: 'Acceso Autorizado',
            html: `Bienvenido, <strong>${usuario.nombre}</strong><br>
                   <span class="badge bg-primary mt-1">${usuario.rol}</span>`,
            timer: 1800,
            showConfirmButton: false
        }).then(() => {
            // Mostrar nombre del operador en el sidebar
            document.getElementById('sidebar-operador').innerText = usuario.nombre;
            document.getElementById('login-view').style.setProperty('display', 'none', 'important');
            document.getElementById('dashboard-view').style.display = 'block';
            actualizarStats();
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
        text: 'Saldrás del sistema de fiscalización.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            usuarioActivo = null;
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
// MÓDULO: ESTADÍSTICAS
// Simula SELECT COUNT(*) sobre infracciones_ia
// y SUM(monto_multa_bs) sobre boletas_oficiales
// ─────────────────────────────────────────────

function actualizarStats() {
    document.getElementById('stat-pendientes').innerText  = stats.pendientes;
    document.getElementById('stat-emitidas').innerText    = stats.emitidas;
    document.getElementById('stat-descartadas').innerText = stats.descartadas;
    document.getElementById('stat-monto').innerText       = `Bs ${stats.montoTotal.toFixed(2)}`;
    // Badge del sidebar
    const badge = document.getElementById('badge-pendientes');
    badge.innerText = stats.pendientes;
    badge.style.display = stats.pendientes > 0 ? 'inline' : 'none';
}


// ─────────────────────────────────────────────
// MÓDULO: INFRACCIONES (vista_infracciones_panel)
// ─────────────────────────────────────────────

function revisarInfraccion(id, placa, falta, gravedad, camara, dueño, auto, monto, confianza) {
    infraccionActivaId = id;

    // Calcular fecha de vencimiento (hoy + 30 días)
    const hoy        = new Date();
    const vencimiento = new Date(hoy.setDate(hoy.getDate() + diasVencimiento));
    const fechaVenc  = vencimiento.toLocaleDateString('es-BO', { day:'2-digit', month:'short', year:'numeric' });

    document.getElementById('detId').innerText         = id;
    document.getElementById('detPlaca').innerText      = placa;
    document.getElementById('detFalta').innerText      = falta;
    document.getElementById('detGravedad').innerText   = gravedad;
    document.getElementById('detCamara').innerText     = camara;
    document.getElementById('detDueño').innerText      = dueño;
    document.getElementById('detAuto').innerText       = auto;
    document.getElementById('detMonto').innerText      = parseFloat(monto).toFixed(2);
    document.getElementById('detVencimiento').innerText = fechaVenc;
    document.getElementById('detConfianza').innerText  = `✓ IA: ${confianza}%`;

    // Color del badge de gravedad
    const badgeGrav = document.getElementById('detGravedad');
    badgeGrav.className = 'badge border';
    if (gravedad === 'Muy Grave') {
        badgeGrav.classList.add('bg-danger', 'text-white');
    } else if (gravedad === 'Grave') {
        badgeGrav.classList.add('bg-warning', 'text-dark');
    } else {
        badgeGrav.classList.add('bg-secondary', 'text-white');
    }

    myModal.show();
}

function cambiarEstadoBoton(id, nuevoEstado) {
    const btn = document.querySelector(`.btn-revisar[data-id="${id}"]`);
    if (!btn) return;
    btn.classList.remove('emitida', 'rechazada');
    if (nuevoEstado === 'emitida') {
        btn.classList.add('emitida');
        btn.innerHTML = '<i class="fa-solid fa-check-double me-1"></i> Boleta Emitida';
    } else if (nuevoEstado === 'rechazada') {
        btn.classList.add('rechazada');
        btn.innerHTML = '<i class="fa-solid fa-xmark me-1"></i> Descartada';
    }
}

function finalizarEmision() {
    myModal.hide();

    const id     = infraccionActivaId;
    const monto  = parseFloat(document.getElementById('detMonto').innerText);
    const placa  = document.getElementById('detPlaca').innerText;
    const dueño  = document.getElementById('detDueño').innerText;
    const falta  = document.getElementById('detFalta').innerText;
    const vence  = document.getElementById('detVencimiento').innerText;

    // Actualizar stats (INSERT en boletas_oficiales)
    stats.pendientes  = Math.max(0, stats.pendientes - 1);
    stats.emitidas   += 1;
    stats.montoTotal += monto;
    actualizarStats();

    // Cambiar estado visual del botón
    cambiarEstadoBoton(id, 'emitida');

    // Registrar boleta en la tabla de boletas (INSERT)
    contadorBoletas++;
    boletasEmitidas.push({ id: contadorBoletas, infraccion: id, placa, dueño, falta, monto, vence, estado: 'No Pagado' });
    renderizarTablaBoletas();

    infraccionActivaId = null;

    Swal.fire({
        title: 'Boleta Generada',
        html: `La multa <strong>${id}</strong> fue registrada.<br>
               Monto: <strong>Bs ${monto.toFixed(2)}</strong><br>
               Vence: <strong>${vence}</strong>`,
        icon: 'success',
        confirmButtonColor: '#198754'
    });
}

function rechazarMulta() {
    myModal.hide();

    const id = infraccionActivaId;

    // Actualizar stats (UPDATE estado_revision = 'Descartada')
    stats.pendientes   = Math.max(0, stats.pendientes - 1);
    stats.descartadas += 1;
    actualizarStats();

    cambiarEstadoBoton(id, 'rechazada');
    infraccionActivaId = null;

    Swal.fire({
        title: 'Infracción Descartada',
        text: 'El registro fue marcado como Falso Positivo en la BD.',
        icon: 'info',
        confirmButtonColor: '#6c757d'
    });
}


// ─────────────────────────────────────────────
// MÓDULO: BOLETAS EMITIDAS
// Renderiza la tabla sec-boletas
// ─────────────────────────────────────────────

function renderizarTablaBoletas() {
    const tbody = document.getElementById('tabla-boletas');

    if (boletasEmitidas.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="text-center text-muted py-5">
                <i class="fa-solid fa-inbox fa-2x mb-2 d-block opacity-25"></i>
                Aún no se han emitido boletas en esta sesión.
            </td></tr>`;
        return;
    }

    tbody.innerHTML = boletasEmitidas.map(b => `
        <tr>
            <td class="ps-4 fw-bold text-dark">#${String(b.id).padStart(4,'0')}</td>
            <td class="text-primary fw-bold">${b.infraccion}</td>
            <td>${b.dueño}<br><small class="text-muted font-monospace">${b.placa}</small></td>
            <td class="fw-bold">Bs ${parseFloat(b.monto).toFixed(2)}</td>
            <td class="text-danger small">${b.vence}</td>
            <td><span class="badge bg-warning text-dark rounded-pill px-2">No Pagado</span></td>
            <td>
                <button class="btn btn-outline-primary btn-sm rounded-pill px-3"
                        onclick="simularNotificacion('${b.dueño}')">
                    <i class="fa-solid fa-envelope me-1"></i> Notificar
                </button>
            </td>
        </tr>
    `).join('');
}

function simularNotificacion(nombre) {
    // Simula INSERT en tabla notificaciones
    Swal.fire({
        icon: 'success',
        title: 'Notificación Enviada',
        html: `Correo enviado a <strong>${nombre}</strong>.<br>
               <small class="text-muted">Registrado en tabla <code>notificaciones</code></small>`,
        timer: 2000,
        showConfirmButton: false
    });
}


// ─────────────────────────────────────────────
// MÓDULO: CÁMARAS (tabla: nodos_edge)
// ─────────────────────────────────────────────

function abrirEditorCamara(idCamara) {
    const cam = CAMARAS_BD[idCamara];
    if (!cam) return;

    // Rellenar el modal con los datos actuales de esa cámara
    document.getElementById('edit-cam-id').value            = idCamara;
    document.getElementById('edit-cam-subtitulo').innerText = cam.nombre;
    document.getElementById('edit-cam-name').value          = cam.nombre;
    document.getElementById('edit-cam-loc').value           = cam.ubicacion;
    document.getElementById('edit-cam-ip').value            = cam.ip;
    document.getElementById('edit-cam-umbral').value        = cam.umbral;
    document.getElementById('edit-cam-umbral-val').innerText = cam.umbral + '%';
    document.getElementById('edit-cam-estado').value        = cam.estado;

    modalEditar.show();
}

function guardarEdicionCamara() {
    const id      = parseInt(document.getElementById('edit-cam-id').value);
    const nombre  = document.getElementById('edit-cam-name').value.trim()  || CAMARAS_BD[id].nombre;
    const loc     = document.getElementById('edit-cam-loc').value.trim()   || CAMARAS_BD[id].ubicacion;
    const ip      = document.getElementById('edit-cam-ip').value.trim()    || CAMARAS_BD[id].ip;
    const umbral  = parseInt(document.getElementById('edit-cam-umbral').value);
    const estado  = document.getElementById('edit-cam-estado').value;

    // Actualizar el objeto local (cuando conectes PHP irá un fetch PUT a api/camaras.php)
    CAMARAS_BD[id] = { nombre, ubicacion: loc, ip, umbral, estado };

    // Actualizar visualmente la tarjeta en el DOM
    _actualizarTarjetaCamara(id, nombre, loc, ip, umbral, estado);

    modalEditar.hide();

    Swal.fire({
        icon: 'success',
        title: 'Cambios Guardados',
        html: `<strong>${nombre}</strong> actualizada.<br>
               <small class="text-muted">UPDATE en <code>nodos_edge</code></small>`,
        timer: 2000,
        showConfirmButton: false
    });
}

function _actualizarTarjetaCamara(id, nombre, ubicacion, ip, umbral, estado) {
    // Buscar la tarjeta por el texto del botón de editar que tiene onclick="abrirEditorCamara(id)"
    const botones = document.querySelectorAll('#contenedor-camaras button');
    let tarjeta = null;
    botones.forEach(btn => {
        if (btn.getAttribute('onclick') === `abrirEditorCamara(${id})`) {
            tarjeta = btn.closest('.card');
        }
    });
    if (!tarjeta) return;

    // Color y badge según estado
    const colorBorde = estado === 'Online' ? 'border-primary'
                     : estado === 'Mantenimiento' ? 'border-warning' : 'border-danger';
    const badgeHTML  = estado === 'Online'
        ? `<span class="badge bg-success rounded-pill px-3">Online</span>`
        : estado === 'Mantenimiento'
        ? `<span class="badge bg-warning text-dark rounded-pill px-3">Mantenimiento</span>`
        : `<span class="badge bg-danger rounded-pill px-3">Offline</span>`;

    // Quitar bordes anteriores y aplicar el nuevo
    tarjeta.classList.remove('border-primary','border-warning','border-danger');
    tarjeta.classList.add(colorBorde);

    // Actualizar contenido de la tarjeta
    tarjeta.querySelector('h5').innerText = nombre;
    tarjeta.querySelector('p.text-muted').innerHTML =
        `<i class="fa-solid fa-map-pin me-1"></i> ${ubicacion}`;

    // Actualizar badge de estado
    const badgeActual = tarjeta.querySelector('.badge');
    if (badgeActual) badgeActual.outerHTML = badgeHTML;

    // Actualizar los datos del recuadro interior
    const spans = tarjeta.querySelectorAll('.bg-light span.fw-bold');
    if (spans[0]) spans[0].innerText = ip;
    if (spans[1]) spans[1].innerText = umbral + '%';

    // Si pasa a Mantenimiento, deshabilitar el botón de editar
    const btnEditar = tarjeta.querySelector('button[onclick^="abrirEditorCamara"]');
    if (btnEditar) {
        if (estado === 'Mantenimiento') {
            btnEditar.outerHTML = `
                <button class="btn btn-warning border w-100 fw-bold text-dark" disabled>
                    <i class="fa-solid fa-wrench me-2"></i> En Mantenimiento
                </button>`;
        } else {
            btnEditar.disabled = false;
            btnEditar.className = 'btn btn-light border w-100 fw-bold text-secondary';
        }
    }
}
    document.getElementById('add-cam-name').value   = '';
    document.getElementById('add-cam-loc').value    = '';
    document.getElementById('add-cam-ip').value     = '';
    document.getElementById('add-cam-umbral').value = '85';
    modalAdd.show();
}

function guardarNuevaCamara() {
    const nombre  = document.getElementById('add-cam-name').value   || 'Equipo Nuevo';
    const loc     = document.getElementById('add-cam-loc').value    || 'Ubicación pendiente';
    const ip      = document.getElementById('add-cam-ip').value     || '0.0.0.0';
    const umbral  = document.getElementById('add-cam-umbral').value || '85';

    contadorCamaras++;
    const nuevaTarjeta = document.createElement('div');
    nuevaTarjeta.className = 'col-md-6 col-lg-4 fade-in';
    nuevaTarjeta.innerHTML = `
        <div class="card card-custom p-4 bg-white border-top border-4 border-success">
            <div class="d-flex align-items-start justify-content-between mb-3">
                <div class="cam-icon"><i class="fa-solid fa-camera fa-xl"></i></div>
                <span class="badge bg-success rounded-pill px-3">Online</span>
            </div>
            <h5 class="fw-bold mb-1 text-dark">${nombre}</h5>
            <p class="text-muted small mb-3"><i class="fa-solid fa-map-pin me-1"></i> ${loc}</p>
            <div class="bg-light p-3 rounded-3 mb-3 border">
                <div class="d-flex justify-content-between small mb-2">
                    <span class="text-muted">Dirección IP:</span>
                    <span class="fw-bold font-monospace">${ip}</span>
                </div>
                <div class="d-flex justify-content-between small mb-2">
                    <span class="text-muted">Umbral IA:</span>
                    <span class="fw-bold text-primary">${umbral}%</span>
                </div>
                <div class="d-flex justify-content-between small">
                    <span class="text-muted">Instalación:</span>
                    <span class="fw-bold">${new Date().toLocaleDateString('es-BO')}</span>
                </div>
            </div>
            <button class="btn btn-light border w-100 fw-bold text-secondary" onclick="alert('Edición en desarrollo')">
                <i class="fa-solid fa-pen-to-square me-2"></i> Editar Configuración
            </button>
        </div>`;

    document.getElementById('contenedor-camaras').appendChild(nuevaTarjeta);
    modalAdd.hide();

    Swal.fire({
        icon: 'success',
        title: 'Nodo Registrado',
        html: `<strong>${nombre}</strong> fue insertado en <code>nodos_edge</code>.`,
        confirmButtonColor: '#0d6efd'
    });
}


// ─────────────────────────────────────────────
// MÓDULO: CONFIGURACIÓN (nodos_edge.umbral_ia)
// ─────────────────────────────────────────────

function guardarAjustes() {
    const umbral    = document.getElementById('slider-umbral').value;
    const vencDias  = document.getElementById('config-vencimiento').value;
    Swal.fire({
        title: 'Configuración Guardada',
        html: `Umbral IA: <strong>${umbral}%</strong><br>
               Vencimiento boletas: <strong>${vencDias} días</strong><br>
               <small class="text-muted">UPDATE en <code>nodos_edge.umbral_ia</code></small>`,
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
    });
}

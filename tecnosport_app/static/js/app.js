/**
 * Tecnosport - Sistema de Cuentas por Cobrar
 * JavaScript Principal - v2.0
 */

// ==================== CONFIGURACIÓN ====================
const CONFIG = {
    API_BASE: '/api',
    TOAST_DURATION: 4000,
    DEBOUNCE_DELAY: 300,
    CURRENCY_LOCALE: 'es-CO',
    CURRENCY_CODE: 'COP'
};

// ==================== THEME MANAGER ====================
const Theme = {
    init() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (!toggleBtn) return;
        
        toggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            const applyTheme = () => {
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
            };

            const rotateButton = () => {
                toggleBtn.style.transform = 'rotate(360deg)';
                setTimeout(() => {
                    toggleBtn.style.transform = '';
                }, 300);
            };

            // Cross-fade unificado (View Transitions API).
            // Se bloquean las transiciones individuales de cada elemento durante el
            // cambio para que el tema no "cambie por partes", solo el fundido global.
            if (document.startViewTransition) {
                document.documentElement.classList.add('vt-theme');
                const vt = document.startViewTransition(applyTheme);
                vt.finished.finally(() => {
                    document.documentElement.classList.remove('vt-theme');
                    rotateButton();
                });
            } else {
                applyTheme();
                rotateButton();
            }
        });
    }
};

// Inicializar tema al cargar el script
Theme.init();

// ==================== UTILIDADES ====================

/**
 * Formatea un número como moneda
 */
function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '$0';
    return new Intl.NumberFormat(CONFIG.CURRENCY_LOCALE, {
        style: 'currency',
        currency: CONFIG.CURRENCY_CODE,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Convierte un valor de input formateado con puntos de miles a un float limpio.
 */
function parseCurrencyInput(value) {
    if (value === null || value === undefined || value === '') return 0;
    // Eliminar todos los puntos (separadores de miles) y convertir a float
    const cleanValue = String(value).replace(/\./g, '');
    return parseFloat(cleanValue) || 0;
}

/**
 * Formatea un elemento input con separadores de miles sobre la marcha
 */
function formatInput(el) {
    let value = el.value.replace(/\D/g, ''); // Remover caracteres que no sean dígitos
    if (value === '') {
        el.value = '';
        return;
    }
    // Formatear usando separadores de miles
    el.value = value.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/**
 * Configura el formateo de miles dinámico en todos los campos numéricos de dinero
 */
function setupCurrencyInputs() {
    const inputs = document.querySelectorAll(
        "input#monto, input#precio-unitario, input[name='precio_compra'], input[name='precio_venta']"
    );
    
    inputs.forEach(input => {
        // Cambiar dinámicamente tipo a text para admitir caracteres de formato
        if (input.type === 'number') {
            input.type = 'text';
            input.inputMode = 'numeric';
        }
        
        // Formatear valor inicial si lo tuviera
        formatInput(input);
        
        // Escuchar cambios
        input.addEventListener('input', () => {
            formatInput(input);
        });
    });
}

/**
 * Formatea una fecha
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('es-CO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    }).format(date);
}

/**
 * Formatea fecha y hora
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('es-CO', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

/**
 * Obtiene las iniciales de un nombre
 */
function getInitials(name) {
    if (!name) return '??';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function lockSubmitButton(form, loadingText = 'Registrando...') {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.disabled) return null;

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.dataset.originalText = originalText;
    btn.textContent = loadingText;
    return btn;
}

function unlockSubmitButton(btn, fallbackText = null) {
    if (!btn) return;

    btn.disabled = false;
    btn.textContent = fallbackText || btn.dataset.originalText || btn.textContent;
    delete btn.dataset.originalText;
}

/**
 * Devuelve la representación visual de una operación basada en tipo_operacion y tipo.
 * Usa tipo_operacion como fuente principal; si no existe, infiere desde tipo.
 * @param {Object} mov - Objeto movimiento con campos tipo, tipo_operacion
 * @returns {Object} { label, badgeClass, icon, sign, amountClass }
 */
function getOperationDisplay(mov) {
    const tipoOp = mov.tipo_operacion;
    const tipo = mov.tipo;

    // Usar tipo_operacion como fuente principal
    if (tipoOp === 'PRESTAMO_MERCANCIA') {
        return { label: 'Préstamo de mercancía', badgeClass: 'badge-prestamo-mercancia', icon: '📦', sign: '+', amountClass: 'negative' };
    }
    if (tipoOp === 'COMPRA') {
        return { label: 'Compra', badgeClass: 'badge-compra', icon: '🛍️', sign: '+', amountClass: 'negative' };
    }
    if (tipoOp === 'DEVUELTO') {
        return { label: 'Devuelto', badgeClass: 'badge-devuelto', icon: '↩️', sign: '-', amountClass: 'positive' };
    }
    if (tipoOp === 'PENDIENTE') {
        return { label: 'Préstamo pendiente', badgeClass: 'badge-pendiente', icon: '⏳', sign: '+', amountClass: 'negative' };
    }
    if (tipoOp === 'DEVOLUCION_CLIENTE') {
        return { label: 'Devolución de cliente', badgeClass: 'badge-devolucion', icon: '🔄', sign: '-', amountClass: 'positive' };
    }
    if (tipoOp === 'DEVOLUCION_PROVEEDOR') {
        return { label: 'Devolución a proveedor', badgeClass: 'badge-devolucion', icon: '↩️', sign: '-', amountClass: 'positive' };
    }

    // Fallback: inferir desde tipo (para compatibilidad con datos antiguos)
    if (tipo === 'abono') {
        return { label: 'Abono', badgeClass: 'badge-abono', icon: '📥', sign: '-', amountClass: 'positive' };
    }
    if (tipo === 'prestamo') {
        return { label: 'Préstamo', badgeClass: 'badge-prestamo', icon: '📤', sign: '+', amountClass: 'negative' };
    }
    if (tipo === 'factura') {
        return { label: 'Factura', badgeClass: 'badge-factura', icon: '📄', sign: '+', amountClass: 'negative' };
    }
    if (tipo === 'pago') {
        return { label: 'Pago', badgeClass: 'badge-pago', icon: '💸', sign: '-', amountClass: 'positive' };
    }

    // Desconocido
    return { label: tipoOp || tipo || 'Desconocido', badgeClass: 'badge-desconocido', icon: '❓', sign: '+', amountClass: 'negative' };
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Valida si un cliente tiene teléfono válido
 */
function tieneTelefonoValido(telefono) {
    if (!telefono) return false;
    // Convertir a string si es número
    const telStr = String(telefono).trim();
    return telStr !== '' && telStr !== 'null' && telStr !== 'undefined';
}

/**
 * Formatea teléfono para mostrar
 */
function formatTelefono(telefono) {
    if (!telefono) return 'Sin teléfono';
    const telStr = String(telefono).trim();
    return telStr || 'Sin teléfono';
}

// ==================== API CLIENT ====================

const API = {
    async request(endpoint, options = {}) {
        const url = CONFIG.API_BASE + endpoint;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        if (options.body && typeof options.body === 'object') {
            mergedOptions.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Error en la solicitud');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Clientes
    getClientes: () => API.request('/clientes'),
    buscarClientes: (q) => API.request(`/clientes/buscar?q=${encodeURIComponent(q)}`),
    getCliente: (id) => API.request(`/clientes/${id}`),
    crearCliente: (data) => API.request('/clientes', { method: 'POST', body: data }),
    actualizarCliente: (id, data) => API.request(`/clientes/${id}`, { method: 'PUT', body: data }),
    eliminarCliente: (id) => API.request(`/clientes/${id}`, { method: 'DELETE' }),
    
    // Movimientos
    getMovimientos: (limite = 100) => API.request(`/movimientos?limite=${limite}`),
    getMovimientosHoy: () => API.request('/movimientos/hoy'),
    getMovimientosCliente: (id) => API.request(`/movimientos/cliente/${id}`),
    crearMovimiento: (data) => API.request('/movimientos', { method: 'POST', body: data }),
    
    // Dashboard y reportes
    getDashboard: () => API.request('/dashboard'),
    getHistorial: (id) => API.request(`/historial/${id}`),
    
    // Proveedores
    getProveedores: () => API.request('/proveedores'),
    buscarProveedores: (q) => API.request(`/proveedores/buscar?q=${encodeURIComponent(q)}`),
    getProveedor: (id) => API.request(`/proveedores/${id}`),
    crearProveedor: (data) => API.request('/proveedores', { method: 'POST', body: data }),
    actualizarProveedor: (id, data) => API.request(`/proveedores/${id}`, { method: 'PUT', body: data }),
    eliminarProveedor: (id) => API.request(`/proveedores/${id}`, { method: 'DELETE' }),
    
    // Movimientos Proveedores
    getMovimientosProveedor: (limite = 100) => API.request(`/movimientos-proveedor?limite=${limite}`),
    getMovimientosProveedorHoy: () => API.request('/movimientos-proveedor/hoy'),
    getMovimientosByProveedor: (id) => API.request(`/movimientos-proveedor/proveedor/${id}`),
    crearMovimientoProveedor: (data) => API.request('/movimientos-proveedor', { method: 'POST', body: data }),
    
    // Dashboard y reportes Proveedores
    getDashboardProveedores: () => API.request('/dashboard-proveedores'),
    getHistorialProveedor: (id) => API.request(`/historial-proveedor/${id}`),

    // Inventario y ventas
    getProductos: () => API.request('/productos'),
    buscarProductos: (q) => API.request(`/productos/buscar?q=${encodeURIComponent(q)}`),
    getProducto: (id) => API.request(`/productos/${id}`),
    crearProducto: (data) => API.request('/productos', { method: 'POST', body: data }),
    actualizarProducto: (id, data) => API.request(`/productos/${id}`, { method: 'PUT', body: data }),
    eliminarProducto: (id) => API.request(`/productos/${id}`, { method: 'DELETE' }),
    getVentas: (limite = 100) => API.request(`/ventas?limite=${limite}`),
    crearVenta: (data) => API.request('/ventas', { method: 'POST', body: data }),
    getDashboardInventario: () => API.request('/dashboard-inventario'),
    
    // Backups
    getBackups: () => API.request('/backups'),
    crearBackup: () => API.request('/backups', { method: 'POST' }),

    // Gastos y Flujo de Caja
    registrarGasto: (data) => API.request('/gastos', { method: 'POST', body: data }),
    getFlujoCaja: (fecha) => API.request(`/dashboard/flujo-caja${fecha ? '?fecha=' + fecha : ''}`),

    // Devoluciones
    registrarDevolucionCliente: (data) => API.request('/devoluciones/cliente', { method: 'POST', body: data }),
    crearDevolucionProveedor: (data) => API.request('/devoluciones/proveedor', { method: 'POST', body: data }),
    registrarDevolucionProveedor: (data) => API.request('/devoluciones/proveedor', { method: 'POST', body: data }),
};

// ==================== TOAST NOTIFICATIONS ====================

const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },
    
    show(message, type = 'success') {
        this.init();
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${escapeHtml(message)}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;
        
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, CONFIG.TOAST_DURATION);
    },
    
    success: (msg) => Toast.show(msg, 'success'),
    error: (msg) => Toast.show(msg, 'error'),
    warning: (msg) => Toast.show(msg, 'warning')
};

// ==================== MODAL MANAGER ====================

const Modal = {
    current: null,
    
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            this.current = modal;
            document.body.style.overflow = 'hidden';
        }
    },
    
    close(modalId) {
        const modal = modalId ? document.getElementById(modalId) : this.current;
        if (modal) {
            modal.classList.remove('active');
            this.current = null;
            document.body.style.overflow = '';
        }
    },
    
    closeAll() {
        document.querySelectorAll('.modal-overlay.active').forEach(modal => {
            modal.classList.remove('active');
        });
        this.current = null;
        document.body.style.overflow = '';
    }
};

// Cerrar modal al hacer clic fuera
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        Modal.closeAll();
    }
});

// Cerrar modal con Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        Modal.closeAll();
    }
});

// ==================== LOADING STATES ====================

const Loading = {
    show(container, message = 'Cargando...') {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (el) {
            el.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 1rem;">${escapeHtml(message)}</p>
                </div>
            `;
        }
    },
    
    hide(container, content) {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (el && content) {
            el.innerHTML = content;
        }
    }
};

// ==================== SKELETON LOADERS ====================

const Skeleton = {
    statCard: () => `
        <div class="stat-card">
            <div class="skeleton" style="width: 48px; height: 48px; border-radius: 10px; margin-bottom: 1rem;"></div>
            <div class="skeleton" style="width: 60%; height: 12px; margin-bottom: 0.5rem;"></div>
            <div class="skeleton" style="width: 80%; height: 28px;"></div>
        </div>
    `,
    
    timelineItem: () => `
        <div class="timeline-item">
            <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
            <div style="flex: 1;">
                <div class="skeleton" style="width: 60%; height: 16px; margin-bottom: 0.5rem;"></div>
                <div class="skeleton" style="width: 40%; height: 12px;"></div>
            </div>
        </div>
    `,
    
    clienteItem: () => `
        <div class="cliente-item">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
                <div>
                    <div class="skeleton" style="width: 120px; height: 16px; margin-bottom: 0.25rem;"></div>
                    <div class="skeleton" style="width: 80px; height: 12px;"></div>
                </div>
            </div>
            <div class="skeleton" style="width: 80px; height: 20px;"></div>
        </div>
    `
};

// ==================== PÁGINA: DASHBOARD ====================

const Dashboard = {
    async init() {
        this.setupBusquedaRapida();
        await this.loadStats();
        await this.loadMovimientosHoy();
        await this.loadTopDeudores();
        await this.loadClientesSinAbono();
        await this.loadCarteraAntiguedad();
        await this.loadColaCobro();
        await this.loadUltimosAbonos();
        await this.loadTopProveedores();
    },
    
    setupBusquedaRapida() {
        const searchInput = document.getElementById('busqueda-rapida');
        const resultsContainer = document.getElementById('resultados-busqueda-rapida');
        
        if (!searchInput || !resultsContainer) return;
        if (searchInput._listenerAttached) return;
        searchInput._listenerAttached = true;
        
        // Cerrar resultados al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box-dashboard')) {
                resultsContainer.classList.remove('active');
            }
        });
        
        // Búsqueda con debounce
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="sin-resultados">
                            <div class="sin-resultados-icon">🔍</div>
                            <p>No se encontraron clientes con "${escapeHtml(query)}"</p>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = data.map(cliente => {
                        const tieneDeuda = cliente.saldo > 0;
                        const ultimoAbono = cliente.ultimo_abono;
                        
                        return `
                            <a href="/cliente/${cliente.id}" class="resultado-cliente">
                                <div class="resultado-cliente-info">
                                    <div class="resultado-cliente-avatar">${getInitials(cliente.nombre)}</div>
                                    <div class="resultado-cliente-datos">
                                        <h4>${escapeHtml(cliente.nombre)}</h4>
                                        <p>${formatTelefono(cliente.telefono)}</p>
                                    </div>
                                </div>
                                <div class="resultado-cliente-saldo">
                                    <div class="deuda ${!tieneDeuda ? 'sin-deuda' : ''}">${formatCurrency(Math.abs(cliente.saldo))}</div>
                                    ${ultimoAbono ? 
                                        `<div class="ultimo-abono">Últ. abono: ${formatDate(ultimoAbono.fecha)}</div>` : 
                                        `<div class="ultimo-abono">Sin abonos</div>`
                                    }
                                </div>
                            </a>
                        `;
                    }).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error en búsqueda:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        
        // Búsqueda inmediata al presionar Enter
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                debouncedSearch.cancel && debouncedSearch.cancel();
                debouncedSearch(searchInput.value);
            }
        });
        
        // Mostrar resultados al enfocar si hay texto
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim() && resultsContainer.innerHTML) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
async loadStats() {
        const container = document.getElementById('stats-container');
        if (!container) return;
        
        try {
            const [dashboardData, flujoData] = await Promise.all([
                API.getDashboard(),
                API.getFlujoCaja()
            ]);
            
            const d = dashboardData.data;
            const f = flujoData.data;
            
            container.innerHTML = `
                <div class="stat-card fade-in">
                    <div class="stat-icon">💰</div>
                    <div class="stat-label">Total Prestado</div>
                    <div class="stat-value">${formatCurrency(d.total_prestado)}</div>
                </div>
                <div class="stat-card success fade-in">
                    <div class="stat-icon">✓</div>
                    <div class="stat-label">Total Recuperado</div>
                    <div class="stat-value text-success">${formatCurrency(d.total_abonado)}</div>
                </div>
                <div class="stat-card danger fade-in">
                    <div class="stat-icon">📊</div>
                    <div class="stat-label">Deuda Activa</div>
                    <div class="stat-value text-danger">${formatCurrency(d.deuda_activa)}</div>
                </div>
                <div class="stat-card fade-in">
                    <div class="stat-icon">👥</div>
                    <div class="stat-label">Clientes Activos</div>
                    <div class="stat-value">${d.clientes_activos}</div>
                </div>
            `;
            
            // Actualizar Flujo de Caja del Día
            const entradas = (Number(f.ventas_total) || 0) + (Number(f.abonos_total) || 0);
            const salidas = (Number(f.pagos_proveedores_total) || 0) + (Number(f.gastos_total) || 0);
            const neto = Number(f.efectivo_neto) || 0;
            
            const entradasEl = document.getElementById('dash-caja-entradas');
            const salidasEl = document.getElementById('dash-caja-salidas');
            const netoEl = document.getElementById('dash-caja-neto');
            if (entradasEl) entradasEl.textContent = formatCurrency(entradas);
            if (salidasEl) salidasEl.textContent = formatCurrency(salidas);
            if (netoEl) netoEl.textContent = formatCurrency(neto);
            if (netoEl) netoEl.className = `number ${neto >= 0 ? 'text-success' : 'text-danger'}`;
            
            // Actualizar stats del día si existen los elementos
            const facturasHoy = document.getElementById('stats-hoy-facturas');
            const abonosHoy = document.getElementById('stats-hoy-abonos');
            if (facturasHoy) facturasHoy.textContent = formatCurrency(d.prestamos_hoy);
            if (abonosHoy) abonosHoy.textContent = formatCurrency(d.abonos_hoy);
            
        } catch (error) {
            container.innerHTML = `
                <div class="stat-card">
                    <p class="text-danger">Error al cargar estadísticas</p>
                    <button class="btn btn-sm btn-secondary mt-1" onclick="Dashboard.loadStats()">Reintentar</button>
                </div>
            `;
        }
    },
    
    async loadMovimientosHoy() {
        const container = document.getElementById('movimientos-lista');
        if (!container) return;
        
        try {
            const { data } = await API.getMovimientosHoy();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📝</div>
                        <div class="empty-state-title">Sin movimientos hoy</div>
                        <div class="empty-state-text">Los movimientos del día aparecerán aquí</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="timeline stagger-in">
                    ${data.slice(0, 10).map(mov => {
                        const d = getOperationDisplay(mov);
                        return `
                        <div class="timeline-item ${d.badgeClass}">
                            <div class="timeline-icon">${d.icon}</div>
                            <div class="timeline-content">
                                <div class="timeline-title">${escapeHtml(mov.cliente_nombre)}</div>
                                <div class="timeline-meta" style="white-space: pre-line;">${escapeHtml(mov.descripcion || d.label)}</div>
                            </div>
                            <div class="timeline-amount ${d.amountClass}">
                                ${d.sign}${formatCurrency(mov.monto)}
                            </div>
                        </div>`;
                    }).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar movimientos</p>`;
        }
    },
    
    async loadTopDeudores() {
        const container = document.getElementById('top-deudores');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const topDeudores = data.top_deudores;
            
            if (topDeudores.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🎉</div>
                        <div class="empty-state-title">¡Excelente!</div>
                        <div class="empty-state-text">No hay deudas activas</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${topDeudores.map(cliente => `
                        <div class="cliente-item">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo}, null)" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },
    
    async loadClientesSinAbono() {
        const container = document.getElementById('clientes-sin-abono');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const clientes = data.clientes_sin_abonos;
            
            if (clientes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✓</div>
                        <div class="empty-state-title">Todo al día</div>
                        <div class="empty-state-text">Todos los clientes tienen abonos recientes</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${clientes.map(cliente => `
                        <div class="cliente-item">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">Sin abono: ${cliente.dias === 'Nunca' ? 'Nunca' : cliente.dias + ' días'}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo}, ${cliente.dias === 'Nunca' ? 0 : cliente.dias})" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },

    async loadCarteraAntiguedad() {
        const container = document.getElementById('aging-buckets');
        if (!container) return;

        try {
            const { data } = await API.getDashboard();
            const buckets = data.cartera_antiguedad || [];

            if (buckets.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-title">Sin cartera activa</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="aging-grid">
                    ${buckets.map(bucket => `
                        <div class="aging-bucket">
                            <div class="label">${escapeHtml(bucket.label)}</div>
                            <div class="amount">${formatCurrency(bucket.total || 0)}</div>
                            <div class="count">${bucket.clientes || 0} cliente${bucket.clientes === 1 ? '' : 's'}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al calcular cartera</p>`;
        }
    },

    async loadColaCobro() {
        const container = document.getElementById('collection-queue');
        if (!container) return;

        try {
            const { data } = await API.getDashboard();
            const clientes = data.cola_cobro || [];

            if (clientes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-title">Sin cobros pendientes</div>
                        <div class="empty-state-text">No hay clientes con saldo activo</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="collection-list">
                    ${clientes.map(cliente => {
                        const dias = cliente.dias_sin_abonar === null || cliente.dias_sin_abonar === undefined
                            ? 'Sin abonos'
                            : `${cliente.dias_sin_abonar} dias sin abono`;
                        return `
                            <div class="collection-item">
                                <a href="/cliente/${cliente.id}" style="min-width: 0; color: inherit; text-decoration: none;">
                                    <div class="collection-name">${escapeHtml(cliente.nombre)}</div>
                                    <div class="collection-meta">${dias} - ${escapeHtml(cliente.proxima_accion || 'Enviar recordatorio')}</div>
                                </a>
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <span class="priority-badge ${escapeHtml(cliente.prioridad || 'normal')}">${escapeHtml(cliente.prioridad || 'normal')}</span>
                                    <strong>${formatCurrency(cliente.saldo || 0)}</strong>
                                    ${cliente.telefono ? `
                                        <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo || 0}, ${cliente.dias_sin_abonar || 0})" title="Enviar WhatsApp">
                                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                        </button>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al priorizar cobros</p>`;
        }
    },
    
    async loadUltimosAbonos() {
        const container = document.getElementById('ultimos-abonos');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const abonos = data.ultimos_abonos;
            
            if (abonos.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💸</div>
                        <div class="empty-state-title">Sin abonos recientes</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="timeline stagger-in">
                    ${abonos.map(abono => `
                        <div class="timeline-item abono">
                            <div class="timeline-icon">📥</div>
                            <div class="timeline-content">
                                <div class="timeline-title">${escapeHtml(abono.cliente_nombre)}</div>
                                <div class="timeline-meta">${formatDate(abono.fecha)}${abono.descripcion ? ' • ' + escapeHtml(abono.descripcion) : ''}</div>
                            </div>
                            <div class="timeline-amount positive">${formatCurrency(abono.monto)}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },
    
    async loadTopProveedores() {
        const container = document.getElementById('top-proveedores');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboardProveedores();
            const topAcreedores = data.top_acreedores;
            
            if (topAcreedores.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✓</div>
                        <div class="empty-state-title">Sin deudas</div>
                        <div class="empty-state-text">No hay deudas con proveedores</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${topAcreedores.map(proveedor => `
                        <div class="cliente-item">
                            <a href="/proveedor/${proveedor.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo" style="color: #ea580c;">${formatCurrency(proveedor.saldo)}</div>
                                ${proveedor.telefono ? `
                                    <button class="btn-whatsapp-small" style="background: #ea580c;" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.open('${proveedor.telefono}', 'Hola ${escapeHtml(proveedor.nombre)},')" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    }
};

// ==================== PÁGINA: CLIENTES ====================

function ordenarLista(data, orden) {
    const arr = [...data];
    switch (orden) {
        case 'saldo_asc':
            arr.sort((a, b) => (a.saldo || 0) - (b.saldo || 0));
            break;
        case 'nombre_asc':
            arr.sort((a, b) => (a.nombre || '').localeCompare(b.nombre || '', 'es'));
            break;
        case 'nombre_desc':
            arr.sort((a, b) => (b.nombre || '').localeCompare(a.nombre || '', 'es'));
            break;
        case 'saldo_desc':
        default:
            arr.sort((a, b) => (b.saldo || 0) - (a.saldo || 0));
    }
    return arr;
}

const Clientes = {
    orden: 'saldo_desc',

    setOrden(orden) {
        this.orden = orden;
    },

    async init() {
        await this.loadClientes();
        this.setupSearch();
    },
    
    async loadClientes() {
        const container = document.getElementById('clientes-list');
        if (!container) return;
        
        container.innerHTML = Array(5).fill(Skeleton.clienteItem()).join('');
        
        try {
            let { data } = await API.getClientes();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">👥</div>
                        <div class="empty-state-title">No hay clientes</div>
                        <div class="empty-state-text">Agrega tu primer cliente para comenzar</div>
                        <button class="btn btn-primary mt-2" onclick="Modal.open('modal-nuevo-cliente')">
                            + Nuevo Cliente
                        </button>
                    </div>
                `;
                return;
            }
            
            // Ordenar según preferencia del usuario
            data = ordenarLista(data, this.orden);
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${data.map(cliente => `
                        <div class="cliente-item stagger-in">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEditarCliente('${cliente.id}')" title="Editar cliente">✏️</button>
                                <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEliminarCliente('${cliente.id}')" title="Eliminar cliente">🗑️</button>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo || 0}, null)" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            console.error('Error al cargar clientes:', error);
            container.innerHTML = `
                <div class="empty-state">
                    <p class="text-danger">Error al cargar clientes</p>
                    <button class="btn btn-secondary mt-1" onclick="Clientes.loadClientes()">Reintentar</button>
                </div>
            `;
        }
    },
    
    setupSearch() {
        const searchInput = document.getElementById('search-clientes');
        if (!searchInput) return;
        
        const debouncedSearch = debounce(async (query) => {
            const container = document.getElementById('clientes-list');
            
            if (!query.trim()) {
                this.loadClientes();
                return;
            }
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <div class="empty-state-title">Sin resultados</div>
                            <div class="empty-state-text">No se encontraron clientes con "${escapeHtml(query)}"</div>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="clientes-list stagger-in">
                        ${ordenarLista(data, this.orden).map(cliente => `
                            <div class="cliente-item">
                                <a href="/cliente/${cliente.id}" class="cliente-info" style="flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                    <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                    <div>
                                        <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                        <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                    </div>
                                </a>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                    <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEditarCliente('${cliente.id}')" title="Editar cliente">✏️</button>
                                    <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEliminarCliente('${cliente.id}')" title="Eliminar cliente">🗑️</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (error) {
                Toast.error('Error en la búsqueda');
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
    },
    
    async crearCliente(formData) {
        try {
            const result = await API.crearCliente(formData);
            Toast.success('Cliente creado exitosamente');
            Modal.closeAll();
            this.loadClientes();
            return result;
        } catch (error) {
            Toast.error(error.message || 'Error al crear cliente');
            throw error;
        }
    }
};

// ==================== PÁGINA: DETALLE CLIENTE ====================

const ClienteDetalle = {
    clienteId: null,
    
    async init(clienteId) {
        this.clienteId = clienteId;
        await this.loadData();
    },
    
    async loadData() {
        const container = document.getElementById('cliente-content');
        if (!container) return;
        
        Loading.show(container, 'Cargando información del cliente...');
        
        try {
            const { data } = await API.getHistorial(this.clienteId);
            const { cliente, resumen, movimientos } = data;
            
            const saldoClass = resumen.saldo > 0 ? 'negative' : (resumen.saldo < 0 ? 'positive' : 'zero');
            const tieneTelefono = tieneTelefonoValido(cliente.telefono);
            const tieneDeuda = resumen.saldo > 0;
            
            container.innerHTML = `
                <div class="page-view" style="gap:0.5rem;padding:0;">
                    <!-- Top section: header + saldo + stats + actions (fixed) -->
                    <div style="flex-shrink:0;">
                        <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                            <div class="avatar-lg" style="width:48px;height:48px;font-size:1.1rem;margin:0;flex-shrink:0;">${getInitials(cliente.nombre)}</div>
                            <div style="flex:1;min-width:0;">
                                <h1 style="margin:0;font-size:1.1rem;">${escapeHtml(cliente.nombre)}</h1>
                                <p style="margin:0.1rem 0 0;font-size:0.8rem;color:var(--text-muted);">${formatTelefono(cliente.telefono)}</p>
                            </div>
                            ${tieneTelefono ? `<a href="https://wa.me/${WhatsApp.formatPhone(cliente.telefono)}" target="_blank" class="btn btn-sm" style="background:#25D366;color:white;padding:0.4rem 0.6rem;font-size:0.75rem;">📱 WhatsApp</a>` : ''}
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-bottom:0.5rem;">
                            <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:0.5rem 0.75rem;text-align:center;">
                                <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Deuda</div>
                                <div style="font-size:1.15rem;font-weight:700;color:${resumen.saldo > 0 ? 'var(--text-primary)' : 'var(--success)'};">${formatCurrency(Math.abs(resumen.saldo))}</div>
                            </div>
                            <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:0.5rem 0.75rem;text-align:center;">
                                <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Comprado</div>
                                <div style="font-size:1.15rem;font-weight:700;">${formatCurrency(resumen.total_prestado)}</div>
                            </div>
                            <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:0.5rem 0.75rem;text-align:center;">
                                <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Abonado</div>
                                <div style="font-size:1.15rem;font-weight:700;color:var(--success);">${formatCurrency(resumen.total_abonado)}</div>
                            </div>
                        </div>
                        <div style="display:flex;gap:0.5rem;margin-bottom:0.5rem;">
                            <a href="/nuevo-prestamo?cliente=${cliente.id}" class="btn btn-primary btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;">🛍️ Venta</a>
                            <a href="/nuevo-abono?cliente=${cliente.id}" class="btn btn-success btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;">💰 Abono</a>
                            <a href="/reporte-cliente/${cliente.id}" class="btn btn-secondary btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;">📄 Reporte</a>
                            ${tieneTelefono && tieneDeuda ? `
                                <button onclick="WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${resumen.saldo}, '')" class="btn btn-sm" style="background:#25D366;color:white;padding:0.5rem;font-size:0.8rem;">📱 Recordar</button>
                            ` : ''}
                        </div>
                    </div>
                    
                    <!-- Historial (scrollable) -->
                    <div class="page-body-scroll" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);min-height:0;">
                        <div style="padding:0.5rem 0.75rem;border-bottom:1px solid var(--border-color);font-size:0.85rem;font-weight:600;flex-shrink:0;">
                            <span>📋 Historial de Movimientos</span>
                        </div>
                        ${movimientos.length === 0 ? `
                            <div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:0.85rem;">
                                <div style="font-size:1.5rem;margin-bottom:0.5rem;">📝</div>
                                <div>Sin movimientos registrados</div>
                            </div>
                        ` : `
                            <table class="historial-table">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Tipo</th>
                                        <th>Descripción</th>
                                        <th>Monto</th>
                                        <th>Saldo</th>
                                    </tr>
                                </thead>
                                <tbody>
${movimientos.map((mov, idx) => {
                                    const d = getOperationDisplay(mov);
                                    return `
                                        <tr data-movimiento='${JSON.stringify(mov).replace(/'/g, "'")}' data-cliente="${escapeHtml(cliente.nombre)}" onclick="ComprobanteModal.open(this)">
                                            <td style="font-size:0.8rem;">${formatDate(mov.fecha)}</td>
                                            <td><span class="badge ${d.badgeClass}" style="font-size:0.65rem;padding:0.15rem 0.5rem;">${d.label}</span></td>
                                            <td style="font-size:0.8rem;white-space:pre-line;">${escapeHtml(mov.descripcion || '-')}</td>
                                            <td class="${d.amountClass}" style="font-size:0.85rem;">${d.sign}${formatCurrency(mov.monto)}</td>
                                            <td style="font-size:0.85rem;">${formatCurrency(mov.saldo_acumulado)}</td>
                                        </tr>
                                    `;
                                    }).join('')}
                                </tbody>
                            </table>
                        `}
                    </div>
                </div>
            `;
            
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error</div>
                    <div class="empty-state-text">${escapeHtml(error.message)}</div>
                    <a href="/" class="btn btn-primary mt-2">Volver al inicio</a>
                </div>
            `;
        }
    }
};

// ==================== PÁGINA: NUEVO ABONO ====================

const NuevoAbono = {
    selectedCliente: null,
    
    async init(clienteId = null) {
        this.setupForm();
        this.setupClienteSearch();
        
        if (clienteId) {
            await this.selectCliente(clienteId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-abono');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedCliente) {
                Toast.error('Selecciona un cliente');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                // Guardar saldo anterior
                const saldoAnterior = this.selectedCliente.saldo || 0;
                
                await API.crearMovimiento({
                    cliente_id: this.selectedCliente.id,
                    tipo: 'abono',
                    descripcion: descripcion || 'Abono',
                    monto: monto
                });
                
                const saldoNuevo = saldoAnterior - monto;
                
                Toast.success('Abono registrado exitosamente');
                
                // Mostrar panel de confirmación con WhatsApp
                this.mostrarConfirmacion(monto, descripcion || 'Abono', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar abono');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = 'Registrar Abono';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        const tieneTelefono = tieneTelefonoValido(this.selectedCliente.telefono);
        const deudaPagada = saldoNuevo <= 0;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">${deudaPagada ? '🎉' : '✅'}</div>
                <h3 style="margin-bottom: 0.5rem;">${deudaPagada ? '¡Deuda Saldada!' : '¡Abono Registrado!'}</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} recibidos de ${escapeHtml(this.selectedCliente.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Saldo anterior</p>
                            <p style="font-weight: 600;">${formatCurrency(saldoAnterior)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Saldo actual</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: ${saldoNuevo > 0 ? 'var(--danger)' : 'var(--success)'};">${formatCurrency(Math.abs(saldoNuevo))}${saldoNuevo <= 0 ? ' (saldado)' : ''}</p>
                        </div>
                    </div>
                </div>
                
                ${tieneTelefono ? `
                    <button onclick="WhatsApp.enviarComprobante('abono', '${this.selectedCliente.id}', '${escapeHtml(this.selectedCliente.nombre)}', '${this.selectedCliente.telefono}', ${monto}, '${escapeHtml(descripcion)}', ${saldoAnterior}, ${saldoNuevo})" 
                            class="btn btn-lg btn-block" 
                            style="background: #25D366; color: white; margin-bottom: 0.5rem;">
                        📱 Enviar comprobante por WhatsApp
                    </button>
                    <button onclick="WhatsApp.generarComprobante('abono', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                            class="btn btn-lg btn-block"
                            style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color); margin-bottom: 1rem;">
                        📸 Descargar comprobante como imagen
                    </button>
                ` : `
                    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--warning); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
                        <p style="font-size: 0.875rem; color: var(--warning);">
                            ⚠️ El cliente no tiene teléfono registrado
                        </p>
                        <button onclick="WhatsApp.generarComprobante('abono', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                                class="btn btn-block mt-1"
                                style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color);">
                            📸 Descargar comprobante como imagen
                        </button>
                    </div>
                `}
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/cliente/${this.selectedCliente.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Cliente
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
            </div>
        `;
    },
    
    setupClienteSearch() {
        const searchInput = document.getElementById('buscar-cliente');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) {
            console.error('No se encontraron elementos de búsqueda');
            return;
        }
        
        // Función para realizar la búsqueda
        const doSearch = async (query) => {
            resultsContainer.innerHTML = '<div class="search-result-item"><span class="text-muted">Buscando...</span></div>';
            resultsContainer.classList.add('active');
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (!data || data.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="search-result-item" style="justify-content: center;">
                            <span class="text-muted">No se encontraron clientes</span>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = data.map(cliente => `
                        <div class="search-result-item" onclick="NuevoAbono.selectCliente('${cliente.id}')">
                            <div class="cliente-info">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div>
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                </div>
                            </div>
                            <div class="cliente-saldo">${formatCurrency(cliente.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
            } catch (error) {
                console.error('Error en búsqueda:', error);
                resultsContainer.innerHTML = `
                    <div class="search-result-item" style="justify-content: center;">
                        <span class="text-danger">Error al buscar: ${escapeHtml(error.message)}</span>
                    </div>
                `;
            }
        };
        
        // Búsqueda con debounce
        const debouncedSearch = debounce(doSearch, CONFIG.DEBOUNCE_DELAY);
        
        // Búsqueda al escribir
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query) {
                debouncedSearch(query);
            } else {
                resultsContainer.classList.remove('active');
            }
        });
        
        // Mostrar todos al enfocar (si está vacío)
        searchInput.addEventListener('focus', () => {
            const query = searchInput.value.trim();
            if (!query) {
                // Cargar todos los clientes al enfocar
                doSearch('');
            } else {
                resultsContainer.classList.add('active');
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                resultsContainer.classList.remove('active');
            }
        });
    },
    
    async selectCliente(clienteId) {
        try {
            const { data } = await API.getCliente(clienteId);
            this.selectedCliente = data;
            
            const searchInput = document.getElementById('buscar-cliente');
            const clienteSeleccionado = document.getElementById('cliente-seleccionado');
            const resultsContainer = document.getElementById('resultados-busqueda');
            
            if (searchInput) searchInput.style.display = 'none';
            if (resultsContainer) resultsContainer.classList.remove('active');
            
            if (clienteSeleccionado) {
                clienteSeleccionado.innerHTML = `
                    <div class="cliente-item" style="cursor: default; border-color: var(--success);">
                        <div class="cliente-info">
                            <div class="cliente-avatar">${getInitials(data.nombre)}</div>
                            <div>
                                <div class="cliente-nombre">${escapeHtml(data.nombre)}</div>
                                <div class="cliente-deuda">Deuda actual: ${formatCurrency(data.saldo || 0)}</div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-ghost" onclick="NuevoAbono.clearCliente()">✕</button>
                    </div>
                `;
                clienteSeleccionado.style.display = 'block';
            }
            
            document.getElementById('monto')?.focus();
            
        } catch (error) {
            console.error('Error al seleccionar cliente:', error);
            Toast.error('Error al seleccionar cliente: ' + error.message);
        }
    },
    
    clearCliente() {
        this.selectedCliente = null;
        
        const searchInput = document.getElementById('buscar-cliente');
        const clienteSeleccionado = document.getElementById('cliente-seleccionado');
        
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
        
        if (clienteSeleccionado) {
            clienteSeleccionado.style.display = 'none';
        }
    }
};

// ==================== FORMULARIO NUEVO CLIENTE ====================

async function crearNuevoCliente(form) {
    const nombre = form.nombre.value.trim();
    const telefono = form.telefono.value.trim();
    
    if (!nombre) {
        Toast.error('El nombre es requerido');
        return;
    }
    
    try {
        await Clientes.crearCliente({ nombre, telefono });
        form.reset();
    } catch (error) {
        // Error ya manejado en Clientes.crearCliente
    }
}

// ==================== EDICIÓN Y ELIMINACIÓN DE CLIENTES / PROVEEDORES ====================

let _pendingDelete = null;

async function abrirEditarCliente(clienteId) {
    try {
        const { data } = await API.getCliente(clienteId);
        document.getElementById('editar-cliente-id').value = data.id;
        document.getElementById('editar-cliente-nombre').value = data.nombre || '';
        document.getElementById('editar-cliente-telefono').value = data.telefono || '';
        Modal.open('modal-editar-cliente');
    } catch (error) {
        Toast.error('Error al cargar el cliente');
    }
}

async function guardarClienteEdicion(form) {
    const id = form.editar_cliente_id.value;
    const nombre = form.editar_cliente_nombre.value.trim();
    const telefono = form.editar_cliente_telefono.value.trim();

    if (!nombre) {
        Toast.error('El nombre es requerido');
        return;
    }

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Guardando...';
    try {
        await API.actualizarCliente(id, { nombre, telefono });
        Toast.success('Cliente actualizado');
        Modal.close('modal-editar-cliente');
        Clientes.loadClientes();
    } catch (error) {
        Toast.error(error.message || 'Error al actualizar el cliente');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Guardar Cambios';
    }
}

async function abrirEditarProveedor(proveedorId) {
    try {
        const { data } = await API.getProveedor(proveedorId);
        document.getElementById('editar-proveedor-id').value = data.id;
        document.getElementById('editar-proveedor-nombre').value = data.nombre || '';
        document.getElementById('editar-proveedor-telefono').value = data.telefono || '';
        Modal.open('modal-editar-proveedor');
    } catch (error) {
        Toast.error('Error al cargar el proveedor');
    }
}

async function guardarProveedorEdicion(form) {
    const id = form.editar_proveedor_id.value;
    const nombre = form.editar_proveedor_nombre.value.trim();
    const telefono = form.editar_proveedor_telefono.value.trim();

    if (!nombre) {
        Toast.error('El nombre es requerido');
        return;
    }

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Guardando...';
    try {
        await API.actualizarProveedor(id, { nombre, telefono });
        Toast.success('Proveedor actualizado');
        Modal.close('modal-editar-proveedor');
        Proveedores.loadProveedores();
    } catch (error) {
        Toast.error(error.message || 'Error al actualizar el proveedor');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Guardar Cambios';
    }
}

async function abrirEliminarCliente(clienteId) {
    let nombre = 'este cliente';
    try {
        const { data } = await API.getCliente(clienteId);
        if (data && data.nombre) nombre = data.nombre;
    } catch (e) { /* se usa el nombre genérico */ }
    _pendingDelete = { tipo: 'cliente', id: clienteId };
    document.getElementById('eliminar-titulo').textContent = 'Eliminar cliente';
    document.getElementById('eliminar-mensaje').innerHTML = `¿Seguro que deseas eliminar a <strong>${escapeHtml(nombre)}</strong>? Se eliminará su historial y no podrá recuperarse.`;
    Modal.open('modal-confirmar-eliminar');
}

async function abrirEliminarProveedor(proveedorId) {
    let nombre = 'este proveedor';
    try {
        const { data } = await API.getProveedor(proveedorId);
        if (data && data.nombre) nombre = data.nombre;
    } catch (e) { /* se usa el nombre genérico */ }
    _pendingDelete = { tipo: 'proveedor', id: proveedorId };
    document.getElementById('eliminar-titulo').textContent = 'Eliminar proveedor';
    document.getElementById('eliminar-mensaje').innerHTML = `¿Seguro que deseas eliminar a <strong>${escapeHtml(nombre)}</strong>? Se eliminará su historial y no podrá recuperarse.`;
    Modal.open('modal-confirmar-eliminar');
}

async function confirmarEliminar() {
    if (!_pendingDelete) return;

    const btn = document.getElementById('btn-confirmar-eliminar');
    btn.disabled = true;
    btn.textContent = 'Eliminando...';
    try {
        if (_pendingDelete.tipo === 'cliente') {
            await API.eliminarCliente(_pendingDelete.id);
            Toast.success('Cliente eliminado');
            Modal.close('modal-confirmar-eliminar');
            Clientes.loadClientes();
        } else {
            await API.eliminarProveedor(_pendingDelete.id);
            Toast.success('Proveedor eliminado');
            Modal.close('modal-confirmar-eliminar');
            Proveedores.loadProveedores();
        }
    } catch (error) {
        Toast.error(error.message || 'Error al eliminar');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sí, eliminar';
        _pendingDelete = null;
    }
}

// ==================== BACKUP ====================

// ==================== PAGINA: INVENTARIO ====================

const Inventario = {
    productosCache: [],
    filtroActual: 'todos',
    categoriaActual: null,

    async init() {
        this.setupForm();
        this.setupSearch();
        await this.loadStats();
        await this.loadProductos();
        await this.loadVentas();
    },

    async loadStats() {
        const container = document.getElementById('inventario-stats');
        if (!container) return;
        try {
            const { data } = await API.getDashboardInventario();
            container.innerHTML = `
                <div class="stat-card"><div class="stat-label">Productos activos</div><div class="stat-value">${data.productos_activos || 0}</div></div>
                <div class="stat-card"><div class="stat-label">Valor inventario</div><div class="stat-value">${formatCurrency(data.valor_inventario || 0)}</div></div>
                <div class="stat-card"><div class="stat-label">Ventas hoy</div><div class="stat-value">${formatCurrency(data.ventas_hoy || 0)}</div></div>
                <div class="stat-card"><div class="stat-label">Stock bajo</div><div class="stat-value">${(data.stock_bajo || []).length}</div></div>
            `;
        } catch (error) {
            container.innerHTML = '';
        }
    },

    async loadProductos(query = '') {
        const container = document.getElementById('productos-list');
        if (!container) return;
        try {
            const response = query ? await API.buscarProductos(query) : await API.getProductos();
            this.productosCache = response.data || [];
            this.renderCategorias();
            this.renderProductos();
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar inventario</p>`;
        }
    },

    renderCategorias() {
        const container = document.getElementById('categorias-list');
        if (!container) return;
        
        const inputBusqueda = document.getElementById('search-productos');
        const isBuscando = inputBusqueda && inputBusqueda.value.trim() !== '';
        
        if (isBuscando) {
            container.innerHTML = '';
            return;
        }
        
        const categorias = [...new Set(this.productosCache.map(p => (p.categoria || 'Sin categoria').trim()))].filter(Boolean).sort();
        
        if (categorias.length === 0) {
            container.innerHTML = '<span class="text-muted" style="font-size: 0.85rem;">No hay categorías definidas</span>';
            return;
        }

        container.innerHTML = `
            <button class="btn btn-sm ${this.categoriaActual === null ? 'btn-primary' : 'btn-secondary'}" 
                    onclick="Inventario.setCategoria(null)" 
                    style="border-radius: 20px; white-space: nowrap;">
                🌟 Todas
            </button>
            ${categorias.map(cat => `
                <button class="btn btn-sm ${this.categoriaActual === cat ? 'btn-primary' : 'btn-secondary'}" 
                        onclick="Inventario.setCategoria('${escapeHtml(cat)}')" 
                        style="border-radius: 20px; white-space: nowrap;">
                    ${escapeHtml(cat)}
                </button>
            `).join('')}
        `;
    },

    setCategoria(cat) {
        this.categoriaActual = cat;
        this.renderCategorias();
        this.renderProductos();
    },

    renderProductos() {
        const container = document.getElementById('productos-list');
        if (!container) return;
        
        const inputBusqueda = document.getElementById('search-productos');
        const isBuscando = inputBusqueda && inputBusqueda.value.trim() !== '';

        if (this.categoriaActual === null && !isBuscando) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 3rem 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📂</div>
                    <div class="empty-state-title">Selecciona una categoría</div>
                    <div class="empty-state-text">Elige una categoría arriba para ver los productos o usa el buscador.</div>
                </div>
            `;
            return;
        }

        let data = this.productosCache;
        
        if (this.categoriaActual !== null && !isBuscando) {
            data = data.filter(p => (p.categoria || 'Sin categoria').trim() === this.categoriaActual);
        }

        if (this.filtroActual === 'bajo_stock') {
            data = data.filter(p => Number(p.stock || 0) <= Number(p.stock_minimo || 0));
        } else if (this.filtroActual === 'sin_stock') {
            data = data.filter(p => Number(p.stock || 0) === 0);
        }
        
        if (data.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-title">No hay productos</div><div class="empty-state-text">Sin resultados para la vista actual</div></div>`;
            return;
        }
        
        container.innerHTML = `
            <div class="clientes-list stagger-in">
                ${data.map(producto => {
                    const stock = Number(producto.stock || 0);
                    const minimo = Number(producto.stock_minimo || 0);
                    const refBadge = producto.referencia ? `<span class="badge" style="background:#475569; margin-left:0.5rem; font-weight:normal;">Ref: ${escapeHtml(producto.referencia)}</span>` : '';
                    return `
                        <div class="cliente-item">
                            <div class="cliente-info" style="flex:1; min-width:0; cursor:pointer;" onclick="Inventario.abrirEditarProducto('${producto.id}')" title="Editar Producto">
                                <div class="cliente-avatar">PR</div>
                                <div style="min-width:0;">
                                    <div class="cliente-nombre" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(producto.nombre)}${refBadge}</div>
                                    <div class="cliente-deuda">${escapeHtml(producto.categoria || 'Sin categoria')} | Stock: ${stock}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                ${stock <= minimo ? '<span class="badge badge-prestamo">Stock bajo</span>' : ''}
                                <div class="cliente-saldo">${formatCurrency(producto.precio_venta || 0)}</div>
                                <button class="btn btn-secondary btn-sm" onclick="Inventario.abrirEditarProducto('${producto.id}')" title="Editar Producto" style="padding: 0.25rem 0.5rem; border-radius: 4px;">✏️</button>
                                <button class="btn btn-secondary btn-sm" onclick="Inventario.abrirAjusteStock('${producto.id}')" title="Ajustar Stock" style="padding: 0.25rem 0.5rem; font-weight: bold; border-radius: 4px;">+/-</button>
                                <a href="/nueva-venta?producto=${producto.id}" class="btn btn-success btn-sm">Vender</a>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    },

    setFiltro(filtro) {
        this.filtroActual = filtro;
        document.getElementById('filter-todos')?.classList.replace('btn-primary', 'btn-secondary');
        document.getElementById('filter-bajo')?.classList.replace('btn-primary', 'btn-secondary');
        document.getElementById('filter-sin')?.classList.replace('btn-primary', 'btn-secondary');
        
        const map = {'todos': 'filter-todos', 'bajo_stock': 'filter-bajo', 'sin_stock': 'filter-sin'};
        document.getElementById(map[filtro])?.classList.replace('btn-secondary', 'btn-primary');
        
        this.renderProductos();
    },

    async loadVentas() {
        const container = document.getElementById('ventas-list');
        if (!container) return;
        try {
            const { data } = await API.getVentas(20);
            if (!data || data.length === 0) {
                container.innerHTML = `<div class="empty-state"><div class="empty-state-text">Aun no hay ventas registradas</div></div>`;
                return;
            }
            container.innerHTML = `
                <div style="overflow-x: auto;">
                    <table class="historial-table">
                        <thead><tr><th>Fecha</th><th>Producto</th><th>Cantidad</th><th>Total</th><th>Nota</th><th>Acción</th></tr></thead>
                        <tbody>
                            ${data.map(venta => `
                                <tr>
                                    <td>${formatDate(venta.fecha)}</td>
                                    <td>${escapeHtml(venta.producto_nombre || '-')}</td>
                                    <td>${venta.cantidad}</td>
                                    <td>${formatCurrency(venta.total || 0)}</td>
                                    <td>${escapeHtml(venta.nota || '-')}</td>
                                    <td>
                                        <button class="btn btn-sm" style="background:#ef4444; color:white; padding: 0.25rem 0.5rem;" onclick="Inventario.anularVenta('${venta.id}')" title="Anular venta y restaurar stock">Anular</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar ventas</p>`;
        }
    },

    async anularVenta(ventaId) {
        if (!confirm('¿Seguro que deseas anular esta venta? El producto será devuelto al stock.')) return;
        try {
            await API.request(`/ventas/${ventaId}`, { method: 'DELETE' });
            Toast.success('Venta anulada y stock devuelto exitosamente');
            this.loadStats();
            this.loadProductos(document.getElementById('search-productos').value);
            this.loadVentas();
        } catch(error) {
            Toast.error(error.message || 'Error al anular venta');
        }
    },

    abrirAjusteStock(productoId) {
        document.getElementById('ajuste-producto-id').value = productoId;
        document.getElementById('form-ajustar-stock').reset();
        Modal.open('modal-ajustar-stock');
    },

    abrirEditarProducto(productoId) {
        const producto = this.productosCache.find(p => p.id === productoId);
        if (!producto) return;
        
        document.getElementById('editar-producto-id').value = producto.id;
        document.getElementById('editar-producto-nombre').value = producto.nombre || '';
        document.getElementById('editar-producto-categoria').value = producto.categoria || '';
        document.getElementById('editar-producto-referencia').value = producto.referencia || '';
        document.getElementById('editar-producto-compra').value = producto.precio_compra || 0;
        document.getElementById('editar-producto-venta').value = producto.precio_venta || 0;
        document.getElementById('editar-producto-minimo').value = producto.stock_minimo || 0;
        
        // Formatear inputs monetarios si setupCurrencyInputs los afecta
        const event = new Event('input', { bubbles: true });
        document.getElementById('editar-producto-compra').dispatchEvent(event);
        document.getElementById('editar-producto-venta').dispatchEvent(event);
        
        Modal.open('modal-editar-producto');
    },

    setupSearch() {
        const input = document.getElementById('search-productos');
        if (!input) return;
        const search = debounce((query) => this.loadProductos(query), CONFIG.DEBOUNCE_DELAY);
        input.addEventListener('input', (e) => search(e.target.value));
    },

    setupForm() {
        const form = document.getElementById('form-producto');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = Object.fromEntries(new FormData(form).entries());
                data.precio_compra = parseCurrencyInput(data.precio_compra);
                data.precio_venta = parseCurrencyInput(data.precio_venta);
                data.stock = Number(data.stock || 0);
                data.stock_minimo = Number(data.stock_minimo || 0);
                try {
                    const btn = lockSubmitButton(form, 'Guardando...');
                    await API.crearProducto(data);
                    unlockSubmitButton(btn);
                    form.reset();
                    Modal.close('modal-nuevo-producto');
                    Toast.success('Producto creado');
                    await this.loadStats();
                    await this.loadProductos(document.getElementById('search-productos').value);
                } catch (error) {
                    const btn = form.querySelector('button[type="submit"]');
                    unlockSubmitButton(btn);
                    Toast.error(error.message || 'Error al guardar producto');
                }
            });
        }
        
        const formAjuste = document.getElementById('form-ajustar-stock');
        if (formAjuste) {
            formAjuste.addEventListener('submit', async (e) => {
                e.preventDefault();
                const prodId = document.getElementById('ajuste-producto-id').value;
                const accion = document.getElementById('accion_ajuste').value;
                const cantidadInput = Number(formAjuste.querySelector('input[name="cantidad"]').value);
                const nota = formAjuste.querySelector('input[name="nota"]').value;
                
                const cantidadCambio = accion === 'sumar' ? cantidadInput : -cantidadInput;
                try {
                    const btn = lockSubmitButton(formAjuste, 'Ajustando...');
                    await API.request(`/productos/${prodId}/ajustar-stock`, {
                        method: 'POST',
                        body: { cantidad_cambio: cantidadCambio, nota: nota }
                    });
                    unlockSubmitButton(btn);
                    Modal.close('modal-ajustar-stock');
                    Toast.success('Stock ajustado exitosamente');
                    this.loadStats();
                    this.loadProductos(document.getElementById('search-productos').value);
                } catch(error) {
                    unlockSubmitButton(formAjuste.querySelector('button[type="submit"]'));
                    Toast.error(error.message || 'Error ajustando stock');
                }
            });
        }
        
        const formEditar = document.getElementById('form-editar-producto');
        if (formEditar) {
            formEditar.addEventListener('submit', async (e) => {
                e.preventDefault();
                const prodId = document.getElementById('editar-producto-id').value;
                const data = Object.fromEntries(new FormData(formEditar).entries());
                
                // Formatear datos
                data.precio_compra = parseCurrencyInput(data.precio_compra);
                data.precio_venta = parseCurrencyInput(data.precio_venta);
                data.stock_minimo = Number(data.stock_minimo || 0);
                
                try {
                    const btn = lockSubmitButton(formEditar, 'Guardando...');
                    await API.request(`/productos/${prodId}`, {
                        method: 'PUT',
                        body: data
                    });
                    unlockSubmitButton(btn);
                    Modal.close('modal-editar-producto');
                    Toast.success('Producto actualizado');
                    this.loadStats();
                    this.loadProductos(document.getElementById('search-productos').value);
                } catch(error) {
                    unlockSubmitButton(formEditar.querySelector('button[type="submit"]'));
                    Toast.error(error.message || 'Error al actualizar producto');
                }
            });
        }
    }
};

const GastosPage = {
    selectedCategoria: null,

    async init() {
        this.cargarFlujoCaja();
        this.cargarGastos();
        this.setupForm();
        this.setupCategoriaTabs();
    },

    setupCategoriaTabs() {
        document.querySelectorAll('.categoria-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.categoria-tab').forEach(t => t.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.selectedCategoria = e.currentTarget.dataset.cat;
                document.getElementById('gasto-categoria').value = this.selectedCategoria;
            });
        });
    },

    formatMonto(input) {
        let value = input.value.replace(/\D/g, '');
        if (value === '') {
            input.value = '';
            return;
        }
        input.value = value.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    },

    async cargarFlujoCaja() {
        try {
            const { data } = await API.getFlujoCaja();
            const container = document.getElementById('flujo-caja');
            if (!container) return;
            
            const toNum = (v) => parseFloat(v) || 0;
            const entradas = toNum(data.ventas_total) + toNum(data.abonos_total);
            const salidas = toNum(data.pagos_proveedores_total) + toNum(data.gastos_total);
            const neto = parseFloat(data.efectivo_neto) || 0;
            
            container.innerHTML = `
                <div class="stat-card stat-card-ingresos">
                    <div class="stat-icon">📥</div>
                    <div class="stat-info">
                        <div class="stat-label">Entradas</div>
                        <div class="stat-value">${formatCurrency(entradas)}</div>
                    </div>
                </div>
                <div class="stat-card stat-card-gastos">
                    <div class="stat-icon">📤</div>
                    <div class="stat-info">
                        <div class="stat-label">Salidas</div>
                        <div class="stat-value">${formatCurrency(salidas)}</div>
                    </div>
                </div>
                <div class="stat-card stat-card-neto">
                    <div class="stat-icon">💵</div>
                    <div class="stat-info">
                        <div class="stat-label">Neto</div>
                        <div class="stat-value ${neto >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(neto)}</div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error cargando flujo de caja:', error);
        }
    },

    async cargarGastos() {
        try {
            const { data } = await API.getGastos();
            const container = document.getElementById('gastos-lista');
            if (!container) return;

            if (!data || data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-title">Sin gastos registrados</div><div class="empty-state-text">Los gastos aparecerán aquí</div></div>';
                return;
            }

            container.innerHTML = `
                <table class="historial-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Categoría</th>
                            <th>Descripción</th>
                            <th>Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(g => `
                            <tr>
                                <td>${formatDate(g.fecha)}</td>
                                <td><span class="badge badge-gasto">${g.categoria}</span></td>
                                <td>${escapeHtml(g.descripcion || '-')}</td>
                                <td class="text-danger">-${formatCurrency(g.monto)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            console.error('Error cargando gastos:', error);
        }
    },

    async registrarGasto(payload) {
        try {
            const btn = document.querySelector('#form-gasto button[type="submit"]');
            const originalText = btn.textContent;
            btn.textContent = 'Registrando...';
            btn.disabled = true;

            const res = await API.registrarGasto(payload);

            if (res.success) {
                Toast.success(`Gasto de ${formatCurrency(payload.monto)} registrado ✓`);
                document.getElementById('gasto-monto').value = '';
                document.getElementById('gasto-descripcion').value = '';
                await Promise.all([this.cargarFlujoCaja(), this.cargarGastos()]);
            }
        } catch (err) {
            Toast.error(err.message || 'Error al registrar gasto');
        } finally {
            const btn = document.querySelector('#form-gasto button[type="submit"]');
            if (btn) {
                btn.textContent = 'Registrar Gasto';
                btn.disabled = false;
            }
        }
    },

    setupForm() {
        const form = document.getElementById('form-gasto');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const monto = parseCurrencyInput(document.getElementById('gasto-monto').value);
            const descripcion = document.getElementById('gasto-descripcion').value.trim();
            const categoria = this.selectedCategoria;

            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }

            if (!categoria) {
                Toast.error('Selecciona una categoría');
                return;
            }

            await this.registrarGasto({
                categoria: categoria,
                monto: monto,
                descripcion: descripcion
            });
        });
    },

    async selectCategoria(cat) {
        this.selectedCategoria = cat;
        document.querySelectorAll('.categoria-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.categoria-tab').forEach(t => {
            if (t.dataset.cat === cat) t.classList.add('active');
        });
        document.getElementById('gasto-categoria').value = cat;
    }
};
const NuevaVenta = {
    selectedProducto: null,

    async init(productoId = null) {
        this.setupSearch();
        this.setupForm();
        this.setupTotal();
        if (productoId) await this.selectProducto(productoId);
    },

    setupSearch() {
        const input = document.getElementById('buscar-producto');
        const results = document.getElementById('resultados-busqueda');
        if (!input || !results) return;
        const doSearch = async (query) => {
            results.innerHTML = '<div class="search-result-item"><span class="text-muted">Buscando...</span></div>';
            results.classList.add('active');
            try {
                const { data } = await API.buscarProductos(query);
                if (!data || data.length === 0) {
                    results.innerHTML = '<div class="search-result-item"><span class="text-muted">Sin productos</span></div>';
                    return;
                }
                results.innerHTML = data.map(producto => `
                    <div class="search-result-item" onclick="NuevaVenta.selectProducto('${producto.id}')">
                        <div class="cliente-info">
                            <div class="cliente-avatar">PR</div>
                            <div><div class="cliente-nombre">${escapeHtml(producto.nombre)}</div><div class="cliente-deuda">Stock: ${producto.stock || 0}</div></div>
                        </div>
                        <div class="cliente-saldo">${formatCurrency(producto.precio_venta || 0)}</div>
                    </div>
                `).join('');
            } catch (error) {
                results.innerHTML = '<div class="search-result-item"><span class="text-danger">Error al buscar</span></div>';
            }
        };
        const debouncedSearch = debounce(doSearch, CONFIG.DEBOUNCE_DELAY);
        input.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        input.addEventListener('focus', () => doSearch(input.value.trim()));
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) results.classList.remove('active');
        });
    },

    setupForm() {
        const form = document.getElementById('form-venta');
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!this.selectedProducto) {
                Toast.error('Selecciona un producto');
                return;
            }
            const cantidad = Number(document.getElementById('cantidad').value || 0);
            const precioInput = document.getElementById('precio-unitario').value;
            const precio = precioInput === '' ? null : parseCurrencyInput(precioInput);
            const nota = document.getElementById('nota').value;
            try {
                const btn = lockSubmitButton(form, 'Registrando...');
                await API.crearVenta({ producto_id: this.selectedProducto.id, cantidad, precio_unitario: precio, nota });
                unlockSubmitButton(btn);
                Toast.success('Venta registrada');
                window.location.href = '/inventario';
            } catch (error) {
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                Toast.error(error.message || 'Error al registrar venta');
            }
        });
    },

    setupTotal() {
        ['cantidad', 'precio-unitario'].forEach(id => {
            document.getElementById(id)?.addEventListener('input', () => this.updateTotal());
        });
    },

    async selectProducto(productoId) {
        try {
            const { data } = await API.getProducto(productoId);
            this.selectedProducto = data;
            document.getElementById('buscar-producto').style.display = 'none';
            document.getElementById('resultados-busqueda').classList.remove('active');
            document.getElementById('precio-unitario').value = data.precio_venta || 0;
            const selected = document.getElementById('producto-seleccionado');
            selected.innerHTML = `
                <div class="cliente-item" style="cursor: default; border-color: var(--primary);">
                    <div class="cliente-info">
                        <div class="cliente-avatar">PR</div>
                        <div><div class="cliente-nombre">${escapeHtml(data.nombre)}</div><div class="cliente-deuda">Stock disponible: ${data.stock || 0}</div></div>
                    </div>
                    <button type="button" class="btn btn-ghost" onclick="NuevaVenta.clearProducto()">x</button>
                </div>
            `;
            selected.style.display = 'block';
            this.updateTotal();
            document.getElementById('cantidad')?.focus();
        } catch (error) {
            Toast.error('Error al seleccionar producto');
        }
    },

    clearProducto() {
        this.selectedProducto = null;
        const input = document.getElementById('buscar-producto');
        input.style.display = 'block';
        input.value = '';
        document.getElementById('producto-seleccionado').style.display = 'none';
        document.getElementById('precio-unitario').value = '';
        this.updateTotal();
    },

    updateTotal() {
        const cantidad = Number(document.getElementById('cantidad')?.value || 0);
        const precioInput = document.getElementById('precio-unitario')?.value;
        const precio = precioInput === '' ? Number(this.selectedProducto?.precio_venta || 0) : parseCurrencyInput(precioInput);
        const totalEl = document.getElementById('venta-total');
        if (totalEl) totalEl.textContent = formatCurrency(cantidad * precio);
    }
};

// ==================== INICIALIZACIÓN GLOBAL ====================

document.addEventListener('DOMContentLoaded', () => {
    // Configurar formateo dinámico de miles en los inputs monetarios
    setupCurrencyInputs();

    // Fecha actual en la topbar
    const dateEl = document.getElementById('topbar-date');
    if (dateEl) {
        try {
            dateEl.textContent = new Intl.DateTimeFormat('es-CO', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date());
        } catch (e) { /* ignore */ }
    }

    // Detectar página actual y ejecutar init correspondiente
    const page = document.body.dataset.page;
    SPA._initPage(page);

    // Inicializar utilidades globales (disponibles en todas las páginas)
    AppSwitcher.init();
    GlobalSearch.init();

    // Inicializar navegación SPA
    SPA.init();
});

// ==================== REPORTES POR ENTIDAD ====================

const ReporteCliente = {
    id: null,

    async init() {
        this.id = document.body.dataset.clienteId;
        if (!this.id) return;
        // Rango por defecto: primer día del mes hasta hoy
        const hoy = new Date();
        const primero = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
        const d = document.getElementById('reporte-desde');
        const h = document.getElementById('reporte-hasta');
        if (d && !d.value) d.value = primero.toISOString().split('T')[0];
        if (h && !h.value) h.value = hoy.toISOString().split('T')[0];
        await this.cargar();
    },

    async cargar() {
        const container = document.getElementById('reporte');
        if (!container) return;
        const desde = document.getElementById('reporte-desde').value;
        const hasta = document.getElementById('reporte-hasta').value;
        container.innerHTML = `<div class="loading" style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem;"><div class="spinner"></div><p style="margin-top:1rem;">Cargando reporte...</p></div>`;
        try {
            const params = new URLSearchParams();
            if (desde) params.set('desde', desde);
            if (hasta) params.set('hasta', hasta);
            const res = await fetch(`/api/reporte/cliente/${this.id}?${params.toString()}`);
            const json = await res.json();
            if (!json.success) throw new Error(json.detail || 'Error al obtener el reporte');
            this.render(json.data, json.rango);
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Error al cargar el reporte</div><div class="empty-state-text">${escapeHtml(e.message)}</div></div>`;
        }
    },

    limpiarFiltros() {
        const d = document.getElementById('reporte-desde');
        const h = document.getElementById('reporte-hasta');
        if (d) d.value = '';
        if (h) h.value = '';
        this.cargar();
    },

    render(data, rango) {
        const container = document.getElementById('reporte');
        const entidad = data.entidad;
        const r = data.resumen;
        const tiendaEl = document.getElementById('reporte-tienda');
        const tienda = tiendaEl ? tiendaEl.textContent : 'Negocio';
        const periodo = (rango.desde || rango.hasta)
            ? `Del ${rango.desde || 'inicio'} al ${rango.hasta || 'hoy'}`
            : 'Todo el historial';
        const fechaGen = new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
        const saldoPeriodoClass = r.saldo_periodo < 0 ? 'texto-negativo' : 'texto-positivo';

        const filaAbono = (m) => `
            <tr>
                <td>${formatDate(m.fecha)}</td>
                <td>${escapeHtml(m.descripcion || '-')}</td>
                <td class="monto texto-positivo">${formatCurrency(m.monto)}</td>
            </tr>`;
        const filaVenta = (m) => `
            <tr>
                <td>${formatDate(m.fecha)}</td>
                <td>${escapeHtml(m.descripcion || '-')}</td>
                <td class="monto">${formatCurrency(m.monto)}</td>
            </tr>`;

        const tablaVentas = `
            <div class="reporte-seccion">🛍️ Ventas / Compras</div>
            <table class="reporte-tabla">
                <thead><tr><th>Fecha</th><th>Descripción</th><th class="monto">Monto</th></tr></thead>
                <tbody>
                    ${data.ventas.length === 0 ? `<tr><td colspan="3" style="color:var(--text-muted);">Sin ventas en este periodo.</td></tr>` : data.ventas.map(filaVenta).join('')}
                </tbody>
                ${data.ventas.length > 0 ? `<tfoot><tr class="total"><td colspan="2">Total ventas / compras</td><td class="monto">${formatCurrency(r.total_ventas)}</td></tr></tfoot>` : ''}
            </table>`;

        const tablaAbonos = `
            <div class="reporte-seccion">💰 Abonos</div>
            <table class="reporte-tabla">
                <thead><tr><th>Fecha</th><th>Descripción</th><th class="monto">Monto</th></tr></thead>
                <tbody>
                    ${data.abonos.length === 0 ? `<tr><td colspan="3" style="color:var(--text-muted);">Sin abonos en este periodo.</td></tr>` : data.abonos.map(filaAbono).join('')}
                </tbody>
                ${data.abonos.length > 0 ? `<tfoot><tr class="total"><td colspan="2">Total abonado</td><td class="monto texto-positivo">${formatCurrency(r.total_abonos)}</td></tr></tfoot>` : ''}
            </table>`;

        container.innerHTML = `
            <div class="reporte-encabezado">
                <div>
                    <div class="reporte-titulo">📄 Reporte de Cliente</div>
                    <div style="font-weight:700;font-size:1.1rem;margin-top:0.25rem;">${escapeHtml(entidad.nombre)}</div>
                    ${entidad.telefono ? `<div class="reporte-meta">📱 ${escapeHtml(entidad.telefono)}</div>` : ''}
                    <div class="reporte-meta">🏪 ${escapeHtml(tienda)}</div>
                </div>
                <div style="text-align:right;">
                    <div class="reporte-meta">Generado: ${fechaGen}</div>
                    <div class="reporte-meta">Periodo: ${periodo}</div>
                </div>
            </div>

            <div class="reporte-card-grid">
                <div class="reporte-card">
                    <div class="label">Ventas / Compras</div>
                    <div class="value">${formatCurrency(r.total_ventas)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Abonos</div>
                    <div class="value">${formatCurrency(r.total_abonos)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Movimiento del periodo</div>
                    <div class="value ${saldoPeriodoClass}">${formatCurrency(r.saldo_periodo)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Saldo actual</div>
                    <div class="value ${r.saldo_actual > 0 ? 'texto-negativo' : ''}">${formatCurrency(r.saldo_actual)}</div>
                </div>
            </div>

            ${tablaVentas}
            ${tablaAbonos}
        `;
    }
};

const ReporteProveedor = {
    id: null,

    async init() {
        this.id = document.body.dataset.proveedorId;
        if (!this.id) return;
        const hoy = new Date();
        const primero = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
        const d = document.getElementById('reporte-desde');
        const h = document.getElementById('reporte-hasta');
        if (d && !d.value) d.value = primero.toISOString().split('T')[0];
        if (h && !h.value) h.value = hoy.toISOString().split('T')[0];
        await this.cargar();
    },

    async cargar() {
        const container = document.getElementById('reporte');
        if (!container) return;
        const desde = document.getElementById('reporte-desde').value;
        const hasta = document.getElementById('reporte-hasta').value;
        container.innerHTML = `<div class="loading" style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem;"><div class="spinner"></div><p style="margin-top:1rem;">Cargando reporte...</p></div>`;
        try {
            const params = new URLSearchParams();
            if (desde) params.set('desde', desde);
            if (hasta) params.set('hasta', hasta);
            const res = await fetch(`/api/reporte/proveedor/${this.id}?${params.toString()}`);
            const json = await res.json();
            if (!json.success) throw new Error(json.detail || 'Error al obtener el reporte');
            this.render(json.data, json.rango);
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Error al cargar el reporte</div><div class="empty-state-text">${escapeHtml(e.message)}</div></div>`;
        }
    },

    limpiarFiltros() {
        const d = document.getElementById('reporte-desde');
        const h = document.getElementById('reporte-hasta');
        if (d) d.value = '';
        if (h) h.value = '';
        this.cargar();
    },

    render(data, rango) {
        const container = document.getElementById('reporte');
        const entidad = data.entidad;
        const r = data.resumen;
        const tiendaEl = document.getElementById('reporte-tienda');
        const tienda = tiendaEl ? tiendaEl.textContent : 'Negocio';
        const periodo = (rango.desde || rango.hasta)
            ? `Del ${rango.desde || 'inicio'} al ${rango.hasta || 'hoy'}`
            : 'Todo el historial';
        const fechaGen = new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
        const saldoPeriodoClass = r.saldo_periodo < 0 ? 'texto-positivo' : 'texto-negativo';

        const filaPago = (m) => `
            <tr>
                <td>${formatDate(m.fecha)}</td>
                <td>${escapeHtml(m.descripcion || '-')}</td>
                <td class="monto texto-positivo">${formatCurrency(m.monto)}</td>
            </tr>`;
        const filaFactura = (m) => `
            <tr>
                <td>${formatDate(m.fecha)}</td>
                <td>${escapeHtml(m.descripcion || '-')}</td>
                <td class="monto">${formatCurrency(m.monto)}</td>
            </tr>`;

        const tablaFacturas = `
            <div class="reporte-seccion">📄 Facturas</div>
            <table class="reporte-tabla">
                <thead><tr><th>Fecha</th><th>Descripción</th><th class="monto">Monto</th></tr></thead>
                <tbody>
                    ${data.facturas.length === 0 ? `<tr><td colspan="3" style="color:var(--text-muted);">Sin facturas en este periodo.</td></tr>` : data.facturas.map(filaFactura).join('')}
                </tbody>
                ${data.facturas.length > 0 ? `<tfoot><tr class="total"><td colspan="2">Total facturado</td><td class="monto">${formatCurrency(r.total_facturas)}</td></tr></tfoot>` : ''}
            </table>`;

        const tablaPagos = `
            <div class="reporte-seccion">💸 Pagos</div>
            <table class="reporte-tabla">
                <thead><tr><th>Fecha</th><th>Descripción</th><th class="monto">Monto</th></tr></thead>
                <tbody>
                    ${data.pagos.length === 0 ? `<tr><td colspan="3" style="color:var(--text-muted);">Sin pagos en este periodo.</td></tr>` : data.pagos.map(filaPago).join('')}
                </tbody>
                ${data.pagos.length > 0 ? `<tfoot><tr class="total"><td colspan="2">Total pagado</td><td class="monto texto-positivo">${formatCurrency(r.total_pagado)}</td></tr></tfoot>` : ''}
            </table>`;

        container.innerHTML = `
            <div class="reporte-encabezado">
                <div>
                    <div class="reporte-titulo">📄 Reporte de Proveedor</div>
                    <div style="font-weight:700;font-size:1.1rem;margin-top:0.25rem;">${escapeHtml(entidad.nombre)}</div>
                    ${entidad.telefono ? `<div class="reporte-meta">📱 ${escapeHtml(entidad.telefono)}</div>` : ''}
                    <div class="reporte-meta">🏪 ${escapeHtml(tienda)}</div>
                </div>
                <div style="text-align:right;">
                    <div class="reporte-meta">Generado: ${fechaGen}</div>
                    <div class="reporte-meta">Periodo: ${periodo}</div>
                </div>
            </div>

            <div class="reporte-card-grid">
                <div class="reporte-card">
                    <div class="label">Facturado</div>
                    <div class="value">${formatCurrency(r.total_facturas)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Pagado</div>
                    <div class="value">${formatCurrency(r.total_pagado)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Movimiento del periodo</div>
                    <div class="value ${saldoPeriodoClass}">${formatCurrency(r.saldo_periodo)}</div>
                </div>
                <div class="reporte-card">
                    <div class="label">Saldo actual</div>
                    <div class="value ${r.saldo_actual > 0 ? 'texto-negativo' : ''}">${formatCurrency(r.saldo_actual)}</div>
                </div>
            </div>

            ${tablaFacturas}
            ${tablaPagos}
        `;
    }
};

// ==================== NAVEGACIÓN SPA (SIN RECARGAR) ====================

const SPA = {
    init() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[data-spa]');
            if (!link) return;
            e.preventDefault();
            const url = link.getAttribute('href');
            if (url && url !== window.location.pathname) {
                this.navigate(url);
            }
        });
        window.addEventListener('popstate', () => this.load(window.location.pathname, false));
    },

    async navigate(url, push = true) {
        if (push) history.pushState(null, '', url);
        await this.load(url);
    },

    async load(url) {
        const container = document.getElementById('spa-content');
        if (!container) return;

        container.innerHTML = '<div class="loading" style="padding: 4rem;"><div class="spinner"></div><p style="margin-top:1rem;color:var(--text-muted)">Cargando...</p></div>';

        try {
            const res = await fetch(url, { headers: { 'X-SPA': '1' } });
            const html = await res.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            const newContent = doc.getElementById('spa-content');
            const newBody = doc.querySelector('body');
            const newTitle = doc.querySelector('title');

            if (newContent) {
                container.innerHTML = newContent.innerHTML;
            }

            if (newTitle) document.title = newTitle.textContent;

            // Aplicar estilos extra_head de la página (sticky thead, tablas, etc.)
            const prevStyles = document.getElementById('spa-styles');
            if (prevStyles) prevStyles.remove();
            const pageStyles = doc.querySelectorAll('head style');
            if (pageStyles.length > 0) {
                const holder = document.createElement('div');
                holder.id = 'spa-styles';
                holder.style.display = 'none';
                pageStyles.forEach(s => {
                    const st = document.createElement('style');
                    st.textContent = s.textContent;
                    holder.appendChild(st);
                });
                document.head.appendChild(holder);
            }

            const newPage = newBody ? newBody.dataset.page : '';
            document.body.dataset.page = newPage;

            // Actualizar active en nav
            document.querySelectorAll('.nav-link, .sidebar-link').forEach(el => el.classList.remove('active'));
            document.querySelectorAll(`.nav-link[href="${url}"], .sidebar-link[href="${url}"]`).forEach(el => el.classList.add('active'));

            // Actualizar app badge
            const badge = document.getElementById('active-app-badge');
            if (badge && newBody) {
                const oldBadge = doc.getElementById('active-app-badge');
                if (oldBadge) badge.textContent = oldBadge.textContent;
            }

            // Cerrar app switcher si está abierto
            AppSwitcher?.close();

            // Ejecutar scripts inline del fetched document (setean dataset + handlers)
            doc.querySelectorAll('script:not([src])').forEach(s => {
                try { (0, eval)(s.textContent); } catch (e) { console.warn('SPA script error:', e); }
            });

            // Re-inicializar página (lee dataset actualizado por scripts inline)
            SPA._initPage(document.body.dataset.page);

        } catch (err) {
            console.error('SPA navigation error:', err);
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Error al cargar</div><div class="empty-state-text">${err.message}</div></div>`;
        }
    },

    _initPage(page) {
        switch (page) {
            case 'dashboard':
                Dashboard?.init();
                break;
            case 'clientes':
                Clientes?.init();
                break;
            case 'cliente-detalle':
                const clienteId = document.body.dataset.clienteId;
                if (clienteId) ClienteDetalle?.init(clienteId);
                break;
            case 'nuevo-prestamo':
                // El template inline maneja el submit; no se requiere inicialización de clase
                break;
            case 'nuevo-abono':
                NuevoAbono?.init(new URLSearchParams(window.location.search).get('cliente'));
                break;
            case 'proveedores':
                Proveedores?.init();
                break;
            case 'proveedor-detalle':
                const proveedorId = document.body.dataset.proveedorId;
                if (proveedorId) ProveedorDetalle?.init(proveedorId);
                break;
            case 'nueva-factura':
                NuevaFactura?.init(new URLSearchParams(window.location.search).get('proveedor'));
                break;
            case 'nuevo-pago-proveedor':
                NuevoPagoProveedor?.init(new URLSearchParams(window.location.search).get('proveedor'));
                break;
            case 'inventario':
                Inventario?.init();
                break;
            case 'gastos':
                GastosPage?.init();
                break;
            case 'nueva-venta':
                NuevaVenta?.init(new URLSearchParams(window.location.search).get('producto'));
                break;
            case 'reporte-cliente':
                ReporteCliente?.init();
                break;
            case 'reporte-proveedor':
                ReporteProveedor?.init();
                break;
        }
    }
};

// ==================== WHATSAPP CLICK-TO-CHAT ====================

const WhatsApp = {
    // Tienda info y plantillas - se cargan dinámicamente
    _config: null,
    
    /**
     * Obtiene la configuración completa desde la API
     */
    async getConfig() {
        if (this._config === null) {
            try {
                const response = await fetch('/api/configuracion');
                const result = await response.json();
                this._config = result.data || {};
            } catch (e) {
                console.error('Error cargando configuración para WhatsApp:', e);
                this._config = {};
            }
        }
        return this._config;
    },
    
    async getTienda() {
        const config = await this.getConfig();
        return config.nombre_tienda || 'Tecnosport';
    },
    
    /**
     * Invalida el caché de configuración
     */
    invalidarCache() {
        this._config = null;
    },
    
    /**
     * Formatea número de teléfono para WhatsApp
     */
    formatPhone(phone) {
        if (!phone) return null;
        
        // Limpiar el número
        let cleaned = phone.toString().replace(/[\s\-\(\)\+]/g, '');
        
        // Si empieza con 57, ya está en formato internacional
        if (cleaned.startsWith('57')) {
            return cleaned;
        }
        
        // Si empieza con 3 (Colombia), agregar 57
        if (cleaned.startsWith('3') && cleaned.length === 10) {
            return '57' + cleaned;
        }
        
        // Si tiene 10 dígitos y no empieza con 3, asumir Colombia
        if (cleaned.length === 10) {
            return '57' + cleaned;
        }
        
        return cleaned;
    },
    
    /**
     * Genera el link de WhatsApp
     */
    generateLink(phone, message) {
        const formattedPhone = this.formatPhone(phone);
        if (!formattedPhone) return null;
        
        const encodedMessage = encodeURIComponent(message);
        return `https://wa.me/${formattedPhone}?text=${encodedMessage}`;
    },
    
    /**
     * Abre WhatsApp con el mensaje
     */
    open(phone, message) {
        const link = this.generateLink(phone, message);
        if (!link) {
            Toast.error('El cliente no tiene teléfono registrado');
            return false;
        }
        window.open(link, '_blank');
        return true;
    },

    /**
     * Motor de plantillas: reemplaza variables en el texto
     */
    replaceVariables(text, data) {
        if (!text) return '';
        
        let result = text;
        const variables = {
            '{nombre}': data.nombre || '',
            '{monto}': data.monto ? formatCurrency(data.monto) : '$0',
            '{saldo}': data.saldo ? formatCurrency(data.saldo) : (data.saldoNuevo ? formatCurrency(data.saldoNuevo) : '$0'),
            '{fecha}': data.fecha || new Date().toLocaleDateString('es-CO', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
            }),
            '{tienda}': data.tienda || 'Negocio',
            '{descripcion}': data.descripcion || '',
            '{metodos_pago}': data.metodos_pago || ''
        };

        for (const [key, value] of Object.entries(variables)) {
            // Reemplazo global (usando RegExp para que reemplace todas las ocurrencias)
            const regex = new RegExp(key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
            result = result.replace(regex, value);
        }

        return result;
    },
    
    /**
     * Construye el bloque de métodos de pago configurados (Nequi, Bancolombia, Daviplata)
     */
    metodosPago(config) {
        const metodos = [];
        if (config.qr_pago_nequi) metodos.push(`🏦 *Nequi:* ${config.qr_pago_nequi}`);
        if (config.qr_pago_bancolombia) metodos.push(`🏦 *Bancolombia:* ${config.qr_pago_bancolombia}`);
        if (config.qr_pago_davi) metodos.push(`🏦 *Daviplata:* ${config.qr_pago_davi}`);
        return metodos;
    },

    /**
     * Genera mensaje para comprobante de abono
     */
    async mensajeAbono(nombre, monto, saldoAnterior, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        const metodos = this.metodosPago(config);
        const bloqueMetodos = metodos.length ? `\n\n💳 Puedes realizar tu pago por:\n${metodos.join('\n')}` : '';
        
        if (config.whatsapp_template_abono) {
            return this.replaceVariables(config.whatsapp_template_abono, {
                nombre, monto, saldo: saldoNuevo, tienda, metodos_pago: bloqueMetodos
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n✅ *ABONO REGISTRADO*\n\n📅 Fecha: ${fecha}\n💰 Abono: ${formatCurrency(monto)}\n📊 Saldo anterior: ${formatCurrency(saldoAnterior)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\nGracias por tu pago. 🙏${bloqueMetodos}\n\n_${tienda}_`;
    },
    
    /**
     * Genera mensaje para comprobante de préstamo
     */
    async mensajePrestamo(nombre, descripcion, monto, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        const metodos = this.metodosPago(config);
        const bloqueMetodos = metodos.length ? `\n\n💳 Puedes realizar tu pago por:\n${metodos.join('\n')}` : '';

        if (config.whatsapp_template_prestamo) {
            return this.replaceVariables(config.whatsapp_template_prestamo, {
                nombre, monto, descripcion, saldo: saldoNuevo, tienda, metodos_pago: bloqueMetodos
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n📤 *PRÉSTAMO REGISTRADO*\n\n📅 Fecha: ${fecha}\n📦 Mercancía: ${descripcion || 'No especificada'}\n💰 Valor: ${formatCurrency(monto)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\nRecuerda que puedes hacer abonos parciales. 😉\n\n_${tienda}_`;
    },
    
    /**
     * Genera mensaje para recordatorio de deuda
     */
    async mensajeRecordatorio(nombre, saldo, diasSinAbono) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        const metodos = this.metodosPago(config);
        const bloqueMetodos = metodos.length ? `\n\n💳 Puedes realizar tu pago por:\n${metodos.join('\n')}` : '';

        if (config.whatsapp_template_recordatorio) {
            return this.replaceVariables(config.whatsapp_template_recordatorio, {
                nombre, saldo, tienda, 
                descripcion: diasSinAbono ? `Han pasado ${diasSinAbono} días desde tu último abono.` : '',
                metodos_pago: bloqueMetodos
            });
        }

        return `Hola ${nombre}, 👋\n\nTe escribimos de *${tienda}* para recordarte que tienes un saldo pendiente de ${formatCurrency(saldo)}.\n\n${diasSinAbono ? `Han pasado ${diasSinAbono} días desde tu último abono.` : ''}\n\nSi deseas hacer un abono o tienes alguna pregunta, no dudes en respondernos. 🙏${bloqueMetodos}\n\n¡Gracias por tu preferencia!`;
    },
    
    /**
     * Genera mensaje para comprobante de factura de proveedor
     */
    async mensajeFactura(nombre, descripcion, monto, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();

        if (config.whatsapp_template_factura) {
            return this.replaceVariables(config.whatsapp_template_factura, {
                nombre, monto, descripcion, saldo: saldoNuevo, tienda
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n📤 *FACTURA REGISTRADA*\n\n📅 Fecha: ${fecha}\n📦 Concepto: ${descripcion || 'No especificado'}\n💰 Valor: ${formatCurrency(monto)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\n¡Gracias por el despacho! 🙏\n\n_${tienda}_`;
    },

    /**
     * Genera mensaje para comprobante de pago a proveedor
     */
    async mensajePagoProveedor(nombre, descripcion, monto, saldoAnterior, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();

        if (config.whatsapp_template_pago) {
            return this.replaceVariables(config.whatsapp_template_pago, {
                nombre, monto, descripcion, saldo: saldoNuevo, tienda
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n✅ *PAGO REALIZADO*\n\n📅 Fecha: ${fecha}\n📦 Concepto: ${descripcion || 'No especificado'}\n💰 Monto: ${formatCurrency(monto)}\n📊 Saldo anterior: ${formatCurrency(saldoAnterior)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\n¡Gracias por tu atención! 🙏\n\n_${tienda}_`;
    },

    /**
     * Envía comprobante de factura o pago de proveedor por WhatsApp
     */
    async enviarComprobanteProveedor(tipo, nombre, telefono, monto, descripcion, saldoAnterior, saldoNuevo) {
        let mensaje;
        
        if (tipo === 'pago') {
            mensaje = await this.mensajePagoProveedor(nombre, descripcion, monto, saldoAnterior, saldoNuevo);
        } else {
            mensaje = await this.mensajeFactura(nombre, descripcion, monto, saldoNuevo);
        }
        
        const enviado = this.open(telefono, mensaje);
        
        if (enviado) {
            Toast.success('Abriendo WhatsApp...');
            this.trackEnvio(1);
        }
    },

    /**
     * Envía recordatorio de deuda por WhatsApp
     */
    async enviarRecordatorio(telefono, nombre, saldo, diasSinAbono) {
        const mensaje = await this.mensajeRecordatorio(nombre, saldo, diasSinAbono);
        const enviado = this.open(telefono, mensaje);
        if (enviado) {
            Toast.success('Abriendo WhatsApp...');
        }
    },
    
    /**
     * Envía comprobante por WhatsApp
     */
    async enviarComprobante(tipo, clienteId, nombre, telefono, monto, descripcion, saldoAnterior, saldoNuevo) {
        let mensaje;
        
        if (tipo === 'abono') {
            mensaje = await this.mensajeAbono(nombre, monto, saldoAnterior, saldoNuevo);
        } else {
            mensaje = await this.mensajePrestamo(nombre, descripcion, monto, saldoNuevo);
        }
        
        const enviado = this.open(telefono, mensaje);
        
        if (enviado) {
            Toast.success('Abriendo WhatsApp...');
            this.trackEnvio(1);
        }
    },

    /**
     * Guarda estadísticas de mensajes enviados en localStorage
     */
    trackEnvio(cantidad = 1) {
        const hoy = new Date().toDateString();
        const guardado = localStorage.getItem('wa_fecha_hoy');
        let acum = parseInt(localStorage.getItem('wa_enviados_hoy') || '0');
        if (guardado !== hoy) acum = 0;
        acum += cantidad;
        localStorage.setItem('wa_enviados_hoy', acum);
        localStorage.setItem('wa_fecha_hoy', hoy);
        let total = parseInt(localStorage.getItem('wa_total_enviados') || '0');
        total += cantidad;
        localStorage.setItem('wa_total_enviados', total);
        localStorage.setItem('wa_ultimo_envio', new Date().toISOString());
    },

    /**
     * Genera un comprobante visual como imagen PNG y lo descarga.
     * Parámetros: tipo ('abono'|'prestamo'), nombre, monto, saldoNuevo, descripcion
     */
    async generarComprobante(tipo, nombre, monto, saldoNuevo, descripcion) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
        });

        const fmt = (v) => new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', maximumFractionDigits: 0
        }).format(v);

        // Verificar si mostramos el código QR de pago
        const mostrarQR = config.qr_pago_activo && (config.qr_pago_nequi || config.qr_pago_davi || config.qr_pago_bancolombia);

        const W = 480;
        const H = mostrarQR ? 430 : 320;
        
        const canvas = document.createElement('canvas');
        canvas.width = W * 2;   // Resolución doble para nitidez
        canvas.height = H * 2;
        const ctx = canvas.getContext('2d');
        ctx.scale(2, 2);

        // Fondo
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, W, H);

        // Barra superior de color
        const isAbono = tipo === 'abono';
        const accentColor = isAbono ? '#25d366' : '#6366f1';
        ctx.fillStyle = accentColor;
        ctx.fillRect(0, 0, W, 6);

        // Ícono y tipo
        ctx.fillStyle = isAbono ? 'rgba(37,211,102,0.12)' : 'rgba(99,102,241,0.12)';
        ctx.beginPath();
        ctx.arc(W / 2, 54, 30, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = 'bold 22px Arial';
        ctx.fillStyle = accentColor;
        ctx.textAlign = 'center';
        ctx.fillText(isAbono ? '✓' : '↑', W / 2, 62);

        // Título
        ctx.font = 'bold 15px Arial';
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(isAbono ? 'ABONO REGISTRADO' : 'PRÉSTAMO REGISTRADO', W / 2, 100);

        // Nombre y tienda
        ctx.font = '13px Arial';
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(nombre + ' · ' + tienda, W / 2, 120);

        // Tarjeta central
        ctx.fillStyle = '#1e293b';
        roundRect(ctx, 24, 134, W - 48, 110, 12);
        ctx.fill();

        // Monto
        ctx.font = 'bold 28px Arial';
        ctx.fillStyle = accentColor;
        ctx.textAlign = 'center';
        ctx.fillText(fmt(monto), W / 2, 170);

        // Labels
        ctx.font = '11px Arial';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'left';
        ctx.fillText(isAbono ? 'Abono recibido' : 'Valor del préstamo', 40, 195);
        ctx.textAlign = 'right';
        ctx.fillText('Saldo actual', W - 40, 195);

        ctx.font = 'bold 13px Arial';
        ctx.fillStyle = '#cbd5e1';
        ctx.textAlign = 'left';
        ctx.fillText(fmt(monto), 40, 213);
        ctx.textAlign = 'right';
        ctx.fillStyle = saldoNuevo > 0 ? '#ef4444' : '#25d366';
        ctx.fillText(fmt(saldoNuevo), W - 40, 213);

        // Descripción si existe
        if (descripcion) {
            ctx.font = '11px Arial';
            ctx.fillStyle = '#64748b';
            ctx.textAlign = 'center';
            const desc = descripcion.length > 50 ? descripcion.substring(0, 47) + '...' : descripcion;
            ctx.fillText(desc, W / 2, 233);
        }

        // Renderizar sección de código QR si está activo
        if (mostrarQR) {
            // Línea divisora punteada
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(24, 262);
            ctx.lineTo(W - 24, 262);
            ctx.stroke();
            ctx.setLineDash([]); // Reset dash

            // Crear valor de código QR estructurado para escaneo rápido
            let qrLines = [];
            qrLines.push(`** PAGO EN LINEA - ${tienda.toUpperCase()} **`);
            if (config.qr_pago_nequi) qrLines.push(`Nequi: ${config.qr_pago_nequi}`);
            if (config.qr_pago_davi) qrLines.push(`Daviplata: ${config.qr_pago_davi}`);
            if (config.qr_pago_bancolombia) qrLines.push(`Bancolombia: ${config.qr_pago_bancolombia}`);
            qrLines.push(`Valor sugerido: ${fmt(monto)}`);
            const qrValue = qrLines.join('\n');

            // Dibujar contenedor blanco del QR
            ctx.fillStyle = '#ffffff';
            roundRect(ctx, 36, 280, 106, 106, 10);
            ctx.fill();

            // Dibujar QRious de forma asíncrona
            try {
                if (typeof QRious !== 'undefined') {
                    const qr = new QRious({
                        value: qrValue,
                        size: 200,
                        level: 'H'
                    });
                    
                    const qrImg = new Image();
                    qrImg.src = qr.toDataURL();
                    await new Promise((resolve, reject) => {
                        qrImg.onload = resolve;
                        qrImg.onerror = reject;
                    });
                    
                    ctx.drawImage(qrImg, 40, 284, 98, 98);
                } else {
                    console.error('Librería QRious no está disponible.');
                    ctx.fillStyle = '#1e293b';
                    ctx.fillRect(40, 284, 98, 98);
                    ctx.font = '10px Arial';
                    ctx.fillStyle = '#94a3b8';
                    ctx.textAlign = 'center';
                    ctx.fillText('Error QR', 89, 333);
                }
            } catch (err) {
                console.error('Error dibujando código QR en canvas:', err);
            }

            // Datos de texto al lado derecho del QR
            ctx.font = 'bold 11px Arial';
            ctx.fillStyle = accentColor;
            ctx.textAlign = 'left';
            ctx.fillText('TRANSFERIR A:', 164, 292);

            ctx.font = '12px Arial';
            let textY = 312;
            if (config.qr_pago_nequi) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Nequi:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_nequi, 224, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }
            if (config.qr_pago_davi) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Daviplata:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_davi, 240, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }
            if (config.qr_pago_bancolombia) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Bancolombia:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_bancolombia, 260, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }

            ctx.font = 'italic 10px Arial';
            ctx.fillStyle = '#64748b';
            ctx.fillText('Escanea el QR para copiar datos rápidamente.', 164, 382);
        }

        // Fecha (posicionada en la parte inferior)
        ctx.font = '10px Arial';
        ctx.fillStyle = '#475569';
        ctx.textAlign = 'center';
        ctx.fillText(fecha, W / 2, H - 15);

        // Descargar
        const link = document.createElement('a');
        link.download = `comprobante_${tipo}_${nombre.replace(/\s+/g,'_')}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

        Toast.success('📸 Comprobante descargado');
    }
};

// Helper para canvas: rectángulo con bordes redondeados
function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

// Exportar funciones globales necesarias
window.Modal = Modal;
window.Toast = Toast;
window.Dashboard = Dashboard;
window.Clientes = Clientes;
window.ClienteDetalle = ClienteDetalle;
window.NuevoAbono = NuevoAbono;
window.WhatsApp = WhatsApp;
window.crearNuevoCliente = crearNuevoCliente;

// ==================== PÁGINA: PROVEEDORES ====================

const Proveedores = {
    orden: 'saldo_desc',

    setOrden(orden) {
        this.orden = orden;
    },

    async init() {
        await this.loadProveedores();
        this.setupSearch();
    },
    
    async loadProveedores() {
        const container = document.getElementById('proveedores-list');
        if (!container) return;
        
        container.innerHTML = Array(5).fill(Skeleton.clienteItem()).join('');
        
        try {
            let { data } = await API.getProveedores();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🏭</div>
                        <div class="empty-state-title">No hay proveedores</div>
                        <div class="empty-state-text">Agrega tu primer proveedor para comenzar</div>
                        <button class="btn btn-primary mt-2" onclick="Modal.open('modal-nuevo-proveedor')">
                            + Nuevo Proveedor
                        </button>
                    </div>
                `;
                return;
            }
            
            // Ordenar según preferencia del usuario
            data = ordenarLista(data, this.orden);
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${data.map(proveedor => `
                        <div class="cliente-item">
                            <a href="/proveedor/${proveedor.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(proveedor.telefono)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(proveedor.saldo)}</div>
                                <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEditarProveedor('${proveedor.id}')" title="Editar proveedor">✏️</button>
                                <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEliminarProveedor('${proveedor.id}')" title="Eliminar proveedor">🗑️</button>
                                ${proveedor.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.open('${proveedor.telefono}', 'Hola ${escapeHtml(proveedor.nombre)},')" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="text-danger">Error al cargar proveedores</p>
                    <button class="btn btn-secondary mt-1" onclick="Proveedores.loadProveedores()">Reintentar</button>
                </div>
            `;
        }
    },
    
    setupSearch() {
        const searchInput = document.getElementById('search-proveedores');
        if (!searchInput) return;
        
        const debouncedSearch = debounce(async (query) => {
            const container = document.getElementById('proveedores-list');
            
            if (!query.trim()) {
                this.loadProveedores();
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <div class="empty-state-title">Sin resultados</div>
                            <div class="empty-state-text">No se encontraron proveedores con "${escapeHtml(query)}"</div>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="clientes-list stagger-in">
                        ${ordenarLista(data, this.orden).map(proveedor => `
                            <div class="cliente-item">
                                <a href="/proveedor/${proveedor.id}" class="cliente-info" style="flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                    <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                    <div>
                                        <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                        <div class="cliente-deuda">${formatTelefono(proveedor.telefono)}</div>
                                    </div>
                                </a>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <div class="cliente-saldo">${formatCurrency(proveedor.saldo)}</div>
                                    <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEditarProveedor('${proveedor.id}')" title="Editar proveedor">✏️</button>
                                    <button class="btn btn-ghost btn-sm" onclick="event.preventDefault(); event.stopPropagation(); abrirEliminarProveedor('${proveedor.id}')" title="Eliminar proveedor">🗑️</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (error) {
                Toast.error('Error en la búsqueda');
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
    },
    
    async crearProveedor(formData) {
        try {
            const result = await API.crearProveedor(formData);
            Toast.success('Proveedor creado exitosamente');
            Modal.closeAll();
            this.loadProveedores();
            return result;
        } catch (error) {
            Toast.error(error.message || 'Error al crear proveedor');
            throw error;
        }
    }
};

// ==================== PÁGINA: DETALLE PROVEEDOR ====================

const ProveedorDetalle = {
    proveedorId: null,
    
    async init(proveedorId) {
        this.proveedorId = proveedorId;
        await this.loadData();
    },
    
    async loadData() {
        const container = document.getElementById('proveedor-content');
        if (!container) return;
        
        Loading.show(container, 'Cargando información del proveedor...');
        
        try {
            const { data } = await API.getHistorialProveedor(this.proveedorId);
            const { proveedor, resumen, movimientos } = data;
            
            const saldoClass = resumen.saldo > 0 ? 'negative' : (resumen.saldo < 0 ? 'positive' : 'zero');
            
            container.innerHTML = `
                <div class="page-view" style="gap:0.5rem;padding:0;">
                    <!-- Top section: header + saldo + stats + actions (fixed) -->
                    <div style="flex-shrink:0;">
                        <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                            <div class="avatar-lg" style="width:48px;height:48px;font-size:1.1rem;margin:0;flex-shrink:0;background:#ea580c;">${getInitials(proveedor.nombre)}</div>
                            <div style="flex:1;min-width:0;">
                                <h1 style="margin:0;font-size:1.1rem;">${escapeHtml(proveedor.nombre)}</h1>
                                <p style="margin:0.1rem 0 0;font-size:0.8rem;color:var(--text-muted);">${formatTelefono(proveedor.telefono)}</p>
                            </div>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.5rem;">
                            <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:0.5rem 0.75rem;text-align:center;">
                                <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Deuda</div>
                                <div style="font-size:1.15rem;font-weight:700;">${formatCurrency(Math.abs(resumen.saldo))}</div>
                            </div>
                            <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:0.5rem 0.75rem;text-align:center;">
                                <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">${resumen.total_facturas ? 'Facturado' : 'Pagado'}</div>
                                <div style="font-size:1.15rem;font-weight:700;">${formatCurrency(resumen.total_facturas || resumen.total_pagado)}</div>
                            </div>
                        </div>
                        <div style="display:flex;gap:0.5rem;margin-bottom:0.5rem;">
                            <a href="/nueva-factura?proveedor=${proveedor.id}" class="btn btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;background:#ea580c;color:white;">📄 Factura</a>
                            <a href="/nuevo-pago-proveedor?proveedor=${proveedor.id}" class="btn btn-success btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;">💸 Pago</a>
                            <a href="/reporte-proveedor/${proveedor.id}" class="btn btn-secondary btn-sm" style="flex:1;padding:0.5rem;font-size:0.8rem;">📄 Reporte</a>
                        </div>
                    </div>
                    
                    <!-- Historial (scrollable) -->
                    <div class="page-body-scroll" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);min-height:0;">
                        <div style="padding:0.5rem 0.75rem;border-bottom:1px solid var(--border-color);font-size:0.85rem;font-weight:600;flex-shrink:0;">
                            <span>📋 Historial de Movimientos</span>
                        </div>
                        ${movimientos.length === 0 ? `
                            <div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:0.85rem;">
                                <div style="font-size:1.5rem;margin-bottom:0.5rem;">📝</div>
                                <div>Sin movimientos registrados</div>
                            </div>
                        ` : `
                            <table class="historial-table">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Tipo</th>
                                        <th>Descripción</th>
                                        <th>Monto</th>
                                        <th>Saldo</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${movimientos.map((mov, idx) => `
                                        <tr data-movimiento='${JSON.stringify(mov).replace(/'/g, "&#39;")}' data-proveedor="${escapeHtml(proveedor.nombre)}" onclick="ComprobanteModal.open(this)">
                                            <td style="font-size:0.8rem;">${formatDate(mov.fecha)}</td>
                                            <td><span class="badge" style="background:${mov.tipo === 'factura' ? '#ea580c' : '#059669'};color:white;font-size:0.65rem;padding:0.15rem 0.5rem;">${mov.tipo}</span></td>
                                            <td style="font-size:0.8rem;white-space:pre-line;">${escapeHtml(mov.descripcion || '-')}</td>
                                            <td class="${mov.tipo === 'factura' ? 'text-danger' : 'text-success'}" style="font-size:0.85rem;">
                                                ${mov.tipo === 'factura' ? '+' : '-'}${formatCurrency(mov.monto)}
                                            </td>
                                            <td style="font-size:0.85rem;">${formatCurrency(mov.saldo_acumulado)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `}
                    </div>
                </div>
            `;
            
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error</div>
                    <div class="empty-state-text">${escapeHtml(error.message)}</div>
                    <a href="/" class="btn btn-primary mt-2">Volver al inicio</a>
                </div>
            `;
        }
    }
};

// ==================== PÁGINA: NUEVA FACTURA ====================

const NuevaFactura = {
    selectedProveedor: null,
    
    async init(proveedorId = null) {
        this.setupForm();
        this.setupProveedorSearch();
        
        if (proveedorId) {
            await this.selectProveedor(proveedorId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-factura');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedProveedor) {
                Toast.error('Selecciona un proveedor');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            const fecha = document.getElementById('fecha').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                const saldoAnterior = this.selectedProveedor.saldo || 0;
                
                await API.crearMovimientoProveedor({
                    proveedor_id: this.selectedProveedor.id,
                    tipo: 'factura',
                    descripcion: descripcion || 'Factura de proveedor',
                    monto: monto,
                    fecha: fecha || null
                });
                
                const saldoNuevo = saldoAnterior + monto;
                
                Toast.success('Factura registrada exitosamente');
                this.mostrarConfirmacion(monto, descripcion || 'Factura de proveedor', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar factura');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = '📄 Registrar Factura';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="margin-bottom: 0.5rem;">¡Factura Registrada!</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} agregados a la deuda con ${escapeHtml(this.selectedProveedor.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Concepto</p>
                            <p style="font-weight: 600; white-space: pre-line;">${escapeHtml(descripcion)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Deuda actual</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: #ea580c;">${formatCurrency(saldoNuevo)}</p>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/proveedor/${this.selectedProveedor.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Proveedor
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
                <div style="margin-top: 1rem;">
                    ${this.selectedProveedor.telefono ? `
                        <button onclick="WhatsApp.enviarComprobanteProveedor('factura', '${escapeHtml(this.selectedProveedor.nombre)}', '${this.selectedProveedor.telefono}', ${monto}, '${escapeHtml(descripcion)}', ${saldoAnterior}, ${saldoNuevo})" class="btn btn-lg" style="width:100%;background:#25D366;color:white;font-size:0.95rem;">
                            📱 Enviar Comprobante por WhatsApp
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
    setupProveedorSearch() {
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) return;
        
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `<div class="search-result-empty">No se encontraron proveedores</div>`;
                } else {
                    resultsContainer.innerHTML = data.map(proveedor => `
                        <div class="search-result-item" onclick="NuevaFactura.selectProveedor('${proveedor.id}', '${escapeHtml(proveedor.nombre)}', ${proveedor.saldo || 0}, '${proveedor.telefono || ''}')">
                            <div class="search-result-name">${escapeHtml(proveedor.nombre)}</div>
                            <div class="search-result-info">${formatTelefono(proveedor.telefono)} • Deuda: ${formatCurrency(proveedor.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error buscando proveedores:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim()) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
    async selectProveedor(proveedorId, nombre, saldo, telefono = '') {
        if (nombre === undefined) {
            try {
                const { data } = await API.getProveedor(proveedorId);
                nombre = data.nombre;
                saldo = data.saldo || 0;
                telefono = data.telefono || '';
            } catch (error) {
                Toast.error("Error al cargar proveedor");
                return;
            }
        }
        this.selectedProveedor = { id: proveedorId, nombre: nombre, saldo: saldo, telefono: telefono };
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        
        if (container) {
            container.innerHTML = `
                <div class="cliente-item" style="cursor: default; border-color: var(--success);">
                    <div class="cliente-info">
                        <div class="cliente-avatar" style="background: #ea580c; color: white;">${getInitials(nombre)}</div>
                        <div>
                            <div class="cliente-nombre">${escapeHtml(nombre)}</div>
                            <div class="cliente-deuda">Deuda actual: ${formatCurrency(saldo)}</div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="NuevaFactura.clearProveedor()">Cambiar</button>
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (searchInput) searchInput.style.display = 'none';
        if (resultsContainer) resultsContainer.classList.remove('active');
    },
    
    clearProveedor() {
        this.selectedProveedor = null;
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        
        if (container) container.style.display = 'none';
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
    }
};

// ==================== PÁGINA: NUEVO PAGO PROVEEDOR ====================

const NuevoPagoProveedor = {
    selectedProveedor: null,
    
    async init(proveedorId = null) {
        this.setupForm();
        this.setupProveedorSearch();
        
        if (proveedorId) {
            await this.selectProveedor(proveedorId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-pago-proveedor');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedProveedor) {
                Toast.error('Selecciona un proveedor');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            const fecha = document.getElementById('fecha').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                const saldoAnterior = this.selectedProveedor.saldo || 0;
                
                await API.crearMovimientoProveedor({
                    proveedor_id: this.selectedProveedor.id,
                    tipo: 'pago',
                    descripcion: descripcion || 'Pago a proveedor',
                    monto: monto,
                    fecha: fecha || null
                });
                
                const saldoNuevo = saldoAnterior - monto;
                
                Toast.success('Pago registrado exitosamente');
                this.mostrarConfirmacion(monto, descripcion || 'Pago a proveedor', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar pago');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = '💸 Registrar Pago';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="margin-bottom: 0.5rem;">¡Pago Registrado!</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} pagados a ${escapeHtml(this.selectedProveedor.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Concepto</p>
                            <p style="font-weight: 600; white-space: pre-line;">${escapeHtml(descripcion)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Deuda restante</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: ${saldoNuevo > 0 ? '#ea580c' : '#059669'};">${formatCurrency(saldoNuevo)}</p>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/proveedor/${this.selectedProveedor.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Proveedor
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
                <div style="margin-top: 1rem;">
                    ${this.selectedProveedor.telefono ? `
                        <button onclick="WhatsApp.enviarComprobanteProveedor('pago', '${escapeHtml(this.selectedProveedor.nombre)}', '${this.selectedProveedor.telefono}', ${monto}, '${escapeHtml(descripcion)}', ${saldoAnterior}, ${saldoNuevo})" class="btn btn-lg" style="width:100%;background:#25D366;color:white;font-size:0.95rem;">
                            📱 Enviar Comprobante por WhatsApp
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
    setupProveedorSearch() {
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) return;
        
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `<div class="search-result-empty">No se encontraron proveedores</div>`;
                } else {
                    resultsContainer.innerHTML = data.map(proveedor => `
                        <div class="search-result-item" onclick="NuevoPagoProveedor.selectProveedor('${proveedor.id}', '${escapeHtml(proveedor.nombre)}', ${proveedor.saldo || 0}, '${proveedor.telefono || ''}')">
                            <div class="search-result-name">${escapeHtml(proveedor.nombre)}</div>
                            <div class="search-result-info">${formatTelefono(proveedor.telefono)} • Deuda: ${formatCurrency(proveedor.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error buscando proveedores:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim()) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
    async selectProveedor(proveedorId, nombre, saldo, telefono = '') {
        if (nombre === undefined) {
            try {
                const { data } = await API.getProveedor(proveedorId);
                nombre = data.nombre;
                saldo = data.saldo || 0;
                telefono = data.telefono || '';
            } catch (error) {
                Toast.error("Error al cargar proveedor");
                return;
            }
        }
        this.selectedProveedor = { id: proveedorId, nombre: nombre, saldo: saldo, telefono: telefono };
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        
        if (container) {
            container.innerHTML = `
                <div class="cliente-item" style="cursor: default; border-color: var(--success);">
                    <div class="cliente-info">
                        <div class="cliente-avatar" style="background: #ea580c; color: white;">${getInitials(nombre)}</div>
                        <div>
                            <div class="cliente-nombre">${escapeHtml(nombre)}</div>
                            <div class="cliente-deuda">Deuda actual: ${formatCurrency(saldo)}</div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="NuevoPagoProveedor.clearProveedor()">Cambiar</button>
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (searchInput) searchInput.style.display = 'none';
        if (resultsContainer) resultsContainer.classList.remove('active');
    },
    
    clearProveedor() {
        this.selectedProveedor = null;
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        
        if (container) container.style.display = 'none';
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
    }
};

// Función global para crear nuevo proveedor
function crearNuevoProveedor(form) {
    const formData = {
        nombre: form.nombre.value,
        telefono: form.telefono.value || ''
    };
    Proveedores.crearProveedor(formData);
}

// Función para crear devolución a proveedor
function crearDevolucionProveedor(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    if (!data.descripcion.trim() || !data.monto) {
        Toast.error('Complete todos los campos requeridos');
        return;
    }
    
    const proveedorId = document.getElementById('devolucion-proveedor-id').value;
    if (!proveedorId) {
        Toast.error('Seleccione un proveedor');
        return;
    }
    
    const monto = parseCurrencyInput(document.getElementById('devolucion-monto').value);
    if (!monto || monto <= 0) {
        Toast.error('Ingrese un monto válido');
        return;
    }
    
    try {
        const btn = document.querySelector('#form-devolucion-proveedor button[type="submit"]');
        const originalText = btn.textContent;
        btn.textContent = 'Guardando...';
        btn.disabled = true;
        
        API.crearDevolucionProveedor({
            proveedor_id: document.getElementById('devolucion-proveedor-id').value,
            descripcion: data.descripcion,
            monto: monto,
            observaciones: data.observaciones || ''
        }).then(res => {
            if (res.success) {
                Toast.success('Devolución a proveedor registrada exitosamente');
                Modal.close('modal-nueva-devolucion-proveedor');
                form.reset();
            } else {
                Toast.error(res.detail || 'Error al registrar devolución');
            }
        }).catch(err => {
            Toast.error('Error: ' + err.message);
        }).finally(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        });
    } catch (err) {
        Toast.error('Error: ' + err.message);
        document.querySelector('#form-devolucion-proveedor button[type="submit"]').disabled = false;
        document.querySelector('#form-devolucion-proveedor button[type="submit"]').textContent = originalText;
    }
}

// Exportar funciones globales de proveedores
window.Proveedores = Proveedores;
window.ProveedorDetalle = ProveedorDetalle;
window.NuevaFactura = NuevaFactura;
window.NuevoPagoProveedor = NuevoPagoProveedor;
window.crearNuevoProveedor = crearNuevoProveedor;
window.crearDevolucionProveedor = crearDevolucionProveedor;

// ==================== APP SWITCHER (ODOO-STYLE) ====================

const AppSwitcher = {
    overlay: null,
    toggleBtn: null,
    closeBtn: null,
    searchInput: null,
    isOpen: false,

    init() {
        this.overlay   = document.getElementById('app-switcher-overlay');
        this.toggleBtn = document.getElementById('app-switcher-toggle');
        this.closeBtn  = document.getElementById('app-switcher-close');
        this.searchInput = document.getElementById('app-switcher-search-input');

        if (!this.overlay || !this.toggleBtn) return;

        // Abrir / cerrar al hacer clic en el botón de 9 puntos
        this.toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.isOpen ? this.close() : this.open();
        });

        // Botón "×" interno
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }

        // Cerrar al hacer clic fuera del overlay (en el fondo)
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });

        // Tecla Escape cierra el overlay
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        // Filtro de búsqueda dentro del overlay
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                this.filterApps(e.target.value.toLowerCase().trim());
            });
        }

        // Resaltar la app activa según la URL actual
        this.highlightActiveApp();
    },

    open() {
        if (!this.overlay) return;
        this.overlay.classList.add('active');
        this.isOpen = true;
        document.body.style.overflow = 'hidden';

        // Enfocar el campo de búsqueda del overlay automáticamente
        setTimeout(() => {
            if (this.searchInput) {
                this.searchInput.value = '';
                this.filterApps('');
                this.searchInput.focus();
            }
        }, 150);

        // Animar el botón de 9 puntos
        if (this.toggleBtn) {
            this.toggleBtn.classList.add('active');
        }
    },

    close() {
        if (!this.overlay) return;
        this.overlay.classList.remove('active');
        this.isOpen = false;
        document.body.style.overflow = '';

        if (this.toggleBtn) {
            this.toggleBtn.classList.remove('active');
        }
    },

    filterApps(query) {
        const cards = this.overlay ? this.overlay.querySelectorAll('.odoo-card') : [];
        cards.forEach(card => {
            const label = (card.querySelector('.odoo-label')?.textContent || '').toLowerCase();
            const match = !query || label.includes(query);
            card.style.display = match ? '' : 'none';
            card.style.opacity = match ? '1' : '0';
        });
    },

    highlightActiveApp() {
        const currentPath = window.location.pathname;
        const cards = document.querySelectorAll('#app-switcher-overlay .odoo-card');
        cards.forEach(card => {
            const href = card.getAttribute('href');
            if (href && (href === currentPath || (href !== '/' && currentPath.startsWith(href)))) {
                card.classList.add('active-app');
            }
        });
    }
};

// ==================== GLOBAL SEARCH (BUSCADOR CRUZADO) ====================

const GlobalSearch = {
    input: null,
    resultsPanel: null,
    isLoading: false,
    currentQuery: '',

    positionDropdown() {
        if (!this.input || !this.resultsPanel) return;
        const rect = this.input.getBoundingClientRect();
        const parent = this.resultsPanel.offsetParent || document.body;
        const pRect = parent.getBoundingClientRect();
        const width = Math.max(rect.width, 320);
        // El header usa backdrop-filter: crea un containing block para position:fixed,
        // por lo que las coordenadas son relativas al offsetParent y hay que restarlo.
        let left = rect.left + rect.width / 2 - width / 2 - pRect.left;
        const maxLeft = window.innerWidth - width - 8 - pRect.left;
        left = Math.min(Math.max(8 - pRect.left, left), maxLeft);
        this.resultsPanel.style.top = (rect.bottom + 8 - pRect.top) + 'px';
        this.resultsPanel.style.left = left + 'px';
        this.resultsPanel.style.width = width + 'px';
    },

    showPanel() {
        this.positionDropdown();
        this.resultsPanel.classList.add('visible');
    },

    init() {
        this.input = document.getElementById('assistant-search');
        this.resultsPanel = document.getElementById('assistant-search-results');

        if (!this.input || !this.resultsPanel) return;

        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.input.focus();
                this.input.select();
            }
            if (e.key === 'Escape' && document.activeElement === this.input) {
                this.hideResults();
                this.input.blur();
            }
        });

        const debouncedSearch = debounce((query) => this.search(query), CONFIG.DEBOUNCE_DELAY);

        this.input.addEventListener('input', (e) => {
            const q = e.target.value.trim();
            this.currentQuery = q;
            if (!q) { this.hideResults(); return; }
            this.showSkeleton();
            debouncedSearch(q);
        });

        this.input.addEventListener('focus', () => {
            if (this.currentQuery) {
                this.showPanel();
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.assistant-search-container')) {
                this.hideResults();
            }
        });

        this.input.addEventListener('keydown', (e) => this.handleKeyboard(e));
    },

    navigateTo(url) {
        this.hideResults();
        this.input.blur();
        this.input.value = '';
        this.currentQuery = '';
        window.location.href = url;
    },

    getRouteMap() {
        return {
            'inicio': '/', 'dashboard': '/', 'tablero': '/',
            'clientes': '/clientes', 'crm': '/clientes', 'contactos': '/clientes',
            'compras': '/proveedores', 'proveedores': '/proveedores', 'proveedor': '/proveedores',
            'inventario': '/inventario', 'productos': '/inventario', 'stock': '/inventario',
            'gastos': '/gastos', 'contabilidad': '/gastos',
            'whatsapp': '/recordatorios', 'recordatorios': '/recordatorios', 'mensajes': '/recordatorios',
            'configuración': '/configuracion', 'configuracion': '/configuracion', 'ajustes': '/configuracion', 'settings': '/configuracion',
        };
    },

    parseIntent(query) {
        const q = query.toLowerCase().trim();
        const routeMap = this.getRouteMap();

        // Command: "abrir X", "ir a X", "navegar a X", "abrir módulo X"
        const routeMatch = q.match(/^(abrir|ir a?|navegar a?|módulo)\s+(.+)/);
        if (routeMatch) {
            const target = routeMatch[2].trim();
            const found = Object.entries(routeMap).find(([k]) => target.includes(k) || k.includes(target));
            if (found) return { type: 'navigate', url: found[1], label: `Abrir ${found[0]}` };
        }

        // Direct module name match
        const moduleMatch = Object.entries(routeMap).find(([k]) => q === k);
        if (moduleMatch) return { type: 'navigate', url: moduleMatch[1], label: `Ir a ${moduleMatch[0]}` };

        // "vender X", "venta X", "registrar venta X"
        const sellMatch = q.match(/^(vender|vende|venta|registrar venta)\s+(.+)/);
        if (sellMatch) return { type: 'navigate', url: '/nuevo-prestamo', label: `💳 Vender: ${sellMatch[2]}`, carryQuery: sellMatch[2] };

        // "cliente X", "buscar cliente X"
        const clientMatch = q.match(/^(cliente|buscar cliente|consultar cliente)\s+(.+)/);
        if (clientMatch) return { type: 'searchClients', query: clientMatch[2] };

        // "producto X", "inventario X", "buscar producto X"
        const productMatch = q.match(/^(producto|inventario|buscar producto|buscar en inventario)\s+(.+)/);
        if (productMatch) return { type: 'searchProducts', query: productMatch[2] };

        // "proveedor X", "buscar proveedor X"
        const providerMatch = q.match(/^(proveedor|buscar proveedor)\s+(.+)/);
        if (providerMatch) return { type: 'searchProviders', query: providerMatch[2] };

        // "factura X", "buscar factura X"
        const invoiceMatch = q.match(/^(factura|buscar factura)\s+(.+)/);
        if (invoiceMatch) return { type: 'searchInvoices', query: invoiceMatch[2] };

        // "crear X"
        const createMatch = q.match(/^crear\s+(.+)/);
        if (createMatch) {
            const what = createMatch[1];
            if (/abono|pago/.test(what)) return { type: 'navigate', url: '/nuevo-abono', label: '➕ Nuevo abono' };
            if (/venta|factura|pr[eé]stamo/.test(what)) return { type: 'navigate', url: '/nuevo-prestamo', label: '🛍️ Nueva venta' };
            if (/producto/.test(what)) return { type: 'navigate', url: '/inventario', label: '📦 Nuevo producto' };
            if (/cliente/.test(what)) return { type: 'navigate', url: '/clientes', label: '👤 Nuevo cliente' };
            if (/proveedor/.test(what)) return { type: 'navigate', url: '/proveedores', label: '🏭 Nuevo proveedor' };
            if (/gasto/.test(what)) return { type: 'navigate', url: '/gastos', label: '💸 Nuevo gasto' };
            if (/devolución|devolucion/.test(what)) return { type: 'navigate', url: '/clientes', label: '🔄 Registrar devolución' };
        }

        // "registrar X"
        const regMatch = q.match(/^registrar\s+(.+)/);
        if (regMatch) {
            const what = regMatch[1];
            if (/abono|pago/.test(what)) return { type: 'navigate', url: '/nuevo-abono', label: '➕ Registrar abono' };
            if (/venta|factura/.test(what)) return { type: 'navigate', url: '/nuevo-prestamo', label: '🛍️ Registrar venta' };
            if (/devolución|devolucion/.test(what)) return { type: 'navigate', url: '/clientes', label: '🔄 Registrar devolución' };
            if (/gasto/.test(what)) return { type: 'navigate', url: '/gastos', label: '💸 Registrar gasto' };
        }

        // "mostrar X", "ver X"
        const showMatch = q.match(/^(mostrar|ver|muestra)\s+(.+)/);
        if (showMatch) {
            const what = showMatch[2];
            if (/gastos|gasto/.test(what)) return { type: 'navigate', url: '/gastos', label: '📊 Ver gastos' };
            if (/clientes|clientes?/.test(what)) return { type: 'navigate', url: '/clientes', label: '👥 Ver clientes' };
            if (/inventario|productos|producto/.test(what)) return { type: 'navigate', url: '/inventario', label: '📦 Ver inventario' };
            if (/compras|proveedores/.test(what)) return { type: 'navigate', url: '/proveedores', label: '🏭 Ver compras' };
            if (/dashboard|tablero/.test(what)) return { type: 'navigate', url: '/', label: '📊 Ver dashboard' };
            if (/hoy|día|dia/.test(q)) return { type: 'navigate', url: '/', label: '📊 Ver actividad de hoy' };
        }

        // Fallback: full search
        return { type: 'fullSearch', query: query };
    },

    async search(query) {
        if (!query) return;
        this.isLoading = true;

        const intent = this.parseIntent(query);

        // Execute based on intent
        switch (intent.type) {
            case 'navigate':
                this.renderNavigation(intent);
                return;

            case 'searchClients':
                try {
                    const res = await API.buscarClientes(intent.query);
                    const data = res?.data || [];
                    this.renderSearchResults(intent.query, data, 'clients');
                } catch { this.showError(); }
                return;

            case 'searchProducts':
                try {
                    const res = await API.buscarProductos(intent.query);
                    const data = res?.data || [];
                    this.renderSearchResults(intent.query, data, 'products');
                } catch { this.showError(); }
                return;

            case 'searchProviders':
                try {
                    const res = await API.buscarProveedores(intent.query);
                    const data = res?.data || [];
                    this.renderSearchResults(intent.query, data, 'providers');
                } catch { this.showError(); }
                return;

            case 'fullSearch':
                try {
                    const [clientesRes, productosRes, proveedoresRes] = await Promise.allSettled([
                        API.buscarClientes(query),
                        API.buscarProductos(query),
                        API.buscarProveedores(query)
                    ]);
                    const clientes = clientesRes.status === 'fulfilled' ? (clientesRes.value?.data || []) : [];
                    const productos = productosRes.status === 'fulfilled' ? (productosRes.value?.data || []) : [];
                    const proveedores = proveedoresRes.status === 'fulfilled' ? (proveedoresRes.value?.data || []) : [];
                    this.renderFullResults(query, clientes, productos, proveedores);
                } catch { this.showError(); }
                return;
        }
    },

    renderNavigation(intent) {
        if (!this.resultsPanel) return;
        this.resultsPanel.innerHTML = `
            <div class="gs-section-header" style="border:none;margin:0;">🚀 Comando</div>
            <a href="${intent.url}" class="gs-result-item gs-result-cliente" onclick="GlobalSearch.navigateTo('${intent.url}');return false;">
                <div class="gs-result-avatar" style="background:linear-gradient(135deg,var(--primary),#1d4ed8);font-size:1rem;">⚡</div>
                <div class="gs-result-info">
                    <div class="gs-result-name">${intent.label || 'Ir'}</div>
                    <div class="gs-result-meta">${intent.carryQuery ? `Parámetro: ${escapeHtml(intent.carryQuery)}` : 'Navegación directa'}</div>
                </div>
                <div class="gs-result-badge gs-badge-success">↵ Ir</div>
            </a>
        `;
        this.showPanel();
    },

    renderSearchResults(query, data, type) {
        if (!this.resultsPanel) return;
        const icon = type === 'clients' ? '👥' : type === 'products' ? '📦' : '🏭';
        const label = type === 'clients' ? 'Clientes' : type === 'products' ? 'Productos' : 'Proveedores';
        const emptyMsg = `No se encontraron ${label.toLowerCase()} para "${escapeHtml(query)}"`;
        const avatarClass = type === 'clients' ? 'gs-avatar-crm' : type === 'products' ? 'gs-avatar-inventory' : 'gs-avatar-crm';
        const hrefPrefix = type === 'clients' ? '/cliente/' : type === 'products' ? '/inventario?q=' : '/proveedores?q=';

        if (!data || data.length === 0) {
            this.resultsPanel.innerHTML = `
                <div class="gs-empty">
                    <div class="gs-empty-icon">🔍</div>
                    <div class="gs-empty-text">${emptyMsg}</div>
                    <div class="gs-empty-hint">Prueba con otro nombre o término</div>
                </div>
            `;
            this.showPanel();
            return;
        }

        let html = `<div class="gs-section-header" style="border:none;margin:0;">${icon} ${label} (${data.length})</div>`;
        html += data.slice(0, 7).map(item => {
            const name = item.nombre || item.name || '';
            const meta = item.telefono || item.email || item.categoria || '-';
            const badge = item.saldo != null
                ? `${item.saldo > 0 ? formatCurrency(item.saldo) : '✓ Al día'}`
                : item.stock != null ? `Stock: ${item.stock}` : '';
            const badgeClass = item.saldo > 0 ? 'gs-badge-danger' : (item.stock > 0 ? 'gs-badge-success' : 'gs-badge-warning');
            const link = type === 'clients' ? `/cliente/${item.id}` : type === 'products' ? `/inventario?q=${encodeURIComponent(name)}` : `/proveedor/${item.id}`;
            return `
                <a href="${link}" class="gs-result-item" onclick="if(GlobalSearch.input)GlobalSearch.navigateTo('${link}');return false;">
                    <div class="gs-result-avatar ${avatarClass}">${type === 'clients' ? getInitials(name) : icon}</div>
                    <div class="gs-result-info">
                        <div class="gs-result-name">${this.highlight(escapeHtml(name), query)}</div>
                        <div class="gs-result-meta">${escapeHtml(meta)}</div>
                    </div>
                    ${badge ? `<div class="gs-result-badge ${badgeClass}">${badge}</div>` : ''}
                </a>
            `;
        }).join('');
        if (data.length > 7) html += `<a href="#" class="gs-see-more" onclick="GlobalSearch.navigateTo('/clientes?q=${encodeURIComponent(query)}');return false;">Ver todos (${data.length}) →</a>`;
        this.resultsPanel.innerHTML = html;
        this.showPanel();
    },

    renderFullResults(query, clientes, productos, proveedores) {
        if (!this.resultsPanel) return;
        const total = clientes.length + productos.length + proveedores.length;

        if (total === 0) {
            this.resultsPanel.innerHTML = `
                <div class="gs-empty">
                    <div class="gs-empty-icon">🔍</div>
                    <div class="gs-empty-text">No se encontraron resultados para "<strong>${escapeHtml(query)}</strong>"</div>
                    <div class="gs-empty-hint">Prueba con otro nombre o término, o usa "abrir [módulo]"</div>
                </div>
            `;
            this.showPanel();
            return;
        }

        let html = '';

        // Quick commands section
        html += `<div class="gs-section-header" style="border:none;">⚡ Acciones rápidas</div>`;
        html += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.35rem;padding:0.5rem 1rem 0.75rem;">
            <a href="/nuevo-prestamo" class="gs-see-more" style="text-align:center;padding:0.4rem;font-size:0.75rem;border-radius:var(--radius-sm);" onclick="GlobalSearch.navigateTo('/nuevo-prestamo');return false;">🛍️ Venta</a>
            <a href="/nuevo-abono" class="gs-see-more" style="text-align:center;padding:0.4rem;font-size:0.75rem;border-radius:var(--radius-sm);" onclick="GlobalSearch.navigateTo('/nuevo-abono');return false;">➕ Abono</a>
        </div>`;

        if (clientes.length > 0) {
            html += `<div class="gs-section-header">👥 Clientes (${clientes.length})</div>`;
            html += clientes.slice(0, 4).map(c => {
                const tieneDeuda = c.saldo > 0;
                return `
                    <a href="/cliente/${c.id}" class="gs-result-item" onclick="GlobalSearch.navigateTo('/cliente/${c.id}');return false;">
                        <div class="gs-result-avatar gs-avatar-crm">${getInitials(c.nombre)}</div>
                        <div class="gs-result-info">
                            <div class="gs-result-name">${this.highlight(escapeHtml(c.nombre), query)}</div>
                            <div class="gs-result-meta">${c.telefono || '-'}</div>
                        </div>
                        <div class="gs-result-badge ${tieneDeuda ? 'gs-badge-danger' : 'gs-badge-success'}">${tieneDeuda ? formatCurrency(c.saldo) : '✓'}</div>
                    </a>
                `;
            }).join('');
        }

        if (productos.length > 0) {
            html += `<div class="gs-section-header">📦 Productos (${productos.length})</div>`;
            html += productos.slice(0, 4).map(p => {
                const stockOk = (p.stock || 0) > 0;
                return `
                    <a href="/inventario?q=${encodeURIComponent(p.nombre)}" class="gs-result-item" onclick="GlobalSearch.navigateTo('/inventario?q=${encodeURIComponent(p.nombre)}');return false;">
                        <div class="gs-result-avatar gs-avatar-inventory">📦</div>
                        <div class="gs-result-info">
                            <div class="gs-result-name">${this.highlight(escapeHtml(p.nombre), query)}</div>
                            <div class="gs-result-meta">${p.categoria || '-'} · $${p.precio_venta || 0}</div>
                        </div>
                        <div class="gs-result-badge ${stockOk ? 'gs-badge-success' : 'gs-badge-warning'}">${stockOk ? `S:${p.stock}` : '0'}</div>
                    </a>
                `;
            }).join('');
        }

        if (proveedores.length > 0) {
            html += `<div class="gs-section-header">🏭 Proveedores (${proveedores.length})</div>`;
            html += proveedores.slice(0, 3).map(p => `
                <a href="/proveedor/${p.id}" class="gs-result-item" onclick="GlobalSearch.navigateTo('/proveedor/${p.id}');return false;">
                    <div class="gs-result-avatar gs-avatar-crm">${getInitials(p.nombre)}</div>
                    <div class="gs-result-info">
                        <div class="gs-result-name">${this.highlight(escapeHtml(p.nombre), query)}</div>
                        <div class="gs-result-meta">${p.telefono || p.email || '-'}</div>
                    </div>
                </a>
            `).join('');
        }

        html += `<div class="gs-footer">
            <span class="gs-footer-label">🔍 ¿Buscabas algo más?</span>
            <span class="gs-footer-link" style="cursor:default;color:var(--text-muted);font-size:0.7rem;">Prueba: "cliente juan", "vender zapatos", "crear abono", "abrir compras"</span>
        </div>`;

        this.resultsPanel.innerHTML = html;
        this.showPanel();
    },

    showSkeleton() {
        if (!this.resultsPanel) return;
        this.resultsPanel.innerHTML = `
            <div class="gs-skeleton-wrap">
                <div class="gs-section-header skeleton" style="width:120px;height:14px;border-radius:6px;border:none;"></div>
                ${[1,2].map(() => `
                    <div class="gs-result-item" style="pointer-events:none;gap:0.75rem;">
                        <div class="skeleton" style="width:36px;height:36px;border-radius:50%;flex-shrink:0;"></div>
                        <div style="flex:1;">
                            <div class="skeleton" style="width:55%;height:14px;border-radius:4px;margin-bottom:6px;"></div>
                            <div class="skeleton" style="width:35%;height:11px;border-radius:4px;"></div>
                        </div>
                        <div class="skeleton" style="width:65px;height:22px;border-radius:10px;"></div>
                    </div>
                `).join('')}
            </div>
        `;
        this.showPanel();
    },

    showError() {
        if (!this.resultsPanel) return;
        this.resultsPanel.innerHTML = `
            <div class="gs-empty">
                <div class="gs-empty-icon">⚠️</div>
                <div class="gs-empty-text">Error al realizar la búsqueda</div>
                <div class="gs-empty-hint">Comprueba tu conexión e intenta de nuevo</div>
            </div>
        `;
        this.showPanel();
    },

    hideResults() {
        if (this.resultsPanel) {
            this.resultsPanel.classList.remove('visible');
        }
    },

    highlight(text, query) {
        if (!query) return text;
        try {
            const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escaped})`, 'gi');
            return text.replace(regex, '<mark class="gs-highlight">$1</mark>');
        } catch { return text; }
    },

    handleKeyboard(e) {
        const items = this.resultsPanel
            ? Array.from(this.resultsPanel.querySelectorAll('.gs-result-item'))
            : [];
        if (!items.length) return;

        const focused = this.resultsPanel.querySelector('.gs-result-item.focused');
        let idx = focused ? items.indexOf(focused) : -1;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (focused) focused.classList.remove('focused');
            idx = (idx + 1) % items.length;
            items[idx].classList.add('focused');
            items[idx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (focused) focused.classList.remove('focused');
            idx = (idx - 1 + items.length) % items.length;
            items[idx].classList.add('focused');
            items[idx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            if (focused) {
                e.preventDefault();
                const href = focused.getAttribute('href');
                if (href) this.navigateTo(href);
            }
        }
    }
};

// ==================== COMPROBANTE MODAL ====================
// Reutiliza el diseño Canvas del comprobante moderno existente

async function _drawComprobante(canvas, tipo, nombre, monto, saldoAnterior, saldoNuevo, descripcion, fecha, hora, metodoPago, referencia) {
    const config = await WhatsApp.getConfig();
    const tienda = await WhatsApp.getTienda();

    const fmt = (v) => new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', maximumFractionDigits: 0
    }).format(v);

    const mostrarQR = config.qr_pago_activo && (config.qr_pago_nequi || config.qr_pago_davi || config.qr_pago_bancolombia);

    const W = 500;
    const H = mostrarQR ? 530 : 400;

    canvas.width = W * 2;
    canvas.height = H * 2;
    const ctx = canvas.getContext('2d');
    ctx.scale(2, 2);

    const isAbono = tipo === 'abono' || tipo === 'pago';
    const accentColor = isAbono ? '#25d366' : '#6366f1';

    // Fondo
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, W, H);

    // Barra superior
    ctx.fillStyle = accentColor;
    ctx.fillRect(0, 0, W, 6);

    // Icono
    ctx.fillStyle = isAbono ? 'rgba(37,211,102,0.12)' : 'rgba(99,102,241,0.12)';
    ctx.beginPath();
    ctx.arc(W / 2, 50, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = 'bold 22px Arial';
    ctx.fillStyle = accentColor;
    ctx.textAlign = 'center';
    ctx.fillText(isAbono ? '✓' : '↑', W / 2, 58);

    // Titulo
    ctx.font = 'bold 14px Arial';
    ctx.fillStyle = '#f8fafc';
    ctx.fillText(isAbono ? 'PAGO REGISTRADO' : 'PRÉSTAMO REGISTRADO', W / 2, 94);

    // Nombre y tienda
    ctx.font = '12px Arial';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(nombre + ' · ' + tienda, W / 2, 113);

    // Tarjeta central: monto grande + resumen saldo
    ctx.fillStyle = '#1e293b';
    _roundRect(ctx, 30, 128, W - 60, 110, 10);
    ctx.fill();

    // Monto grande
    ctx.font = 'bold 28px Arial';
    ctx.fillStyle = accentColor;
    ctx.textAlign = 'center';
    ctx.fillText(fmt(monto), W / 2, 165);

        // Grid de 3 columnas: Saldo anterior | Valor pagado | Saldo restante
        ctx.font = '10px Arial';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'left';
        ctx.fillText(isAbono ? 'Saldo anterior' : 'Saldo anterior', 46, 185);
        ctx.textAlign = 'center';
        ctx.fillText(isAbono ? 'Valor pagado' : 'Monto', W / 2, 185);
        ctx.textAlign = 'right';
        ctx.fillText('Saldo restante', W - 46, 185);

        // Valores bajo labels
        ctx.font = 'bold 12px Arial';
        ctx.fillStyle = '#cbd5e1';
        ctx.textAlign = 'left';
        ctx.fillText(fmt(saldoAnterior !== undefined ? saldoAnterior : 0), 46, 205);
        ctx.textAlign = 'center';
        ctx.fillText(fmt(monto), W / 2, 205);
        ctx.textAlign = 'right';
        ctx.fillStyle = saldoNuevo > 0 ? '#ef4444' : '#25d366';
        ctx.fillText(fmt(saldoNuevo), W - 46, 205);

    // Descripcion
    if (descripcion) {
        ctx.font = '10px Arial';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'center';
        const desc = descripcion.length > 55 ? descripcion.substring(0, 52) + '...' : descripcion;
        ctx.fillText('Observaciones: ' + desc, W / 2, 225);
    }

    // Metodo de pago y referencia
    const extraY = descripcion ? 240 : 228;
    if (metodoPago || referencia) {
        ctx.font = '10px Arial';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'left';
        let extraX = 46;
        if (metodoPago) {
            ctx.fillText('Metodo de pago:', extraX, extraY);
            ctx.font = 'bold 10px Arial';
            ctx.fillStyle = '#cbd5e1';
            ctx.fillText(metodoPago, extraX + 88, extraY);
            ctx.font = '10px Arial';
            ctx.fillStyle = '#64748b';
            extraX = 46;
        }
        if (referencia) {
            const refY = metodoPago ? extraY + 14 : extraY;
            ctx.fillText('Referencia:', extraX, refY);
            ctx.font = 'bold 10px Arial';
            ctx.fillStyle = '#cbd5e1';
            ctx.fillText('#' + referencia, extraX + 60, refY);
        }
    }

    // QR section
    if (mostrarQR) {
        const qrY = 258;
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(30, qrY);
        ctx.lineTo(W - 30, qrY);
        ctx.stroke();
        ctx.setLineDash([]);

        let qrLines = [];
        qrLines.push('** PAGO EN LINEA - ' + tienda.toUpperCase() + ' **');
        if (config.qr_pago_nequi) qrLines.push('Nequi: ' + config.qr_pago_nequi);
        if (config.qr_pago_davi) qrLines.push('Daviplata: ' + config.qr_pago_davi);
        if (config.qr_pago_bancolombia) qrLines.push('Bancolombia: ' + config.qr_pago_bancolombia);
        qrLines.push('Valor sugerido: ' + fmt(monto));
        const qrValue = qrLines.join('\n');

        ctx.fillStyle = '#ffffff';
        _roundRect(ctx, 40, qrY + 22, 106, 106, 10);
        ctx.fill();

        try {
            if (typeof QRious !== 'undefined') {
                const qr = new QRious({ value: qrValue, size: 200, level: 'H' });
                const qrImg = new Image();
                qrImg.src = qr.toDataURL();
                await new Promise((resolve, reject) => {
                    qrImg.onload = resolve;
                    qrImg.onerror = reject;
                });
                ctx.drawImage(qrImg, 44, qrY + 26, 98, 98);
            } else {
                ctx.fillStyle = '#1e293b';
                ctx.fillRect(44, qrY + 26, 98, 98);
                ctx.font = '10px Arial';
                ctx.fillStyle = '#94a3b8';
                ctx.textAlign = 'center';
                ctx.fillText('Error QR', 93, qrY + 74);
            }
        } catch (err) {
            console.error('Error dibujando QR:', err);
        }

        ctx.font = 'bold 10px Arial';
        ctx.fillStyle = accentColor;
        ctx.textAlign = 'left';
        ctx.fillText('TRANSFERIR A:', 168, qrY + 36);

        ctx.font = '11px Arial';
        let textY = qrY + 56;
        if (config.qr_pago_nequi) {
            ctx.fillStyle = '#64748b';
            ctx.fillText('• Nequi:', 168, textY);
            ctx.fillStyle = '#f8fafc';
            ctx.font = 'bold 11px Arial';
            ctx.fillText(config.qr_pago_nequi, 228, textY);
            ctx.font = '11px Arial';
            textY += 18;
        }
        if (config.qr_pago_davi) {
            ctx.fillStyle = '#64748b';
            ctx.fillText('• Daviplata:', 168, textY);
            ctx.fillStyle = '#f8fafc';
            ctx.font = 'bold 11px Arial';
            ctx.fillText(config.qr_pago_davi, 244, textY);
            ctx.font = '11px Arial';
            textY += 18;
        }
        if (config.qr_pago_bancolombia) {
            ctx.fillStyle = '#64748b';
            ctx.fillText('• Bancolombia:', 168, textY);
            ctx.fillStyle = '#f8fafc';
            ctx.font = 'bold 11px Arial';
            ctx.fillText(config.qr_pago_bancolombia, 264, textY);
            ctx.font = '11px Arial';
            textY += 18;
        }

        ctx.font = 'italic 9px Arial';
        ctx.fillStyle = '#64748b';
        ctx.fillText('Escanea el QR para copiar datos.', 168, qrY + 128);
    }

    // Fecha y hora en el footer
    ctx.font = '10px Arial';
    ctx.fillStyle = '#475569';
    ctx.textAlign = 'center';
    const footerText = hora ? fecha + ' - ' + hora : fecha;
    ctx.fillText(footerText, W / 2, H - 16);
}

function _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

const ComprobanteModal = {
    overlay: null,
    canvas: null,

    async open(triggerEl) {
        const raw = triggerEl.dataset.movimiento;
        if (!raw) return;
        const mov = JSON.parse(raw);
        const nombre = triggerEl.dataset.cliente || triggerEl.dataset.proveedor || '';

        const esPrestamo = mov.tipo === 'prestamo' || mov.tipo === 'factura';
        const saldoAnterior = esPrestamo
            ? mov.saldo_acumulado - mov.monto
            : mov.saldo_acumulado + mov.monto;

        const fechaFormatted = mov.fecha ? new Date(mov.fecha + 'T12:00:00').toLocaleDateString('es-CO', {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
        }) : '-';

        const hora = mov.timestamp ? mov.timestamp.split(' ')[1] || '' : '';

        const metodoPago = mov.metodo_pago || null;
        const referencia = mov.referencia || null;
        const observaciones = mov.descripcion || mov.observaciones || null;

        await this._show({
            tipo: mov.tipo,
            nombre,
            monto: mov.monto,
            saldoAnterior,
            saldoNuevo: mov.saldo_acumulado,
            descripcion: observaciones,
            fecha: fechaFormatted,
            hora,
            metodoPago,
            referencia
        });
    },

    async _show(data) {
        this._cleanup();

        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay comprobante-overlay';
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });

        const wrapper = document.createElement('div');
        wrapper.className = 'comprobante-wrapper';

        this.canvas = document.createElement('canvas');
        this.canvas.className = 'comprobante-canvas';

        await _drawComprobante(
            this.canvas,
            data.tipo,
            data.nombre,
            data.monto,
            data.saldoAnterior,
            data.saldoNuevo,
            data.descripcion,
            data.fecha,
            data.hora,
            data.metodoPago,
            data.referencia
        );

        wrapper.appendChild(this.canvas);

        const actions = document.createElement('div');
        actions.className = 'comprobante-actions';
        actions.innerHTML = `
            <button class="btn btn-primary comprobante-btn" onclick="ComprobanteModal._print()">
                🖨️ Imprimir
            </button>
            <button class="btn btn-primary comprobante-btn" onclick="ComprobanteModal._download()">
                📄 Descargar PDF
            </button>
            <button class="btn btn-primary comprobante-btn" onclick="ComprobanteModal._share()">
                📤 Compartir
            </button>
            <button class="btn comprobante-btn comprobante-btn-close" onclick="ComprobanteModal.close()">
                Cerrar
            </button>
        `;
        wrapper.appendChild(actions);

        this.overlay.appendChild(wrapper);
        document.body.appendChild(this.overlay);

        document.addEventListener('keydown', this._keyHandler = (e) => {
            if (e.key === 'Escape') this.close();
        });

        requestAnimationFrame(() => this.overlay.classList.add('active'));
        document.body.style.overflow = 'hidden';
    },

    _cleanup() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
            this._keyHandler = null;
        }
        document.body.style.overflow = '';
    },

    close() {
        this._cleanup();
    },

    _print() {
        if (!this.canvas) return;
        const dataUrl = this.canvas.toDataURL('image/png');
        const win = window.open('');
        win.document.write(`
            <html><head><title>Comprobante</title>
            <style>body{margin:0;display:flex;justify-content:center;padding:20px}
            img{max-width:100%;height:auto}</style></head>
            <body><img src="${dataUrl}" onload="window.print();window.close()"></body></html>
        `);
        win.document.close();
    },

    _download() {
        if (!this.canvas) return;
        const tipo = this.overlay ? 'comprobante' : 'comprobante';
        const link = document.createElement('a');
        link.download = 'comprobante.png';
        link.href = this.canvas.toDataURL('image/png');
        link.click();
        Toast.success('📄 Comprobante descargado');
    },

    _share() {
        if (!this.canvas) return;
        this.canvas.toBlob(async (blob) => {
            if (navigator.share && navigator.canShare) {
                try {
                    const file = new File([blob], 'comprobante.png', { type: 'image/png' });
                    await navigator.share({ files: [file], title: 'Comprobante' });
                } catch (e) {
                    if (e.name !== 'AbortError') this._download();
                }
            } else {
                this._download();
                Toast.info('Comparte la imagen descargada');
            }
        });
    }
};

// Exportar módulos globales de UI
window.API = API;
window.AppSwitcher = AppSwitcher;
window.GlobalSearch = GlobalSearch;
window.ComprobanteModal = ComprobanteModal;

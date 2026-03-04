/* main.js — Sistema de Compras UNAPEC */

document.addEventListener('DOMContentLoaded', function () {

  // ── Auto-dismiss de alertas flash ──────────────────────────────────────────
  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 4000); // desaparece después de 4 segundos
  });

  // ── Confirmación antes de enviar formularios de eliminación ───────────────
  // (respaldo por si el usuario deshabilita el template de confirmación)
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm(form.dataset.confirm || '¿Estás seguro?')) {
        e.preventDefault();
      }
    });
  });

});

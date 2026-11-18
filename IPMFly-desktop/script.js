// T3: Script inicial con validación muy básica y carente de gestión ARIA o control de foco
document.getElementById('vuelo-form').addEventListener('submit', function(event) {
    const email = document.getElementById('email').value;
    const telefono = document.getElementById('telefono').value;
    const nombre = document.getElementById('nombre').value;

    // Validación rudimentaria mediante alerts (mala UX y nada accesible)
    if (nombre.trim() === "") {
        alert("El campo nombre es obligatorio.");
        event.preventDefault();
        return;
    }

    if (email.trim() === "" || !email.includes("@")) {
        alert("Por favor, introduce un correo electrónico válido.");
        event.preventDefault();
        return;
    }

    if (telefono.trim() === "" || telefono.length < 9) {
        alert("El teléfono debe tener al menos 9 dígitos.");
        event.preventDefault();
        return;
    }

    alert("¡Formulario validado con éxito!");
});

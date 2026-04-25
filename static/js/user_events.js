(function () {
    const p = new URLSearchParams(window.location.search);
    if (p.has('registered')) {
        window.history.replaceState({}, '', window.location.pathname);
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: 'Registered!',
            text: 'Your QR code has been emailed to you.',
            showConfirmButton: false,
            timer: 4500,
            timerProgressBar: true,
        });
    }
})();

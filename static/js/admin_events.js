(function () {
    /* ── Pagination ── */
    const rowsPerPage = 6;
    let currentPage = 1;
    // Note: since events use a grid layout with col-12 col-md-6 wrappers,
    // we should paginate the immediate parent of `.event-card`
    const allEventCards = Array.from(document.querySelectorAll('.event-card')).map(card => card.parentElement);
    let filteredEvents = [...allEventCards];

    function renderPagination() {
        const totalPages = Math.ceil(filteredEvents.length / rowsPerPage);
        const start = (currentPage - 1) * rowsPerPage;
        const end = start + rowsPerPage;

        allEventCards.forEach(r => r.style.display = 'none');
        filteredEvents.slice(start, end).forEach(r => r.style.display = '');

        const info = document.getElementById('paginationInfo');
        if (info) {
            info.textContent = filteredEvents.length === 0 
                ? 'Showing 0 to 0 of 0 events'
                : `Showing ${start + 1} to ${Math.min(end, filteredEvents.length)} of ${filteredEvents.length} events`;
        }

        const controls = document.getElementById('paginationControls');
        if (controls) {
            let html = '';
            html += `<button class="btn btn-sm btn-outline-secondary" ${currentPage === 1 ? 'disabled' : ''} onclick="window.goToEventPage(${currentPage - 1})"><i class="bi bi-chevron-left"></i></button>`;
            
            let startPage = Math.max(1, currentPage - 2);
            let endPage = Math.min(totalPages, startPage + 4);
            if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);
            
            for (let i = startPage; i <= endPage; i++) {
                html += `<button class="btn btn-sm ${i === currentPage ? 'btn-primary' : 'btn-outline-secondary'}" onclick="window.goToEventPage(${i})">${i}</button>`;
            }
            
            html += `<button class="btn btn-sm btn-outline-secondary" ${currentPage >= totalPages || totalPages === 0 ? 'disabled' : ''} onclick="window.goToEventPage(${currentPage + 1})"><i class="bi bi-chevron-right"></i></button>`;
            controls.innerHTML = html;
        }
    }

    window.goToEventPage = function(page) {
        currentPage = page;
        renderPagination();
    };

    // Initialize pagination
    renderPagination();

    /* ── Form HTML builder ── */
    function buildFormHtml(vals) {
        vals = vals || {};
        return '<div class="ef-form">' +
            '<div class="ef-group">' +
                '<div class="ef-label"><i class="bi bi-type-h1"></i> Event Title <span class="text-danger">*</span></div>' +
                '<input id="swalTitle" class="ef-input" placeholder="e.g. Open Dev Summit \'26" value="' + (vals.title || '').replace(/"/g, '&quot;') + '">' +
            '</div>' +
            '<div class="ef-group">' +
                '<div class="ef-label"><i class="bi bi-text-paragraph"></i> Description</div>' +
                '<textarea id="swalDesc" class="ef-input" rows="2" placeholder="Brief description…">' + (vals.description || '') + '</textarea>' +
            '</div>' +
            '<div class="ef-group">' +
                '<div class="ef-label"><i class="bi bi-geo-alt"></i> Location</div>' +
                '<input id="swalLocation" class="ef-input" placeholder="e.g. Main Auditorium" value="' + (vals.location || '').replace(/"/g, '&quot;') + '">' +
            '</div>' +
            '<div class="ef-row">' +
                '<div class="ef-group ef-half">' +
                    '<div class="ef-label"><i class="bi bi-calendar-event"></i> Start</div>' +
                    '<input id="swalStart" class="ef-input" type="datetime-local" value="' + (vals.start_time || '') + '">' +
                '</div>' +
                '<div class="ef-group ef-half">' +
                    '<div class="ef-label"><i class="bi bi-calendar-check"></i> End</div>' +
                    '<input id="swalEnd" class="ef-input" type="datetime-local" value="' + (vals.end_time || '') + '">' +
                '</div>' +
            '</div>' +
            '<div class="ef-group">' +
                '<div class="ef-label"><i class="bi bi-image"></i> Cover Image URL</div>' +
                '<input id="swalImage" class="ef-input" placeholder="https://..." value="' + (vals.image_url || '').replace(/"/g, '&quot;') + '">' +
            '</div>' +
            '<div class="ef-group">' +
                '<div class="ef-label"><i class="bi bi-whatsapp"></i> WhatsApp Group Link</div>' +
                '<input id="swalWhatsapp" class="ef-input" placeholder="https://chat.whatsapp.com/..." value="' + (vals.whatsapp_link || '').replace(/"/g, '&quot;') + '">' +
            '</div>' +
            '<div class="ef-divider"></div>' +
            '<label class="ef-toggle">' +
                '<input id="swalActive" type="checkbox"' + (vals.is_active ? ' checked' : '') + '>' +
                '<div>' +
                    '<div class="ef-toggle-label">Set as active event</div>' +
                    '<div class="ef-toggle-hint">Other active events will be deactivated</div>' +
                '</div>' +
            '</label>' +
            '</div>';
    }

    function getFormValues() {
        var title = document.getElementById('swalTitle').value.trim();
        if (!title) { Swal.showValidationMessage('Title is required'); return false; }
        return {
            title: title,
            description: document.getElementById('swalDesc').value.trim(),
            location: document.getElementById('swalLocation').value.trim(),
            start_time: document.getElementById('swalStart').value,
            end_time: document.getElementById('swalEnd').value,
            image_url: document.getElementById('swalImage').value.trim(),
            whatsapp_link: document.getElementById('swalWhatsapp').value.trim(),
            is_active: document.getElementById('swalActive').checked
        };
    }

    /* ── Create Event Modal ── */
    document.getElementById('createEventBtn').addEventListener('click', function () {
        Swal.fire({
            title: 'Create New Event',
            html: buildFormHtml(),
            showCancelButton: true,
            confirmButtonText: '<i class="bi bi-plus-lg me-1"></i>Create Event',
            confirmButtonColor: '#a855f7',
            cancelButtonColor: '#64748b',
            reverseButtons: true,
            customClass: { popup: 'rounded-4', htmlContainer: 'text-start' },
            width: 'min(520px, 95vw)',
            preConfirm: getFormValues
        }).then(function (result) {
            if (result.isConfirmed) {
                var d = result.value;
                document.getElementById('formTitle').value = d.title;
                document.getElementById('formDescription').value = d.description;
                document.getElementById('formLocation').value = d.location;
                document.getElementById('formStartTime').value = d.start_time;
                document.getElementById('formEndTime').value = d.end_time;
                document.getElementById('formImageUrl').value = d.image_url;
                document.getElementById('formWhatsappLink').value = d.whatsapp_link;
                document.getElementById('formIsActive').value = d.is_active ? 'on' : '';
                document.getElementById('createEventForm').submit();
            }
        });
    });

    /* ── Edit Event Modal ── */
    document.querySelectorAll('.btn-event-edit').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var eventId = btn.dataset.eventId;
            var vals = {
                title: btn.dataset.eventTitle,
                description: btn.dataset.eventDesc,
                location: btn.dataset.eventLocation,
                start_time: btn.dataset.eventStart,
                end_time: btn.dataset.eventEnd,
                image_url: btn.dataset.eventImage,
                whatsapp_link: btn.dataset.eventWhatsapp,
                is_active: btn.dataset.eventActive === 'true'
            };

            Swal.fire({
                title: 'Edit Event',
                html: buildFormHtml(vals),
                showCancelButton: true,
                confirmButtonText: '<i class="bi bi-check-lg me-1"></i>Save Changes',
                confirmButtonColor: '#a855f7',
                cancelButtonColor: '#64748b',
                reverseButtons: true,
                customClass: { popup: 'rounded-4', htmlContainer: 'text-start' },
                width: '520px',
                preConfirm: getFormValues
            }).then(function (result) {
                if (result.isConfirmed) {
                    var d = result.value;
                    var form = document.getElementById('editEventForm');
                    form.action = '/admin/events/' + eventId + '/edit';
                    document.getElementById('editTitle').value = d.title;
                    document.getElementById('editDescription').value = d.description;
                    document.getElementById('editLocation').value = d.location;
                    document.getElementById('editStartTime').value = d.start_time;
                    document.getElementById('editEndTime').value = d.end_time;
                    document.getElementById('editImageUrl').value = d.image_url;
                    document.getElementById('editWhatsappLink').value = d.whatsapp_link;
                    document.getElementById('editIsActive').value = d.is_active ? 'on' : '';
                    form.submit();
                }
            });
        });
    });

    /* ── Confirm Actions (Toggle / Delete) ── */
    function handleAction(btn) {
        var action = btn.dataset.action;
        var name   = btn.dataset.name;
        var url    = btn.dataset.url;

        var config = {
            activate: {
                title: 'Activate Event',
                html: 'Set <strong>' + name + '</strong> as the active event?<br><small class="text-muted">All other events will be deactivated.</small>',
                icon: 'question', iconColor: '#14b8a6',
                confirmButtonText: 'Yes, Activate', confirmButtonColor: '#14b8a6'
            },
            deactivate: {
                title: 'Deactivate Event',
                html: 'Deactivate <strong>' + name + '</strong>?<br><small class="text-muted">No event will be active.</small>',
                icon: 'warning', iconColor: '#f59e0b',
                confirmButtonText: 'Yes, Deactivate', confirmButtonColor: '#f59e0b'
            },
            delete_event: {
                title: 'Delete Event',
                html: 'Delete <strong>' + name + '</strong>?<br><small class="text-muted">This action cannot be undone.</small>',
                icon: 'warning', iconColor: '#ef4444',
                confirmButtonText: 'Yes, Delete', confirmButtonColor: '#ef4444'
            }
        }[action];

        Swal.fire({
            ...config,
            showCancelButton: true,
            cancelButtonText: 'Cancel',
            cancelButtonColor: '#64748b',
            reverseButtons: true,
            customClass: { popup: 'rounded-4' }
        }).then(function (result) {
            if (result.isConfirmed) {
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = url;
                document.body.appendChild(form);
                form.submit();
            }
        });
    }

    document.querySelectorAll('[data-action]').forEach(function (btn) {
        btn.addEventListener('click', function () { handleAction(btn); });
    });

    /* ── Success Toast ── */
    var params  = new URLSearchParams(window.location.search);
    var success = params.get('success');

    if (success) {
        window.history.replaceState({}, '', window.location.pathname);

        var messages = {
            created:       { title: 'Event Created!',      text: 'The new event has been added.' },
            updated:       { title: 'Event Updated!',      text: 'The event has been saved.' },
            activated:     { title: 'Event Activated!',     text: 'This is now the active event.' },
            deactivated:   { title: 'Event Deactivated',    text: 'The event is now inactive.' },
            event_deleted: { title: 'Event Deleted',        text: 'The event has been removed.' }
        };
        var msg = messages[success] || { title: 'Done!', text: '' };

        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: msg.title,
            text: msg.text,
            showConfirmButton: false,
            timer: 4000,
            timerProgressBar: true
        });
    }
})();

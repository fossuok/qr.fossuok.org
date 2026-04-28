(function () {

    /* ── Confirm + Submit via SweetAlert2 ── */
    function handleAction(btn) {
        const action = btn.dataset.action;
        const name   = btn.dataset.name;
        const url    = btn.dataset.url;

        const config = {
            promote: {
                title: 'Promote to Admin',
                html: 'Are you sure you want to promote <strong>' + name + '</strong> to admin?<br><small class="text-muted">They will gain full admin privileges.</small>',
                icon: 'question', iconColor: '#a855f7',
                confirmButtonText: 'Yes, Promote', confirmButtonColor: '#a855f7'
            },
            demote: {
                title: 'Demote to Participant',
                html: 'Are you sure you want to demote <strong>' + name + '</strong>?<br><small class="text-muted">They will lose admin privileges.</small>',
                icon: 'warning', iconColor: '#f59e0b',
                confirmButtonText: 'Yes, Demote', confirmButtonColor: '#f59e0b'
            },
            delete: {
                title: 'Delete User',
                html: 'Are you sure you want to delete <strong>' + name + '</strong>?<br><small class="text-muted">This action cannot be undone.</small>',
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
                // Submit via hidden form
                const form = document.createElement('form');
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

    /* ── Success Toast via SweetAlert2 ── */
    const params  = new URLSearchParams(window.location.search);
    const success = params.get('success');

    if (success) {
        window.history.replaceState({}, '', window.location.pathname);

        const messages = {
            promoted: { title: 'User Promoted!', text: 'The user now has admin privileges.' },
            demoted:  { title: 'User Demoted',   text: 'The user is now a participant.' },
            deleted:  { title: 'User Deleted',    text: 'The user has been removed from the system.' }
        };
        const msg = messages[success] || { title: 'Done!', text: '' };

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

    /* ── Affiliation Modal ── */
    const affiliationModal = document.getElementById('affiliationModal');
    if (affiliationModal) {
        affiliationModal.addEventListener('show.bs.modal', function (e) {
            const btn  = e.relatedTarget;
            const type = btn.dataset.type;
            const name = btn.dataset.name;

            document.getElementById('affil-username').textContent = name;

            const labels = {
                uok_student:      '🎓 UoK Student',
                other_university: '🏫 Other University',
                industry:         '💼 Industry / Professional',
            };

            let rows = `<div class="affil-badge">${labels[type] || type}</div>`;

            if (type === 'uok_student') {
                rows += affilRow('University', btn.dataset.university || 'University of Kelaniya');
                rows += affilRow('Student ID', btn.dataset.studentId || '—');
            } else if (type === 'other_university') {
                rows += affilRow('University', btn.dataset.university || '—');
                rows += affilRow('Year of Study', btn.dataset.studyYear || '—');
            } else if (type === 'industry') {
                rows += affilRow('Organization', btn.dataset.organization || '—');
                rows += affilRow('Job Role', btn.dataset.jobRole || '—');
            }

            document.getElementById('affiliationModalBody').innerHTML = rows;
        });
    }

    function affilRow(label, value) {
        return `<div class="affil-row">
            <span class="affil-label">${label}</span>
            <span class="affil-value">${value}</span>
        </div>`;
    }

})();

document.addEventListener('DOMContentLoaded', function () {
    const validDaysInput = document.getElementById('id_valid_days');
    const validFromInput = document.getElementById('id_enrollment_valid_from');
    const validUntilInput = document.getElementById('id_enrollment_valid_until');

    // Store previous values to detect changes
    let prevValidDays = '';
    let prevValidFrom = '';

    function calculateValidUntil() {
        if (!validDaysInput || !validFromInput || !validUntilInput) return;

        const currentValidDays = validDaysInput.value;
        const currentValidFrom = validFromInput.value;

        // Only calculate if values changed
        if (currentValidDays === prevValidDays && currentValidFrom === prevValidFrom) {
            return;
        }

        prevValidDays = currentValidDays;
        prevValidFrom = currentValidFrom;

        const validDays = parseInt(currentValidDays);
        const validFromDate = new Date(currentValidFrom);

        if (!isNaN(validDays) && !isNaN(validFromDate.getTime())) {
            const validUntilDate = new Date(validFromDate);
            validUntilDate.setDate(validFromDate.getDate() + validDays);

            const year = validUntilDate.getFullYear();
            const month = String(validUntilDate.getMonth() + 1).padStart(2, '0');
            const day = String(validUntilDate.getDate()).padStart(2, '0');

            validUntilInput.value = `${year}-${month}-${day}`;
        }
    }

    // Polling to detect changes from the Django Admin DatePicker widget
    setInterval(calculateValidUntil, 500);

    // Also listen for direct input
    if (validDaysInput) validDaysInput.addEventListener('input', calculateValidUntil);
    if (validFromInput) validFromInput.addEventListener('change', calculateValidUntil);
});

document.addEventListener('DOMContentLoaded', function () {
    // 1. Identify the Main Batch Dropdown
    const mainBatchSelect = document.querySelector('#id_batch');

    if (!mainBatchSelect) {
        console.warn('Main batch selector #id_batch not found.');
        return;
    }

    // 2. Define function to sync value to all inline rows
    function syncBatchToInlines() {
        const selectedValue = mainBatchSelect.value;
        if (!selectedValue) return;

        // Find all batch selectors within the "resources" inline group
        // Django inline rows have IDs like "id_resources-0-batch", "id_resources-1-batch", etc.
        const inlineBatchSelects = document.querySelectorAll('select[id^="id_resources-"][id$="-batch"]');

        inlineBatchSelects.forEach(select => {
            select.value = selectedValue;

            // 🚨 CRITICAL FIX: Do NOT trigger 'change' events on hidden selects
            // Django Admin might have swapped this with a select2/autocomplete widget
            // triggering events on the hidden original select can cause validation race conditions
            if (select.offsetParent !== null) {
                const event = new Event('change');
                select.dispatchEvent(event);
            }
        });
    }

    // 3. Attach Listeners
    // Sync when the main batch changes
    mainBatchSelect.addEventListener('change', syncBatchToInlines);

    // Also sync immediately if there is already a value (e.g. edit mode)
    // But mostly useful when adding new rows.

    // 4. Handle "Add another Resource" clicks
    // Django adds new rows dynamically. We need to watch for new rows.
    // Ideally, we use MutationObserver or just a click listener on the "Add row" button.

    const inlineGroup = document.querySelector('#resources-group');
    if (inlineGroup) {
        // Observe changes to the inline group to catch new rows
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.addedNodes.length) {
                    // New row added? Sync it.
                    syncBatchToInlines();
                }
            });
        });

        observer.observe(inlineGroup, { childList: true, subtree: true });
    }
});

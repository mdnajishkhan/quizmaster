
(function ($) {
    $(document).ready(function () {
        console.log("RecGetUp: Coupon Admin Script Loaded (Polling Version)");

        var $select = $('#id_workshop_package');

        // Standard Change Event
        $select.on('change', function () {
            console.log("RecGetUp: Package Changed to " + $(this).val());
            var packageId = $(this).val();
            if (packageId) {
                $.ajax({
                    url: '/training/api/package-details/' + packageId + '/',
                    success: function (data) {
                        console.log("RecGetUp: API Success", data);
                        if (data.price) {
                            $('#id_payment_amount').val(data.price);
                        }
                        if (data.duration) {
                            $('#id_valid_days').val(data.duration);
                            calculateEndDate(); // Trigger recalc
                        }
                    },
                    error: function (err) {
                        console.error("RecGetUp: API Error", err);
                    }
                });
            }
        });

        // --- Auto-Calculate Valid Until ---
        function calculateEndDate() {
            try {
                var days = parseInt($('#id_valid_days').val());
                var startStr = $('#id_enrollment_valid_from').val();

                if (!days || !startStr) return;

                // Handle format YYYY-MM-DD
                var parts = startStr.split('-');
                if (parts.length !== 3) {
                    // Attempt Date constructor fallback?
                    if (startStr.indexOf('/') > -1) {
                        // Maybe DD/MM/YYYY? 
                        // Let's stick to strict or fallback
                    }
                    return;
                }

                var year = parseInt(parts[0]);
                var month = parseInt(parts[1]) - 1;
                var day = parseInt(parts[2]);

                var startDate = new Date(year, month, day);

                if (isNaN(startDate.getTime())) return;

                // Add Days
                var endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + days);

                // Format YYYY-MM-DD
                var y = endDate.getFullYear();
                var m = (endDate.getMonth() + 1).toString().padStart(2, '0');
                var d = endDate.getDate().toString().padStart(2, '0');

                // Only update if different to avoid infinite loops or fighting user
                var currentVal = $('#id_enrollment_valid_until').val();
                var newVal = y + '-' + m + '-' + d;

                if (currentVal !== newVal) {
                    $('#id_enrollment_valid_until').val(newVal);
                }
            } catch (e) {
                console.error("RecGetUp: Calculation Exception", e);
            }
        }

        // POLLING: The ultimate fallback for widgets that don't fire events
        // Checks every 200ms if the value changed
        var lastStartStr = "";
        var lastDays = "";

        setInterval(function () {
            var currentStart = $('#id_enrollment_valid_from').val();
            var currentDays = $('#id_valid_days').val();

            // If value changed from what we last saw
            if (currentStart !== lastStartStr || currentDays !== lastDays) {
                lastStartStr = currentStart;
                lastDays = currentDays;
                calculateEndDate();
            }
        }, 200);

        // Trigger once on load
        calculateEndDate();

    });
})(django.jQuery);

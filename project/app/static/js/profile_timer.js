        document.addEventListener("DOMContentLoaded", function () {
            const timerBoxes = document.querySelectorAll(".booking-timer-box");

            timerBoxes.forEach(box => {
                const expiresStr = box.dataset.expires;
                if (!expiresStr) return;

                // Если в базе записано время создания, прибавляем к нему 15 минут (900000 миллисекунд)
                const expiresAt = new Date(expiresStr).getTime();
                const displayEl = box.querySelector(".countdown-timer");

                function updateCountdown() {
                    const now = new Date().getTime();
                    const distance = expiresAt - now;

                    if (distance < 0) {
                        displayEl.textContent = "Время истекло";
                        setTimeout(() => location.reload(), 1500);
                        return;
                    }

                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                    displayEl.textContent = 
                        String(minutes).padStart(2, '0') + ":" + String(seconds).padStart(2, '0');
                }

                updateCountdown();
                setInterval(updateCountdown, 1000);
            });
        });
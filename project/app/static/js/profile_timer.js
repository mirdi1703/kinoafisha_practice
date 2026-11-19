document.addEventListener("DOMContentLoaded", function () {
    const timerBoxes = document.querySelectorAll(".booking-timer-box");
    if (!timerBoxes.length) return;

    let reloadScheduled = false;

    function triggerReload() {
        if (reloadScheduled) return;
        reloadScheduled = true;
        clearInterval(intervalId);
        setTimeout(function () {
            window.location.reload();
        }, 1000);
    }

    function updateCountdown(box, displayEl, expiresAt) {
        const now = Date.now();
        const distance = expiresAt - now;

        if (distance <= 0) {
            displayEl.textContent = "Время истекло";
            triggerReload();
            return;
        }

        const totalSeconds = Math.floor(distance / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;

        displayEl.textContent =
            String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
    }

    const activeTimers = [];

    timerBoxes.forEach((box) => {
        const expiresStr = box.dataset.expires;
        const displayEl = box.querySelector(".countdown-timer");
        if (!expiresStr || !displayEl) return;

        const expiresAt = Date.parse(expiresStr);
        if (Number.isNaN(expiresAt)) return;

        activeTimers.push({ box, displayEl, expiresAt });
    });

    if (!activeTimers.length) return;

    function tick() {
        activeTimers.forEach((item) => {
            updateCountdown(item.box, item.displayEl, item.expiresAt);
        });
    }

    tick();
    const intervalId = setInterval(tick, 1000);
});
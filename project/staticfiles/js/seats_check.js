document.addEventListener("DOMContentLoaded", function () {
    const sessionEl = document.getElementById("session-data");
    if (!sessionEl) return;

    const sessionId = sessionEl.dataset.sessionId;
    if (!sessionId) return;

    function fetchOccupiedSeats() {
        fetch(`/api/session/${sessionId}/seats/`)
            .then(response => response.json())
            .then(data => {
                data.occupied_seats.forEach(seatId => {
                    const seatElement = document.querySelector(`input[name="seats"][value="${seatId}"]`);
                    if (seatElement && !seatElement.checked) {
                        seatElement.disabled = true;
                        const label = seatElement.closest('.seat-item');
                        if (label) {
                            label.classList.add('occupied');
                        }
                    }
                });
            })
            .catch(err => console.error("Ошибка автообновления мест:", err));
    }

    // Проверяем занятые места каждые 5 секунд без перезагрузки
    setInterval(fetchOccupiedSeats, 5000);
});
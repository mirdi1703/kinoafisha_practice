        const checkboxes = document.querySelectorAll('input[name="seats"]');
        const selectedList = document.getElementById('selected-seats-list');
        const totalPriceEl = document.getElementById('total-price');
        const submitBtn = document.getElementById('submit-booking-btn');

        function updateSummary() {
            const checked = Array.from(checkboxes).filter(cb => cb.checked);
            let total = 0;

            if (checked.length === 0) {
                selectedList.innerHTML = '<p class="caption">Выберите места на схеме зала</p>';
                totalPriceEl.textContent = '0 руб.';
                submitBtn.disabled = true;
                return;
            }

            let html = '<div class="selected-chips">';
            checked.forEach(cb => {
                const row = cb.dataset.row;
                const seat = cb.dataset.seat;
                const cat = cb.dataset.category;
                const price = parseFloat(cb.dataset.price) || 0;
                total += price;

                html += `
                    <div class="selected-seat-row">
                        <span>Ряд ${row}, место ${seat} (${cat})</span>
                        <strong>${price} руб.</strong>
                    </div>
                `;
            });
            html += '</div>';

            selectedList.innerHTML = html;
            totalPriceEl.textContent = `${total.toFixed(2)} руб.`;
            submitBtn.disabled = false;
        }

        checkboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const label = cb.closest('.seat-item');
                const row = cb.closest('.hall-row');

                if (cb.checked) {
                    label.classList.add('selected');
                } else {
                    label.classList.remove('selected');
                }

                const anyInRow = row.querySelectorAll('input[name="seats"]:checked').length > 0;
                row.classList.toggle('has-selected', anyInRow);

                updateSummary();
            });
        });
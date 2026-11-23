        const searchInput = document.getElementById('search-input');
        const genreSelect = document.getElementById('genre-select');
        const moviesContainer = document.getElementById('movies-container');

        function fetchMovies() {
            const query = searchInput.value;
            const genre = genreSelect.value;
            const url = `?q=${encodeURIComponent(query)}&genre=${encodeURIComponent(genre)}`;

            fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                moviesContainer.innerHTML = data.html;
            })
            .catch(error => console.error('Ошибка при загрузке фильмов:', error));
        }

        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchMovies, 300);
        });

        genreSelect.addEventListener('change', fetchMovies);
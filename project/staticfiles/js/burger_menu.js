document.addEventListener("DOMContentLoaded", function () {
    const header = document.querySelector(".header");
    const burgerBtn = document.querySelector(".burger-btn");
    const nav = document.querySelector(".nav");

    if (!header || !burgerBtn || !nav) return;

    function closeMenu() {
        header.classList.remove("menu-open");
        burgerBtn.setAttribute("aria-expanded", "false");
    }

    burgerBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        const isOpen = header.classList.toggle("menu-open");
        burgerBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    nav.querySelectorAll("a, button").forEach(function (item) {
        item.addEventListener("click", function () {
            closeMenu();
        });
    });

    document.addEventListener("click", function (event) {
        if (!header.contains(event.target)) {
            closeMenu();
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 375) {
            closeMenu();
        }
    });
});
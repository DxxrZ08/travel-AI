const navToggle = document.querySelector('#navToggle');
const navLinks = document.querySelector('#navLinks');

navToggle?.addEventListener('click', () => {
    const isOpen = navLinks?.classList.toggle('is-open') ?? false;
    navToggle.setAttribute('aria-expanded', String(isOpen));
});

document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', (event) => {
        event.stopPropagation();
        button.closest('.flash-message')?.remove();
    });
});
const bag = JSON.parse(localStorage.getItem('asterBag') || '[]');

const cartCount = document.getElementById('cartCount');
const bagPanel = document.getElementById('bagPanel');
const bagItems = document.getElementById('bagItems');
const overlay = document.getElementById('overlay');

function saveBag() {
  localStorage.setItem('asterBag', JSON.stringify(bag));
  renderBag();
}

function renderBag() {
  cartCount.textContent = bag.reduce((total, item) => total + item.quantity, 0);
  if (!bag.length) {
    bagItems.innerHTML = '<p>Your bag is empty.</p>';
    return;
  }

  const total = bag.reduce((sum, item) => sum + item.price * item.quantity, 0);
  bagItems.innerHTML = bag.map((item, index) => `
    <div class="bag-item">
      <div><strong>${item.name}</strong><span>$${item.price}</span></div>
      <div class="quantity"><button data-action="minus" data-index="${index}" aria-label="Remove one">−</button><span>${item.quantity}</span><button data-action="plus" data-index="${index}" aria-label="Add one">+</button></div>
    </div>`).join('') + `<div class="bag-total"><span>Total</span><strong>$${total}</strong></div>`;
}

function setBag(open) {
  bagPanel.classList.toggle('open', open);
  overlay.classList.toggle('open', open);
  bagPanel.setAttribute('aria-hidden', String(!open));
}

document.querySelectorAll('.add-button').forEach(button => {
  button.addEventListener('click', () => {
    const name = button.dataset.name;
    const existing = bag.find(item => item.name === name);
    if (existing) existing.quantity += 1;
    else bag.push({ name, price: Number(button.dataset.price), quantity: 1 });
    saveBag();
    button.textContent = 'Added ✓';
    setTimeout(() => button.textContent = 'Add to bag', 900);
  });
});

bagItems.addEventListener('click', event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const index = Number(button.dataset.index);
  if (button.dataset.action === 'plus') bag[index].quantity += 1;
  else if (--bag[index].quantity === 0) bag.splice(index, 1);
  saveBag();
});

document.getElementById('cartButton').addEventListener('click', () => setBag(true));
document.getElementById('closeBag').addEventListener('click', () => setBag(false));
overlay.addEventListener('click', () => setBag(false));

document.querySelectorAll('.filter').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.filter').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    document.querySelectorAll('.catalog-item').forEach(item => {
      item.hidden = button.dataset.filter !== 'all' && item.dataset.category !== button.dataset.filter;
    });
  });
});

renderBag();

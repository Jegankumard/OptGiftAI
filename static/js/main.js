let compareList = [];
let cart = [];

// --- Professional Toast Notification ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `<span>${icon}</span><div class="toast-content">${message}</div>`;
    container.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s forwards';
        toast.addEventListener('animationend', () => toast.remove());
    }, 3000);
}

// --- Like Logic ---
function likeProduct(productId) {
    // 1. Visual Feedback
    const card = document.getElementById(`card-${productId}`);
    if(card) card.style.border = '2px solid #4caf50';
    
    // 2. Send Feedback
    fetch('/feedback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ product_id: productId, action: 'purchase' })
    }).then(() => {
        showToast("Thanks! We'll show more items like this.", "success");
    });
}

// --- Dislike & Replace Logic ---
function dislikeProduct(productId) {
    const card = document.getElementById(`card-${productId}`);
    
    // 1. Collect currently visible IDs to avoid duplicates in replacement
    const visibleCards = document.querySelectorAll('.card');
    let excludeIds = Array.from(visibleCards).map(c => parseInt(c.getAttribute('data-id')));
    
    // 2. Visual removal
    if(card) card.style.opacity = '0';
    showToast("Product removed. Fetching new recommendation...", "info");
    
    setTimeout(() => {
        if(card) {
            const parent = card.parentNode;
            card.remove(); // Remove old card

            // 3. Fetch Replacement
            fetch('/get_replacement_card', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ exclude_ids: excludeIds })
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    // Insert new HTML
                    parent.insertAdjacentHTML('beforeend', data.html);
                    showToast("New suggestion added!", "success");
                } else {
                    showToast(data.message, "error");
                }
            });
        }
    }, 500);

    // Send backend feedback
    fetch('/feedback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ product_id: productId, action: 'dislike' })
    });
}

// --- Add to Cart ---
function addToCart(productId) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ product_id: productId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            const badge = document.getElementById('nav-cart-count');
            if (badge) badge.innerText = data.cart_count;
            showToast(data.message, 'success');
        } else {
            showToast(data.message, 'info');
        }
    })
    .catch(err => {
        console.error("Error:", err);
        showToast("Something went wrong.", "error");
    });
}

// --- Cart Toggle (+/-) Logic ---
function toggleCart(productId, btnElement) {
    const isRemoving = btnElement.classList.contains('remove-mode');
    const endpoint = isRemoving ? '/remove_from_cart' : '/add_to_cart';
    
    fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ product_id: productId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            // Update Navbar
            const badge = document.getElementById('nav-cart-count');
            if (badge) badge.innerText = data.cart_count;
            
            // Toggle Button State
            const signSpan = btnElement.querySelector('.sign');
            
            if (isRemoving) {
                // Switched to "Add" Mode
                btnElement.classList.remove('remove-mode');
                signSpan.textContent = '+';
                btnElement.title = "Add to Cart";
                showToast("Removed from Cart", "info");
            } else {
                // Switched to "Remove" Mode
                btnElement.classList.add('remove-mode');
                signSpan.textContent = '-';
                btnElement.title = "Remove from Cart";
                showToast("Added to Cart", "success");
            }
        } else {
            showToast(data.message, "info");
        }
    });
}

// ==========================================
// --- COMPARE LOGIC (Updated) ---
// ==========================================

function toggleCompare(productId, btnElement) {
    const index = compareList.indexOf(productId);
    const signSpan = btnElement.querySelector('.sign');
    
    if (index === -1) {
        // Add
        if (compareList.length >= 3) {
            showToast("You can only compare up to 3 products.", "error");
            return;
        }
        compareList.push(productId);
        btnElement.classList.add('active');
        signSpan.textContent = '-';
        showToast("Added to compare.", "success");
    } else {
        // Remove
        compareList.splice(index, 1);
        btnElement.classList.remove('active');
        signSpan.textContent = '+';
    }

    updateCompareFloat();
}

function updateCompareFloat() {
    const floatBtn = document.getElementById('compare-floating-btn');
    const countSpan = document.getElementById('compare-count');
    
    if(countSpan) countSpan.innerText = compareList.length;
    
    if (floatBtn) {
        if (compareList.length > 0) {
            floatBtn.style.display = 'block';
        } else {
            floatBtn.style.display = 'none';
        }
    }
}

// --- NEW: Clear Comparison Logic ---
function clearComparison() {
    // 1. Reset the UI buttons for items currently in the list
    compareList.forEach(id => {
        const card = document.getElementById(`card-${id}`);
        if (card) {
            const btn = card.querySelector('.compare-btn');
            if (btn) {
                btn.classList.remove('active');
                if(btn.querySelector('.sign')) btn.querySelector('.sign').textContent = '+';
            }
        }
    });

    // 2. Empty the array
    compareList = [];

    // 3. Update UI elements
    updateCompareFloat(); 
    closeCompareModal();
    showToast("Comparison cleared.", "info");
}

function openCompareModal() {
    const modal = document.getElementById('compareModal');
    const grid = document.getElementById('compare-grid');
    grid.innerHTML = ''; // Clear previous content

    if (compareList.length === 0) return;

    // Generate Table Headers
    let tableHtml = '<table class="compare-table"><thead><tr><th>Feature</th>';
    
    // Gather Data from DOM
    let products = [];
    compareList.forEach(id => {
        const card = document.getElementById(`card-${id}`);
        if(card) {
            products.push({
                title: card.getAttribute('data-title'),
                price: card.getAttribute('data-price'),
                vendor: card.getAttribute('data-vendor'),
                img: card.getAttribute('data-img')
            });
        }
    });

    // Headers
    products.forEach(p => { tableHtml += `<th>${p.title}</th>`; });
    tableHtml += '</tr></thead><tbody>';

    // Rows
    tableHtml += '<tr><td><strong>Image</strong></td>';
    products.forEach(p => { tableHtml += `<td><img src="${p.img}" width="80" style="border-radius:4px;"></td>`; });
    tableHtml += '</tr>';

    tableHtml += '<tr><td><strong>Price</strong></td>';
    products.forEach(p => { tableHtml += `<td>₹${p.price}</td>`; });
    tableHtml += '</tr>';

    tableHtml += '<tr><td><strong>Vendor</strong></td>';
    products.forEach(p => { tableHtml += `<td>${p.vendor}</td>`; });
    tableHtml += '</tr>';

    tableHtml += '</tbody></table>';

    // --- NEW: Action Buttons (Clear & Close) ---
    tableHtml += `
        <div style="margin-top: 20px; text-align: right; display: flex; justify-content: flex-end; gap: 10px;">
            <button class="btn-primary" style="background-color: #d32f2f; border:none;" onclick="clearComparison()">Clear All</button>
            <button class="btn-primary" onclick="closeCompareModal()">Close</button>
        </div>
    `;

    grid.innerHTML = tableHtml;
    modal.style.display = 'block';
}

function closeCompareModal() {
    const modal = document.getElementById('compareModal');
    if(modal) modal.style.display = 'none';
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', function() {
    // 1. Close modal if clicked outside
    window.onclick = function(event) {
        const modal = document.getElementById('compareModal');
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // 2. Fix Close Button (The 'X' at top right)
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.onclick = function() {
            closeCompareModal();
        };
    }
});
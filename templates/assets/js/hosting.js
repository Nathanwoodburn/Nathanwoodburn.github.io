// Rates
const cpuRate = 4;
const memoryRate = 5;
const diskRate = 0.1;
const backupRate = 5;

// Memory values mapping
const memoryValues = [1, 2, 4, 8, 16, 24];

function updateValue(field) {
    const el = document.getElementById(field);
    if (!el) return;
    let value = el.value;

    if (field === 'memory') {
        value = memoryValues[parseInt(value, 10)] || 1;
    }

    const valueEl = document.getElementById(field + 'Value');
    if (valueEl) {
        valueEl.textContent = value;
    }
    calculateCost();
}

function selectPreset(presetValue) {
    const radio = document.querySelector(`input[name="preset"][value="${presetValue}"]`);
    if (radio) {
        radio.checked = true;
    }
    handlePresetChange();
    updateCardStyles();
}

function updateCardStyles() {
    const cards = document.querySelectorAll('.plan-card');
    const checkedRadio = document.querySelector('input[name="preset"]:checked');
    if (!checkedRadio) return;
    const selectedPreset = checkedRadio.value;

    cards.forEach((card, index) => {
        const presetValues = ['standard', 'premium', 'custom'];
        const isSelected = presetValues[index] === selectedPreset;

        if (isSelected) {
            card.classList.add('selected');
            card.style.borderColor = '#007bff';
            card.style.background = '#f8f9fa';
            card.style.transform = 'translateY(-2px)';
            card.style.boxShadow = '0 4px 12px rgba(0,123,255,0.15)';
        } else {
            card.classList.remove('selected');
            card.style.borderColor = '#ddd';
            card.style.background = '#ffffff';
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = 'none';
        }
    });
}

function handlePresetChange() {
    const checkedRadio = document.querySelector('input[name="preset"]:checked');
    if (!checkedRadio) return;
    const selectedPreset = checkedRadio.value;
    const customSliders = document.getElementById('customSliders');

    updateCardStyles();

    if (selectedPreset === 'custom') {
        if (customSliders) customSliders.style.display = 'block';
    } else {
        if (customSliders) customSliders.style.display = 'none';

        // Set preset values
        const cpusEl = document.getElementById('cpus');
        const memoryEl = document.getElementById('memory');
        const diskEl = document.getElementById('disk');
        const backupsEl = document.getElementById('backups');

        if (selectedPreset === 'standard') {
            if (cpusEl) cpusEl.value = 1;
            if (memoryEl) memoryEl.value = 0; // 1GB
            if (diskEl) diskEl.value = 10;
            if (backupsEl) backupsEl.checked = false;
        } else if (selectedPreset === 'premium') {
            if (cpusEl) cpusEl.value = 2;
            if (memoryEl) memoryEl.value = 1; // 2GB
            if (diskEl) diskEl.value = 50;
            if (backupsEl) backupsEl.checked = true;
        }

        // Update displayed values
        updateValue('cpus');
        updateValue('memory');
        updateValue('disk');
    }

    calculateCost();
}

function calculateCost() {
    const checkedRadio = document.querySelector('input[name="preset"]:checked');
    if (!checkedRadio) return;
    const selectedPreset = checkedRadio.value;
    const monthlyCostEl = document.getElementById('monthlyCost');
    if (!monthlyCostEl) return;

    // For presets, use fixed pricing
    if (selectedPreset === 'standard') {
        monthlyCostEl.textContent = '10.00';
        return;
    } else if (selectedPreset === 'premium') {
        monthlyCostEl.textContent = '20.00';
        return;
    }

    // Custom calculation
    const cpus = parseFloat(document.getElementById('cpus').value) || 0;
    const memoryIndex = parseInt(document.getElementById('memory').value, 10) || 0;
    const memory = memoryValues[memoryIndex] || 1;
    const disk = parseFloat(document.getElementById('disk').value) || 0;

    let monthlyCost = (cpus * cpuRate) + (memory * memoryRate) + (disk * diskRate);

    const backupsEl = document.getElementById('backups');
    if (backupsEl && backupsEl.checked) {
        const backupUnits = Math.ceil(disk / 50);
        monthlyCost += backupUnits * backupRate;
    }

    monthlyCostEl.textContent = monthlyCost.toFixed(2);
}

function sendEnquiry() {
    const emailEl = document.getElementById('email');
    const statusEl = document.getElementById('enquiryStatus');
    if (!emailEl || !statusEl) return;

    const email = emailEl.value;
    if (!email) {
        statusEl.textContent = 'Please enter your email address.';
        statusEl.style.color = '#ef4444';
        return;
    }

    const checkedRadio = document.querySelector('input[name="preset"]:checked');
    const selectedPreset = checkedRadio ? checkedRadio.value : 'standard';
    const cpus = document.getElementById('cpus') ? document.getElementById('cpus').value : 1;
    const memoryIndex = document.getElementById('memory') ? parseInt(document.getElementById('memory').value, 10) : 0;
    const memory = memoryValues[memoryIndex] || 1;
    const disk = document.getElementById('disk') ? document.getElementById('disk').value : 10;
    const backups = (document.getElementById('backups') && document.getElementById('backups').checked) ? 'Yes' : 'No';
    const message = document.getElementById('message') ? document.getElementById('message').value : '';

    const enquiryData = {
        email: email,
        preset: selectedPreset,
        cpus: cpus,
        memory: memory,
        disk: disk,
        backups: backups,
        message: message
    };

    fetch('/hosting/send-enquiry', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(enquiryData)
    })
    .then(response => {
        if (response.ok) {
            statusEl.textContent = 'Enquiry sent successfully!';
            statusEl.style.color = '#22c55e';
            calculateCost();
        } else {
            statusEl.textContent = 'Failed to send enquiry. Please try again.';
            statusEl.style.color = '#ef4444';
        }
    })
    .catch(error => {
        console.error('Error sending enquiry:', error);
        statusEl.textContent = 'Error sending enquiry. Please check your network connection.';
        statusEl.style.color = '#ef4444';
    });
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.has('preset')) {
        const presetValue = urlParams.get('preset');
        const presetRadio = document.querySelector(`input[name="preset"][value="${presetValue}"]`);
        if (presetRadio) {
            presetRadio.checked = true;
            handlePresetChange();
        }
    }

    if (urlParams.has('cpus')) {
        const cpusEl = document.getElementById('cpus');
        if (cpusEl) cpusEl.value = urlParams.get('cpus');
    }
    if (urlParams.has('memory')) {
        const memoryParam = parseFloat(urlParams.get('memory'));
        const memoryIndex = memoryValues.indexOf(memoryParam);
        const memoryEl = document.getElementById('memory');
        if (memoryEl) memoryEl.value = memoryIndex >= 0 ? memoryIndex : 0;
    }
    if (urlParams.has('disk')) {
        const diskEl = document.getElementById('disk');
        if (diskEl) diskEl.value = urlParams.get('disk');
    }
    if (urlParams.has('backups')) {
        const backupsEl = document.getElementById('backups');
        if (backupsEl) backupsEl.checked = urlParams.get('backups') === 'true';
    }
    if (urlParams.has('email')) {
        const emailEl = document.getElementById('email');
        if (emailEl) emailEl.value = urlParams.get('email');
    }
    if (urlParams.has('message')) {
        const messageEl = document.getElementById('message');
        if (messageEl) messageEl.value = urlParams.get('message');
    }

    updateValue('cpus');
    updateValue('memory');
    updateValue('disk');
    calculateCost();

    const form = document.getElementById('costForm');
    if (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            sendEnquiry();
        });
    }

    handlePresetChange();
    updateCardStyles();
});

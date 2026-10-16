function copyToClipboard(element) {
    if (!element) return;
    const textToCopy = element.textContent;
    const textArea = document.createElement('textarea');
    textArea.value = textToCopy;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    const tooltips = document.querySelectorAll('.tooltip-inner');
    tooltips.forEach(tooltip => {
        tooltip.innerText = 'Copied!';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Section click listeners
    const commonCryptoIds = ['btc', 'eth', 'hns', 'sol', 'btc-domain', 'eth-domain', 'hns-domain', 'sol-domain'];
    commonCryptoIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('click', () => copyToClipboard(el));
        }
    });

    // Donate page dropdown search
    const dropdownButton = document.getElementById('dropdownButton');
    const cryptoSearch = document.getElementById('cryptoSearch');
    const cryptoListContainer = document.getElementById('cryptoList');

    if (dropdownButton && cryptoSearch && cryptoListContainer) {
        dropdownButton.addEventListener('click', function () {
            setTimeout(() => cryptoSearch.focus(), 0);
        });

        const defaultCoins = window.DEFAULT_COINS || ['btc', 'eth', 'hns', 'sol', 'xrp', 'ada', 'dot'];

        cryptoSearch.addEventListener('input', function () {
            const searchValue = this.value.toLowerCase();
            const cryptoLinks = cryptoListContainer.getElementsByTagName('a');

            if (searchValue === '') {
                for (let i = 0; i < cryptoLinks.length; i++) {
                    const href = cryptoLinks[i].getAttribute('href') || '';
                    const parts = href.split('=');
                    const cryptoName = parts.length > 1 ? parts[1] : '';
                    if (defaultCoins.includes(cryptoName)) {
                        cryptoLinks[i].style.display = '';
                    } else {
                        cryptoLinks[i].style.display = 'none';
                    }
                }
            } else {
                for (let i = 0; i < cryptoLinks.length; i++) {
                    const cryptoName = cryptoLinks[i].textContent.toLowerCase();
                    if (cryptoName.indexOf(searchValue) > -1) {
                        cryptoLinks[i].style.display = '';
                    } else {
                        cryptoLinks[i].style.display = 'none';
                    }
                }
            }
        });

        cryptoSearch.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const cryptoLinks = cryptoListContainer.getElementsByTagName('a');
                for (let i = 0; i < cryptoLinks.length; i++) {
                    if (cryptoLinks[i].style.display === '') {
                        window.location.href = cryptoLinks[i].getAttribute('href');
                        break;
                    }
                }
            }
        });
    }
});

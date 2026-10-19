document.addEventListener('DOMContentLoaded', function () {
    const navbar = document.getElementById('mainNav');
    const headers = document.querySelectorAll('.section-header');

    if (navbar) {
        const navbarHeight = navbar.offsetHeight;
        headers.forEach(header => {
            header.style.top = navbarHeight + 'px';
            header.style.zIndex = '100';
            header.style.scrollMarginTop = navbarHeight + 'px';
        });

        if (window.location.hash && window.location.hash.length > 1 && window.location.hash !== '#') {
            setTimeout(() => {
                try {
                    const target = document.querySelector(window.location.hash);
                    if (target) {
                        window.scrollTo({
                            top: target.offsetTop - navbarHeight,
                            behavior: 'smooth'
                        });
                    }
                } catch {
                    // Ignore invalid CSS selector
                }
            }, 0);
        }
    }

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('show.bs.modal', () => {
            const body = modal.querySelector('.modal-body');
            if (body && body.dataset.demoLoaded === 'false') {
                const demoUrl = modal.dataset.demoUrl;
                const iframeId = 'iframe-' + modal.id;

                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'tool-modal-loading';
                const loadingMsg = document.createElement('p');
                loadingMsg.className = 'text-center';
                loadingMsg.textContent = 'Loading demo...';
                loadingDiv.appendChild(loadingMsg);
                body.style.position = 'relative';
                body.appendChild(loadingDiv);

                const iframe = document.createElement('iframe');
                iframe.src = demoUrl + '/iframe';
                iframe.id = iframeId;
                iframe.className = 'tool-modal-iframe';
                iframe.setAttribute('scrolling', 'no');
                iframe.setAttribute('allowfullscreen', 'true');

                body.appendChild(iframe);
                body.dataset.demoLoaded = 'true';

                const origin = new URL(demoUrl).origin;
                function onMessage(event) {
                    if (event.origin !== origin || event.source !== iframe.contentWindow) return;
                    if (event.data.type === 'bodySize' && event.data.payload.height) {
                        iframe.style.height = event.data.payload.height + 'px';
                        if (body.contains(loadingDiv)) {
                            body.removeChild(loadingDiv);
                        }
                        const dialog = modal.querySelector('.modal-dialog');
                        if (dialog) dialog.style.maxHeight = '90vh';
                    }
                }

                window.addEventListener('message', onMessage, false);
            }
        });
    });
});

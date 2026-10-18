(function () {
    const widget = document.getElementById('spotify-widget');
    const toggleBtn = document.getElementById('spotify-toggle');
    if (!widget || !toggleBtn) return;

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function updateVisibility() {
        if (isMobile()) {
            widget.style.transform = 'translateX(120%)';
            toggleBtn.style.transform = 'translateX(0)';
        } else {
            widget.style.transform = 'translateX(0)';
            toggleBtn.style.transform = 'translateX(200%)';
        }
    }

    toggleBtn.addEventListener('click', (e) => {
        widget.style.transform = 'translateX(0)';
        toggleBtn.style.transform = 'translateX(200%)';
        e.stopPropagation();
    });

    document.addEventListener('click', (e) => {
        if (isMobile()) {
            if (!widget.contains(e.target) && e.target !== toggleBtn) {
                widget.style.transform = 'translateX(120%)';
                toggleBtn.style.transform = 'translateX(0)';
            }
        }
    });

    widget.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    let progressInterval = null;
    let trackDuration = 0;
    let currentProgress = 0;
    let lastUpdateTime = Date.now();
    let currentTrackId = null;

    async function updateSpotifyWidget() {
        try {
            const res = await fetch('/api/v1/playing?_=' + Date.now(), { cache: 'no-store' });
            if (!res.ok) return;

            const data = await res.json();
            if (data.error || data.message) {
                const songEl = document.getElementById('spotify-song');
                if (songEl && songEl.textContent) {
                    return;
                }
                const artEl = document.getElementById('spotify-album-art');
                if (artEl) artEl.src = '/assets/img/external/spotify.png';
                if (songEl) songEl.textContent = 'Not Playing';
                const artistEl = document.getElementById('spotify-artist');
                if (artistEl) artistEl.textContent = '';
                const albumEl = document.getElementById('spotify-album');
                if (albumEl) albumEl.textContent = '';
                const progEl = document.getElementById('spotify-progress');
                if (progEl) progEl.style.width = '0%';
                clearInterval(progressInterval);
                progressInterval = null;
                currentProgress = 0;
                currentTrackId = null;
                return;
            }

            const track = data.spotify;
            let firstLoad = false;
            const songEl = document.getElementById('spotify-song');
            if (songEl && !songEl.textContent) {
                firstLoad = true;
            }

            const trackId = track.song_name + track.artist;
            const isNewTrack = currentTrackId !== null && currentTrackId !== trackId;
            const progressBar = document.getElementById('spotify-progress');

            if (isNewTrack && progressBar) {
                currentProgress = 0;
                progressBar.style.transition = 'none';
                progressBar.style.width = '0%';
                progressBar.offsetHeight;
                progressBar.style.transition = 'width 0.1s linear';
            }

            currentTrackId = trackId;

            const artEl = document.getElementById('spotify-album-art');
            if (artEl) artEl.src = track.album_art;
            if (songEl) songEl.textContent = track.song_name;
            const artistEl = document.getElementById('spotify-artist');
            if (artistEl) artistEl.textContent = track.artist;
            const albumEl = document.getElementById('spotify-album');
            if (albumEl) albumEl.textContent = track.album_name;

            if (progressBar) {
                if (track.is_playing) {
                    currentProgress = (track.progress_ms / track.duration_ms) * 100;
                    trackDuration = track.duration_ms;
                    lastUpdateTime = Date.now();

                    progressBar.style.width = currentProgress + '%';

                    if (progressInterval) {
                        clearInterval(progressInterval);
                    }
                    progressInterval = setInterval(animateProgressBar, 100);
                } else {
                    progressBar.style.width = currentProgress + '%';
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
            }

            if (firstLoad) {
                updateVisibility();
            }
        } catch (err) {
            console.error('Failed to fetch Spotify data', err);
        }
    }

    function animateProgressBar() {
        if (trackDuration === 0) return;

        const now = Date.now();
        const elapsed = now - lastUpdateTime;
        lastUpdateTime = now;

        const progressIncrement = (elapsed / trackDuration) * 100;
        currentProgress += progressIncrement;

        const progressBar = document.getElementById('spotify-progress');
        if (progressBar) {
            if (currentProgress >= 100) {
                currentProgress = 100;
                progressBar.style.width = '100%';
                clearInterval(progressInterval);
                progressInterval = null;
                setTimeout(updateSpotifyWidget, 500);
            } else {
                progressBar.style.width = currentProgress + '%';
            }
        }
    }

    updateSpotifyWidget();
    window.addEventListener('resize', updateVisibility);
    setInterval(updateSpotifyWidget, 15000);
})();

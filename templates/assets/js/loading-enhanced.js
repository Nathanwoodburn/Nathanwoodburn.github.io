document.addEventListener("DOMContentLoaded", function() {
    const loadingScreen = document.getElementById("loading-screen");
    
    // Terminal simulation data
    const commands = [
        { pre: '┌──(<span class="blue">nathan@NWTux</span>)-[<span class="white">~</span>]', message: "cd Git" },
        { pre: '┌──(<span class="blue">nathan@NWTux</span>)-[<span class="white">~/Git</span>]', message: "cd Nathanwoodburn.github.io" },
        { pre: '┌──(<span class="blue">nathan@NWTux</span>)-[<span class="white">~/Git/Nathanwoodburn.github.io</span>]', message: "python3 main.py" }
    ];
    
    const serverMessages = [
        "Starting server with 1 workers and 2 threads",
        "+0000] [1] [INFO] Starting gunicorn 22.0.0",
        "+0000] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)",
        "+0000] [1] [INFO] Using worker: gthread",
        "+0000] [8] [INFO] Booting worker with pid: 8",
        "Preloading assets for faster navigation..."
    ];
    
    let currentCommand = 0;
    let assetsLoaded = false;
    let terminalComplete = false;
    
    // Enhanced asset preloading function
    function preloadAssets() {
        const assets = [
            // Additional CSS files that might not be in preload
            '/assets/css/animate.min.min.css',
            '/assets/css/fixes.min.css',
            '/assets/css/Footer-Dark-icons.min.css',
            '/assets/css/GridSystem-1.min.css',
            // Font files
            '/assets/fonts/fa-solid-900.woff2',
            '/assets/fonts/fa-brands-400.woff2',
            '/assets/fonts/fa-regular-400.woff2'
        ];
        
        let loadedCount = 0;
        const totalAssets = assets.length;
        
        function onAssetLoad() {
            loadedCount++;
            if (loadedCount === totalAssets) {
                assetsLoaded = true;
                checkReadyToRedirect();
            }
        }
        
        // Load additional assets
        assets.forEach(assetUrl => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = assetUrl.endsWith('.css') ? 'style' : 
                     assetUrl.endsWith('.js') ? 'script' : 
                     assetUrl.includes('/fonts/') ? 'font' : 'fetch';
            if (link.as === 'font') {
                link.crossOrigin = 'anonymous';
            }
            link.href = assetUrl;
            link.onload = onAssetLoad;
            link.onerror = onAssetLoad; // Count errors as loaded to prevent hanging
            document.head.appendChild(link);
        });
        
        // If no additional assets, mark as loaded
        if (totalAssets === 0) {
            assetsLoaded = true;
            checkReadyToRedirect();
        }
    }
    
    function checkReadyToRedirect() {
        if (assetsLoaded && terminalComplete) {
            setTimeout(redirectToIndex, 200);
        }
    }
    
    function getCurrentTime() {
        const now = new Date();
        return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')} ${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')}`;
    }
    
    function displayServerMessages(messages, callback) {
        const timestamp = getCurrentTime();
        
        for (let i = 0; i < messages.length; i++) {
            const messageDiv = document.createElement("div");
            messageDiv.classList.add("loading-line");
            messageDiv.innerHTML = i !== 0 ? "[" + timestamp + "] " + messages[i] : messages[i];
            loadingScreen.appendChild(messageDiv);
        }
        
        callback();
    }
    
    function redirectToIndex() {
        if (window.location.pathname === "/") {
            window.location.reload();
        } else {
            window.location.href = "/";
        }
    }
    
    // Event listeners for manual redirect
    window.addEventListener("keypress", redirectToIndex);
    
    if (window.innerWidth < 768) {
        console.log("Screen width is less than 768px, allowing click to redirect");
        window.addEventListener("click", redirectToIndex);
    }
    
    function typeCommand(command, callback) {
        const preDiv = document.createElement("div");
        preDiv.classList.add("loading-pre");
        preDiv.innerHTML = command.pre;
        loadingScreen.appendChild(preDiv);
        
        const commandDiv = document.createElement("div");
        commandDiv.classList.add("loading-line");
        commandDiv.innerHTML = '└─<span class="blue">$</span> <span class="cursor"></span>';
        loadingScreen.appendChild(commandDiv);
        
        let charIndex = 0;
        const typeInterval = setInterval(() => {
            commandDiv.removeChild(commandDiv.querySelector(".cursor"));
            commandDiv.innerHTML += command.message[charIndex] + '<span class="cursor"></span>';
            charIndex++;
            
            if (charIndex === command.message.length) {
                commandDiv.removeChild(commandDiv.querySelector(".cursor"));
                clearInterval(typeInterval);
                callback();
            }
        }, 50);
    }
    
    function runTerminalSimulation() {
        if (currentCommand < commands.length) {
            typeCommand(commands[currentCommand], () => {
                currentCommand++;
                setTimeout(runTerminalSimulation, 200);
            });
        } else {
            displayServerMessages(serverMessages, () => {
                terminalComplete = true;
                checkReadyToRedirect();
            });
        }
    }
    
    // Start the loading process
    preloadAssets();
    runTerminalSimulation();
});

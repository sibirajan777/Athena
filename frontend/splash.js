/**
 * Athena App Splash Screen
 * Plays once on first load then fades out before main UI appears
 */

(function () {
    // Inject splash HTML + CSS immediately (before DOMContentLoaded)
    const splashCSS = `
    #athena-splash {
        position: fixed;
        inset: 0;
        z-index: 9999;
        background: #faf9f5;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 20px;
        pointer-events: none;
        transition: opacity 0.55s cubic-bezier(0.4, 0, 0.2, 1), transform 0.55s cubic-bezier(0.4, 0, 0.2, 1);
    }
    [data-theme="dark"] #athena-splash { background: #1f1e1b; }

    #athena-splash.splash-out {
        opacity: 0;
        transform: scale(1.04);
        pointer-events: none;
    }

    .splash-emblem {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: splashPop 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s both;
    }

    .splash-ring {
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
    }

    .splash-ring-1 {
        width: 124px;
        height: 124px;
        border: 1.5px dashed rgba(20,20,19,0.18);
        animation: splashOrbit1 20s linear infinite;
    }
    [data-theme="dark"] .splash-ring-1 { border-color: rgba(236,235,228,0.18); }

    .splash-ring-2 {
        width: 152px;
        height: 152px;
        border: 1px solid transparent;
        border-top-color: rgba(204,120,92,0.75);
        border-bottom-color: rgba(204,120,92,0.75);
        animation: splashOrbit2 12s linear infinite;
        box-shadow: 0 0 18px rgba(204,120,92,0.15);
    }
    [data-theme="dark"] .splash-ring-2 {
        border-top-color: rgba(217,119,87,0.85);
        border-bottom-color: rgba(217,119,87,0.85);
        box-shadow: 0 0 22px rgba(217,119,87,0.22);
    }

    .splash-logo-circle {
        width: 94px;
        height: 94px;
        background: #ffffff;
        border: 1.5px solid rgba(20,20,19,0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        box-shadow: 0 10px 32px -8px rgba(20,20,19,0.1);
        position: relative;
        z-index: 2;
    }
    [data-theme="dark"] .splash-logo-circle {
        background: #272622;
        border-color: rgba(236,235,228,0.1);
        box-shadow: 0 10px 32px -8px rgba(0,0,0,0.5);
    }

    .splash-logo-circle img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    [data-theme="dark"] .splash-logo-circle img {
        filter: invert(1) brightness(1.2);
    }

    .splash-wordmark {
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 28px;
        font-weight: 600;
        letter-spacing: -0.03em;
        color: #141413;
        animation: splashFadeUp 0.5s ease 0.55s both;
    }
    [data-theme="dark"] .splash-wordmark { color: #ecebe4; }

    .splash-tagline {
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 13px;
        color: rgba(20,20,19,0.4);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        animation: splashFadeUp 0.5s ease 0.7s both;
    }
    [data-theme="dark"] .splash-tagline { color: rgba(236,235,228,0.35); }

    .splash-loader-bar {
        width: 120px;
        height: 2px;
        background: rgba(20,20,19,0.08);
        border-radius: 2px;
        overflow: hidden;
        animation: splashFadeUp 0.4s ease 0.75s both;
    }
    [data-theme="dark"] .splash-loader-bar { background: rgba(236,235,228,0.08); }

    .splash-loader-fill {
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, #cc785c, #141413);
        border-radius: 2px;
        animation: splashLoaderFill 1.1s cubic-bezier(0.4, 0, 0.2, 1) 0.8s forwards;
    }
    [data-theme="dark"] .splash-loader-fill {
        background: linear-gradient(90deg, #d97757, #ecebe4);
    }

    @keyframes splashPop {
        from { opacity: 0; transform: scale(0.75); }
        to   { opacity: 1; transform: scale(1); }
    }
    @keyframes splashFadeUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes splashOrbit1 {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
    }
    @keyframes splashOrbit2 {
        from { transform: rotate(360deg); }
        to   { transform: rotate(0deg); }
    }
    @keyframes splashLoaderFill {
        from { width: 0%; }
        to   { width: 100%; }
    }

    /* Hide main content until splash exits */
    body.splash-active > :not(#athena-splash) {
        opacity: 0;
        pointer-events: none;
    }
    body.splash-done > :not(#athena-splash) {
        opacity: 1;
        transition: opacity 0.45s ease 0.05s;
        pointer-events: auto;
    }
    `;

    const styleEl = document.createElement("style");
    styleEl.textContent = splashCSS;
    document.head.appendChild(styleEl);

    function buildSplash() {
        const splash = document.createElement("div");
        splash.id = "athena-splash";
        splash.innerHTML = `
            <div class="splash-emblem">
                <div class="splash-ring splash-ring-2"></div>
                <div class="splash-ring splash-ring-1"></div>
                <div class="splash-logo-circle">
                    <img src="assets/logo-dark.png" alt="Athena">
                </div>
            </div>
            <div class="splash-wordmark">Athena</div>
            <div class="splash-tagline">AI Knowledge Assistant</div>
            <div class="splash-loader-bar">
                <div class="splash-loader-fill"></div>
            </div>
        `;
        document.body.classList.add("splash-active");
        document.body.insertBefore(splash, document.body.firstChild);

        // Dismiss after loader finishes (~2s total)
        setTimeout(() => {
            splash.classList.add("splash-out");
            document.body.classList.remove("splash-active");
            document.body.classList.add("splash-done");
            setTimeout(() => {
                splash.remove();
                document.body.classList.remove("splash-done");
            }, 600);
        }, 2000);
    }

    if (document.body) {
        buildSplash();
    } else {
        document.addEventListener("DOMContentLoaded", buildSplash);
    }
})();

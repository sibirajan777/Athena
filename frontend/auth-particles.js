/**
 * Auth Page Particle Engine
 * Lightweight zero-gravity constellation canvas for Sign In / Sign Up pages
 */

(function () {
    const canvas = document.getElementById("auth-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];
    let animId = null;
    let w = 0, h = 0;
    const COUNT = 38;
    const MAX_DIST = 110;
    const mouse = { x: -999, y: -999 };

    // ── Staggered card entrance ─────────────────────────────────────────────
    function runStagger() {
        const items = document.querySelectorAll(".stagger-item");
        items.forEach((el, i) => {
            el.style.animationDelay = `${0.55 + i * 0.09}s`;
            el.classList.add("stagger-ready");
        });
    }

    // ── Resize ───────────────────────────────────────────────────────────────
    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }

    // ── Particle factory ─────────────────────────────────────────────────────
    function mkParticle() {
        const accent = Math.random() < 0.2;
        return {
            x: Math.random() * w,
            y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.38,
            vy: (Math.random() - 0.5) * 0.38,
            r: Math.random() * 1.8 + (accent ? 2 : 1),
            accent,
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: 0.018 + Math.random() * 0.025
        };
    }

    function createParticles() {
        particles = Array.from({ length: COUNT }, mkParticle);
    }

    // ── Theme colour helper ──────────────────────────────────────────────────
    function colours() {
        const dark = document.documentElement.getAttribute("data-theme") === "dark";
        return {
            node: dark ? "rgba(236,235,228," : "rgba(20,20,19,",
            accent: dark ? "rgba(217,119,87," : "rgba(204,120,92,",
            line: dark ? "rgba(236,235,228," : "rgba(20,20,19,",
            accentLine: dark ? "rgba(217,119,87," : "rgba(204,120,92,"
        };
    }

    // ── Update ───────────────────────────────────────────────────────────────
    function update() {
        const t = performance.now() * 0.001;
        particles.forEach(p => {
            p.pulse += p.pulseSpeed;

            p.x += p.vx;
            p.y += p.vy;
            p.vx *= 0.994;
            p.vy *= 0.994;

            // Gentle drift maintenance
            if (Math.abs(p.vx) < 0.12) p.vx += (Math.random() - 0.5) * 0.04;
            if (Math.abs(p.vy) < 0.12) p.vy += (Math.random() - 0.5) * 0.04;

            // Mouse gravity
            const dx = mouse.x - p.x, dy = mouse.y - p.y;
            const dist = Math.hypot(dx, dy);
            if (dist < 130 && dist > 4) {
                const f = ((130 - dist) / 130) * 0.18;
                p.vx += (dx / dist) * f;
                p.vy += (dy / dist) * f;
            }

            // Wrap edges
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;
        });
    }

    // ── Draw ─────────────────────────────────────────────────────────────────
    function draw() {
        ctx.clearRect(0, 0, w, h);
        const c = colours();

        // Connection threads
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const a = particles[i], b = particles[j];
                const d = Math.hypot(a.x - b.x, a.y - b.y);
                if (d < MAX_DIST) {
                    const alpha = (1 - d / MAX_DIST) * 0.18;
                    ctx.beginPath();
                    ctx.moveTo(a.x, a.y);
                    ctx.lineTo(b.x, b.y);
                    ctx.strokeStyle = (a.accent || b.accent)
                        ? `${c.accentLine}${alpha * 1.5})`
                        : `${c.line}${alpha})`;
                    ctx.lineWidth = 0.75;
                    ctx.stroke();
                }
            }
        }

        // Nodes
        particles.forEach(p => {
            const br = p.r + Math.sin(p.pulse) * 0.55;
            ctx.beginPath();
            ctx.arc(p.x, p.y, Math.max(0.5, br), 0, Math.PI * 2);
            if (p.accent) {
                ctx.fillStyle = `${c.accent}0.75)`;
                ctx.shadowBlur = 9;
                ctx.shadowColor = `${c.accent}0.5)`;
            } else {
                ctx.fillStyle = `${c.node}0.4)`;
                ctx.shadowBlur = 0;
            }
            ctx.fill();
        });
        ctx.shadowBlur = 0;
    }

    function loop() {
        update();
        draw();
        animId = requestAnimationFrame(loop);
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    window.addEventListener("resize", () => { resize(); createParticles(); });
    window.addEventListener("mousemove", e => { mouse.x = e.clientX; mouse.y = e.clientY; });
    window.addEventListener("mouseleave", () => { mouse.x = -999; mouse.y = -999; });

    resize();
    createParticles();
    runStagger();
    loop();

    // ── Page-exit transition for auth links ──────────────────────────────────
    document.querySelectorAll(".auth-link, .btn-primary[type='submit']").forEach(el => {
        if (el.tagName === "A") {
            el.addEventListener("click", function (e) {
                const href = this.getAttribute("href");
                if (href && !href.startsWith("http")) {
                    e.preventDefault();
                    document.getElementById("auth-wrapper").classList.add("exit-up");
                    setTimeout(() => { window.location.href = href; }, 380);
                }
            });
        }
    });
})();

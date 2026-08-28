/**
 * Antigravity Visual Engine
 * Interactive Zero-Gravity Particle Constellation & Ambient Physics
 */

class AntigravityEngine {
    constructor(canvasId = "antigravity-canvas") {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext("2d");
        this.particles = [];
        this.particleCount = 50;
        this.maxDistance = 120;
        this.mouse = { x: -1000, y: -1000, radius: 150, active: false };
        this.animFrameId = null;

        this.init();
    }

    init() {
        this.resize();
        this.createParticles();
        this.setupEvents();
        this.loop();
    }

    resize() {
        if (!this.canvas) return;
        this.width = this.canvas.parentElement.clientWidth;
        this.height = this.canvas.parentElement.clientHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;

        // Adjust particle density based on screen size
        if (this.width < 768) {
            this.particleCount = 24;
            this.maxDistance = 85;
        } else {
            this.particleCount = 48;
            this.maxDistance = 125;
        }
    }

    getThemeColors() {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        return {
            particleColor: isDark ? "rgba(236, 235, 228, 0.45)" : "rgba(20, 20, 19, 0.35)",
            accentParticleColor: isDark ? "rgba(217, 119, 87, 0.75)" : "rgba(204, 120, 92, 0.65)",
            lineColor: isDark ? "rgba(236, 235, 228," : "rgba(20, 20, 19,",
            accentLineColor: isDark ? "rgba(217, 119, 87," : "rgba(204, 120, 92,"
        };
    }

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            const isAccent = Math.random() < 0.25;
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                vx: (Math.random() - 0.5) * 0.45,
                vy: (Math.random() - 0.5) * 0.45,
                baseRadius: Math.random() * 2 + (isAccent ? 2.2 : 1.2),
                radius: Math.random() * 2 + 1.2,
                isAccent: isAccent,
                pulseSpeed: 0.02 + Math.random() * 0.03,
                pulseOffset: Math.random() * Math.PI * 2
            });
        }
    }

    setupEvents() {
        window.addEventListener("resize", () => {
            this.resize();
            this.createParticles();
        });

        // Mouse hover interaction inside main content
        const container = this.canvas.parentElement;
        if (container) {
            container.addEventListener("mousemove", (e) => {
                const rect = this.canvas.getBoundingClientRect();
                this.mouse.x = e.clientX - rect.left;
                this.mouse.y = e.clientY - rect.top;
                this.mouse.active = true;
            });

            container.addEventListener("mouseleave", () => {
                this.mouse.active = false;
                this.mouse.x = -1000;
                this.mouse.y = -1000;
            });

            // Click ripple impulse
            container.addEventListener("click", (e) => {
                const rect = this.canvas.getBoundingClientRect();
                this.triggerImpulse(e.clientX - rect.left, e.clientY - rect.top);
            });
        }
    }

    triggerImpulse(x, y) {
        this.particles.forEach(p => {
            const dx = p.x - x;
            const dy = p.y - y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 200 && dist > 0) {
                const force = (200 - dist) / 200;
                p.vx += (dx / dist) * force * 2.5;
                p.vy += (dy / dist) * force * 2.5;
            }
        });
    }

    loop() {
        this.update();
        this.draw();
        this.animFrameId = requestAnimationFrame(() => this.loop());
    }

    update() {
        const time = performance.now() * 0.001;

        this.particles.forEach(p => {
            // Organic breathing radius
            p.radius = p.baseRadius + Math.sin(time * p.pulseSpeed * 10 + p.pulseOffset) * 0.6;

            // Zero-gravity position update
            p.x += p.vx;
            p.y += p.vy;

            // Gentle damping so particles drift smoothly
            p.vx *= 0.992;
            p.vy *= 0.992;

            // Maintain slight baseline cosmic drift
            if (Math.abs(p.vx) < 0.15) p.vx += (Math.random() - 0.5) * 0.05;
            if (Math.abs(p.vy) < 0.15) p.vy += (Math.random() - 0.5) * 0.05;

            // Mouse gravitational interaction
            if (this.mouse.active) {
                const dx = this.mouse.x - p.x;
                const dy = this.mouse.y - p.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < this.mouse.radius && dist > 5) {
                    const force = (this.mouse.radius - dist) / this.mouse.radius;
                    // Gentle orbital gravity pull
                    p.vx += (dx / dist) * force * 0.25;
                    p.vy += (dy / dist) * force * 0.25;
                }
            }

            // Screen boundary wrapping
            if (p.x < 0) p.x = this.width;
            if (p.x > this.width) p.x = 0;
            if (p.y < 0) p.y = this.height;
            if (p.y > this.height) p.y = 0;
        });
    }

    draw() {
        if (!this.ctx) return;
        this.ctx.clearRect(0, 0, this.width, this.height);

        const colors = this.getThemeColors();

        // 1. Draw connecting constellation threads
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const p1 = this.particles[i];
                const p2 = this.particles[j];
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < this.maxDistance) {
                    const alpha = (1 - dist / this.maxDistance) * 0.22;
                    this.ctx.beginPath();
                    this.ctx.moveTo(p1.x, p1.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    
                    if (p1.isAccent || p2.isAccent) {
                        this.ctx.strokeStyle = `${colors.accentLineColor} ${alpha * 1.4})`;
                    } else {
                        this.ctx.strokeStyle = `${colors.lineColor} ${alpha})`;
                    }
                    this.ctx.lineWidth = 0.8;
                    this.ctx.stroke();
                }
            }
        }

        // 2. Draw particle nodes
        this.particles.forEach(p => {
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, Math.max(0.5, p.radius), 0, Math.PI * 2);
            
            if (p.isAccent) {
                this.ctx.fillStyle = colors.accentParticleColor;
                // Delicate glow halo on accent nodes
                this.ctx.shadowBlur = 8;
                this.ctx.shadowColor = colors.accentParticleColor;
            } else {
                this.ctx.fillStyle = colors.particleColor;
                this.ctx.shadowBlur = 0;
            }
            
            this.ctx.fill();
        });

        // Reset shadow
        this.ctx.shadowBlur = 0;
    }
}

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    window.antigravity = new AntigravityEngine("antigravity-canvas");
});

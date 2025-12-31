/**
 * Background Particle Animation
 * Implements a morphing particle system that transitions between shapes based on view.
 */

export class ParticleBackground {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.time = 0;
        this.mode = 'OVERVIEW';
        this.activeSectionId = 'section-overview';

        this.colors = {
            'overview': '#3b82f6',
            'landscape': '#10b981',
            'flow': '#f59e0b',
            'wordcloud': '#ec4899',
            'leaderboard': '#fbbf24',
            'ai': '#8b5cf6'
        };

        this.currentColor = this.colors['overview'];
        this.targetColor = this.hexToRgb(this.currentColor);
        this.displayColor = { ...this.targetColor };
        this.pointer = { x: 0, y: 0, targetX: 0, targetY: 0, strength: 0, targetStrength: 0 };
        this.motionMediaQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
        this.prefersReducedMotion = this.motionMediaQuery?.matches || false;
        this.updateMotionTuning();

        this.handlePointerMove = this.handlePointerMove.bind(this);
        this.handlePointerLeave = this.handlePointerLeave.bind(this);
        this.handlePrefersMotionChange = this.handlePrefersMotionChange.bind(this);

        this.init();
        this.animate();

        window.addEventListener('resize', () => this.resize());
        window.addEventListener('pointermove', this.handlePointerMove);
        window.addEventListener('pointerleave', this.handlePointerLeave);
        window.addEventListener('blur', this.handlePointerLeave);
        if (this.motionMediaQuery) {
            if (this.motionMediaQuery.addEventListener) {
                this.motionMediaQuery.addEventListener('change', this.handlePrefersMotionChange);
            } else if (this.motionMediaQuery.addListener) {
                this.motionMediaQuery.addListener(this.handlePrefersMotionChange);
            }
        }
    }

    init() {
        this.resize();
    }

    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        const desired = this.calculateParticleBudget();
        if (desired !== this.numParticles) {
            this.numParticles = desired;
            this.createParticles(true);
        } else {
            this.setMode(this.activeSectionId);
        }
    }

    createParticles(forceReset = false) {
        if (!forceReset && this.particles.length === this.numParticles) {
            return;
        }
        this.particles = [];
        if (!this.numParticles) {
            this.numParticles = this.calculateParticleBudget();
        }
        for (let i = 0; i < this.numParticles; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                z: Math.random() * 2000 - 1000,
                tx: 0, ty: 0, tz: 0, // Target positions
                vx: 0, vy: 0, vz: 0, // Velocities
                size: Math.random() * 2 + 0.5,
                color: this.currentColor
            });
        }
        this.setMode(this.activeSectionId);
    }

    setMode(sectionId) {
        this.activeSectionId = sectionId || this.activeSectionId || 'section-overview';
        const key = (this.activeSectionId.replace('section-', '') || 'overview');
        this.mode = key.toUpperCase();
        this.currentColor = this.colors[key] || '#ffffff';
        this.targetColor = this.hexToRgb(this.currentColor);

        // Update targets based on mode
        let i = 0;
        const cx = this.width / 2;
        const cy = this.height / 2;

        if (this.mode === 'OVERVIEW') {
            // SPHERE
            const radius = 350;
            for (let p of this.particles) {
                const theta = Math.acos(2 * Math.random() - 1);
                const phi = Math.sqrt(this.numParticles * Math.PI) * theta;
                p.tx = cx + radius * Math.sin(theta) * Math.cos(phi);
                p.ty = cy + radius * Math.sin(theta) * Math.sin(phi);
                p.tz = radius * Math.cos(theta);
            }
        } else if (this.mode === 'LANDSCAPE') {
            // WAVY PLANE
            for (let p of this.particles) {
                const x = (i % 40) * 30 - 600 + cx;
                const z = Math.floor(i / 40) * 30 - 600;
                p.tx = x;
                p.ty = cy + 100 + Math.sin(x * 0.01 + z * 0.01) * 50;
                p.tz = z;
                i++;
            }
        } else if (this.mode === 'FLOW') {
            // STREAM
            for (let p of this.particles) {
                p.tx = (Math.random() - 0.5) * this.width * 1.5 + cx;
                p.ty = (Math.random() - 0.5) * this.height + cy;
                p.tz = (Math.random() - 0.5) * 800;
            }
        } else if (this.mode === 'WORDCLOUD') {
            // EXPLOSION / RANDOM CLOUD
            for (let p of this.particles) {
                const theta = Math.random() * Math.PI * 2;
                const r = Math.random() * 400;
                p.tx = cx + r * Math.cos(theta);
                p.ty = cy + r * Math.sin(theta);
                p.tz = (Math.random() - 0.5) * 600;
            }
        } else if (this.mode === 'LEADERBOARD') {
            // TOWER / PILLAR
            for (let p of this.particles) {
                const theta = Math.random() * Math.PI * 2;
                const r = 100 + Math.random() * 50;
                p.tx = cx + r * Math.cos(theta);
                p.ty = Math.random() * this.height; // Spread vertically
                p.tz = r * Math.sin(theta);
            }
        } else if (this.mode === 'AI') {
            // NETWORK / CUBE
            const size = 400;
            for (let p of this.particles) {
                p.tx = cx + (Math.random() - 0.5) * size;
                p.ty = cy + (Math.random() - 0.5) * size;
                p.tz = (Math.random() - 0.5) * size;
            }
        }
    }

    animate() {
        if (!document.body.classList.contains('landing-active')) {
            // Pause animation when not in landing mode to save resources
            requestAnimationFrame(() => this.animate());
            return;
        }

        this.ctx.clearRect(0, 0, this.width, this.height);
        this.time += 0.005;

        this.updateDisplayColor();
        this.updatePointerState();

        // Sort particles by Z for depth sorting
        this.particles.sort((a, b) => b.z - a.z);

        const cx = this.width / 2;
        const cy = this.height / 2;

        // Rotation matrices based on time
        const cosY = Math.cos(this.time);
        const sinY = Math.sin(this.time);
        const cosX = Math.cos(this.time * 0.5);
        const sinX = Math.sin(this.time * 0.5);

        const flowFollowSpeed = Math.max(this.lerpSpeed * 1.6, 0.025);
        for (let p of this.particles) {
            // Special behavior for Flow mode (streaming)
            if (this.mode === 'FLOW') {
                p.tx += this.flowSpeed;
                if (p.tx > this.width + 200) p.tx = -200;
                // Lerp current to target (softer follow)
                p.x += (p.tx - p.x) * flowFollowSpeed;
                p.y += (p.ty - p.y) * flowFollowSpeed;
                p.z += (p.tz - p.z) * flowFollowSpeed;
            } else {
                // Standard Morph Lerp
                p.x += (p.tx - p.x) * this.lerpSpeed;
                p.y += (p.ty - p.y) * this.lerpSpeed;
                p.z += (p.tz - p.z) * this.lerpSpeed;
            }

            // 3D Rotation
            // Center geometry
            let dx = p.x - cx;
            let dy = p.y - cy;
            let dz = p.z;

            // Rotate Y
            let x1 = dx * cosY - dz * sinY;
            let z1 = dx * sinY + dz * cosY;

            // Rotate X (optional, adds more 3D feel)
            let y2 = dy * cosX - z1 * sinX;
            let z2 = dy * sinX + z1 * cosX;

            // Projection
            const fov = 800;
            const scale = fov / (fov + z2);
            // Pointer parallax adds subtle camera drift based on cursor intent
            const parallaxGain = 40 * this.pointer.strength;
            const parallaxScale = 0.3 + scale;
            x1 += this.pointer.x * parallaxGain * parallaxScale;
            y2 += this.pointer.y * parallaxGain * 0.5 * parallaxScale;
            const x2d = x1 * scale + cx;
            const y2d = y2 * scale + cy;

            // Draw
            const depthFade = Math.max(0, Math.min(1, scale - 0.15));
            const alpha = Math.min(1, depthFade * 0.9);
            if (scale > 0) {
                this.ctx.beginPath();
                this.ctx.arc(x2d, y2d, p.size * scale, 0, Math.PI * 2);
                this.ctx.fillStyle = this.getColorString(alpha * 0.7 + 0.1);
                this.ctx.globalAlpha = 1;
                this.ctx.fill();
            }
        }

        requestAnimationFrame(() => this.animate());
    }

    calculateParticleBudget() {
        const area = this.width * this.height;
        const base = Math.min(1600, Math.max(260, Math.round(area / 1800)));
        let budget = base;
        if (this.width < 900) {
            budget = Math.round(budget * 0.75);
        }
        if (this.prefersReducedMotion) {
            budget = Math.round(budget * 0.6);
        }
        return Math.max(180, budget);
    }

    updateMotionTuning() {
        this.lerpSpeed = this.prefersReducedMotion ? 0.015 : 0.035;
        this.flowSpeed = this.prefersReducedMotion ? 1 : 2.6;
    }

    handlePointerMove(evt) {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const nx = ((evt.clientX - rect.left) / rect.width) - 0.5;
        const ny = ((evt.clientY - rect.top) / rect.height) - 0.5;
        this.pointer.targetX = nx * 2;
        this.pointer.targetY = ny * 2;
        this.pointer.targetStrength = 1;
    }

    handlePointerLeave() {
        this.pointer.targetStrength = 0;
    }

    handlePrefersMotionChange(event) {
        this.prefersReducedMotion = event?.matches ?? this.prefersReducedMotion;
        this.updateMotionTuning();
        this.numParticles = this.calculateParticleBudget();
        this.createParticles(true);
    }

    updatePointerState() {
        this.pointer.x += (this.pointer.targetX - this.pointer.x) * 0.08;
        this.pointer.y += (this.pointer.targetY - this.pointer.y) * 0.08;
        this.pointer.strength += (this.pointer.targetStrength - this.pointer.strength) * 0.05;
    }

    updateDisplayColor() {
        this.displayColor.r += (this.targetColor.r - this.displayColor.r) * 0.08;
        this.displayColor.g += (this.targetColor.g - this.displayColor.g) * 0.08;
        this.displayColor.b += (this.targetColor.b - this.displayColor.b) * 0.08;
    }

    getColorString(alpha = 1) {
        const a = Math.max(0, Math.min(1, alpha));
        return `rgba(${Math.round(this.displayColor.r)}, ${Math.round(this.displayColor.g)}, ${Math.round(this.displayColor.b)}, ${a})`;
    }

    hexToRgb(hex) {
        const value = hex.replace('#', '');
        const bigint = parseInt(value, 16);
        if (Number.isNaN(bigint)) {
            return { r: 255, g: 255, b: 255 };
        }
        return {
            r: (bigint >> 16) & 255,
            g: (bigint >> 8) & 255,
            b: bigint & 255
        };
    }
}

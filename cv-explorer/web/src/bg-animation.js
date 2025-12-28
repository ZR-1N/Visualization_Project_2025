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
        this.numParticles = 1200;
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.mode = 'SPHERE';
        this.time = 0;
        
        this.colors = {
            'overview': '#3b82f6',
            'landscape': '#10b981',
            'flow': '#f59e0b',
            'wordcloud': '#ec4899',
            'leaderboard': '#fbbf24',
            'ai': '#8b5cf6'
        };
        
        this.currentColor = this.colors['overview'];
        
        this.init();
        this.animate();
        
        window.addEventListener('resize', () => this.resize());
    }

    init() {
        this.resize();
        this.createParticles();
    }

    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    }

    createParticles() {
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
        this.setMode('overview'); // Set initial targets
    }

    setMode(sectionId) {
        const key = sectionId.replace('section-', '');
        this.mode = key.toUpperCase();
        this.currentColor = this.colors[key] || '#ffffff';
        
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

        // Sort particles by Z for depth sorting
        this.particles.sort((a, b) => b.z - a.z);

        const cx = this.width / 2;
        const cy = this.height / 2;
        
        // Rotation matrices based on time
        const cosY = Math.cos(this.time);
        const sinY = Math.sin(this.time);
        const cosX = Math.cos(this.time * 0.5);
        const sinX = Math.sin(this.time * 0.5);

        for (let p of this.particles) {
            // Special behavior for Flow mode (streaming)
            if (this.mode === 'FLOW') {
                 p.tx += 2;
                 if (p.tx > this.width + 200) p.tx = -200;
                 // Lerp current to target (softer follow)
                 p.x += (p.tx - p.x) * 0.05;
                 p.y += (p.ty - p.y) * 0.05;
                 p.z += (p.tz - p.z) * 0.05;
            } else {
                 // Standard Morph Lerp
                 p.x += (p.tx - p.x) * 0.03;
                 p.y += (p.ty - p.y) * 0.03;
                 p.z += (p.tz - p.z) * 0.03;
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
            const x2d = x1 * scale + cx;
            const y2d = y2 * scale + cy;

            // Draw
            const alpha = Math.min(1, (scale - 0.2)); // Fade out distant
            if (scale > 0) {
                this.ctx.beginPath();
                this.ctx.arc(x2d, y2d, p.size * scale, 0, Math.PI * 2);
                this.ctx.fillStyle = this.currentColor;
                this.ctx.globalAlpha = alpha * 0.6; // Base transparency
                this.ctx.fill();
            }
        }
        
        requestAnimationFrame(() => this.animate());
    }
}

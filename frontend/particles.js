const canvas = document.createElement('canvas');
document.getElementById('particles-container').appendChild(canvas);
const ctx = canvas.getContext('2d');

let width, height;
function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
}
window.addEventListener('resize', resize);
resize();

const particles = [];
const particleCount = 40;

for (let i = 0; i < particleCount; i++) {
    particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 4 + 1,
        dx: (Math.random() - 0.5) * 0.3,
        dy: -(Math.random() * 0.8 + 0.2),
        alpha: Math.random() * 0.4 + 0.1
    });
}

function animate() {
    ctx.clearRect(0, 0, width, height);
    particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(212, 175, 55, ${p.alpha})`; // Gold dust effect
        ctx.fill();
        
        p.x += p.dx;
        p.y += p.dy;
        
        // Float back to bottom when reaching top
        if (p.y + p.r < 0) {
            p.y = height + p.r;
            p.x = Math.random() * width;
        }
    });
    requestAnimationFrame(animate);
}
animate();

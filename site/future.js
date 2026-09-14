(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canvas = document.getElementById('signal-canvas');
  const ctx = canvas && canvas.getContext('2d');
  let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
  let nodes = [];

  function resize() {
    if (!canvas || !ctx) return;
    w = window.innerWidth; h = window.innerHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.max(28, Math.min(64, Math.round(w / 26)));
    nodes = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - .5) * .12, vy: (Math.random() - .5) * .12,
      r: Math.random() * 1.2 + .45
    }));
  }

  function frame() {
    if (!ctx || reduce) return;
    ctx.clearRect(0, 0, w, h);
    for (const n of nodes) {
      n.x += n.vx; n.y += n.vy;
      if (n.x < -20) n.x = w + 20; if (n.x > w + 20) n.x = -20;
      if (n.y < -20) n.y = h + 20; if (n.y > h + 20) n.y = -20;
    }
    ctx.lineWidth = .6;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      ctx.beginPath();
      ctx.fillStyle = 'rgba(124,231,255,.34)';
      ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2); ctx.fill();
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 150) {
          ctx.strokeStyle = `rgba(124,231,255,${(1 - dist / 150) * .07})`;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    }
    requestAnimationFrame(frame);
  }

  window.addEventListener('resize', resize, { passive: true });
  resize(); if (!reduce) requestAnimationFrame(frame);

  document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('pointermove', e => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - r.left}px`);
      card.style.setProperty('--my', `${e.clientY - r.top}px`);
    });
  });

  const menu = document.querySelector('.nav');
  const toggle = document.querySelector('.menu-toggle');
  toggle?.addEventListener('click', () => menu?.classList.toggle('open'));
  menu?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => menu.classList.remove('open')));

  const modal = document.getElementById('command-modal');
  const openers = document.querySelectorAll('[data-command-open]');
  const close = document.querySelector('.modal-close');
  const openModal = () => { modal?.classList.add('open'); document.body.style.overflow = 'hidden'; };
  const closeModal = () => { modal?.classList.remove('open'); document.body.style.overflow = ''; };
  openers.forEach(x => x.addEventListener('click', openModal));
  close?.addEventListener('click', closeModal);
  modal?.addEventListener('click', e => { if (e.target === modal) closeModal(); });
  window.addEventListener('keydown', e => {
    if (e.key === '/' && !/input|textarea/i.test(document.activeElement?.tagName || '')) { e.preventDefault(); openModal(); }
    if (e.key === 'Escape') closeModal();
  });

  const reveal = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.animate([
        { opacity: 0, transform: 'translateY(18px)' },
        { opacity: 1, transform: 'translateY(0)' }
      ], { duration: 650, easing: 'cubic-bezier(.2,.75,.25,1)', fill: 'both' });
      reveal.unobserve(entry.target);
    });
  }, { threshold: .12 });
  if (!reduce) document.querySelectorAll('[data-reveal]').forEach(el => reveal.observe(el));

  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();

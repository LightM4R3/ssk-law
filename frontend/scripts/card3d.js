// Mouse-tilt + dynamic shadow + radial shine effect for cards.
// bindPick3D: large carousel cards (gentler tilt)
// bindCard3D: latest-grid + search-result cards (stronger tilt)
function bindPick3D(el) {
  let raf = null;
  el.addEventListener("mousemove", (e) => {
    if (carDragging) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      const rx = (py - 0.5) * -4.5;
      const ry = (px - 0.5) * 6;
      const sx = (px - 0.5) * -36;
      const sy = (py - 0.5) * -22 + 28;
      el.style.setProperty("--rx", rx + "deg");
      el.style.setProperty("--ry", ry + "deg");
      el.style.setProperty("--sx", sx + "px");
      el.style.setProperty("--sy", sy + "px");
      el.style.setProperty("--mx", (px * 100) + "%");
      el.style.setProperty("--my", (py * 100) + "%");
      el.classList.add("tilting");
    });
  });
  const reset = () => {
    el.classList.remove("tilting");
    el.style.removeProperty("--rx");
    el.style.removeProperty("--ry");
    el.style.removeProperty("--sx");
    el.style.removeProperty("--sy");
  };
  el.addEventListener("mouseleave", reset);
  el.addEventListener("pointerdown", reset);
}

function bindCard3D(el) {
  let raf = null;
  el.addEventListener("mousemove", (e) => {
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      const rx = (py - 0.5) * -7;
      const ry = (px - 0.5) * 9;
      const sx = (px - 0.5) * -28;
      const sy = (py - 0.5) * -16 + 22;
      el.style.setProperty("--rx", rx + "deg");
      el.style.setProperty("--ry", ry + "deg");
      el.style.setProperty("--sx", sx + "px");
      el.style.setProperty("--sy", sy + "px");
      el.style.setProperty("--mx", (px * 100) + "%");
      el.style.setProperty("--my", (py * 100) + "%");
      el.classList.add("tilting");
    });
  });
  el.addEventListener("mouseleave", () => {
    el.classList.remove("tilting");
    el.style.removeProperty("--rx");
    el.style.removeProperty("--ry");
    el.style.removeProperty("--sx");
    el.style.removeProperty("--sy");
  });
}


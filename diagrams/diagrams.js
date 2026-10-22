mermaid.initialize({ startOnLoad: false });

mermaid.run().then(() => {
  document.querySelectorAll(".mermaid svg").forEach((svg) => {
    const box = svg.viewBox.baseVal;
    if (!box || !box.width || !box.height) {
      return;
    }
    svg.setAttribute("width", String(box.width));
    svg.setAttribute("height", String(box.height));
    svg.style.width = `${box.width}px`;
    svg.style.height = `${box.height}px`;
    svg.style.maxWidth = "none";
  });
});

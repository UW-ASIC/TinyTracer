// MathJax configuration for pymdownx.arithmatex (generic mode).
// Arithmatex emits \( ... \) for inline and \[ ... \] for display math,
// wrapped in elements with class "arithmatex". Restrict MathJax to those
// so stray dollar signs elsewhere in the docs are left alone.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

window.MathJax = {
  tex: {
    tags: 'ams',
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']],
    // The FEBio Theory Manual LyX source defines a handful of custom
    // LaTeX operators in its document preamble (\newcommand{\tr}{...}
    // etc., see FEBio_Theory_Manual.lyx lines ~104-158). The Feature
    // Manual has no such preamble macros, so this `macros` block is an
    // intentional addition beyond the Feature Manual's baseline config,
    // needed so MathJax can render these operators instead of leaving
    // raw command names on the page. \obslash has no macro definition
    // anywhere in the LyX source (a genuine gap in the original document,
    // not introduced by this converter) -- it is approximated here as an
    // overlined \oslash, which matches its use alongside the already-
    // defined \oslash operator in continuum-mechanics tensor notation;
    // see CONVERSION_NOTES.md.
    macros: {
      tr: '\\operatorname{tr}',
      dev: '\\operatorname{dev}',
      Dev: '\\operatorname{Dev}',
      grad: '\\operatorname{grad}',
      Grad: '\\operatorname{Grad}',
      divg: '\\operatorname{div}',
      Divg: '\\operatorname{Div}',
      Ei: '\\operatorname{Ei}',
      cay: '\\operatorname{cay}',
      rot: '\\operatorname{rot}',
      obslash: '\\overline{\\oslash}',
      // \mbox is plain-TeX/LaTeX only; MathJax's default macro set does
      // not define it. The LyX source uses \mbox{...} in a handful of
      // places (section 2.1 eq. 11 "\mbox{\thinspace and\thinspace}";
      // also \mbox{\dot{...}}, \mbox{grad}, \mbox{div}, \mbox{M} in later
      // sections), mixing literal text with nested math macros like
      // \dot{} and \thinspace. Real LaTeX \mbox switches to horizontal
      // (text) mode but macros are still expanded textually beforehand;
      // MathJax's \text{} does not expand nested macros at all. Aliasing
      // \mbox to a no-op group (rather than \text) keeps its argument in
      // math mode so nested macros like \dot{} and \thinspace still
      // typeset correctly, at the cost of rendering plain-word arguments
      // ("grad", "div", "M") in italic math font instead of upright text
      // font -- a minor cosmetic difference documented in
      // CONVERSION_NOTES.md.
      mbox: ['{#1}', 1],
      thinspace: '\\,'
    }
  }
};

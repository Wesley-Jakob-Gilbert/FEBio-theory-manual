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
    // not introduced by this converter). Visual comparison against the
    // published manual confirmed it should render as U+29B8 CIRCLED
    // REVERSE SOLIDUS (a backslash-in-a-circle, the mirror image of
    // \oslash's U+2298 CIRCLED DIVISION SLASH) -- consistent with its use
    // alongside \oslash as its "conjugate" (X-transposed) counterpart in
    // eqs. 17-24; see CONVERSION_NOTES.md.
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
      obslash: '\\mathbin{\\unicode{x29B8}}',
      // \mbox is plain-TeX/LaTeX only; MathJax's default macro set does
      // not define it. The LyX source uses \mbox{...} in a handful of
      // places (section 2.1 eq. 11 "\mbox{\thinspace and\thinspace}";
      // also \mbox{\dot{...}}, \mbox{grad}, \mbox{div}, \mbox{M} in later
      // sections), mixing literal text with nested math macros like
      // \dot{} and \thinspace. Real LaTeX \mbox switches to horizontal
      // (text) mode but macros are still expanded textually beforehand;
      // MathJax's \text{} does not expand nested macros at all, so
      // aliasing \mbox to \text{} would leave literal "\thinspace"/"\dot{}"
      // command names on the page. \mathrm{} keeps the argument in math
      // mode -- so nested macros like \dot{} and \thinspace still expand
      // -- while switching the font to upright/roman, giving correct
      // rendering for both the macro-nesting cases and the plain-word
      // cases ("and", "grad", "div", "M") in one alias.
      mbox: ['\\mathrm{#1}', 1],
      thinspace: '\\,'
    }
  }
};

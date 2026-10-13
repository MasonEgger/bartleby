# Acknowledgments

Bartleby is MIT licensed (see [LICENSE](LICENSE)).
This file credits what Bartleby bundles, adapts, and learned from.
Each entry names the project, what was taken, the license, and whether that license is compatible with shipping inside an MIT package.
Licenses were read from the upstream repositories, not from memory.
Last checked 2026-10-12.

## Bundled Code

These files ship inside the Bartleby wheel.
The full notices that their licenses require are reproduced under Notices below.

- **Alpine.js 3.14.1**, `themes/base/static/js/alpine.min.js`.
  MIT, Copyright 2019-2021 Caleb Porzio and contributors.
  https://github.com/alpinejs/alpine.
  Compatible: MIT into MIT.
  The file has no header comment, so the notice below and `THIRD-PARTY-NOTICES` carry it.
- **htmx 2.0.4**, `themes/base/static/js/htmx.min.js`.
  Zero-Clause BSD, Big Sky Software and contributors.
  https://github.com/bigskysoftware/htmx.
  Compatible: 0BSD asks for no notice, and permits any use.
- **lunr.js 2.3.9**, `themes/base/static/js/lunr.min.js`.
  MIT, Copyright 2020 Oliver Nightingale.
  https://github.com/olivernn/lunr.js.
  Compatible: MIT into MIT.
  The file keeps its own header comment.
- **Material Design Icons (Pictogrammers)**, 10 SVGs in `themes/base/icons/material/` and one inline path in `themes/material/templates/partials/back_to_top.html`.
  Apache License 2.0.
  https://github.com/Templarian/MaterialDesign.
  Compatible: Apache-2.0 permits redistribution inside an MIT package when the license text ships with it and modified files are marked.
  `src/bartleby/THIRD-PARTY-NOTICES` carries the full license text, and this entry marks the modified files.
  `home.svg` and `close.svg` match the upstream paths exactly, and the material back-to-top partial inlines the upstream `chevron-up` path unchanged.
  The other eight files are modified: `account.svg`, `arrow-up.svg`, `calendar.svg`, `chevron-right.svg`, `clock.svg`, `magnify.svg`, `menu.svg`, and `tag.svg` are close or simplified revisions of the upstream glyphs.
- **Font Awesome Free (brands)**, 5 SVGs in `themes/base/icons/fontawesome-brands/`.
  Icons are CC BY 4.0, Copyright Fonticons, Inc.
  https://fontawesome.com/license/free.
  Compatible: CC BY 4.0 allows redistribution with attribution, which this entry gives.
  The paths are an earlier revision of the glyphs (512-unit grid, 496 wide), so they differ from the current pack.
- **Octicons**, 5 SVGs in `themes/base/icons/octicons/`.
  MIT, Copyright 2026 GitHub Inc.
  https://github.com/primer/octicons.
  Compatible: MIT into MIT.
  `star-16` matches the outline of the current glyph and omits its inner cutout, so it renders filled.
  Others are close revisions.
- **Simple Icons**, 4 SVGs in `themes/base/icons/simple/`.
  CC0 1.0 Universal.
  https://github.com/simple-icons/simple-icons.
  Compatible: public-domain dedication.
  The marks themselves are trademarks of their owners (GitHub, JavaScript, Python, Rust); the CC0 grant covers the drawing, not the brand.
- **Tailwind CSS 3.4.17** and **@tailwindcss/typography**, compiled into `themes/*/static/css/main.css`.
  MIT, Copyright Tailwind Labs, Inc.
  https://github.com/tailwindlabs/tailwindcss.
  The compiled CSS also carries Tailwind's preflight reset, which is derived from modern-normalize (MIT, Copyright Nicolas Gallagher, Jonathan Neal, and Sindre Sorhus, https://github.com/sindresorhus/modern-normalize).
  Compatible: MIT into MIT.

## Adapted Code and Assets

- **Lucide sun icon**, the sun in `themes/base/templates/partials/color_mode_toggle.html`.
  ISC, Copyright 2026 Lucide Icons and Contributors.
  https://github.com/lucide-icons/lucide.
  The sun has the same construction as Lucide's `sun`: a circle of radius 4 at the center and eight rays from 2 to 4 and 20 to 22.
  The diagonal rays are rounded to one decimal.
  Treated as adapted, and credited.
  Compatible: ISC is a permissive license that needs only the notice below.
- **The moon icon** in the same file is original.
  Its path matches no Lucide, Feather, or Heroicons moon (all three were compared).
- **markwright** (Mason Egger, MIT) is a dependency, not a borrowing.
  `themes/base/static/js/click_to_load.js` is Bartleby's own host script and follows markwright's documented click-to-load markup contract.
- **Material indigo color values** in the material theme's palette are color constants, not code.
  No stylesheet or template was copied from Material for MkDocs.

## Design Inspiration

No code was copied from these projects.
Each is listed because the spec asks for the credit and the license check.
Verdict for every entry: inspiration only, no code copied.

- **Zensical** (the Material for MkDocs team).
  MIT, Copyright 2025-2026 Zensical and contributors.
  https://github.com/zensical/zensical (`LICENSE.md`, confirmed MIT; PyPI metadata agrees).
  The three-column docs layout and the position that docs output should be solid.
- **Material for MkDocs** 9.7.5.
  MIT, Copyright 2016-2025 Martin Donath.
  https://github.com/squidfunk/mkdocs-material.
  The docs-site shape (header tabs, section sidebar, page table of contents) and the vocabulary many authors already know.
  Bartleby's theme vocabulary is its own.
- **MkDocs**.
  BSD 2-Clause, Copyright 2014-present Tom Christie.
  https://github.com/mkdocs/mkdocs.
  The model of a YAML config, a nav tree, and a Markdown content directory.
- **Hugo**.
  Apache License 2.0.
  https://github.com/gohugoio/hugo.
  The shape of first-run output, and page bundles for co-located assets.
- **sphinx-autobuild**.
  MIT, Copyright 2020 Pradyun Gedam and 2013 Jonathan Stoppani.
  https://github.com/sphinx-doc/sphinx-autobuild.
  The design of a dev server that rebuilds on change and reloads the browser.
  Bartleby's server is written on Starlette and uvicorn with its own reload hub.
- **Furo**.
  MIT, Copyright 2020 Pradyun Gedam.
  https://github.com/pradyunsg/furo.
  Restraint in the Scrivener theme: neutral palette, one accent, little decoration.

## Notices

Alpine.js (MIT):

> Copyright 2019-2021 Caleb Porzio and contributors
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

lunr.js (MIT):

> Copyright (C) 2013 by Oliver Nightingale
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Octicons (MIT):

> Copyright (c) 2026 GitHub Inc.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Tailwind CSS (MIT):

> Copyright (c) Tailwind Labs, Inc.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

modern-normalize (MIT):

> Copyright (c) Nicolas Gallagher
> Copyright (c) Jonathan Neal
> Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (sindresorhus.com)
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Lucide (ISC):

> Copyright (c) 2026 Lucide Icons and Contributors
>
> Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.
>
> THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Material Design Icons (Apache-2.0): licensed under the Apache License, Version 2.0.
The full text is in `src/bartleby/THIRD-PARTY-NOTICES`, which ships inside the package.
Upstream has no NOTICE file.
Eight of the ten icon files (`account`, `arrow-up`, `calendar`, `chevron-right`, `clock`, `magnify`, `menu`, `tag`) differ from the current upstream glyphs, so treat them as modified; `home`, `close`, and the inline `chevron-up` in the material theme's `partials/back_to_top.html` are unmodified.

Font Awesome Free icons (CC BY 4.0): Copyright Fonticons, Inc., https://fontawesome.com.
Licensed under https://creativecommons.org/licenses/by/4.0/.
The icons here were modified (reduced to a single path with no embedded comment).

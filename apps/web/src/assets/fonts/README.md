# Local reading fonts

The current interface uses Noto Serif SC Variable, pinned in `apps/web/package.json`.
Vite bundles its Unicode-range WOFF2 files from `@fontsource-variable/noto-serif-sc`.
Body text uses weight 400 and headings use weight 800. The license is shipped at
`/licenses/noto-serif-sc.txt`. Font files are loaded from the application origin.

- [Fontsource package](https://fontsource.org/fonts/noto-serif-sc)

## Previous releases

Noto Sans SC (400 regular and 600 semibold), distributed under the adjacent
SIL Open Font License. The CSS family alias is `Ciyuan Sans`.

Upstream: https://github.com/google/fonts/tree/main/ofl/notosanssc

Google Fonts v40 source files:

- Regular: https://fonts.gstatic.com/s/notosanssc/v40/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_FnYw.ttf
- Semibold: https://fonts.gstatic.com/s/notosanssc/v40/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaGwHCnYw.ttf

The two WOFF subsets cover the characters in the checked-in frontend and course
copy, ASCII and punctuation (about 420 KiB total). New/dynamic characters not
present in the subset use Noto Sans SC / PingFang SC / Microsoft YaHei fallbacks.
Fonts are served by Vite with content hashes, not a third-party font CDN.
`font-display: swap` keeps text visible while they load or when they fail.

To refresh after significant curriculum/localization additions, download the
two upstream TTFs and run `python apps/web/scripts/subset_fonts.py regular.ttf
semibold.ttf` from the repository root. This optional asset-build step requires
fontTools; the application and normal build have no new dependencies.

Barlow Condensed Light supplies the narrow Latin display face. DM Sans supplies Latin reading and control text. Both Latin WOFF2 subsets are bundled locally from Google Fonts. Chinese headings prefer the platform light face and fall back to the existing CJK subset. Fonts are served by the application.

- [Barlow Condensed](https://github.com/google/fonts/tree/main/ofl/barlowcondensed), license in barlow-condensed-light-OFL.txt
- [DM Sans](https://github.com/google/fonts/tree/main/ofl/dmsans), license in dm-sans-OFL.txt

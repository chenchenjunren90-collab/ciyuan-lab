# Local reading fonts

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

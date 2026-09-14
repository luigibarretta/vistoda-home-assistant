# Vistoda integration icon

`icon.png` reuses the Vistoda app artwork from
`vistoda-apple/Sources/iOS/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png`.
It represents Vistoda, not Ring, Blink or EZVIZ.

Home Assistant 2026.3+ serves this local asset through its authenticated
brands API. Home Assistant's standard fallback chain also uses it for logo,
dark-mode and high-resolution requests; no CDN submission or frontend patch
is needed. See the [Home Assistant brand image contract](https://developers.home-assistant.io/docs/core/integration/brand_images/).

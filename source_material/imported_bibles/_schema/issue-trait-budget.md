# Issue Trait Budget

The comic generator should normally use fewer traits than the Bible contains. Recognition comes from consistency, not from exhausting every quirk.

## Default Per Character, Per Issue

- 1 defining personality trait
- 0 or 1 speech trait
- 0 or 1 physical behavior
- 0 or 1 running element
- 1 story-relevant strength or weakness

The system may use fewer. Exceed the budget only when the story intentionally focuses on that character.

## Cooldowns

Catchphrases and running gags should have cooldowns. A funny line becomes weaker if the generator reaches for it every issue.

Suggested defaults:

- Catchphrase cooldown: at least 1 issue between uses unless it is the point of the scene.
- Running gag cooldown: at least 1 issue between uses unless the issue spotlights that gag.
- Special traits: require explicit context.

## Selection Priority

1. Use traits relevant to the scene goal.
2. Prefer defining or strong traits over a pile of background details.
3. Avoid combining traits that flatten the character into a caricature.
4. For ensemble scenes, use the character's story function before minor quirks.
5. If a trait is `rarely` or `special circumstances only`, require a reason.

## Validation Expectations

- `maximum_defining_traits_per_issue` should normally be 0 to 1 and never above 3.
- `maximum_minor_quirks_per_issue` should normally be 0 to 2 and never above 4.
- Trait cooldowns must be non-negative integers.
- Trait combinations marked incompatible should not be selected together by issue planning tools.


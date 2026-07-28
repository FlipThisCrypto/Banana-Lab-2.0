# Trait Status Guide

Every trait needs a status, strength, and usage frequency. This keeps the Bible useful without forcing unfinished characters to pretend they are complete.

## Status

- `canon`: immutable unless deliberately revised by the project owner.
- `established`: repeatedly used and considered reliable.
- `experimental`: may be tested in a future comic.
- `optional`: available when useful but not defining.
- `dormant`: previously used but currently inactive.
- `retired`: should no longer appear.
- `contradicted`: conflicts with stronger canon and requires review.
- `unknown`: not yet determined.
- `reserved`: intentionally left open for future development.

## Strength

- `defining`: may appear frequently and helps the audience recognize the character.
- `strong`: reliable, but not required in every appearance.
- `moderate`: useful when story-relevant.
- `subtle`: light flavor that should not drive a scene by itself.
- `background`: rare texture; do not use it merely to fill space.

## Usage Frequency

- `almost always`
- `often`
- `sometimes`
- `rarely`
- `special circumstances only`
- `never`

## Example Trait

```yaml
- category: speech_pattern
  name: short deadpan lines
  value: Uses short declarative sentences when uncomfortable.
  status: established
  strength: strong
  usage_frequency: often
  source_refs:
    - MonkeyZoo_Comic_Factory/00_SYSTEM/character_bible.md
  notes: Use only when the scene benefits from restraint.
```

## Empty Is Valid

Use `unknown` when a trait is not known yet. Use `reserved` when the space is intentionally being held for later development. Do not turn a reserved field into personality filler.


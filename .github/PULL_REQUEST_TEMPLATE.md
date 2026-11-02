## What this changes

## If it touches a platform fact

- [ ] Status is honest (official means the platform says it)
- [ ] Source link added, and `as_of` is the day I checked
- [ ] I searched the skills for the fact's id and updated any text that quotes it

## Checks

- [ ] `python -m unittest discover -s tests`
- [ ] `python scripts/validate_skills.py`
- [ ] `python scripts/lint_prose.py`
- [ ] `python scripts/sync_shims.py --check`
- [ ] `python scripts/gen_refs.py --check`

## Tested where

Say what you ran it in. If you could not test something, say that too.

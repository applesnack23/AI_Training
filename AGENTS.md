# Unity Project AI Rules

## Project Scope
- Focus on Assets/Scripts.
- Read Packages/manifest.json only when needed.
- Read Unity scenes and prefabs only when required.

## Excluded Directories
- Library/
- Temp/
- Logs/
- obj/
- Build/
- Builds/
- Assets/Models/
- Assets/Textures/

## Working Rules
- Do not scan the entire project.
- Search for relevant classes before opening files.
- Read only files related to the requested feature.
- Avoid unnecessary changes to scenes and prefabs.
- Preserve existing public interfaces.
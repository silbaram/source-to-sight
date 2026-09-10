# First-time user quickstart

[한국어](quickstart.md) | English

Follow this guide to **create an HTML explanation of your project and open it in a browser**. Explore project map → capability/behavior → a picture-first explanation of its important business rules. Start with one map and add only the details you need.

Source to Sight is a set of skills for a coding agent. You ask a question, the agent reads the actual source and writes an explanation, and the bundled tools validate the data and generate HTML. It is not a separate web service you need to run.

Complete steps 1–4 for your first result. Steps 5–6 are optional.

Jump to: [Preparation](#1-prepare-your-tools-and-project) · [Installation](#2-install-the-skills) · [Readiness](#3-open-your-project-and-check-readiness) · [First map](#4-create-and-open-your-first-project-map) · [Walkthrough](#5-optional-add-a-capability-walkthrough) · [Rules](#6-optional-explain-conditions-reasons-and-exceptions) · [Troubleshooting](#troubleshooting)

## First: where do I enter things?

| Place | What to do there |
| --- | --- |
| Terminal / Windows PowerShell | Check versions and run `npx skills ...` installation commands. |
| Coding agent chat | Send explanation requests starting with `$codebase-atlas`, `$code-flow`, and similar skill names. |
| Web browser | Open the generated `.html` files and explore the explanation. |

`$code-flow` is not a terminal command. Paste the **agent chat** examples into your coding agent. A plain chat without local-file tools cannot read your project.

## 1. Prepare your tools and project

Where: a terminal. Use PowerShell on Windows, or a terminal app or editor terminal on macOS and Linux. WSL is not required.

Prepare the following. You do not need to reinstall tools you already have.

- A coding agent that can read local folders, run commands, and use Agent Skills: finish its installation and sign-in first. Check the [Skills CLI supported-agent list](https://github.com/vercel-labs/skills#supported-agents).
- [Git](https://git-scm.com/install/): used to fetch skills and remote repositories.
- [Node.js](https://nodejs.org/en/download): choose a supported LTS release for a new installation. The current [Skills CLI minimum](https://github.com/vercel-labs/skills/blob/main/package.json) is **22.20.0**; npm/npx must also be available.
- [Python 3.10 or newer](https://www.python.org/downloads/): used for source-backed HTML generation. No additional Python packages, `pip` step, or virtual environment are required.
- A local folder containing the source you want explained, and a browser for the output.

Run these commands one line at a time:

```sh
git --version
node --version
npm --version
npx --version
```

If PowerShell blocks `npm.ps1` or `npx.ps1`, check with `npm.cmd --version` or `npx.cmd --version`, respectively. npm provides the Windows [npm.cmd](https://github.com/npm/cli/blob/latest/bin/npm.cmd) and [npx.cmd](https://github.com/npm/cli/blob/latest/bin/npx.cmd) launchers. You can also replace `npx` with `npx.cmd` in the remaining commands in this guide.

Check Python with the command for your operating system.

macOS and Linux:

```sh
python3 --version
```

Windows PowerShell:

```powershell
python --version
```

If Windows cannot find `python` and the Python launcher is installed, try `py --version`. Tell the agent which command actually worked.

**Ready to continue when:** every command prints a version, Node.js is at least 22.20.0, and Python is at least 3.10. Python 3.9, for example, needs an upgrade. If a command is missing, install the tool using its official instructions above, then reopen the terminal and agent.

If you already have the project on your computer, use that folder. If it only exists on GitHub, download and extract it or clone it with Git first. **You do not need to clone the Source to Sight repository itself.** The next step installs the skills directly.

Installation needs internet access. Connectivity and data handling during analysis depend on your coding agent's settings; check your access permissions and your organization's source-use policy. You do not need to start the target project's server or install all of its dependencies.

## 2. Install the skills

Where: a terminal. This one-line command works in both Bash and PowerShell.

```sh
npx skills add silbaram/source-to-sight --global --skill '*'
```

1. If the first run asks to run the `skills` package, check its name and continue.
2. If an agent selection screen appears, choose **the agent you actually use**. Follow the on-screen selection and confirmation keys. If an agent is selected automatically, check that the installation summary names the right one.
3. If asked for an installation method, use the default. If symlink creation fails, use the `--copy` option in troubleshooting below.
4. Wait for installation to finish, then check the skill names and target agent in the summary.

`--global` installs for your user across projects; `--skill '*'` selects all skills in this repository. See the [official CLI options](https://github.com/vercel-labs/skills#options).

Check the installed list too:

```sh
npx skills ls -g
```

**Ready to continue when:** `code-flow`, `codebase-atlas`, and `visual-primer` appear and are linked to your chosen agent. This check follows the [CLI's list implementation](https://github.com/vercel-labs/skills/blob/main/src/list.ts).

You do not need to move skill folders or install Python packages afterward. If your environment requires manual copying, preserve each complete skill folder, including scripts, templates, references, vendored files, and licenses—not just `SKILL.md`.

## 3. Open your project and check readiness

Where: your coding agent's chat.

1. Open **the source folder of the project you want explained** in the agent, not the folder where the skills were installed.
2. Start a new conversation so the installed skills can be discovered.
3. Copy and send this request:

```text
I am using Source to Sight for the first time. Check readiness only; do not generate HTML yet.

1. Tell me the root path of the project currently open.
2. Find the actual installed paths of code-flow, codebase-atlas, and visual-primer, and check availability.
3. Find a Python 3.10+ command and report its version and executable path.
4. Use that Python to run the installed author.py doctor and atlas.py doctor.
   If code-flow is installed separately, pass its actual --code-flow-root to atlas.py.

Do not modify source code or configuration. If anything is missing, report the error and the action needed.
```

If step 1 worked with `py` or another command instead of `python`, add that information. If the agent requests approval to read local files or run these checks, inspect the target and command before approving.

`doctor` checks the generation tools and installed resources. It does not analyze or test your project.

**Ready to continue when:** the project path is correct, all three skills are available, and both `doctor` commands finish without errors. If a skill is missing, use troubleshooting below before moving on.

## 4. Create and open your first project map

Where: the same agent conversation you used in step 3.

```text
$codebase-atlas Create an English project map for someone seeing this project for the first time.
Explain its purpose, main responsibilities, real package/folder structure, component relationships, and representative capabilities using the actual source.
Create only the map for now; do not generate capability detail pages yet.
Distinguish the reviewed scope from anything that could not be verified.

Save the HTML at build/source-to-sight/project.html relative to the project root.
Keep the internal authoring data needed for regeneration under build/source-to-sight/_internal/project/.
Do not modify source code or configuration.
When finished, provide the HTML's absolute path and link, plus the internal data locations.
```

`build/source-to-sight/` is the **output folder** chosen for this guide. Internal authoring JSON lives below the HTML directory in **`_internal/<map HTML filename without extension>/`**, so this request uses `build/source-to-sight/_internal/project/`. The workflow creates the directories if needed; you do not need to write the files yourself. A project-specific storage policy takes precedence. For a separate private location, the agent must also pass that path as the builder's `--internal-dir`.

Without an output-location request, the defaults are `docs/atlas/<project-key>.html` and `docs/atlas/_internal/<project-key>/` under the target project root, not the skill installation folder.

Wait for the agent to read the source and create the files. If it asks which package to cover, choose one package to start with. If an existing output belongs to another project, subject, or language, choose a new output path instead of overwriting it.

When generation finishes:

1. Open the HTML link from the agent. If it does not open, find `build/source-to-sight/project.html` in your file manager and open it with a browser.
2. Read the project purpose and inputs/results. **Analysis source and review scope** reports recorded items, not whole-project completeness or test coverage.
3. Explore the diagram under **How do the parts work together?**. Groups show shared responsibility, not execution order. **Include supporting parts** reveals additional components.
4. Select a generated capability to open its data flow, then a processing node for rule pictures and maintenance evidence. **Find in the capability catalog** and **Find anything** also locate capabilities.
5. Use **Explore packages and folders** for paths or **Inspect the structure** for the full diagram. Read the analysis limits; direct connections are not exhaustive change impact, and recorded tests are not passing results.

GitHub's HTML file view is not the rendered interactive page. Download remote files and open them locally. Viewing the result needs no Node.js, Python, or web server; the interactive map needs JavaScript enabled in the browser.

**Done when:** `project.html` opens and you can explore the purpose, structure, and evidence. A small project may have a single node. Your first use is complete at this point.

## 5. Optional: add a capability walkthrough

Where: first the browser, then the same agent chat.

1. Find a capability in the diagram or **Find in the capability catalog**.
2. Select a generated capability in the diagram or open **Detailed flow** from the catalog.
3. If you see **Copy detail request**, click it to copy the request. An ungenerated detail does not mean the capability is absent.
4. Paste the copied request into the agent, append the following, and send them together:

```text
Keep the copied request's subject, scope, and output path, and generate this capability's behavior explanation.
Store internal authoring data under the existing build/source-to-sight/_internal/project/ and preserve other capabilities' data.
Add only this capability, and rebuild the existing build/source-to-sight/project.html
so I can navigate from the map to the detail and back to the same map.
Report the generated HTML paths when finished.
```

If you changed the output folders earlier, use those same paths here. If copying fails, tell the agent the capability name shown in the map and ask it to confirm the target and scope before generating the detail.

**Done when:** after reopening or refreshing the rebuilt map, you can open the capability detail and return. Ordered behavior may have a walkthrough; an unordered relationship diagram does not need playback controls.

Returning restores search, filters and the selected capability, bringing its card into view without automatically reopening the dialog. Old `tab=roles/files` links still open; the tab value is ignored. Missing folder/test mappings do not establish that those things are absent. Ask the agent to review source and update the internal JSON before adding unrecorded content. For UI-only changes, re-render the retained internal JSON.

The browser button only copies a request. Clicking it does not start analysis or generate HTML.

## 6. Optional: explain conditions, reasons, and exceptions

Where: the same agent conversation as step 5.

This step creates a picture-first lesson with the teaching approach shown in the [OAuth example](../assets/oauth-visual-primer-example.html). A large visual introduces the key decision; condition selection or step controls are added when they help. Different business rules do not have to become the same cards or flowchart.

```text
$code-flow --explain Explain the conditions, outcomes, reasons, and exceptions for the capability we just linked from the map, in English.
Use visual-primer's authored picture lesson so a newcomer can understand the important business rules.
Lead with large meaningful visuals and short explanations; add controls for real conditions or branches when useful.
Preserve the behavior explanation's subject and scope, and reread the actual source.
Keep internal authoring data and the original picture-layout JSON under the existing build/source-to-sight/_internal/project/.
Update the map, behavior, and rules pages together so their navigation links work in both directions.
Save results under the existing build/source-to-sight/ folder and report the HTML paths.
```

Here `--explain` is part of a **skill request**, not a terminal command. This workflow needs both `code-flow` and `visual-primer`, which you installed in step 2.

**Done when:** map → behavior → **Rules & reasons** takes you to a picture-first business-logic lesson. You can expand the exact conditions, reasons, exceptions and evidence, then return to the behavior and the same map. A picture without enough support is replaced by a review notice, not filled in by guesswork.

If you have a reference HTML for the desired visual style, include its actual path in the request. The example lives in this repository's `assets/`; installing only the skills does not copy it into another project. Authored picture lessons are the default even without that reference file.

## Start without a map, or choose another output language

If you only want one capability explained, use `$code-flow` directly after the readiness check in step 3. Replace `TARGET_FUNCTION` below with a real function name or file path from your project.

```text
$code-flow Explain TARGET_FUNCTION's inputs, processing, return values, and error handling in English, based on its source.
Save HTML under build/source-to-sight/ and internal authoring data below it in _internal/<HTML filename without extension>/.
Report the actual file paths.
```

A general concept explainer is a separate workflow from source-backed maps and walkthroughs:

```text
$visual-primer Explain OAuth to a complete beginner using a picture-first English HTML page.
Save it at build/source-to-sight/oauth.html.
```

This guide's main requests already ask for English. To keep a separate English map alongside another language, use explicit paths:

```text
$codebase-atlas Explain this project's purpose, responsibilities, and representative capabilities in English.
Generate only the project map at build/source-to-sight/project.en.html.
Keep internal authoring data under build/source-to-sight/_internal/project.en/ and report all file paths.
Show the reviewed scope and anything that could not be verified. Do not modify source code or configuration.
```

Both Korean and English are supported for explanations and viewer controls. Request each language separately and use different file paths; do not overwrite one language with another. Keep related pages in the same language. For a Korean first-use walkthrough, see the [Korean quickstart](quickstart.md).

## Keep, share, and regenerate your files

| File / folder | Purpose and precautions |
| --- | --- |
| HTML under `build/source-to-sight/` | Browser-ready output. Share linked HTML files together to preserve navigation. |
| Internal JSON under `build/source-to-sight/_internal/project/` | Analysis, source evidence, original picture layouts and page mappings. These are reusable authoring inputs, not shareable outputs. |
| Optional render JSON | Display data. It does not replace the internal authoring JSON and is not needed just to view the HTML. |

The atlas builder automatically retains `atlas.internal.json` and `pages.json`. For explicitly requested details it also retains `detail-<subject-id>.behavior.internal.json`, `detail-<subject-id>.logic.internal.json` and `detail-<subject-id>.layout.json`; logic/layout files are absent until rules are requested. `<subject-id>` is the capability's filename-escaped unique identifier. A map-only refresh preserves existing detail inputs, and the browser never fetches these JSON files. For standalone `code-flow`, the agent writes the internal input at the requested location; it does not automatically create an atlas bundle.

Files are read and written as UTF-8. Before sharing, review project names, paths, identifiers, and explanations visible or embedded in the HTML. Package the linked HTML files with their relative folder structure intact. Recipients can download and extract them, then open `project.html`. **Exclude the entire `_internal/` directory from shared packages and static-site publishing.** It may contain source excerpts; an underscore-prefixed directory name is not access control.

For presentation-only regeneration, reuse the existing analysis:

```text
Use the original JSON and pages.json under build/source-to-sight/_internal/project/
to re-render the existing map and linked HTML. Keep source snapshot and evidence checks,
and review affected explanations if changes are detected. Do not recreate the original analysis from scratch.
```

HTML does not update automatically when the source changes. With the existing files and internal data available in the project, ask:

```text
Reread the latest source and regenerate build/source-to-sight/project.html and its existing linked explanations.
Reuse the original JSON under build/source-to-sight/_internal/project/, reviewing and updating changed evidence and explanations.
Preserve the existing subjects, scopes, and languages, and refresh links between the pages already generated.
Do not create detail pages for other capabilities we have not requested.
```

This retention feature does not automatically analyze Git diffs or patch parts of HTML. The agent reviews affected source and updates the JSON; the builder renders each explicitly requested page as a complete file. To retain older inputs from `work/` or another location, supply them once to the atlas builder. It does not delete the original inputs, and HTML alone cannot recover lost verification anchors or the full original picture layout.

To update Source to Sight itself, **rerun the installation command in step 2**, then repeat **step 3's readiness check** in a new conversation. Preserve any edits you made to installed copies first. Updating the skills does not automatically update existing HTML.

## Troubleshooting

| Symptom | First action |
| --- | --- |
| `git`, `node`, `npm`, or `npx` is not found | Install the relevant tool from step 1, then reopen the terminal and agent. |
| `EBADENGINE` or a Node version error | Update to a supported Node.js LTS release and check the current CLI requirement. |
| Windows blocks `npx.ps1` | Run the command below with npm's [npx.cmd](https://github.com/npm/cli/blob/latest/bin/npx.cmd). There is no need to disable security policy globally. |
| Symlink creation fails | Use the `--copy` installation command below and select the same agent. |
| Skills are installed but unavailable | Check names and agent links with `npx skills ls -g`, then start a new conversation in the target project. If `$` invocation is not recognized, select the named skill through the host's skill picker. |
| An error or old guide asks you to install `jsonschema` | An older skill copy may be loaded. Update through step 2 and check the actual paths through step 3. |
| No HTML is generated | Ask the agent to inspect the complete error, Python executable and version, and both installed `doctor` results. |
| You cannot find the HTML | Ask the agent for its absolute path. Look in the target project's output folder, not the skill installation folder. |
| A detail still shows a generation request | Send step 5's request, generate the detail, rebuild the map, and refresh. |
| There is no rules page | Check that you requested step 6 and installed `visual-primer`. If the skills came from different releases, repeat step 2 to update all three together. |
| Output belongs to another project, subject, or language | Choose a new output path instead of deleting the existing file or bypassing the check. |
| Old JSON fails at `/snapshot/generatedAt` | Follow the compatibility note below. |

For a blocked `npx.ps1`, in Windows PowerShell:

```powershell
npx.cmd skills add silbaram/source-to-sight --global --skill '*'
```

For a symlink error, in a terminal:

```sh
npx skills add silbaram/source-to-sight --global --skill '*' --copy
```

If both problems occur, add `--copy` to the `npx.cmd` command. The [copy installation option](https://github.com/vercel-labs/skills#installation-methods) copies skill files; it does not require WSL or a global security-policy change.

### Compatibility when rebuilding existing JSON

Starting with authoring tool 0.7.0, the bundled validator always checks internal JSON's `snapshot.generatedAt` as an RFC 3339 timestamp. Invalid dates or times and trailing newlines that older environments accepted are now rejected, so rebuilding old JSON can fail validation.

Check the original generation time and timezone. Correct the value to a form such as `2026-09-07T12:00:00+09:00` or the equivalent UTC `2026-09-07T03:00:00Z`, remove trailing newlines, save as UTF-8, and rerun generation. Do not bypass validation or substitute the current time arbitrarily. You can give the agent the error and internal JSON path and ask it to make this correction.

## Further reading

- [Project-map guide](project-maps.md) (Korean): exploring the viewer and connecting pages.
- [Distribution policy](distribution.md) (Korean): installed resources versus generated files.
- [Skill assembly guide](../skills/code-flow/references/assembly-protocol.md) (English): advanced reference for running generation commands and working with internal data directly.

A source-backed explanation is not the same as a program execution test. Read the recorded scope and limitations; do not interpret them as an observed runtime trace or completed human review unless those checks actually happened.

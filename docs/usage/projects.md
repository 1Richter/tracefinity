# Projects

Projects are named containers that group tools and bins for planning a drawer or workspace layout. They help you organise which tools go together and track progress from tracing through to printing.

## Creating a project

From the dashboard, click **New project**. Give it a name and optional description.

## Project status

Each project has a status that tracks its lifecycle:

| Status | Meaning |
|-|-|
| Active | Work in progress. Tools being traced and bins being designed. |
| Ready to print | All tools are placed in bins. Ready for export. |
| Printed | Bins have been printed. |
| Archived | Project is complete or shelved. |

Change the status from the dropdown in the project header.

## Adding tools

The **Add tools** section shows all tools not yet assigned to the project. Select tools using checkboxes and click **Add**. Use the search field to filter by name. Select all / select none buttons are available.

Tools can belong to multiple projects.

## Removing tools

Click the delete icon next to a tool in the **Project tools** section to remove it from the project. This does not delete the tool itself.

## Tool quantities

Use the **−/+** counter on a tool card to plan for more than one of the same tool -- three identical socket wrenches, for example. The card then tracks progress as "2/3 placed", counting how many copies sit in the project's linked bins.

A tool only counts as placed once every planned copy is in a bin, so the **Unplaced** filter and the dashboard's "need bin" count keep showing it until you are done.

## Filtering project tools

The project tools list has filter buttons:

- **All** shows every tool in the project.
- **Unplaced** shows tools with copies not yet placed in any bin.
- **Placed** shows tools whose every copy is already assigned to a bin.

A search field filters by name within the current filter.

## Creating a bin from a project

1. In the **Project tools** section, tick the tools you want in the new bin.
2. Click **Create bin** in the project header.

The bin is created with the project's default configuration (if set) and opens in the bin editor. The bin is automatically linked to the project.

Tools with a quantity above 1 are placed once per copy, each copy offset slightly so they do not sit on top of each other. The button count shows copies, not distinct tools.

## Default bin settings

Expand the **Bin defaults** section to configure default settings for all new bins created from this project. This uses the same controls as the bin configurator (grid size, height, magnets, stacking lip, etc.).

Click **Save defaults** to store. Click **Clear** to revert to global defaults.

## Linking existing bins

Click **Add existing bin** in the **Linked bins** section header. This shows unassigned bins that can be linked to the project.

Options when importing:

- **Import bin tools** also adds the bin's tools to the project.
- **Show assigned bins** includes bins already linked to other projects.

## Detaching bins

Click the unlink icon next to a bin in the **Linked bins** section. This removes the association but does not delete the bin.

## Deleting bins

Click the delete icon next to a bin to permanently delete it and all associated files.

## Project health check

If there are inconsistencies (orphaned tools, mismatched bin assignments), a health banner appears showing the issues. Common issues:

- A tool referenced by the project no longer exists.
- A bin's project ID does not match.
- A tool in a linked bin is not part of the project.

## Project repair

When health issues are detected and some are repairable, a **Repair links** button appears. Clicking it auto-fixes what it can (re-linking orphaned items, correcting mismatched IDs) and re-runs the health check.

## Bin contents

Expand a linked bin to see which tools are placed in it. Tools from outside the project are flagged with a warning.

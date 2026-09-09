# Bin Layout Editor

The bin layout editor is where you arrange tools inside a gridfinity bin and configure it for printing.

## Layout

The editor has three areas: a configuration sidebar on the left, a 2D canvas in the centre, and a 3D preview on the right. A horizontal tool library strip sits above the canvas and preview.

## Adding tools

The tool library strip shows all available tools (filtered to the current project if you arrived from one). Click a tool to add it to the bin. It is automatically centred, and the grid expands if needed.

## Selecting and moving tools

Click a placed tool to select it. Drag to reposition. The toolbar updates to show options for the selected tool.

Snap is off by default (5mm grid when enabled). Toggle it with the **Snap** button in the floating toolbar.

## Rotating tools

When a tool is selected, a rotation handle appears. Drag it to rotate freely.

## Duplicating tools

With a tool selected, press Ctrl/Cmd+C then Ctrl/Cmd+V, press Ctrl/Cmd+D, or click the copy button in the toolbar. The copy is an independent placement offset 5mm from the original -- moving, rotating or re-cutting it leaves the original alone. Pasting repeatedly cascades the copies instead of stacking them in one spot.

## Per-tool cutout depth

Select a tool to see a **Depth** field in the toolbar. Leave it blank to use the bin's default cutout depth. Enter a value to override it for that tool only. Click the reset button to clear the override.

The **max** value next to the field is the deepest pocket the current bin height allows -- anything deeper would break through the bin floor. Entering more clamps to that maximum and the hint turns amber. The same field and cap apply to a selected cutout.

## Editing cutouts in the bin

Cutouts of a placed tool can be edited without leaving the bin, and the changes apply to that placement only -- the library tool and every other bin keep the original cutouts.

- Pick a cutout shape in the floating toolbar (circle, cylinder, square, rectangle, filleted rectangle) and click a placed tool to add one. Escape returns to Select.
- In Select mode, drag a cutout to move it. When it is selected, drag the round handle to resize, and the handle above it (rectangles and squares) to rotate.
- **Depth** in the toolbar overrides the pocket depth for that cutout.
- The trash button, or the Delete key, removes the selected cutout from this placement.

Edits made here survive reloads: the bin remembers which cutouts were changed or removed, so later edits to the library tool no longer overwrite them. Untouched cutouts still follow the library tool.


## Text labels

1. Click the **Text** tool in the floating toolbar.
2. Click anywhere on the canvas to place a label. A text input appears.
3. Type the label text and press Enter to confirm (Escape to cancel).
4. Double-click an existing label to edit its text.

When a label is selected, the toolbar shows:

- **Text** field to edit the content.
- **Size** to set the font size in mm.
- **Depth** to set how deep the text is cut or raised, in mm.
- **Emboss / Recess** toggle. Emboss raises the text above the surface; recess cuts it in.

Labels can be dragged to reposition and have a rotation handle.

## Auto-size grid

Enabled by default. The grid automatically expands or contracts to fit all placed tools with clearance. Tools are recentred when the grid changes. Turn it off in the sidebar to set grid dimensions manually.

## Recentre

Click **Recentre** in the toolbar to move all placed tools to the centre of the bin.

## 3D preview

The right panel shows a live 3D preview that regenerates whenever the layout or configuration changes. Controls:

- **Drag** to orbit, **scroll** to zoom, **right-drag** to pan.
- Camera preset buttons: Home, Top, Front, Right, Fit.
- Render mode toggle: solid or edges (wireframe).

## Split visualisation

When the bin exceeds the configured bed size, the STL is automatically split. The sidebar shows a "Split into N pieces" banner. The 3D preview shows each piece in a different colour, spaced apart.

## Insert display

When **Contrast Insert** is enabled in the sidebar, the insert appears in the 3D preview as an orange piece alongside the main bin.

## Bin configuration

The sidebar controls all bin parameters:

| Setting | Description |
|-|-|
| Grid Width / Depth | Bin size in gridfinity units (42mm each). 1-25 per axis, up to a 100-cell footprint. |
| Custom size (mm) | Size the bin in exact outer millimetres (42-1000mm) instead of gridfinity units, so it fills a drawer or shelf. Base feet and magnets stay on the 42mm grid; auto-size is disabled. |
| Height | Bin height in units (7mm each + 4.75mm base). |
| Cutout Depth | How deep tool pockets are cut. |
| Clearance | Extra space around tool outlines. |
| Cutout Chamfer | Bevel on the top edge of each pocket. 0 = sharp. |
| Magnet holes | Holes in the base for magnets. Configurable diameter and depth. |
| Corners only | Place magnet holes at the four outer corners only. |
| Stacking lip | Raised rim for stacking bins. |
| Contrast Insert | Generates a separate insert STL for two-colour printing. |
| Insert Height | Thickness of the insert piece. |
| Bed Size | Print bed dimension. Bins exceeding this are split automatically. |
| Partial Bins | Disable individual grid cells in the bin. |

**Save as default** stores the current settings for all new bins. **Reset** restores factory defaults.

## Keyboard shortcuts

| Key | Action |
|-|-|
| Escape | Deselect / cancel text input |
| Enter | Confirm text input |

# QGIS Plugin for GeoAI

A corporate-friendly fork of the [upstream GeoAI plugin](https://github.com/opengeos/geoai) with the same dockable AI tools and a policy-safe runtime path. The plugin does not download or execute Python, uv, Conda/Pixi, PowerShell, or Git installers.

## Corporate Quick Start

1. Install an IT-approved Python that matches QGIS's Python major/minor version (the Windows pilot uses Python 3.12).
2. Create the runtime with standard Python and pip:

    ```text
    python qgis_plugin/setup_corporate_runtime.py --python C:\path\to\approved\python.exe
    ```

3. For an offline deployment, have IT build a complete wheelhouse from `qgis_plugin/geoai/runtime/requirements-corporate.txt`, then run:

    ```text
    python qgis_plugin/setup_corporate_runtime.py --python C:\path\to\approved\python.exe --wheelhouse C:\approved\geoai-wheelhouse
    ```

4. Set `GEOAI_RUNTIME_DIR` to the runtime printed by the script before QGIS starts, install the plugin ZIP, and enable **GeoAI Corporate**.
5. In **Segment Anything → Model**, either select an IT-provisioned checkpoint or click **Download Public SAM 3.1**. The 1.63 GiB file is public, pinned, checksum-verified, and needs no Hugging Face account or token. It remains subject to the [SAM License](geoai/runtime/MODEL_NOTICE.md), which company legal/security teams should approve before deployment.

The built-in setup panel uses the same standard-library `venv` and pip path. Package sources can be controlled with `GEOAI_WHEELHOUSE`, `GEOAI_PIP_INDEX_URL`, `GEOAI_PIP_EXTRA_INDEX_URL`, and `GEOAI_PIP_CERT`. TLS verification is never disabled unless IT explicitly sets `GEOAI_PIP_TRUSTED_HOST` or `GEOAI_ALLOW_INSECURE_INSTALL=1`.

## Video Tutorials

### Installation Tutorial

You can follow this [video tutorial](https://youtu.be/TJmZQXJK-IU) to install the GeoAI QGIS Plugin on Linux/Windows:

[![installation](https://github.com/user-attachments/assets/6fa17c97-2ff5-40d6-be16-c6dcfe03f806)](https://youtu.be/TJmZQXJK-IU)

### Usage Tutorial

Check out this [short video demo](https://youtu.be/Esr_e6_P1is) and [full video tutorial](https://youtu.be/8-OhlqeoyiY) on how to use the GeoAI plugin in QGIS.

[![demo](https://github.com/user-attachments/assets/5aabc3d3-efd1-4011-ab31-2b3f11aab3ed)](https://youtu.be/8-OhlqeoyiY)



## Requirements

-   QGIS 3.28 or later (QGIS 4.x supported)
-   Python 3.12+ matching QGIS's embedded Python major/minor version
-   PyTorch (CUDA if you want GPU acceleration)
-   `geoai` and `samgeo` packages

## Features

Each tool lives inside a dockable panel that can be attached to either side of the QGIS interface, so you can keep layers, maps, and models visible simultaneously.

### Moondream Vision-Language Model Panel

-   **Caption**: Generate descriptions of geospatial imagery (short, normal, or long)
-   **Query**: Ask questions about images using natural language
-   **Detect**: Detect and locate objects with bounding boxes
-   **Point**: Locate specific objects with point markers

### Segmentation Panel (Combined Training & Inference)

-   **Tab 1 - Create Training Data**: Export GeoTIFF tiles from raster and vector data
-   **Tab 2 - Train Models**: Train custom segmentation models (U-Net, DeepLabV3+, FPN, etc.)
-   **Tab 3 - Run Inference**: Apply trained models to new imagery and vectorize results. Vector outputs can optionally be smoothed or simplified for immediate use in GIS workflows.

### SamGeo Panel (Segment Anything Model)

-   **Model Tab**: Load the public SAM 3.1 checkpoint with configurable device settings and no Hugging Face authentication
-   **Text Tab**: Segment objects using text prompts (e.g., "tree", "building", "road")
-   **Interactive Tab**: Segment using point prompts (foreground/background) or box prompts drawn on the map
-   **Batch Tab**: Process multiple points interactively or from vector files/layers
-   **Output Tab**: Save results as raster (GeoTIFF) or vector (GeoPackage, Shapefile) with optional regularization (orthogonalize polygons, filter by minimum area)

### GPU Memory Management

-   **Clear GPU Memory**: Release GPU memory and clear CUDA cache for all loaded models

## Upstream Pixi Installation (Reference Only)

> This section is retained for upstream comparison. It is not used or supported
> by the corporate fork when Conda/Pixi, PowerShell, or runtime executable
> downloads are blocked. Use [Corporate Quick Start](#corporate-quick-start).

### 1. Set up the environment

Installing the GeoAI QGIS plugin can be challenging due to the complicated pytorch/cuda dependencies. Conda or mamba might take a while to resolve the dependencies, while pip might fail to install the dependencies properly. It is recommended to use [pixi](https://pixi.prefix.dev/latest) to install the dependencies to avoid these issues.

#### 1) Install Pixi

#### Linux/macOS (bash/zsh)

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Close and re-open your terminal (or reload your shell) so `pixi` is on your `PATH`. Then confirm:

```bash
pixi --version
```

#### Windows (PowerShell)

Open **PowerShell** (preferably as a normal user, Admin not required), then run:

```powershell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

Close and re-open PowerShell, then confirm:

```powershell
pixi --version
```

---

#### 2) Create a Pixi project

Navigate to a directory where you want to create the project and run:

```powershell
pixi init geo
cd geo
```

---

#### 3) Configure `pixi.toml`

Open `pixi.toml` in the `geo` directory and replace its contents with the following depending on your system.

If you have a NVIDIA GPU with CUDA, run `nvidia-smi` to check the CUDA version.

> **Note:** QGIS is pinned to `3.44.*` on purpose. Do not lower it to `3.42.*`:
> with the dependencies below, that pin resolves to QGIS 3.42.2 (3.42.3 conflicts
> with the rest of the stack), and 3.42.2 shipped a Windows regression that makes
> saving any `.qgz` project fail with "Unable to perform zip"
> ([QGIS #61560](https://github.com/qgis/QGIS/issues/61560), fixed by
> [QGIS #61567](https://github.com/qgis/QGIS/pull/61567)). qgis.org reissued its
> 3.42.2 Windows installer with the fix, but conda-forge builds 3.42.2 from the
> original release, so the broken code is what you get. The bug is in QGIS itself
> and is unrelated to this plugin.
>
> If you already created the environment and hit this, update QGIS in place:
>
> ```bash
> cd geo
> pixi update qgis
> ```
>
> Check **Help → About** to confirm you are off 3.42.2. Until you can update,
> save with *Save As* → **QGIS Project File (\*.qgs)**; `.qgs` is uncompressed
> XML and never touches the zip path, so it is unaffected.

- For GPU with CUDA 12.x:

```toml
[workspace]
channels = ["https://prefix.dev/conda-forge"]
name = "geo"
platforms = ["linux-64", "win-64"]

[system-requirements]
cuda = "12.0"

[dependencies]
python = "3.12.*"
pytorch-gpu = ">=2.7.1,<3"
qgis = "3.44.*"
pyqt = "5.15.*"
geoai = ">=0.24.0"
segment-geospatial = ">=1.2.0"
sam3 = ">=0.1.0.20251211"
libopenblas = ">=0.3.30"
```

- For GPU with CUDA 13.x:

```toml
[workspace]
channels = ["https://prefix.dev/conda-forge"]
name = "geo"
platforms = ["linux-64", "win-64"]

[system-requirements]
cuda = "13.0"

[dependencies]
python = "3.12.*"
pytorch-gpu = ">=2.7.1,<3"
qgis = "3.44.*"
pyqt = "5.15.*"
geoai = ">=0.24.0"
segment-geospatial = ">=1.2.0"
sam3 = ">=0.1.0.20251211"
```

- For CPU:

```toml
[workspace]
channels = ["https://prefix.dev/conda-forge"]
name = "geo"
platforms = ["linux-64", "win-64"]

[dependencies]
python = "3.12.*"
pytorch-cpu = ">=2.7.1,<3"
qgis = "3.44.*"
pyqt = "5.15.*"
geoai = ">=0.24.0"
segment-geospatial = ">=1.2.0"
sam3 = ">=0.1.0.20251211"
libopenblas = ">=0.3.30"
```

---

#### 4) Install the environment

From the `geo` folder:

```powershell
pixi install
```

This step may take several minutes on first install depending on your internet connection and system.

---

#### 5) Verify PyTorch + CUDA

If you have a NVIDIA GPU with CUDA, run the following command to verify the PyTorch + CUDA installation:

```powershell
pixi run python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU:', (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'))"
```

Expected output should be like this:

-   `PyTorch: 2.9.1`
-   `CUDA available: True`
-   `GPU: NVIDIA RTX 4090`

If CUDA is `False`, check:

-   `nvidia-smi` works in PowerShell
-   NVIDIA driver is up to date

---


#### Upstream gated SAM 3 (not used by this fork)

The corporate fork does not call Meta's gated model repository and contains no login flow. It uses the pinned public `Comfy-Org/sam3.1` checkpoint from the Model tab. CUDA is strongly recommended; CPU remains available but may take several minutes per request.

### 2. Install the QGIS plugin

Build the internal plugin ZIP:

```text
python qgis_plugin/package_plugin.py --output geoai-corporate-1.7.1.zip
```

In QGIS, go to **Plugins → Manage and Install Plugins → Install from ZIP**, select that file, and enable **GeoAI Corporate**. Do not install the public repository version over this internal build; it uses the upstream dependency bootstrap.

For a developer checkout, the helper script can copy the fork into the current QGIS profile:

```text
cd qgis_plugin
python install.py
```

Manual copy is also supported:

-   Copy the `qgis_plugin` folder to your QGIS plugins directory:
    -   Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
    -   Windows: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
    -   macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

### 3. Enable in QGIS

Launch the company-installed QGIS, then use **Plugins → Manage and Install Plugins** to enable **GeoAI Corporate**. After updates, toggle the plugin off/on or restart QGIS to reload.

![](https://github.com/user-attachments/assets/1b6dab14-311d-4f62-85aa-1faed73ead5b)

## Usage

### Moondream Vision-Language Model

Sample dataset: [parking_lot.tif](https://huggingface.co/datasets/giswqs/geospatial/resolve/main/parking_lot.tif)

Steps:

1. Click the **Moondream** button in the GeoAI toolbar (or `GeoAI` menu → `Moondream VLM`)
2. Load a Moondream model (default: vikhyatk/moondream2)
3. Select a raster layer or browse for an image file
4. Choose a mode:
    - **Caption**: Generate a description of the image
    - **Query**: Ask a question about the image
    - **Detect**: Detect objects by type (e.g., "building", "car")
    - **Point**: Locate specific objects
5. Click "Run"
6. Results are displayed and optionally added to the map. You can drag the panel to any side of QGIS to keep it out of the way while browsing results. Save the output table or vector layer if you want to reuse detections later.

    ![moondream](https://github.com/user-attachments/assets/bb800a04-b7c4-4fdd-a628-a48842d7eac5)

### Segmentation Panel (Create Data, Train, Inference)

Sample datasets:

-   [naip_rgb_train.tif](https://huggingface.co/datasets/giswqs/geospatial/resolve/main/naip_rgb_train.tif)
-   [naip_test.tif](https://huggingface.co/datasets/giswqs/geospatial/resolve/main/naip_test.tif)
-   [naip_train_buildings.geojson](https://huggingface.co/datasets/giswqs/geospatial/resolve/main/naip_train_buildings.geojson)

Steps:

1. Download the sample datasets (links above) or prepare your own imagery/vector labels. Store them in a folder that is accessible to pixi project.
2. Click the **Segmentation** button in the GeoAI toolbar (or `GeoAI` menu → `Segmentation`)
3. Use the tabs at the top of the panel to switch between:

    - **Create Training Data**: Select input raster and vector labels, configure tile size and stride, and export tiles to a directory.
    - **Train Model**: Select the images and labels directories, choose model architecture (U-Net, DeepLabV3+, etc.), configure training parameters, and start training.
    - **Run Inference**: Select input raster layer or file, specify the trained model path, configure inference parameters, run inference, and optionally vectorize the results.

    ![data](https://github.com/user-attachments/assets/121fcfa8-6f9b-4413-9419-af666698c053)

    ![train](https://github.com/user-attachments/assets/dfeefb86-ebf7-467c-a5ff-794cde80a7cb)

    ![inference](https://github.com/user-attachments/assets/f0945c01-0fcb-4607-9226-4a3b2bcb05e1)

### SamGeo Panel (Segment Anything Model)

Sample dataset:

-   [uc_berkeley.tif](https://huggingface.co/datasets/giswqs/geospatial/resolve/main/uc_berkeley.tif)
-   [wa_building_image.tif](https://github.com/opengeos/datasets/releases/download/places/wa_building_image.tif)
-   [wa_building_centroids.geojson](https://github.com/opengeos/datasets/releases/download/places/wa_building_centroids.geojson)
-   [wa_building_bboxes.geojson](https://github.com/opengeos/datasets/releases/download/places/wa_building_bboxes.geojson)

Steps:

1. Click the **SamGeo** button in the GeoAI toolbar (or `GeoAI` menu → `SamGeo`)
2. In the **Model** tab:

    - Select the SAM model version (SamGeo3/SAM3, SamGeo2/SAM2, or SamGeo/SAM1)
    - Configure backend (meta or transformers) and device (auto, cuda, cpu)
    - Click "Load Model" to initialize the model
    - Select a raster layer or browse for an image file and click "Set Image"

    ![](https://github.com/user-attachments/assets/600b0879-f851-4423-b668-cb9e8df28425)

3. Choose a segmentation method:

    - **Text Tab**: Enter text prompts describing objects to segment (e.g., "tree, building")

        ![](https://github.com/user-attachments/assets/da2c17fc-4633-488d-ba44-00f1cd97555c)

    - **Interactive Tab**:

        - Click "Add Foreground Points" or "Add Background Points" and click on the map
        - Or click "Draw Box" and drag a rectangle on the map
        - Click "Segment by Points" or "Segment by Box"

        ![](https://github.com/user-attachments/assets/6730737d-62fc-438a-bff5-cffb685d391e)

    - **Batch Tab**: Add multiple points interactively or load from a vector file/layer

        ![](https://github.com/user-attachments/assets/104ec741-44cc-404a-9213-36cf78456171)

4. In the **Output** tab:

    - Select output format (Raster GeoTIFF, Vector GeoPackage, or Vector Shapefile)
    - For vector output, optionally enable regularization:
        - Check "Regularize polygons (orthogonalize)"
        - Set Epsilon (simplification tolerance) and Min Area (filter small polygons)
    - Click "Save Masks" to export results

    ![](https://github.com/user-attachments/assets/5c80cc57-3870-4a20-bb74-73e394ef22a6)

### Clear GPU Memory

Click the **GPU** button in the GeoAI toolbar to release GPU memory from all loaded models (Moondream, SamGeo, etc.) and clear CUDA cache. Use this frequently when switching between large models to prevent out-of-memory errors.

![](https://github.com/user-attachments/assets/76c9dd8a-581c-4975-9ecb-4bfe301447bd)

### Plugin Update Checker

Go to `GeoAI` menu → `Check for Updates...` to see if a newer version of the GeoAI plugin is available. Click on the `Check for Updates` button to fetch the latest version info from GitHub. If an update is found, click the `Download and Install Update` button to download and install the latest version automatically. Restart QGIS to apply the update.

![](https://github.com/user-attachments/assets/cc0dfd38-9b41-4735-9af0-c49b7aa71b72)

### Diagnostics Report

Go to `GeoAI` menu → `Generate Diagnostics Report...` to create a Markdown report that can be copied directly into a GitHub issue. The report includes the plugin version, QGIS/Python runtime, operating system, managed virtual environment path, CUDA availability, GPU details, and versions/import status for key packages such as `geoai-py`, PyTorch, SAM3, Transformers, and `segment-geospatial`.

## Supported Model Architectures (Segmentation)

The QGIS plugin supports any models supported by [Pytorch Segmentation Models](https://smp.readthedocs.io/en/latest/models.html), including:

-   U-Net
-   U-Net++
-   DeepLabV3
-   DeepLabV3+
-   FPN (Feature Pyramid Network)
-   PSPNet
-   LinkNet
-   MANet
-   PAN
-   UperNet
-   SegFormer
-   DPT

## Supported Encoders (Segmentation)

-   ResNet (34, 50, 101, 152)
-   EfficientNet (b0-b4)
-   MobileNetV2
-   VGG (16, 19)

## Supported SAM Models (SamGeo)

-   **SamGeo3.1 (public checkpoint)**: Text, point, and box prompts through the Meta backend, using the pinned `Comfy-Org/sam3.1` safetensors file without login

## Troubleshooting

-   If you report a plugin issue on GitHub, include the Markdown from `GeoAI` menu → `Generate Diagnostics Report...`.
-   Plugin missing after install: confirm the plugin folder exists in your QGIS profile path and that you restarted QGIS.
-   CUDA OOM: use the **GPU** button to clear cache, lower batch sizes, or switch to CPU for smaller runs.
-   Model download failures: check network/firewall, then retry loading models from the panel.

### Windows installation issues

The upstream PowerShell quick installer below is not part of the corporate
deployment. Use the Python-only setup at the top of this document or an IT-built
offline wheelhouse.

If the plugin or dependencies fail to install on Windows when using the QGIS Plugin Manager, try a clean reinstall with the quick installer instead:

1. Uninstall the GeoAI plugin completely from QGIS.
2. Close QGIS.
3. Open PowerShell and run:

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://qgis.gishub.org/install.ps1 | iex"
    ```

4. Restart QGIS.
5. Open `Plugins` → `Manage and Install Plugins...`, enable **GeoAI**, then use the plugin's dependency installer.

This sequence has resolved cases where installing dependencies directly from PowerShell or installing the plugin only through the Plugin Manager failed on Windows.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Links

-   [GeoAI Documentation](https://opengeoai.org)
-   [SamGeo Documentation](https://samgeo.gishub.org)
-   [Corporate Fork](https://github.com/Gavinex/geoai)
-   [Upstream Repository](https://github.com/opengeos/geoai)
-   [Report Corporate-Fork Issues](https://github.com/Gavinex/geoai/issues)

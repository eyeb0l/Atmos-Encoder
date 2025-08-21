# Atmos-Encoder

**Atmos-Encoder** is a tool that converts Dolby TrueHD audio into Dolby Digital Plus (E-AC3) format while preserving Atmos metadata when available.

---

## Important Notice

> ⚠️ This project contains test files adapted from the **truehdd** project. The source material has been modified to enable conversion to Dolby Digital Plus Atmos format.

---

## Overview

The encoder automatically detects whether the input `.thd` file contains Atmos audio and generates the corresponding outputs:

* Dolby Digital Plus 5.1 with Atmos (`_atmos_5_1.mp4`)
* Dolby Digital Plus 7.1 with Atmos (`_atmos_7_1.mp4`)
* Or both, depending on the chosen mode.

If no Atmos is detected, it creates a standard 5.1 DDP file.

---

## Features

* Automatic Atmos detection using [`truehdd`](https://github.com/truehdd/truehdd)
* Converts TrueHD Atmos to DDP Atmos (5.1, 7.1, or both)
* Configurable bitrate for Atmos 5.1, Atmos 7.1, and fallback DDP
* Warp mode support (`normal`, `warping`, `prologiciix`, `loro`)
* Bed conform option for Atmos (enabled by default)
* Cross-platform support (Windows/Linux/macOS)
* No `ffmpeg` required
* Live progress bar during DEE encoding
* Uses:

  * `truehdd` for analysis and decoding
  * Dolby Encoding Engine (DEE) for encoding

---

## Requirements

* `truehdd.exe` / `truehdd` (must be placed in the same folder as scripts)
* `dee.exe` / `dee` and other Dolby Encoding Engine binaries (**not included** due to licensing)
* Python 3.7 or higher
* Python module `colorama` (`pip install colorama`)

---

## Usage

Run the encoder with:

```bash
python main.py -i input_file.thd -ba 1024 -b7 1536 -am both -w normal -bc
```

### Main parameters

| Parameter                    | Description                              | Default | Allowed Values                     |
| ---------------------------- | ---------------------------------------- | ------- | ---------------------------------- |
| `-i`, `--input`              | Input `.thd` file path                   | *req.*  | Any `.thd` file                    |
| `-bd`, `--bitrate-ddp`       | Bitrate for fallback DDP 5.1 (non-Atmos) | 1024    | 256, 384, 448, 640, 1024           |
| `-ba`, `--bitrate-atmos-5-1` | Bitrate for Atmos 5.1                    | 1024    | 384, 448, 576, 640, 768, 1024      |
| `-b7`, `--bitrate-atmos-7-1` | Bitrate for Atmos 7.1                    | 1536    | 1152, 1280, 1536, 1664             |
| `-am`, `--atmos-mode`        | Select Atmos mode                        | both    | 5.1, 7.1, both                     |
| `-w`, `--warp-mode`          | Warp mode                                | normal  | normal, warping, prologiciix, loro |
| `-bc`, `--bed-conform`       | Enable bed conform (Atmos only)          | enabled | toggle (default enabled)           |

---

## Example Run

```text
[INFO] Input file: input_file.thd
[INFO] Output directory: ddp_encode
[INFO] Checking for TrueHDD Decoder...
[OK] Found TrueHDD Decoder: truehdd.exe
[INFO] Analyzing TrueHD stream...

[INFO] Dolby Atmos detected.
[INFO] Selected bitrates and warp mode:
  Atmos 5.1 bitrate: 1024 kbps
  Atmos 7.1 bitrate: 1536 kbps
  Warp mode: normal
[INFO] Starting decoding...

████████████████████████████████████████ 2971927/2971927 frames (100%)
speed: 10.2x | timestamp: 00:00:00.000 | elapsed: 00:00:00
[INFO] Decoding completed. Organizing files...

[OK] Atmos file moved to ddp_encode\ddp_encode.atmos
[OK] Atmos file moved to ddp_encode\ddp_encode.atmos.audio
[OK] Atmos file moved to ddp_encode\ddp_encode.atmos.metadata
[INFO] Creating Atmos 5.1 XML...
XML written to: ddp_encode_atmos_5_1.xml
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:33:08, remaining: 00:00:00)
[INFO] Creating Atmos 7.1 XML...
XML written to: ddp_encode_atmos_7_1.xml
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:50:09, remaining: 00:00:00)
```

---

## Included files and external tools

### Python scripts

* `main.py` — Primary execution script
* `ddp_config.py` — Generates XML configuration files for DEE encoding

### Third-party tools

* `truehdd` — For audio stream analysis and decoding

### Dolby Encoding Engine (DEE) package

*Note: These proprietary binaries are not included due to licensing restrictions.*

* `dee.exe` / `dee`
* `license.lic`
* `Mediainfo.dll`
* `Mediainfo.exe`
* `mp4muxer.exe`
* `atmos_info.exe`
* `dee_audio_filter_cod.dll`
* `dee_audio_filter_convert_atmos_mezz.dll`
* `dee_audio_filter_ddp.dll`
* `dee_audio_filter_ddp_atmos.dll`
* `dee_audio_filter_ddp_single_pass.dll`
* `dee_audio_filter_ddp_transcode.dll`
* `dee_audio_filter_dthd.dll`
* `dee_audio_filter_edit_ddp.dll`
* `dee_plugin_mp4_mux_base.dll`

---

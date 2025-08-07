# Atmos-Encoder

**Atmos-Encoder** is a tool that converts Dolby TrueHD audio into Dolby Digital Plus (E-AC3) format while preserving Atmos metadata when available.

---

## Important Notice

> ⚠️ This project contains test files adapted from the truehdd project. The source material has been modified to enable conversion to Dolby Digital Plus Atmos format.

---
It automatically detects whether the input `.thd` file contains Atmos audio and generates two output versions:  
- Dolby Digital Plus 5.1 with Atmos (`_atmos_5_1.mp4`)  
- Dolby Digital Plus 7.1 (`_atmos_7_1.mp4`)

If no Atmos is detected, it creates a standard 5.1 DDP file.

---

## Features

- Automatic Atmos detection using [`truehdd`](https://github.com/truehdd/truehdd)  
- Converts TrueHD Atmos to DDP Atmos 5.1 and DDP Atmos 7.1  
- Configurable bitrate for 5.1, 7.1, and fallback DDP  
- No `ffmpeg` required  
- Uses:  
  - `truehdd` for analysis and decoding  
  - Dolby Encoding Engine (DEE) for encoding  

---

## Requirements

- `truehdd.exe` (must be placed in the same folder as scripts)  
- `dee.exe` and other Dolby Encoding Engine binaries (**not included** due to licensing)  
- Python 3.7 or higher  
- Python module `colorama` (`pip install colorama`)  

---

## Usage

Run the encoder with:

```bash
python main.py -i input_file.thd -ba 1024 -b7 1664
```

### Optional bitrate parameters

| Parameter                    | Description                                | Default | Allowed Values           |
| ---------------------------- | ------------------------------------------ | ------- | ------------------------ |
| `-bd`, `--bitrate-ddp`       | Bitrate for standard DDP 5.1 output (kbps) | 1024    | 256, 384, 448, 640, 1024 |
| `-ba`, `--bitrate-atmos-5-1` | Bitrate for Atmos 5.1 track (kbps)         | 768     | 640, 768, 1024           |
| `-b7`, `--bitrate-atmos-7-1` | Bitrate for Atmos 7.1 track (kbps)         | 1536    | 1152, 1280, 1536, 1664   |

---

## Included files and external tools

### Python scripts

* `main.py` — Primary execution script
* `ddp_config.py` — Generates XML configuration files for DEE encoding

### Third-party tools

* `truehdd.exe` — For audio stream analysis and decoding

### Dolby Encoding Engine (DEE) package

*Note: These proprietary binaries are not included due to licensing restrictions.*

* `dee.exe`
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

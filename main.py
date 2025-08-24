import os
import sys
import re
import time
import argparse
import subprocess
import platform
from colorama import Fore, Style, init
from ddp_config import (
    create_xml_5_1,
    create_xml_5_1_atmos,
    create_xml_7_1_atmos_bluray,
)

init(autoreset=True)

dee_path = None
dee_cwd = None

# -------------------- Utilities -------------------- #


def get_executable_name(name):
    return f"{name}.exe" if platform.system().lower() == "windows" else name


def build_path_in(folder, filename):
    return os.path.join(folder, filename)


def check_tool(executable, display_name):
    location = os.path.join(os.getcwd(), executable)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Checking for {display_name}...")
    if not os.path.isfile(location):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Missing tool: {executable}")
        sys.exit(1)
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Found {display_name}: {executable}")
    return location


def remove_files(folder, extensions):
    for f in os.listdir(folder):
        if f.endswith(extensions):
            try:
                os.remove(os.path.join(folder, f))
            except:
                pass


def sanitize_dee_xml(xml_path, clamp_to=1024):
    # Clamp data_rate to <=1024 for online MP4 jobs (5.1). Remove legacy tags if present.
    try:
        with open(xml_path, "r", encoding="utf-8") as fh:
            xml = fh.read()
        def _clamp(m):
            val = int(m.group(1))
            return f"<data_rate>{min(val, clamp_to)}</data_rate>"
        xml = re.sub(r"<data_rate>\s*(\d+)\s*</data_rate>", _clamp, xml, flags=re.I)
        xml = re.sub(r"<encoding_backend>.*?</encoding_backend>\s*", "", xml, flags=re.I | re.S)
        xml = re.sub(r"<encoder_mode>.*?</encoder_mode>\s*", "", xml, flags=re.I | re.S)
        with open(xml_path, "w", encoding="utf-8") as fh:
            fh.write(xml)
    except Exception as e:
        print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} XML sanitize skipped: {e}")


def run_dee(xml_file, job_dir, skip_validation=False):
    # Run DEE with optional xmllint bypass (needed for Blu‑ray 7.1 configs)
    xml_full = os.path.join(job_dir, xml_file)
    cmd = [dee_path, "-x", xml_full]
    env = os.environ.copy()

    shim_dir = None
    if skip_validation:
        import tempfile
        shim_dir = tempfile.mkdtemp(prefix="dee_shim_")
        if platform.system().lower() == "windows":
            shim = os.path.join(shim_dir, "xmllint.bat")
            with open(shim, "w") as f:
                f.write("@echo off\r\nexit /b 0\r\n")
        else:
            shim = os.path.join(shim_dir, "xmllint")
            with open(shim, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(shim, 0o755)
        env["PATH"] = shim_dir + os.pathsep + env.get("PATH", "")

    start = time.time()
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=dee_cwd,
            env=env,
        )
        log_lines = []
        for line in process.stdout:
            log_lines.append(line.rstrip())
            m = re.search(r"Overall progress: (\d+\.\d+)", line)
            if m:
                pct = float(m.group(1))
                elapsed = time.time() - start
                total = elapsed / (pct / 100) if pct else 0
                remaining = max(0, int(total - elapsed)) if pct else 0
                filled = int(40 * pct // 100)
                bar = "■" * filled + "-" * (40 - filled)
                sys.stdout.write(
                    f"\r[{bar}] {pct:.1f}% (elapsed: {time.strftime('%H:%M:%S', time.gmtime(int(elapsed)))}, "
                    f"remaining: {time.strftime('%H:%M:%S', time.gmtime(remaining))})"
                )
                sys.stdout.flush()

        process.wait()
        elapsed = time.time() - start
        if process.returncode != 0:
            print(f"\n{Fore.RED}[ERROR]{Style.RESET_ALL} DEE failed (exit {process.returncode}). Last output:")
            print("\n".join(log_lines[-40:]))
            return process.returncode
        bar = "■" * 40
        sys.stdout.write(
            f"\r[{bar}] 100.0% (elapsed: {time.strftime('%H:%M:%S', time.gmtime(int(elapsed)))}, remaining: 00:00:00)\n"
        )
        sys.stdout.flush()
        return 0
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run DEE: {e}")
        return 1


# -------------------- Arguments -------------------- #

parser = argparse.ArgumentParser(description="TrueHD to DDP encoder with Atmos support")
parser.add_argument("-i", "--input", required=True, help="Input TrueHD (.thd) file path")

# Non‑Atmos 5.1 (PCM -> DD+)
parser.add_argument(
    "-bd",
    "--bitrate-ddp",
    type=int,
    choices=[192, 256, 320, 448, 576, 640, 768, 1024],
    default=640,
    help="Bitrate for non-Atmos DDP 5.1 (default: 640)",
)

# Atmos 5.1 (online)
parser.add_argument(
    "-ba",
    "--bitrate-atmos-5-1",
    type=int,
    choices=[384, 448, 576, 640, 768, 1024],
    default=768,
    help="Bitrate for Atmos 5.1 (default: 768)",
)

# Atmos 7.1 (Blu‑ray)
parser.add_argument(
    "-b7",
    "--bitrate-atmos-7-1",
    type=int,
    choices=[1152, 1280, 1408, 1512, 1536, 1664],
    default=1536,
    help="Bitrate for Atmos 7.1 Blu-ray profile (default: 1536)",
)

parser.add_argument(
    "-am",
    "--atmos-mode",
    choices=["5.1", "7.1", "both"],
    default="both",
    help="Select Atmos output mode",
)
parser.add_argument(
    "-w",
    "--warp-mode",
    choices=["normal", "warping", "prologiciix", "loro"],
    default="normal",
    help="Warp mode (default: normal)",
)

# Bed conform toggle
group_bc = parser.add_mutually_exclusive_group()
group_bc.add_argument(
    "--bed-conform",
    dest="bed_conform",
    action="store_true",
    help="Conform Atmos bed to 5.1 (downmix 7.1 to 5.1).",
)
group_bc.add_argument(
    "--no-bed-conform",
    dest="bed_conform",
    action="store_false",
    help="Preserve original Atmos bed (keep 7.1 if present).",
)
parser.set_defaults(bed_conform=True)

parser.add_argument("--dee-dir", help="Directory containing the Dolby Encoding Engine (DEE).")
parser.add_argument("--truehdd-dir", help="Directory containing the TrueHDD executable.")
args = parser.parse_args()

# -------------------- Setup -------------------- #

input_file = os.path.abspath(args.input)
input_name = os.path.basename(input_file)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Input file: {input_name}")
if not os.path.isfile(input_file):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File does not exist: {input_name}")
    sys.exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))
final_out_dir = os.path.join(script_dir, "ddp_encode")
os.makedirs(final_out_dir, exist_ok=True)
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Output directory: {os.path.basename(final_out_dir)}")

# Resolve TrueHDD
truehdd_exec_name = get_executable_name("truehdd")
truehdd_dir = args.truehdd_dir or os.environ.get("TRUEHDD_DIR")
if truehdd_dir:
    truehdd_dir = os.path.abspath(truehdd_dir)
    truehdd_path = os.path.join(truehdd_dir, truehdd_exec_name)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Using TrueHDD directory: {truehdd_dir}")
    if not os.path.isfile(truehdd_path):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Could not find {truehdd_exec_name} in {truehdd_dir}")
        sys.exit(1)
    truehdd_cwd = truehdd_dir
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Found TrueHD Decoder: {truehdd_path}")
else:
    truehdd_path = check_tool(truehdd_exec_name, "TrueHD Decoder")
    truehdd_cwd = os.path.dirname(os.path.abspath(truehdd_path))

# Resolve DEE
dee_dir = args.dee_dir or os.environ.get("DEE_DIR") or os.environ.get("DEE_HOME")
dee_exec_name = get_executable_name("dee")
if dee_dir:
    dee_dir = os.path.abspath(dee_dir)
    dee_path = os.path.join(dee_dir, dee_exec_name)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Using DEE directory: {dee_dir}")
    if not os.path.isfile(dee_path):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Could not find {dee_exec_name} in {dee_dir}")
        sys.exit(1)
    dee_cwd = dee_dir
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Found Dolby Encoding Engine: {dee_path}")
else:
    dee_path = check_tool(dee_exec_name, "Dolby Encoding Engine")
    dee_cwd = os.path.dirname(os.path.abspath(dee_path))

# -------------------- Analyze Stream -------------------- #

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Analyzing TrueHD stream...\n")
atmos_flag = None
try:
    result = subprocess.run(
        [truehdd_path, "info", input_file],
        capture_output=True,
        text=True,
        check=True,
        cwd=truehdd_cwd,
    )
    for line in result.stdout.splitlines():
        if "Dolby Atmos" in line:
            atmos_flag = line.split()[-1].lower()
            break
    if atmos_flag == "true":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos detected.")
    elif atmos_flag == "false":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos not present.")
    else:
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Atmos information unavailable.")
except subprocess.CalledProcessError as e:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Info command failed: {e}")
    sys.exit(1)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected bitrates and warp mode:")
if atmos_flag != "true":
    print(f"  DDP 5.1 bitrate: {args.bitrate_ddp} kbps")
else:
    if args.atmos_mode in ["5.1", "both"]:
        print(f"  Atmos 5.1 bitrate: {args.bitrate_atmos_5_1} kbps")
    if args.atmos_mode in ["7.1", "both"]:
        print(f"  Atmos 7.1 bitrate: {args.bitrate_atmos_7_1} kbps")
print(f"  Warp mode: {args.warp_mode}")

# -------------------- Decode helpers -------------------- #


def decode_mezz(out_dir, bed_conform_flag):
    os.makedirs(out_dir, exist_ok=True)
    mezz_base = os.path.basename(out_dir)
    targets = {
        ".atmos": f"{mezz_base}.atmos",
        ".atmos.audio": f"{mezz_base}.atmos.audio",
        ".atmos.metadata": f"{mezz_base}.atmos.metadata",
    }

    decode_cmd = [
        truehdd_path,
        "decode",
        "--loglevel",
        "off",
        "--progress",
        input_file,
        "--output-path",
        out_dir,
    ]
    decode_cmd.extend(["--warp-mode", args.warp_mode])
    if bed_conform_flag:
        decode_cmd.append("--bed-conform")

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting decoding into {os.path.basename(out_dir)}...\n")
    rc = subprocess.run(decode_cmd, cwd=truehdd_cwd).returncode
    if rc != 0:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
        sys.exit(1)

    for base in (out_dir, script_dir):
        for f in os.listdir(base):
            fl = f.lower()
            src = os.path.join(base, f)
            for ext, new_name in targets.items():
                if fl.endswith(ext):
                    dest = os.path.join(out_dir, new_name)
                    if os.path.abspath(src) != os.path.abspath(dest):
                        if os.path.exists(dest):
                            os.remove(dest)
                        os.rename(src, dest)

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Decoding completed for {os.path.basename(out_dir)}.\n")
    return f"{mezz_base}.atmos"


# -------------------- Run pipelines -------------------- #

base_name = os.path.splitext(os.path.basename(input_file))[0]
work_51 = os.path.join(script_dir, "ddp_encode_5_1")
work_71 = os.path.join(script_dir, "ddp_encode_7_1")

if atmos_flag == "true":
    targets = []

    if args.atmos_mode in ["5.1", "both"]:
        atmos_file_51 = decode_mezz(work_51, bed_conform_flag=args.bed_conform)
        xml_5_1 = "ddp_encode_atmos_5_1.xml"
        tmp_out_5_1 = "ddp_encode_atmos_5_1.mp4"

        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 5.1 XML...")
        create_xml_5_1_atmos(
            work_51, atmos_file_51, tmp_out_5_1, args.bitrate_atmos_5_1, xml_5_1
        )
        sanitize_dee_xml(build_path_in(work_51, xml_5_1))
        rc = run_dee(xml_5_1, job_dir=work_51, skip_validation=False)
        if rc != 0:
            sys.exit(1)

        src = build_path_in(work_51, tmp_out_5_1)
        dst = build_path_in(final_out_dir, f"{base_name}_atmos_5_1.mp4")
        os.replace(src, dst)
        targets.append(dst)

    if args.atmos_mode in ["7.1", "both"]:
        if args.bed_conform:
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} 7.1 selected: overriding to no bed conform to preserve 7.1 bed.")
        atmos_file_71 = decode_mezz(work_71, bed_conform_flag=False)

        xml_7_1 = "ddp_encode_atmos_7_1.xml"
        tmp_out_7_1 = "ddp_encode_atmos_7_1.eb3"

        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 7.1 (Blu‑ray) XML...")
        create_xml_7_1_atmos_bluray(
            work_71, atmos_file_71, tmp_out_7_1, args.bitrate_atmos_7_1, xml_7_1
        )

        # Bypass DEE's online schema validation for Blu‑ray profile
        rc = run_dee(xml_7_1, job_dir=work_71, skip_validation=True)
        if rc != 0:
            sys.exit(1)

        src = build_path_in(work_71, tmp_out_7_1)
        dst = build_path_in(final_out_dir, f"{base_name}_atmos_7_1.eb3")
        os.replace(src, dst)
        targets.append(dst)

    for d in (work_51, work_71):
        if os.path.isdir(d):
            remove_files(d, (".xml", ".atmos", ".metadata", ".audio"))

    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Done. Outputs:")
    for t in targets:
        print(f"  - {t}")

else:
    # Non‑Atmos PCM -> DD+ 5.1
    work_pcm = os.path.join(script_dir, "ddp_encode_pcm")
    os.makedirs(work_pcm, exist_ok=True)
    
    # Decode to Wave64 (TrueHDD supports caf, pcm, w64)
    decode_cmd = [
        truehdd_path,
        "decode",
        "--loglevel",
        "off",
        "--progress",
        input_file,
        "--output-path",
        work_pcm,
        "--format",
        "w64",
    ]
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting W64 decoding...\n")
    rc = subprocess.run(decode_cmd, cwd=truehdd_cwd).returncode
    if rc != 0:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
        sys.exit(1)
    
    # Find the produced file (.w64 or sometimes .wav) and normalize the name
    audio_in_name = None
    for base in (work_pcm, script_dir):
        for f in os.listdir(base):
            fl = f.lower()
            if fl.endswith(".w64") or fl.endswith(".wav"):
                src = os.path.join(base, f)
                ext = os.path.splitext(f)[1].lower()
                dest_name = f"ddp_encode{ext}"  # keep the same extension
                dest = build_path_in(work_pcm, dest_name)
                if os.path.abspath(src) != os.path.abspath(dest):
                    if os.path.exists(dest):
                        os.remove(dest)
                    os.rename(src, dest)
                audio_in_name = dest_name
                break
        if audio_in_name:
            break
    
    if not audio_in_name:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No .w64 or .wav found after decode in {work_pcm}.")
        print("Directory listing:")
        for f in os.listdir(work_pcm):
            print("  -", f)
        sys.exit(1)
    
    xml_pcm = "ddp_encode_5_1.xml"
    tmp_out = "ddp_encode_5_1.ec3"
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating DDP 5.1 XML...")
    create_xml_5_1(work_pcm, audio_in_name, tmp_out, args.bitrate_ddp, xml_pcm)
    
    rc = run_dee(xml_pcm, job_dir=work_pcm, skip_validation=False)
    if rc != 0:
        sys.exit(1)
    
    src = build_path_in(work_pcm, tmp_out)
    dst = build_path_in(final_out_dir, f"{base_name}_5_1.ec3")
    os.replace(src, dst)
    # Clean both possible extensions
    remove_files(work_pcm, (".xml", ".w64", ".wav"))
    
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Done. Output: {dst}")

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Allowed rates
ALLOWED_ATMOS_51 = [384, 448, 576, 640, 768, 1024]  # MP4/online profile
ALLOWED_ATMOS_71_BLURAY = [1152, 1280, 1408, 1512, 1536, 1664]  # EB3/Blu‑ray
ALLOWED_DDP_51 = [192, 256, 320, 448, 576, 640, 768, 1024]  # Non‑Atmos DD+ 5.1


def print_saved_xml(path):
    print(f"XML written to: {os.path.basename(path)}")


def prettify(elem):
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def _bn(p):
    return os.path.basename(str(p))


def _norm(rate, allowed):
    try:
        r = int(rate)
    except Exception:
        r = allowed[-1]
    if r in allowed:
        return r
    under = [v for v in allowed if v <= r]
    return under[-1] if under else allowed[0]


def _common_input_atmos(root, output_path, atmos_file, fps="23.976"):
    input_elem = ET.SubElement(root, "input")
    audio_in = ET.SubElement(input_elem, "audio")
    atmos = ET.SubElement(audio_in, "atmos_mezz", version="1")
    ET.SubElement(atmos, "file_name").text = _bn(atmos_file)
    ET.SubElement(atmos, "timecode_frame_rate").text = fps
    ET.SubElement(atmos, "offset").text = "00:00:00:00"
    ET.SubElement(atmos, "ffoa").text = "auto"
    storage = ET.SubElement(atmos, "storage")
    local = ET.SubElement(storage, "local")
    ET.SubElement(local, "path").text = str(output_path)


def _common_misc(root, output_path):
    misc = ET.SubElement(root, "misc")
    temp_dir = ET.SubElement(misc, "temp_dir")
    ET.SubElement(temp_dir, "clean_temp").text = "true"
    ET.SubElement(temp_dir, "path").text = str(output_path)


def create_xml_5_1_atmos(output_path, atmos_file, mp4_file, data_rate, xml_filename):
    root = ET.Element("job_config")

    _common_input_atmos(root, output_path, atmos_file)

    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    encode = ET.SubElement(audio_filter, "encode_to_atmos_ddp", version="1")

    loudness = ET.SubElement(encode, "loudness")
    measure = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure, "metering_mode").text = "1770-4"
    ET.SubElement(measure, "dialogue_intelligence").text = "true"
    ET.SubElement(measure, "speech_threshold").text = "15"

    ET.SubElement(encode, "data_rate").text = str(_norm(data_rate, ALLOWED_ATMOS_51))
    ET.SubElement(encode, "timecode_frame_rate").text = "23.976"
    ET.SubElement(encode, "start").text = "first_frame_of_action"
    ET.SubElement(encode, "end").text = "end_of_file"
    ET.SubElement(encode, "time_base").text = "file_position"
    ET.SubElement(encode, "prepend_silence_duration").text = "0.0"
    ET.SubElement(encode, "append_silence_duration").text = "0.0"

    drc = ET.SubElement(encode, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "film_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "film_light"

    downmix = ET.SubElement(encode, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = "0"
    ET.SubElement(downmix, "loro_surround_mix_level").text = "-1.5"
    ET.SubElement(downmix, "ltrt_center_mix_level").text = "0"
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = "-1.5"
    ET.SubElement(downmix, "preferred_downmix_mode").text = "loro"

    ET.SubElement(encode, "custom_dialnorm").text = "0"

    output_elem = ET.SubElement(root, "output")
    mp4 = ET.SubElement(output_elem, "mp4", version="1")
    ET.SubElement(mp4, "output_format").text = "mp4"
    ET.SubElement(mp4, "override_frame_rate").text = "no"
    ET.SubElement(mp4, "file_name").text = _bn(mp4_file)
    storage_out = ET.SubElement(mp4, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)
    plugin = ET.SubElement(mp4, "plugin")
    ET.SubElement(plugin, "base")

    _common_misc(root, output_path)

    xml_str = prettify(root)
    xml_file_path = os.path.join(output_path, xml_filename)
    with open(xml_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print_saved_xml(xml_file_path)


def create_xml_7_1_atmos_bluray(output_path, atmos_file, eb3_file, data_rate, xml_filename, fps="23.976"):
    # Blu‑ray profile (JOC Atmos at 1152–1664 kbps, EC‑3 with .eb3 name)
    root = ET.Element("job_config")

    _common_input_atmos(root, output_path, atmos_file, fps=fps)

    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    encode = ET.SubElement(audio_filter, "encode_to_atmos_ddp", version="1")

    loudness = ET.SubElement(encode, "loudness")
    measure = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure, "metering_mode").text = "1770-4"
    ET.SubElement(measure, "dialogue_intelligence").text = "true"
    ET.SubElement(measure, "speech_threshold").text = "15"

    ET.SubElement(encode, "data_rate").text = str(_norm(data_rate, ALLOWED_ATMOS_71_BLURAY))
    ET.SubElement(encode, "timecode_frame_rate").text = fps
    ET.SubElement(encode, "start").text = "00:00:00:00"
    ET.SubElement(encode, "end").text = "end_of_file"
    ET.SubElement(encode, "time_base").text = "embedded_timecode"

    ET.SubElement(encode, "prepend_silence_duration").text = "0f"
    ET.SubElement(encode, "append_silence_duration").text = "0f"

    drc = ET.SubElement(encode, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "film_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "film_light"

    downmix = ET.SubElement(encode, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = "-3"
    ET.SubElement(downmix, "loro_surround_mix_level").text = "-3"
    ET.SubElement(downmix, "ltrt_center_mix_level").text = "-3"
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = "-3"
    ET.SubElement(downmix, "preferred_downmix_mode").text = "loro"

    trims = ET.SubElement(encode, "custom_trims")
    ET.SubElement(trims, "surround_trim_5_1").text = "auto"
    ET.SubElement(trims, "height_trim_5_1").text = "auto"

    ET.SubElement(encode, "custom_dialnorm").text = "0"

    # Blu‑ray unlockers (this is what DME sets)
    ET.SubElement(encode, "encoding_backend").text = "atmosprocessor"
    ET.SubElement(encode, "encoder_mode").text = "bluray"

    output_elem = ET.SubElement(root, "output")
    ec3 = ET.SubElement(output_elem, "ec3", version="1")
    ET.SubElement(ec3, "file_name").text = _bn(eb3_file)  # e.g. ddp_encode_atmos_7_1.eb3
    storage_out = ET.SubElement(ec3, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)

    _common_misc(root, output_path)

    xml_str = prettify(root)
    xml_file_path = os.path.join(output_path, xml_filename)
    with open(xml_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print_saved_xml(xml_file_path)


def create_xml_5_1(output_path, wav_file, ec3_file, data_rate, xml_filename):
    root = ET.Element("job_config")
    
    # Input (WAV/W64 are both represented as <wav> in DEE)
    input_elem = ET.SubElement(root, "input")
    audio = ET.SubElement(input_elem, "audio")
    wav = ET.SubElement(audio, "wav", version="1")
    ET.SubElement(wav, "file_name").text = _bn(wav_file)  # .wav or .w64
    ET.SubElement(wav, "timecode_frame_rate").text = "not_indicated"
    ET.SubElement(wav, "offset").text = "auto"
    ET.SubElement(wav, "ffoa").text = "auto"
    storage = ET.SubElement(wav, "storage")
    local = ET.SubElement(storage, "local")
    ET.SubElement(local, "path").text = str(output_path)
    
    # Filter
    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    pcm = ET.SubElement(audio_filter, "pcm_to_ddp", version="3")
    
    loudness = ET.SubElement(pcm, "loudness")
    measure = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure, "metering_mode").text = "1770-3"
    ET.SubElement(measure, "dialogue_intelligence").text = "true"
    ET.SubElement(measure, "speech_threshold").text = "20"
    
    ET.SubElement(pcm, "encoder_mode").text = "ddp"
    ET.SubElement(pcm, "bitstream_mode").text = "complete_main"
    ET.SubElement(pcm, "downmix_config").text = "off"
    ET.SubElement(pcm, "data_rate").text = str(_norm(data_rate, ALLOWED_DDP_51))
    ET.SubElement(pcm, "timecode_frame_rate").text = "not_indicated"
    ET.SubElement(pcm, "start").text = "0:00:00.005333"
    ET.SubElement(pcm, "end").text = "end_of_file"
    ET.SubElement(pcm, "time_base").text = "file_position"
    ET.SubElement(pcm, "prepend_silence_duration").text = "0.0"
    ET.SubElement(pcm, "append_silence_duration").text = "0.0"
    ET.SubElement(pcm, "lfe_on").text = "true"
    ET.SubElement(pcm, "dolby_surround_mode").text = "not_indicated"
    ET.SubElement(pcm, "dolby_surround_ex_mode").text = "no"
    ET.SubElement(pcm, "user_data").text = "-1"
    
    # Correct DRC block (this is what schema expects here)
    drc = ET.SubElement(pcm, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "music_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "music_light"
    
    embedded_timecodes = ET.SubElement(pcm, "embedded_timecodes")
    ET.SubElement(embedded_timecodes, "starting_timecode").text = "off"
    ET.SubElement(embedded_timecodes, "frame_rate").text = "auto"
    
    # Output
    output_elem = ET.SubElement(root, "output")
    ec3 = ET.SubElement(output_elem, "ec3", version="1")
    ET.SubElement(ec3, "file_name").text = _bn(ec3_file)
    storage_out = ET.SubElement(ec3, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)
    
    _common_misc(root, output_path)
    
    xml_str = prettify(root)
    xml_path = os.path.join(output_path, xml_filename)
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
    
    print_saved_xml(xml_path)

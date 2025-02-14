import requests
import json
import re

# 常量定义
NEW_VERSION = "maimai でらっくす PRiSM"
NEW_VERSION_RELEASES_DATE = 20240912


def load_mapping(file_path):
    """
    加载映射文件，用于 'from' 字段的版本名称转换。
    :param file_path: 映射文件路径
    :return: 映射字典，文件不存在时返回空字典
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def map_date_to_version(raw_date_str, mapping):
    """
    根据日期字符串映射到对应的版本名称。
    :param raw_date_str: 原始日期字符串（如 "20120711"）
    :param mapping: 日期字符串到版本名称的映射字典，键为日期字符串
    :return: 对应版本名称，如果日期格式不正确则返回原字符串
    """
    try:
        date_int = int(raw_date_str)
    except ValueError:
        return raw_date_str

    boundaries = sorted(int(k) for k in mapping.keys())
    if not boundaries:
        return raw_date_str

    if date_int < boundaries[0]:
        return mapping[str(boundaries[0])]

    for i in range(1, len(boundaries)):
        if date_int < boundaries[i]:
            return mapping[str(boundaries[i - 1])]
    return mapping[str(boundaries[-1])]


def parse_ds_value(ds_str):
    """
    解析 ds 字符串，提取数值部分，若包含 '+' 则返回基数+0.5，否则返回基数。
    :param ds_str: 包含难度信息的字符串
    :return: 解析后的浮点数或 None
    """
    if not ds_str:
        return None
    num_str = re.sub(r"[^\d.]", "", ds_str)
    if not num_str:
        return None
    base = float(num_str)
    return base + 0.5 if '+' in ds_str else base


def parse_notes(song, difficulty_prefix, song_type):
    """
    解析谱面音符数据及设计者信息。
    :param song: 歌曲数据字典
    :param difficulty_prefix: 难度前缀（如 "lev_bas" 或 "dx_lev_bas"）
    :param song_type: 歌曲类型，"SD" 使用4项，"DX"/"utage" 使用5项
    :return: 包含音符数组及设计者信息的字典
    """
    if song_type == "SD":
        note_keys = ["notes_tap", "notes_hold", "notes_slide", "notes_break"]
    else:
        note_keys = ["notes_tap", "notes_hold", "notes_slide", "notes_touch", "notes_break"]

    notes = []
    for nk in note_keys:
        key = f"{difficulty_prefix}_{nk}"
        value = song.get(key, "")
        try:
            notes.append(int(value))
        except ValueError:
            notes.append(0)
    # 如果没有设计者信息，则返回 "-"
    charter = song.get(f"{difficulty_prefix}_designer", "-")
    return {"notes": notes, "charter": charter}


def parse_basic_info(song, song_type, from_mapping):
    """
    解析歌曲的基本信息，包括标题、艺术家、BPM、发布日期、来源及是否为新版本。
    :param song: 歌曲数据字典
    :param song_type: 歌曲类型 ("SD", "DX", 或 "utage")
    :param from_mapping: 日期到版本名称的映射字典
    :return: 基本信息字典
    """
    # 优先判断 SD 和 DX 的情况，其它情况统一使用 date_added
    if "lev_bas" in song and "dx_lev_bas" in song:
        raw_from = song.get("date_added", "") if song_type == "SD" else song.get("date_updated", "")
    else:
        raw_from = song.get("date_added", "")

    mapped_from = map_date_to_version(raw_from, from_mapping)
    bpm_value = song.get("bpm", "0")
    bpm = int(bpm_value) if str(bpm_value).isdigit() else 0

    return {
        "title": song["title"],
        "artist": song["artist"],
        "genre": song.get("catcode", "其他游戏"),
        "bpm": bpm,
        "release_date": raw_from,
        "from": mapped_from,
        "is_new": mapped_from == NEW_VERSION
    }


def process_sd_song(song, from_mapping):
    """
    将原始数据处理为 SD 类型的谱面对象。
    :param song: 原始歌曲数据字典
    :param from_mapping: 日期到版本名称的映射字典
    :return: 处理后的 SD 对象字典
    """
    temporary_id = song.get("image_url", "").replace(".png", "")
    title = song["title"]

    sd_ds, sd_levels, sd_charts = [], [], []
    # 默认难度序列
    diffs = ["bas", "adv", "exp", "mas"]
    if song.get("lev_remas"):
        diffs.append("remas")

    for diff in diffs:
        diff_i_key = f"lev_{diff}_i"
        level_key = f"lev_{diff}"
        ds_str = song.get(diff_i_key) or song.get(level_key, "")
        if ds_str:
            difficulty = parse_ds_value(ds_str)
            if difficulty is not None:
                sd_ds.append(difficulty)
                sd_levels.append(song.get(level_key, ""))
        diff_prefix = f"lev_{diff}"
        note_keys = [f"{diff_prefix}_{nk}" for nk in ["notes_tap", "notes_hold", "notes_slide", "notes_break"]]
        if any(key in song for key in note_keys):
            sd_charts.append(parse_notes(song, diff_prefix, "SD"))

    basic_info = parse_basic_info(song, "SD", from_mapping)
    return {
        "id": temporary_id,
        "title": title,
        "type": "SD",
        "comment": "",
        "ds": sd_ds,
        "level": sd_levels,
        "cids": [],
        "charts": sd_charts,
        "basic_info": basic_info
    }


def process_dx_song(song, from_mapping):
    """
    将原始数据处理为 DX 类型的谱面对象。
    :param song: 原始歌曲数据字典
    :param from_mapping: 日期到版本名称的映射字典
    :return: 处理后的 DX 对象字典
    """
    temporary_id = song.get("image_url", "").replace(".png", "")
    title = song["title"]

    dx_ds, dx_levels, dx_charts = [], [], []
    diffs = ["bas", "adv", "exp", "mas"]
    if song.get("dx_lev_remas"):
        diffs.append("remas")

    for diff in diffs:
        diff_i_key = f"dx_lev_{diff}_i"
        level_key = f"dx_lev_{diff}"
        ds_str = song.get(diff_i_key) or song.get(level_key, "")
        if ds_str:
            difficulty = parse_ds_value(ds_str)
            if difficulty is not None:
                dx_ds.append(difficulty)
                dx_levels.append(song.get(level_key, ""))
        diff_prefix = f"dx_lev_{diff}"
        note_keys = [f"{diff_prefix}_{nk}" for nk in ["notes_tap", "notes_hold", "notes_slide", "notes_touch", "notes_break"]]
        if any(key in song for key in note_keys):
            dx_charts.append(parse_notes(song, diff_prefix, "DX"))

    basic_info = parse_basic_info(song, "DX", from_mapping)
    return {
        "id": temporary_id,
        "title": title,
        "type": "DX",
        "comment": "",
        "ds": dx_ds,
        "level": dx_levels,
        "cids": [],
        "charts": dx_charts,
        "basic_info": basic_info
    }


def process_utage_song(song, from_mapping):
    """
    将原始数据处理为 UTAGE 类型的谱面对象。
    :param song: 原始歌曲数据字典
    :param from_mapping: 日期到版本名称的映射字典
    :return: 处理后的 UTAGE 对象字典
    """
    temporary_id = song.get("image_url", "").replace(".png", "")
    title = song["title"]

    # 优先尝试使用 "lev_utage_i"，否则使用 "lev_utage"
    ut_str = song.get("lev_utage_i", "") or song.get("lev_utage", "")
    difficulty = parse_ds_value(ut_str) if ut_str else None
    ds = [difficulty] if difficulty is not None else []
    level_list = [song.get("lev_utage", "")]

    note_keys = ["notes_tap", "notes_hold", "notes_slide", "notes_touch", "notes_break"]
    notes = []
    for nk in note_keys:
        key = f"lev_utage_{nk}"
        value = song.get(key, "")
        try:
            notes.append(int(value))
        except ValueError:
            notes.append(0)
    chart = {"notes": notes, "charter": "-"}
    basic_info = parse_basic_info(song, "utage", from_mapping)

    return {
        "id": temporary_id,
        "title": title,
        "type": "UTAGE",
        "comment": song.get("comment", ""),
        "ds": ds,
        "level": level_list,
        "cids": [],
        "charts": [chart],
        "basic_info": basic_info
    }


def update_special_cases(output_data):
    """
    根据特殊情况字典直接覆盖部分谱面的 id。
    同名歌曲差不多得了
    """
    special_cases = {
        "1e44516a8a3b5a51": "131",
        "e90f79d9dcff84df": "383",
    }
    for song in output_data:
        if song.get("id") in special_cases:
            song["id"] = special_cases[song.get("id")]


def update_ids_from_origin(output_data, origin_music_data):
    """
    使用本地 origin_music_data.json 文件的数据，通过 (title, type) 匹配来更新谱面 id。
    """
    origin_dict = {
        (item.get("title", ""), item.get("type", "")): item.get("id", "")
        for item in origin_music_data
    }
    for song in output_data:
        # 若特殊情况已处理，则跳过
        if song.get("id") in ["131", "383"]:
            continue
        key = (song.get("title", ""), song.get("type", ""))
        if key in origin_dict and origin_dict[key]:
            song["id"] = origin_dict[key]


def update_ds_from_diving_fish(output_data, diving_fish_data):
    """
    仅在 (title, type) 匹配时，使用 diving_fish 数据覆盖谱面 ds 数组的前两项。
    """
    diving_fish_dict = {
        (item.get("title", ""), item.get("type", "")): item for item in diving_fish_data
    }
    for idx, song in enumerate(output_data):
        key = (song.get("title", ""), song.get("type", ""))
        if key in diving_fish_dict:
            df_song = diving_fish_dict[key]
            if (
                "ds" in df_song and isinstance(df_song["ds"], list) and len(df_song["ds"]) >= 2
                and "ds" in song and isinstance(song["ds"], list) and len(song["ds"]) >= 2
            ):
                song["ds"][0] = df_song["ds"][0]
                song["ds"][1] = df_song["ds"][1]
            output_data[idx] = song


def adjust_sd_dx_ids(output_data):
    """
    对于同一标题下同时存在 SD 和 DX 类型的谱面，
    将 DX 谱面的 id 设为对应 SD 谱面 id 加上 10000。
    """
    title_groups = {}
    for song in output_data:
        title = song.get("title", "")
        if title not in title_groups:
            title_groups[title] = {}
        if song.get("type", "") in ["SD", "DX"]:
            title_groups[title][song["type"]] = song

    for group in title_groups.values():
        if "SD" in group and "DX" in group:
            sd_song = group["SD"]
            dx_song = group["DX"]
            try:
                new_dx_id = int(sd_song["id"]) + 10000
                dx_song["id"] = str(new_dx_id)
            except ValueError:
                # 若 SD 的 id 不能转换为整数，则跳过此项
                pass


def main():
    # 数据来源 URL
    oto_data_url = "https://otoge-db.net/maimai/data/music-ex.json"
    diving_fish_url = "https://www.diving-fish.com/api/maimaidxprober/music_data"

    # 获取远程数据
    data = requests.get(oto_data_url).json()
    diving_fish_data = requests.get(diving_fish_url).json()

    # 加载用于版本映射的本地文件
    from_mapping = load_mapping("music_data/mapping.json")

    output_data = []
    for song in data:
        # 使用 image_url 去除后缀作为临时 id
        if "lev_bas" in song:
            output_data.append(process_sd_song(song, from_mapping))
        if "dx_lev_bas" in song:
            output_data.append(process_dx_song(song, from_mapping))
        if "lev_utage" in song:
            output_data.append(process_utage_song(song, from_mapping))

    # 处理特殊 id 覆盖情况
    update_special_cases(output_data)

    # 从本地 origin_music_data.json 中加载数据，并更新 id
    try:
        with open("music_data/origin_music_data.json", "r", encoding="utf-8") as f:
            origin_music_data = json.load(f)
    except FileNotFoundError:
        origin_music_data = []
    update_ids_from_origin(output_data, origin_music_data)

    # 根据 diving_fish 数据更新 ds 数组的前两项
    update_ds_from_diving_fish(output_data, diving_fish_data)

    # 对同一 title 的 SD 与 DX 进行 id 调整
    adjust_sd_dx_ids(output_data)

    # 保存处理后的数据到 JSON 文件
    output_file = "convert_music_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    print(f"数据已保存到 {output_file}，先根据 origin_music_data.json 更新 id，再仅在 (title,type) 匹配时更新 ds 前两项，最后对相同 title 的 SD 和 DX 进行 id 调整。")


if __name__ == "__main__":
    main()
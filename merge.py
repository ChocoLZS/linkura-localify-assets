import os, json, shutil
import posixpath

from merge_utils import (
    merge_translated_csv_into_txt,
    line_level_dual_lang_translation_merger,
)

def merge_translation_files(raw_folder: str, translation_folder: str, pretranslation_folder, resource_folder: str):
    translation_file_index = json.load(
        open(os.path.join(pretranslation_folder, "index.json"), encoding="utf-8")
    )

    for k in translation_file_index:
        translation_file_index[k] = posixpath.join(
            pretranslation_folder, translation_file_index[k]
        )

    # overwrite fields because of higher priority
    with open(
        os.path.join(translation_folder, "index.json"), "r", encoding="utf-8"
    ) as f:
        tmp = json.load(f)
        for k in tmp:

            translation_file_index[k] = posixpath.join(translation_folder, tmp[k])

    for file in os.listdir(raw_folder):
        if not file.endswith(".txt") and not file.startswith("adv_"):
            continue
        translation_file_path = translation_file_index.get(file)
        if translation_file_path is None:
            continue

        csv: str
        txt: str
        with open(translation_file_path, "r", encoding="utf-8") as f:
            csv = "".join(f.readlines())
        with open(posixpath.join(raw_folder, file), "r", encoding="utf-8") as f:
            txt = "".join(f.readlines())
        dest_resource_path = posixpath.join(resource_folder, file)
        
        try:
            merged_txt = merge_translated_csv_into_txt(
                csv, txt, line_level_dual_lang_translation_merger
            )
            with open(dest_resource_path, "w", encoding="utf-8") as f:
                f.write(merged_txt)
            # break
        except Exception as e:
            print(e)
            print(dest_resource_path)

def collect_available_locales(data_folder: str) -> set:
    """
    扫描数据文件夹中所有JSON文件，收集可用的语言代码
    
    Args:
        data_folder (str): 数据文件夹路径
        
    Returns:
        set: 所有可用的语言代码集合
    """
    locales = set()
    
    for filename in os.listdir(data_folder):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(data_folder, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                if not isinstance(item, dict):
                    continue
                    
                translation_dict = item.get("translation", {})
                if isinstance(translation_dict, dict):
                    locales.update(translation_dict.keys())
                    
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"警告: 处理文件 {file_path} 时出错: {e}")
            continue
    
    return locales

def format_json_translation_for_locale(
    input_file_path: str, 
    output_file_path: str, 
    language_code: str,
    indent: int = 2
) -> int:
    """
    将翻译JSON文件从数组格式转换为键值对格式（针对特定语言）
    
    Args:
        input_file_path (str): 输入JSON文件路径
        output_file_path (str): 输出JSON文件路径
        language_code (str): 要提取的语言代码
        indent (int): JSON格式化缩进，默认为2
        
    Returns:
        int: 成功转换的记录数
        
    输入格式:
    [
        {
            "raw": "原文",
            "translation": {
                "zh-CN": {
                    "text": "中文翻译",
                    "author": "作者"
                }
            }
        }
    ]
    
    输出格式:
    {
        "原文": "中文翻译"
    }
    """
    try:
        # 读取输入文件
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 转换格式
        result = {}
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            raw_text = item.get("raw")
            translation_dict = item.get("translation", {})
            
            if raw_text and isinstance(translation_dict, dict):
                translation_obj = translation_dict.get(language_code)
                if translation_obj and isinstance(translation_obj, dict):
                    translation_text = translation_obj.get("text", "")
                    if translation_text:  # 只有当翻译不为空时才添加
                        result[raw_text] = translation_text
        
        # 写入输出文件
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=indent)
        
        return len(result)
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file_path}")
        return 0
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
        return 0
    except Exception as e:
        print(f"错误: {e}")
        return 0

def is_folder_empty(folder_path: str) -> bool:
    """
    检查文件夹是否只包含空的JSON文件
    
    Args:
        folder_path (str): 要检查的文件夹路径
        
    Returns:
        bool: 如果文件夹为空或只包含空JSON文件则返回True
    """
    if not os.path.exists(folder_path):
        return True
    
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    if not json_files:
        return True
    
    for json_file in json_files:
        file_path = os.path.join(folder_path, json_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 如果JSON文件不是空对象，则文件夹不为空
            if data:
                return False
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    
    return True

def process_multilingual_translations(
    source_folder: str,
    base_dest_folder: str,
    folder_type: str = "genericTrans"
) -> set:
    """
    处理多语言翻译文件，为每个语言代码创建对应目录
    
    Args:
        source_folder (str): 源数据文件夹路径
        base_dest_folder (str): 基础目标文件夹路径
        folder_type (str): 文件夹类型（genericTrans 或 masterTrans）
        
    Returns:
        set: 处理的有效语言代码集合（排除当前处理类型中为空的文件夹）
    """
    # 收集所有可用的语言代码
    available_locales = collect_available_locales(source_folder)
    valid_locales = set()
    
    print(f"发现的语言代码: {sorted(available_locales)}")
    
    for locale_code in available_locales:
        # 为每个语言代码创建目录
        locale_dest_folder = os.path.join(base_dest_folder, locale_code, folder_type)
        
        # 清理并重新创建目录
        if os.path.exists(locale_dest_folder):
            shutil.rmtree(locale_dest_folder)
        os.makedirs(locale_dest_folder, exist_ok=True)
        
        print(f"处理语言: {locale_code}")
        total_translations = 0
        
        # 处理该语言的所有JSON文件
        for filename in os.listdir(source_folder):
            if filename.endswith('.json'):
                source_file_path = os.path.join(source_folder, filename)
                dest_file_path = os.path.join(locale_dest_folder, filename)
                
                count = format_json_translation_for_locale(
                    source_file_path, 
                    dest_file_path, 
                    locale_code
                )
                total_translations += count
                
                if count > 0:
                    print(f"  {filename}: {count} 条翻译")
        
        print(f"语言 {locale_code} 总计: {total_translations} 条翻译")
        
        # 如果当前处理类型有翻译内容，则记录为有效语言
        if total_translations > 0:
            valid_locales.add(locale_code)
        # 只清理当前处理类型的空文件夹，不删除整个语言文件夹
        elif is_folder_empty(locale_dest_folder):
            try:
                shutil.rmtree(locale_dest_folder)
                print(f"删除空的 {folder_type} 文件夹: {locale_code}/{folder_type}")
            except OSError as e:
                print(f"删除文件夹失败 {locale_code}/{folder_type}: {e}")
    
    return valid_locales

def get_language_display_names() -> dict:
    """
    获取语言代码的显示名称映射
    
    Returns:
        dict: 语言代码到显示名称的映射
    """
    return {
        "zh-CN": "简体中文",
        "zh-TW": "繁体中文", 
        "ja-JP": "日本語",
        "en": "English",
        "en-US": "English",
        "ko-KR": "한국어",
        "fr-FR": "Français",
        "de-DE": "Deutsch",
        "es-ES": "Español",
        "it-IT": "Italiano",
        "pt-BR": "Português",
        "ru-RU": "Русский"
    }

def cleanup_empty_locale_folders(base_dest_folder: str, all_locales: set) -> set:
    """
    清理完全为空的语言文件夹
    
    Args:
        base_dest_folder (str): 基础目标文件夹路径
        all_locales (set): 所有处理过的语言代码
        
    Returns:
        set: 有效的语言代码集合
    """
    valid_locales = set()
    
    for locale_code in all_locales:
        locale_base_folder = os.path.join(base_dest_folder, locale_code)
        
        if not os.path.exists(locale_base_folder):
            continue
            
        # 检查语言文件夹下的所有子文件夹是否都为空
        has_content = False
        
        for subfolder in ["genericTrans", "masterTrans"]:
            subfolder_path = os.path.join(locale_base_folder, subfolder)
            if os.path.exists(subfolder_path) and not is_folder_empty(subfolder_path):
                has_content = True
                break
        
        if has_content:
            valid_locales.add(locale_code)
        else:
            # 删除整个语言文件夹
            try:
                shutil.rmtree(locale_base_folder)
                print(f"清理完全为空的语言文件夹: {locale_code}")
            except OSError as e:
                print(f"删除语言文件夹失败 {locale_code}: {e}")
    
    return valid_locales

def generate_i18n_config(available_locales: set, output_path: str) -> None:
    """
    生成或更新 i18n.json 配置文件
    
    Args:
        available_locales (set): 可用的语言代码集合
        output_path (str): 输出文件路径
    """
    language_names = get_language_display_names()
    
    # 生成配置
    config = []
    for locale_code in sorted(available_locales):
        display_name = language_names.get(locale_code, locale_code)
        config.append({
            "name": display_name,
            "code": locale_code
        })
    
    # 写入配置文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"生成 i18n.json 配置，包含 {len(config)} 种语言")
    for item in config:
        print(f"  {item['code']}: {item['name']}")

if __name__ == "__main__":
    raw_folder = "./raw"
    translation_folder = "./gakuen-adapted-translation-data"
    pretranslation_folder = "./GakumasPreTranslation"
    generic_translation_source_folder = "./linkura-generic-strings-translation/data"
    resource_folder = "./local-files/resource"
    master_translation_source_folder = "./linkura-master-translation/data"
    local_files_folder = "./local-files"
    i18n_config_path = "./local-files/i18n.json"

    print("=== 开始处理多语言翻译文件 ===")
    
    # merge_translation_files(raw_folder, translation_folder, pretranslation_folder, resource_folder)
    # shutil.copy(
    #     f"{pretranslation_folder}/etc/localization.json",
    #     f"./local-files/localization.json",
    # )
    
    # 收集所有语言代码
    all_locales = set()
    
    # 处理 generic 翻译
    print("\n--- 处理 Generic 翻译 ---")
    generic_locales = process_multilingual_translations(
        generic_translation_source_folder,
        local_files_folder,
        "genericTrans"
    )
    all_locales.update(generic_locales)

    # 处理 master 翻译
    print("\n--- 处理 Master 翻译 ---")
    master_locales = process_multilingual_translations(
        master_translation_source_folder,
        local_files_folder,
        "masterTrans"
    )
    all_locales.update(master_locales)

    # 最终清理：删除完全为空的语言文件夹
    print("\n--- 清理空文件夹 ---")
    final_locales = cleanup_empty_locale_folders(local_files_folder, all_locales)

    # 生成 i18n.json 配置文件
    print("\n--- 生成 i18n.json 配置文件 ---")
    generate_i18n_config(final_locales, i18n_config_path)
    
    print(f"\n=== 处理完成 ===")
    print(f"总共处理了 {len(final_locales)} 种语言: {sorted(final_locales)}")
    if final_locales:
        print(f"文件结构:")
        print(f"  ./local-files/")
        for locale in sorted(final_locales):
            print(f"    {locale}/")
            print(f"      genericTrans/")
            print(f"      masterTrans/")
        print(f"    i18n.json")
    else:
        print("没有有效的翻译内容，所有语言文件夹都已清理")

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

def format_json_translation(
    input_file_path: str, 
    output_file_path: str, 
    language_code: str = "zh-CN",
    indent: int = 2
) -> None:
    """
    将翻译JSON文件从数组格式转换为键值对格式
    
    Args:
        input_file_path (str): 输入JSON文件路径
        output_file_path (str): 输出JSON文件路径
        language_code (str): 要提取的语言代码，默认为"zh-CN"
        indent (int): JSON格式化缩进，默认为2
        
    输入格式:
    [
        {
            "raw": "原文",
            "translation": {
                "zh-CN": "中文翻译",
                "en": "英文翻译"
            },
            "author": "作者"
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
                translation = translation_dict.get(language_code, "")
                if translation and translation["text"]:  # 只有当翻译不为空时才添加
                    result[raw_text] = translation["text"]
        
        # 写入输出文件
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=indent)
        
        print(f"成功转换 {len(result)} 条翻译记录")
        print(f"输出文件: {output_file_path}")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    raw_folder = "./raw"
    translation_folder = "./gakuen-adapted-translation-data"
    pretranslation_folder = "./GakumasPreTranslation"
    generic_translation_source_folder = "./linkura-generic-strings-translation/data"
    generic_translation_dest_folder = "./local-files/genericTrans"
    resource_folder = "./local-files/resource"
    master_translation_source_folder = "./linkura-master-translation/data"
    master_translation_dest_folder = "./local-files/masterTrans"

    # merge_translation_files(raw_folder, translation_folder, pretranslation_folder, resource_folder)
    # shutil.copy(
    #     f"{pretranslation_folder}/etc/localization.json",
    #     f"./local-files/localization.json",
    # )
    if os.path.exists(generic_translation_dest_folder):
        shutil.rmtree(generic_translation_dest_folder)
    shutil.copytree(generic_translation_source_folder, generic_translation_dest_folder)
    
    # 转换复制后的JSON文件格式
    for filename in os.listdir(generic_translation_dest_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(generic_translation_dest_folder, filename)
            format_json_translation(file_path, file_path, "zh-CN")

    # if os.path.exists(master_translation_dest_folder):
    #     shutil.rmtree(master_translation_dest_folder)
    # shutil.copytree(master_translation_source_folder, master_translation_dest_folder)
